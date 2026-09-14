# Requisitos

**Requisitos** definem o que um sistema deve fazer e sob quais restrições.

Requisitos relacionados com a primeira parte dessa definição — "o que um sistema deve fazer", ou seja, suas funcionalidades — são chamados de **Requisitos Funcionais**.

Já os requisitos relacionados com a segunda parte — "sob que restrições" — são chamados de **Requisitos Não-Funcionais**.

> - Descrever os requisitos funcionais (RF) em alto nível (Épico);
> - Descrever os requisitos não-funcionais (RNF) de forma objetiva;
> - Ao descrever os requisitos (RF e RNF), usar a classificação MoSCoW (*Must have*, *Should have* e *Could have*), para auxiliar a priorização.

---

## Requisitos Funcionais (RF)

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RF01 | Navegação autônoma | O Micromouse deve percorrer o labirinto de forma autônoma, sem intervenção humana durante a execução normal do desafio. | Must | Otávio Teixeira | |
| RF02 | Detecção de paredes | O sistema deve detectar a existência de paredes ao redor do Micromouse durante sua movimentação. | Must | Otávio Teixeira | |
| RF03 | Monitoramento da localização | O sistema deve determinar e atualizar a localização do Micromouse durante a execução do desafio. | Must | Otávio Teixeira | |
| RF04 | Monitoramento da orientação | O sistema deve determinar a orientação atual do Micromouse para auxiliar sua navegação pelo labirinto. | Must | Otávio Teixeira | |
| RF05 | Mapeamento do labirinto | O sistema deve construir uma representação do labirinto a partir das paredes descobertas durante a execução. | Must | Otávio Teixeira | |
| RF06 | Atualização do mapa | O sistema deve atualizar o mapa do labirinto sempre que novas informações sobre paredes e caminhos forem obtidas. | Must | Otávio Teixeira | |
| RF07 | Planejamento de rota | O sistema deve determinar um caminho entre a posição atual do Micromouse e a área objetivo utilizando as informações conhecidas do labirinto. | Must | Otávio Teixeira | |
| RF08 | Replanejamento da rota | O sistema deve atualizar o caminho planejado quando novas informações sobre o labirinto tornarem a rota anterior inadequada. | Must | Otávio Teixeira | |
| RF09 | Controle de movimentação | O sistema deve executar os movimentos necessários para que o Micromouse percorra o caminho planejado. | Must | Otávio Teixeira | |
| RF10 | Detecção do objetivo | O sistema deve detectar quando o Micromouse alcançar a área objetivo do labirinto. | Must | Otávio Teixeira | |
| RF11 | Registro do trajeto | O sistema deve registrar o trajeto percorrido pelo Micromouse durante a resolução do labirinto. | Must | Otávio Teixeira | |
| RF12 | Monitoramento da velocidade | O sistema deve obter e registrar os dados necessários para calcular a velocidade média do Micromouse durante o desafio. | Must | Otávio Teixeira | |
| RF13 | Monitoramento da bateria | O sistema deve obter e registrar informações referentes ao consumo ou nível da bateria durante a execução. | Must | João Paulo Cesar | |
| RF14 | Contagem do tempo | O sistema deve registrar o tempo decorrido durante a resolução de cada desafio e o tempo de conclusão. | Must | João Paulo Cesar | |
| RF15 | Telemetria | O sistema deve transmitir os dados do Micromouse para um sistema web durante a execução do desafio. | Must | João Paulo Cesar | |
| RF16 | Visualização da telemetria | O sistema web deve apresentar em tempo real o tipo do labirinto, o trajeto, o consumo de bateria, a velocidade média, o tempo de conclusão e o estado do desafio. | Must | João Paulo Cesar | |
| RF17 | Armazenamento dos resultados | O sistema deve armazenar em banco de dados os dados finais obtidos após a conclusão de cada desafio. | Must | João Paulo Cesar | |
| RF18 | Consulta por labirinto | O sistema web deve permitir consultar os dados correspondentes a um labirinto específico. | Must | João Paulo Cesar | |
| RF19 | Consulta geral | O sistema web deve permitir consultar conjuntamente os dados dos labirintos executados. | Must | João Paulo Cesar | |
| RF20 | Suporte aos labirintos | O sistema deve operar nos três formatos de labirinto definidos no projeto: 4x4, 8x4 e 12x4 células. | Must | João Paulo Cesar | |
| RF21 | Identificação do desafio | O sistema deve identificar o labirinto que está sendo executado para associar corretamente os dados de telemetria e os resultados armazenados. | Should | João Paulo Cesar | |
| RF22 | Estado do desafio | O sistema deve registrar se o Micromouse concluiu ou não o desafio com sucesso. | Must | João Paulo Cesar | |
| RF23 | Recuperação de informações | O sistema web deve permitir visualizar os dados registrados de uma execução após sua conclusão. | Should | João Paulo Cesar | |
| RF24 | Teste do sistema | O sistema deve permitir a realização de testes em uma pista 4x4 simplificada com condições análogas às do desafio. | Must | João Paulo Cesar | |

---

