"""Etapa 5: marcação inline com spans sintéticos (sem depender do PDF)."""

from nbr2md.inline import marcar


def span(texto, tamanho=10.0, origem_y=100.0, negrito=False, italico=False):
    return {
        "texto": texto,
        "tamanho": tamanho,
        "origem_y": origem_y,
        "negrito": negrito,
        "italico": italico,
        "fonte": "ArialMT",
    }


def test_subscrito_abaixo_da_linha_de_base():
    spans = [span("R"), span("X", tamanho=7.0, origem_y=102.0), span(" é")]
    assert marcar(spans, 1)[0] == "R<sub>X</sub> é"


def test_sobrescrito_de_unidade_vira_unicode():
    spans = [span("mg/m"), span("2", tamanho=6.5, origem_y=95.0)]
    assert marcar(spans, 31)[0] == "mg/m²"


def test_sobrescrito_negativo_de_unidade_vira_unicode():
    spans = [span("10 μs"), span("-1", tamanho=6.5, origem_y=95.0)]
    assert marcar(spans, 1)[0] == "10 μs⁻¹"


def test_sobrescrito_sem_unidade_vira_tag_sup():
    # corpo com dois caracteres: a referência de tamanho é o texto normal, não o sobrescrito
    spans = [span("xy"), span("n", tamanho=6.5, origem_y=95.0)]
    assert marcar(spans, 1)[0] == "xy<sup>n</sup>"


def test_nota_de_rodape_vira_marcador():
    spans = [span("1 mm"), span("1)", tamanho=6.5, origem_y=95.0)]
    texto, marcas = marcar(spans, 31)
    assert texto == "1 mm[^p31-1]"
    assert marcas == ["p31-1"]


def test_negrito_nao_inclui_espacos_das_pontas():
    spans = [span("1.1", negrito=True), span(" Esta Norma")]
    assert marcar(spans, 9)[0] == "**1.1** Esta Norma"


def test_italico_junta_trechos_vizinhos():
    spans = [span("de reboques ("), span("trailers", italico=True), span("), locais")]
    assert marcar(spans, 9)[0] == "de reboques (*trailers*), locais"
