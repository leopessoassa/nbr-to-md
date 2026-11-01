"""Termos e definições (Etapa 10) e fallback de tabelas por texto (Etapa 7)."""

import pytest

from nbr2md.chunks import interpretar_definicao
from nbr2md.renderizar import renderizar_bloco


@pytest.mark.parametrize(
    "texto, numero, termo, definicao",
    [
        ("**3.1.1 componente** (de uma instalação elétrica): Termo empregado para designar itens.",
         "3.1.1", "componente (de uma instalação elétrica)", "Termo empregado para designar itens."),
        ("**3.1.2 quadro de distribuição principal:** Primeiro quadro da instalação.",
         "3.1.2", "quadro de distribuição principal", "Primeiro quadro da instalação."),
        ("**3.2.1 elemento condutivo ou parte condutiva**: Elemento condutor.",
         "3.2.1", "elemento condutivo ou parte condutiva", "Elemento condutor."),
    ],
)
def test_interpretar_definicao_reconhece_as_formas_da_norma(texto, numero, termo, definicao):
    info = interpretar_definicao(texto)
    assert info == {"numero": numero, "termo": termo, "definicao": definicao}


def test_texto_fora_do_formato_nao_e_interpretado():
    assert interpretar_definicao("Texto corrido sem número de definição.") is None


def test_definicao_vira_cabecalho_do_nivel_do_numero():
    bloco = {"tipo": "definicao", "numero": "3.1.1", "pagina": 17,
             "texto_md": "**3.1.1 componente** (de uma instalação elétrica): Termo de exemplo."}
    md = renderizar_bloco(bloco, set())
    assert md == "#### 3.1.1 componente (de uma instalação elétrica)\n\nTermo de exemplo."
