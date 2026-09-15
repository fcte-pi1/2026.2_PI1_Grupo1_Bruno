# Termo de Abertura do Projeto

> Termo de abertura do projeto / Project Charter. Um documento publicado pelo iniciador ou patrocinador do projeto que autoriza formalmente a existência de um projeto e fornece ao gerente do projeto a autoridade para aplicar os recursos organizacionais nas atividades do projeto.

## Visão Geral do Projeto

### Dados do projeto

- **Nome do Projeto:** MicroPreá
- **Data de Início:** 09/09/2026
- **Data de Término:** 20/11/2026
- **Patrocinador:** Universidade de Brasília


### Objetivos

> O que o grupo pretende obter com a realização do projeto. Descrever o que se pretende realizar para resolver o problema central ou explorar a oportunidade identificada. Para a correta definição do objetivo, siga a regra "SMART":

- **_Specific_ (específico):** Deve ser redigido de forma clara, concisa e compreensiva.
  
  O projeto tem como objetivo projetar, construir e programar um mini robô autônomo (mini rato) capaz de navegar e alcançar com sucesso a saída de 3 labirintos distintos, integrando o trabalho das equipes de software, hardware e estrutura.

- **_Measurable_ (mensurável):** O objetivo específico deve ser mensurável, ou seja, possível de ser medido por meio de um ou mais indicadores.
  
  O sucesso do projeto será mensurado por meio dos seguintes indicadores de desempenho:
  - **Taxa de conclusão dos labirintos:** Alcance da saída em 100% dos 3 labirintos distintos (3/3), sem necessidade de intervenção manual humana durante o percurso.
  - **Integração dos subsistemas:** Validação funcional completa das 3 frentes de trabalho (estrutura física funcional e dentro do gabarito, circuito elétrico/hardware sem falhas de alimentação e software executando o algoritmo de navegação).
  - **Confiabilidade:** Conclusão do percurso dentro de um tempo limite determinado pela disciplina em pelo menos 3 testes consecutivos para cada labirinto.

- **_Agreed_ (acordado):** Deve ser acordado com as partes interessadas, ou seja, as áreas envolvidas na empresa: P&D, Produção, Comercial, Marketing, Financeira, Jurídica, Manutenção, ambiental, entre outras.
  
  O escopo e os objetivos do projeto foram alinhados e consensuados entre as 3 frentes de trabalho da equipe (Software, Hardware e Estrutura), alocando responsabilidades claras para os 19 integrantes, e em concordância com os requisitos estabelecidos pelos professores e orientadores da disciplina.

- **_Realistic_ (realista):** Deve estar centrado na realidade, no que é possível de ser feito considerando as premissas e restrições existentes, como: orçamento e tempo.
  
  O objetivo é viável e atingível considerando as seguintes premissas e restrições:
  - **Divisão de trabalho eficiente:** A distribuição dos 19 integrantes em 3 subequipes especializadas (Software, Hardware e Estrutura) permite a execução de atividades em paralelo, otimizando o fluxo de desenvolvimento.
  - **Escopo focado:** A meta está delimitada à resolução de 3 labirintos com tecnologia adequada e acessível (sensores de navegação e algoritmos de mapeamento/desvio de obstáculos).
  - **Gestão da carga horária:** O cronograma e o nível de complexidade do robô consideram a rotina acadêmica dos estudantes e a dedicação concomitante a outras disciplinas da faculdade.

- **_Time Bound_ (limitado no tempo):** Deve ter um prazo determinado para sua finalização.
  
  O projeto tem como prazo final de entrega o dia **28 de novembro de 2026** e apresentação no dia **02 de dezembro de 2026**, com etapas intermediárias organizadas para garantir o cumprimento do cronograma diante das restrições de tempo da faculdade:
  - **Prazo Final:** Finalização completa do protótipo e testes de validação até dia 28/11.
  - **Marcos Intermediários (*Milestones*):**
    - **Fase 1:** Validação do design estrutural e escolha dos componentes de hardware.
    - **Fase 2:** Montagem do chassi e desenvolvimento inicial dos algoritmos de navegação (software).
    - **Fase 3:** Integração entre hardware, software e estrutura para testes práticos nos labirintos e ajustes finos até a data limite.
### Público-Alvo

> Pessoas, empresas, instituições etc. que podem usufruir dos produtos, serviços e resultados gerados pelo projeto, cujos requisitos (tópico abaixo) devem atender as suas necessidades. Podem ser internas ou externas à organização, mas, merecem destaque especial, pois, o projeto está sendo feito para atendê-los de forma direta ou indireta.

1. Professores Avaliadores da FCTE (Clientes do Projeto):
Atuam como os clientes diretos e principais stakeholders externos ao grupo. Eles são os responsáveis por definir os requisitos e restrições do desafio. Este público usufruirá do sistema web desenvolvido para realizar consultas no banco de dados e verificar, em tempo real, se o micromouse cumpriu os desafios e atingiu as metas de desempenho nos labirintos durante os testes de integração e a apresentação final.

