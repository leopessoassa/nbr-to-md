"""Etapa 10: chunks.jsonl (RAG) e termos.json (Seção 3).

Um chunk por cláusula numerada, definição, tabela, figura, fórmula ou símbolo.
Parágrafos sem número entram no chunk da cláusula ou seção em curso.
"""

from __future__ import annotations

import re

LIMITE_CARACTERES = 6000   # ~1500 tokens (estimativa: caracteres / 4)
_REFERENCIA = re.compile(
    r"Tabela \d+|Figura [A-Z]?\.?\d+|Anexo [A-Z]\b|\b\d+(?:\.\d+)+\b"
)
_TIPOS_PROPRIOS = {"paragrafo_numerado": "requisito", "definicao": "definicao",
                   "tabela": "tabela", "figura": "figura", "formula": "formula",
                   "simbolo": "simbolo"}


def _referencias(texto: str) -> list[str]:
    vistos: list[str] = []
    for achado in _REFERENCIA.findall(texto):
        if achado not in vistos:
            vistos.append(achado)
    return vistos


def gerar_chunks(saida: dict, norma_id: str, norma_completa: str) -> list[dict]:
    chunks: list[dict] = []
    caminho: list[str] = []
    pilha: list[tuple[int, str]] = []
    secao = None
    atual: dict | None = None
    contador: dict[str, int] = {}

    def novo(tipo: str, numero: str | None) -> dict:
        base = f"{norma_id}#{numero or 'sem-numero'}"
        contador[base] = contador.get(base, 0) + 1
        ident = base if contador[base] == 1 else f"{base}-{contador[base]}"
        return {
            "id": ident,
            "norma": norma_completa,
            "secao": numero,
            "caminho": list(caminho),
            "tipo": tipo,
            "paginas": [],
            "texto": "",
        }

    def fechar() -> None:
        nonlocal atual
        if atual is None:
            return
        atual["referencias"] = _referencias(atual["texto"])
        chunks.append(atual)
        atual = None

    def acrescentar(bloco: dict, texto: str) -> None:
        nonlocal atual
        if atual is not None and len(atual["texto"]) + len(texto) > LIMITE_CARACTERES:
            fechar()
        if atual is None:
            atual = novo("requisito" if secao else "contexto", secao)
        atual["texto"] = f"{atual['texto']}\n\n{texto}".strip()
        for p in bloco["paginas"]:
            if p not in atual["paginas"]:
                atual["paginas"].append(p)

    for bloco in saida["blocos"]:
        tipo = bloco["tipo"]
        texto = bloco["texto_md"]
        if tipo == "tabela" and len(texto) > LIMITE_CARACTERES:
            # Tabela grande: partes por grupos de linhas, cabeçalho repetido em cada parte.
            fechar()
            for parte in _dividir_tabela(texto):
                atual = novo("tabela", bloco["numero"])
                atual["texto"] = parte
                atual["paginas"] = list(bloco["paginas"])
                atual["parte_de_tabela"] = True
                fechar()
            continue
        if tipo == "titulo_secao" or tipo == "anexo":
            fechar()
            titulo = re.sub(r"\*+", "", texto).strip()
            numero = bloco["numero"]
            nivel = (numero or "").count(".") + 1 if numero and numero.isdigit() else 1
            # pilha de ancestrais: um título de nível n descarta os de nível >= n
            pilha = [(n, t) for n, t in pilha if n < nivel]
            pilha.append((nivel, titulo))
            caminho = [t for _, t in pilha]
            secao = numero if numero else None
            continue
        if tipo in _TIPOS_PROPRIOS:
            fechar()
            atual = novo(_TIPOS_PROPRIOS[tipo], bloco["numero"] or secao)
            atual["texto"] = texto
            atual["paginas"] = list(bloco["paginas"])
            if tipo in ("tabela", "figura", "formula", "simbolo"):
                if tipo == "figura":
                    atual["imagem"] = bloco["extra"].get("arquivo")
                    atual["descricao_revisada"] = False
                if tipo == "formula":
                    atual["formula_revisada"] = False
                fechar()
            continue
        if tipo in ("legenda_tabela", "legenda_figura"):
            fechar()
            acrescentar(bloco, texto)
            continue
        acrescentar(bloco, texto)
    fechar()
    return chunks


def _dividir_tabela(texto: str) -> list[str]:
    """Divide uma tabela em partes de até LIMITE_CARACTERES, repetindo o cabeçalho.

    GFM: cabeçalho = primeiras duas linhas (título e separador). HTML: linhas <tr>.
    """
    if texto.startswith("<table>"):
        # HTML: a primeira <tr> é o cabeçalho; as demais são o corpo.
        trs = re.findall(r"<tr>.*?</tr>", texto, flags=re.S)
        cabecalho, corpo = trs[0], trs[1:]
        abertura, fecho, sep = "<table>", "</table>", ""
    else:
        # GFM: título da tabela (primeira linha) + separador (segunda); depois as linhas.
        linhas = texto.split("\n")
        cabecalho, corpo = "\n".join(linhas[:2]), linhas[2:]
        abertura, fecho, sep = "", "", "\n"
    partes: list[str] = []
    atual: list[str] = []
    tamanho = len(abertura) + len(cabecalho) + len(fecho)
    for linha in corpo:
        if atual and tamanho + len(linha) + 1 > LIMITE_CARACTERES:
            partes.append(abertura + sep.join([cabecalho, *atual]) + fecho)
            atual, tamanho = [], len(abertura) + len(cabecalho) + len(fecho)
        atual.append(linha)
        tamanho += len(linha) + 1
    partes.append(abertura + sep.join([cabecalho, *atual]) + fecho)
    return partes


_RE_DEFINICAO = re.compile(
    r"^\*\*(?P<num>\d+(?:\.\d+)+)\s+(?P<termo>[^*]+?)\*\*\s*(?P<qual>\([^)]*\))?\s*:?\s*(?P<def>.*)$",
    re.S,
)
_RE_INGLES = re.compile(r"^\*?Em inglês:\s*(?P<en>.+?)\*?$", re.S)


def interpretar_definicao(texto: str) -> dict | None:
    """Número, termo (com qualificador entre parênteses) e texto de uma definição da Seção 3.

    '**3.1.1 componente** (de uma instalação elétrica): Termo...' ->
    termo 'componente (de uma instalação elétrica)'. Devolve None se não reconhecer o formato.
    """
    casa = _RE_DEFINICAO.match(texto.strip())
    if not casa:
        return None
    termo = casa.group("termo").strip().rstrip(":").strip()
    if casa.group("qual"):
        termo = f"{termo} {casa.group('qual')}"
    return {"numero": casa.group("num"), "termo": termo, "definicao": casa.group("def").strip()}


def gerar_termos(saida: dict) -> list[dict]:
    """Definições da Seção 3. termo_en vem da linha '*Em inglês: …*' logo após a definição, se houver."""
    termos = []
    blocos = saida["blocos"]
    for i, bloco in enumerate(blocos):
        if bloco["tipo"] != "definicao":
            continue
        info = interpretar_definicao(bloco["texto_md"]) or {
            "numero": bloco["numero"],
            "termo": bloco["texto_md"].replace("**", "").strip(),
            "definicao": "",
        }
        termo_en = None
        if i + 1 < len(blocos):
            casa_en = _RE_INGLES.match(blocos[i + 1]["texto_md"].strip())
            if casa_en:
                termo_en = casa_en.group("en").strip()
        termos.append({"numero": info["numero"], "termo": info["termo"],
                       "termo_en": termo_en, "definicao": info["definicao"]})
    return termos
