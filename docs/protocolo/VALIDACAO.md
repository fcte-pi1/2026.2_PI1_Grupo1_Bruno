# Evidências locais — INT03, TEL01, FW09 e FW10

Verificação executada em **26/10/2026**, no Linux, com CPython **3.14.8**.
Dependências instaladas de `src/telemetria/requirements-dev.txt`, incluindo
Pydantic 2.14.1, NiceGUI 3.18.0, pySerial 3.5, pytest 9.1.1 e Ruff 0.17.2.
O ambiente virtual de teste fica fora do clone; não é versionado.

## Resultado

| Verificação | Resultado observado |
| --- | --- |
| Suíte de telemetria, painel e integração TCP com firmware | **112 passed** |
| Núcleo portátil e adaptador Wi-Fi/TCP | **33 testes, OK**, sem skips |
| Regressão do Flood Fill existente | **7 casos, todos passaram** |
| Ruff / formatação Python da telemetria | Passou; 24 arquivos formatados |
| Ruff / formatação dos novos módulos de firmware e exportador | Passou; 6 arquivos formatados |
| `git diff --check` | Passou |

Os números acima incluem testes de contrato e regressões; não são contagens
de ensaios físicos. Os testes de TCP precisam poder abrir sockets locais;
os testes de serial usam pySerial `loop://` e pseudo-terminal POSIX.
O teste do painel usa `nicegui.testing.User`.

## Rastreabilidade

| Issue | Implementação e evidência automatizada | Validação física pendente |
| --- | --- | --- |
| [#23 / INT03](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/23) | Contrato v1, JSON Schema, exemplos válidos/inválidos, modelos estritos, mapa e envelopes de comando/ACK; `test_contrato.py`, `test_modelos.py` | Confirmar placa/pinagem/firmware na INT02 e permissão de início remoto no regulamento |
| [#17 / TEL01](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/17) | Parser fragmentado/grande/inválido, fila e timeout, serial/TCP, captura/reprodução, gerador e CLI; testes `test_receptor`, `test_captura`, `test_gerador`, `test_cli` e `test_estado` | Porta UART/USB, baud efetivo, desconexão física e posse da porta na placa |
| [#11 / FW09](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/11) | `test_telemetry.py`: 20 testes, consumidor lento/ausente, perda limitada, prioridade crítica, parciais, monotonicidade e validação cruzada com Pydantic | Duração real de UART.write, orçamento de CPU/RAM e atraso do controle na ESP32 |
| [#12 / FW10](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/12) | `test_wifi_telemetry.py`: 13 testes, AP ausente, backoff/timeout, socket parcial, EAGAIN, app reiniciado e TCP real localhost | Associação STA na placa/rede do desafio, reconexão física, consumo, memória e jitter do controle |

`test_integracao_firmware.py` conecta o **publisher e adaptador TCP reais do
firmware portátil** ao **receptor TCP real** no computador, com escrita de
97 bytes por chamada. Verifica `start/sample/fault/map_update/finish`, sequência,
mesmo `run_id`, ausência de rejeição do contrato e avanço dos 100 ciclos de
controle **simulados**. A interface WLAN desse teste é falsa; o socket TCP é real.

As regressões cobrem mensagens antigas de robô/boot/corrida, `finish` terminal
mesmo após reconexão, cancelamento com fila crítica cheia, arquivos existentes,
disco cheio e fechamento de portas/arquivos. Os casos de sobrecarga conferem
os limites das filas e a continuidade do controle simulado.

## Como reproduzir

Em um ambiente com as dependências instaladas, a partir da raiz do clone:

```bash
cd src/telemetria
pytest -q
ruff check .
ruff format --check .
cd ../..

PYTHONPATH=src/telemetria python -m unittest discover -s src/firmware -p 'test_*.py' -v
python src/firmware/test_floodfill.py

ruff check --isolated --select E,F,I --line-length 110 \
  src/firmware/telemetry.py src/firmware/demo_telemetry.py \
  src/firmware/test_telemetry.py src/firmware/wifi_telemetry.py \
  src/firmware/test_wifi_telemetry.py docs/protocolo/exportar_schema.py
ruff format --isolated --line-length 110 --check \
  src/firmware/telemetry.py src/firmware/demo_telemetry.py \
  src/firmware/test_telemetry.py src/firmware/wifi_telemetry.py \
  src/firmware/test_wifi_telemetry.py docs/protocolo/exportar_schema.py
git diff --check
```

Os lints de firmware usam regras explícitas: o núcleo é portátil para
MicroPython e não depende de recursos de estilo/stdlib exclusivos de CPython.
O exportador regenera o schema e `test_contrato.py` detecta divergência entre o
arquivo versionado e os modelos executáveis. Para ensaiar sem UI, veja os
[comandos do receptor e gerador](../../src/telemetria/README.md).

## Limites da evidência

Não foi conectada placa ESP32, UART física, sensor, bateria ou robô. O código
MicroPython foi exercitado em CPython com adaptadores falsos; não foi executado
em um runtime MicroPython nem gravado na placa. As APIs da versão ESP32
MicroPython 1.26.0 foram usadas como referência documental, sem fixar o firmware
da equipe antes de INT02. Os roteiros em [FW09](../../src/firmware/TELEMETRY.md)
e [FW10](../../src/firmware/WIFI.md) descrevem o ensaio de bancada que falta.

Comandos de movimento e ACK são **contrato reservado**, com início remoto
desabilitado por padrão; sua execução não foi ligada a motores/controlador.
A integração depende da FW08 e do regulamento. Reconexão de telemetria jamais
é autorização para mover ou iniciar a corrida.

A entrega fica na branch **local** `feat/23-telemetria-integrada`, em commits
referenciando as issues. Não houve push, publicação de branch ou abertura de PR;
por isso não existe URL de PR associada a esta evidência. As issues no GitHub
permanecem inalteradas para revisão pela equipe e conclusão dos ensaios físicos.
