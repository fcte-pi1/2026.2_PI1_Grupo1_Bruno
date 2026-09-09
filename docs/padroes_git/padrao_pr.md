# Padrão de Pull Request

Toda pull request deve apresentar claramente o que foi alterado, por que a alteração foi feita e como ela foi verificada. O objetivo é facilitar a revisão e manter o histórico do projeto compreensível.

## Título

Use um título curto no mesmo estilo dos commits:

```text
tipo(escopo): descrição curta
```

## Exemplos de Título

```text
docs(git): adiciona padrões de contribuição
feat(telemetria): implementa painel inicial de dados
fix(firmware): corrige leitura do encoder
```

## Descrição Recomendada

```md
## Resumo

- Descreva brevemente o que foi feito.
- Informe quais partes do projeto foram alteradas.

## Motivação

Explique por que essa alteração é necessária.

## Como Testar

- Liste os passos usados para validar a alteração.
- Inclua comandos, simulações, imagens ou resultados quando fizer sentido.

## Checklist

- [ ] A alteração está focada em um único objetivo.
- [ ] O código ou documento foi revisado antes de abrir a PR.
- [ ] A documentação foi atualizada, se necessário.
- [ ] A alteração foi testada ou validada de alguma forma.
```

## Boas Práticas

- Abra a pull request com tamanho razoável para revisão.
- Evite misturar documentação, refatoração e funcionalidade na mesma PR sem necessidade.
- Explique decisões técnicas importantes na descrição.
- Marque pessoas do subgrupo responsável quando precisar de revisão específica.
- Inclua imagens, logs ou resultados quando a mudança envolver interface, telemetria, simulação ou comportamento físico do robô.

## Critérios Antes de Mesclar

- A PR deve ter uma descrição suficiente para outro membro entender a mudança.
- Comentários relevantes de revisão devem ser resolvidos.
- O projeto deve continuar funcionando conforme o esperado.
- Alterações de documentação devem apontar para arquivos e padrões atualizados.
