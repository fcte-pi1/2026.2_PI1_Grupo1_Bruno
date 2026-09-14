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
| RF01 | Suportar e integrar os componentes | A estrutura do micromouse deve ser capaz de suportar e integrar todos os componentes necessários para a operação do carrinho | must |                  |                          |
| RF02 | Percorrer a pista | A estrutura deve permitir que o micromouse percorra o caminho sem interferências, respeitando limites de altura, largura e mobilidade | must |                  |                          |
| RF03 | Proteger componentes eletrônicos | A estrutura deve proteger os componentes eletrônicos contra possíveis danos durante os testes e o percurso durante a avaliação | should |                  |                          |
| RF04 | Substituir e atualizar módulos | A estrutura deve permitir a substituição e atualização de módulos de forma independente | should |                  |                          |
| RF05 | construir percurso para testes | O projeto deve conter um protótipo de percurso construído para os testes do micromouse | |                  |                          |
| RF06 | | | |                  |                          |
| RF07 | | | |                  |                          |
| RF08 | | | |                  |                          |
| RF09 | | | |                  |                          |
| 10 | | | |                  |                          |

### 1.2 Requisitos de Hardware

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| 1 | Mapear o percurso | O circuito deve detectar presença ou ausência de paredes nas direções frontal, lateral esquerda, lateral direita do micromouse | must |                  |                          |
| 2 | Controlar velocidade | O circuito deve controlar individualmente a velocidade de cada motor DC por meio de sinal PWM enviado ao driver de motor | must |                  |                          |
| 3 | Comunicar sem fio | O circuito deve incluir um módulo de comunicação sem fio para transmitir em tempo real os dados do robô para o sistema web | must |                  |                          |
| 4 | Informar consumo de bateria | O circuito deve detectar e sinalizar informações sobre o consumo da bateria em tempo real | must |                  |                          |
| 5 | movimentar micromouse | O robô deve possuir motores e rodas controláveis adequados para percorrer o trajeto | must |                  |                          |
| 6 | centralizar micromouse | O sistema deve mover o micromouse em linha reta dentro dos corredores do labirinto, mantendo a trajetória centralizada entre as paredes da trajetória | must |                  |                          |
| 7 | Executar rotações | O sistema deve executar curvas de 90° e 180° de maneira precisa | |                  |                          |
| 8 | Iniciar e nterromper navegação | O sistema deve iniciar e interromper a navegação por meio de um botão físico acessível externamente no micromouse | should |                  |                          |
| 9 | Emitir alarme | O sistema deve acionar um alarme ao detectar que o micromouse atingiu a sala objetivo do labirinto | could |                  |                          |
| 10 | Transmitir dados de telemetria | O sistema deve transmitir dados de telemtria ao sistema web em tempo real | must |                  |                          |

### 1.3 Requisitos de Software

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| 1 | | | |                  |                          |
| 2 | | | |                  |                          |
| 3 | | | |                  |                          |
| 4 | | | |                  |                          |
| 5 | | | |                  |                          |
| 6 | | | |                  |                          |
| 7 | | | |                  |                          |
| 8 | | | |                  |                          |
| 9 | | | |                  |                          |
| 10 | | | |                  |                          |

## 2. Requisitos Não-Funcionais (RNF)

### 2.1 Requisitos Não-Funcionais Estruturas

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| 1 | | | |                  |                          |
| 2 | | | |                  |                          |
| 3 | | | |                  |                          |
| 4 | | | |                  |                          |
| 5 | | | |                  |                          |
| 6 | | | |                  |                          |
| 7 | | | |                  |                          |
| 8 | | | |                  |                          |
| 9 | | | |                  |                          |
| 10 | | | |                  |                          |

### 2.2 Requisitos Não-Funcionais Hardware

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| 1 | | | |                  |                          |
| 2 | | | |                  |                          |
| 3 | | | |                  |                          |
| 4 | | | |                  |                          |
| 5 | | | |                  |                          |
| 6 | | | |                  |                          |
| 7 | | | |                  |                          |
| 8 | | | |                  |                          |
| 9 | | | |                  |                          |
| 10 | | | |                  |                          |

### 2.3 Requisitos Não-Funcionais Software

| **ID** | **Nome do Requisito** | **Descrição** | **Prioridade** | **Responsáveis** | **Link Github Projects** |
|:------:|------------------------|---------------|:--------------:|------------------|--------------------------|
| 1 | | | |                  |                          |
| 2 | | | |                  |                          |
| 3 | | | |                  |                          |
| 4 | | | |                  |                          |
| 5 | | | |                  |                          |
| 6 | | | |                  |                          |
| 7 | | | |                  |                          |
| 8 | | | |                  |                          |
| 9 | | | |                  |                          |
| 10 | | | |                  |                          |
