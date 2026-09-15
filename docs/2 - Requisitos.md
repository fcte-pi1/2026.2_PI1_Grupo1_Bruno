# Requisitos
**'Requisitos** definem o que um sistema deve fazer e sob quais restrições. 

Requisitos relacionados com a primeira parte dessa definição — "o que um sistema deve fazer", ou seja, suas funcionalidades — são chamados de **Requisitos Funcionais**.

Já os requisitos relacionados com a segunda parte — "sob que restrições" — são chamados de **Requisitos Não-Funcionais'**. [Ref: Requisitos](https://engsoftmoderna.info/cap3.html)

>- Descrever os requisitos funcionais (RF) em alto nível (Épico);
>- Descrever os requisitos não-funcionais (RNF) de forma objetiva; Mais facilmente, mais rapidamente, mais responsivo, de fácil uso, são descrições subjetivas não-válidas. Um exemplo de requisito não-funcional de desempenho: "a página deve carregar em até 5s quando em conexão 4G".
>- Ao descrever os requisitos (RF e RNF), usar a classificação MoSCoW (*Must have*, *Should have* e *Could have*), para auxiliar a priorização.


## 1 Requisitos Funcionais (RF) 

### 1.1 Requisitos de estruturas

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RF01-E | Suportar e integrar os componentes | A estrutura do micromouse deve ser capaz de suportar e integrar todos os componentes necessários para a operação do carrinho | Must |                  |                          |
| RF02-E | Percorrer a pista | A estrutura deve permitir que o micromouse percorra o caminho sem interferências, respeitando limites de altura, largura e mobilidade | Must |                  |                          |
| RF03-E | Proteger componentes eletrônicos | A estrutura deve proteger os componentes eletrônicos contra possíveis danos durante os testes e o percurso durante a avaliação | Should |                  |                          |
| RF04-E | Substituir e atualizar módulos | A estrutura deve permitir a substituição e atualização de módulos de forma independente | Should |                  |                          |
| RF05-E | Construir percurso para testes | O projeto deve conter um protótipo de percurso construído para a realização de testes do micromouse | Must |                  |                          |

### 1.2 Requisitos de Hardware

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RF01-H | Mapear o percurso | O circuito deve detectar presença ou ausência de paredes nas direções frontal, lateral esquerda, lateral direita do micromouse | Must |                  |                          |
| RF02-H | Controlar velocidade | O circuito deve controlar individualmente a velocidade de cada motor DC por meio de sinal PWM enviado ao driver de motor | Must |                  |                          |
| RF03-H | Comunicar sem fio | O circuito deve incluir um módulo de comunicação sem fio para transmitir em tempo real os dados do robô para o sistema web | Must |                  |                          |
| RF04-H | Informar consumo de bateria | O circuito deve detectar e sinalizar informações sobre o consumo da bateria em tempo real | Must |                  |                          |
| RF05-H | Movimentar micromouse | O robô deve possuir motores e rodas controláveis adequados para percorrer o trajeto | Must |                  |                          |
| RF06-H | Centralizar micromouse | O sistema deve mover o Micromouse em linha reta dentro dos corredores do labirinto, mantendo sua trajetória centralizada entre as paredes laterais. | Must |                  |                          |
| RF07-H | Executar rotações | O sistema deve executar curvas de 90° e 180° de maneira precisa | Must |                  |                          |
| RF08-H | Iniciar e interromper navegação | O sistema deve iniciar e interromper a navegação por meio de um botão físico acessível externamente no micromouse | Should |                  |                          |
| RF09-H | Emitir alarme | O sistema deve acionar um alarme ao detectar que o micromouse atingiu a sala objetivo do labirinto | Could |                  |                          |

### 1.3 Requisitos de Software

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RF01-S | Navegação autônoma | O Micromouse deve percorrer o labirinto de forma autônoma, sem intervenção humana durante a execução normal do desafio. | Must |  | |
| RF02-S | Detecção de paredes | O sistema deve detectar a existência de paredes ao redor do Micromouse durante sua movimentação. | Must |  | |
| RF03-S | Monitoramento da localização | O sistema deve determinar e atualizar a localização do Micromouse durante a execução do desafio. | Must |  | |
| RF04-S | Monitoramento da orientação | O sistema deve determinar a orientação atual do Micromouse para auxiliar sua navegação pelo labirinto. | Must |  | |
| RF05-S | Mapeamento do labirinto | O sistema deve construir uma representação do labirinto a partir das paredes descobertas durante a execução. | Must |  | |
| RF06-S | Atualização do mapa | O sistema deve atualizar o mapa do labirinto sempre que novas informações sobre paredes e caminhos forem obtidas. | Must |  | |
| RF07-S | Planejamento de rota | O sistema deve determinar um caminho entre a posição atual do Micromouse e a área objetivo utilizando as informações conhecidas do labirinto. | Must |  | |
| RF08-S | Replanejamento da rota | O sistema deve atualizar o caminho planejado quando novas informações sobre o labirinto tornarem a rota anterior inadequada. | Must |  | |
| RF09-S | Controle de movimentação | O sistema deve executar os movimentos necessários para que o Micromouse percorra o caminho planejado. | Must |  | |
| RF10-S | Detecção do objetivo | O sistema deve detectar quando o Micromouse alcançar a área objetivo do labirinto. | Must |  | |
| RF11-S | Registro do trajeto | O sistema deve registrar o trajeto percorrido pelo Micromouse durante a resolução do labirinto. | Must |  | |
| RF12-S | Monitoramento da velocidade | O sistema deve obter e registrar os dados necessários para calcular a velocidade do Micromouse durante o desafio. | Must |  | |
| RF13-S | Monitoramento da bateria | O sistema deve obter e registrar informações referentes ao consumo e nível da bateria durante a execução. | Must | | |
| RF14-S | Contagem do tempo | O sistema deve registrar o tempo decorrido durante a resolução de cada desafio e o tempo de conclusão. | Must | | |
| RF15-S | Telemetria | O sistema deve transmitir os dados do Micromouse para um sistema web durante a execução do desafio. | Must | | |
| RF16-S | Visualização da telemetria | O sistema web deve apresentar em tempo real o tipo do labirinto, o trajeto, o consumo de bateria, a velocidade média, o tempo de conclusão e o estado do desafio. | Must | | |
| RF17-S | Armazenamento dos resultados | O sistema deve armazenar em banco de dados os dados finais obtidos após a conclusão de cada desafio. | Must | | |
| RF18-S | Consulta por labirinto | O sistema web deve permitir consultar os dados correspondentes a um labirinto específico. | Must | | |
| RF19-S | Consulta geral | O sistema web deve permitir consultar os dados das execuções de todos os labirintos armazenados. | Must | | |
| RF20-S | Identificação do desafio | O sistema deve identificar o labirinto que está sendo executado para associar corretamente os dados de telemetria e os resultados armazenados. | Must | | |
| RF21-S | Estado do desafio | O sistema deve registrar se o Micromouse concluiu ou não o desafio com sucesso. | Must | | |
| RF22-S | Recuperação de informações | O sistema web deve permitir visualizar os dados registrados de uma execução após sua conclusão. | Should | | |

