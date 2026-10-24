# _Firmware_
Esta pasta deverá armazenar arquivos referentes a:

## FW09 / FW10 — Telemetria

- [Emissor serial e núcleo portátil](TELEMETRY.md): fila limitada, 10 Hz,
  escrita parcial e demonstração sem placa.
- [Adaptador Wi-Fi/TCP STA](WIFI.md): conexão local, timeout e backoff.
- [Contrato compartilhado v1](../../docs/protocolo/README.md): eventos,
  leituras, mapa, comandos reservados e limites do transporte.
- [Receptor Python e captura](../telemetria/README.md): serial ou servidor TCP,
  reprodução e painel.

Os testes usam simulação e sockets locais. Placa, pinagem e controle físico
dependem das integrações das demais equipes; não estão validados fisicamente.

## FW12 - Flood Fill

### Testes (sem hardware)
cd src/firmware
python test_floodfill.py

### Adaptador mms (opcional)
1. Baixe o mms em github.com/mackorone/mms (Releases).
2. Copie o API.py de github.com/mackorone/mms-python para src/firmware/
   (o arquivo não é versionado neste repositório).
3. No mms, crie um mouse com Directory = src/firmware e
   Run Command = python mms_adapter.py.

- Código-fonte para microcontroladores e SOCs: [Arduino](https://www.arduino.cc/), [ESP32](https://www.espressif.com/), [Raspberry Pi](https://www.raspberrypi.com/), dentre outros.
- Projetos de organização destes códigos, caso utilize IDEs: [Arduino IDE](https://www.arduino.cc/en/software/), [Visual Studio](https://visualstudio.microsoft.com/pt-br/downloads/) etc.
- Arquivos de configuração: ```CMakeLists.txt``` se for usar [CMake](https://cmake.org/download/), ```Makefile``` se for usar [make](https://www.cs.colby.edu/maxwell/courses/tutorials/maketutor/) etc.

Evite incluir:
- Artefatos de compilação: os arquivos de saída compilados (binários, arquivos objeto, .hex, .elf) devem ser gerados pelo processo de compilação e não incluídos no repositório.
- Arquivos temporários/específicos do sistema operacional: Arquivos como .DS_Store (macOS) ou arquivos de configuração do editor (a menos que esteja usando uma configuração compartilhada como .editorconfig).
- Configurações pessoais: Arquivos de configuração locais específicos da máquina do desenvolvedor.

> [!WARNING]
> **Não acrescente arquivos referentes a _hardware_ nesta pasta.** Eles deverão ser armazenados na pasta [hw](https://github.com/fcte-pi1/template/tree/main/hw) deste repositório.
