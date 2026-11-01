# Design: conversor nbr2md

Origem: `docs/PLANO-CONVERSAO.md`, Seções 2, 3, 4 e 5.

## Abordagem

Regras determinísticas sobre PyMuPDF, sem modelo de ML. O pdfplumber é um segundo extrator independente, usado só na validação e no diagnóstico de glifos. O MarkItDown foi avaliado e descartado.

Pipeline:

```
PDF
 → extrair.py   spans por página (build/<id>/01-spans/)
 → limpar.py    marca d'água, cabeçalho/rodapé, glifos, espaços (build/<id>/02-limpo/)
 → inline.py    sub/sup, negrito, itálico, notas de rodapé
 → blocos.py    agrupamento em blocos, tipos, juntura entre páginas (classificar.py)
 → tabelas.py   tabelas GFM/HTML
 → figuras.py / formulas.py   recortes e fórmulas
 → revisoes.py  aplica config/<id>/revisoes.yaml
 → estrutura.py árvore de seções (build/<id>/04-arvore.json)
 → renderizar.py / chunks.py   normas/<id>/
 → validar.py   normas/<id>/revisao.md, código ≠ 0 em bloqueante
```

## Estrutura de pacotes

```
src/nbr2md/   __init__, __main__, cli, config, modelo, extrair, limpar, inline,
              blocos, classificar, tabelas, figuras, formulas, estrutura,
              revisoes, renderizar, chunks, validar
config/       defaults.yaml, <id>/norma.yaml, <id>/revisoes.yaml
tests/        conftest.py, fixtures/<id>/, test_*.py
build/        intermediários (no .gitignore)
normas/       saída versionada
```

## Representação intermediária (`modelo.py`)

Dataclasses serializáveis em JSON:

- `Span`: texto, fonte, tamanho, negrito, itálico, bbox, origem_y (baseline), direção, `glifos_sem_unicode`.
- `Linha`: spans, bbox, página.
- `Bloco`: id (ex.: `p053-b007`), tipo, página, páginas, bbox, texto_md, número, extra.
- `No`: número, título, nível, blocos, filhos.

## Decisões importantes

- **Glifos.** Extração com `rawdict` e sem `TEXT_CID_FOR_UNKNOWN_UNICODE`, para que glifos sem mapeamento venham como `U+FFFD`. Cada um é casado com `get_texttrace()` pela origem do caractere. A chave do mapa é `(fonte sem prefixo de subconjunto, id do glifo)`, e não o caractere devolvido, que pode ser uma letra ASCII falsa.
- **Configuração.** `defaults.yaml` com merge profundo. Listas são concatenadas.
- **Revisões.** Descrições de figuras e fórmulas são escritas pelo Kiro e gravadas em `revisoes.yaml`. O pipeline só lê. Marcadores: `[imagem]`/`[formula]` enquanto `revisado_por: ia`; `[imagem revisada]`/`[formula revisada]` quando `humano`.
- **Idempotência.** Duas conversões seguidas produzem a mesma saída. Nenhuma chamada externa no pipeline.
- **Regeneração.** `normas/<id>/` é apagada e refeita por completo, sempre confinada ao caminho `normas/`.

## Validação

Tabela de verificações do plano (Etapa 11). Os limites são fixos no código e não são afrouxados para passar. Se um limite parecer errado, o caso é reportado com números.
