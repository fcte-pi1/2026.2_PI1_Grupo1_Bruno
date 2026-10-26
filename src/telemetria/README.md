# Telemetria do Micromouse

Painel local em Python para acompanhar o robô durante os testes (issue #18, TEL02). Nesta versão o painel recebe dados de uma **fonte simulada**; o receptor serial da TEL01 (#17) entra no lugar dela sem mudar a interface.

## Como executar

Requer Python 3.11 ou mais novo.

```bash
cd src/telemetria
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m telemetria
```

O navegador abre em `http://localhost:8080`. Opções úteis:

| Opção | Padrão | Uso |
| --- | --- | --- |
| `--porta` | 8080 | Porta do painel |
| `--taxa` | 20 | Mensagens por segundo geradas pela fonte |
| `--seed` | 7 | Semente do simulador (mesma semente, mesmos dados) |
| `--intervalo-queda` | 25 | Segundos entre quedas simuladas de conexão |
| `--duracao-queda` | 4 | Duração de cada queda, em segundos |
| `--sem-navegador` | — | Não abre o navegador automaticamente |

## O que o painel mostra

- Estado da conexão: `aguardando`, `conectado`, `desatualizado` (mais de 2 s sem mensagem) e `desconectado` (mais de 5 s ou link perdido). Os valores ficam congelados e esmaecidos quando não há dados novos.
- Execução: estado do robô, `run_id`, labirinto, tempo do robô, sequência e quantidade de mensagens descartadas (duplicadas ou fora de ordem).
- Velocidade e alvo de cada roda, erro do controle, sensores de distância e tensão da bateria.
- Origem de cada valor (`simulado`, `medido` ou `estimado`). Valor ausente aparece como `indisponível`, `sem leitura` ou `inválida`, nunca como zero.
- Gráfico das velocidades nos últimos 30 s do tempo do robô, com lacunas onde não houve leitura.
- Log de conexão, início e fim de execução e falhas.

A bateria mostra apenas a tensão. O percentual de carga não é calculado enquanto não houver curva de descarga medida.

## Fonte simulada

O simulador gera uma execução de 60 s com retas, paradas e giros, ruído nas velocidades, leituras ausentes, leituras inválidas e falhas ocasionais de sensor. As quedas alternam entre dois tipos: silêncio (o link continua aberto, mas as mensagens param) e perda do link (a porta "desconecta" e volta). Ao reconectar, a execução continua com o mesmo `run_id` e a sequência pula as mensagens perdidas.

Todos os valores gerados levam origem `simulated`, então tudo o que aparece nesse modo é resultado **simulado**, não medição em bancada nem no robô.

## Formato das mensagens

O modelo em `telemetria/modelos.py` é uma proposta provisória para o contrato da INT03 (#23). Campos principais: `schema_version`, `robot_id`, `boot_id`, `run_id`, `maze_id`, `seq`, `t_ms`, `event` (`start`, `sample`, `fault`, `finish`) e `state`. Cada leitura tem `value`, `unit`, `source` e `valid`. Mensagens com versão diferente, campos desconhecidos ou valores fora do formato são rejeitadas.

Exemplo de amostra:

```json
{"schema_version": 1, "robot_id": "micromouse-01", "boot_id": "boot-1a2b3c", "run_id": "run-001", "maze_id": "4x4", "seq": 42, "t_ms": 2050, "event": "sample", "state": "executando", "wheel_left": {"speed": {"value": 287.4, "unit": "mm/s", "source": "measured", "valid": true}, "target": {"value": 300.0, "unit": "mm/s", "source": "measured", "valid": true}}, "control_error": {"value": 9.8, "unit": "mm/s", "source": "estimated", "valid": true}, "sensors": {"frontal": {"value": null, "unit": "cm", "source": "measured", "valid": true}}, "battery_voltage": {"value": 8.12, "unit": "V", "source": "measured", "valid": true}}
```

## Estrutura

| Arquivo | Responsabilidade |
| --- | --- |
| `telemetria/modelos.py` | Modelos Pydantic das mensagens e eventos de conexão |
| `telemetria/estado.py` | Estado do painel: conexão, último frame, janela do gráfico, log, descarte de duplicados |
| `telemetria/coleta.py` | Liga qualquer fonte ao estado, separada da interface |
| `telemetria/fonte_simulada.py` | Simulador determinístico do robô |
| `telemetria/formatacao.py` | Texto exibido para leituras, origem e tempo |
| `telemetria/painel.py` | Interface NiceGUI e gráfico Plotly |
| `telemetria/__main__.py` | Linha de comando |

A coleta roda como tarefa em segundo plano e só atualiza o estado; a tela lê esse estado em um temporizador próprio (4 vezes por segundo). Por isso a taxa de renderização não depende da taxa de mensagens.

Para trocar a fonte, basta um objeto com `simulada`, `nome` e um método assíncrono `eventos()` que produza `Frame`, `LinkAberto` e `LinkFechado`.

## Testes

```bash
pytest
ruff check .
ruff format --check .
```

Os testes cobrem validação das mensagens, transições de conexão, descarte de duplicados e fora de ordem, troca de boot e de execução, janela do gráfico, leituras ausentes, o simulador e a interface (com o simulador de usuário do NiceGUI).

## Limitações desta versão

- Sem receptor serial: depende da TEL01 (#17).
- Contrato de mensagens provisório até a INT03 (#23) ser fechada.
- Nenhuma validação em bancada ou no robô montado.
