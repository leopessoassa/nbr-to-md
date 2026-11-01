# Produto: conversão de NBRs para Markdown

Este projeto converte normas técnicas brasileiras (ABNT NBR), em PDF digital, para Markdown. O público são IAs e sistemas de RAG que precisam citar cláusulas com precisão.

## Princípios

- **Nada se perde.** Todo texto normativo do PDF aparece no Markdown. A validação de cobertura (Etapa 11 do plano) confere isso palavra por palavra.
- **Texto da norma não é reescrito.** Nada é parafraseado, resumido ou "corrigido" por estilo. Correção de texto só entra por `correcoes_texto` em `config/<id>/revisoes.yaml`, e só para defeito de extração comprovado pela imagem da página.
- **Figuras e fórmulas que não viram texto** recebem imagem recortada e descrição escrita pelo Kiro. Essa descrição fica marcada como não revisada (`[imagem]`, `[formula]`) até uma pessoa revisar.
- **Rastreabilidade.** Cada bloco guarda a página de origem (`<!-- p. N -->`).
- **Sem dados do licenciado.** Marca d'água, CNPJ e número de pedido nunca aparecem em `normas/`.

## Saídas por norma

- arquivo único (`normas/<id>/<id>.md`);
- arquivos por seção (`normas/<id>/secoes/`);
- `chunks.jsonl` para RAG, com um registro por cláusula;
- `termos.json`, `manifest.json` e `revisao.md`.

Plano completo: `docs/PLANO-CONVERSAO.md`.
