"""Etapa 7: tabelas (detecção pelo PyMuPDF, texto dos spans limpos, GFM ou HTML).

- A grade vem das caixas das células de `find_tables()` (já salvas em 01-spans).
- O texto de cada célula é reextraído dos spans limpos dentro da caixa, para manter
  <sub>, <sup>, unidades e notas de rodapé.
- Tabela associada à legenda mais próxima acima (até 40 pt). Tabela sem legenda que
  começa no topo da página e tem o mesmo número de colunas da tabela anterior é
  continuação. Continuações com o mesmo número são unidas em uma tabela só.
- Linha "NOTA ..." dentro da tabela sai dela e vira bloco de nota logo após.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from nbr2md import inline
from nbr2md.blocos import _agrupar_spans, _com_espacos

DISTANCIA_LEGENDA = 40.0   # pt, acima da tabela
TOPO_CONTINUACAO = 130.0   # pt: tabela que começa neste topo pode ser continuação
_MARCADOR_LISTA = re.compile(r"^(?:[•–—\-]\s|[a-z]\)\s)")
_CONTINUACAO = re.compile(r"\((?:continuação|conclusão)\)")


@dataclass
class Celula:
    r0: int
    r1: int
    c0: int
    c1: int
    bbox: tuple[float, float, float, float]
    texto: str
    xn0: float = 0.0   # x esquerdo relativo à largura da própria tabela (0 a 1)
    xn1: float = 1.0   # x direito relativo à largura da própria tabela


@dataclass
class TabelaPagina:
    pagina: int
    bbox: tuple[float, float, float, float]
    celulas: list[Celula]
    nlinhas: int
    ncolunas: int
    numero: str | None = None
    continuacao: bool = False
    sem_legenda: bool = False
    notas: list[str] = field(default_factory=list)
    paginas: list[int] = field(default_factory=list)
    cabecalhos_descartados: list[str] = field(default_factory=list)  # linhas repetidas removidas
    confianca: str = "alta"  # "baixa" quando veio do fallback find_tables(strategy="text")


def _centro(bbox) -> tuple[float, float]:
    return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


def _texto_celula(spans: list[dict], bbox, pagina: int) -> str:
    x0, y0, x1, y1 = bbox
    dentro = []
    for s in spans:
        cx, cy = _centro(s["bbox"])
        if x0 - 0.5 <= cx <= x1 + 0.5 and y0 - 0.5 <= cy <= y1 + 0.5:
            dentro.append(s)  # inclui espaços: são eles que separam "m²" de "e"
    if not any(s["texto"].strip() for s in dentro):
        return ""
    grupos = _agrupar_spans(dentro)
    linhas = []
    for grupo in grupos:
        grupo.sort(key=lambda s: s["bbox"][0])
        md, _ = inline.marcar(_com_espacos(grupo), pagina)
        if md.strip():
            linhas.append((_centro(grupo[0]["bbox"])[1], md))
    linhas.sort()
    texto = ""
    for _, md in linhas:
        md = md.strip()
        if not texto:
            texto = md
        elif texto.endswith("-") and md[:1].islower():
            texto = texto + md          # hífen mantido: "não-" + "residenciais"
        elif _MARCADOR_LISTA.match(md):
            texto = f"{texto}<br>{md}"
        else:
            texto = f"{texto} {md}"
    return re.sub(r" {2,}", " ", texto).strip()


def tabelas_da_pagina(pagina: dict) -> list[TabelaPagina]:
    """Tabelas detectadas na página, com o texto de cada célula."""
    spans = [s for linha in pagina["linhas"] for s in linha["spans"]]
    resultado = []
    for bruta in pagina.get("tabelas", []):
        linhas = bruta["linhas"]
        ncol = max((len(r) for r in linhas), default=0)
        caixas = [c for c in bruta["celulas"] if c]
        if len(linhas) < 2 or ncol < 2 or not caixas:
            continue
        ys = sorted({round(v, 1) for c in caixas for v in (c[1], c[3])})
        xs = sorted({round(v, 1) for c in caixas for v in (c[0], c[2])})
        largura = (bruta["bbox"][2] - bruta["bbox"][0]) or 1.0
        celulas = []
        for c in caixas:
            celulas.append(
                Celula(
                    r0=ys.index(round(c[1], 1)),
                    r1=ys.index(round(c[3], 1)),
                    c0=xs.index(round(c[0], 1)),
                    c1=xs.index(round(c[2], 1)),
                    bbox=tuple(c),
                    texto=_texto_celula(spans, c, pagina["pagina"]),
                    xn0=(c[0] - bruta["bbox"][0]) / largura,
                    xn1=(c[2] - bruta["bbox"][0]) / largura,
                )
            )
        resultado.append(
            TabelaPagina(
                pagina=pagina["pagina"],
                bbox=tuple(bruta["bbox"]),
                celulas=celulas,
                nlinhas=len(ys) - 1,
                ncolunas=len(xs) - 1,
                paginas=[pagina["pagina"]],
                confianca=bruta.get("confianca", "alta"),
            )
        )
    return resultado


def associar(
    tabelas_por_pagina: dict[int, list[TabelaPagina]],
    legendas_por_pagina: dict[int, list[dict]],
) -> None:
    """Preenche numero, continuacao e sem_legenda de cada tabela (in place)."""
    anterior: TabelaPagina | None = None
    for pagina in sorted(tabelas_por_pagina):
        for tabela in tabelas_por_pagina[pagina]:
            legenda = _legenda_acima(tabela, legendas_por_pagina.get(pagina, []))
            if legenda is not None:
                tabela.numero = legenda["numero"]
                tabela.continuacao = bool(_CONTINUACAO.search(legenda["texto_md"]))
            elif (
                anterior is not None
                and tabela.bbox[1] <= TOPO_CONTINUACAO
                and anterior.ncolunas == tabela.ncolunas
                and anterior.numero is not None
            ):
                tabela.numero = anterior.numero
                tabela.continuacao = True
            else:
                tabela.sem_legenda = True
            anterior = tabela


DISTANCIA_LEGENDA_BAIXA = 120.0  # pt: tabela do fallback por texto (recortada logo abaixo da legenda)


def _legenda_acima(tabela: TabelaPagina, legendas: list[dict]) -> dict | None:
    limite = DISTANCIA_LEGENDA_BAIXA if tabela.confianca == "baixa" else DISTANCIA_LEGENDA
    candidatas = []
    for leg in legendas:
        base = leg["bbox"][3]
        distancia = tabela.bbox[1] - base
        if -2 <= distancia <= limite:
            candidatas.append((distancia, leg))
    return min(candidatas, key=lambda par: par[0])[1] if candidatas else None


def _compactar(celulas: list[Celula]) -> tuple[list[Celula], int, int]:
    """Remove linhas e colunas vazias e renumera a grade."""
    linhas = sorted({r for c in celulas for r in range(c.r0, c.r1)})
    colunas = sorted({k for c in celulas for k in range(c.c0, c.c1)})
    mapa_r = {r: i for i, r in enumerate(linhas)}
    mapa_c = {k: i for i, k in enumerate(colunas)}
    novas = []
    for c in celulas:
        novas.append(
            Celula(
                r0=mapa_r[c.r0],
                r1=mapa_r[c.r1 - 1] + 1,
                c0=mapa_c[c.c0],
                c1=mapa_c[c.c1 - 1] + 1,
                bbox=c.bbox,
                texto=c.texto,
                xn0=c.xn0,
                xn1=c.xn1,
            )
        )
    return novas, len(linhas), len(colunas)


def _linhas_de_cabecalho_repetido(principal: TabelaPagina, fragmento: TabelaPagina, maximo: int = 3) -> int:
    """Quantas linhas iniciais do fragmento repetem o cabeçalho da tabela principal.

    Uma linha repete o cabeçalho quando todos os seus textos já aparecem nas primeiras
    `maximo` linhas da principal. A contagem para na primeira linha de dados.
    """
    referencia = {
        c.texto for c in principal.celulas if c.r0 < min(maximo, principal.nlinhas) and c.texto
    }
    k = 0
    while k < fragmento.nlinhas:
        textos = {c.texto for c in fragmento.celulas if c.r0 == k and c.texto}
        if not textos or not textos <= referencia:
            break
        k += 1
    return k


def _regrade_colunas(tabela: TabelaPagina, tol: float = 0.01) -> None:
    """Recalcula c0/c1 de cada célula pela posição x relativa à largura da tabela.

    Fragmentos da mesma tabela podem estar deslocados na página; a posição relativa
    alinha as colunas. `tol` é 1% da largura.
    """
    valores = sorted(v for c in tabela.celulas for v in (c.xn0, c.xn1))
    grupos: list[list[float]] = []
    for v in valores:
        if grupos and v - grupos[-1][-1] <= tol:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    xs = [sum(g) / len(g) for g in grupos]

    def indice(v: float) -> int:
        return min(range(len(xs)), key=lambda i: abs(xs[i] - v))

    for c in tabela.celulas:
        c.c0 = indice(c.xn0)
        c.c1 = max(indice(c.xn1), c.c0 + 1)
    tabela.ncolunas = len(xs) - 1


def unir_continuacoes(tabelas: list[TabelaPagina]) -> list[TabelaPagina]:
    """Une fragmentos com o mesmo número. Cabeçalho repetido é descartado."""
    saida: list[TabelaPagina] = []
    principais: dict[str, TabelaPagina] = {}
    for tabela in tabelas:
        if tabela.numero is None or not tabela.continuacao or tabela.numero not in principais:
            if tabela.numero is not None and not tabela.continuacao:
                principais[tabela.numero] = tabela
            saida.append(tabela)
            continue
        principal = principais[tabela.numero]
        # O PyMuPDF pode detectar número de colunas diferente em cada página; a grade
        # é refeita pelas coordenadas, depois da união.
        k = _linhas_de_cabecalho_repetido(principal, tabela)  # linhas do fragmento a descartar
        novas = []
        for c in tabela.celulas:
            if c.r0 < k:
                continue
            novas.append(
                Celula(c.r0 - k + principal.nlinhas, c.r1 - k + principal.nlinhas,
                       c.c0, c.c1, c.bbox, c.texto, xn0=c.xn0, xn1=c.xn1)
            )
        principal.cabecalhos_descartados.extend(c.texto for c in tabela.celulas if c.r0 < k and c.texto)
        principal.celulas.extend(novas)
        principal.nlinhas = principal.nlinhas + tabela.nlinhas - k
        _regrade_colunas(principal)
        principal.notas.extend(tabela.notas)
        principal.paginas.extend(p for p in tabela.paginas if p not in principal.paginas)
        principal.bbox = (
            min(principal.bbox[0], tabela.bbox[0]),
            principal.bbox[1],
            max(principal.bbox[2], tabela.bbox[2]),
            max(principal.bbox[3], tabela.bbox[3]),
        )
    return saida


_DEFINICAO_RODAPE = re.compile(r"^\d+\)\s")


def _e_nota(texto: str) -> bool:
    return texto.startswith("NOTA") or bool(_DEFINICAO_RODAPE.match(texto))


def extrair_notas(tabela: TabelaPagina) -> None:
    """Tira da grade as células de nota ("NOTA …" ou "1) …") e as guarda em `notas`.

    Célula com várias definições "1) … 2) …" vira uma nota por definição.
    """
    notas = [c for c in tabela.celulas if _e_nota(c.texto)]
    if not notas:
        return
    for c in notas:
        if c.texto.startswith("NOTA"):
            tabela.notas.append(c.texto)
        else:
            partes = re.split(r"(?<=[.;])\s+(?=\d+\)\s)", c.texto)
            tabela.notas.extend(p.strip() for p in partes if p.strip())
    restantes = [c for c in tabela.celulas if not _e_nota(c.texto)]
    tabela.celulas, tabela.nlinhas, tabela.ncolunas = _compactar(restantes)


def _gfm_possivel(celulas: list[Celula], nlinhas: int, ncolunas: int) -> bool:
    for r in range(nlinhas):
        da_linha = [c for c in celulas if c.r0 == r]
        if any(c.r1 - c.r0 > 1 for c in da_linha):
            return False
        if any(c.c1 - c.c0 > 1 for c in da_linha):
            if not (len(da_linha) == 1 and da_linha[0].c0 == 0 and da_linha[0].c1 == ncolunas):
                return False
        elif len(da_linha) != ncolunas:
            return False
    return True


def _escapar(texto: str) -> str:
    return texto.replace("|", "\\|")


def renderizar(tabela: TabelaPagina) -> tuple[str, str]:
    """Devolve (markdown, formato) com formato 'gfm' ou 'html'."""
    if _gfm_possivel(tabela.celulas, tabela.nlinhas, tabela.ncolunas):
        return _gfm(tabela), "gfm"
    return _html(tabela), "html"


def _gfm(tabela: TabelaPagina) -> str:
    linhas_md = []
    for r in range(tabela.nlinhas):
        valores = [""] * tabela.ncolunas
        for c in tabela.celulas:
            if c.r0 != r:
                continue
            texto = c.texto
            if c.c1 - c.c0 > 1 and texto and r > 0:
                texto = f"**{texto}**" if not texto.startswith("**") else texto
            valores[c.c0] = _escapar(texto)
        linhas_md.append("| " + " | ".join(valores) + " |")
    cabecalho = linhas_md[0]
    separador = "| " + " | ".join(["---"] * tabela.ncolunas) + " |"
    return "\n".join([cabecalho, separador, *linhas_md[1:]])


def _html(tabela: TabelaPagina) -> str:
    partes = ["<table>"]
    for r in range(tabela.nlinhas):
        partes.append("<tr>")
        for c in sorted((c for c in tabela.celulas if c.r0 == r), key=lambda c: c.c0):
            atributos = ""
            if c.r1 - c.r0 > 1:
                atributos += f' rowspan="{c.r1 - c.r0}"'
            if c.c1 - c.c0 > 1:
                atributos += f' colspan="{c.c1 - c.c0}"'
            marcacao = "th" if r == 0 else "td"
            partes.append(f"<{marcacao}{atributos}>{c.texto}</{marcacao}>")
        partes.append("</tr>")
    partes.append("</table>")
    return "".join(partes)
