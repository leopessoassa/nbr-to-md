"""Etapa 5: marcação inline de spans (subscrito, sobrescrito, unidades, notas, estilo).

Regras (docs/PLANO-CONVERSAO.md, Etapa 5):
- tamanho de referência = mediana ponderada (por caracteres) dos tamanhos da linha;
- linha de base de referência = mediana ponderada da linha de base dos spans de tamanho normal;
- span menor que razao × referência e deslocado para baixo é subscrito; para cima, sobrescrito;
- sobrescrito `\\d+\\)` logo após palavra ou número é marcador de nota de rodapé;
- sobrescrito numérico após unidade vira caractere Unicode (m², mm³, 10⁻³); senão <sup>;
- negrito e itálico são juntados em trechos antes de virar ** e *.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RAZAO_TAMANHO = 0.88
DESLOCAMENTO_MIN = 0.8  # pt

UNIDADES = {
    "m", "mm", "cm", "km", "s", "ms", "µs", "μs", "ns", "mg", "g", "kg", "t",
    "h", "min", "A", "V", "W", "kV", "mV", "Hz", "kHz", "MHz", "Ω", "K", "Pa", "mm²", "m³",
}
_SUP_UNICODE = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
    "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻", "+": "⁺",
}
_NOTA_RODAPE = re.compile(r"^\d+\)$")
_NUMERO_SUP = re.compile(r"^-?\d+$")
_PALAVRA_FINAL = re.compile(r"([A-Za-zµμΩ]+)$")


@dataclass
class Segmento:
    texto: str
    posicao: str   # "normal" | "sub" | "sup"
    negrito: bool
    italico: bool


def mediana_ponderada(pares: list[tuple[float, int]]) -> float:
    pares = sorted((v, p) for v, p in pares if p > 0)
    if not pares:
        return 0.0
    total = sum(p for _, p in pares)
    acumulado = 0
    for valor, peso in pares:
        acumulado += peso
        if acumulado * 2 >= total:
            return valor
    return pares[-1][0]


def classificar_posicao(tamanho: float, origem_y: float, ref: float, base: float) -> str:
    if tamanho >= RAZAO_TAMANHO * ref:
        return "normal"
    deslocamento = origem_y - base
    if deslocamento >= DESLOCAMENTO_MIN:
        return "sub"
    if -deslocamento >= DESLOCAMENTO_MIN:
        return "sup"
    return "normal"


def segmentos(spans: list[dict]) -> list[Segmento]:
    """Converte spans (dicts limpos) em segmentos com posição e estilo, juntando vizinhos iguais."""
    com_texto = [s for s in spans if s["texto"].strip()]
    ref = mediana_ponderada([(s["tamanho"], len(s["texto"].strip())) for s in com_texto])
    base = mediana_ponderada(
        [
            (s["origem_y"], len(s["texto"].strip()))
            for s in com_texto
            if s["tamanho"] >= RAZAO_TAMANHO * ref
        ]
    )
    brutos: list[Segmento] = []
    for s in spans:
        if not s["texto"]:
            continue
        posicao = classificar_posicao(s["tamanho"], s["origem_y"], ref, base)
        estilo = posicao == "normal"
        brutos.append(
            Segmento(
                texto=s["texto"],
                posicao=posicao,
                negrito=estilo and bool(s.get("negrito")),
                italico=estilo and bool(s.get("italico")),
            )
        )
    juntados: list[Segmento] = []
    for seg in brutos:
        if juntados:
            ant = juntados[-1]
            if (ant.posicao, ant.negrito, ant.italico) == (seg.posicao, seg.negrito, seg.italico):
                ant.texto += seg.texto
                continue
        juntados.append(Segmento(seg.texto, seg.posicao, seg.negrito, seg.italico))
    return juntados


def _envolver(texto: str, marca: str) -> str:
    """Aplica marcação só ao miolo, mantendo espaços das pontas fora dela."""
    nucleo = texto.strip()
    if not nucleo:
        return texto
    inicio = texto[: len(texto) - len(texto.lstrip())]
    fim = texto[len(texto.rstrip()):]
    return f"{inicio}{marca}{nucleo}{marca}{fim}"


def _sobrescrito_unicode(texto: str) -> str | None:
    if not _NUMERO_SUP.match(texto):
        return None
    try:
        return "".join(_SUP_UNICODE[c] for c in texto)
    except KeyError:
        return None


def _unidade_antes(acumulado: str) -> bool:
    casa = _PALAVRA_FINAL.search(acumulado)
    return bool(casa) and casa.group(1) in UNIDADES


def marcar(spans: list[dict], pagina: int) -> tuple[str, list[str]]:
    """Devolve (texto em Markdown, marcas de nota de rodapé usadas)."""
    saida = ""
    marcas: list[str] = []
    for seg in segmentos(spans):
        if seg.posicao == "sup":
            nucleo = seg.texto.strip()
            if _NOTA_RODAPE.match(nucleo) and saida and saida[-1].isalnum():
                n = nucleo[:-1]
                chave = f"p{pagina}-{n}"
                marcas.append(chave)
                saida += f"[^{chave}]"
                continue
            unicode_sup = _sobrescrito_unicode(nucleo) if _unidade_antes(saida) else None
            if unicode_sup is not None:
                saida += _substituir_nucleo(seg.texto, unicode_sup)
            else:
                saida += _tag(seg.texto, "sup")
        elif seg.posicao == "sub":
            saida += _tag(seg.texto, "sub")
        else:
            marca = ""
            if seg.negrito:
                marca += "**"
            if seg.italico:
                marca += "*"
            saida += _envolver(seg.texto, marca) if marca else seg.texto
    saida = re.sub(r" {2,}", " ", saida).strip()
    return saida, marcas


def _tag(texto: str, tag: str) -> str:
    nucleo = texto.strip()
    if not nucleo:
        return texto
    return _substituir_nucleo(texto, f"<{tag}>{nucleo}</{tag}>")


def _substituir_nucleo(texto: str, novo: str) -> str:
    """Troca o miolo de `texto` por `novo`, mantendo os espaços das pontas."""
    inicio = texto[: len(texto) - len(texto.lstrip())]
    fim = texto[len(texto.rstrip()):]
    return f"{inicio}{novo}{fim}"
