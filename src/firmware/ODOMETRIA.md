# FW04 - Encoders e odometria

Issue: [#6](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/6). Responsável: Guilherme Negreiros Pereira.

## O que esta entrega faz

`odometria.py` calcula velocidade e deslocamento de cada roda a partir de contadores cumulativos. Integra uma pose contínua `(x_mm, y_mm, theta_rad)` com o modelo diferencial. O núcleo usa apenas `math` e `time`; não depende de `machine`, Pydantic ou NiceGUI. Não inicia motores.

A origem é a posição inicial do robô: x aponta para a frente, y para a esquerda e ângulos positivos giram no sentido anti-horário. A pose é uma estimativa por encoders, sujeita a derrapagem e erro de geometria. Não representa a célula do labirinto e não modifica o mapa do Flood Fill.

## Contagem e unidades

- `mm_por_contagem = pi * diametro_mm / contagens_por_volta`.
- `deslocamento_mm = delta_contagens * mm_por_contagem * polaridade`.
- `velocidade_mm_s = deslocamento_mm * 1000 / dt_ms`.
- `delta_theta = (direita_mm - esquerda_mm) / distancia_rodas_mm`.

Cada roda pode ter diâmetro, escala e polaridade próprios. As contagens por volta são as contagens efetivas na roda: incluir a redução se o sensor estiver no eixo do motor e o fator de bordas adotado. Não multiplicar novamente por quatro se o valor já veio em x4. Não existe configuração física padrão enquanto a INT02 não confirmar as medidas.

`EncoderQuadratura` demonstra contagem x4: `00 -> 01 -> 11 -> 10 -> 00` soma quatro; a sequência inversa subtrai quatro. Estados repetidos não contam. Uma transição que muda A e B ao mesmo tempo é descartada, incrementa `transicoes_invalidas` e ressincroniza no novo estado. Esse diagnóstico não recupera pulsos perdidos.

## Uso pelo controle de velocidade

```python
from odometria import Odometria

# Valores DIDÁTICOS, sem calibração no carrinho.
odom = Odometria(
    diametro_esquerdo_mm=32,
    diametro_direito_mm=32,
    contagens_por_volta_esquerda=960,
    contagens_por_volta_direita=960,
    distancia_rodas_mm=90,
)
odom.atualizar(0, 0, 1000)  # Primeira leitura só estabelece a referência.
amostra = odom.atualizar(96, 96, 1100)
print(amostra.velocidade_esquerda, amostra.velocidade_direita)
```

A FW05 usa as duas velocidades como realimentação independente, com alvos nas mesmas unidades. O chamador deve obter um snapshot coerente dos contadores esquerdo/direito e de `ticks_ms()` e chamar `atualizar`. A leitura sincronizada e a seção crítica, se necessárias, pertencem ao adaptador da placa. Não executar a integração trigonométrica dentro da IRQ.

Preferir `Encoder`/PCNT quando a placa e o firmware confirmados oferecerem esse recurso. Nesta entrega não há driver GPIO/IRQ, escolha de pinos ou comprovação da taxa máxima de captura. `EncoderQuadratura` permite testar bordas sem depender dessas decisões; não deve ser usado como prova de captura física em alta frequência.

Para a telemetria existente, as velocidades correspondem a `wheel_left.speed` e `wheel_right.speed`, unidade `mm/s`. Pulsos de teste exigem `source=simulated`; pulsos capturados por sensor permitem `measured` para velocidade, enquanto a pose continua estimada. Antes da primeira amostra, ou sem encoder disponível, publicar leitura indisponível, não zero. A ligação ao emissor serial pertence à FW09.

## Tempo, overflow e reset

No MicroPython, o módulo usa `time.ticks_diff`; no CPython, subtração comum. Também aceita `diferenca_tempo` injetada para simular rollover do relógio. O tempo deve ser monotônico em milissegundos. Intervalos nulos/negativos são rejeitados sem consumir as contagens. Ler antes de atingir metade do período do relógio: depois disso `ticks_diff` não distingue passado de futuro.

Contadores assinados ilimitados usam `modulo_contador=None`. Para um contador de N bits que realmente dá wrap, informar `modulo_contador=2**N`. O delta usa o caminho assinado mais curto. Exatamente metade do módulo é ambígua e gera erro; deslocamentos maiores podem parecer menores e não são detectáveis só por duas leituras. Dimensionar a frequência de amostragem conforme o máximo de pulsos por segundo. Contador saturante/PCNT com limites precisa de tratamento no adaptador, não deve ser tratado como contador com wrap.

Após um reset conhecido do contador ou do relógio, chamar `rebasear(esquerda, direita, t_ms)` antes de continuar. Isso preserva a pose e os deslocamentos acumulados; o movimento durante a perda de referência é desconhecido e não é integrado. O núcleo não tenta adivinhar se uma queda na contagem foi ré ou reset. Para uma nova origem, criar uma nova instância.

## Testes reproduzíveis

Na raiz do repositório, com Python 3.11 ou posterior, sem instalar pacotes:

```powershell
python -B -m unittest discover -s src/firmware -p test_odometria.py -v
python -B src/firmware/test_floodfill.py
```

Os testes comparam velocidades, distâncias e arcos com resultados analíticos. Cobrem primeira leitura, avanço/ré, roda parada, curva, giro, escalas/polaridades independentes, rollover em ambos os sentidos, wrap do relógio, reset explícito, entradas inválidas sem alteração do estado e pulsos de quadratura alimentando a odometria.

Resultado desta entrega: 19 testes automatizados de odometria aprovados no CPython 3.12.10, usando pulsos e relógio simulados. Isso não comprova execução no MicroPython nem valida sensor, pinagem, precisão física ou captura em alta frequência.

## Conferência na bancada (pendente)

1. Com rodas suspensas e motores desabilitados, confirmar alimentação e GPIOs com Hardware/Energia. Registrar placa, versão do MicroPython e API do contador.
2. Girar cada roda uma volta manualmente nos dois sentidos. Registrar contagens, fator de bordas e redução. Ajustar polaridade para que avanço seja positivo nas duas rodas.
3. Medir diâmetros e distância entre rodas; repetir deslocamentos conhecidos para conferir escala. Registrar valor esperado, observado e erro.
4. Comparar contagem em baixa e alta velocidade com uma referência independente; verificar perda de bordas, limites do contador e frequência de amostragem.
5. Conferir reset, rollover e leitura sincronizada. Só depois ligar a medição à malha de velocidade e executar os testes físicos da INT05.

A issue depende de INT02, FW01 e FW02 para fechar a integração física. Escala, polaridade, driver da placa e execução no MicroPython continuam pendentes até essa conferência.
