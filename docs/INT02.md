# INT02: Hardware, pinagem e viabilidade do MicroPython

| Campo | Valor |
|---|---|
| Equipe | Integração |
| Prioridade | P0 |
| Prazo sugerido | 21/10/2026 |
| Fonte da pinagem | Esquemático MicroMouse Hardware, versão V1.0 (28/09/2026), confirmado pelo Hardware |
| Última atualização | 26/10/2026 |

Os componentes do repositório 2026.1 são referência histórica e não constituem inventário confirmado da equipe atual. Este documento refere-se ao hardware da equipe atual.

Valores de status utilizados: **Confirmado**, **Pendente** (depende de definição ou medição) e **A verificar** (depende de teste ou conferência na placa).

---

## 1. GPIOs, tensões, alimentação, I2C e pinos de boot/reservados

### 1.1 Placa

| Item | Valor | Status |
|---|---|---|
| Modelo | ESP32-S3-DevKitC-1, módulo N8R2 (8 MB de flash, 2 MB de PSRAM quad) | Confirmado (esquemático V1.0) |
| Variante exata | Conferir a marcação impressa no módulo (N8R2, N8R8, N16R8, etc.) | A verificar |

A variante influencia os pinos reservados: nos módulos com PSRAM octal (R8), os GPIO 35 a 37 não ficam disponíveis. Na N8R2 (PSRAM quad), ficam livres.

### 1.2 Mapa de pinos

| Função | Sinal | GPIO | Observação |
|---|---|---|---|
| Sensor 1, esquerda (HC-SR04) | TRIG_1 / ECHO_1_3V3 | 4 / 5 | ECHO passa pelo conversor de nível |
| Sensor 2, frontal esquerda (HC-SR04) | TRIG_2 / ECHO_2_3V3 | 6 / 7 | ECHO passa pelo conversor de nível |
| Sensor 3, direita (HC-SR04) | TRIG_3 / ECHO_3_3V3 | 8 / 9 | ECHO passa pelo conversor de nível; posição inferida (ver 1.6) |
| Sensor 4, frontal direita (HC-SR04) | TRIG_4 / ECHO_4_3V3 | 10 / 11 | ECHO passa pelo conversor de nível |
| Encoder esquerdo (N20, canais C1 e C2) | ENC_ESQ_A / ENC_ESQ_B | 12 / 13 | Sinais em 3,3 V |
| Encoder direito (N20, canais C1 e C2) | ENC_DIR_A / ENC_DIR_B | 14 / 15 | Sinais em 3,3 V |
| Ponte H, canal A (motor esquerdo) | MOT_INA1 / MOT_INA2 | 16 / 17 | ZS-H2, saída OUT_A ligada ao motor M1 |
| Ponte H, canal B (motor direito) | MOT_INB1 / MOT_INB2 | 18 / 21 | ZS-H2, saída OUT_B ligada ao motor M2 |
| IMU | SDA / SCL | Pendente | Não consta no esquemático V1.0 |
| Botão | A definir | Pendente | Não consta no esquemático V1.0 |

### 1.3 Tensões e alimentação

| Item | Valor | Status |
|---|---|---|
| Bateria | LiPo 2S, 7,4 V nominal, 650 mAh | Confirmado |
| Tensão da bateria carregada | 8,3 V | Confirmado (Hardware, 24/10/2026) |
| Step-down A | 7,4 V para 5 V, 3 A. Alimenta a ESP (pino VIN), os HC-SR04 e o lado HV do conversor de nível | Confirmado (esquemático) |
| Step-down B | 7,4 V para 6 V, 3 A. Alimenta a ponte H e os motores N20 de 6 V | Confirmado (esquemático) |
| Lógica da ESP | 3,3 V | Confirmado |
| Alimentação dos encoders | Fornecida pela ESP, com sinais em 3,3 V | Confirmado (Hardware, 24/10/2026) |
| Conversor de nível | BSS138, 4 canais, HV = 5 V e LV = 3,3 V, aplicado aos sinais ECHO | Confirmado (componente recebido em 26/10/2026) |
| Sinais TRIG (3,3 V para HC-SR04 alimentado em 5 V) | Ligação direta, sem conversor | A verificar em bancada |
| Sinais INA/INB do ZS-H2 recebendo lógica de 3,3 V | Ligação direta, sem conversor | A verificar com o Hardware |

