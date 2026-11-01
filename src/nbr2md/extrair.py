"""Etapa 3: extração de spans, imagens, desenhos e tabelas por página.

Glifos sem mapeamento Unicode: o texto sai com `rawdict` e sem a flag
TEXT_CID_FOR_UNKNOWN_UNICODE, então esses glifos aparecem como U+FFFD. Cada
U+FFFD é casado com `get_texttrace()` pela origem do caractere, que devolve o
id do glifo e a fonte. Ver docs/PLANO-CONVERSAO.md, Etapa 3.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from nbr2md.modelo import Linha, Span, fonte_base

# A flag CID nunca pode ficar ligada (Etapa 3 do plano, regra 8 do prompt).
FLAGS_EXTRACAO = (
    pymupdf.TEXTFLAGS_DICT
    & ~pymupdf.TEXT_PRESERVE_IMAGES
    & ~pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
)
assert not (FLAGS_EXTRACAO & pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE)

REPLACEMENT = "\ufffd"
_ESTILO_NEGRITO = 16
_ESTILO_ITALICO = 2
_JANELA_CONTEXTO = 20  # caracteres de cada lado: 40 ao todo


@dataclass
class ResultadoExtracao:
    sha256: str
    total_paginas: int
    paginas: dict[int, dict] = field(default_factory=dict)  # número -> dados da página
    erros: list[dict] = field(default_factory=list)


def sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            digest.update(bloco)
    return digest.hexdigest()


def indice_glifos(pagina: pymupdf.Page) -> dict[tuple[float, float], tuple[str, int] | None]:
    """Mapa origem do caractere -> (fonte, id do glifo) para os U+FFFD da página.

    A chave é a origem arredondada a 0,1 pt. Origens repetidas com fonte ou
    glifo diferentes viram None (ambíguo) e geram erro na extração.
    """
    indice: dict[tuple[float, float], tuple[str, int] | None] = {}
    for trilha in pagina.get_texttrace():
        for caractere in trilha["chars"]:
            unicode, glifo, origem = caractere[0], caractere[1], caractere[2]
            if unicode != 0xFFFD:
                continue
            chave = (round(origem[0], 1), round(origem[1], 1))
            valor = (fonte_base(trilha["font"]), glifo)
            if chave in indice and indice[chave] != valor:
                indice[chave] = None
            else:
                indice.setdefault(chave, valor)
    return indice


def _negrito(nome: str, flags: int) -> bool:
    return "Bold" in nome or bool(flags & _ESTILO_NEGRITO)


def _italico(nome: str, flags: int) -> bool:
    return any(p in nome for p in ("Italic", "Oblique")) or bool(flags & _ESTILO_ITALICO)


def _linha_com_glifos(
    linha_bruta: dict,
    numero: int,
    indice: dict,
    erros: list[dict],
) -> Linha:
    """Monta a Linha. Os U+FFFD da linha recebem fonte, glifo e contexto."""
    direcao = tuple(linha_bruta["dir"])
    textos_da_linha = [
        "".join(c["c"] for c in span_bruto.get("chars", []))
        for span_bruto in linha_bruta["spans"]
    ]
    texto_linha = "".join(textos_da_linha)

    spans: list[Span] = []
    deslocamento = 0
    for span_bruto, texto in zip(linha_bruta["spans"], textos_da_linha):
        glifos: list[dict] = []
        for i, caractere in enumerate(span_bruto.get("chars", [])):
            if caractere["c"] != REPLACEMENT:
                continue
            ox, oy = caractere["origin"][0], caractere["origin"][1]
            chave = (round(ox, 1), round(oy, 1))
            achado = indice.get(chave)
            if achado is None:
                motivo = "ambiguo" if chave in indice else "sem_par_no_texttrace"
                erros.append(
                    {
                        "pagina": numero,
                        "origem": [ox, oy],
                        "fonte": span_bruto["font"],
                        "motivo": motivo,
                    }
                )
                continue
            posicao = deslocamento + i
            inicio = max(0, posicao - _JANELA_CONTEXTO)
            glifos.append(
                {
                    "indice": i,
                    "glifo": achado[1],
                    "fonte": achado[0],
                    "contexto": texto_linha[inicio : posicao + _JANELA_CONTEXTO],
                }
            )
        deslocamento += len(texto)
        spans.append(
            Span(
                texto=texto,
                fonte=span_bruto["font"],
                tamanho=span_bruto["size"],
                negrito=_negrito(span_bruto["font"], span_bruto["flags"]),
                italico=_italico(span_bruto["font"], span_bruto["flags"]),
                bbox=tuple(span_bruto["bbox"]),
                origem_x=span_bruto["origin"][0],
                origem_y=span_bruto["origin"][1],
                direcao=direcao,
                glifos_sem_unicode=glifos,
            )
        )
    return Linha(spans=spans, bbox=tuple(linha_bruta["bbox"]), pagina=numero, direcao=direcao)


def extrair_pagina(pagina: pymupdf.Page, numero: int) -> tuple[dict, list[dict]]:
    """Extrai uma página. Devolve (dados da página, erros de extração)."""
    erros: list[dict] = []
    indice = indice_glifos(pagina)
    bruto = pagina.get_text("rawdict", flags=FLAGS_EXTRACAO)

    linhas: list[Linha] = []
    for bloco in bruto["blocks"]:
        if bloco.get("type", 0) != 0:  # só texto; imagens são tratadas à parte
            continue
        for linha_bruta in bloco["lines"]:
            linhas.append(_linha_com_glifos(linha_bruta, numero, indice, erros))

    dados = {
        "pagina": numero,
        "largura": pagina.rect.width,
        "altura": pagina.rect.height,
        "linhas": [linha.para_dict() for linha in linhas],
        "imagens": _imagens(pagina),
        "desenhos": _desenhos(pagina),
        "tabelas": _tabelas(pagina),
    }
    return dados, erros


def _imagens(pagina: pymupdf.Page) -> list[dict]:
    return [
        {
            "xref": info.get("xref", 0),
            "bbox": list(info["bbox"]),
            "largura_px": info.get("width"),
            "altura_px": info.get("height"),
        }
        for info in pagina.get_image_info(xrefs=True)
    ]


def _desenhos(pagina: pymupdf.Page) -> dict:
    desenhos = pagina.get_drawings()
    uniao = pymupdf.Rect()
    for desenho in desenhos:
        uniao |= desenho["rect"]
    return {
        "quantidade": len(desenhos),
        "bbox_agregada": list(uniao) if desenhos else None,
    }


def _tabelas(pagina: pymupdf.Page) -> list[dict]:
    return [
        {
            "bbox": list(tabela.bbox),
            "linhas": tabela.extract(),
            "celulas": [list(c) if c else None for c in tabela.cells],
        }
        for tabela in pagina.find_tables().tables
    ]


def extrair_pdf(pdf: Path, paginas: range | None = None) -> ResultadoExtracao:
    """Extrai o PDF inteiro, ou só o intervalo `paginas` (numeração a partir de 1)."""
    documento = pymupdf.open(pdf)
    try:
        resultado = ResultadoExtracao(
            sha256=sha256_arquivo(pdf), total_paginas=documento.page_count
        )
        alvo = paginas if paginas is not None else range(1, documento.page_count + 1)
        for numero in alvo:
            dados, erros = extrair_pagina(documento[numero - 1], numero)
            resultado.paginas[numero] = dados
            resultado.erros.extend(erros)
    finally:
        documento.close()
    return resultado


def gravar_paginas(resultado: ResultadoExtracao, pasta: Path) -> None:
    """Grava build/<id>/01-spans/pagina-NNNN.json, uma por página."""
    pasta.mkdir(parents=True, exist_ok=True)
    for numero, dados in resultado.paginas.items():
        caminho = pasta / f"pagina-{numero:04d}.json"
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def resumir_glifos(resultado: ResultadoExtracao, mapa: dict[str, dict[int, str]]) -> dict:
    """Agrupa os glifos sem Unicode por (fonte, id do glifo).

    `mapeado` indica se o par já tem entrada em `mapa_glifos`. Os exemplos são
    até três ocorrências, com página e contexto de 40 caracteres.
    """
    agregado: dict[tuple[str, int], dict] = {}
    total = 0
    for numero, pagina in resultado.paginas.items():
        for linha in pagina["linhas"]:
            for span in linha["spans"]:
                for glifo in span["glifos_sem_unicode"]:
                    total += 1
                    chave = (glifo["fonte"], glifo["glifo"])
                    entrada = agregado.setdefault(
                        chave,
                        {"fonte": chave[0], "glifo": chave[1], "ocorrencias": 0, "exemplos": []},
                    )
                    entrada["ocorrencias"] += 1
                    if len(entrada["exemplos"]) < 3:
                        entrada["exemplos"].append(
                            {"pagina": numero, "contexto": glifo["contexto"]}
                        )
    pares = sorted(agregado.values(), key=lambda e: (-e["ocorrencias"], e["fonte"], e["glifo"]))
    for par in pares:
        par["mapeado"] = par["glifo"] in mapa.get(par["fonte"], {})
    return {"total_pares": len(pares), "total_ocorrencias": total, "pares": pares}
