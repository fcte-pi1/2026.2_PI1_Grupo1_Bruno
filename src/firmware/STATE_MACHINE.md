# Máquina de estados do firmware (FW08)

| Campo | Valor |
|---|---|
| Equipe | Firmware |
| Prioridade | P0 |
| Prazo sugerido | 25/10/2026 |
| Dependências | FW01, FW03, FW02 |
| Código | `state_machine.py`, `button.py` (em `src/firmware`) |
| Testes | `test_state_machine.py`, `test_button.py` (em `src/firmware`) |

## 1. Objetivo

Definir os estados IDLE, READY, RUNNING, STOPPED, FINISHED e FAULT, com transições explícitas. A segurança e o controle local não dependem do aplicativo de telemetria.

## 2. Estados

| Estado | Descrição | Motores |
|---|---|---|
| IDLE | Boot concluído. Executa a autoverificação a cada ciclo. | Parados |
| READY | Autoverificação aprovada. Aguarda o acionamento de início. | Parados |
| RUNNING | Corrida em andamento. Único estado em que a camada de movimento pode aplicar PWM. | Habilitados |
| STOPPED | Parada comandada (botão, comando remoto ou timeout do comando). | Parados |
| FINISHED | Objetivo alcançado. | Parados |
| FAULT | Falha detectada. Só sai por reconhecimento explícito. | Parados |

A camada de movimento só pode aplicar PWM aos motores quando `fsm.allows_motion` for verdadeiro.

## 3. Transições

| Origem | Evento | Destino | Observação |
|---|---|---|---|
| IDLE | Autoverificação aprovada | READY | Automática, a cada ciclo |
| READY | Início (botão ou comando remoto) | RUNNING | Ação explícita |
| RUNNING | Parada (botão, comando remoto ou timeout do comando) | STOPPED | Motores parados antes da mudança de estado |
| RUNNING | Objetivo alcançado | FINISHED | Motores parados |
| STOPPED | Rearmar (botão) | READY | Ação explícita |
| FINISHED | Rearmar (botão) | READY | Ação explícita |
| Qualquer, exceto FAULT | Falha | FAULT | Motores parados antes da mudança de estado |
| FAULT | Reconhecimento da falha (botão) | IDLE | Ação explícita. Em seguida a autoverificação leva a READY |

Um novo início depois de STOPPED, FINISHED ou FAULT exige acionamentos explícitos e sucessivos: reconhecer ou rearmar, e depois iniciar. Eventos que não constam na tabela para o estado atual são ignorados.

## 4. Causas de falha e parada

| Causa | Tipo | Condição |
|---|---|---|
| BOOT | Falha | `motors.stop()` falha no boot |
| WDT_RESET | Falha | O boot ocorreu por reset do watchdog |
| EXCEPTION | Falha | Exceção em `guarded()` ou na autoverificação |
| FRONT_CRITICAL | Falha | Distância frontal menor que `front_critical_mm` em RUNNING |
| SENSOR_INVALID | Falha | Sem leitura frontal válida por mais de `sensor_timeout_ms` em RUNNING |
| STALL | Falha | Movimento comandado sem variação do encoder por mais de `stall_ms` |
| RUN_TIMEOUT | Falha | RUNNING por mais de `run_timeout_ms` |
| BUTTON | Parada | Botão acionado em RUNNING |
| REMOTE | Parada | Comando remoto de parada |
| CMD_TIMEOUT | Parada | Sem comando por mais de `cmd_timeout_ms` em modo remoto |

A parada definida é a chamada a `motors.stop()`, que deve ser idempotente e levar o hardware a PWM zero com a ponte H no modo de parada.

## 5. Botão

O botão usa interrupção com debounce por janela de bloqueio (`debounce_ms`, padrão 50 ms). A rotina de interrupção apenas registra um flag. Ela não realiza E/S de rede, `print` ou alocação. O loop principal lê o flag com `consume()` e chama `fsm.on_button()`.

| Estado atual | Efeito do acionamento do botão |
|---|---|
| IDLE | Ignorado |
| READY | Início (RUNNING) |
| RUNNING | Parada (STOPPED) |
| STOPPED ou FINISHED | Rearmar (READY) |
| FAULT | Reconhecer a falha (IDLE) |

O GPIO do botão ainda não está definido (ver `INT02.md`, seção 1.2). Para teste de bancada pode-se usar o botão BOOT da placa (GPIO 0), sem apertá-lo durante o reset.

## 6. Watchdog

O watchdog de hardware (`machine.WDT`) só é alimentado quando `fsm.health_ok()` retorna verdadeiro, isto é, quando o intervalo entre dois ciclos consecutivos de `update()` não excedeu `loop_max_ms`. Se o loop travar, o watchdog não é alimentado e a placa reinicia.

Após o reinício, o construtor da máquina de estados chama `motors.stop()` antes de qualquer outra ação. Quando a causa do reset é o watchdog, o estado inicial é FAULT (causa WDT_RESET), e portanto o reinício não reativa os motores.

