# Validação FW01 e FW03 — 26/10/2026

## Resultado executado

Ambiente: Windows, CPython 3.14.0, mpremote 1.26.1, esptool 5.0.2. Ferramentas instaladas em `src/firmware/.venv`, fora do versionamento. Base de desenvolvimento: `dev` no commit `bdf480e`.

Na raiz do repositório:

```text
python -m unittest discover -s src/firmware -p 'test_*.py'
Ran 62 tests
OK

python src/firmware/smoke_test.py
SMOKE OK - runtime: cpython 3.14.0 ...
Origem: simulada. Nenhum GPIO ou motor fisico foi acionado.

src/firmware/.venv/Scripts/mpremote.exe --version
mpremote 1.26.1

src/firmware/.venv/Scripts/python.exe -m esptool version
esptool v5.0.2
5.0.2
```

Foram adicionados 22 testes (2 de aplicação, 11 de controle dos motores, 6 do adaptador PWM e 3 de inicialização). Os outros 40 testes já existentes também passaram. Casos parametrizados dentro de um método não são contados como testes adicionais nesse total.

Cobertura relevante: boot sem acionamento, saída normal/erro/Ctrl-C, habilitação explícita, duty independente e saturado, rampa, reversão com passagem por zero e pausa, parada imediata, rejeição de NaN/infinito e ciclos atrasados, falha de escrita, validação antes de GPIOs e tentativa de desabilitar a outra roda mesmo quando um PWM falha.

## O que não foi validado

- Nenhuma ESP32 identificada nesta sessão. A listagem `mpremote connect list` exibiu somente `COM1`, sem número de série e com VID/PID `0000:0000`; essa porta não foi tratada como placa do projeto nem recebeu comandos de gravação.
- `micropython` não foi encontrado no PATH. O smoke test foi executado no **CPython**, não na VM MicroPython; compatibilidade real permanece pendente.
- Modelo de placa, driver, GPIOs, frequência PWM real, deadband física, polaridade, freio/roda livre e proteção elétrica ainda dependem da INT02/#22. O usuário confirmou não possuir esses dados nesta etapa.
- O teste de `PontePWM` usa `MachineFake`, com GPIOs/tabela sintéticos. Não comprova temporização elétrica ou resposta mecânica.
- Não houve gravação, teste em bancada, calibração, teste sob carga, watchdog físico ou deslocamento do carrinho.

## Estado da entrega

**#3:** estrutura, configuração externa, boot desabilitado, ferramentas e roteiro de gravação implementados; execução em MicroPython/ESP32 e definição do binário exato pendentes.

**#5:** controle portátil e adaptador condicional testados em simulação; confirmação/adaptação ao driver real e validação em bancada pendentes. Os comentários `TODO(INT02/#22)` indicam os pontos de configuração que não devem ser preenchidos por suposição.

As issues não devem ser fechadas como integralmente validadas com base nestes testes. Roteiros para a próxima etapa: [AMBIENTE.md](AMBIENTE.md) e [MOTORES.md](MOTORES.md).
