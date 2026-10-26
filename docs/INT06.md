# INT06: Projects, rastreabilidade e responsabilidades

| Campo | Valor |
|---|---|
| Issue | [#26](https://github.com/fcte-pi1/2026.2_PI1_Grupo1_Bruno/issues/26) |
| Equipe | Integração |
| Prioridade | P1 |
| Quadro | [Project 31](https://github.com/orgs/fcte-pi1/projects/31) |
| Última atualização | 26/10/2026 |

O Project 31 reúne dois repositórios: os requisitos e tarefas de planejamento criados em `2026.1_PI1_Grupo01_Bruno` (75 itens) e as tarefas técnicas deste repositório (24 issues, #3 a #26). Nada do repositório antigo foi apagado, fechado ou renomeado: não temos permissão de escrita nele, e a issue pede que essas mudanças sejam propostas, não aplicadas.

## 1. O que foi feito no quadro

- As 24 issues deste repositório (#3 a #26) foram adicionadas ao Project 31.
- O campo **Status** passou a seguir o fluxo da issue. As opções antigas foram renomeadas mantendo o identificador interno, então nenhum item perdeu o status:

| Antes | Depois | Itens antigos |
|---|---|---|
| A Fazer | **Backlog** | 62 |
| Backlog do Sprint | **Pronto** | 0 |
| Em Progesso | **Em andamento** | 0 |
| Em Revisão | **Em revisão** | 0 |
| Fechado | **Validado** | 13 |
| Backlog do Produto, Em Inspeção | removidas (não eram usadas) | 0 |

- Campos novos: **Área** (Firmware, Telemetria, Integração, Software, Hardware, Estruturas, Labirinto, Documentação, Gestão) e **Tipo** (Requisito, Tarefa técnica, Documentação, Entrega). Os dois foram preenchidos nos 99 itens.
- Nas issues deste repositório, **Priority** (P0/P1/P2) e **Target date** foram copiados do campo "Prioridade" e do "Prazo sugerido" de cada issue. Prazos sem data ("Após 26/10") ficaram em branco.
- O backup do quadro anterior (itens e campos em JSON) foi guardado antes das alterações.

## 2. Regras de uso

| Status | Quando usar |
|---|---|
| Backlog | Ainda não planejado ou com dependência aberta |
| Pronto | Dependências resolvidas; qualquer responsável pode começar |
| Em andamento | Alguém está trabalhando; a issue tem responsável |
| Em revisão | PR aberto, ou PR integrado com validação pendente |
| Validado | Critérios de aceite conferidos e evidência registrada no PR ou na issue |

- **Requisito** é item de produto: as HUs e os RFs do repositório 2026.1 (#531 a #571). Eles não são fechados por PR; ficam em "Validado" quando todas as tarefas ligadas a eles estiverem validadas.
- **Tarefa técnica** é implementação: as issues FW, TEL e INT deste repositório. Todo PR cita a issue com `Closes #N` (ou `Refs #N`, se não a conclui) e informa a evidência: comando de teste, captura ou registro de bancada, deixando claro se o resultado é simulado, de bancada ou físico.
- **Fechar a issue leva o item para "Validado" automaticamente.** Se a validação física ainda depende de hardware, deixe a issue aberta em "Em revisão" e registre o que falta.
- Cada issue tem um responsável individual definido pela equipe. O revisor é outra pessoa da mesma frente, marcada no PR.

## 3. Rastreabilidade: requisitos, tarefas e PRs

Situação em 26/10/2026. HU e RF seguem o [backlog do produto](4.4%20-%20Projeto%20conceitual%20de%20software.md) e os [requisitos](2%20-%20Requisitos.md).

### 3.1 Histórias de usuário (requisitos de software)

| HU | Item no quadro (2026.1) | Tarefas (2026.2) | PRs |
|---|---|---|---|
| HU-01 Resolver o labirinto sem intervenção | #531 | FW12 #14, FW13 #15, FW08 #10 | #28 |
| HU-02 Executar os movimentos da rota | #532 | FW03 #5, FW05 #7, FW07 #9 | — |
| HU-03 Detectar a chegada à área objetivo | #533 | FW13 #15 | — |
| HU-04 Detectar paredes | #534 | FW06 #8 | — |
| HU-05 Atualizar a posição | #535 | FW04 #6, FW11 #13 | #31, #37 |
| HU-06 Manter a orientação | #536 | FW06 #8, FW11 #13 | #37 |
| HU-07 Construir o mapa | #537 | FW11 #13 | #37 |
| HU-08 Atualizar o mapa | #538 | FW11 #13 | #37 |
| HU-09 Planejar a rota | #539 | FW12 #14 | #28 |
| HU-10 Replanejar a rota | #540 | FW12 #14 | #28 |
| HU-11 Registrar o trajeto | #541 | FW11 #13, TEL03 #19, TEL04 #20 | #36, #37 |
| HU-12 Registrar a velocidade | #542 | FW04 #6, FW09 #11 | #31, #35 |
| HU-13 Registrar a bateria | #543 | FW14 #16 | #32 |
| HU-14 Cronometrar o desafio | #544 | FW13 #15, TEL02 #18 | #27 |
| HU-15 Identificar o labirinto | #545 | INT03 #23, FW13 #15 | #35 |
| HU-16 Registrar o resultado | #546 | FW13 #15, TEL03 #19 | #36 |
| HU-17 Transmitir a telemetria | #550 | FW09 #11, FW10 #12, TEL01 #17, INT03 #23 | #35 |
| HU-18 Acompanhar em tempo real | #551 | TEL02 #18, TEL04 #20 | #27 |
| HU-19 Estado da conexão | #552 | TEL02 #18 | #27 |
| HU-20 Armazenar o resultado | #553 | TEL03 #19 | #36 |
| HU-21 Consultar por labirinto | #554 | TEL03 #19 | #36 |
| HU-22 Consultar todos os labirintos | #555 | TEL03 #19 | #36 |
| HU-23 Rever uma execução | #556 | TEL03 #19, TEL04 #20 | #36 |

### 3.2 Requisitos de hardware e estrutura que estavam como "Software"

| Item (2026.1) | Requisito | Área no quadro | Tarefas (2026.2) |
|---|---|---|---|
| #557 Suportar e integrar os componentes | RF01-E | Estruturas | — (suporte físico) |
| #558 Percorrer a pista | RF02-E | Estruturas | — |
| #559 Proteger os componentes eletrônicos | RF03-E | Estruturas | — (proteção) |
| #560 Substituir e atualizar módulos | RF04-E | Estruturas | — |
| #561 Construir o percurso para testes | RF05-E | Estruturas | — (percurso) |
| #562 Mapear o percurso com sensores | RF01-H | Hardware | FW06 #8 |
| #563 Controlar a velocidade dos motores | RF02-H | Hardware | FW03 #5, FW05 #7 |
| #564 Comunicar sem fio | RF03-H | Hardware | FW10 #12 |
| #565 Informar o consumo da bateria | RF04-H | Hardware | FW14 #16 |
| #566 Movimentar por meio dos motores | RF05-H | Hardware | FW03 #5 |
| #567 Centralizar nos corredores | RF06-H | Hardware | FW07 #9 |
| #568 Rotações de 90° e 180° | RF07-H | Hardware | FW07 #9 |
| #569 Iniciar e interromper por botão | RF08-H | Hardware | FW08 #10 |
| #570 Emitir alarme na área objetivo | RF09-H | Hardware | **nenhuma** |
| #571 Operar por 30 minutos | RNF01-H | Hardware | INT05 #25 |

### 3.3 Tarefas de base sem requisito direto

FW01 #3 e FW02 #4 (projeto MicroPython, HAL e simuladores, PR #38), INT01 #21 (stack), INT02 #22 (pinagem, PR #34), INT04 #24 (entrega de 26/10) e INT06 #26 (este documento) sustentam as demais tarefas.

## 4. Propostas para o repositório 2026.1

Estas mudanças precisam de alguém com permissão de escrita no repositório antigo. Nenhuma foi aplicada.

1. **Duplicados.** #547, #548 e #549 repetem #544 (HU-14), #545 (HU-15) e #546 (HU-16). Os itens #544 a #546 seguem a sequência das HUs (#531 a #556), então a proposta é manter #544, #545 e #546, comentar nos duplicados apontando para eles e fechá-los como "not planned" depois que a equipe concordar.
2. **Reclassificação.** #557 a #561 são requisitos de estrutura (RF01-E a RF05-E) e #562 a #571 são de hardware (RF01-H a RF09-H e RNF01-H), mas todos começam com "Software:". No quadro, o campo Área já mostra a frente correta. A proposta é trocar o prefixo do título para "Estruturas:" e "Hardware:", mantendo o número para preservar a rastreabilidade.
3. **Datas impossíveis.** Itens que terminam antes de começar: #534 (09/10 → 02/10), #535 (09/10 → 03/10), #539 (09/10 → 07/10) e #582 (27/10 → 04/10). Os responsáveis precisam informar as datas corretas.

## 5. Pendências

- **#570 (alarme ao chegar ao objetivo, RF09-H, Could)** não tem tarefa técnica. Se a equipe mantiver o requisito, criar uma tarefa de firmware ligada à FW13 #15.
- O campo **Sprint** não tem iterações configuradas; os prazos estão em **Target date**.
- Revisar o filtro das visualizações que usavam as opções antigas de Status. Por exemplo, a visualização "Backlog do Produto" filtrava `status:"Backlog do Produto"`, opção que deixou de existir. O filtro equivalente agora é `tipo:Requisito`.
- Responsáveis e revisores: as issues #3 a #26 já têm responsável atribuído; os revisores devem ser marcados em cada PR.
