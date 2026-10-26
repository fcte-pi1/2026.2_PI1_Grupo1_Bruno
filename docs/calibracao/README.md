# INT05 - Calibração e desempenho

Issue: [#25](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/25). Responsável: Guilherme Negreiros Pereira.

Base da entrega: `feat/16-medicao-bateria`, commit `53af115`. Essa branch inclui a `dev` em `b4d8aad` e as entregas de encoders (FW04) e bateria (FW14).

## O que está disponível

A ferramenta `tools/calibracao.py` analisa arquivos CSV no computador, usando apenas a biblioteca padrão do Python 3.11+. Não é código para copiar na ESP32: não aciona motores, não altera ganhos e não grava configuração. Usa medições registradas pela equipe para calcular erros e sugerir correções geométricas.

O ensaio físico ainda não foi executado. Não há medidas reais, ganhos calibrados ou autonomia comprovada nesta entrega. FW07/FW08, navegação, sensores e coleta física precisam estar integrados antes da validação final. A INT05 depende de INT04, FW10, FW13 e FW14; o material aqui permite preparar os ensaios enquanto essas integrações avançam.

## Antes de medir

Copiar a [ficha de ensaio](FICHA_ENSAIO.md) e os modelos CSV para uma pasta da campanha. Registrar commit, configuração, montagem, superfície, velocidade, carga, instrumentos e responsáveis. Definir tolerâncias e quantidade de repetições antes da primeira tentativa, para que os limites não sejam escolhidos depois de ver os erros. Usar arquivos separados para campanhas com condições diferentes.

Confirmar parada por comando/falha com as rodas suspensas. Conferir encoders, sensores e alimentação com as outras frentes. As medidas de fita, gabarito angular e instrumentos externos são a referência; comparar a odometria consigo mesma não calibra o robô.

## Sequência de calibração

1. **Encoders:** conferir polaridade e pulsos por volta em ambas as rodas, nos dois sentidos. Registrar se o valor inclui redução e x1/x2/x4. Repetir em baixa e alta velocidade para verificar perda de bordas.
2. **Diâmetro efetivo:** medir distância percorrida por cada roda em deslocamento controlado, registrar suas contagens e repetir. Para uma referência independente, `diametro_mm = distancia_referencia_mm * contagens_por_volta / (pi * abs(contagens))`. A função `diametro_por_volta` faz esse cálculo. Exige distância positiva e contagens não nulas. Derrapagem invalida o ajuste de escala.
3. **Distância entre rodas:** após calibrar as escalas individuais, executar giros lentos nos dois sentidos. Comparar o ângulo acumulado da odometria com o ângulo medido externamente. `distancia_nova = distancia_atual * angulo_odometria / angulo_referencia`; usar `distancia_rodas_corrigida`. Não confundir ângulo alvo com ângulo calculado pelos encoders. Para voltas completas, registrar ângulo acumulado, pois `theta_rad` da FW04 é normalizado e perde o número de voltas.
4. **Sensores:** registrar leituras contra distâncias conhecidas, offsets, validade, tempo de resposta e falhas. Conferir orientação da IMU com referência externa. Não compensar erro de sensor alterando ganhos de motor.
5. **Controle:** começar em velocidade baixa; ajustar uma malha por vez, registrando ganhos e saturação. Comparar alvos, velocidades medidas, erro e tempo de resposta. Confirmar timeout, estol e parada antes de elevar velocidade. Não transportar ganhos de simulação como ganhos físicos.
6. **Retas e giros:** executar repetições em ambos os sentidos, mantendo montagem e condições. Como ponto de partida de planejamento, propor cinco repetições por condição e obter acordo da equipe. Registrar também tentativas interrompidas, falhas e colisões; não descartar tentativas ruins do CSV.

Exemplo de uso das funções no Python, a partir da raiz:

```python
from tools.calibracao import diametro_por_volta, distancia_rodas_corrigida

# Dados didáticos, sem medição no carrinho.
print(diametro_por_volta(100, 960, 960))
print(distancia_rodas_corrigida(100, 90, 100))
```

Repetir o ensaio após cada ajuste e registrar a diferença na ficha. Uma mudança geométrica afeta o controle e exige reteste.

## Registro de retas e giros

Usar [modelo_movimentos.csv](modelo_movimentos.csv). Separador: vírgula; decimais com ponto; UTF-8. Não editar os cabeçalhos. Cada linha representa uma tentativa:

| Campo | Conteúdo |
| --- | --- |
| origem | `measured` para medição física; `simulated` para dados de teste |
| tipo | `reta` ou `giro` |
| controle | `com_correcao` ou `sem_correcao` |
| alvo, medido | mm para reta; graus para giro; preservar sinal de ré e sentido do giro |
| desvio_mm | Maior desvio lateral absoluto do centro em relação à trajetória; para giro no lugar, deslocamento máximo do centro |
| colisoes | Inteiro não negativo; contar contatos durante a tentativa |
| resultado | `concluido`, `interrompido` ou `falha` |

Se não houver uma medição, não preencher zero para fingir sucesso. Registrar a tentativa e o motivo na ficha, como pendência; o analisador exige medidas numéricas para calcular o erro. `medido` é a medida externa, não a estimativa do robô.

A ferramenta separa origem, tipo, controle e alvo. Calcula erro assinado (`medido - alvo`), erro absoluto médio, desvio padrão amostral, colisões e taxa de sucesso. Com uma única tentativa, a dispersão é `null`. Sucesso exige resultado concluído, erro e desvio dentro dos limites e nenhuma colisão. Não normaliza um erro de 360 graus para zero.

Para demonstrar o fluxo sem hardware, executar:

```powershell
python -B tools/calibracao.py movimentos docs/calibracao/exemplo_simulado_movimentos.csv --tolerancia-reta-mm 20 --tolerancia-giro-graus 3 --desvio-max-mm 10
```

Os valores desse comando e do CSV são fictícios. O resultado permanece marcado como `simulated`. Para uma campanha real, substituir o arquivo e os limites pelos valores acordados, salvando a saída JSON junto das evidências.

Comparar as médias de erro absoluto e a dispersão entre `com_correcao` e `sem_correcao`, com o mesmo alvo e condições. Neste roteiro, sem correção significa desativar a correção de trajetória/orientação mantendo as malhas de velocidade. Se a equipe também comparar malha aberta e fechada, fazer campanhas separadas e indicar isso na ficha. Alternar a ordem dos modos ajuda a reduzir o efeito da descarga e do aquecimento.

## Ensaio de 30 minutos

Usar [modelo_autonomia.csv](modelo_autonomia.csv), um arquivo por robô/boot/campanha. Capturar execução física contínua por pelo menos 1800 segundos, com intervalo de amostragem acordado previamente. O tempo é decorrido desde o início do ensaio em um relógio monotônico externo ou reconstruído com identificação de boot. Não concatenar relógios que reiniciaram.

| Campo | Conteúdo |
| --- | --- |
| t_s | Tempo decorrido em segundos, estritamente crescente |
| origem | Uma única origem no arquivo: `measured` ou `simulated` |
| estado | `executando`, `parado` ou `falha` |
| tensao_v | Tensão do pacote; vazio quando indisponível |
| corrente_a | Corrente de descarga medida; vazio se não houver sensor |
| temperatura_c | Maior temperatura dos pontos de monitoramento definidos na ficha; vazio sem medição |
| resets, quedas_link | Contadores cumulativos desde o início do ensaio; nunca diminuir |

Registrar os pontos de temperatura e o limite adotado com Hardware/Energia. Anexar logs brutos, evidências do movimento, resets e quedas. Uma coleta do computador aberta por 30 minutos não comprova que o robô operou por 30 minutos.

Com os limites acordados, executar, substituindo os exemplos numéricos:

```powershell
python -B tools/calibracao.py autonomia caminho/do/ensaio.csv --intervalo-max-s 5 --tensao-min-v 6.3 --temperatura-max-c 60
```

Esses limites são ilustrativos e não constituem especificação da bateria ou dos componentes. O resultado lista duração, maior intervalo, extremos de tensão/temperatura, resets, quedas e pendências. O campo `criterios_observaveis_atendidos` só verifica os números informados: não certifica a origem, movimento contínuo, precisão dos instrumentos ou conclusão da INT05. Dois pontos separados por 1800 segundos falham se a lacuna superar o intervalo permitido.

Energia em Wh é calculada por integração trapezoidal de `tensao * corrente` apenas se todas as amostras tiverem ambas as medidas. Sem corrente, retorna `null`; isso não impede avaliar duração, tensão e temperatura, mas mantém consumo indisponível. Os sensores necessários não estão confirmados no repositório. A integração é uma aproximação sujeita à frequência da coleta; não mede capacidade total nem percentual da bateria.

## Testes e critério de encerramento

```powershell
python -B -m unittest discover -s tools -p test_calibracao.py -v
python -B -m unittest discover -s src/firmware -p "test_*.py"
python -B src/firmware/test_floodfill.py
```

Os 21 testes do analisador cobrem geometria, sinais, erro e dispersão, agrupamento, falhas, colisões, leitura CSV e execução da CLI até JSON. Cobrem também duração, energia com potência constante/variável, dados ausentes, limites, resets, desconexões e tempo inválido. Toda a validação automatizada usa dados sintéticos.

Para encerrar a issue, anexar ficha preenchida, configuração calibrada, medições repetidas, comparação entre modos, captura física de 30 minutos e revisão das frentes envolvidas. Registrar erros acima da tolerância, ações corretivas e retestes. Permanecem pendentes todos os resultados físicos, a calibração dos sensores/ganhos e a comprovação de autonomia.
