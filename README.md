# Projeto Micromouse

Este repositório reúne a documentação, organização e padrões de desenvolvimento do projeto Micromouse. O objetivo do projeto é construir um robô autônomo capaz de explorar, mapear e solucionar labirintos, utilizando integração entre mecânica, eletrônica, controle, firmware, software embarcado e telemetria.

## Sobre o Projeto

O Micromouse será desenvolvido de forma modular, permitindo que os subgrupos trabalhem em paralelo com responsabilidades bem definidas. A documentação deste repositório serve como base comum para manter decisões técnicas, padrões de contribuição e informações da equipe centralizadas.

## Membros

| **Nome** | **Matrícula** | **Curso** | **Funções** |
|---|---|---|---|
| Arthur Mezzaroba Scartezini | 241025176 | Engenharia de Software | Hardware |
| Arthur Miranda Silva | 251035971 | Engenharia de Software | Hardware |
| Carlos Henrique Brasil de Souza | 232014404 | Engenharia de Software | Hardware |
| Davi Monteiro de Negreiros | 232013971 | Engenharia de Software | Líder Geral |
| Frederico Rolim Walter | 231011373 | Engenharia Aeroespacial | Estrutura |
| Gabriel Pinto Simplicio | 251035200 | Engenharia de Software | Estrutura |
| Gabriella Orlando Avelino de Carvalho Veríssimo | 242004690 | Engenharia de Software | Estrutura |
| Guilherme Ferreira Mendes | 241025935 | Engenharia de Software | Hardware |
| Guilherme Negreiros Pereira | 232014001 | Engenharia de Software | Sub-líder de Software |
| Ian Pedersoli Barbosa | 241025944 | Engenharia de Software | Hardware |
| João Marcelo Guimarães Costa Naves | 232014709 | Engenharia de Software | Hardware |
| João Paulo Oliveira César | 242004760 | Engenharia de Software | Software |
| João Paulo Pires Silva | 251010909 | Engenharia de Software | Software |
| Kaio Amory | 241012276 | Engenharia de Software | Hardware |
| Otávio de Paiva Menezes Teixeira | 242004911 | Engenharia de Software | Software |
| Paulo Renato Medrado Roque | 221035068 | Engenharia Automotiva | Estrutura |
| Pietro Calegari Visentin | 232014754 | Engenharia de Software | Software |
| Tamires Lima Araújo | 241037551 | Engenharia Aeroespacial | Sub-líder de Estrutura |
| Yogi Nam de Souza Barbosa | 232014576 | Engenharia de Software | Hardware |

**Orientador:** Bruno Luiz Pereira

## Subgrupos Sugeridos

- Estrutura
- Hardware
- Software

## Documentação

Os padrões de colaboração do projeto estão descritos nos arquivos abaixo:

- [Padrão de Commit](docs/padroes_git/padrao_commit.md)
- [Padrão de Branch](docs/padroes_git/padrao_branch.md)
- [Padrão de Pull Request](docs/padroes_git/padrao_pr.md)

## Organização Recomendada

- Registrar decisões importantes em arquivos Markdown dentro de `docs`.
- Manter nomes de branches, commits e pull requests padronizados.
- Separar alterações por contexto para facilitar revisão e histórico.
- Atualizar a documentação sempre que houver mudança relevante no projeto.

## Conectar a placa

Para a **ESP32-S3-DevKitC-1 N8R2**, siga o [passo a passo de bancada](src/firmware/CONEXAO_ESP32_S3.md). O primeiro teste usa USB para carregar o código e Wi-Fi para chegar ao painel, sem sensores nem motores.

## Status

O [contrato v1 de telemetria e comandos](docs/protocolo/README.md) integra o
[painel e receptor Python](src/telemetria/README.md) ao emissor
[serial](src/firmware/TELEMETRY.md) ou [Wi-Fi/TCP](src/firmware/WIFI.md).
Há fontes simuladas, captura/reprodução e testes sem hardware. A validação
na ESP32 e no robô permanece pendente; veja as [evidências](docs/protocolo/VALIDACAO.md).
