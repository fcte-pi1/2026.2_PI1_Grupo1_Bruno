# FW03 — Controle dos motores

Entrega referente à [issue #5](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/5). O código e os testes simulados estão disponíveis; a implementação específica do driver real e a validação física dependem da INT02/#22.

## Interface portátil

```python
from robo.controle.motores import Motores
from robo.drivers.falso import MotorFalso

motores = Motores(MotorFalso())  # SIMULAÇÃO
motores.enable()                # começa com saída zero
try:
    motores.set_output(0.3, -0.2)  # esquerda e direita, duty assinado
    motores.update(20)            # exemplo: intervalo medido de 20 ms
finally:
    motores.stop()
```

`set_output(left, right)` recebe duty normalizado, limita amplitude ao `max_duty` e atualiza alvos. `update(dt_ms)` aplica a rampa por segundo e escreve as duas saídas. No MicroPython medir o intervalo com `time.ticks_diff(agora, anterior)`, usando `ticks_ms()`, em vez de presumir que o loop sempre dura 20 ms.

Na reversão, a roda desacelera até zero, permanece nesse estado por `pausa_reversao_ms` e só depois acelera no sentido oposto. Cada roda tem seu próprio estado. `stop()` ignora a rampa e desabilita imediatamente o driver; descarta os alvos e exige novo `enable()`. A pausa de reversão não pode ser burlada por `stop()/enable()`.

Valores NaN/infinito, tipos inválidos, atraso acima de `max_dt_ms` e falhas de escrita causam tentativa de desabilitação dos dois motores. A detecção de atraso ocorre na próxima chamada a `update`; **não substitui watchdog** se o programa travar ou nunca voltar ao loop (integração FW02). Falhas elétricas ou falha do próprio GPIO não podem ser corrigidas por software.

`deadband` zera comandos pequenos; não aplica impulso mínimo nem compensa automaticamente atrito. A rampa pode atravessar valores abaixo da deadband para evitar saltos. Os valores padrão são de simulação, não calibrados. Duty não equivale a velocidade: malha PI/PID e encoders pertencem às issues #7 e #6.

## Adaptador de placa e pendências explícitas

`PontePWM` é condicional a uma interface com **IN1 + IN2 + PWM para cada roda e enable comum**. Não é uma identificação do driver do projeto. O código tem comentários `TODO(INT02/#22)`; se o driver real tiver outra interface, será necessário outro adaptador com os métodos `enable()`, `write(left, right)` e `disable()`.

Não há GPIOs de produção preenchidos. A configuração `HARDWARE` começa como `None` e bloqueia a inicialização física. A tabela abaixo descreve os campos para substituir esse valor por um dicionário em `config_local.py`:

| Campo | Preenchimento após confirmação |
| --- | --- |
| `confirmado` | `True` somente após revisão da equipe |
| `placa`, `driver` | Modelo exato da placa e da ponte |
| `interface` | `"2in_pwm_enable"` somente se a interface corresponder |
| `fonte_tabela` | Datasheet, revisão e seção da tabela verdade |
| `comportamento_desabilitado` | Descrever freio, roda livre ou outro estado conforme datasheet e ligação |
| `enable_gpio`, `enable_ativo` | GPIO e nível ativo (0 ou 1) do enable comum |
| `esquerda`, `direita` | Tuplas `(gpio_in1, gpio_in2, gpio_pwm)` |
| `gpios_saida_aprovados` | Lista de GPIOs revisados: saída suportada, boot/reservas e demais periféricos |
| `pwm_hz` | Frequência compatível com driver, PWM da placa e motores |
| `tabela` | Dicionário com `frente`, `re` e `zero`, cada um com tupla `(in1, in2)` |

Os GPIOs e tabelas em `test_ponte_pwm.py` são apenas dados sintéticos para um `machine` falso. Não copiar para a placa. O adaptador valida a configuração antes de importar `machine` e inicializa enable no nível inativo antes dos PWMs, que começam em zero. O teste não verifica se a lista de GPIOs aprovada está eletricamente correta: essa revisão é responsabilidade da INT02.

O PWM usa `duty_u16` entre 0 e 65535. A implementação zera PWM antes de escrever os pinos de sentido. `disable()` desativa enable e tenta zerar os dois PWMs mesmo se uma das operações falhar.

### Freio, roda livre e reset

Não há comando de frenagem ativa implementado. `stop()` significa enable inativo e PWM zero; **não é possível afirmar se isso produz freio ou roda livre sem o driver e a ligação reais**. O estado `zero` da tabela precisa ser definido pelo datasheet considerando PWM zero e enable ativo. Não assumir que IN1=IN2=0 produz sempre o mesmo efeito.

Antes de Python executar, os pinos podem estar em alta impedância. Hardware deve garantir o nível inativo do enable durante energização, reset, bootloader e queda de tensão, por meio da ligação apropriada. O código de boot não substitui essa condição elétrica.

## Roteiro de bancada pendente

1. Confirmar os campos acima, alimentação, terra comum, níveis lógicos e estado inativo durante reset.
2. Com potência dos motores desligada, medir enable, sentido, frequência e duty. Conferir o boot sem pulsos de acionamento.
3. Com rodas suspensas, testar uma roda por vez, começando com duty e rampa baixos aprovados pela equipe. Registrar polaridade, deadband medida, frequência, corrente e limite adotado.
4. Testar parada, erro, Ctrl-C e reset; registrar separadamente o comportamento mecânico (freio/roda livre).
5. Medir passagem por zero e tempo de pausa em reversões. Só depois integrar encoders, PI/PID e testes no chão.

Até essa validação, não marcar a issue como totalmente concluída nem tratar os valores de simulação como parâmetros de bancada.
