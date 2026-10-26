# Firmware do Micromouse

Comece pelo [guia da ESP32-S3-DevKitC-1 N8R2](CONEXAO_ESP32_S3.md).
O script `board_smoke.py` permite comprovar placa → painel sem configurar motores
ou sensores. A validação física ainda deve ser feita pela equipe.

| Arquivo | Uso |
| --- | --- |
| `telemetry.py` | Contrato JSONL, fila limitada e escrita parcial ([FW09](TELEMETRY.md)) |
| `wifi_telemetry.py` | Cliente STA/TCP e reconexão ([FW10](WIFI.md)) |
| `board_smoke.py` | Teste manual de bancada, 30 s, estado pronto, sem leituras fictícias |
| `demo_telemetry.py` | Demonstração no computador, com dados simulados |
| `wifi_config.example.py` | Modelo de configuração local sem credenciais reais |

Na placa vão somente os módulos usados pelo transporte e a configuração local.
Pydantic, pySerial, NiceGUI e pytest ficam no computador. O
[contrato compartilhado](../../docs/protocolo/README.md) e o
[receptor Python](../telemetria/README.md) completam a integração.

## Flood Fill (FW12)

```bash
cd src/firmware
python test_floodfill.py
```

Para o simulador mms, use `mms_adapter.py` com o `API.py` do projeto
[mms-python](https://github.com/mackorone/mms-python), não versionado aqui.

## Testes no computador

```bash
cd src/firmware
python -m unittest test_telemetry test_wifi_telemetry test_board_smoke -v
```

Não há gravação automática na ESP32 nem um `main.py` de controle dos motores.
