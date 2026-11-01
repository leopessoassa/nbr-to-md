"""Etapa 6: linhas visuais, agrupamento em blocos e juntura entre páginas.

Linha visual: spans da mesma altura que ficam lado a lado (ex.: número '1.1' e o
texto que o PyMuPDF devolve como duas linhas). Spans de colunas distantes (mais de
GAP_MAX pt) viram linhas visuais separadas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from nbr2md import figuras as fg
from nbr2md import inline
from nbr2md.classificar import Regras, atualiza_secao, classificar, extrair_capa, inicia_bloco
from nbr2md.classificar import _PUA
from nbr2md.modelo import Bloco

GAP_MAX = 25.0          # pt entre spans da mesma linha visual
TOLERANCIA_SOBREPOSICAO = 0.5
CONTINUACAO_GAP = 0.6   # fração da altura da linha para continuar o bloco
TIPOS_JUNTAVEIS = {"paragrafo", "paragrafo_numerado", "item_lista"}


@dataclass
class LinhaVisual:
    pagina: int
    spans: list[dict]
    bbox: tuple[float, float, float, float]
    tamanho: float
    negrito: bool
    italico: bool
    pua: bool
    texto: str                 # texto puro, espaços normalizados
    md: str                    # texto com marcação inline
    marcas: list[str] = field(default_factory=list)

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def centro_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def y1(self) -> float:
        return self.bbox[3]


def _agrupar_spans(spans: list[dict]) -> list[list[dict]]:
    """Agrupa spans em linhas visuais: mesma faixa vertical e separados por pouco espaço."""
    grupos: list[dict] = []  # {"spans": [...], "bbox": [x0,y0,x1,y1]}
    # Ordenar por x: sobrescritos começam acima da linha de base, e ordenar por y
    # mistura spans de linhas diferentes e separa o que está na mesma linha.
    for s in sorted(spans, key=lambda s: (s["bbox"][0], s["bbox"][1])):
        x0, y0, x1, y1 = s["bbox"]
        altura = y1 - y0
        melhor, melhor_gap = None, None
        for g in grupos:
            gx0, gy0, gx1, gy1 = g["bbox"]
            sobreposicao = min(y1, gy1) - max(y0, gy0)
            if sobreposicao < TOLERANCIA_SOBREPOSICAO * min(altura, gy1 - gy0):
                continue
            gap = max(x0 - gx1, gx0 - x1)
            if gap < -3 or gap > GAP_MAX:
                continue
            if melhor is None or gap < melhor_gap:
                melhor, melhor_gap = g, gap
        if melhor is None:
            grupos.append({"spans": [s], "bbox": [x0, y0, x1, y1]})
        else:
            melhor["spans"].append(s)
            gx0, gy0, gx1, gy1 = melhor["bbox"]
            melhor["bbox"] = [min(gx0, x0), min(gy0, y0), max(gx1, x1), max(gy1, y1)]
    return [g["spans"] for g in grupos]


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    return re.sub(r"\s+", " ", texto).strip()


FRACAO_ESPACO = 0.2  # fração do tamanho da fonte: afastamento que é espaço (espaço Arial = 0,28 em)


def _com_espacos(grupo: list[dict]) -> list[dict]:
    """Insere um span de espaço onde há afastamento visível e nenhum espaço no texto.

    Ex.: número '1.1' em negrito seguido de 'Esta Norma' (dois spans, sem espaço no texto).
    """
    saida: list[dict] = []
    for s in grupo:
        if saida:
            anterior = saida[-1]
            gap = s["bbox"][0] - anterior["bbox"][2]
            limite = FRACAO_ESPACO * max(anterior["tamanho"], 1.0)
            sem_espaco = not anterior["texto"][-1:].isspace() and not s["texto"][:1].isspace()
            # Subscrito/sobrescrito (outra linha de base ou outro tamanho) nunca ganha espaço:
            # "I" + "Δn" continua "IΔn".
            mesma_base = abs(s["origem_y"] - anterior["origem_y"]) < 0.8
            mesmo_corpo = abs(s["tamanho"] - anterior["tamanho"]) < 0.5
            if gap > limite and sem_espaco and mesma_base and mesmo_corpo and anterior["texto"] and s["texto"]:
                saida.append({**anterior, "texto": " ", "bbox": [anterior["bbox"][2], *anterior["bbox"][1:]]})
        saida.append(s)
    return saida


def linhas_visuais(pagina: dict) -> list[LinhaVisual]:
    spans = []
    for linha in pagina["linhas"]:
        for s in linha["spans"]:
            spans.append(s)
    linhas: list[LinhaVisual] = []
    for grupo in _agrupar_spans(spans):
        grupo.sort(key=lambda s: s["bbox"][0])
        grupo = _com_espacos(grupo)
        md, marcas = inline.marcar(grupo, pagina["pagina"])
        com_texto = [s for s in grupo if s["texto"].strip()]
        if not com_texto:
            continue
        tamanho = inline.mediana_ponderada(
            [(s["tamanho"], len(s["texto"].strip())) for s in com_texto]
        )
        x0 = min(s["bbox"][0] for s in grupo)
        y0 = min(s["bbox"][1] for s in grupo)
        x1 = max(s["bbox"][2] for s in grupo)
        y1 = max(s["bbox"][3] for s in grupo)
        linhas.append(
            LinhaVisual(
                pagina=pagina["pagina"],
                spans=grupo,
                bbox=(x0, y0, x1, y1),
                tamanho=tamanho,
                negrito=all(s.get("negrito") for s in com_texto),
                italico=all(s.get("italico") for s in com_texto),
                pua=any(_PUA.search(s["texto"]) for s in grupo),
                texto=_normalizar("".join(s["texto"] for s in grupo)),
                md=_normalizar(md),
                marcas=marcas,
            )
        )
    linhas.sort(key=lambda l: ((l.y0 + l.y1) / 2, l.x0))
    return linhas


def _agrupar_em_blocos(linhas: list[LinhaVisual], regras: Regras) -> list[list[LinhaVisual]]:
    blocos: list[list[LinhaVisual]] = []
    for linha in linhas:
        if not blocos:
            blocos.append([linha])
            continue
        atual = blocos[-1]
        primeira = atual[0]
        anterior = atual[-1]
        gap = linha.y0 - anterior.y1
        altura = max(anterior.tamanho, linha.tamanho) * 1.2
        perto = gap <= CONTINUACAO_GAP * altura
        if inicia_bloco(linha.texto, linha.negrito, regras):
            continuar = False
        elif primeira.negrito and linha.negrito and perto and abs(linha.x0 - primeira.x0) <= 8:
            continuar = True  # título em duas linhas
        elif (
            regras.anexo.match(primeira.texto)
            and gap <= 1.3 * altura
            and abs(linha.centro_x - primeira.centro_x) <= 12
        ):
            continuar = True  # título de anexo centralizado: "Anexo A", "(normativo)", título
        elif perto and linha.x0 >= primeira.x0 - 2 and not primeira.negrito:
            continuar = True
        else:
            continuar = False
        if continuar:
            atual.append(linha)
        else:
            blocos.append([linha])
    return blocos


def _montar_bloco(
    grupo: list[LinhaVisual], regras: Regras, secao_atual: str | None, indice: int
) -> tuple[Bloco, str | None]:
    primeira = grupo[0]
    tipo, numero = classificar(
        primeira.texto, primeira.negrito, regras, secao_atual, any(l.pua for l in grupo)
    )
    md = " ".join(l.md for l in grupo)
    md = re.sub(r" {2,}", " ", md).strip()
    marcas = [m for l in grupo for m in l.marcas]
    bloco = Bloco(
        id=f"p{primeira.pagina:03d}-b{indice:03d}",
        tipo=tipo,
        pagina=primeira.pagina,
        paginas=[primeira.pagina],
        bbox=(
            min(l.x0 for l in grupo),
            min(l.y0 for l in grupo),
            max(l.bbox[2] for l in grupo),
            max(l.y1 for l in grupo),
        ),
        texto_md=md,
        numero=numero,
        extra={
            "marcas_nota": marcas,
            "pua": any(l.pua for l in grupo),
            "tamanho": round(primeira.tamanho, 2),
        },
    )
    return bloco, atualiza_secao(tipo, numero, secao_atual)


def _juntar_paginas(blocos: list[Bloco]) -> list[Bloco]:
    """Une parágrafo que atravessa a quebra de página (Etapa 6, 'Juntar entre páginas')."""
    saida: list[Bloco] = []
    for bloco in blocos:
        if saida:
            anterior = saida[-1]
            if (
                anterior.tipo in TIPOS_JUNTAVEIS
                and bloco.tipo == "paragrafo"
                and bloco.pagina == anterior.paginas[-1] + 1
                and anterior.texto_md
                and anterior.texto_md[-1] not in ".:;"
                and bloco.texto_md[:1].islower()
            ):
                anterior.texto_md = f"{anterior.texto_md} {bloco.texto_md}"
                anterior.paginas = anterior.paginas + [bloco.pagina]
                anterior.bbox = (
                    min(anterior.bbox[0], bloco.bbox[0]),
                    min(anterior.bbox[1], bloco.bbox[1]),
                    max(anterior.bbox[2], bloco.bbox[2]),
                    max(anterior.bbox[3], bloco.bbox[3]),
                )
                continue
        saida.append(bloco)
    return saida


_CONTINUACAO_LEGENDA = re.compile(r"\((?:continuação|conclusão)\)")


def _dentro_de_algum(linha: LinhaVisual, areas: list[tuple]) -> bool:
    cx, cy = (linha.bbox[0] + linha.bbox[2]) / 2, (linha.bbox[1] + linha.bbox[3]) / 2
    return any(a[0] - 1 <= cx <= a[2] + 1 and a[1] - 1 <= cy <= a[3] + 1 for a in areas)


def _integrar_tabelas(
    por_pagina: dict[int, list[Bloco]],
    tabelas_pagina: dict[int, list],
) -> None:
    """Associa legendas, une continuações e grava os blocos de tabela e de nota (Etapa 7)."""
    from nbr2md import tabelas as tb

    for n in tabelas_pagina:
        for tabela in tabelas_pagina[n]:
            tb.extrair_notas(tabela)
    finais = tb.unir_continuacoes([t for n in sorted(tabelas_pagina) for t in tabelas_pagina[n]])

    # Legenda "(continuação)/(conclusão)" não se repete: a tabela já é uma só.
    for n in tabelas_pagina:
        if any(t.continuacao for t in tabelas_pagina[n]):
            por_pagina[n] = [
                b for b in por_pagina.get(n, [])
                if not (b.tipo == "legenda_tabela" and _CONTINUACAO_LEGENDA.search(b.texto_md))
            ]

    for tabela in finais:
        md, formato = tb.renderizar(tabela)
        pagina = tabela.pagina
        destino = por_pagina.setdefault(pagina, [])
        indice = sum(1 for b in destino if b.tipo == "tabela") + 1
        destino.append(
            Bloco(
                id=f"p{pagina:03d}-t{indice:02d}",
                tipo="tabela",
                pagina=pagina,
                paginas=list(tabela.paginas),
                bbox=tuple(tabela.bbox),
                texto_md=md,
                numero=tabela.numero,
                extra={
                    "formato": formato,
                    "sem_legenda": tabela.sem_legenda,
                    "continuacao_de_paginas": len(tabela.paginas) > 1,
                    "cabecalhos_descartados": tabela.cabecalhos_descartados,
                    "confianca": tabela.confianca,
                },
            )
        )
        for k, nota in enumerate(tabela.notas, start=1):
            casa = _RODAPE.match(nota)
            destino.append(
                Bloco(
                    id=f"p{pagina:03d}-n{indice:02d}{k:02d}",
                    tipo="rodape" if casa else "nota",
                    numero=casa.group(1) if casa else None,
                    pagina=pagina,
                    paginas=[pagina],
                    bbox=(tabela.bbox[0], tabela.bbox[3], tabela.bbox[2], tabela.bbox[3]),
                    texto_md=nota,
                    extra={"da_tabela": tabela.numero},
                )
            )
    for n in por_pagina:
        por_pagina[n].sort(key=lambda b: b.bbox[1])


_MARCA_NOTA = re.compile(r"\[\^(p\d+-\d+)\]")
_RODAPE = re.compile(r"^(\d+)\)\s")
_TAMANHO_RODAPE = 9.5  # pt: definições de nota ficam em corpo menor que 10 pt


def _texto_figura(regiao: fg.Regiao, legenda_titulo: str, revisao: dict | None = None) -> str:
    """Bloco da figura. Com `revisao` (hash conferido), a descrição do revisoes.yaml entra no bloco.

    revisado_por: ia -> marcador [imagem]; humano -> [imagem revisada] (Etapa 9).
    """
    partes = []
    if not regiao.sem_imagem and regiao.arquivo:
        partes.append(f"![{legenda_titulo}]({regiao.arquivo})")
    if revisao:
        marcador = "[imagem revisada]" if revisao.get("revisado_por") == "humano" else "[imagem]"
        partes.append(marcador)
        partes.append(revisao["descricao"].strip())
        if revisao.get("mermaid"):
            partes.append("```mermaid\n" + revisao["mermaid"].strip() + "\n```")
    else:
        partes.append("[imagem]")
        partes.append("PENDENTE: descrição não escrita." if not regiao.sem_imagem
                      else "PENDENTE: imagem da figura não localizada no PDF; descrição não escrita.")
    if regiao.rotulos:
        partes.append("Rótulos presentes na figura: " + ", ".join(f'"{r}"' for r in regiao.rotulos) + ".")
    partes.append("[/imagem]")
    return "\n".join(partes)


def _titulo_legenda(texto: str) -> str:
    return re.sub(r"\*+", "", texto).strip()


def _integrar_figuras_e_notas(
    por_pagina: dict[int, list[Bloco]],
    paginas: dict[int, dict],
    figuras_pagina: dict[int, list[fg.Regiao]],
    formulas_pagina: dict[int, list[fg.Regiao]],
    renderizador,
    revisoes: dict | None = None,
) -> None:
    """Blocos de figura e de fórmula, rodapés e pendências de nota (Etapas 8 e 6)."""
    for n, regioes in figuras_pagina.items():
        for idx, regiao in enumerate(regioes, start=1):
            arquivo, sha = None, None
            if not regiao.sem_imagem and regiao.bbox is not None:
                arquivo = f"assets/{fg.nome_figura(regiao.numero)}" if regiao.numero else (
                    f"assets/figura-p{n:03d}-{idx:02d}.png")
                if renderizador is not None:
                    sha = renderizador(n, regiao.bbox, arquivo)
            regiao.arquivo = arquivo
            titulo = _titulo_legenda(regiao.legenda or f"Figura {regiao.numero}")
            # Descrição só vale para o recorte que foi descrito (hash igual).
            rev = (revisoes or {}).get("figuras", {}).get(regiao.numero or "")
            if rev and sha and rev.get("hash_recorte") != sha:
                rev = None  # recorte mudou: volta a pendente e aparece no revisao.md
            por_pagina.setdefault(n, []).append(
                Bloco(
                    id=f"p{n:03d}-f{idx:02d}",
                    tipo="figura",
                    pagina=n,
                    paginas=[n],
                    bbox=regiao.bbox or (0.0, 0.0, 0.0, 0.0),
                    texto_md=_texto_figura(regiao, titulo, rev),
                    numero=regiao.numero,
                    extra={"arquivo": arquivo, "sha256": sha, "rotulos": regiao.rotulos,
                           "sem_imagem": regiao.sem_imagem, "legenda": titulo},
                )
            )
    for n, regioes in formulas_pagina.items():
        for idx, regiao in enumerate(regioes, start=1):
            arquivo = f"assets/equacao-p{n:03d}-{idx:02d}.png"
            sha = renderizador(n, regiao.bbox, arquivo) if renderizador is not None else None
            por_pagina.setdefault(n, []).append(
                Bloco(
                    id=f"p{n:03d}-e{idx:02d}",
                    tipo="formula",
                    pagina=n,
                    paginas=[n],
                    bbox=regiao.bbox,
                    texto_md=f"![Equação {regiao.numero or ''}]({arquivo})\n"
                             "[formula]\nPENDENTE: fórmula não transcrita.\n[/formula]",
                    numero=regiao.numero,
                    extra={"arquivo": arquivo, "sha256": sha},
                )
            )
    for n in por_pagina:
        por_pagina[n].sort(key=lambda b: b.bbox[1])

    # Notas de rodapé: definições (texto pequeno no pé da página) e marcadores sem definição.
    definicoes: set[str] = set()
    for n, blocos in por_pagina.items():
        altura = paginas[n]["altura"]
        for b in blocos:
            if b.tipo == "rodape" and b.numero:
                definicoes.add(f"p{n}-{b.numero}")
                continue
            casa = _RODAPE.match(b.texto_md)
            if (b.tipo == "paragrafo" and casa and b.extra.get("tamanho", 99) <= _TAMANHO_RODAPE
                    and b.bbox[1] > 0.5 * altura):
                b.tipo = "rodape"
                b.numero = casa.group(1)
                definicoes.add(f"p{n}-{casa.group(1)}")

    for n in list(por_pagina):
        novos: list[Bloco] = []
        pendentes = 0
        for b in por_pagina[n]:
            novos.append(b)
            for chave in dict.fromkeys(_MARCA_NOTA.findall(b.texto_md)):
                if chave in definicoes:
                    continue
                definicoes.add(chave)  # evita repetir o aviso para a mesma marca
                pendentes += 1
                novos.append(
                    Bloco(
                        id=f"p{n:03d}-r{pendentes:02d}",
                        tipo="rodape_pendente",
                        pagina=n,
                        paginas=[n],
                        bbox=b.bbox,
                        texto_md=(f"[rodape]\nPENDENTE: definição da nota [^{chave}] "
                                  "não localizada no PDF.\n[/rodape]"),
                        numero=None,
                        extra={"chave": chave},
                    )
                )
        por_pagina[n] = novos


def _integrar_simbolos(por_pagina, simbolos_pagina, renderizador) -> None:
    """Símbolos em frase: bloco [simbolo] com PENDENTE, na altura da imagem."""
    for n, regioes in simbolos_pagina.items():
        for idx, regiao in enumerate(regioes, start=1):
            arquivo = f"assets/simbolo-p{n:03d}-{idx:02d}.png"
            sha = renderizador(n, regiao.bbox, arquivo) if renderizador is not None else None
            por_pagina.setdefault(n, []).append(
                Bloco(
                    id=f"p{n:03d}-s{idx:02d}",
                    tipo="simbolo",
                    pagina=n,
                    paginas=[n],
                    bbox=regiao.bbox,
                    texto_md=f"![Símbolo]({arquivo})\n[simbolo]\nPENDENTE: símbolo não transcrito.\n[/simbolo]",
                    numero=None,
                    extra={"arquivo": arquivo, "sha256": sha},
                )
            )
    for n in por_pagina:
        por_pagina[n].sort(key=lambda b: b.bbox[1])


def processar(
    paginas: dict[int, dict],
    cfg: dict,
    renderizador=None,
    revisoes: dict | None = None,
) -> dict:
    """Etapa 6 completa sobre as páginas limpas.

    Devolve {"blocos", "capa", "sumario_linhas", "paginas_ignoradas"}.
    Capa e sumário não viram blocos do corpo.
    """
    regras = Regras.de_config(cfg)
    capa_paginas = set(cfg["paginas"]["capa"])
    ficha_paginas = set(cfg["paginas"].get("ficha", []))
    sumario_intervalo = cfg["paginas"]["sumario"]
    sumario = set(range(sumario_intervalo[0], sumario_intervalo[-1] + 1))

    from nbr2md import tabelas as tb

    capa: dict = {}
    sumario_linhas: list[dict] = []
    secao_atual: str | None = None
    ignoradas: list[int] = []
    por_pagina: dict[int, list[Bloco]] = {}
    tabelas_pagina: dict[int, list[tb.TabelaPagina]] = {}

    # Tabelas primeiro: as linhas que caem dentro delas saem do fluxo de texto.
    for numero in sorted(paginas):
        if numero in capa_paginas or numero in ficha_paginas or numero in sumario:
            continue
        tabelas_pagina[numero] = tb.tabelas_da_pagina(paginas[numero])

    # Legendas "Tabela N" lidas das linhas visuais, antes de montar os blocos.
    legendas_pre: dict[int, list[dict]] = {}
    for numero in tabelas_pagina:
        legendas_pre[numero] = [
            {"numero": regras.tabela.match(l.texto).group("num"), "texto_md": l.texto, "bbox": l.bbox}
            for l in linhas_visuais(paginas[numero])
            if regras.tabela.match(l.texto)
        ]
    tb.associar(tabelas_pagina, legendas_pre)
    # Todas as caixas de tabela detectadas, inclusive as sem legenda: imagens dentro delas
    # são conteúdo de tabela, não fórmula.
    caixas_tabela = {n: [t.bbox for t in ts] for n, ts in tabelas_pagina.items()}
    tabelas_sem_legenda: list[dict] = []
    for numero in tabelas_pagina:
        mantidas = []
        for tabela in tabelas_pagina[numero]:
            if tabela.sem_legenda:
                # Não vira tabela: o texto continua no fluxo e a tabela vai para revisão.
                tabelas_sem_legenda.append(
                    {"pagina": numero, "bbox": list(tabela.bbox),
                     "linhas": tabela.nlinhas, "colunas": tabela.ncolunas}
                )
            else:
                mantidas.append(tabela)
        tabelas_pagina[numero] = mantidas

    # Figuras e fórmulas em imagem: as regiões saem do fluxo de texto (rótulos incluídos).
    figuras_pagina: dict[int, list[fg.Regiao]] = {}
    areas_figura: dict[int, list] = {}
    formulas_pagina: dict[int, list[fg.Regiao]] = {}
    simbolos_pagina: dict[int, list[fg.Regiao]] = {}
    for numero in sorted(paginas):
        if numero in capa_paginas or numero in ficha_paginas or numero in sumario:
            continue
        vis = linhas_visuais(paginas[numero])
        areas_tab = caixas_tabela.get(numero, [])
        legs = [
            (regras.figura.match(l.texto).group("num"), l.texto, l)
            for l in vis if regras.figura.match(l.texto)
        ]
        regs, areas = fg.detectar_figuras(paginas[numero], vis, legs, areas_tab)
        forms, simb, _ = fg.detectar_formulas(paginas[numero], vis, areas_tab, areas)
        figuras_pagina[numero] = regs
        areas_figura[numero] = areas
        formulas_pagina[numero] = forms
        simbolos_pagina[numero] = simb

    for numero in sorted(paginas):
        visuais = linhas_visuais(paginas[numero])
        if numero in capa_paginas:
            capa.update(extrair_capa([_resumo(l) for l in visuais]))
            ignoradas.append(numero)
            continue
        if numero in ficha_paginas:  # direitos autorais: não é texto normativo
            ignoradas.append(numero)
            continue
        if numero in sumario:
            sumario_linhas.extend({"pagina": numero, "texto": l.texto} for l in visuais)
            ignoradas.append(numero)
            continue
        # Só o texto dentro de células sai do fluxo. Texto na caixa da tabela e fora
        # de qualquer célula (ex.: notas de rodapé logo abaixo) continua no fluxo.
        areas = [c.bbox for t in tabelas_pagina.get(numero, []) for c in t.celulas]
        areas += areas_figura.get(numero, [])
        visuais = [l for l in visuais if not _dentro_de_algum(l, areas)]
        for regra in cfg.get("remover_linhas", []):
            if regra["pagina"] == numero:
                visuais = [l for l in visuais if l.texto not in regra["textos"]]
        grupos = _agrupar_em_blocos(visuais, regras)
        por_pagina[numero] = []
        for indice, grupo in enumerate(grupos, start=1):
            bloco, secao_atual = _montar_bloco(grupo, regras, secao_atual, indice)
            por_pagina[numero].append(bloco)

    _integrar_tabelas(por_pagina, tabelas_pagina)
    _integrar_figuras_e_notas(por_pagina, paginas, figuras_pagina, formulas_pagina, renderizador, revisoes)
    _integrar_simbolos(por_pagina, simbolos_pagina, renderizador)

    blocos: list[Bloco] = []
    for numero in sorted(por_pagina):
        blocos.extend(por_pagina[numero])
    blocos = _juntar_paginas(blocos)
    return {
        "blocos": [b.para_dict() for b in blocos],
        "capa": capa,
        "sumario_linhas": sumario_linhas,
        "paginas_ignoradas": ignoradas,
        "tabelas_sem_legenda": tabelas_sem_legenda,
    }


def _resumo(linha: LinhaVisual) -> dict:
    return {
        "texto": linha.texto,
        "negrito": linha.negrito,
        "italico": linha.italico,
        "tamanho": linha.tamanho,
    }
