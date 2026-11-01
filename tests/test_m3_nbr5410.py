"""Critérios de aceite da Etapa 7 (M3) aplicados à ABNT NBR 5410.

Tabela 5 sai uma vez, inteira, com AE1 a AE6 (atravessa as páginas 30 e 31).
O critério das tabelas de agrupamento e de símbolos da NBR 5419-2 fica para
"a verificar quando a norma 5419-2 for convertida".
"""

import pytest

from nbr2md.blocos import processar
from nbr2md.config import carregar_norma
from test_m2_nbr5410 import blocos_5410, paginas_limpas_5410  # noqa: F401  (fixtures)


def _tabelas(saida, numero):
    return [b for b in saida["blocos"] if b["tipo"] == "tabela" and b["numero"] == numero]


def test_tabela_5_sai_uma_unica_vez(blocos_5410):
    assert len(_tabelas(blocos_5410, "5")) == 1


def test_tabela_5_atravessa_paginas_30_e_31(blocos_5410):
    tabela = _tabelas(blocos_5410, "5")[0]
    assert tabela["paginas"] == [30, 31]
    assert tabela["extra"]["continuacao_de_paginas"] is True


@pytest.mark.parametrize("codigo", ["AE1", "AE2", "AE3", "AE4", "AE5", "AE6"])
def test_tabela_5_tem_todas_as_linhas(blocos_5410, codigo):
    texto = _tabelas(blocos_5410, "5")[0]["texto_md"]
    assert f"| {codigo} |" in texto


def test_cabecalho_da_continuacao_nao_se_repete(blocos_5410):
    texto = _tabelas(blocos_5410, "5")[0]["texto_md"]
    assert texto.count("| Código |") == 1


def test_legenda_de_continuacao_nao_aparece_como_bloco(blocos_5410):
    assert not [
        b for b in blocos_5410["blocos"]
        if b["tipo"] == "legenda_tabela" and "(conclusão)" in b["texto_md"]
    ]


def test_nota_da_tabela_5_sai_depois_dela(blocos_5410):
    notas = [b for b in blocos_5410["blocos"] if b["tipo"] == "nota" and b["extra"].get("da_tabela") == "5"]
    assert notas and notas[0]["texto_md"].startswith("NOTA Nas condições AE2 e AE3")
    assert "NOTA" not in _tabelas(blocos_5410, "5")[0]["texto_md"]


def test_unidade_com_espaco_dentro_da_celula(blocos_5410):
    texto = _tabelas(blocos_5410, "5")[0]["texto_md"]
    assert "mg/m² e no máximo" in texto


def test_tabela_6_gfm_com_todas_as_linhas(blocos_5410):
    tabela = _tabelas(blocos_5410, "6")[0]
    assert tabela["extra"]["formato"] == "gfm"
    for codigo in ("AF1", "AF2", "AF3", "AF4"):
        assert f"| {codigo} |" in tabela["texto_md"]


def test_tabela_sem_legenda_fica_marcada(blocos_5410):
    sem = [b for b in blocos_5410["blocos"] if b["tipo"] == "tabela" and b["extra"]["sem_legenda"]]
    # Não é erro, mas precisa ficar visível para revisão (revisao.md, M5).
    assert all(b["texto_md"].strip() for b in sem)


def test_celulas_nao_vazias_da_tabela_5_iguais_a_soma_das_partes(blocos_5410, paginas_limpas_5410):
    """Etapa 7: contagem de células não vazias = soma das partes (sem cabeçalhos repetidos e notas)."""
    from nbr2md import tabelas as tb

    cabecalho = {"Código", "Classificação", "Características", "Aplicações e exemplos"}
    partes = []
    for pagina, codigo in ((30, "AE1"), (31, "AE3")):
        fragmento = next(
            t for t in tb.tabelas_da_pagina(paginas_limpas_5410[pagina])
            if any(c.texto.startswith(codigo) for c in t.celulas)
        )
        partes += [c.texto for c in fragmento.celulas if c.texto and c.texto not in cabecalho
                   and not c.texto.startswith("NOTA")]
    unida = _tabelas(blocos_5410, "5")[0]["texto_md"].splitlines()[2:]  # sem cabeçalho e separador
    celulas_unidas = [v.strip() for linha in unida for v in linha.strip("|").split(" | ") if v.strip()]
    assert len(celulas_unidas) == len(partes)


def test_sem_caractere_proibido_nas_tabelas(blocos_5410):
    for b in blocos_5410["blocos"]:
        if b["tipo"] == "tabela":
            for proibido in ("\ufffd", "⟦glifo:", "(cid:"):
                assert proibido not in b["texto_md"], b["id"]
