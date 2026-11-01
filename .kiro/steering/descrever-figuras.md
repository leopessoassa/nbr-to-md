---
inclusion: manual
---

# Descrever figuras e fórmulas (Etapa 9)

Use quando o usuário pedir para descrever figuras pendentes de uma norma.

## Fluxo

1. `mise exec -- python -m nbr2md recortes <id>` gera `build/<id>/recortes/*.png` e `pendencias.yaml` (número, página, legenda, rótulos, hash).
2. Abra cada PNG pendente com a ferramenta de leitura de imagem. Use a legenda e os rótulos como apoio. Trabalhe em lotes de até 10 figuras.
3. Grave cada item em `config/<id>/revisoes.yaml` com:
   - `arquivo`, `hash_recorte` (copie de `pendencias.yaml`), `descricao` e, se for fluxograma, `mermaid`;
   - `revisado_por: ia`.
4. Reconverta (`converter <id>`) e valide.

## Regras

- Nunca grave `revisado_por: humano`. Só o dono do repositório faz isso.
- Descreva o que a figura mostra, de forma objetiva. Não acrescente requisito nem interpretação normativa.
- Fluxograma: Mermaid `flowchart`, com o texto de cada nó idêntico ao da figura.
- Esquema elétrico: condutores, ligações, aterramentos e massas, da esquerda para a direita.
- Gráfico: eixos, unidades, curvas e pontos legíveis. Sem valor numérico que não esteja na figura.
- Fórmula: LaTeX exato, conferindo cada índice e expoente contra a imagem.
- Se a figura estiver ilegível, grave `descricao` começando com `PENDENTE:` e o motivo, em vez de inventar.
- Se o `hash_recorte` não bater com o PNG atual, o item volta a pendente. Atualize o hash ao redescrever.
- Os marcadores `[imagem]` e `[formula]` são gerados pelo pipeline. Não os escreva à mão.
