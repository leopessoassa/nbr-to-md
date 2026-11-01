"""Critérios de aceite das Etapas 5 e 6 (M2) aplicados à ABNT NBR 5410.

Lê build/nbr-5410/02-limpo; se não existir, roda a limpeza antes (converter até a etapa 4).
Os critérios de NBR 5419 (p. 42, tabela de símbolos, testes de agrupamento) ficam para
quando as normas forem convertidas: "a verificar quando a norma 5419 for convertida".
"""

import json

import pytest

from nbr2md.blocos import processar
from nbr2md.config import RAIZ, carregar_norma

LIMPO = RAIZ / "build" / "nbr-5410" / "02-limpo"


@pytest.fixture(scope="session")
def paginas_limpas_5410():
    if not LIMPO.is_dir() or not any(LIMPO.glob("pagina-*.json")):
        from nbr2md.pipeline import converter_etapas_1_a_4

        converter_etapas_1_a_4("nbr-5410", ate_etapa=4)
    paginas = {}
    for arquivo in sorted(LIMPO.glob("pagina-*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        paginas[dados["pagina"]] = dados
    return paginas


@pytest.fixture(scope="session")
def blocos_5410(paginas_limpas_5410):
    return processar(paginas_limpas_5410, carregar_norma("nbr-5410"))


def _blocos(saida, pagina, tipo=None):
    return [
        b for b in saida["blocos"]
        if b["pagina"] == pagina and (tipo is None or b["tipo"] == tipo)
    ]


def test_capa_extraida(blocos_5410):
    capa = blocos_5410["capa"]
    assert capa["titulo"] == "Instalações elétricas de baixa tensão"
    assert capa["edicao"] == "Segunda edição"
    assert capa["data_publicacao"] == "2004-09-30"
    assert capa["valida_a_partir_de"] == "2005-03-31"
    assert capa["versao_corrigida"] == "2008-03-17"
    assert capa["ics"] == ["91.140.50"]
    assert capa["norma_completa"] == "ABNT NBR 5410:2004"


def test_capa_sumario_e_ficha_ficam_fora_do_corpo(blocos_5410):
    assert blocos_5410["paginas_ignoradas"] == [1, 2, 3, 4, 5, 6]
    assert not [b for b in blocos_5410["blocos"] if b["pagina"] <= 6]


def test_prefacio_e_titulo_sem_numero(blocos_5410):
    titulos = _blocos(blocos_5410, 7, "titulo_secao")
    assert titulos and titulos[0]["numero"] is None
    assert "Prefácio" in titulos[0]["texto_md"]


def test_titulo_de_secao_com_numero(blocos_5410):
    titulos = _blocos(blocos_5410, 9, "titulo_secao")
    assert titulos[0]["numero"] == "1"
    assert "Objetivo" in titulos[0]["texto_md"]


def test_paragrafo_numerado_com_numero_e_texto(blocos_5410):
    blocos = [b for b in _blocos(blocos_5410, 9, "paragrafo_numerado") if b["numero"] == "1.1"]
    assert blocos, "1.1 não virou paragrafo_numerado"
    assert blocos[0]["texto_md"].startswith("**1.1** Esta Norma estabelece as condições")


def test_nota_e_item_de_lista(blocos_5410):
    notas = _blocos(blocos_5410, 9, "nota")
    assert notas[0]["texto_md"].startswith("NOTA A aplicação às linhas de sinal")
    itens = _blocos(blocos_5410, 9, "item_lista")
    assert itens[0]["texto_md"].startswith("a) em áreas descobertas")


def test_italico_sem_espaco_espurio(blocos_5410):
    texto = " ".join(b["texto_md"] for b in _blocos(blocos_5410, 9))
    assert "(*trailers*)" in texto


def test_unidade_e_nota_de_rodape_p31(blocos_5410):
    """Critérios da Etapa 5: 'mg/m2' vira mg/m² e '1 mm1)' vira '1 mm[^…]'.

    Os trechos estão nas tabelas 5 e 6 (ver M3). A Tabela 5 é atribuída à página 30,
    onde começa, e a Tabela 6 à página 31.
    """
    texto = " ".join(b["texto_md"] for b in blocos_5410["blocos"])
    assert "mg/m²" in texto
    assert "1 mm[^p31-1]" in texto


def test_paragrafo_atravessa_paginas(blocos_5410):
    juntados = [b for b in blocos_5410["blocos"] if len(b["paginas"]) > 1]
    assert juntados, "nenhum parágrafo foi juntado entre páginas"
    assert all(b["paginas"][1] == b["paginas"][0] + 1 for b in juntados)


def test_nenhum_caractere_proibido_no_texto(blocos_5410):
    for b in blocos_5410["blocos"]:
        for proibido in ("\ufffd", "⟦glifo:", "(cid:"):
            assert proibido not in b["texto_md"], f"{b['id']}: {proibido!r}"


def test_tipos_conhecidos(blocos_5410):
    tipos = {
        "titulo_secao", "paragrafo", "paragrafo_numerado", "item_lista", "nota",
        "exemplo", "definicao", "legenda_tabela", "legenda_figura", "anexo", "rodape", "tabela",
            "figura", "formula", "rodape_pendente", "simbolo",
    }
    assert {b["tipo"] for b in blocos_5410["blocos"]} <= tipos
