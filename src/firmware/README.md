# _Firmware_
## FW01 e FW03 — Base MicroPython e motores

- [Ambiente, estrutura, gravação e smoke test](AMBIENTE.md)
- [Controle dos motores e configuração pendente de Hardware](MOTORES.md)
- [Evidências de validação e limitações](VALIDACAO_FW01_FW03.md)

Esta pasta deverá armazenar arquivos referentes a:

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

## FW04 - Encoders e odometria

Cálculo de velocidades e pose contínua com testes sem hardware: [documentação e roteiro de bancada](ODOMETRIA.md).
