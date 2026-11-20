# Carrinho: software preparado para a proxima bancada

Preparado em 19/11/2026. Firmware experimental para a montagem da equipe.
A parte nova esta em `src/firmware/robot`; os modulos anteriores foram
preservados. Esta versao ainda nao foi gravada nem validada na ESP.

## O que esta pronto e o que ainda depende do carrinho

Implementados: controle dos dois motores, leitura assinada de encoders, leitura
sequencial de quatro ultrassons, rampa de aceleracao, compensacao entre rodas,
movimentos por contagens, giros, limite por tempo, deteccao de roda travada,
parada por BOOT, partida manual e dois modos de navegacao.

Validacao no computador cobre falhas e exploracao em 200 labirintos gerados com
becos e ciclos. Isso NAO valida aderencia, frenagem, torque, interferencia de
ultrassom ou geometria. O codigo novo ainda nao foi executado na placa.

Na segunda-feira, 23/11, faltara: corrigir tombamento, verificar a API Encoder
na build instalada, medir contagens por distancia, acertar giros de 90 graus,
medir folga para girar e distancia de parada e testar o conjunto. Nao e possivel
prometer que apenas redistribuir o peso deixara o robo autonomo.

## Duas formas de navegar

**patrol (padrao):** anda em passos curtos; diante de parede procura direita,
esquerda ou retorno. Nao precisa saber sua coordenada inicial. Comecar alinhado
com o corredor e com espaco para o corpo inteiro. Pode repetir trajetos e nao
garante encontrar uma saida; e o modo para testar a pista atual.

**explore:** busca em profundidade (DFS), registra celulas visitadas e retorna
por caminhos conhecidos. Usa coordenadas relativas: o ponto inicial e (0,0),
e a frente inicial e +y. Pode comecar em qualquer CELULA, mas precisa estar
centrado nela, alinhado e percorrer celulas de tamanho uniforme. Uma posicao
arbitraria fora do centro nao e equivalente a uma celula calibrada. Com uma
pista fechada e observacoes corretas, visita a area alcancavel e retorna ao
inicio; informa EXPLORED, nao 'saida encontrada'. Se o mapa exige mais de 256
celulas ou 100 acoes, para por limite configurado.

Uma saida externa ainda nao tem regra fisica definida. Nao foi implementada uma
regra falsa do tipo 'sem eco = saida'. GOAL_CELL permite futuramente parar em
uma celula-objetivo conhecida relativa ao inicio. Cruzar uma abertura externa
exige definir a geometria/borda e o criterio de chegada antes de usar.

## Pinagem adotada: a planilha enviada

| Funcao | GPIOs |
|---|---|
| Motor esquerdo INA1/INA2 | 16 / 17 |
| Motor direito INB1/INB2 | 18 / 8 |
| Encoder esquerdo A/B | 11 / 12 |
| Encoder direito A/B | 14 / 13 |
| Frontal TRIG/ECHO | 35 / 36 |
| Traseiro TRIG/ECHO | 37 / 38 |
| Direito TRIG/ECHO | 39 / 40 |
| Esquerdo TRIG/ECHO | 41 / 42 |
| Botao de inicio/parada | BOOT / GPIO 0 |

ECHO passa pelo conversor de nivel. Nao mudar fiacao com USB ou bateria ligados.
Esta pinagem difere de `docs/INT02.md`: para esta montagem, prevalece a planilha
confirmada pelo usuario. GPIOs 17/18 ja sao motores: nao executar o teste legado
de UART1/telemetria nesses pinos.

## Arquivos para abrir no Thonny

- `robot/config.py`: todos os pinos, limites e parametros de calibracao.
- `robot/hardware.py`: acesso a PWM, sensores e encoders.
- `robot/control.py`: deslocamentos e giros monitorados.
- `robot/planner.py`: decisao de direcao e exploracao DFS, testavel sem placa.
- `robot/app.py`: modos, inicio, parada e comandos de bancada.
- `main_robot.py`: entrada opcional para funcionar sem computador.
- `tests/test_robot*.py`: testes do computador; NAO copiar para a ESP.

Manter o backup completo anterior e os seis arquivos originais em armazenamento
local da equipe. Backups de flash e configuracoes Wi-Fi nao fazem parte desta
entrega, pois podem conter credenciais. Nao publicar esses arquivos.

