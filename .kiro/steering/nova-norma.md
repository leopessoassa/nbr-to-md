---
inclusion: manual
---

# Como converter uma norma nova (ou nova edição)

Use este passo a passo quando o usuário pedir para converter uma NBR. Os comandos são sempre `mise exec -- python -m ...`.

## Nova norma (Etapa 12 do plano)

1. Copie o PDF para `nbr/<numero>/`.
2. Crie `config/<id>/norma.yaml` com `id` e `fonte`. Use `config/nbr-5410/norma.yaml` como modelo.
3. Converta até a limpeza para achar glifos sem mapa:
   `mise exec -- python -m nbr2md converter <id> --ate-etapa 4`
   Glifos desconhecidos ficam em `build/<id>/glifos-desconhecidos.json`.
4. Para cada glifo: renderize o trecho (`inspecionar <pdf> --pagina N --glifos --png`), abra o PNG, identifique o caractere e confira o `(cid:N)` do pdfplumber. Só então adicione em `mapa_glifos`. Nunca adivinhe um glifo sem ver a imagem.
5. Converta a norma completa: `mise exec -- python -m nbr2md converter <id>`.
6. Valide: `mise exec -- python -m nbr2md validar <id>`. Leia `normas/<id>/revisao.md`. Ajuste em `norma.yaml` primeiro; `config/defaults.yaml` só se a regra servir para qualquer NBR; código só com teste novo e sem quebrar as normas já convertidas.
7. Figuras e fórmulas: rode `mise exec -- python -m nbr2md recortes <id>` e siga `descrever-figuras.md`.
8. Adicione fixtures de regressão em `tests/fixtures/<id>/` (10 trechos verificados contra a imagem da página) e rode `mise exec -- python -m pytest -q`.
9. Não faça commit. O dono faz.

## Nova edição de norma já convertida (Etapa 12a)

1. Substitua o PDF em `nbr/<numero>/`. Apague o antigo só depois de confirmar com o usuário.
2. Atualize `fonte` em `config/<id>/norma.yaml`. Revise `mapa_glifos`, `mapa_caracteres` e `paginas`.
3. Não apague `config/<id>/revisoes.yaml`. Rode `converter` e `validar`:
   - `correcoes_texto` cujo `de` não existe mais falham e precisam ser refeitos;
   - figuras cujo `hash_recorte` mudou voltam a pendentes e aparecem em `revisao.md`.
4. O conversor regenera `normas/<id>/` por completo, e só dentro de `normas/`.
5. Atualize as fixtures da norma com trechos da nova edição.
6. Commit único (feito pelo dono): `ABNT NBR <numero>: substitui edição <ano antigo> por <ano novo>`.