Conforme a nota do esquemático, as saídas dos dois step-downs (5 V e 6 V) devem ser reguladas antes da ligação dos demais módulos. Todos os módulos compartilham a mesma referência de GND.

### 1.4 Interface I2C

| Item | Valor | Status |
|---|---|---|
| Modelo do IMU | A definir com o Hardware | Pendente |
| Endereço I2C | A definir | Pendente |
| GPIOs de SDA e SCL | A definir | Pendente |
| Tensão do barramento | 3,3 V (proposta) | Pendente |

Na porta ESP32 do MicroPython, o I2C de hardware pode assumir pinos padrão que coincidem com os GPIO 8 e 9, utilizados neste projeto por TRIG_3 e ECHO_3_3V3. Os pinos `scl` e `sda` devem ser sempre informados explicitamente no código. O comportamento padrão deve ser conferido na build utilizada.

### 1.5 Pinos de boot, reservados e livres

| Categoria | GPIOs | Situação no esquemático V1.0 |
|---|---|---|
| Strapping e boot | 0, 3, 45, 46 | Não utilizados |
| USB nativo | 19, 20 | Não utilizados |
| UART0 (console) | 43, 44 | Não utilizados |
| Flash e PSRAM quad (não utilizar) | 26 a 32 | Não utilizados |
| LED RGB da placa | 48 (ou 38, conforme a revisão da placa) | A verificar a revisão |
| Livres | 1, 2, 35 a 42, 47 | Disponíveis para IMU e botão |

Os GPIO 39 a 42 correspondem aos pinos padrão de JTAG e podem ser usados como GPIO comum caso o JTAG não seja utilizado. Os GPIO 35 a 37 são livres apenas em módulos com PSRAM quad. A escolha dos pinos do IMU e do botão deve ser validada com o Hardware.

### 1.6 Divergências entre fontes

Existe uma segunda lista de pinagem em uso pela equipe. Ela foi comparada ao esquemático V1.0, que prevalece em caso de divergência.

| Item | Segunda lista | Esquemático V1.0 (adotado) | Observação |
|---|---|---|---|
| Ponte H (INA1, INA2, INB1, INB2) | 16, 17, 18, 21 | 16, 17, 18, 21 | Sem divergência. A lista acrescenta que INA corresponde ao motor esquerdo e INB ao direito |
| Sensor esquerda | 4 / 5 | 4 / 5 | Sem divergência |
| Sensor frontal esquerda | 6 / 7 | 6 / 7 | Sem divergência |
| Sensor frontal direita | 10 / 11 | 10 / 11 | Sem divergência |
| Sensor direita | 12 / 13 | 8 / 9 (sensor 3) | Divergente. Os GPIO 12 e 13 pertencem ao encoder esquerdo no esquemático. A posição "direita" para o sensor 3 foi inferida por exclusão e deve ser confirmada com o Hardware |
| Encoder esquerdo | 1 / 2 | 12 / 13 | Divergente. Adotado 12 / 13 |
| Encoder direito | 14 / 15 | 14 / 15 | Sem divergência |
| Condicionamento do ECHO | Divisor de tensão | Conversor de nível BSS138 | Divergente. Adotado o conversor de nível |

Com a adoção do esquemático, os GPIO 1 e 2 ficam livres. Recomenda-se informar o Hardware e o responsável pela segunda lista para que ela seja atualizada conforme o esquemático V1.0.

---

## 2. Parâmetros mecânicos

| Parâmetro | Valor | Status | Forma de obtenção |
|---|---|---|---|
| Motor | N20, 6 V, 750 RPM, com encoder | Confirmado (esquemático) | Não se aplica |
| Pulsos por volta do encoder (PPR) | A definir | Pendente | Datasheet do modelo exato ou contagem manual |
| Redução da caixa | A definir | Pendente | Datasheet do modelo exato ou contagem manual |
| Pulsos por revolução efetivos da roda | A definir | Pendente | Girar a roda um número conhecido de voltas e ler o contador |
| Diâmetro da roda | A definir | Pendente | Medição com paquímetro |
| Distância entre rodas | A definir | Pendente | Medição entre os pontos de contato das rodas |
| Tamanho da célula do labirinto | 18 cm | Confirmado | Estrutura de 72 x 216 cm, com 4 colunas e 12 linhas |
| Roda boba | A definir | Pendente (aguardando chegada) | Medição após a montagem |

