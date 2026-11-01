"""Etapa 8: regiões de figuras e de fórmulas em imagem.

Figura: a legenda "Figura N — …" fica abaixo da figura. A região é a união das
imagens entre o fim da legenda anterior e o topo desta legenda. Textos dentro da
região são rótulos da figura e saem do fluxo de texto.

Fórmula em imagem: imagem com menos de 60 pt de altura fora de tabela e de figura.
Imagens dentro de tabela são conteúdo de célula e não viram fórmula.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MARGEM = 3.0           # pt de folga em volta da região
ALTURA_FORMULA = 60.0  # pt: imagem menor que isso pode ser fórmula


@dataclass
class Regiao:
    tipo: str                               # "figura" | "formula"
    pagina: int
    bbox: tuple[float, float, float, float] | None
    numero: str | None = None
    legenda: str | None = None               # texto da legenda, para figuras
    rotulos: list[str] = field(default_factory=list)
    arquivo: str | None = None               # caminho relativo a normas/<id>/
    sem_imagem: bool = False


def _centro(bbox) -> tuple[float, float]:
    return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


def _no_interior(bbox, areas) -> bool:
    cx, cy = _centro(bbox)
    return any(a[0] - 1 <= cx <= a[2] + 1 and a[1] - 1 <= cy <= a[3] + 1 for a in areas)


def nome_figura(numero: str) -> str:
    """'7' -> figura-07.png; 'D.1' -> figura-d-01.png (anexos)."""
    if "." in numero:
        letra, sub = numero.split(".", 1)
        return f"figura-{letra.lower()}-{int(sub):02d}.png"
    return f"figura-{int(numero):02d}.png"


def _imagens_do_corpo(pagina: dict, areas_tabela: list) -> list[tuple]:
    largura, altura = pagina["largura"], pagina["altura"]
    saida = []
    for img in pagina["imagens"]:
        x0, y0, x1, y1 = img["bbox"]
        if (x1 - x0) * (y1 - y0) >= 0.85 * largura * altura:
            continue  # imagem de fundo (já filtrada na limpeza; cinto de segurança)
        if _no_interior(img["bbox"], areas_tabela):
            continue
        saida.append(tuple(img["bbox"]))
    return saida


def detectar_figuras(
    pagina: dict,
    linhas: list,
    legendas: list[tuple],
    areas_tabela: list,
) -> tuple[list[Regiao], list[tuple]]:
    """Regiões de figuras da página.

    `linhas` são LinhaVisual; `legendas` são (numero, texto, LinhaVisual) já lidas.
    Devolve (regiões, áreas a retirar do fluxo de texto).
    """
    imagens = _imagens_do_corpo(pagina, areas_tabela)
    usadas: set[int] = set()
    regioes: list[Regiao] = []
    areas: list[tuple] = []
    anterior_fim = 0.0
    legenda_linhas = {id(linha) for _, _, linha in legendas}

    for numero, texto, linha in sorted(legendas, key=lambda t: t[2].bbox[1]):
        topo = linha.bbox[1]
        indices = [
            k for k, img in enumerate(imagens)
            if k not in usadas and img[1] >= anterior_fim - 1 and img[3] <= topo + 2
        ]
        usadas.update(indices)
        if not indices:
            regioes.append(Regiao("figura", pagina["pagina"], None, numero, texto, sem_imagem=True))
        else:
            x0 = min(imagens[k][0] for k in indices) - MARGEM
            y0 = min(imagens[k][1] for k in indices) - MARGEM
            x1 = max(imagens[k][2] for k in indices) + MARGEM
            y1 = min(max(imagens[k][3] for k in indices) + MARGEM, topo - 1)
            bbox = (max(0.0, x0), max(0.0, y0), x1, y1)
            rotulos = [
                l.texto for l in linhas
                if id(l) not in legenda_linhas and _no_interior(l.bbox, [bbox])
            ]
            regioes.append(
                Regiao("figura", pagina["pagina"], bbox, numero, texto, rotulos=rotulos)
            )
            areas.append(bbox)
        anterior_fim = linha.bbox[3]
    return regioes, areas


def _texto_ao_lado(bbox, linhas, distancia: float = 30.0) -> bool:
    """Há texto na mesma faixa vertical, perto da imagem? Então é símbolo em frase."""
    x0, y0, x1, y1 = bbox
    for l in linhas:
        lx0, ly0, lx1, ly1 = l.bbox
        if min(y1, ly1) - max(y0, ly0) <= 0.5 * min(y1 - y0, ly1 - ly0):
            continue
        if l.texto.endswith(")") and "(" in l.texto:
            continue  # número de equação "(3)" na mesma linha não conta como frase
        if max(x0 - lx1, lx0 - x1) <= distancia:
            return True
    return False


def detectar_formulas(
    pagina: dict,
    linhas: list,
    areas_tabela: list,
    areas_figura: list,
) -> tuple[list[Regiao], int]:
    """Imagens pequenas fora de tabela e de figura.

    Devolve (fórmulas, símbolos em frase, imagens dentro de tabela).
    """
    largura, altura = pagina["largura"], pagina["altura"]
    regioes: list[Regiao] = []
    simbolos: list[Regiao] = []
    em_tabela = 0
    for img in pagina["imagens"]:
        x0, y0, x1, y1 = img["bbox"]
        if (x1 - x0) * (y1 - y0) >= 0.85 * largura * altura:
            continue
        if y1 - y0 >= ALTURA_FORMULA:
            continue
        if _no_interior(img["bbox"], areas_tabela):
            em_tabela += 1
            continue
        if _no_interior(img["bbox"], areas_figura):
            continue
        if _texto_ao_lado(img["bbox"], linhas):
            # símbolo dentro de frase (ex.: isolação dupla): bloco [simbolo] próprio
            simbolos.append(
                Regiao("simbolo", pagina["pagina"],
                       (max(0.0, x0 - MARGEM), max(0.0, y0 - MARGEM), x1 + MARGEM, y1 + MARGEM))
            )
            continue
        cy = (y0 + y1) / 2
        tag = None
        for l in linhas:
            if abs(((l.bbox[1] + l.bbox[3]) / 2) - cy) <= 8 and l.texto.endswith(")"):
                casa = l.texto.rsplit("(", 1)
                if len(casa) == 2 and casa[1][:-1].isdigit():
                    tag = casa[1][:-1]
        regioes.append(
            Regiao(
                "formula",
                pagina["pagina"],
                (max(0.0, x0 - MARGEM), max(0.0, y0 - MARGEM), x1 + MARGEM, y1 + MARGEM),
                numero=tag,
            )
        )
    return regioes, simbolos, em_tabela
