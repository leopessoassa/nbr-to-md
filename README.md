# nbr-to-md
conversao das Normas Técnicas Brasileira (NBRs) em Markdown (md)

# para rodar o python através do mise
# mise exec -- python __COMANDO__

## Como converter uma norma

Todos os comandos rodam pelo mise (`mise exec -- python -m ...`). Python 3.12 é gerenciado pelo mise.

```bash
mise exec -- python -m pip install -e ".[dev]"     # instalação, uma vez
mise exec -- python -m nbr2md converter nbr-5410   # converte (saídas em normas/nbr-5410/)
mise exec -- python -m nbr2md validar nbr-5410     # valida e grava normas/nbr-5410/revisao.md
mise exec -- python -m nbr2md recortes nbr-5410    # gera recortes de figuras para descrição
mise exec -- python -m pytest -q                   # testes
```

O PDF de cada norma fica em `nbr/<número>/`. A configuração fica em `config/<id>/norma.yaml` (ajustes da norma) e `config/defaults.yaml` (regras para todas as NBRs).

### O que sai em `normas/<id>/`

- `<id>.md`: arquivo único com todo o texto da norma.
- `secoes/`: um arquivo por seção de primeiro nível e por anexo.
- `chunks.jsonl`: um registro por cláusula, para RAG.
- `termos.json`: definições da Seção 3.
- `manifest.json`: metadados e contagens.
- `revisao.md`: pendências e alertas da validação.
- `assets/`: recortes PNG de figuras, fórmulas e símbolos.

`normas/llms.txt` lista todas as normas convertidas.

### Pendências de revisão

Itens que o pipeline não resolve aparecem com uma tag e `PENDENTE:`. Para localizar tudo, busque no repositório:

- `[imagem]` com `PENDENTE:`: descrição de figura não escrita;
- `[simbolo]`: símbolo em frase, não transcrito;
- `[rodape]`: nota de rodapé sem definição localizada no PDF.

As descrições de figuras escritas por IA aparecem com `[imagem]` e ficam em `config/<id>/revisoes.yaml` com `revisado_por: ia`. Depois da revisão humana, o marcador vira `[imagem revisada]`.

### Regras de documentação

- A especificação do formato está em `docs/FORMATO-SAIDA.md`.
- O plano de implementação está em `docs/PLANO-CONVERSAO.md`.
- Não há commit automático. O dono do repositório faz o commit.
