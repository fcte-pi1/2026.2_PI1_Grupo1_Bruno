# Padrão de Branch

As branches devem indicar claramente o tipo de trabalho e o assunto tratado. Isso facilita a organização do repositório e a revisão das alterações.

## Formato

```text
tipo/descricao-curta
```

Quando houver uma issue ou tarefa numerada, utilize:

```text
tipo/numero-descricao-curta
```

## Tipos

| Tipo | Uso |
| --- | --- |
| `feat` | Desenvolvimento de nova funcionalidade |
| `fix` | Correção de erro |
| `docs` | Alterações em documentação |
| `refactor` | Refatoração de código ou estrutura |
| `test` | Criação ou ajuste de testes |
| `chore` | Organização, configuração ou manutenção |
| `hotfix` | Correção urgente |

## Exemplos

```text
docs/padroes-git
feat/telemetria-inicial
fix/leitura-sensor-frontal
chore/estrutura-repositorio
feat/12-controle-motores
```

## Boas Práticas

- Use letras minúsculas.
- Separe palavras com hífen.
- Evite nomes longos demais.
- Crie branches a partir da branch principal atualizada.
- Mantenha cada branch focada em uma única entrega.
- Apague branches remotas após a pull request ser concluída, quando não forem mais necessárias.

## Branches Principais

| Branch | Finalidade |
| --- | --- |
| `main` | Versão principal e estável do projeto |
| `develop` | Integração de funcionalidades em desenvolvimento, se o grupo optar por usar fluxo com branch de desenvolvimento |

Caso o projeto use apenas `main`, todas as contribuições devem ser feitas por pull request a partir de branches específicas.
