"""Diagnóstico de uma página: spans, glifos sem Unicode e recortes em PNG.

`--glifos` confere o mapeamento com um segundo extrator: cada U+FFFD do PyMuPDF
é casado com o caractere `(cid:N)` do pdfplumber na mesma posição (tolerância
de 2 pt). Pelo plano, N deve ser igual ao id do glifo do PyMuPDF.
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
import pymupdf

from nbr2md.config import RAIZ
from nbr2md.extrair import FLAGS_EXTRACAO, indice_glifos

TOLERANCIA_PT = 2.0
_CID = re.compile(r"^\(cid:(\d+)\)$")
PASTA_INSPECAO = RAIZ / "build" / "inspecao"


def _glifos_da_pagina(pagina: pymupdf.Page) -> list[dict]:
    """Um item por U+FFFD da página, com fonte, id do glifo e bbox."""
    indice = indice_glifos(pagina)
    achados = []
    bruto = pagina.get_text("rawdict", flags=FLAGS_EXTRACAO)
    for bloco in bruto["blocks"]:
        for linha in bloco.get("lines", []):
            for span in linha["spans"]:
                for caractere in span.get("chars", []):
                    if caractere["c"] != "\ufffd":
                        continue
                    ox, oy = caractere["origin"][0], caractere["origin"][1]
                    par = indice.get((round(ox, 1), round(oy, 1)))
                    achados.append(
                        {
                            "fonte_span": span["font"],
                            "fonte": par[0] if par else None,
                            "glifo": par[1] if par else None,
                            "bbox": tuple(caractere["bbox"]),
                            "origem": (ox, oy),
                            "tamanho": span["size"],
                        }
                    )
    return achados


def _cids_da_pagina_pdfplumber(pdf_plumber_pagina) -> list[dict]:
    cids = []
    for caractere in pdf_plumber_pagina.chars:
        casa = _CID.match(caractere.get("text", ""))
        if casa:
            cids.append(
                {
                    "cid": int(casa.group(1)),
                    "x0": caractere["x0"],
                    "base": caractere["bottom"],
                    "fonte": caractere.get("fontname", ""),
                }
            )
    return cids


def _casar(glifo: dict, cids: list[dict]) -> dict | None:
    """Casa pelo canto inferior esquerdo (x0 e base), que é o mesmo nos dois extratores.

    O centro do bbox não serve: glifos grandes têm altura diferente entre PyMuPDF e pdfplumber.
    """
    x0, _, _, y1 = glifo["bbox"]
    melhor, distancia_min = None, TOLERANCIA_PT
    for cid in cids:
        distancia = max(abs(cid["x0"] - x0), abs(cid["base"] - y1))
        if distancia <= distancia_min:
            melhor, distancia_min = cid, distancia
    return melhor


def _nome_arquivo(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", texto).strip("-")


def inspecionar_pagina(pdf: str, numero: int, glifos: bool, png: bool) -> int:
    caminho = Path(pdf)
    if not caminho.is_absolute():
        caminho = RAIZ / caminho
    if not caminho.is_file():
        print(f"PDF não encontrado: {caminho}")
        return 2

    documento = pymupdf.open(caminho)
    try:
        if not 1 <= numero <= documento.page_count:
            print(f"página fora do intervalo 1-{documento.page_count}")
            return 2
        pagina = documento[numero - 1]
        print(f"Página {numero} de {documento.page_count} | {pagina.rect.width:.1f} x {pagina.rect.height:.1f} pt")
        _imprimir_spans(pagina)

        if glifos or png:
            achados = _glifos_da_pagina(pagina)
            if glifos:
                _imprimir_glifos(caminho, numero, achados)
            if png:
                _gravar_recortes(pagina, numero, achados)
    finally:
        documento.close()
    return 0


def _imprimir_spans(pagina: pymupdf.Page) -> None:
    bruto = pagina.get_text("dict", flags=FLAGS_EXTRACAO)
    print("\nSpans (fonte | tamanho | bbox | texto):")
    for bloco in bruto["blocks"]:
        if bloco.get("type", 0) != 0:
            continue
        for linha in bloco["lines"]:
            for span in linha["spans"]:
                texto = span["text"].replace("\ufffd", "⟨?⟩")
                x0, y0, x1, y1 = (round(v, 1) for v in span["bbox"])
                print(f"  {span['font']} | {span['size']:.2f} | ({x0}, {y0}, {x1}, {y1}) | {texto}")


def _imprimir_glifos(caminho: Path, numero: int, achados: list[dict]) -> None:
    print(f"\nGlifos sem Unicode: {len(achados)} (PyMuPDF x pdfplumber)")
    if not achados:
        return
    with pdfplumber.open(caminho) as pdf:
        pagina_pp = pdf.pages[numero - 1]
        cids = _cids_da_pagina_pdfplumber(pagina_pp)
    print("  fonte | glifo | (cid:N) pdfplumber | coincide | bbox")
    for glifo in achados:
        par = _casar(glifo, cids)
        cid = par["cid"] if par else None
        if glifo["glifo"] is None:
            coincide = "sem par no texttrace"
        elif cid is None:
            coincide = "sem caractere no pdfplumber"
        else:
            coincide = "sim" if cid == glifo["glifo"] else "NAO"
        x0, y0, x1, y1 = (round(v, 1) for v in glifo["bbox"])
        print(f"  {glifo['fonte']} | {glifo['glifo']} | {cid} | {coincide} | ({x0}, {y0}, {x1}, {y1})")


def _gravar_recortes(pagina: pymupdf.Page, numero: int, achados: list[dict]) -> None:
    PASTA_INSPECAO.mkdir(parents=True, exist_ok=True)
    for indice, glifo in enumerate(achados):
        x0, y0, x1, y1 = glifo["bbox"]
        recorte = pymupdf.Rect(x0 - 6, y0 - 4, x1 + 6, y1 + 4) & pagina.rect
        rotulo = _nome_arquivo(f"{glifo['fonte'] or 'sem-par'}-{glifo['glifo']}")
        destino = PASTA_INSPECAO / f"p{numero:03d}-{rotulo}-{indice:02d}.png"
        pagina.get_pixmap(clip=recorte, dpi=300).save(destino)
        print(f"  recorte: {destino.relative_to(RAIZ)}")
