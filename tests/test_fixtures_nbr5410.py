"""Regressão: trechos verificados à mão contra a página do PDF (tests/fixtures/nbr-5410/trechos.yaml)."""

import yaml

from nbr2md.config import RAIZ

FIXTURE = RAIZ / "tests" / "fixtures" / "nbr-5410" / "trechos.yaml"
MD = RAIZ / "normas" / "nbr-5410" / "nbr-5410.md"


def test_fixtures_tem_dez_trechos():
    dados = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert len(dados["trechos"]) == 10


def test_trechos_verificados_aparecem_no_markdown():
    md = MD.read_text(encoding="utf-8")
    dados = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    faltando = [t["texto"] for t in dados["trechos"] if t["texto"] not in md]
    assert faltando == []
