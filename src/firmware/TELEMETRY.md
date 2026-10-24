# FW09 — telemetria serial limitada

`telemetry.py` funciona em CPython e MicroPython: importa somente `json`; não
depende de Pydantic, drivers ou threads. O adaptador UART opcional fica em
`demo_telemetry.py`. O caminho de controle chama a telemetria depois dos atuadores,
fora de interrupções. A implementação não escreve amostras em flash.

## Executar sem placa

Na raiz do repositório:

```sh
python src/firmware/test_telemetry.py
python src/firmware/demo_telemetry.py --cycles 100 > frames.jsonl
```

O demo avança um relógio **simulado**, com 100 ciclos de controle a 100 Hz e
10 amostras por segundo a 10 Hz, além de `start` e `finish`. Todas as leituras
declaram `source=simulated`. JSONL sai em stdout; resumo de contadores sai em
stderr, separado dos dados. A saída do host em arquivo pode bloquear: esse
adaptador é exclusivo da demonstração CPython, não do controle embarcado.

Para também validar todos os frames do demo pelo modelo Pydantic do receptor,
use o ambiente com as dependências de `src/telemetria` instaladas:

```sh
PYTHONPATH=src/telemetria python src/firmware/test_telemetry.py
```

Sem essas dependências, somente essa verificação cruzada é pulada. Os testes
independentes exercitam consumidor lento/ausente, filas críticas cheias, escrita
parcial, `None`, EAGAIN, queda no meio de frame, reconexão, limite em bytes UTF-8,
sequência, amostragem, mapa e rollover do relógio.

## API e contrato

```python
from telemetry import TelemetryPublisher, BoundedWriter, reading

publisher = TelemetryPublisher(
    robot_id="bruno-1", boot_id=boot_id, run_id=None, maze_id=None,
    clock_ms=monotonic_ms, sample_hz=10, queue_capacity=8,
)
# A aplicação decide quando começa uma corrida e quais são seus identificadores.
publisher.run_id = run_id
publisher.maze_id = maze_id
publisher.emit("start", "running")

# Executar depois de cada ciclo de controle (por exemplo, a cada 10 ms).
publisher.record_control_cycle(late=control_exceeded_deadline)
publisher.sample("running", sensors={"front": reading(front_cm, "cm")})
publisher.service(writer, byte_budget=128)

# Quando o controle encerrar a corrida:
publisher.emit("finish", "stopped")
```

`emit(event, state, **payload)` retorna se o frame entrou na fila. `sample`
retorna falso também quando ainda não chegou o período de 100 ms; isso é
amostragem deliberada, sem incrementar perdas. Após atrasos, emite no máximo
uma amostra atual, sem rajada para compensar períodos passados. `emit("sample",
...)` ignora o limitador e só deve ser usado quando a aplicação já controla a
taxa. `service` faz **uma** chamada ao driver por invocação e oferece no máximo
`byte_budget` bytes, incluindo LF. Retorna os bytes aceitos pelo driver.

Cada frame tem `schema_version=1`, `robot_id`, `boot_id`, `run_id`, `maze_id`,
`seq`, `t_ms`, `event` e `state`. Os eventos são `start`, `sample`, `map_update`,
`finish` e `fault`. `start`/`finish` exigem `run_id`; a aplicação pode manter
`run_id=null` nas amostras anteriores à corrida. `fault` exige
`fault={"code": "...", "message": "..."}`; esse objeto só aparece em `fault`.
`map_update` exige `maze_id` e o objeto `map` do contrato v1 (dimensões 1–32,
fonte explícita, até 32 células únicas, máscaras N/E/S/W 1/2/4/8 e paredes
contidas nos bits conhecidos). Mapa só aparece em `map_update`.

Uma leitura contém exatamente `{value, unit, source, valid}`; `value=null`
representa indisponibilidade e `valid=false` indica leitura inválida. Valores
NaN/infinito são rejeitados. Rodas e erro exigem `mm/s`, sensores exigem `cm` e
bateria exige `V`; a aplicação faz a conversão antes de publicar. O máximo é
oito sensores com nomes de 1 a 24 caracteres. Há
exemplos de todos esses campos no demo.

O JSON é codificado em UTF-8, com no máximo **4096 bytes de payload**, seguidos
de um LF adicional (`b"\n"`). O limite é medido depois da serialização: caracteres
acentuados e escapes contam seus bytes reais. Frames maiores são descartados,
contados e retornam falso. Campos inválidos levantam `ValueError` antes de
enfileirar; não envie logs, strings arbitrárias ou objetos de aplicação.

Forneça um `boot_id` novo a cada inicialização, por exemplo aleatoriedade de
hardware suficiente codificada em hexadecimal, e mantenha o mesmo publisher
por todo o boot. Identidade física/chip sozinha não distingue boots. Não altere
`robot_id`/`boot_id` durante o boot. `run_id` é criado pela aplicação a cada
corrida, nunca pelo transporte. `seq` começa em zero, cresce por boot e inclui
tentativas perdidas por saturação/tamanho. Saltos permitem detectar perdas;
não são motivo para inventar novas corridas. Frames aceitos saem em ordem FIFO.

O relógio injetado deve fornecer milissegundos inteiros monotônicos desde o
boot, sem horário civil. Em MicroPython, estenda `ticks_ms()` com `TicksClock`:

