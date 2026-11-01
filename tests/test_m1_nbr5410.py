"""Critérios de aceite das Etapas 3 e 4 (M1) aplicados à ABNT NBR 5410.

Os testes rodam a extração real do PDF em nbr/5410 uma vez por sessão (~40 s).
Marca d'água: só sai linha que casa com a regex. Texto rotacionado de tabela
(página 86, "Limite inferior/superior") precisa permanecer.
"""

import pytest

from nbr2md.config import carregar_norma
from nbr2md.extrair import FLAGS_EXTRACAO, extrair_pdf, resumir_glifos
from nbr2md.limpar import _texto_linha, limpar
from nbr2md.config import RAIZ
import pymupdf

PDF_5410 = RAIZ / "nbr" / "5410" / "NBR5410.pdf"


@pytest.fixture(scope="session")
def extracao_5410():
    return extrair_pdf(PDF_5410)


@pytest.fixture(scope="session")
def limpeza_5410(extracao_5410):
    cfg = carregar_norma("nbr-5410")
    paginas, relatorio = limpar(extracao_5410.paginas, cfg, len(extracao_5410.erros))
    return paginas, relatorio


def _textos_da_pagina(paginas, numero):
    return [_texto_linha(l) for l in paginas[numero]["linhas"]]


def test_flag_cid_fica_desligada():
    assert not (FLAGS_EXTRACAO & pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE)


def test_extracao_sem_erros_de_glifo(extracao_5410):
    assert extracao_5410.erros == []


def test_glifos_desconhecidos_5410_tem_31_pares_e_575_ocorrencias(extracao_5410):
    glifos = resumir_glifos(extracao_5410, carregar_norma("nbr-5410")["mapa_glifos"])
    assert glifos["total_pares"] == 31
    assert glifos["total_ocorrencias"] == 575


def test_p31_contem_tabela_6(extracao_5410):
    textos = [s["texto"] for l in extracao_5410.paginas[31]["linhas"] for s in l["spans"]]
    assert any("Tabela 6" in t for t in textos)


def test_nenhum_u_fffd_sobra_apos_limpeza(limpeza_5410):
    paginas, _ = limpeza_5410
    for numero in paginas:
        for texto in _textos_da_pagina(paginas, numero):
            assert "\ufffd" not in texto, f"p.{numero}: {texto[:60]}"


@pytest.mark.parametrize(
    "pagina, esperado",
    [
        (17, "•"),       # marcador de lista, glifo ArialMT 650
        (48, "Δ"),       # ArialMT 507
        (48, "≤"),       # ArialMT 148
        (29, "≤ 2 000 m"),  # SymbolMT 100
        (35, "10 μs"),   # SymbolMT 80
        (119, "√"),      # SymbolMT 32
    ],
)
def test_glifos_confirmados_aparecem_com_caractere_correto(limpeza_5410, pagina, esperado):
    paginas, _ = limpeza_5410
    assert any(esperado in t for t in _textos_da_pagina(paginas, pagina)), (
        f"p.{pagina}: '{esperado}' não encontrado"
    )


def test_sem_marca_dagua_nem_dados_do_licenciado(limpeza_5410):
    paginas, _ = limpeza_5410
    for numero in paginas:
        for texto in _textos_da_pagina(paginas, numero):
            assert "Exemplar para uso exclusivo" not in texto
            assert "CONNECTCOM" not in texto


def test_sem_cabecalho_isolado(limpeza_5410):
    """A capa (paginas.capa) fica de fora: a designação impressa nela é dado do front matter."""
    paginas, _ = limpeza_5410
    capa = set(carregar_norma("nbr-5410")["paginas"]["capa"])
    for numero in paginas:
        if numero in capa:
            continue
        for texto in _textos_da_pagina(paginas, numero):
            assert texto.strip() != "ABNT NBR 5410:2004"


def test_imagem_de_fundo_removida_em_todas_as_paginas(limpeza_5410):
    _, relatorio = limpeza_5410
    assert relatorio.imagens_fundo_removidas == 217


def test_ne_legitimo_nao_e_alterado(extracao_5410):
    """Um ņ sem registro de glifo (texto já mapeado) não pode ser trocado."""
    cfg = carregar_norma("nbr-5410")
    pagina = {
        "pagina": 1,
        "largura": 595.0,
        "altura": 842.0,
        "imagens": [],
        "desenhos": {},
        "tabelas": [],
        "linhas": [
            {
                "bbox": [100, 400, 300, 412],
                "direcao": [1.0, 0.0],
                "spans": [
                    {
                        "texto": "ņ legítimo",
                        "fonte": "ArialMT",
                        "tamanho": 10.0,
                        "negrito": False,
                        "italico": False,
                        "bbox": [100, 400, 300, 412],
                        "origem_x": 100,
                        "origem_y": 410,
                        "direcao": [1.0, 0.0],
                        "glifos_sem_unicode": [],
                    }
                ],
            }
        ],
    }
    paginas, _ = limpar({1: pagina}, cfg)
    assert _texto_linha(paginas[1]["linhas"][0]) == "ņ legítimo"


def test_marca_dagua_removida_uma_vez_por_pagina(limpeza_5410):
    _, relatorio = limpeza_5410
    paginas_sem_marca = [n for n, q in relatorio.marca_dagua_por_pagina.items() if q < 1]
    assert paginas_sem_marca == []
    assert all(q == 1 for q in relatorio.marca_dagua_por_pagina.values())


def test_rotulos_rotacionados_da_tabela_sao_mantidos(limpeza_5410):
    """p. 86: os rótulos 'Limite inferior/superior' da tabela em paisagem não são marca d'água."""
    paginas, _ = limpeza_5410
    textos = _textos_da_pagina(paginas, 86)
    assert sum(t.strip() in ("Limite", "inferior", "superior") for t in textos) == 12