## Preparacao na segunda-feira

1. Com tudo desligado, corrigir a mecanica. Carrinho deve ficar apoiado sem mao,
   nao tombar ao partir/parar e permitir curvas sem raspar sensores ou chassi.
2. Conferir com o montador alimentacao, GND comum e conversor de nivel. Para
   bancada USB, manter a alimentacao externa positiva da ESP isolada conforme
   a ligacao identificada pelo montador. Bateria alimenta demais componentes.
   Nao reconectar esse fio simultaneamente ao USB sem revisar o circuito.
3. Pelo Thonny, escolher MicroPython (ESP32), porta COM atual. Nao reinstalar
   MicroPython: o firmware identificado foi v1.29.0, flash 8MB, PSRAM 2MB.
4. Fazer backup atualizado se a equipe alterou arquivos. Copiar a pasta `robot`
   completa para a raiz da ESP (o dispositivo deve ter `/robot/__init__.py`,
   `/robot/config.py`, etc.). Nao copiar `main_robot.py` como `main.py` ainda.
5. Fechar outros programas usando a serial. No Shell do Thonny:

```python
from robot.app import connect
r = connect()                 # para motores; cria interfaces; nao anda
print(r.sensors())            # mm ou None; nunca 'infinito' em falha
print(r.hw.counts())          # dois contadores quadratura phases=4
```

Se `machine.Encoder` nao existir na build, o construtor para e informa isso.
Nao ha fallback silencioso por IRQ que mudaria a unidade da calibracao.
Referencia da API: https://docs.micropython.org/en/latest/library/machine.Encoder.html

## Calibracao pratica

Os flags STABLE_CHASSIS e CALIBRATED comecam False. O programa recusa navegacao
enquanto nao forem validados. Nao marque True apenas para remover o bloqueio.

### Sentidos, medidas e partida

Com rodas suspensas, confirmar um motor por vez, ambos os sentidos:

```python
r.pulse(left=0.40, right=0, duration_ms=150, wheels_lifted=True)
r.pulse(left=0, right=0.40, duration_ms=150, wheels_lifted=True)
```

Cada chamada e um teste separado; observar antes de repetir. Para reverso,
usar -0.40. Se o sentido fisico estiver invertido, ajustar MOTOR_SIGNS. Ao
avancar, ambos os contadores devem aumentar; ajustar ENCODER_SIGNS se necessario.

Medir diametro das rodas. Com robot parado, registrar `a=r.hw.counts()`, girar
suavemente cada roda um numero conhecido de voltas completas no sentido de
avancar e registrar `b=r.hw.counts()`. Se a reducao resistir, nao forcar; obter
essa medida com procedimento de bancada do montador. Usar b-a para cada roda:

`contagens_por_mm = abs(delta_contagens) / (voltas * pi * diametro_mm)`

O utilitario `tools/calibrar_robot.py --help` calcula a partir dessas medidas.
Preencher COUNTS_PER_MM com as duas medidas. Contagens antigas desta conversa
eram transicoes individuais A/B; nao reutilizar seus numeros como phases=4.

Depois de corrigida a mecanica, marcar STABLE_CHASSIS=True, salvar config e
reiniciar a ESP. Voltar a criar `r`. Para calibrar NO CHAO, em area desobstruida:

```python
r.jog('forward', 150)  # um unico pulso, retorna contagens assinadas
```

Maximo 300ms por chamada, MAX_PWM=50%. Nao repetir se travar. Comparar distancia
real medida no chao com contagens; ajustar contagens/mm se houver diferenca
consistente. Investigar atrito/bateria antes de subir PWM. Nao ha pulso inicial
de alta potencia nem aumento automatico para vencer travamento.

### Giro e folga do corpo

Medir a folga necessaria para o corpo/sensores varrerem uma curva e preencher
TURN_CLEARANCE_MM, considerando a posicao de CADA sensor. Os quatro raios de
ultrassom nao enxergam todas as quinas do corpo; revisar fisicamente esse limite.
Para curva no chao, em area ampla, depois da validacao mecanica:

