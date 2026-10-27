# Validação da telemetria

Testes executados em 26/10/2026, no Linux com CPython 3.14.8 e as dependências
de `src/telemetria/requirements-dev.txt`.

| Verificação | Resultado |
| --- | --- |
| Telemetria, painel e integração TCP | 152 testes passaram |
| Firmware | 75 testes passaram, sem skips |
| Ruff e formatação dos arquivos revisados | Passou |
| `git diff --check` | Passou |

Os testes cobrem v1/v2, tipos e campos inválidos, coordenadas, orientações,
rotas, limite de bytes, filas, perda de conexão, captura e reprodução.
A integração conecta o emissor do firmware ao receptor por TCP localhost,
com escritas parciais, mantendo versão, sequência e corrida. A serial usa
`loop://` e pseudo-terminal POSIX; a interface usa `nicegui.testing.User`.

Os resultados são de testes no computador, sem ensaio físico na ESP32.

## Arquivos e issues

| Issue | Arquivos |
| --- | --- |
| [#23 — INT03](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/23) | Modelos, schemas e exemplos v1/v2 em `docs/protocolo` |
| [#17 — TEL01](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/17) | Receptor, gerador, captura e reprodução em `src/telemetria` |
| [#11 — FW09](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/11) | Emissor e fila em `src/firmware/telemetry.py` |
| [#12 — FW10](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/12) | Conexão e reconexão em `src/firmware/wifi_telemetry.py` |

## Executar

Os testes TCP e NiceGUI precisam de sockets localhost liberados.
Com o ambiente Python ativado, a partir da raiz:

```bash
python docs/protocolo/exportar_schema.py
cd src/telemetria
pytest -q
ruff check .
ruff format --check .
cd ../..
PYTHONPATH=src/telemetria python -m unittest discover -s src/firmware -p 'test_*.py' -q
```

Para os arquivos Python de telemetria em `src/firmware` e o exportador, use
Ruff com `--isolated --line-length 110` e lint `--select E,F,I`.
O teste `test_contrato.py` confere o schema v1; `test_contrato_v2.py` confere
v2 e aplica os mesmos exemplos ao emissor e ao receptor.

O teste manual da placa está no [guia de conexão da ESP32-S3](../../src/firmware/CONEXAO_ESP32_S3.md).