## Requisitos Não-Funcionais (RNF)

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| RNF01 | Limite de dimensões | O Micromouse não deve exceder 16,5 cm de comprimento ou 16,5 cm de largura. | Must | Otávio Teixeira | |
| RNF02 | Tempo de execução | O sistema deve permitir a resolução de cada desafio dentro do limite de 10 minutos estabelecido para a avaliação. | Must | Otávio Teixeira | |
| RNF03 | Processamento em tempo adequado | O processamento das informações dos sensores e a tomada de decisões devem ocorrer sem impedir a movimentação do Micromouse durante o desafio. | Must | Otávio Teixeira | |
| RNF04 | Atualização da telemetria | Os dados de telemetria devem ser atualizados durante a execução do Micromouse, permitindo o acompanhamento do desafio em tempo real. | Must | Otávio Teixeira | |
| RNF05 | Confiabilidade dos sensores | O sistema deve tolerar pequenas variações e ruídos nas leituras dos sensores sem comprometer imediatamente o funcionamento da navegação. | Should | Otávio Teixeira | |
| RNF06 | Integridade do mapa | Quando uma parede for registrada entre duas células adjacentes, essa informação deve permanecer consistente na representação das duas células. | Must | Otávio Teixeira | |
| RNF07 | Compatibilidade com os labirintos | O sistema deve suportar os labirintos 4x4, 8x4 e 12x4 sem exigir uma implementação independente da solução de navegação para cada formato. | Must | Otávio Teixeira | |
| RNF08 | Segurança operacional | O Micromouse não deve executar comandos que resultem deliberadamente em colisão com uma parede conhecida. | Must | Otávio Teixeira | |
| RNF09 | Integridade durante a execução | O código e a memória referentes ao labirinto não devem ser alterados externamente durante a resolução do trajeto. | Must | Otávio Teixeira | |
| RNF10 | Compatibilidade física | O Micromouse deve operar dentro das dimensões e características físicas dos labirintos utilizados no projeto. | Must | João Paulo Cesar | |
| RNF11 | Eficiência computacional | O software deve utilizar recursos de memória e processamento compatíveis com o hardware de processamento escolhido para o Micromouse. | Must | João Paulo Cesar | |
| RNF12 | Separação de responsabilidades | Os componentes de sensores, localização, mapeamento, navegação, controle, telemetria e armazenamento devem possuir responsabilidades definidas e separadas. | Should | João Paulo Cesar | |
| RNF13 | Testabilidade | Os principais componentes do sistema devem poder ser testados individualmente antes dos testes de integração com o Micromouse completo. | Should | João Paulo Cesar | |
| RNF14 | Consistência dos dados | Os dados armazenados no banco de dados devem corresponder aos dados produzidos durante a execução do desafio. | Must | João Paulo Cesar | |
| RNF15 | Usabilidade da interface | A interface web deve apresentar os dados de telemetria de forma organizada, permitindo identificar a situação atual do Micromouse durante a execução. | Should | João Paulo Cesar | |
| RNF16 | Segurança do labirinto | O Micromouse não deve causar danos ao labirinto durante sua operação. | Must | João Paulo Cesar | |
| RNF17 | Manutenibilidade | A organização do sistema deve permitir que seus componentes sejam modificados e mantidos individualmente sem exigir alterações desnecessárias nos demais componentes. | Should | João Paulo Cesar | |
| RNF18 | Documentação | Os componentes e interfaces desenvolvidos pela equipe devem possuir documentação suficiente para permitir a integração e manutenção do projeto. | Should | João Paulo Cesar | |

---

## Restrições do Projeto

As restrições abaixo são condições definidas para o desenvolvimento e execução do projeto e não representam funcionalidades do sistema.

- O Micromouse deve resolver os labirintos de forma autônoma.
- O primeiro labirinto possui 4x4 células e dimensões de 72 x 72 cm.
- O segundo labirinto possui 8x4 células e dimensões de 144 x 72 cm.
- O terceiro labirinto possui 12x4 células e dimensões de 216 x 72 cm.
- Cada célula possui 18 cm de lado, incluindo a espessura das paredes.
- As paredes possuem 5 cm de altura e 1,2 cm de espessura.
- O chão do labirinto é preto e as paredes são brancas com topos vermelhos.
- O Micromouse começa em um beco sem saída localizado em um canto do labirinto.
- A área objetivo está localizada no canto diametralmente oposto ao início.
- O Micromouse não pode exceder 16,5 cm de comprimento ou largura.
- Não são permitidos voo, salto, escalada, propulsão por combustão ou foguete.
- Intervenções humanas durante a corrida não são permitidas, exceto em situações previstas no regulamento, como mau funcionamento ou colisão.
- O código e a memória sobre o labirinto não podem ser alterados durante a resolução do trajeto.
- A equipe deve desenvolver uma pista 4x4 simplificada para testes.
- O projeto deve utilizar um repositório no GitHub e o GitHub Projects conforme o padrão definido pela disciplina.
- As tarefas devem ser acompanhadas por meio de issues e sub-issues.
- O sistema deve ser desenvolvido pela própria equipe, sem utilização de uma solução pronta que substitua o desenvolvimento proposto.

---

## Observações

A classificação MoSCoW foi utilizada para priorizar os requisitos:

- **Must:** requisito obrigatório para o funcionamento ou atendimento das exigências principais do projeto.
- **Should:** requisito importante, mas que pode ser tratado posteriormente caso exista alguma restrição de implementação.
- **Could:** requisito desejável, que pode ser implementado caso haja disponibilidade de tempo e recursos.
- **Won't:** requisito que não fará parte do escopo da versão atual.

Os requisitos devem permanecer em alto nível. Decisões específicas de implementação, como a escolha de sensores, microcontrolador, protocolo de comunicação ou algoritmo de resolução do labirinto, devem ser definidas posteriormente no projeto conceitual de hardware e software.