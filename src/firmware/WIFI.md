# FW10 — Telemetria WiFi local

O ESP32 usa MicroPython e se conecta como **STA** a uma rede WiFi local. O
computador na mesma rede executa o painel como servidor TCP; o robô inicia a
conexão. Não há serviço na nuvem, broker ou dependência de internet. A conexão
serve somente para observação: bytes recebidos são descartados e não acionam
motores, início/fim de execução nem reset do robô.

```text
ESP32 (STA, cliente TCP) -> roteador/AP local -> computador (servidor TCP)
```

No desafio, use um roteador local dedicado ou o hotspot do computador, se
permitidos pelo regulamento. Isso mantém a mesma topologia mesmo sem WiFi ou
internet do local. O endereço do computador deve ser estável (reserva DHCP ou
configuração equivalente). A implementação não cria AP no robô; se nenhum AP
estiver disponível, o controle continua e a telemetria tenta reconectar.

## Configuração e execução

1. No computador, instale as dependências do painel conforme
   [README da telemetria](../telemetria/README.md). Inicie o receptor:

   ```bash
   cd src/telemetria
   python -m telemetria --tcp-listen 0.0.0.0:8765 --sem-navegador
   ```

   Abra `http://localhost:8080`. Se necessário, permita a porta TCP escolhida no
   firewall da rede local. Use uma rede de testes de confiança: o protocolo
   local não oferece autenticação nem TLS.

2. Copie `telemetry.py` e `wifi_telemetry.py` para o sistema de arquivos do
   ESP32. Copie o conteúdo de `wifi_config.example.py` para `wifi_config.py`
   **no dispositivo ou em um diretório fora do clone** e preencha SSID, senha,
   IPv4 do computador e porta. Credenciais reais não devem entrar no Git.
   O exemplo versionado contém somente marcadores.

3. Construa a interface e o adaptador antes de iniciar os motores. Integre o
   serviço depois do passo de controle existente. Exemplo de integração
   (as funções de controle, aquisição e identificação são da aplicação):

   ```python
   import network
   import time
   import wifi_config
   from telemetry import TelemetryPublisher, TicksClock
   from wifi_telemetry import WifiTelemetry

   clock = TicksClock(time.ticks_ms, time.ticks_diff)
   publisher = TelemetryPublisher(
       robot_id=robot_id, boot_id=boot_id, run_id=run_id, maze_id="4x4",
       clock_ms=clock, sample_hz=10, queue_capacity=8,
   )
   link = WifiTelemetry(
       network.WLAN(network.WLAN.IF_STA),
       wifi_config.SSID, wifi_config.PASSWORD,
       wifi_config.HOST, wifi_config.PORT,
   )
   publisher.emit("start", "executando")

   # Corpo do laço já temporizado pela aplicação; nunca dentro de IRQ.
   while executando:
       control_step()  # Primeiro: ler sensores, controlar e aplicar motores.
       publisher.record_control_cycle(late=controle_atrasado())
       publisher.sample("executando", **telemetry_snapshot())
       link.service(publisher, time.ticks_ms(), byte_budget=256)
       # Agendamento do próximo ciclo permanece sob responsabilidade do controle.

   publisher.emit("finish", "finalizado")
   # Na fase parada, continue chamando service() para escoar os eventos.
   ```

   `boot_id` deve identificar o boot real; `run_id`, a execução real. Não crie
   nenhum deles nas reconexões. O exemplo demonstra os pontos de integração;
   não fornece drivers de motores/sensores nem substitui o laço de controle.
   `telemetry_snapshot()` deve seguir o contrato de
   [telemetry.py](telemetry.py): leituras medido/estimado/simulado explícitas,
   valores ausentes como `None`, rodas, sensores, bateria e erros disponíveis.

## Contrato e limites

O transporte usa o contrato v1 do painel, UTF-8 JSON Lines: uma mensagem por
linha, até **4096 bytes de JSON**, mais um LF. Mantém `robot_id`, `boot_id`,
`run_id`, `maze_id`, `seq`, `t_ms`, `event` e `state`, além dos payloads do
publisher comum. A amostragem inicial é **10 Hz**; eventos de início, falha,
fim e mapa usam a mesma fila. Uma reconexão não sintetiza eventos nem zera
sequência ou execução. Não há confirmação de entrega pela aplicação: um
frame entregue ao buffer TCP pode se perder antes de chegar ao painel.

