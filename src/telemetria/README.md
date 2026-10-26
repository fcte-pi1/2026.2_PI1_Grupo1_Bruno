# Telemetria do Micromouse

Painel local Python (TEL01 #17 e TEL02 #18) com receptor serial/TCP, simulador determinístico, captura e playback. O receptor é passivo: não transmite comandos nem inicia uma execução ao reconectar. Os dados do simulador levam origem `simulated`; medições reais dependem do produtor no robô.

Para usar a **ESP32-S3-DevKitC-1 N8R2**, comece pelo [guia de conexão com a placa](../firmware/CONEXAO_ESP32_S3.md). Ele cobre firmware, USB, Wi-Fi e o primeiro teste sem sensores.

## Instalação e execução

Requer Python 3.11 ou mais novo. No Linux/macOS:

```bash
cd src/telemetria
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m telemetria
```

No PowerShell/Windows:

```powershell
cd src/telemetria
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m telemetria
```

O simulador é a fonte padrão e o navegador abre em `http://localhost:8080`.

```bash
# Linux: substitua a porta pela mostrada por python -m serial.tools.list_ports
python -m telemetria --serial /dev/ttyUSB0 --baud 115200
# Windows: COM3, COM4 etc.
python -m telemetria --serial COM3 --baud 115200
# PC escuta; ESP32 conectado ao Wi-Fi em STA abre conexão como cliente
python -m telemetria --tcp-listen 0.0.0.0:8765
```

A porta serial deve estar livre: feche mpremote, REPL e monitores seriais antes de abrir o painel. No Linux, permissões do dispositivo dependem da distribuição (grupo `dialout` ou `uucp`); configure o acesso e entre novamente na sessão, se necessário. A abertura serial pode acionar DTR/RTS conforme o adaptador/driver e provocar reset físico da placa; o receptor não escreve comandos. TCP permite um cliente por vez; um segundo cliente é fechado. Escolha o IP do PC acessível pelo ESP32 e libere somente a porta necessária no firewall da rede de bancada.

| Opção | Padrão | Uso |
| --- | --- | --- |
| `--serial PORT` | — | pySerial, inclusive URL `loop://` para testes |
| `--tcp-listen HOST:PORT` | — | Servidor TCP no PC para ESP32 cliente |
| `--arquivo PATH` | — | Playback de Frames JSONL |
| `--baud` | 115200 | Baud da serial |
| `--taxa` | 10 | Hz do simulador/playback; não configura o robô |
| `--fila-max` | 256 | Máximo de eventos pendentes no receptor |
| `--captura PATH` | — | Arquivo novo de captura JSONL serial/TCP |
| `--captura-max-bytes` | 10485760 | Limite de disco da captura |
| `--headless` | — | Sem interface; Frames validados em stdout |
| `--limite N` / `--duracao S` | — | Limita headless por Frames ou tempo |
| `--rapido` | — | Playback sem espera, ainda cooperativo com o event loop |
| `--porta` | 8080 | Porta HTTP do painel |
| `--seed` | 7 | Semente determinística do simulador |
| `--intervalo-queda` / `--duracao-queda` | 25 / 4 | Segundos das quedas simuladas |
| `--sem-navegador` | — | Não abre navegador automaticamente |
| `--verbose` | — | Diagnóstico detalhado em stderr |

`--serial`, `--tcp-listen` e `--arquivo` são mutuamente exclusivos. O transporte real usa a taxa enviada pelo produtor; a taxa inicial de referência do contrato é 10 Hz.

## Testes sem hardware, captura e reprodução

O gerador usa `SimuladorRobo`, com a mesma semente e tempos calculados por passo, e produz os mesmos bytes independentemente da velocidade da máquina. A execução tem `start`, amostras/falhas e `finish`. Todas as leituras são simuladas.

```bash
# Arquivo determinístico, sem esperar 10 segundos (não sobrescreve arquivo existente)
python -m telemetria.gerador --seed 7 --taxa 10 --duracao 10 --rapido --output fake.jsonl
# Playback no painel, lento ou rápido
python -m telemetria --arquivo fake.jsonl --taxa 2
python -m telemetria --arquivo fake.jsonl --rapido
# Playback sem UI; stdout contém somente Frames JSONL normalizados
python -m telemetria --arquivo fake.jsonl --headless --rapido > validado.jsonl
```

Para exercitar TCP com processos separados:

```bash
# Terminal 1: receptor com captura JSONL limitada
python -m telemetria --tcp-listen 127.0.0.1:8765 --captura captura.jsonl
# Terminal 2: fake lento (cliente TCP)
python -m telemetria.gerador --tcp 127.0.0.1:8765 --taxa 2 --duracao 20
# Ou fake rápido para testar sobrecarga
python -m telemetria.gerador --tcp 127.0.0.1:8765 --taxa 1000 --duracao 20 --rapido
# Depois: mesma decodificação, sem UI
python -m telemetria --arquivo captura.jsonl --headless --rapido > reproduzido.jsonl
```

O gerador também emite em stdout quando não recebe `--output` nem `--tcp`. Para uma coleta finita em bancada:

```bash
python -m telemetria --serial /dev/ttyUSB0 --headless --duracao 60 --captura bancada.jsonl > frames.jsonl
```

A captura salva **somente frames validados**, um objeto JSON por linha, no mesmo formato usado pelo gerador. Não há Base64 ou envelope próprio. Bytes inválidos são rejeitados e contados pelo receptor; fragmentos incompletos são descartados ao desconectar, antes da gravação. Captura e reprodução não misturam fragmentos de conexões diferentes.

O arquivo capturado mantém a ordem recebida, incluindo duplicatas válidas; o filtro de identidade/ordem do painel e do modo headless descarta essas duplicatas e mensagens antigas ao consumir. A reprodução usa uma taxa escolhida, sem reproduzir as pausas da conexão. Capturas experimentais antigas com `capture_version`/Base64 deixam de ser suportadas; não há migração automática.

Cada leitura de transporte tem no máximo 1024 bytes. Cada escrita da captura é aguardada em thread, sem fila ilimitada; uma unidade lenta aplica backpressure ao receptor. Ao atingir o limite de disco, a captura para em uma fronteira de registro e o receptor continua, com aviso em stderr. Erros ao abrir ou escrever também suspendem a captura com diagnóstico em stderr, mantendo a recepção. Um arquivo existente não é sobrescrito. Registros incompletos no EOF são descartados.

## Contrato e tolerância a falhas

O contrato versionado em `telemetria/modelos.py` e na documentação INT03 é a referência. Cada mensagem é JSON UTF-8 terminado em LF, com **até 4096 bytes de payload, excluindo LF**. Campos principais: `schema_version`, `robot_id`, `boot_id`, `run_id`, `maze_id`, `seq`, `t_ms`, `event` (`start`, `sample`, `map_update`, `fault`, `finish`) e `state`. Cada leitura explicita `value`, `unit`, `source` e `valid`; o mapa e `telemetry_stats` são opcionais.

O receptor junta fragmentos e processa várias linhas por leitura. Payload acima do limite é rejeitado e o parser descarta até o próximo LF, usando memória limitada. UTF-8/JSON inválido, chaves duplicadas, versão incompatível, campos desconhecidos, NaN/Infinity e tipos fora do contrato são rejeitados e contados. ACKs de comandos não são Frames de telemetria: são rejeitados/contados como linhas inválidas. O receptor nunca envia comandos automaticamente.

A fila preserva a ordem dos eventos mantidos. Quando está cheia, remove a amostra `sample` mais antiga para dar lugar a dados novos; se só há eventos críticos e chega uma amostra, ela é descartada. `start`, `finish`, `fault`, `map_update` e eventos de link têm prioridade; se a fila contém só críticos, o produtor aguarda espaço. Essa política mantém a memória limitada, mas não garante ausência de perdas no buffer do driver serial durante sobrecarga. Descartes locais ficam em `fonte.estatisticas.amostras_descartadas`; estatísticas do produtor permanecem em `Frame.telemetry_stats`, com origens distintas.

A serial usa timeout de leitura de 0,1 s em thread e reconexão com espera de 1 s, dobrando até 10 s quando a abertura falha repetidamente. TCP usa leitura assíncrona com timeout de 0,5 s para checar silêncio sem inventar desconexão. Após perda de cliente, o servidor continua escutando. Fechar/cancelar a fonte fecha serial, clientes e servidor. Nenhuma reconexão altera `boot_id` ou `run_id`, redefine sequência ou emite `start`; isso pertence ao produtor. `EstadoPainel` filtra duplicados, mensagens atrasadas e trocas de identidade, isolando o histórico de execução.

Diagnósticos de conexão, limite e erros vão para stderr. Headless também mostra contadores ao encerrar; `--verbose` detalha rejeições, sem misturar diagnóstico com JSONL em stdout.

## O que o painel mostra

- Conexão: aguardando, conectado, desatualizado (mais de 2 s sem mensagem), desconectado (mais de 5 s ou link perdido). Valores ficam congelados e esmaecidos sem dados novos.
- Estado, `run_id`, labirinto, tempo do robô, sequência e quantidade de mensagens descartadas por identidade/ordem.
- Velocidade e alvo de cada roda, erro de controle, sensores e tensão da bateria.
- Origem de cada valor: simulado, medido ou estimado. Ausente aparece como indisponível/sem leitura/inválida, sem substituir por zero.
- Gráfico das velocidades nos últimos 30 s do tempo do robô e log de conexões, inícios, finais e falhas.

A bateria mostra tensão; percentual depende de curva de descarga medida. A coleta atualiza o estado em tarefa independente e a interface renderiza 4 vezes por segundo.

## Estrutura e testes

| Arquivo | Responsabilidade |
| --- | --- |
| `modelos.py` | Contrato Pydantic e eventos de link |
| `estado.py` | Estado, identidade/ordem, histórico e conexão do painel |
| `coleta.py` | Protocolo `Fonte`: `simulada`, `nome`, `eventos()` assíncrono |
| `receptor.py` | Parser incremental, fila limitada, serial e servidor TCP |
| `captura.py` | Captura JSONL limitada e fonte de playback |
| `fonte_simulada.py` / `gerador.py` | Modelo determinístico e emissor JSONL headless |
| `formatacao.py` / `painel.py` | Textos, interface NiceGUI e gráfico |
| `__main__.py` | Seleção de fonte, CLI/UI e encerramento |

```bash
pytest
ruff check .
ruff format --check .
```

Os testes exercitam parser fragmentado e sobrecarregado, contrato, pySerial real `loop://`, PTY no Linux, TCP localhost, desconexão/reconexão, cancelamento e fechamento de recursos, captura limitada, disco cheio, playback e CLI. A suíte também cobre simulador, estado e interface NiceGUI. **Validação física com ESP32, serial USB, Wi-Fi de bancada, taxa real e robô montado permanece pendente.** Nenhum resultado dos testes locais deve ser interpretado como medição no robô.