```python
import time
from telemetry import TicksClock

monotonic_ms = TicksClock(time.ticks_ms, time.ticks_diff)
```

O adaptador deve ser chamado pelo menos uma vez em cada meia volta do período
de ticks, mesmo offline; uma pausa maior torna o delta ambíguo. Instancie-o no
início do boot. Reconexão preserva relógio, sequência e identificadores.

## Saturação e reconexão

A capacidade inclui o frame parcialmente transmitido. Nunca se intercala o
início de outra linha no meio dele. Quando cheia, a fila descarta o mais antigo
frame não crítico ainda não iniciado para aceitar dados atuais. Uma amostra só
pode substituir outra amostra. Eventos `start`/`finish`/`fault` podem substituir
amostra ou mapa; não expulsam eventos críticos já aceitos.

**Se todos os slots forem críticos ou estiverem presos em transmissão parcial,
o novo frame é rejeitado e contado.** Não existe promessa de retenção infinita.
A aplicação deve observar o retorno de `emit` e os contadores, dimensionar a
fila e conduzir paradas por seu próprio controle, independentemente da entrega
de telemetria. Não espere espaço no caminho de controle. A fila padrão usa no
máximo 8 × 4097 bytes de dados codificados mais overhead de objetos; a construção
de cada JSON usa memória temporária adicional. Forneça snapshots pequenos e
limitados; o núcleo não é apropriado para execução em ISR nem garante tempo real
duro ou ausência de pausas do coletor de lixo.

`BoundedWriter(write, close=None)` aceita uma função de escrita **já configurada
sem bloqueio**. Retornos parciais avançam o cursor; `None`, zero, EAGAIN e
EWOULDBLOCK não avançam. Outros `OSError` desconectam o stream. O wrapper não
consegue limitar a duração de um driver bloqueante. O orçamento em bytes limita
trabalho oferecido, não constitui garantia de deadline físico.

Na queda, marque `writer.disconnect()` inclusive quando a perda foi detectada
fora de `write`; crie **outro** `BoundedWriter` ao reconectar. O próximo `service`
reinicia o frame atual desde `{`, nunca de um sufixo. O receptor precisa limpar
seu buffer parcial na abertura de cada conexão. Um frame inteiramente aceito
pelo driver já sai da fila: não há ACK da aplicação, garantia de entrega ou
retransmissão de frames concluídos. Uma reconexão pode exigir deduplicação por
`(robot_id, boot_id, seq)` no receptor. O transporte não emite `start`.

## Contadores

`stats()` retorna uma cópia; `include_stats=True` inclui um snapshot opcional
em `telemetry_stats`, com exatamente estes inteiros não negativos:

| Campo | Significado |
| --- | --- |
| `control_cycles` | Ciclos registrados pela aplicação. |
| `control_late_cycles` | Ciclos que a aplicação marcou como atrasados. |
| `samples_dropped` | Amostras descartadas por limite, substituição ou tamanho. |
| `events_dropped` | Outros eventos descartados pelas mesmas causas. |
| `queue_high_water` | Maior ocupação da fila, incluindo parcial. |

Os contadores pertencem ao boot e saturam em `2**53-1`, limite também aplicado
a sequência e tempo. O snapshot descreve o instante de criação do
frame; suas próprias alterações de fila aparecem nos frames posteriores.
O núcleo não mede automaticamente o deadline do controle: o chamador compara
seu tempo de execução/período e passa `late=True`.

## UART e validação de bancada pendente

No ESP, `demo_telemetry.uart_writer(uart_id, tx, rx)` instancia
`machine.UART(..., timeout=0, timeout_char=0, txbuf=512)` a 115200 baud, 8N1.
Use UART de dados separada da REPL/boot/debug; nunca faça `print` de logs nessa
UART. Se a placa emitir mensagens de boot na UART escolhida, mude a UART/pinos
ou separe fisicamente o canal. Não conecte TTL de 3,3 V diretamente a RS-232;
confira GND comum e adaptação elétrica do hardware do projeto.

Pinos, UART disponível, buffers e semântica temporal do driver dependem do port.
Verifique se o firmware da placa aceita os argumentos e confirme com medição
que a chamada não segura o loop quando o buffer TX enche. `timeout=0` e
`timeout_char=0` devem ser explícitos; não use `flush()`/`txdone()` em espera
ativa. A 115200 baud, 8N1 oferece cerca de 11520 bytes/s: dez frames máximos
de 4097 bytes/s exigiriam 40970 bytes/s e saturariam. Ajuste payload/taxa/baud
com dados reais; a fila limitada só torna a perda observável.

Para bancada, execute o loop de controle a 100 Hz, transporte a 10 Hz e capture
JSONL pelo receptor serial do projeto; interrompa a leitura e desconecte/reconecte
o cabo durante uma linha. Confira ciclos/atrasos, saltos de sequência, limites
da fila e ausência de corrupção na próxima conexão. Essa é uma instrução de
validação: **não há evidência de placa, UART física, sensores ou tempo real**
nos testes simulados deste commit.

APIs públicas consultadas: [UART](https://docs.micropython.org/en/latest/library/machine.UART.html),
[ticks_ms/ticks_diff](https://docs.micropython.org/en/latest/library/time.html),
[JSON](https://docs.micropython.org/en/latest/library/json.html). A documentação
`latest` pode descrever recursos ainda não lançados; confirme na versão instalada.
