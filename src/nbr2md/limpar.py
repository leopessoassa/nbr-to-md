"""Etapa 4: limpeza do texto extraído.

Trabalha sobre as páginas no formato de `extrair.extrair_pagina` (dicts JSON).
A ordem das etapas segue o plano e não deve mudar:

1. marca d'água (linha que casa com a regex de `remover.marca_dagua`; texto rotacionado sem casamento é mantido);
2. imagem de fundo (área ≥ 85% da página);
3. cabeçalho e rodapé (regex, depois repetição nas faixas);
4. glifos sem Unicode (mapa_glifos) e mapa_caracteres;
5. espaços especiais;
6. marcação de uso privado (U+F000 a U+F8FF), sem remover nada;
7. NFC.

Decisão registrada em relatório: as regex de cabeçalho e rodapé só valem dentro
das faixas superior e inferior da página. Sem isso, `^\\d{1,3}$` removeria
qualquer linha do corpo que tenha só um número (por exemplo, uma célula).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from nbr2md.modelo import fonte_base

_LIMITE_IMAGEM_FUNDO = 0.85
_REGEX_PUA = re.compile("[\U0000f000-\U0000f8ff]")
_REGEX_DIGITO = re.compile(r"\d")
_REPLACEMENT = "\ufffd"


@dataclass
class RelatorioLimpeza:
    marca_dagua_por_pagina: dict[int, int] = field(default_factory=dict)
    imagens_fundo_removidas: int = 0
    cabecalho_regex: int = 0
    cabecalho_repeticao: int = 0
    chaves_repeticao: dict[str, int] = field(default_factory=dict)  # chave -> páginas
    glifos_mapeados: int = 0
    glifos_nao_mapeados: dict[str, int] = field(default_factory=dict)  # "fonte:glifo" -> n
    mapa_caracteres_aplicados: dict[str, int] = field(default_factory=dict)
    espacos_normalizados: int = 0
    linhas_pua: int = 0
    linhas_vazias_descartadas: int = 0
    erros_extracao: int = 0

    @property
    def marca_dagua_total(self) -> int:
        return sum(self.marca_dagua_por_pagina.values())

    def para_dict(self) -> dict:
        return {
            "marca_dagua_total": self.marca_dagua_total,
            "marca_dagua_por_pagina": self.marca_dagua_por_pagina,
            "imagens_fundo_removidas": self.imagens_fundo_removidas,
            "cabecalho_rodape": {
                "regex": self.cabecalho_regex,
                "repeticao": self.cabecalho_repeticao,
                "chaves_repeticao": self.chaves_repeticao,
            },
            "glifos_mapeados": self.glifos_mapeados,
            "glifos_nao_mapeados": self.glifos_nao_mapeados,
            "mapa_caracteres_aplicados": self.mapa_caracteres_aplicados,
            "espacos_normalizados": self.espacos_normalizados,
            "linhas_pua": self.linhas_pua,
            "linhas_vazias_descartadas": self.linhas_vazias_descartadas,
            "erros_extracao": self.erros_extracao,
        }


def _texto_linha(linha: dict) -> str:
    return "".join(span["texto"] for span in linha["spans"])


def _na_faixa(linha: dict, altura: float, faixa_sup: float, faixa_inf: float) -> str | None:
    """'superior', 'inferior' ou None, conforme a posição vertical da linha."""
    _, y0, _, y1 = linha["bbox"]
    if y1 <= faixa_sup * altura:
        return "superior"
    if y0 >= (1 - faixa_inf) * altura:
        return "inferior"
    return None


def _regexes_marca_dagua(cfg: dict) -> list[re.Pattern]:
    return [
        re.compile(item["regex"])
        for item in cfg["remover"]["marca_dagua"]
        if "regex" in item
    ]


def _regexes_cabecalho(cfg: dict) -> list[re.Pattern]:
    return [re.compile(r) for r in cfg["remover"]["cabecalho_rodape"]["regex"]]


def _substituir_glifos(span: dict, mapa: dict, relatorio: RelatorioLimpeza) -> None:
    """Troca cada U+FFFD do span pelo caractere de mapa_glifos ou por marcador."""
    caracteres = list(span["texto"])
    fonte = fonte_base(span["fonte"])
    for glifo in span.get("glifos_sem_unicode", []):
        indice = glifo["indice"]
        if indice >= len(caracteres) or caracteres[indice] != _REPLACEMENT:
            continue
        caractere = mapa.get(fonte, {}).get(glifo["glifo"])
        if caractere is not None:
            caracteres[indice] = caractere
            relatorio.glifos_mapeados += 1
        else:
            chave = f"{fonte}:{glifo['glifo']}"
            caracteres[indice] = f"⟦glifo:{chave}⟧"
            relatorio.glifos_nao_mapeados[chave] = relatorio.glifos_nao_mapeados.get(chave, 0) + 1
    span["texto"] = "".join(caracteres)


def _aplicar_mapa_caracteres(span: dict, mapa: dict[str, str], relatorio: RelatorioLimpeza) -> None:
    for origem, destino in mapa.items():
        ocorrencias = span["texto"].count(origem)
        if ocorrencias:
            span["texto"] = span["texto"].replace(origem, destino)
            relatorio.mapa_caracteres_aplicados[origem] = (
                relatorio.mapa_caracteres_aplicados.get(origem, 0) + ocorrencias
            )


def _normalizar_espacos(span: dict, especiais: list[str], relatorio: RelatorioLimpeza) -> None:
    original = span["texto"]
    texto = original
    for caractere in especiais:
        texto = texto.replace(caractere, " ")
    texto = re.sub(r" {2,}", " ", texto)
    if texto != original:
        relatorio.espacos_normalizados += 1
        span["texto"] = texto


def limpar(
    paginas: dict[int, dict],
    cfg: dict,
    erros_extracao: int = 0,
) -> tuple[dict[int, dict], RelatorioLimpeza]:
    """Limpa as páginas extraídas. Não altera `paginas` de entrada."""
    relatorio = RelatorioLimpeza(erros_extracao=erros_extracao)
    total = len(paginas)
    marca = _regexes_marca_dagua(cfg)
    cabecalho = _regexes_cabecalho(cfg)
    cab_cfg = cfg["remover"]["cabecalho_rodape"]
    area_minima = cfg["remover"]["imagem_fundo_area_minima"]
    especiais = list(cfg["normalizar_espacos"])
    mapa_glifos = cfg["mapa_glifos"]
    mapa_caracteres = cfg["mapa_caracteres"]

    trabalho = {n: _copia_pagina(p) for n, p in paginas.items()}

    # 1 e 2: marca d'água e imagem de fundo; 3a: cabeçalho por regex.
    for numero, pagina in trabalho.items():
        largura, altura = pagina["largura"], pagina["altura"]
        area_pagina = largura * altura
        imagens = []
        for imagem in pagina["imagens"]:
            x0, y0, x1, y1 = imagem["bbox"]
            if (x1 - x0) * (y1 - y0) >= _LIMITE_IMAGEM_FUNDO * area_pagina:
                relatorio.imagens_fundo_removidas += 1
            else:
                imagens.append(imagem)
        pagina["imagens"] = imagens

        removidas = 0
        manter = []
        for linha in pagina["linhas"]:
            texto = _texto_linha(linha).strip()
            # Texto rotacionado só sai se for a marca d'água. Rótulos de tabela
            # em paisagem também são rotacionados e precisam ficar.
            if any(r.search(texto) for r in marca):
                removidas += 1
                continue
            faixa = _na_faixa(linha, altura, cab_cfg["faixa_superior"], cab_cfg["faixa_inferior"])
            if faixa and any(r.search(texto) for r in cabecalho):
                relatorio.cabecalho_regex += 1
                continue
            manter.append(linha)
        relatorio.marca_dagua_por_pagina[numero] = removidas
        pagina["linhas"] = manter

    # 3b: cabeçalho e rodapé por repetição nas faixas (dígitos viram '#').
    contagem_paginas: dict[str, set[int]] = {}
    for numero, pagina in trabalho.items():
        for linha in pagina["linhas"]:
            if _na_faixa(linha, pagina["altura"], cab_cfg["faixa_superior"], cab_cfg["faixa_inferior"]):
                chave = _REGEX_DIGITO.sub("#", _texto_linha(linha).strip())
                contagem_paginas.setdefault(chave, set()).add(numero)
    repetidas = {
        chave: len(paginas_)
        for chave, paginas_ in contagem_paginas.items()
        if chave and len(paginas_) / total >= cab_cfg["repeticao_minima"]
    }
    relatorio.chaves_repeticao = dict(sorted(repetidas.items(), key=lambda kv: -kv[1]))
    for pagina in trabalho.values():
        manter = []
        for linha in pagina["linhas"]:
            chave = _REGEX_DIGITO.sub("#", _texto_linha(linha).strip())
            if (
                chave in repetidas
                and _na_faixa(linha, pagina["altura"], cab_cfg["faixa_superior"], cab_cfg["faixa_inferior"])
            ):
                relatorio.cabecalho_repeticao += 1
                continue
            manter.append(linha)
        pagina["linhas"] = manter

    # 4 a 7: glifos, mapa de caracteres, espaços, uso privado e NFC.
    for pagina in trabalho.values():
        manter = []
        for linha in pagina["linhas"]:
            for span in linha["spans"]:
                _substituir_glifos(span, mapa_glifos, relatorio)
                _aplicar_mapa_caracteres(span, mapa_caracteres, relatorio)
                _normalizar_espacos(span, especiais, relatorio)
                span["texto"] = unicodedata.normalize("NFC", span["texto"])
            linha["pua"] = bool(_REGEX_PUA.search(_texto_linha(linha)))
            if linha["pua"]:
                relatorio.linhas_pua += 1
            if not _texto_linha(linha).strip():
                relatorio.linhas_vazias_descartadas += 1
                continue
            manter.append(linha)
        pagina["linhas"] = manter

    return trabalho, relatorio


def _copia_pagina(pagina: dict) -> dict:
    return {
        "pagina": pagina["pagina"],
        "largura": pagina["largura"],
        "altura": pagina["altura"],
        "linhas": [
            {
                "bbox": list(l["bbox"]),
                "direcao": list(l["direcao"]),
                "spans": [
                    {**s, "glifos_sem_unicode": [dict(g) for g in s.get("glifos_sem_unicode", [])]}
                    for s in l["spans"]
                ],
            }
            for l in pagina["linhas"]
        ],
        "imagens": [dict(i) for i in pagina["imagens"]],
        "desenhos": pagina["desenhos"],
        "tabelas": pagina["tabelas"],
    }


def chaves_proibidas_presentes(paginas: dict[int, dict]) -> list[str]:
    """Textos que não podem existir após a limpeza (diagnóstico para testes)."""
    achados = []
    for numero, pagina in paginas.items():
        for linha in pagina["linhas"]:
            texto = _texto_linha(linha)
            if _REPLACEMENT in texto or "⟦glifo:" in texto:
                achados.append(f"p.{numero}: {texto[:60]}")
    return achados