```python
a = r.hw.counts()
r.jog('right', 100)    # observar, repetir manualmente apenas se necessario
# quando a orientacao atingir exatamente 90 graus medidos:
b = r.hw.counts()
print(b[0]-a[0], b[1]-a[1])
```

Preencher TURN_90_COUNTS com magnitudes das duas rodas, repetir para esquerda
e ajustar. Se os sentidos exigirem valores muito diferentes, investigar a
mecanica; esta versao usa o mesmo par de magnitudes nos dois sentidos.

### Frenagem e geometria

FRONT_STOP_MM=150 e START_CLEARANCE_MM=200 sao limites conservadores de bancada,
NAO valores finais para corredores de 18cm. Medir a distancia de parada real
com carga, bateria e velocidade finais; manter margem para latencia e inercia.
PWM zero pode deixar a roda livre: o modo eletrico de frenagem da ZS-H2 ainda
nao foi confirmado. Nenhuma garantia de parar exatamente na leitura limiar.

Para explore, medir CELL_MM real e CENTER_FRONT_WALL_MM (sensor ate uma parede
vizinha quando o robo esta centrado). O limiar de parada deve permitir chegar
ao centro sem colisao; se a geometria nao permitir margem, nao habilitar explore.
WALL_MM e WALL_HYST_MM devem separar parede vizinha de corredor aberto. Leituras
na faixa ambigua interrompem a exploracao, em vez de registrar um mapa falso.

Somente depois de medir e validar, preencher os parametros e CALIBRATED=True.
Os valores de distancia e giro sao separados justamente para permitir terminar
a calibracao sem reescrever a logica.

## Rodar depois da calibracao

```python
r.run('patrol')   # teste de andar/desviar; limite de 60s e 100 acoes
# OU, centrado em uma celula e apos calibrar geometria:
r.run('explore')
```

BOOT interrompe durante a execucao. Ctrl+C tambem encerra com comandos em zero
quando o interpretador responde. A chave continua sendo a parada fisica.
Uma falha nao retoma automaticamente e nao confirma uma celula parcialmente
percorrida. Reposicionar o robo antes de reiniciar explore (mapa novo a cada run).

Quando pronto para funcionar sem USB, copiar `main_robot.py` para a raiz da ESP
com nome `main.py`. Ele zera as saidas e aguarda. Pressionar BOOT por 2s e SOLTAR
inicia o MODE escolhido; qualquer pressao durante a corrida para. Nao segurar
BOOT durante reset/energizacao, pois isso abre o modo de gravacao da ESP.
Restaurar alimentacao pela bateria somente com tudo desligado e USB removido,
conforme a montagem confirmada. O programa inclui watchdog no modo standalone;
apos reset volta a aguardar comando, nunca retoma corrida.

Nao instalar outro programa com partida automatica junto. Na bancada pelo
Thonny (sem main.py), watchdog nao e ativado; limites de software e finally
continuam ativos, mas uma falha dura do interpretador exige a chave fisica.

## Testes do computador

Na raiz desta copia local, com Python:

```powershell
python -m unittest discover -s tests -p "test_robot*.py" -v
python -m compileall -q src/firmware/robot src/firmware/main_robot.py
```

Os testes cobrem partida bloqueada, botao, timeout, roda travada, encoder
invertido, perda de sensor, obstaculo durante movimento, pose sem confirmacao,
giro, rampa, pinagem, saturacao PWM, espacamento dos ultrassons e 200 mapas.
Esta suite nao substitui a validacao na ESP nem na pista.

## Limites desta entrega

- Sem sensor de inclinacao: o software nao detecta nem corrige tombamento.
- Sem medicao de bateria: nao infere carga pelo comportamento dos motores.
- Sem IMU: curvas dependem de encoder, calibracao e aderencia.
- Sem integracao Bluetooth ou painel: controle local/USB, logs no console;
  modulos de telemetria existentes preservados, mas nao ligados ao novo loop.
- Ultrassom sem eco ou inconsistente causa parada. Espacos abertos sem alvo
  podem parar a patrulha; isso e preferivel a tratar falha como passagem livre.
- DFS testa topologia discreta. Erros acumulados, escorregamento e leituras
  falsas podem invalidar o mapa fisico: a confirmacao e por encoder, nao visao.
- Firmware novo ainda nao gravado nesta etapa; instalacao e validacao fisica pendentes.