## 7. Telemetria e comando remoto

| Modo | Comportamento |
|---|---|
| LOCAL (padrão) | A máquina de estados não consulta o estado da telemetria. A perda de telemetria não altera a operação. Comandos remotos são ignorados. |
| REMOTE | Comandos remotos são aceitos e renovam o watchdog de comando. Se não houver comando por mais de `cmd_timeout_ms`, o movimento é interrompido (STOPPED, causa CMD_TIMEOUT). |

Falhas na função de notificação de transições (`on_transition`) são capturadas e não interferem na lógica de segurança.

## 8. Parâmetros

Os valores abaixo são provisórios e devem ser calibrados no robô montado.

| Parâmetro | Valor inicial | Descrição |
|---|---|---|
| `front_critical_mm` | 40 | Distância frontal crítica |
| `sensor_timeout_ms` | 200 | Tempo máximo sem leitura frontal válida |
| `stall_ms` | 400 | Tempo máximo sem variação do encoder com movimento comandado |
| `run_timeout_ms` | 120000 | Duração máxima de uma corrida |
| `cmd_timeout_ms` | 500 | Tempo máximo sem comando em modo remoto |
| `loop_max_ms` | 100 | Período máximo do loop para alimentar o watchdog |
| `debounce_ms` | 50 | Janela de debounce do botão |

## 9. Integração

Interfaces mínimas esperadas das dependências (FW01, FW02 e FW03):

- `motors.stop()`: obrigatório e idempotente.
- Leitura frontal em milímetros (ou `None` se inválida).
- Indicação de movimento comandado e de variação do encoder.

Exemplo de loop principal:

```python
import time
import machine
from machine import WDT
from state_machine import MouseFSM
from button import Button

btn = Button(BTN_GPIO)
fsm = MouseFSM(motors, time.ticks_ms, time.ticks_us,
               self_check=self_check,
               reset_was_wdt=(machine.reset_cause() == machine.WDT_RESET))
wdt = WDT(timeout=2000)


def step():
    if btn.consume():
        fsm.on_button()
    front_mm, commanded, moved = ler_entradas()
    fsm.update(front_mm, commanded, moved)
    if fsm.allows_motion:
        controlar_movimento()


while True:
    fsm.guarded(step)
    if fsm.health_ok():
        wdt.feed()
    time.sleep_ms(10)
```

## 10. Execução dos testes

Na raiz do repositório, com Python 3 no PC (os testes usam mocks e não dependem da placa):

```
python -m unittest discover -s src/firmware -p "test_state_machine.py" -v
python -m unittest discover -s src/firmware -p "test_button.py" -v
```

`test_state_machine.py` (26 testes) cobre: boot e autoverificação, todas as transições da seção 3, cada causa de falha da seção 4, exceção no loop, reset por watchdog, saúde do loop, perda de telemetria em modo local, watchdog de comando em modo remoto e registro da latência de parada.

`test_button.py` (8 testes) simula os módulos `machine` e `time` e cobre: configuração do pino, um evento por acionamento, repique dentro da janela de debounce, acionamentos separados e a rotina de interrupção limitada a marcar o flag.

## 11. Evidências e latência de parada

| Item | Simulado (mocks no PC) | Bancada | Físico |
|---|---|---|---|
| Transições e falhas | 26 testes aprovados | Pendente | Pendente |
| Botão com interrupção e debounce | 8 testes aprovados (`machine` simulado) | Pendente (depende da placa) | Pendente |
| Watchdog e reboot sem reativar motores | Lógica testada | Pendente | Pendente |
| Latência de parada | Registro validado com mock (ver abaixo) | Pendente | Pendente |

**Latência de parada.** A máquina de estados registra em `last_stop_latency_us` o tempo entre a detecção da condição e o retorno de `motors.stop()`. No teste simulado, o mock de motores tem custo fixo de 120 µs, e o valor registrado foi 120 µs. Esse número valida apenas o mecanismo de medição e não representa o hardware.

Para a medição real, executar na placa:

```python
import time
t0 = time.ticks_us()
motors.stop()
print(time.ticks_diff(time.ticks_us(), t0))
```

Na bancada, o tempo entre a condição de falha e o PWM em zero deve ser medido com analisador lógico ou osciloscópio. O tempo total até a parada inclui também o período do loop (detecção em até um ciclo). Os resultados devem ser registrados na tabela acima.

## 12. Pendências

| Item | Responsável | Observação |
|---|---|---|
| GPIO e ligação do botão (pull-up ou pull-down) | A definir | Depende do INT02 |
| Modo de parada da ponte H ZS-H2 (freio ou roda livre) | A definir | Conferir no datasheet e implementar em `motors.stop()` |
| Interfaces reais de FW01, FW02 e FW03 | A definir | Adaptar o exemplo da seção 9 |
| Calibração dos limiares da seção 8 | A definir | Requer o robô montado |
| Validação em bancada e física | A definir | Não marcar como concluída enquanto o hardware estiver indisponível |
