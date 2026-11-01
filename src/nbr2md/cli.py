"""Interface de linha de comando do conversor.

Os subcomandos são registrados aqui desde o Marco 0. A implementação de cada um
chega nos marcos seguintes (ver docs/PLANO-CONVERSAO.md, Seção 7).
"""

from __future__ import annotations

import argparse
import json
import sys

from nbr2md import __version__


def _nao_implementado(nome: str, marco: str):
    def executar(args: argparse.Namespace) -> int:
        print(
            f"'{nome}' ainda não está implementado (previsto para {marco}).",
            file=sys.stderr,
        )
        return 2

    return executar


def _converter(args: argparse.Namespace) -> int:
    from nbr2md.pipeline import converter_etapas_1_a_4

    if args.alvo.lower().endswith(".pdf"):
        print(
            "Informe o id da norma (ex.: nbr-5410), não o caminho do PDF. "
            "O PDF vem de config/<id>/norma.yaml.",
            file=sys.stderr,
        )
        return 2
    intervalo = range(args.paginas[0], args.paginas[1] + 1) if args.paginas else None
    resumo = converter_etapas_1_a_4(args.alvo, ate_etapa=args.ate_etapa or 10, paginas=intervalo)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    return 0


def _validar(args: argparse.Namespace) -> int:
    from nbr2md.pipeline import validar_norma

    codigo = validar_norma(args.id)
    print("validação sem bloqueantes" if codigo == 0 else "validação com bloqueantes; ver revisao.md")
    return codigo


def _recortes(args: argparse.Namespace) -> int:
    from nbr2md.pipeline import gerar_recortes

    if args.id.lower().endswith(".pdf"):
        print("Informe o id da norma (ex.: nbr-5410).", file=sys.stderr)
        return 2
    caminho = gerar_recortes(args.id)
    print(f"pendências gravadas em {caminho}")
    return 0


def _inspecionar(args: argparse.Namespace) -> int:
    from nbr2md.inspecao import inspecionar_pagina

    return inspecionar_pagina(
        args.pdf, args.pagina, glifos=args.glifos, png=args.png
    )


def _intervalo_paginas(texto: str) -> tuple[int, int]:
    """Converte '1-20' em (1, 20). Aceita também um número único, como '5'."""
    partes = texto.split("-")
    try:
        if len(partes) == 1:
            inicio = fim = int(partes[0])
        elif len(partes) == 2:
            inicio, fim = int(partes[0]), int(partes[1])
        else:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"intervalo inválido: {texto!r} (use N ou INICIO-FIM)"
        ) from None
    if inicio < 1 or fim < inicio:
        raise argparse.ArgumentTypeError(
            f"intervalo inválido: {texto!r} (páginas começam em 1)"
        )
    return inicio, fim


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbr2md",
        description="Converte normas técnicas brasileiras (PDF) em Markdown.",
    )
    parser.add_argument("--version", action="version", version=f"nbr2md {__version__}")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO", required=True)

    p = sub.add_parser("converter", help="converte uma norma (id ou caminho do PDF)")
    p.add_argument("alvo", metavar="id|caminho.pdf")
    p.add_argument(
        "--ate-etapa",
        type=int,
        metavar="N",
        help="para na etapa N do plano (útil para depuração)",
    )
    p.add_argument(
        "--paginas",
        type=_intervalo_paginas,
        metavar="INICIO-FIM",
        help="processa só um intervalo de páginas, por exemplo 1-20",
    )
    p.set_defaults(executar=_converter)

    p = sub.add_parser("inspecionar", help="mostra spans e glifos de uma página do PDF")
    p.add_argument("pdf", metavar="pdf")
    p.add_argument("--pagina", type=int, required=True, metavar="N")
    p.add_argument(
        "--glifos",
        action="store_true",
        help="lista glifos sem Unicode (PyMuPDF) lado a lado com (cid:N) do pdfplumber",
    )
    p.add_argument(
        "--png",
        action="store_true",
        help="salva o recorte de cada glifo em build/",
    )
    p.set_defaults(executar=_inspecionar)

    p = sub.add_parser("recortes", help="gera PNGs de figuras e fórmulas para revisão")
    p.add_argument("id", metavar="id")
    p.set_defaults(executar=_recortes)

    p = sub.add_parser("validar", help="valida a saída de uma norma")
    p.add_argument("id", metavar="id")
    p.set_defaults(executar=_validar)

    p = sub.add_parser("todas", help="converte todas as normas com config/*/norma.yaml")
    p.set_defaults(executar=_nao_implementado("todas", "Marco M5"))

    return parser


def main(argv: list[str] | None = None) -> int:
    # Acentos no console do Windows (cp1252 por padrão) não podem quebrar a saída.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    args = construir_parser().parse_args(argv)
    return args.executar(args)
