---
inclusion: fileMatch
fileMatchPattern: 'normas/**/*.md'
---

# Formato de saída das normas

Ao editar ou ler um Markdown em `normas/`, siga a especificação completa abaixo.

#[[file:docs/FORMATO-SAIDA.md]]

Pontos que não podem ser quebrados:

- Texto normativo nunca é parafraseado. Correção só via `correcoes_texto` em `config/<id>/revisoes.yaml`.
- `[imagem]`, `[formula]`, `[simbolo]` e `[rodape]` são gerados pelo pipeline. Não escreva esses marcadores à mão no Markdown gerado.
- `[imagem]` e `[formula]` abertos sem `revisada` são pendentes de revisão humana.
