import subprocess
import sys

import pytest

from nbr2md.cli import construir_parser, _intervalo_paginas

SUBCOMANDOS = ["converter", "inspecionar", "recortes", "validar", "todas"]


def test_help_do_modulo_funciona():
    resultado = subprocess.run(
        [sys.executable, "-m", "nbr2md", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert resultado.returncode == 0
    for nome in SUBCOMANDOS:
        assert nome in resultado.stdout


@pytest.mark.parametrize("nome", SUBCOMANDOS)
def test_cada_subcomando_tem_help(nome):
    with pytest.raises(SystemExit) as saida:
        construir_parser().parse_args([nome, "--help"])
    assert saida.value.code == 0


def test_inspecionar_aceita_flags_do_plano():
    args = construir_parser().parse_args(
        ["inspecionar", "x.pdf", "--pagina", "48", "--glifos", "--png"]
    )
    assert (args.pagina, args.glifos, args.png) == (48, True, True)


def test_converter_aceita_paginas_e_ate_etapa():
    args = construir_parser().parse_args(
        ["converter", "nbr-5410", "--ate-etapa", "4", "--paginas", "1-20"]
    )
    assert args.ate_etapa == 4
    assert args.paginas == (1, 20)


@pytest.mark.parametrize("valor", ["1-20", "5"])
def test_intervalo_de_paginas_valido(valor):
    inicio, fim = _intervalo_paginas(valor)
    assert 1 <= inicio <= fim


@pytest.mark.parametrize("valor", ["0-3", "5-2", "a-b", "1-2-3"])
def test_intervalo_de_paginas_invalido(valor):
    with pytest.raises(Exception):
        _intervalo_paginas(valor)
