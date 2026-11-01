"""Etapa 11: validação da saída. Gera normas/<id>/revisao.md e diz se há bloqueantes.

Limites fixos (plano, Etapa 11). Não são afrouxados para passar.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from nbr2md.config import RAIZ, carregar_norma
from nbr2md.modelo import fonte_base

COBERTURA_PYMUPDF_MIN = 0.995
COBERTURA_PDFPLUMBER_MIN = 0.990
TEXTO_EXTRA_MAX = 0.002
PAGINA_ALERTA = 0.98

_SUP = str.maketrans({"²": "2", "³": "3", "¹": "1", "⁰": "0", "⁴": "4", "⁵": "5",
                      "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-", "⁺": "+"})
_PONTUACAO = ".,;:!?()[]{}\"'«»“”‘’–—-/|*#>•"
_PROIBIDOS = re.compile("[\uf000-\uf8ff]|ņ|ʊ|ǻ|\x94|□|\ufffd|⟦glifo:|\\(cid:")
_MARCA_CNPJ = re.compile(r"Exemplar para uso|CONNECTCOM|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|Pedido \d{5,}|Impresso:")
_CONTINUACAO_LEGENDA = re.compile(r"^Tabela \d+ \((?:continuação|conclusão)\)$")


_LETRA_DIGITO = re.compile(r"^([^\W\d_]+)(\d+)$")


def tokens(texto: str) -> list[str]:
    """Palavras normalizadas. 'mm2' e 'mm²' viram ['mm', '2'], como no PDF (sobrescrito é palavra à parte)."""
    texto = unicodedata.normalize("NFC", texto).translate(_SUP).lower()
    saida = []
    for palavra in texto.split():
        palavra = palavra.strip(_PONTUACAO)
        if not palavra or not re.search(r"\w", palavra):
            continue
        casa = _LETRA_DIGITO.match(palavra)
        if casa:
            saida.extend([casa.group(1), casa.group(2)])
        else:
            saida.append(palavra)
    return saida


def texto_do_markdown(md: str) -> str:
    """Texto que conta como norma: sem marcação, sem comentários, sem conteúdo de tags."""
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    md = re.sub(r"\[(imagem|formula|simbolo|rodape)(?: revisada)?\][\s\S]*?\[/\1\]", " ", md)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    # Nota de rodapé: o marcador [^p30-1] representa o "1)" do PDF (sobrescrito ou pé da página).
    md = re.sub(r"\[\^p\d+-(\d+)\]:?", r" \1 ", md)
    md = re.sub(r"\[\^[^\]]+\]:?", " ", md)
    md = re.sub(r"</?(?:sub|sup)>", "", md)  # sub/sup não separam palavra: "t<sub>1</sub>" é "t1"
    md = re.sub(r"</?(?:br|table|tr|td|th)[^>]*>", " ", md)
    md = re.sub(r"\*+", "", md)  # ênfase não separa palavra: "*I*<sub>Δn</sub>" é "IΔn"
    return md


def _sem_front_matter(md: str) -> str:
    if md.startswith("---\n"):
        fim = md.find("\n---\n", 4)
        if fim != -1:
            return md[fim + 5:]
    return md


def _linhas_pdf(pagina: dict, cfg: dict) -> list[str]:
    """Linhas do PDF limpo que contam como norma: exclui o que o plano manda descartar."""
    excluir = set()
    for regra in cfg.get("remover_linhas", []):
        if regra["pagina"] == pagina["pagina"]:
            excluir.update(regra["textos"])
    linhas = []
    for linha in pagina["linhas"]:
        texto = "".join(s["texto"] for s in linha["spans"]).strip()
        if not texto or texto in excluir or _CONTINUACAO_LEGENDA.match(texto):
            continue
        linhas.append(texto)
    return linhas


@dataclass
class Resultado:
    bloqueantes: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)
    pendencias: dict = field(default_factory=dict)
    paginas_baixas: list[tuple[int, float]] = field(default_factory=list)
    palavras_faltantes: list[str] = field(default_factory=list)


def _pdfplumber_tokens(pdf: Path, paginas_corpo: list[int], mapa: dict) -> tuple[Counter, int]:
    import pdfplumber

    contagem: Counter = Counter()
    nao_mapeados = 0
    with pdfplumber.open(pdf) as doc:
        for n in paginas_corpo:
            pagina = doc.pages[n - 1]
            altura = pagina.height
            pagina = pagina.filter(lambda o: o.get("object_type") != "char" or o.get("upright", True))
            for palavra in pagina.extract_words(x_tolerance=1.5, extra_attrs=["fontname"]):
                if palavra["top"] < 0.08 * altura or palavra["bottom"] > 0.92 * altura:
                    continue  # faixas de cabeçalho e rodapé (ver defaults.yaml)
                fonte = fonte_base(palavra.get("fontname", "").split("+")[-1])
                texto = palavra["text"]

                def trocar(casa):
                    nonlocal nao_mapeados
                    cid = int(casa.group(1))
                    caractere = mapa.get(fonte, {}).get(cid)
                    if caractere is None:
                        nao_mapeados += 1
                        return " "
                    return caractere

                texto = re.sub(r"\(cid:(\d+)\)", trocar, texto)
                contagem.update(tokens(texto))
    return contagem, nao_mapeados


def _resolver_juntadas(faltam: Counter, extras: Counter) -> None:
    """Segunda tentativa de casamento (plano, Etapa 11): uma palavra do Markdown que é
    a junção de duas palavras do PDF (ex.: 'ia' contra 'i' + 'a') não conta como erro.
    Modifica os dois contadores in place."""
    for palavra in list(extras):
        while extras[palavra] > 0:
            for i in range(1, len(palavra)):
                esquerda, direita = palavra[:i], palavra[i:]
                if faltam[esquerda] > 0 and faltam[direita] > 0:
                    faltam[esquerda] -= 1
                    faltam[direita] -= 1
                    extras[palavra] -= 1
                    break
            else:
                break


def _descontar(contagem: Counter, textos: list[str]) -> None:
    """Tira de `contagem` as palavras de `textos` (remoções deliberadas), sem ficar negativo."""
    for texto in textos:
        for palavra in tokens(texto):
            if contagem[palavra] > 0:
                contagem[palavra] -= 1


def validar(norma_id: str, pdf_pdfplumber: bool = True) -> Resultado:
    pasta_build = RAIZ / "build" / norma_id
    pasta_norma = RAIZ / "normas" / norma_id
    cfg = carregar_norma(norma_id)
    capa_paginas = set(cfg["paginas"]["capa"])
    ficha = set(cfg["paginas"].get("ficha", []))
    sumario = set(range(cfg["paginas"]["sumario"][0], cfg["paginas"]["sumario"][-1] + 1))
    res = Resultado()

    md = _sem_front_matter((pasta_norma / f"{norma_id}.md").read_text(encoding="utf-8"))
    saida = json.loads((pasta_build / "03-blocos.json").read_text(encoding="utf-8"))
    extracao = json.loads((pasta_build / "extracao.json").read_text(encoding="utf-8"))

    # ---------- cobertura (PyMuPDF) e texto extra ----------
    paginas_pdf = {}
    for arq in sorted((pasta_build / "02-limpo").glob("pagina-*.json")):
        dados = json.loads(arq.read_text(encoding="utf-8"))
        n = dados["pagina"]
        if n in capa_paginas or n in ficha or n in sumario:
            continue
        paginas_pdf[n] = Counter(tokens("\n".join(_linhas_pdf(dados, cfg))))
    pdf_total = Counter()
    for toks in paginas_pdf.values():
        pdf_total.update(toks)
    # Cabeçalhos de tabela repetidos nas continuações foram removidos de propósito (Etapa 7).
    descartados = [
        texto for b in saida["blocos"] if b["tipo"] == "tabela"
        for texto in b["extra"].get("cabecalhos_descartados", [])
    ]
    res.metricas["cabecalhos_repetidos_removidos"] = len(descartados)
    _descontar(pdf_total, descartados)

    md_texto = texto_do_markdown(md)
    md_total = Counter(tokens(md_texto))
    faltam = pdf_total - md_total
    extras = md_total - pdf_total
    _resolver_juntadas(faltam, extras)
    cobertura = 1 - sum(faltam.values()) / max(1, sum(pdf_total.values()))
    extra = sum(extras.values()) / max(1, sum(md_total.values()))
    res.metricas["cobertura_pymupdf"] = round(cobertura, 5)
    res.metricas["texto_extra"] = round(extra, 5)
    res.metricas["palavras_pdf"] = sum(pdf_total.values())
    res.metricas["palavras_md"] = sum(md_total.values())
    if cobertura < COBERTURA_PYMUPDF_MIN:
        res.bloqueantes.append(f"cobertura PyMuPDF {cobertura:.4%} < {COBERTURA_PYMUPDF_MIN:.1%}")
        faltam = pdf_total - md_total
        res.palavras_faltantes = [f"{p} ({c})" for p, c in faltam.most_common(40)]
    if extra > TEXTO_EXTRA_MAX:
        res.bloqueantes.append(f"texto extra {extra:.4%} > {TEXTO_EXTRA_MAX:.1%}")

    # por página (segmentos entre marcadores <!-- p. N -->)
    partes = re.split(r"<!-- p\. (\d+) -->", md)
    por_pagina_md: dict[int, Counter] = {}
    for i in range(1, len(partes), 2):
        por_pagina_md.setdefault(int(partes[i]), Counter()).update(
            tokens(texto_do_markdown(partes[i + 1])))
    for n, toks in paginas_pdf.items():
        total = sum(toks.values())
        if not total:
            continue
        feitas = sum(min(toks[t], por_pagina_md.get(n, Counter())[t]) for t in toks)
        taxa = feitas / total
        if taxa < PAGINA_ALERTA:
            res.paginas_baixas.append((n, round(taxa, 4)))

    # ---------- cobertura cruzada (pdfplumber) ----------
    if pdf_pdfplumber:
        pdf = RAIZ / cfg["fonte"]
        mapa = {f: {int(k): v for k, v in d.items()} for f, d in cfg["mapa_glifos"].items()}
        corpo = sorted(paginas_pdf)
        pl_total, nao_mapeados = _pdfplumber_tokens(pdf, corpo, mapa)
        _descontar(pl_total, descartados)
        cobertura_pl = sum(min(pl_total[t], md_total[t]) for t in pl_total) / max(1, sum(pl_total.values()))
        res.metricas["cobertura_pdfplumber"] = round(cobertura_pl, 5)
        res.metricas["cids_sem_mapa"] = nao_mapeados
        if cobertura_pl < COBERTURA_PDFPLUMBER_MIN:
            res.bloqueantes.append(f"cobertura pdfplumber {cobertura_pl:.4%} < {COBERTURA_PDFPLUMBER_MIN:.1%}")
        if nao_mapeados:
            res.bloqueantes.append(f"{nao_mapeados} (cid:N) do pdfplumber sem entrada em mapa_glifos")

    # ---------- caracteres proibidos e marca d'água ----------
    proibidos = _PROIBIDOS.findall(md)
    res.metricas["caracteres_proibidos"] = len(proibidos)
    if proibidos:
        res.bloqueantes.append(f"{len(proibidos)} caractere(s) proibido(s) no Markdown")
    cnpj = _MARCA_CNPJ.findall(md)
    res.metricas["marca_dagua_cnpj"] = len(cnpj)
    if cnpj:
        res.bloqueantes.append(f"{len(cnpj)} trecho(s) de marca d'água/CNPJ no Markdown")

    # ---------- marcadores balanceados ----------
    aberturas = Counter(re.findall(r"^\[(imagem|formula|simbolo|rodape)(?: revisada)?\]$", md, re.M))
    fechamentos = Counter(re.findall(r"^\[/(imagem|formula|simbolo|rodape)\]$", md, re.M))
    for nome in ("imagem", "formula", "simbolo", "rodape"):
        if aberturas[nome] != fechamentos[nome]:
            res.bloqueantes.append(f"marcadores [{nome}] desbalanceados: {aberturas[nome]} abre, {fechamentos[nome]} fecha")
    figuras = sum(1 for b in saida["blocos"] if b["tipo"] == "figura")
    if aberturas["imagem"] != figuras:
        res.bloqueantes.append(f"{aberturas['imagem']} blocos [imagem] para {figuras} figuras")

    # ---------- notas de rodapé ----------
    referencias = set(re.findall(r"\[\^([^\]]+)\](?!:)", md))
    definicoes = set(re.findall(r"^\[\^([^\]]+)\]:", md, re.M))
    pendentes_nota = {b["extra"]["chave"] for b in saida["blocos"] if b["tipo"] == "rodape_pendente"}
    sem_definicao = referencias - definicoes - pendentes_nota
    if sem_definicao:
        res.bloqueantes.append(f"marcadores de nota sem definição e sem pendência: {sorted(sem_definicao)}")
    res.metricas["notas_com_definicao"] = len(referencias & definicoes)
    res.pendencias["notas_sem_definicao_pendentes"] = sorted(referencias & pendentes_nota)
    orfas = definicoes - referencias
    if orfas:
        res.alertas.append(f"definições de nota sem marcador no texto: {sorted(orfas)}")

    # ---------- sumário contra árvore ----------
    titulos = {b["numero"] or "" for b in saida["blocos"] if b["tipo"] in ("titulo_secao", "anexo")}
    # Uma entrada por linha: número no início, pontilhado e página no fim.
    entradas = []
    for linha in saida["sumario_linhas"]:
        texto = linha["texto"]
        casa = re.match(r"^(\d+(?:\.\d+)*)\s+.+?\s*\.{3,}\s*\d+\s*$", texto)
        if casa:
            entradas.append(casa.group(1))
            continue
        casa = re.match(r"^Anexo ([A-Z])\b.*\.{3,}\s*\d+\s*$", texto)
        if casa:
            entradas.append(casa.group(1))
    faltantes = [e for e in dict.fromkeys(entradas) if e not in titulos]
    res.metricas["sumario_entradas"] = len(dict.fromkeys(entradas))
    if faltantes:
        res.bloqueantes.append(f"entradas do sumário sem seção correspondente: {faltantes[:20]}")

    # ---------- tabelas e figuras: lacunas pela numeração das legendas ----------
    # Legenda sem tabela/figura estruturada não é lacuna: fica em pendência (texto mantido).
    for tipo_legenda, tipo_bloco, rotulo, chave in (
        ("legenda_tabela", "tabela", "Tabela", "tabela_sem_estrutura"),
        ("legenda_figura", "figura", "Figura", "figura_sem_estrutura"),
    ):
        legendas = {b["numero"] for b in saida["blocos"] if b["tipo"] == tipo_legenda and b["numero"]}
        estruturados = {b["numero"] for b in saida["blocos"] if b["tipo"] == tipo_bloco and b["numero"]}
        grupos: dict[str, set[int]] = {}
        for n in legendas:
            prefixo, _, num = n.rpartition(".")
            grupos.setdefault(prefixo, set()).add(int(num) if num.isdigit() else 0)
        for prefixo, nums in grupos.items():
            ausentes = [i for i in range(1, max(nums) + 1) if i not in nums]
            if ausentes:
                etiqueta = f"{rotulo} {prefixo + '.' if prefixo else ''}".strip()
                res.bloqueantes.append(f"lacuna na numeração de {etiqueta}: faltam {ausentes}")
        res.pendencias[chave] = sorted(
            legendas - estruturados, key=lambda n: (n.rpartition(".")[0], int(n.rpartition(".")[2] or 0))
        )
    res.metricas["tabelas"] = sum(1 for b in saida["blocos"] if b["tipo"] == "tabela")
    res.metricas["figuras"] = figuras
    res.metricas["formulas"] = sum(1 for b in saida["blocos"] if b["tipo"] == "formula")
    res.metricas["simbolos"] = sum(1 for b in saida["blocos"] if b["tipo"] == "simbolo")

    # ---------- pendências (não bloqueiam; listadas) ----------
    res.pendencias["imagem"] = sum(1 for m in re.finditer(r"PENDENTE: descrição não escrita|PENDENTE: imagem da figura", md))
    res.pendencias["formula"] = md.count("[formula]\nPENDENTE")
    res.pendencias["simbolo"] = md.count("[simbolo]\nPENDENTE")
    res.pendencias["rodape"] = md.count("[rodape]\nPENDENTE")
    res.pendencias["tabelas_sem_legenda"] = len(saida.get("tabelas_sem_legenda", []))
    res.pendencias["tabelas_confianca_baixa"] = [
        f"Tabela {b['numero']} (p. {b['pagina']})" for b in saida["blocos"]
        if b["tipo"] == "tabela" and b["extra"].get("confianca") == "baixa"
    ]

    # ---------- numeração de seções: alerta ----------
    niveis = sorted(int(b["numero"]) for b in saida["blocos"]
                    if b["tipo"] == "titulo_secao" and b["numero"] and b["numero"].isdigit())
    if niveis:
        faltam = [i for i in range(1, max(niveis) + 1) if i not in niveis]
        if faltam:
            res.alertas.append(f"seções de 1º nível ausentes na sequência: {faltam}")
    return res


def gravar_revisao(norma_id: str, res: Resultado) -> Path:
    """normas/<id>/revisao.md: bloqueantes, métricas, pendências e alertas."""
    linhas = [f"# Revisão: {norma_id}", ""]
    estado = "OK, sem bloqueantes" if not res.bloqueantes else f"{len(res.bloqueantes)} BLOQUEANTE(S)"
    linhas += [f"**Estado:** {estado}", "", "## Bloqueantes", ""]
    linhas += [f"- {b}" for b in res.bloqueantes] or ["- nenhum"]
    linhas += ["", "## Métricas", ""]
    linhas += [f"- {k}: {v}" for k, v in res.metricas.items()]
    linhas += ["", "## Páginas com cobertura abaixo de 98%", ""]
    linhas += ["Tabelas unidas e parágrafos juntados entram no segmento da primeira página. "
               "Páginas de continuação aparecem baixas por esse motivo; o bloqueante é o total do documento.", ""]
    linhas += [f"- p. {n}: {t:.2%}" for n, t in res.paginas_baixas] or ["- nenhuma"]
    if res.palavras_faltantes:
        linhas += ["", "## Palavras faltantes (as mais frequentes)", ""]
        linhas += [f"- {p}" for p in res.palavras_faltantes]
    linhas += ["", "## Pendentes de revisão humana", ""]
    for chave, valor in res.pendencias.items():
        linhas.append(f"- {chave}: {valor}")
    linhas += ["", "## Alertas (não bloqueiam)", ""]
    linhas += [f"- {a}" for a in res.alertas] or ["- nenhum"]
    caminho = RAIZ / "normas" / norma_id / "revisao.md"
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho
