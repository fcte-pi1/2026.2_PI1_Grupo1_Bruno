# Conectar a ESP32-S3-DevKitC-1 N8R2 ao painel

A placa informada pela equipe é a **ESP32-S3-DevKitC-1 N8R2**: 8 MB de flash
e 2 MB de PSRAM Quad SPI. Comece com a placa sozinha, sem motores/periféricos.
O primeiro teste usa USB para carregar/executar Python e Wi-Fi para enviar dados:

```text
computador -- USB/mpremote --> ESP32-S3 -- Wi-Fi/TCP --> painel no computador
```

Não é necessário comprar adaptador serial para esse caminho. O teste envia
apenas estado `pronto`, sequência e tempo: comprova comunicação com a placa,
sem inventar valores de sensores ou iniciar uma corrida.

## 1. Preparar o computador

Na raiz do clone, no Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r src/telemetria/requirements.txt mpremote esptool
mpremote connect list
```

Conecte um **cabo USB de dados** à porta da placa identificada como
**USB-to-UART/UART**. A outra porta, USB nativa do S3, não é uma UART1 de
telemetria. Escolha a porta que apareceu na listagem, por exemplo:

```bash
PORTA_PLACA=/dev/ttyUSB0
mpremote connect "$PORTA_PLACA" exec "import os; print(os.uname())"
```

Se imprimir a versão do MicroPython, prossiga ao passo 2. No Windows, use o
mesmo ambiente Python e substitua a porta por `COM3`, por exemplo. Feche Thonny,
monitores seriais e outras sessões de mpremote que estejam usando essa porta.

**Se a placa ainda não tem MicroPython:** baixe o `.bin` **ESP32_GENERIC_S3
v1.26.0 da seção padrão** na [página oficial](https://micropython.org/download/ESP32_GENERIC_S3/).
N8R2 usa PSRAM Quad, portanto não escolha `spiram-oct` (destinada à PSRAM Octal).
Essa versão mantém a referência usada pelo adaptador; não use uma preview.
Instalar firmware apaga o programa/arquivos anteriores: faça backup se houver.

```bash
python -m esptool --chip esp32s3 --port "$PORTA_PLACA" erase-flash
python -m esptool --chip esp32s3 --port "$PORTA_PLACA" --baud 460800 \
  write-flash 0x0 /caminho/para/ESP32_GENERIC_S3-20250809-v1.26.0.bin
