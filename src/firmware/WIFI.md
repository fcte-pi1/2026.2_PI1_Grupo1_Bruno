# FW10 — telemetria Wi-Fi/TCP

O ESP32 é **cliente STA** e conecta a um servidor TCP no computador da mesma
rede. Sem nuvem, MQTT ou Socket.IO. Para carregar os arquivos e executar na
ESP32-S3-DevKitC-1 N8R2, siga o [guia de bancada](CONEXAO_ESP32_S3.md).
SSID/senha/IPv4/porta ficam em `wifi_config.py`, ignorado pelo Git; o arquivo
`.example.py` só contém marcadores.

## Integração ao controle

Construa o adaptador antes de iniciar os motores. No laço existente, depois
do controle e de `publisher.sample(...)`, chame:

```python
link.service(publisher, time.ticks_ms(), byte_budget=256)
```

`link` é `WifiTelemetry(wlan, ssid, password, host, port)` e `publisher` é o
[emissor comum](TELEMETRY.md). O [teste da placa](board_smoke.py) é um exemplo
executável sem sensores; não substitui o laço real da FW08.

O adaptador não cria uma segunda fila, não altera boot/corrida e descarta
bytes recebidos em vez de executar comandos. Reconexão usa outro writer para
recomeçar o parcial inteiro. O receptor deve limpar sua linha por conexão.

| Configuração | Padrão |
| --- | --- |
| Timeout por tentativa Wi-Fi/TCP | 5000 ms |
| Timeout sem progresso de escrita | 2000 ms |
| Backoff exponencial inicial / máximo | 500 / 8000 ms |
| Fila do publisher | 8 frames, incluindo parcial |

`service` não dorme: usa socket não bloqueante, `poll(0)`, até 64 bytes de
leitura e uma escrita limitada. HOST é IPv4 literal para não resolver DNS no
controle. Tentativas internas ilimitadas de Wi-Fi são desativadas com
`reconnects=0`. Backoff só reinicia após envio com progresso.

Em CPython, a conclusão de connect é verificada com SO_ERROR. No port ESP32
MicroPython 1.26, que não expõe getsockopt, uma segunda connect não bloqueante
confirma EISCONN; EALREADY continua aguardando. Timeout/erro fecha a sessão.
TCP sem ACK de aplicação pode perder um frame já aceito pelo buffer do SO.

## Verificar

```bash
cd src/firmware
python -m unittest test_telemetry test_wifi_telemetry test_board_smoke -v
```

Os testes cobrem Wi-Fi ausente, backoff, timeout, EAGAIN, parciais e rollover.
O teste localhost reinicia o servidor e mantém a corrida. Para executar na
placa, siga o [roteiro de bancada](CONEXAO_ESP32_S3.md).

Referências: [WLAN/STA](https://docs.micropython.org/en/v1.26.0/esp32/quickref.html#networking),
[socket](https://docs.micropython.org/en/v1.26.0/library/socket.html),
[implementação ESP32](https://github.com/micropython/micropython/blob/v1.26.0/ports/esp32/modsocket.c).
