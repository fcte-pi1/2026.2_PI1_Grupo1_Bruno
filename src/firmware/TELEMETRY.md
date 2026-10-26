# FW09 — emissor serial

Para ligar a ESP32-S3-DevKitC-1 N8R2, siga o [guia de bancada](CONEXAO_ESP32_S3.md).
`telemetry.py` é o núcleo portátil: depende só de `json`; não usa Pydantic,
threads, flash ou drivers de motores. O formato completo fica no
[contrato v1](../../docs/protocolo/README.md).

## Uso na aplicação do robô

```python
from telemetry import BoundedWriter, TelemetryPublisher, TicksClock, reading
import time

clock = TicksClock(time.ticks_ms, time.ticks_diff)
publisher = TelemetryPublisher(
    robot_id=robot_id, boot_id=boot_id, run_id=None, maze_id=None,
    clock_ms=clock, sample_hz=10, queue_capacity=8,
)
writer = BoundedWriter(uart.write, uart.deinit)  # UART já configurada sem espera.

# A aplicação cria a corrida; reconexão nunca faz isso.
publisher.run_id = novo_run_id
publisher.maze_id = maze_id
publisher.emit("start", "executando")

# Após o controle, em cada iteração do laço existente:
publisher.record_control_cycle(late=controle_atrasado)
publisher.sample("executando", sensors={"frontal": reading(distancia_cm, "cm")})
publisher.service(writer, byte_budget=256)

# Quando o controle encerrar:
publisher.emit("finish", "concluido")
# Continuar service() na fase parada para escoar a fila.
```

Os identificadores e leituras acima são fornecidos pela aplicação; não é um
programa completo de controle. `boot_id` muda no boot; `run_id` muda por corrida;
`seq` e `t_ms` continuam crescendo em reconexões. `TicksClock` estende o rollover
de `ticks_ms` com `ticks_diff`; consulte-o antes de meio período de ticks.

## Limites que precisam ser mantidos

- `sample` publica no máximo 10 Hz por padrão, sem compensar atrasos com rajadas.
  `emit` retorna falso quando não consegue enfileirar; a aplicação decide como lidar.
- A fila inclui o parcial e tem 8 frames por padrão. Quando cheia, expulsa dados
  não críticos ainda não enviados, preservando a ordem e priorizando
  `start/finish/fault`. Se só houver críticos/parcial, rejeita o novo e conta perda.
- `service` faz uma escrita de até `byte_budget` bytes. Retorno parcial, `None`
  e EAGAIN são tratados; dois frames não se intercalam. Driver bloqueante não
  se torna não bloqueante por estar dentro do wrapper: configure timeout zero.
- Ao perder o link, desconecte o writer; na reconexão crie outro. O parcial
  recomeça inteiro. O receptor limpa o acumulador de linha por conexão.
- Não há ACK por evento: bytes aceitos pelo driver ainda podem se perder.
  RAM e trabalho por chamada são limitados, mas jitter/tempo real exigem bancada.
- Os contadores `control_cycles`, `control_late_cycles`, `samples_dropped`,
  `events_dropped`, `queue_high_water` são snapshots cumulativos por boot.

Use UART de dados separada da REPL/debug: no teste da S3, UART1 TX17/RX18,
115200 8N1, timeout=0 e timeout_char=0. Confira GPIOs livres na montagem final.
Na placa cabem no máximo 8 × 4097 bytes de frames, mais overhead/temporários.
A 115200 8N1 há cerca de 11520 bytes/s: payloads máximos a 10 Hz excedem a banda;
ajuste payload/taxa. O teste de bancada envia frames pequenos, sem sensores.

## Testes sem placa

```bash
python src/firmware/test_telemetry.py
python src/firmware/demo_telemetry.py --cycles 100 > frames.jsonl
PYTHONPATH=src/telemetria python src/firmware/test_telemetry.py
```

A demonstração roda no computador, com relógio e leituras simulados; stdout
contém JSONL e stderr contém diagnóstico. A validação cruzada com Pydantic
usa o ambiente do receptor. Fakes cobrem fila cheia, consumidor lento/ausente,
parciais, perdas, contrato e rollover. Não medem UART física nem atraso real
do controle. O roteiro de bancada está no [guia da placa](CONEXAO_ESP32_S3.md).

Referência: [UART no MicroPython 1.26](https://docs.micropython.org/en/v1.26.0/library/machine.UART.html).