```

Troque o caminho pelo arquivo baixado. Se não conectar ao bootloader: segure
BOOT, aperte/solte RESET e solte BOOT; repita a gravação. Depois aperte RESET
e confirme `os.uname()` com o comando acima. Não grave firmware em cada teste.

## 2. Copiar três arquivos e configurar a rede

Ainda na raiz do clone, com o ambiente ativado:

```bash
mpremote connect "$PORTA_PLACA" fs cp src/firmware/telemetry.py :telemetry.py
mpremote connect "$PORTA_PLACA" fs cp src/firmware/wifi_telemetry.py :wifi_telemetry.py
mpremote connect "$PORTA_PLACA" fs cp src/firmware/board_smoke.py :board_smoke.py
cp src/firmware/wifi_config.example.py src/firmware/wifi_config.py
```

Edite `src/firmware/wifi_config.py`: coloque `SSID`, `PASSWORD`, o **IPv4 do
computador** em `HOST` e `PORT=8765`. Use uma rede **2,4 GHz**, com placa e
computador na mesma rede e sem isolamento entre clientes. `HOST` não é
`127.0.0.1` nem o IP da própria placa; no Linux, `hostname -I` ajuda a encontrar
o IP do computador. O arquivo preenchido é ignorado pelo Git.

```bash
mpremote connect "$PORTA_PLACA" fs cp src/firmware/wifi_config.py :wifi_config.py
```

Não copie `main.py`/`boot.py` nem instale NiceGUI, Pydantic ou pySerial na placa.
O teste será iniciado manualmente e não altera a aplicação que roda no boot.

## 3. Receber no computador e executar na placa

No **terminal 1**, na raiz do clone e com o ambiente ativado:

```bash
PYTHONPATH=src/telemetria python -m telemetria --tcp-listen 0.0.0.0:8765
```

Abra [localhost:8080](http://localhost:8080). No **terminal 2**, ative o mesmo
ambiente, defina `PORTA_PLACA` novamente e execute:

```bash
mpremote connect "$PORTA_PLACA" exec "import board_smoke; board_smoke.run('wifi', duration_s=30)"
```

O terminal 2 fica ocupado por 30 segundos. No painel, o esperado é:

- conexão `conectado`, estado `pronto`, sequência e tempo aumentando;
- sensores/bateria indisponíveis, pois nenhum driver faz leituras nesse teste;
- nenhuma corrida iniciada; ao final, conexão encerrada.

Isso valida placa → rede → receptor → painel. Para verificar reconexão, use
`duration_s=120`, feche/reabra o painel durante o teste e confira o mesmo
`boot_id`, sem reiniciar a corrida. Para ver IDs e JSON, inicie o receptor com
`--headless --verbose`; `--captura /tmp/bancada.jsonl` salva os frames válidos.

Se não chegar dado: confira IP/SSID/senha, Wi-Fi 2,4 GHz, isolamento do roteador
e liberação da porta TCP 8765 no firewall. `Connection refused` normalmente
significa receptor fechado ou porta errada. `ModuleNotFoundError` na placa
indica arquivo não copiado. Permissão negada na porta USB exige acesso ao
dispositivo (grupo `dialout`/`uucp`, conforme a distribuição).

## Serial dedicada, se vocês tiverem adaptador TTL 3,3 V

Para testar FW09, mantenha o USB da placa para mpremote e conecte um **segundo
adaptador USB–serial TTL de 3,3 V**, com GPIO17/18 livres dos outros periféricos:

| ESP32-S3 | Adaptador |
| --- | --- |
| GPIO17 / UART1 TX | RX |
| GND | GND |

A alimentação continua pelo USB da placa; deixe VCC e TX do adaptador sem
conexão. O teste só transmite. A UART1 usa TX=17/RX=18 a 115200, 8N1, conforme
os pinos expostos dessa DevKit. **A porta USB-to-UART da placa usa UART0** e
não recebe automaticamente os bytes enviados na UART1.

No terminal 1, substitua pela porta do **adaptador**, não pela do mpremote:

```bash
PYTHONPATH=src/telemetria python -m telemetria --serial /dev/ttyUSB1 --baud 115200
```

No terminal 2:

```bash
mpremote connect "$PORTA_PLACA" exec "import board_smoke; board_smoke.run('serial', duration_s=30)"
```

Sem adaptador separado, faça o teste Wi-Fi acima; não abra o painel serial e o
mpremote na mesma porta. Não use UART0/REPL como canal definitivo de dados.

## Depois da primeira conexão

O próximo passo é a aplicação do robô chamar `publisher.sample(...)` com suas
leituras reais e `service(...)` após o controle, como em [FW09](TELEMETRY.md)
e [FW10](WIFI.md). Esse teste não configura motores, encoders ou sensores, não
substitui a FW08 e não deve ser copiado como laço de controle.

Até alguém executar estes passos na placa, o resultado continua **pendente de
bancada**. Registre versão, transporte, duração e resultado; não inclua senha
da rede. O modelo foi informado pela equipe, mas os testes automatizados deste
repositório ainda usam o computador e adaptadores falsos.

Referências: [DevKitC-1 N8R2 e pinagem](https://docs.espressif.com/projects/esp-idf/en/v5.0/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1-v1.0.html),
[firmware S3](https://micropython.org/download/ESP32_GENERIC_S3/),
[mpremote](https://docs.micropython.org/en/v1.26.0/reference/mpremote.html).