## 2. Requisitos Não-Funcionais (RNF)

### 2.1 Requisitos Não-Funcionais Estruturas

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RNF01-E | Dimensões máximas | A dimensão máxima do chassi não deve ultrapassar 12 cm x 12 cm | Must |                  |                          |
| RNF02-E | Manter a estabilidade do veículo | O veículo deve se manter estável durante todo o percurso | Should |                  |                          |
| RNF03-E | Manter a rigidez estrutural do veículo | O veículo deve manter a sua rigidez estrutural durante todo o percurso | Should |                  |                          |

### 2.2 Requisitos Não-Funcionais Hardware

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RNF01-H | Duração da bateria | A bateria deve fornecer energia suficiente para manter o Micromouse em operação contínua por no mínimo 30 minutos. | Should |                  |                          |
| RNF02-H | Tensão de operação | A alimentação dos componentes eletrônicos deve permanecer dentro das faixas de tensão especificadas pelos respectivos componentes durante a operação. | Must |                  |                          |
| RNF03-H | Frequência de leitura | Os sensores utilizados na navegação devem realizar leituras com frequência suficiente para permitir a correção da trajetória durante a movimentação. | Must |                  |                          |
| RNF04-H | Controle dos motores | O sistema de acionamento deve permitir variações de velocidade dos motores compatíveis com a precisão necessária para a navegação no labirinto. | Must |                  |                          |
| RNF05-H | Filtragem de sinais | Os sinais analógicos utilizados pelo sistema devem ser filtrados para atenuar ruídos de alta frequência durante a aquisição e processamento.  | Should |                  |                          |
| RNF06-H | Comunicação sem fio | O módulo de comunicação deve manter conexão suficiente para transmitir os dados de telemetria durante a execução do desafio.  | Must |                  |                          |
| RNF07-H | Fixação dos componentes | Os componentes eletrônicos, motores e sensores devem permanecer fixados em suas posições durante a movimentação do Micromouse.  | Must |                  |                          |


### 2.3 Requisitos Não-Funcionais Software

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RNF01-S | Tempo de execução | O sistema deve concluir cada desafio dentro do limite de 10 minutos estabelecido para a avaliação. | Must |  | |
| RNF02-S | Processamento em tempo adequado | O processamento das informações dos sensores e a tomada de decisões devem ser concluídos em até 15 ms. | Must |  | |
| RNF03-S | Atualização da telemetria | Os dados de telemetria devem ser atualizados durante a execução do Micromouse, permitindo o acompanhamento do desafio em tempo real. | Must |  | |
| RNF04-S | Confiabilidade dos sensores | O sistema deve tolerar pequenas variações e ruídos nas leituras dos sensores sem comprometer imediatamente o funcionamento da navegação. | Should |  | |
| RNF05-S | Compatibilidade com os labirintos | O sistema deve suportar os labirintos 4x4, 8x4 e 12x4. | Must |  | |
| RNF06-S | Segurança operacional | O Micromouse não deve executar comandos que resultem em colisão com uma parede conhecida. | Must |  | |
| RNF07-S | Eficiência computacional | O software deve utilizar recursos de memória e processamento compatíveis com o hardware de processamento escolhido para o Micromouse. | Must | | |
| RNF08-S | Testabilidade | Os principais componentes do sistema devem poder ser testados individualmente antes dos testes de integração com o Micromouse completo. | Should | | |
| RNF09-S | Consistência dos dados | Os dados armazenados no banco de dados devem corresponder aos dados produzidos durante a execução do desafio. | Must | | |
| RNF10-S | Usabilidade da interface | A interface web deve apresentar o estado atual do Micromouse, o trajeto, a velocidade, o nível da bateria e o tempo de execução em uma única tela durante o desafio. | Should | | |
| RNF11-S | Manutenibilidade | A organização do sistema deve permitir que seus componentes sejam modificados e mantidos individualmente sem exigir alterações desnecessárias nos demais componentes. | Should | | |