Relações de referência, a aplicar após as medições:

```
pulsos_por_volta_da_roda = PPR_encoder x modo_de_decodificacao x reducao
distancia_por_pulso      = pi x diametro_da_roda / pulsos_por_volta_da_roda
```

O Hardware informou, em 24/10/2026, que não dispõe dos parâmetros mecânicos. Eles devem ser levantados pela equipe após a chegada da roda boba.

---

## 3. Firmware MicroPython e drivers

### 3.1 Firmware

| Item | Valor | Status |
|---|---|---|
| Porta | ESP32_GENERIC_S3 | Confirmado |
| Versão estável fixada | v1.28.0 (06/04/2026) | Confirmado (verificar se há versão posterior antes de congelar) |
| Origem | https://micropython.org/download/ESP32_GENERIC_S3/ | Confirmado |
| Variante da build | A build padrão é suficiente se a PSRAM não for utilizada. Caso seja, conferir a variante adequada na página de download | A verificar |
| Licença do MicroPython | MIT | Confirmado |

### 3.2 Encoder e PCNT

A documentação da v1.28.0 descreve a classe `machine.Encoder` com suporte no ESP32 por meio do periférico PCNT, incluindo filtro de ruído (`filter_ns`) e decodificação em 1, 2 ou 4 fases (`phases`).

Teste a executar na placa exata:

```python
from machine import Pin, Encoder

enc_esq = Encoder(0, Pin(12), Pin(13))
enc_dir = Encoder(1, Pin(14), Pin(15))
print(enc_esq.value(), enc_dir.value())
```

Girar cada roda manualmente nos dois sentidos e registrar o resultado.

| Verificação | Resultado | Status |
|---|---|---|
| A classe `machine.Encoder` existe na build instalada | A registrar | A verificar |
| A contagem varia conforme o sentido de rotação | A registrar | A verificar |
| Filtro e modo de decodificação definidos | A registrar | A verificar |

### 3.3 Drivers, ferramentas e licenças

| Item | Uso | Licença | Status |
|---|---|---|---|
| MicroPython | Firmware | MIT | Confirmado |
| esptool | Gravação do firmware | GPL v2 (confirmar) | A verificar |
| mpremote | Transferência de arquivos e REPL | MIT (confirmar) | A verificar |
| Driver USB-serial no PC, caso a porta não seja reconhecida | Console e gravação | Conforme o fabricante | A verificar |
| Driver do IMU | Leitura via I2C | Depende do modelo | Pendente |

---

## 4. Componentes disponíveis, aguardados e substitutos simulados

| Item | Situação | Responsável | Data de desbloqueio | Substituto simulado |
|---|---|---|---|---|
| ESP32-S3-DevKitC-1 | A confirmar com a equipe | A definir | A definir | Não se aplica |
| Conversor de nível BSS138 (4 canais) | Disponível (recebido em 26/10/2026) | A definir | Não se aplica | Não se aplica |
| Roda boba | Aguardado | A definir | A definir | Apoio provisório para testes de bancada. As medições mecânicas definitivas dependem da roda |
| Motores N20 com encoder | A confirmar com a equipe | A definir | A definir | Classe de encoder simulada para testes no PC |
| Ponte H ZS-H2 | A confirmar com a equipe | A definir | A definir | Não se aplica |
| Sensores HC-SR04 (4 unidades) | A confirmar com a equipe | A definir | A definir | Leituras de distância simuladas |
| Step-downs de 5 V e 6 V | A confirmar com a equipe | A definir | A definir | Fonte de bancada |
| Bateria LiPo 2S 650 mAh | A confirmar com a equipe | A definir | A definir | Fonte de bancada |
| IMU | Pendente de definição | A definir | A definir | Valores simulados |
| Botão | Pendente de definição | A definir | A definir | Não se aplica |

---

## Critérios de aceite

- [ ] Registrar GPIOs, tensões lógicas, alimentação, interfaces I2C e pinos de boot/reservados.
- [ ] Definir pulsos por revolução efetivos, redução, diâmetro, distância entre rodas e tamanho de célula, com pendências explícitas.
- [ ] Fixar firmware MicroPython estável e verificar Encoder/PCNT na placa exata, listando drivers e licenças.
- [ ] Separar componentes disponíveis, aguardados e substitutos simulados, com responsável e data de desbloqueio.
