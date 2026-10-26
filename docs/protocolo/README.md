# Contrato de comandos e telemetria v1 — INT03 (#23)

Este é o contrato compartilhado entre firmware e computador. A versão 1 mantém
os nomes e unidades do painel TEL02 e acrescenta mapa, estatísticas e envelopes
de comando/ACK. O modelo executável está em
[`modelos.py`](../../src/telemetria/telemetria/modelos.py); o
[`v1.schema.json`](v1.schema.json) permite inspeção por outras equipes.
Mudanças incompatíveis de campos, significado ou unidade exigem nova versão.
Não há negociação nem conversão silenciosa de versões.

## Transporte e limites

| Item | Regra v1 |
| --- | --- |
| Codificação | Um objeto JSON UTF-8 por linha, sem BOM; LF (`0x0a`) termina o frame |
| Tamanho | Até **4096 bytes de payload**, excluindo LF; contar bytes, não caracteres |
| Serial | UART dedicada, **115200 baud, 8N1**, timeout de escrita zero no firmware |
| TCP | Stream TCP simples; ESP32 cliente STA → computador servidor na porta configurada (exemplo 8765) |
| Taxa inicial | **10 amostras/s**, separada do controle (exemplo simulado: 100 ciclos/s) |
| Eventos | Além da taxa de amostragem, sempre sujeitos aos limites da fila |
| Reconexão | Novo stream, novo buffer de linhas; nenhum `start` nem comando automático |
| Debug | REPL/UART de debug ou stderr no computador; jamais misturado ao stream de dados |

TCP e serial podem fragmentar ou agrupar qualquer número de linhas. O receptor
só valida linhas completas. Linha grande é descartada até o próximo LF;
UTF-8/JSON inválido, tipos incorretos, campos desconhecidos e versão incompatível
são rejeitados e contados. Uma linha parcial não atravessa desconexões.
CRLF é tolerado como espaço JSON final, mas o emissor produz LF. A conexão
NiceGUI do navegador é interna ao painel: Socket.IO/WebSocket não faz parte
deste transporte entre ESP32 e computador.

