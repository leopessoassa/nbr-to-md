"""Etapa 6: classificação de cada linha visual em tipo de bloco, e extração da capa.

Ordem de teste conforme a tabela da Etapa 6 do plano. As regexes vêm de
`config` (seção `estrutura`), para que outra norma ajuste só o YAML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PUA = re.compile("[\U0000f000-\U0000f8ff]")
_MARCADORES_DEFAULT = ("—", "–", "•", "-")
_DATA = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


@dataclass
class Regras:
    secao: re.Pattern
    anexo: re.Pattern
    tabela: re.Pattern
    figura: re.Pattern
    nota: re.Pattern
    exemplo: re.Pattern
    item_letra: re.Pattern
    marcadores: tuple[str, ...]
    preliminares: tuple[str, ...]

    @classmethod
    def de_config(cls, cfg: dict) -> "Regras":
        e = cfg["estrutura"]
        return cls(
            preliminares=tuple(e.get("secoes_preliminares", [])),
            secao=re.compile(e["regex_secao"]),
            anexo=re.compile(e["regex_anexo"]),
            tabela=re.compile(e["regex_tabela"]),
            figura=re.compile(e["regex_figura"]),
            nota=re.compile(e["regex_nota"]),
            exemplo=re.compile(e["regex_exemplo"]),
            item_letra=re.compile(e["regex_item_letra"]),
            marcadores=tuple(e.get("marcadores_lista", _MARCADORES_DEFAULT)),
        )


def numero_secao(texto: str, regras: Regras, negrito: bool = False) -> tuple[str, str] | None:
    """Número e resto de uma linha numerada, ou None.

    Regras para não confundir texto corrido com número de seção:
    - um número seguido de dígito (ex.: '2 000 m') não é seção;
    - letra sem ponto ('A Associação...') só é seção em negrito (anexo: 'A.1' tem ponto);
    - número sem ponto ('1 Objetivo') só é seção em negrito.
    """
    casa = regras.secao.match(texto)
    if not casa:
        return None
    resto = casa.group("resto")
    if not resto or resto[0].isdigit():
        return None
    numero = casa.group("num")
    if "." not in numero and not negrito:
        return None
    return numero, resto


def inicia_bloco(texto: str, negrito: bool, regras: Regras) -> bool:
    """True quando a linha começa um bloco novo (não é continuação da anterior)."""
    if numero_secao(texto, regras, negrito):
        return True
    if re.match(r"^\d+\)\s", texto):  # definição de nota de rodapé
        return True
    if (
        regras.anexo.match(texto)
        or regras.tabela.match(texto)
        or regras.figura.match(texto)
        or regras.nota.match(texto)
        or regras.exemplo.match(texto)
        or regras.item_letra.match(texto)
    ):
        return True
    return texto[:1] in regras.marcadores and texto[1:2] == " "


def classificar(
    texto: str,
    negrito: bool,
    regras: Regras,
    secao_atual: str | None,
    pua: bool,
) -> tuple[str, str | None]:
    """Devolve (tipo, número). `secao_atual` é a seção de 1º nível em curso ('3', 'anexo-A')."""
    if negrito and texto.strip() in regras.preliminares:
        return "titulo_secao", None  # Prefácio, Introdução: seção sem número
    if regras.anexo.match(texto) and negrito:
        letra = regras.anexo.match(texto).group("letra")
        return "anexo", letra

    casa = numero_secao(texto, regras, negrito)
    if casa:
        numero, _ = casa
        if negrito and not pua and len(texto) < 120 and not texto.rstrip().endswith("."):
            return "titulo_secao", numero
        if secao_atual == "3" and numero.startswith("3.") and numero.count(".") >= 2:
            return "definicao", numero
        return "paragrafo_numerado", numero

    if regras.tabela.match(texto):
        return "legenda_tabela", regras.tabela.match(texto).group("num")
    if regras.figura.match(texto):
        return "legenda_figura", regras.figura.match(texto).group("num")
    if regras.nota.match(texto):
        return "nota", None
    if regras.exemplo.match(texto):
        return "exemplo", None
    if regras.item_letra.match(texto) or (texto[:1] in regras.marcadores and texto[1:2] == " "):
        return "item_lista", None
    return "paragrafo", None


def atualiza_secao(tipo: str, numero: str | None, secao_atual: str | None) -> str | None:
    """Mantém a seção de 1º nível em curso, usada para reconhecer definições (Seção 3)."""
    if tipo == "titulo_secao" and numero and "." not in numero:
        return numero
    if tipo == "anexo" and numero:
        return f"anexo-{numero}"
    return secao_atual


# --- capa -------------------------------------------------------------------------

def extrair_capa(linhas: list[dict]) -> dict:
    """Metadados da capa a partir das linhas visuais da página 1.

    `linhas` tem: texto, negrito, italico, tamanho (ver blocos.LinhaVisual).
    Campos não encontrados não entram no dicionário; a validação os registra.
    """
    capa: dict = {}
    textos = [l["texto"] for l in linhas]
    for linha in linhas:
        if "titulo" not in capa and linha["negrito"] and 14 <= linha["tamanho"] <= 18:
            capa["titulo"] = linha["texto"]
        elif "titulo_en" not in capa and linha["italico"] and linha["tamanho"] >= 10 and "titulo" in capa:
            capa["titulo_en"] = linha["texto"]
    for i, texto in enumerate(textos):
        if texto.startswith("Palavra-chave"):
            capa["palavras_chave"] = [texto.split(":", 1)[1].strip().rstrip(".")]
        if texto.startswith("ICS"):
            capa["ics"] = [texto.split(" ", 1)[1].strip()]
        if texto.startswith("Segunda edição"):
            capa["edicao"] = "Segunda edição"
            if i + 1 < len(textos) and _DATA.search(textos[i + 1]):
                capa["data_publicacao"] = _iso(textos[i + 1])
        if texto.startswith("Válida a partir de") and i + 1 < len(textos):
            if _DATA.search(textos[i + 1]):
                capa["valida_a_partir_de"] = _iso(textos[i + 1])
        if texto.startswith("Versão Corrigida") and i + 1 < len(textos):
            if _DATA.search(textos[i + 1]):
                capa["versao_corrigida"] = _iso(textos[i + 1])
        casa = re.search(r"ABNT NBR \d+:\d{4}", texto)
        if casa and "norma_completa" not in capa:
            capa["norma_completa"] = casa.group(0)
    return capa


def _iso(texto: str) -> str:
    casa = _DATA.search(texto)
    dia, mes, ano = casa.group(1), casa.group(2), casa.group(3)
    return f"{ano}-{mes}-{dia}"
