# Requisitos: conversor nbr2md

Origem: `docs/PLANO-CONVERSAO.md`, Seções 2 e 5. Cada critério de aceite de etapa vira um requisito.

## Requisitos gerais

- R1. O conversor converte normas técnicas brasileiras em PDF digital (com camada de texto) para Markdown, sem OCR e sem chamadas de API de modelo.
- R2. Todo texto normativo do PDF aparece no Markdown, sem paráfrase. A validação confere a cobertura palavra por palavra.
- R3. Marca d'água, cabeçalho, rodapé e CNPJ/número de pedido nunca aparecem em `normas/`.
- R4. Glifos sem Unicode nunca são adivinhados. Cada um entra em `mapa_glifos` por chave `(fonte, id do glifo)`, depois de conferido na imagem e no `(cid:N)` do pdfplumber.
- R5. A flag `TEXT_CID_FOR_UNKNOWN_UNICODE` do PyMuPDF fica desligada em todo o pipeline.
- R6. Saída em três formatos: arquivo único, arquivos por seção e `chunks.jsonl`, além de `termos.json`, `manifest.json` e `revisao.md`.
- R7. Descrições de figuras e transcrições de fórmulas são escritas pelo Kiro, marcadas `revisado_por: ia` e aplicadas pelo pipeline a partir de `config/<id>/revisoes.yaml`.

## Requisitos por etapa

- **Etapa 0.** `mise exec -- python -m nbr2md --help` funciona. Subcomandos: `converter`, `inspecionar`, `recortes`, `validar`, `todas`.
- **Etapa 1.** `docs/FORMATO-SAIDA.md` especifica o Markdown gerado (front matter, cabeçalhos, notas, listas, definições, tabelas, figuras, fórmulas, marcadores de página).
- **Etapa 2.** `config/defaults.yaml` com merge profundo sobre `config/<id>/norma.yaml`. Listas são concatenadas.
- **Etapa 3.** Extração de spans por página para `build/<id>/01-spans/`, com glifos sem Unicode casados pelo `get_texttrace()`. A extração da 5410 leva menos de 1 minuto. O JSON da p. 31 contém `Tabela 6`.
- **Etapa 4.** Limpeza na ordem fixa do plano. Nenhum resíduo de marca d'água, cabeçalho ou glifo quebrado nas 5410 e 5419. Os casos conhecidos da 5410 saem corretos (p. 17, 29, 35, 48 e 119). `glifos-desconhecidos.json` da 5410 lista 31 pares e 575 ocorrências. O das 5419 fica vazio.
- **Etapa 5.** Marcação inline: `<sub>`, `<sup>`, Unicode para unidades, negrito e itálico, notas de rodapé.
- **Etapa 6.** Blocos e classificação, com juntura entre páginas e tratamento de preliminares.
- **Etapa 7.** Tabelas GFM ou HTML, com continuação entre páginas, linhas de agrupamento e notas.
- **Etapa 8.** Figuras recortadas em PNG e fórmulas em LaTeX. Comando `recortes`.
- **Etapa 9.** Revisões em `revisoes.yaml`, com `revisado_por` e `hash_recorte`.
- **Etapa 10.** Árvore de seções, renderização, arquivos por seção, `chunks.jsonl`, `termos.json`, `manifest.json` e `normas/llms.txt`.
- **Etapa 11.** Validação com bloqueantes (cobertura PyMuPDF ≥ 99,5%, cobertura pdfplumber ≥ 99,0%, glifos, marcadores balanceados, caracteres proibidos, marca d'água/CNPJ, sumário contra árvore, notas de rodapé) e não bloqueantes (sequência de numeração, pendências, markdownlint).
- **Etapa 12 e 12a.** Processo para nova norma e para nova edição. A nova edição substitui a anterior, e `normas/<id>/` é regenerada por completo.

## Restrições

- Não baixar limites de validação nem remover texto para passar.
- Não alterar a saída de outra norma sem que os testes de regressão dela passem.
- Não fazer commit nem push. Apagar fora de `build/<id>/` e `normas/<id>/` só com confirmação.
