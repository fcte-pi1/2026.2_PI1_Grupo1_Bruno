# FW01 — Ambiente e gravação

Entrega referente à [issue #3](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/3).

## Organização

| Caminho | Responsabilidade |
| --- | --- |
| `robo/aplicacao.py` | Ciclo de vida e parada em saída normal, exceção ou Ctrl-C |
| `robo/controle/motores.py` | Duty, rampa e reversão; independente de `machine` |
| `robo/drivers/` | Driver falso e adaptador condicional de GPIO/PWM |
| `robo/navegacao/` | Ponto de integração com os módulos existentes `floodfill.py` e `odometria.py` |
| `robo/protocolo/` | Espaço reservado ao contrato INT03, ainda sem implementação |
| `robo/inicializacao.py` | Composição com configuração externa |
| `boot.py`, `main.py` | Inicialização desabilitada; não iniciam corrida |
| `config_exemplo.py` | Modelo sem segredos e sem GPIOs inventados |
| `config_local.py` | Configuração da placa confirmada; ignorada pelo Git |

Os módulos existentes de bateria, odometria e flood fill continuam na raiz, preservando as importações e testes dos colegas. Eles não foram conectados automaticamente à aplicação. Testes `unittest`, ferramentas de gravação e dependências da telemetria são exclusivos do computador.

## Ambiente do computador

Na raiz do repositório, em PowerShell:

```powershell
python -m venv src/firmware/.venv
src/firmware/.venv/Scripts/python.exe -m pip install -r src/firmware/requirements-tools.lock.txt
python -m unittest discover -s src/firmware -p 'test_*.py'
python src/firmware/smoke_test.py
src/firmware/.venv/Scripts/mpremote.exe connect list
```

Ferramentas fixadas: mpremote 1.26.1 e esptool 5.0.2. `requirements-tools.txt` declara as ferramentas diretas; `requirements-tools.lock.txt` registra também as dependências resolvidas no Windows/CPython 3.14.0 para reproduzir este ambiente. O núcleo não instala pacotes externos. A evidência local e as limitações estão em [VALIDACAO_FW01_FW03.md](VALIDACAO_FW01_FW03.md).

## Firmware MicroPython e bloqueio atual

MicroPython **v1.26.0** é a referência de API desta implementação, ainda candidata para a placa do projeto. A seleção do binário depende do modelo exato da ESP32 na [INT02/#22](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/22). Não existe binário, offset ou pinagem homologado nesta entrega.

Antes de gravar, registrar modelo/variante da placa, URL oficial do binário, versão, SHA-256, chip e offset de gravação. Usar a página de download da **placa exata**; ESP32, S2, S3 e C3 não são intercambiáveis. Registrar também disponibilidade de Encoder/PCNT para a equipe da FW04.

Modelo de comandos (substituir os campos `<...>` pelos dados confirmados; não executar literalmente):

```powershell
Get-FileHash '<firmware.bin>' -Algorithm SHA256
src/firmware/.venv/Scripts/python.exe -m esptool --chip <chip> --port <COMx> erase-flash
src/firmware/.venv/Scripts/python.exe -m esptool --chip <chip> --port <COMx> write-flash <offset-da-placa> '<firmware.bin>'
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> exec "import sys, os; print(sys.implementation); print(os.uname())"
```

`erase-flash` apaga os arquivos existentes na placa: fazer backup antes. Gravar com a alimentação dos motores desconectada. Os comandos acima são um roteiro, não evidência de gravação executada.

## Smoke test na placa, sem acionar motores

Após gravar MicroPython, na raiz do repositório:

```powershell
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> mount src/firmware exec "import smoke_test; smoke_test.executar()"
```

O teste importa o núcleo e usa `MotorFalso`, inclusive quando executado na ESP32. Deve imprimir `SMOKE OK - runtime: micropython ...`. Isso valida importações e execução nessa VM, mas não valida GPIOs ou motores. Guardar a saída completa com modelo da placa, versão e hash do commit.

## Copiar a aplicação após a confirmação de Hardware

1. Copiar `config_exemplo.py` para `config_local.py` e preencher a configuração descrita em [MOTORES.md](MOTORES.md), com revisão da equipe de Hardware.
2. Executar o smoke test acima antes de habilitar qualquer saída real.
3. Copiar somente os arquivos de execução. Os comandos abaixo partem da raiz do repositório e exigem o `config_local.py` preenchido. O pacote é copiado antes dos pontos de entrada:

```powershell
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> fs cp -r src/firmware/robo :
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> fs cp src/firmware/config_local.py :config_local.py
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> fs cp src/firmware/main.py :main.py
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> fs cp src/firmware/boot.py :boot.py
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> reset
src/firmware/.venv/Scripts/mpremote.exe connect <COMx> repl
```

Resultado esperado no boot configurado: mensagem de motores desabilitados. Configuração ausente/incompleta causa erro explícito, sem fallback para pinagem suposta. A aplicação não contém loop de navegação ou partida automática. Para integrar uma tarefa, usar `app.executar(tarefa)` e chamar `enable()` deliberadamente dentro dela; esse invólucro chama `stop()` em `finally`.

## Referências de API

- [MicroPython v1.26.0 — ESP32, GPIO e PWM](https://docs.micropython.org/en/v1.26.0/esp32/quickref.html).
- [mpremote — cópia, mount e execução](https://docs.micropython.org/en/v1.26.0/reference/mpremote.html).
- [Downloads oficiais por placa](https://micropython.org/download/).