Não há segredos no contrato ou no Git. A rede STA precisa ser confirmada no local
do desafio; pode ser um roteador local sem Internet. Os adaptadores não assumem
GPIOs nem modelo de placa enquanto INT02 (#22) estiver pendente. Limites de
buffer e orçamento por ciclo estão em [FW09](../../src/firmware/TELEMETRY.md) e
[FW10](../../src/firmware/WIFI.md).

## Envelope de telemetria

| Campo | Tipo / significado |
| --- | --- |
| `schema_version` | Inteiro JSON `1` (booleano, string e `1.0` não são aceitos) |
| `robot_id` | String 1..40, identidade estável do robô |
| `boot_id` | String 1..40, nova e única por boot, comum a todos os transportes |
| `run_id` | String 1..40 ou `null` antes/fora de uma corrida; não reutilizar no mesmo boot |
| `maze_id` | String 1..20 ou `null` se desconhecido; obrigatório para mapa |
| `seq` | Inteiro não negativo, crescente **por boot**, comum aos eventos e às corridas |
| `t_ms` | Inteiro não negativo, milissegundos monotônicos desde o boot; não é UTC |
| `event` | `start`, `sample`, `map_update`, `finish` ou `fault` |
| `state` | String 1..30 com estado local da máquina de estados FW08 |

`run_id`/`maze_id` ausentes têm o mesmo significado de `null` na telemetria;
em comandos/ACK devem ser explícitos. `seq` e `t_ms` são limitados a `2**53-1`
para preservar inteiros em clientes JSON/JavaScript. `seq` não volta a zero em
reconexão nem em uma nova corrida. Saltos indicam perda ou descarte; não se
inventam amostras para preenchê-los. Se serial e TCP estiverem ativos ao mesmo
tempo, a aplicação deve replicar o **mesmo frame e sequência**; os exemplos
fornecidos usam um transporte por publisher.

O relógio de firmware deve estender `ticks_ms()` com `ticks_diff()`, como faz
`TicksClock`, e ser consultado antes de meio período de rollover. Reiniciar o
contador de tempo requer novo `boot_id`. A aplicação cria os identificadores;
nenhum adaptador de transporte cria uma nova corrida.

| Evento | Payload / condição |
| --- | --- |
| `start` | Aplicação iniciou uma corrida por ação local autorizada; exige `run_id` |
| `sample` | Snapshot parcial de leituras; pode ser enviado no estado `pronto` sem corrida |
| `map_update` | Exige `maze_id` e objeto `map`; delta de células conhecidas |
| `finish` | Encerramento local, inclusive parada/aborto; exige `run_id` |
| `fault` | Exige `fault: {code, message}`; pode ocorrer fora de corrida |

`finish` é terminal para esse `run_id`: snapshots posteriores fora da corrida
usam `run_id=null`; uma nova corrida recebe outro identificador.

`fault` só aparece no evento `fault`, com código de 1..40 e mensagem de até 200
caracteres. `map` só aparece em `map_update`. Os estados de exemplo são `pronto`,
`executando`, `concluido`, `parado` e `falha`; o contrato admite outros nomes
limitados para acomodar a FW08, sem lhes atribuir transições implícitas.

## Leituras, mapa e diagnóstico

Uma leitura é `{value, unit, source, valid}`. `value` pode ser número finito ou
`null`; `source` é `simulated`, `measured` ou `estimated`; `valid` é booleano.
Sem leitura: `value=null, valid=true`. Leitura inválida: `valid=false`; qualquer
valor numérico presente é ignorado pelo painel. Ausência ou `null` não equivale
a zero. Nunca publicar estimativas com origem medida. `value` ausente assume
`null`; `valid` ausente assume `true`.

| Campo opcional | Estrutura e unidade fixa |
| --- | --- |
| `wheel_left`, `wheel_right` | `{speed: leitura, target: leitura}`, ambos em `mm/s` |
| `control_error` | Leitura em `mm/s` |
| `sensors` | Até 8 sensores, nomes de 1..24 caracteres, distância em `cm`; omitido = `{}` |
| `battery_voltage` | Leitura em `V`; não implica corrente, consumo ou percentual de carga |
| `map` | `{width, height, source, cells}` |
| `telemetry_stats` | Contadores de controle e fila descritos abaixo |

Todos os campos opcionais acima, exceto `sensors`, podem ser omitidos ou `null`.
Unidades são explícitas; converter na aquisição antes de publicar. Novas
grandezas, como gyro, precisam de uma extensão versionada; não reutilizar campo
de distância. Não são aceitos `NaN`, infinito ou coerção de texto para número.

O mapa tem dimensões de 1..32 e de 1..32 células por delta. Cada célula é
`{x, y, walls, known}`, com coordenadas inteiras dentro do mapa, sem repetição
no delta. Origem `(0,0)` é o canto inferior esquerdo, `x` cresce para leste e `y`
para norte, como no Flood Fill. Máscaras de 4 bits usam **N=1, E=2, S=4, W=8**.
`known` indica os lados observados: bit zero significa desconhecido.
`walls` deve ser subconjunto de `known`; um lado conhecido sem parede indica
passagem. `source` é a origem do delta inteiro. Dividir mapas grandes em deltas
que caibam em 4096 bytes. O consumidor substitui o registro de cada célula; um
delta deve trazer todos os lados já conhecidos daquela célula. Perda de um
delta pode deixar o mapa incompleto: republicar células periodicamente; não
declarar mapa completo por inferência do link.

`telemetry_stats` contém inteiros não negativos cumulativos por boot:
`control_cycles`, `control_late_cycles`, `samples_dropped`, `events_dropped` e
`queue_high_water`. A aplicação informa atraso conforme seu prazo de controle;
o transporte não mede jitter físico por conta própria. Contadores são um
snapshot antes da inclusão do próprio frame e aparecem no próximo envio.

## Comandos e ACK

O contrato reserva os comandos abaixo. **Os adaptadores FW09/FW10 e o receptor
TEL01 desta entrega são passivos para comandos**: não executam movimento,
nem enviam comandos automaticamente. A ligação à máquina de estados/motores
depende da FW08 e da confirmação do regulamento. Os modelos e exemplos permitem
que essa integração futura seja feita com o mesmo envelope.

Comando tem exatamente `schema_version`, `kind="command"`, `robot_id`, `boot_id`,
`run_id`, `command_id`, `command` e `expires_at_ms`. `command_id` é string de
1..40, única por boot e não reutilizada. `run_id` é o contexto esperado, inclusive
`null` quando o robô está pronto sem corrida. `expires_at_ms` é o prazo no relógio
do **robô**, obtido de telemetria recente; deve estar no futuro e no máximo
5000 ms à frente. Não emitir comandos se a estimativa desse relógio estiver
desatualizada. Esta proteção elimina pacotes atrasados sem comparar relógios UTC.

| Comando | Estados aceitos / comportamento requerido na integração |
| --- | --- |
| `ping` | Qualquer estado; responde ACK sem alterar controle |
| `stop` | Qualquer estado; parada local idempotente; em execução encerra pelo caminho seguro da FW08 |
| `start` | Somente `pronto`, `run_id=null` e permissão local explícita baseada no regulamento; **desabilitado por padrão** |

Antes de executar: validar schema e destino, contexto de boot/run, prazo e
estado. Envelope malformado é descartado; nenhum efeito. Um comando válido
recebe `{schema_version, kind:"ack", robot_id, boot_id, run_id, command_id,
status, error, state, t_ms}` com snapshot do robô. `status="ok"` exige
`error=null`; `status="error"` exige um destes códigos:

- `wrong_target`: robô, boot ou corrida diferente do contexto atual.
- `expired`: prazo vencido ou mais de 5000 ms à frente.
- `invalid_state`: comando incompatível com o estado local.
- `remote_start_disabled`: início remoto sem permissão local.
- `id_conflict`: mesmo `command_id` com envelope diferente durante sua janela.
- `busy`: memória de idempotência/execução cheia; não executar.

O integrador deve guardar envelope e ACK por `command_id` até o vencimento,
com capacidade inicial de 32 comandos. Duplicata **idêntica** devolve o ACK
guardado sem executar novamente, inclusive se o estado mudou desde a primeira
execução. Não expulsar entradas ainda válidas para liberar espaço: responder
`busy`. Depois do vencimento, retransmissão idêntica retorna `expired` sem
execução. Este cache não atravessa boot; o destino `boot_id` impede replay após
reset. Comparar identidades antes de retornar cache de outro robô/boot.

O cliente aguarda ACK por **1000 ms**, pode retransmitir o mesmo envelope uma
vez se ainda válido e, sem resposta, apresenta resultado desconhecido. Nunca
cria outro ID nem inicia de novo para compensar ACK perdido. ACK confirma
aceitação pelo controle; evidência de início/fim vem dos eventos. Sem hardware
ou controlador, estes requisitos não significam que uma parada física foi validada.

## Perda, isolamento e reconexão

O firmware possui fila limitada (8 frames por padrão, incluindo o parcial),
prioriza `start/finish/fault` expulsando frames não críticos que ainda não foram
iniciados, preserva ordem de sequência e contabiliza perdas. Se todos os slots
forem críticos ou estiverem presos em uma escrita parcial, rejeita o novo evento
e incrementa `events_dropped`. A aplicação pode tratar essa condição localmente;
o contrato não promete entrega infinita com link ausente. Não grava flash a cada
amostra. Reconexão retransmite o parcial inteiro no novo stream, mantendo IDs.

O receptor possui fila limitada e descarta amostras em sobrecarga. Eventos
críticos aplicam backpressure se não houver amostra removível; buffers do SO/serial
também são finitos, então não há garantia de entrega física sem ACK por evento.
O painel vincula-se ao primeiro `robot_id`, rejeita outro robô, sequência
duplicada/decrescente e tempo regressivo no mesmo boot. Novo boot limpa o gráfico
e inicia nova época. Corrida nova limpa amostras anteriores, mesmo se seu `start`
se perdeu; isso não cria nem reinicia corrida no robô. Mensagens de boots/runs
já encerrados são rejeitadas, inclusive depois da reconexão.

O histórico do painel limita-se a 256 boots encerrados e 256 corridas encerradas
por boot. Ao atingir o limite, rejeita novas épocas e mantém a corrente; reiniciar
o processo do painel cria uma nova sessão de observação. Não há descarte silencioso
do histórico de proteção. Não se mistura tempo de dois boots no mesmo gráfico.

## Exemplos e verificação

- [`validos.jsonl`](validos.jsonl): todos os eventos, ausência de leitura,
  diagnóstico, comandos e ACK. Cada linha é um pacote independente.
- [`invalidos.json`](invalidos.json): casos nomeados com pacote inválido;
  inclui rejeição de versão, tipos, unidades e payload obrigatório.
- [`VALIDACAO.md`](VALIDACAO.md): comandos, resultados e pendências físicas.

O JSON Schema cobre tipos, limites e campos permitidos. Condições entre campos
(unidade por papel, evento/payload, coordenadas e máscaras, ACK coerente) são
validadas adicionalmente pelos modelos; validade de estado, prazo e destino
exige contexto da aplicação. Schema estático sozinho não substitui essas etapas.

Para regenerar o schema, no ambiente Python com dependências de telemetria:

```bash
python docs/protocolo/exportar_schema.py
cd src/telemetria
pytest tests/test_contrato.py tests/test_modelos.py tests/test_estado.py
```
