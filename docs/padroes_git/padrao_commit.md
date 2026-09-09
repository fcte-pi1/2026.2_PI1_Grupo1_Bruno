# Padrão de Commit

Este projeto utiliza uma padronização inspirada em Conventional Commits para manter o histórico claro, rastreável e fácil de revisar.

## Formato

```text
tipo(escopo): descrição curta
```

O escopo é opcional, mas recomendado quando a alteração pertence a uma parte específica do projeto.

## Tipos

| Tipo | Uso |
| --- | --- |
| `feat` | Nova funcionalidade |
| `fix` | Correção de erro |
| `docs` | Alterações de documentação |
| `style` | Formatação, organização visual ou ajustes sem mudança de lógica |
| `refactor` | Refatoração sem alterar comportamento esperado |
| `test` | Criação ou ajuste de testes |
| `chore` | Tarefas de manutenção, configuração ou organização |
| `build` | Alterações em dependências, ferramentas de build ou empacotamento |
| `ci` | Alterações em integração contínua |

## Escopos Sugeridos

- `estrutura`
- `fse`
- `hardware`
- `telemetria`
- `docs`
- `git`
- `infra`

## Exemplos

```text
docs(git): adiciona padrão de commits
feat(telemetria): cria leitura inicial dos dados do robô
fix(firmware): corrige cálculo de velocidade dos motores
chore(repo): organiza estrutura inicial do projeto
```

## Boas Práticas

- Use o verbo no presente: `adiciona`, `corrige`, `remove`, `atualiza`.
- Faça commits pequenos e com uma única intenção.
- Evite mensagens genéricas como `ajustes`, `mudanças` ou `update`.
- Não misture alterações de áreas diferentes no mesmo commit quando puder separar.
- Quando houver uma issue relacionada, cite o identificador no corpo do commit ou na pull request.