Há somente a fila limitada do publisher (8 frames por padrão, incluindo o
parcial). O adaptador não cria uma segunda fila. Em sobrecarga, o core
contabiliza descartes e preserva eventos críticos conforme sua política;
não há promessa de retenção ilimitada enquanto a rede estiver indisponível.
Na reconexão, o frame que ainda estava parcialmente transmitido recomeça
**inteiro**, em uma nova sessão TCP. O receptor limpa seu acumulador de linha
entre sessões. Sequências repetidas/atrasadas são tratadas pelo estado do painel.

Cada `service()` faz uma transição de rede, consulta `poll(0)`, lê no máximo
64 bytes remotos e faz no máximo uma escrita de até `byte_budget` bytes. Não
usa `sleep`, laço de espera, `sendall`, DNS ou mDNS. `HOST` aceita somente
IPv4 decimal literal; hostnames são rejeitados antes de ativar a rede.
`TicksClock` mantém o tempo monotônico do publisher durante quedas e wrap do
contador; o adaptador usa `time.ticks_diff` nos seus próprios timeouts.

| Parâmetro | Padrão | Comportamento |
| --- | --- | --- |
| `connect_timeout_ms` | 5000 | Limite por tentativa WiFi e por tentativa TCP |
| `stall_timeout_ms` | 2000 | Fecha socket sem progresso de escrita pelo período |
| `backoff_initial_ms` | 500 | Espera inicial após falha |
| `backoff_max_ms` | 8000 | Teto da espera exponencial entre tentativas |

A configuração desliga as tentativas internas ilimitadas do driver WiFi
(`reconnects=0`). Ao vencer o timeout WiFi, desconecta a tentativa antes de
aguardar. Uma falha de socket mantém a conexão STA quando ela ainda existe.
O backoff volta ao valor inicial somente após envio com progresso. O status
do adaptador fica em `state`, `connected`, `last_error` e `reconnects`;
nenhum desses valores decide o estado de movimento do robô.

Esses limites restringem o trabalho cooperativo de rede; não são uma garantia
de tempo real de todo o firmware. Ativar o driver pode demorar e deve ocorrer
antes do movimento. Alocação/serialização e interferência de rádio precisam
ser medidas no ESP32 junto do período real de controle.

## Verificação e roteiro de bancada

```bash
cd src/firmware
python -m unittest test_telemetry test_wifi_telemetry -v
```

Os testes com fakes exercitam ausência de AP, backoff limitado, timeout de
conexão, `EINPROGRESS`/`EALREADY`/`EISCONN`, escrita parcial, `EAGAIN`, queda
de WiFi, reset de socket, encerramento remoto, atraso de envio e wrap de
ticks. Contadores confirmam que o controle simulado avança durante falhas e
a fila permanece limitada. O teste TCP de localhost usa sockets reais do
computador, envia frames em pequenos pedaços, reinicia o servidor na mesma
porta e verifica preservação do `run_id` e da sequência. Ele precisa de
permissão para criar sockets locais no ambiente de teste.

Para a bancada: registrar frequência/atrasos do controle e descartes com link
normal; desligar o AP; religá-lo; fechar/reabrir o painel; e atrasar o
consumidor. Conferir que o robô mantém o controle local, o painel marca a
queda/desatualização e a reconexão conserva a execução. Medir latência,
perda, memória, tempo de ciclo e comportamento dos motores no hardware.
**Os testes automatizados não são validação física, ensaio de bancada ou
evidência de desempenho do robô montado.**

## Referências de implementação

O alvo documentado é o port ESP32 do MicroPython v1.26.0. A referência oficial
explica [STA e `reconnects`](https://docs.micropython.org/en/v1.26.0/esp32/quickref.html#networking).
O contrato de [`socket`](https://docs.micropython.org/en/v1.26.0/library/socket.html)
permite escritas curtas, e [`select.poll`](https://docs.micropython.org/en/v1.26.0/library/select.html)
permite consulta com timeout zero. O [código do port ESP32](https://github.com/micropython/micropython/blob/v1.26.0/ports/esp32/modsocket.c)
implementa `connect` não bloqueante sobre lwIP e não expõe `getsockopt` na API
Python dessa versão. Por isso, após `POLLOUT`, o adaptador confirma com uma
segunda `connect` não bloqueante (`EISCONN` confirma; `EALREADY` mantém espera).
Em CPython/ports com suporte, usa `SO_ERROR` após `POLLOUT` para verificar a
conclusão. Erros e timeout fecham a sessão; disponibilidade de escrita por si
só não é considerada prova de conexão.
