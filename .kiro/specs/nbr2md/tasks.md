# Tarefas: conversor nbr2md

Ordem da Seção 7 do plano. Cada tarefa tem o critério de aceite da etapa correspondente em `docs/PLANO-CONVERSAO.md`.

## Marco M0

- [x] **Etapa 0.** Preparação: `pyproject.toml`, `mise.toml`, `.gitignore`, CLI com `--help`.
- [x] Steerings `produto.md` e `tecnologia.md`.

## Marco M1

- [ ] **Etapa 1.** `docs/FORMATO-SAIDA.md` (revisado pelo dono do repositório).
- [ ] **Etapa 2.** `config.py`, `config/defaults.yaml`, `config/nbr-5410/norma.yaml`. Teste de merge.
- [ ] **Etapa 3.** `extrair.py`. Spans, imagens, desenhos e tabelas por página. Glifos sem Unicode via `get_texttrace()`. Teste de aceite: p. 31 contém `Tabela 6`; extração da 5410 em menos de 1 min.
- [ ] **Etapa 4.** `limpar.py`. Ordem fixa do plano. Testes de aceite listados na Etapa 4.

## Marco M2

- [ ] **Etapa 5.** `inline.py`. Testes: p. 42 da 5419-2, `mg/m2` da 5410 p. 31, `1 mm1)`.
- [ ] **Etapa 6.** `blocos.py`, `classificar.py`. Fixtures de 3 trechos por norma.

## Marco M3

- [ ] **Etapa 7.** `tabelas.py`. Tabela 5 da 5410 aparece uma vez, com AE1 a AE6. Linhas de agrupamento da 5419-2 em negrito.

## Marco M4

- [ ] **Etapa 8.** `figuras.py`, `formulas.py`, comando `recortes`. Figura 1 da 5419-1 gera PNG legível. Equação (3) da 5419-2 sai em LaTeX.
- [ ] **Etapa 9.** `revisoes.py`. Descrição das figuras pelo Kiro, em lotes de até 10, com `revisado_por: ia`.

## Marco M5

- [ ] **Etapa 10.** `estrutura.py`, `renderizar.py`, `chunks.py`. Três formatos, `termos.json`, `manifest.json`, `llms.txt`.
- [ ] **Etapa 11.** `validar.py`. As 5 normas passam sem bloqueantes.

## Marco M6

- [ ] **Etapa 12.** Processo para nova norma e steerings `nova-norma.md`, `descrever-figuras.md`, `formato-saida.md`. Seção "Como converter uma norma" no `README.md`.
- [ ] **Etapa 12a.** Processo para nova edição.