2. Equipe de Desenvolvimento do Grupo (Usuários Internos)
Os próprios membros do grupo são um público-alvo direto do ecossistema criado. A equipe utilizará a pista simplificada de 4x4 desenvolvida para testes internos e será a principal usuária do sistema web para monitorar a telemetria do robô (trajeto, consumo de bateria, velocidade média e tempo de conclusão) durante a fase de construção e ajustes do micromouse.

### Descrição do Problema

> Informar o problema ou a oportunidade (necessidade) que justifica o porquê de o projeto ser realizado. Por exemplo: atende uma demanda específica do consumidor final; supre uma necessidade do mercado comercializador; é um diferencial X para o órgão regulamentador.

O projeto surge da oportunidade de solucionar um desafio clássico e global de robótica: a navegação autônoma em ambientes desconhecidos, inspirada nas competições de micromouse realizadas anualmente no mundo inteiro. O problema central consiste em criar um robô capaz de explorar, descobrir paredes, mapear trajetos e encontrar o objetivo final em labirintos de formatos não conhecidos previamente pelas equipes, operando de forma autônoma e sem qualquer intervenção humana.

Essa necessidade atende, em primeiro lugar, à demanda do consumidor final do projeto: os professores avaliadores da FCTE, que precisam de um meio confiável para verificar, em tempo real, se o robô cumpriu os desafios propostos. Para isso, é necessário capturar, transmitir e exibir os dados de telemetria do robô (trajeto no labirinto, consumo de bateria, velocidade média e tempo) por meio de um sistema web, além de armazená-los em um banco de dados que permita consultas estruturadas de desempenho.

### Indicadores

> Listar até 10 indicadores que determinam o mercado consumidor do produto desenvolvido: exemplo: 1) nº de alunos da FGA que utilizam ônibus às 18:00; 2) nº de usuários do restaurante universitários, 3) número de idosos classificados como público-alvo no DF e no estado de Goiás, 4) nº de empresas de segurança registradas no DF etc.

1) Número de instituições de ensino com cursos de Engenharia
2) Número de instituições de ensino com projetos ou laboratórios de robótica
3) Número de estudantes envolvidos com robótica e programação 
4) Número de competições e eventos de robótica realizados anualmente 
5) Número de equipes participantes de competições de robótica
### Membros da Equipe

| **Nome** | **Matrícula** | **Curso** | **E-mail** | **Funções** |
|----------|---------------|-----------|------------|-------------|
| Arthur Mezzaroba Scartezini | 241025176 | Engenharia de Software | ascartezini2005@gmail.com | Hardware |
| Arthur Miranda Silva | 251035971 | Engenharia de Software | arthurmirandas@outlook.com | Hardware |
| Carlos Henrique Brasil de Souza | 232014404 | Engenharia de Software | 232014404@aluno.unb.br | Hardware |
| Davi Monteiro de Negreiros | 232013971 | Engenharia de Software | dv.neg1711@gmail.com | Líder Geral |
| Frederico Rolim Walter | 231011373 | Engenharia Aeroespacial | frw1302@gmail.com | Estrutura |
| Gabriel Pinto Simplicio | 251035200 | Engenharia de Software | gabrielsimplicio043@gmail.com | Estrutura |
| Gabriella Orlando Avelino de Carvalho Veríssimo | 242004690 | Engenharia de Software | 242004690@aluno.unb.br | Estrutura |
| Guilherme Ferreira Mendes| 241025935 | Engenharia de Software | guilherme.jm2015@gmail.com | Hardware |
| Guilherme Negreiros Pereira | 232014001 | Engenharia de Software | negreiros.4k@gmail.com | Sub-líder de Software |
| Ian Pedersoli Barbosa| 241025944 | Engenharia de Software | ianpbarbosa@gmail.ccom | Hardware |
| João Marcelo Guimarães Costa Naves | 232014709 | Engenharia de Software | joaomarcelogcn@gmail.com | Hardware |
| João Paulo Oliveira César| 242004760 | Engenharia de Software | jp.oliveiracesar@gmail.com| Software |
| João Paulo Pires Silva | 251010909 | Engenharia de Software | joaopaulojppsa@gmail.com | Software |
| Kaio Amory Sasaki | 241012276 | Engenharia de Software | kaioamory8968@gmail.com | Hardware |
| Otávio De Paiva| 242004911| Engenharia de Software |otaviodepaivaa@gmail.com | Software |
| Paulo Renato Medrado Roque | 221035068 | Engenharia Automotiva | pmedrado15@gmail.com | Estrutura |
| Pietro Calegari Visentin | 232014754  | Engenharia de Software | pietrocvisentin@gmail.com | Software |
| Tamires Lima Araújo | 241037551 | Engenharia Aeroespacial | | Sub-líder de Estrutura|
| Yogi Nam de Souza Barbosa | 232014576 | Engenharia de Software | yogiqhz@gmail.com | Hardware |

**Orientador:** Bruno Luiz Pereira

### Orçamento estimado (R$)

Orçamento estimado de R$1020,00.

### Duração estimada (horas)

Duração estimada de 100 horas totais.















