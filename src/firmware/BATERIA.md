# FW14 - Medição da bateria

Issue: [#16](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/16). Responsável: Guilherme Negreiros Pereira.

## Escopo e situação do hardware

Esta entrega prepara a conversão de tensão e a política local de baixa tensão em `bateria.py`. O repositório ainda não confirma bateria, circuito divisor, GPIO, atenuação, faixa útil do ADC ou calibração. Por isso não há configuração física padrão nem inicialização de `machine.ADC`.

| Informação necessária | Situação |
| --- | --- |
| Química e número de células em série | Pendente com Energia (INT02) |
| Tensão máxima e limites de operação do pacote | Pendente com Energia |
| Resistores medidos do divisor | Pendente com Hardware/Energia |
| Placa, GPIO, atenuação e faixa útil do ADC | Pendente com Hardware (FW06) |
| Ganho e offset comparados com multímetro | Pendente de bancada |
| Limiares de parada e retomada | Pendente com Energia |

Não usar os valores dos testes como configuração do robô. O núcleo é importável no CPython, sem `machine` ou dependências externas. Execução no MicroPython e captura real do ADC ainda precisam de validação.

## Interface de aquisição

`MonitorBateria(configuracao, ler_uv, origem)` recebe uma função síncrona que retorna a tensão no pino do ADC em **microvolts**, ou `None` quando não há leitura. Sem função ou sem configuração, retorna `indisponivel` e não acessa hardware. `origem` aceita `measured` e `simulated`; não rotula tensão calculada a partir de sensor como percentual estimado.

O adaptador da FW06 deve converter a API concreta da placa para esse contrato, com aquisição limitada em tempo. Não passar diretamente contagens brutas de `read()`/`read_u16()` como se fossem microvolts. Calibrar a conversão conforme a placa e o firmware confirmados. Um ADC bloqueado não pode ser interrompido por este núcleo síncrono; timeout e detecção de leitura antiga são responsabilidades do adaptador/agendador.

`OSError` de aquisição vira `erro_sensor`. Outros erros de programação propagam para o tratamento de falhas da aplicação. Uma entrada não numérica, não finita, nula/negativa, saturada ou uma tensão fora do máximo configurado vira `incoerente`. O valor rejeitado não é reaproveitado na telemetria.

## Divisor e calibração

R superior liga bateria ao ponto de medição; R inferior liga esse ponto ao GND:

- `fator_divisor = 1 + R_superior / R_inferior`.
- `tensao_bateria = adc_uv * fator_divisor * ganho / 1_000_000 + offset_v`.

Os resistores são informados em ohms. Ganho e offset corrigem a tensão do pacote; os padrões são 1 e 0. A faixa útil configurada em `adc_max_uv` precisa representar o ADC real e sua atenuação, não uma suposição de que toda placa mede até 3,3 V. Leituras em zero ou no teto são rejeitadas porque não permitem distinguir uma medição útil de ausência/saturação.

A configuração exige resistores, limites e ganho positivos e finitos, além de `baixa < retomada <= maxima`. Verifica que a escala calibrada cobre a tensão máxima com margem numérica. Essa verificação não substitui o dimensionamento elétrico: Hardware deve conferir a máxima tensão física no pino, tolerâncias, impedância, filtragem e proteção antes de conectar o circuito.

## Resultado e política de parada

`ler()` retorna `LeituraBateria`, com `tensao_v`, `origem`, `valida`, `estado` e `solicitar_parada`.

| Estado | Valor e validade | Decisão local |
| --- | --- | --- |
| `normal` | Tensão válida | Não solicita parada |
| `baixa` | Tensão válida, abaixo ou no limiar de baixa | Solicita parada |
| `indisponivel` | `None`, inválida | Solicita parada |
| `erro_sensor` | `None`, inválida | Solicita parada |
| `incoerente` | `None`, inválida | Solicita parada |

Depois de entrar em `baixa`, só sai desse estado com uma leitura válida maior ou igual ao limiar de retomada. Uma falha de leitura não apaga esse bloqueio. Antes de uma baixa detectada, uma leitura entre os dois limiares é normal. A histerese evita alternância no limite; não há média que esconda uma queda de tensão.

O módulo não escreve em motores. A FW08 deve consumir `solicitar_parada`, desabilitar o movimento e registrar o motivo. Voltar a `normal` não é autorização para reiniciar uma corrida automaticamente; o início explícito continua sendo decisão da máquina de estados. Sem esse consumo pela FW08, a parada física ainda não está integrada.

## Telemetria e grandezas não disponíveis

`leitura.telemetria()` devolve apenas o conteúdo de `battery_voltage`, compatível com o modelo atual de `src/telemetria/telemetria/modelos.py`:

```json
{"value": 7.5, "unit": "V", "source": "simulated", "valid": true}
```

Sem leitura:

```json
{"value": null, "unit": "V", "source": "measured", "valid": false}
```

A função não monta o frame completo e não envia pela serial. O emissor da FW09 acrescenta esse campo ao frame; eventos de falha e estado da aplicação dependem do contrato INT03.

| Grandeza | Suporte nesta entrega |
| --- | --- |
| Tensão do pacote (V) | Disponível com divisor/ADC configurados |
| Corrente (A) | Indisponível: sensor de corrente não confirmado |
| Potência (W) | Indisponível: requer corrente e tensão medidas |
| Energia consumida (Wh) | Indisponível: requer integração temporal da potência |
| Carga (%) e autonomia restante | Indisponíveis: sem modelo e calibração |

Essas grandezas não são calculadas nem adicionadas como campos desconhecidos ao contrato atual. Se uma interface futura pedir esses valores, usar `null`/indisponível, nunca zero. Qualquer percentual futuro deverá ter origem `estimated` e documentar química, curva de descarga e efeito da carga. Dividir tensão por tensão máxima não mede carga.

## Exemplo reproduzível sem hardware

Na pasta `src/firmware`, executar no Python:

```python
from bateria import ConfiguracaoBateria, MonitorBateria

# Valores fictícios, apenas para demonstrar a interface.
config = ConfiguracaoBateria(
    r_superior_ohm=20000,
    r_inferior_ohm=10000,
    adc_max_uv=3_000_000,
    tensao_max_v=8.4,
    tensao_baixa_v=6.3,
    tensao_retomada_v=6.6,
)
valores = iter((2_500_000, 2_000_000, None, 2_150_000, 2_250_000))
monitor = MonitorBateria(config, lambda: next(valores), origem="simulated")
for _ in range(5):
    leitura = monitor.ler()
    print(leitura.estado, leitura.solicitar_parada, leitura.telemetria())
```

Estados esperados: `normal`, `baixa`, `indisponivel`, `baixa`, `normal`. Todas as leituras desse exemplo são simuladas.

## Testes e evidências

Na raiz do repositório:

```powershell
python -B -m unittest discover -s src/firmware -p test_bateria.py -v
python -B src/firmware/test_floodfill.py
```

Foram aprovados 21 testes da bateria no CPython 3.12.10: conversão, calibração, limites do pacote e ADC, ausência de sensor/configuração, origem dos dados, formato de telemetria, baixa tensão, recuperação com histerese, falha durante baixa tensão e rejeição de configuração inválida. As fontes são funções simuladas; nenhum sensor ou circuito foi acessado.

## Pendências para validação física

1. Energia confirma química/células, tensão máxima e limiares do pacote; Hardware registra divisor, GPIO e faixa útil do ADC.
2. Comparar tensão do pacote, tensão no divisor e leitura do ADC em vários pontos com multímetro. Registrar ganho, offset, dispersão e versão do firmware.
3. Validar ausência de bateria, circuito desconectado, saturação e falha de aquisição, sem assumir que todos esses casos são distinguíveis só pela tensão.
4. Com fonte ajustável e condições de bancada definidas pela equipe, conferir limiares e recuperação. Não descarregar a bateria abaixo dos limites para provocar um teste.
5. Integrar a decisão de parada à FW08 e a leitura ao emissor da FW09. Confirmar no painel tensão, origem, validade e falhas, incluindo falta de leitura.

A parte física e a integração com estados/serial continuam pendentes. Os testes no computador não encerram esses critérios da issue.
