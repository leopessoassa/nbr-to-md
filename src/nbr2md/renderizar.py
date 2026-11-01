"""Etapa 10: renderização do Markdown da norma e dos arquivos por seção.

Regras de formato em docs/FORMATO-SAIDA.md. Este módulo não altera o texto normativo:
só monta a apresentação a partir dos blocos.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import yaml

from nbr2md import __version__
from nbr2md.chunks import interpretar_definicao

_MARCADOR_ITEM = ("•", "–", "—")
_RE_NOTA = re.compile(r"^(NOTAS?|EXEMPLOS?)(\s\d+)?(?:\s+(.*))?$", re.S)
_RE_NEGRITO_ENVOLVENTE = re.compile(r"^\*\*(.*)\*\*$", re.S)
_TIPOS_COM_IMAGEM = {"figura", "formula", "simbolo"}


def _sem_negrito(texto: str) -> str:
    """Remove ** que envolvem o título e os ** internos (títulos vêm inteiros em negrito)."""
    texto = texto.strip()
    casa = _RE_NEGRITO_ENVOLVENTE.match(texto)
    if casa:
        texto = casa.group(1)
    return texto.replace("**", "").strip()


def _nivel(numero: str | None) -> int:
    """'5.1.5.4.2' -> 6 (cabeçalho ###### limitado a 6); sem número -> 2."""
    if not numero:
        return 2
    return numero.count(".") + 2


def renderizar_bloco(bloco: dict, legendas_com_figura: set) -> str | None:
    tipo, texto = bloco["tipo"], bloco["texto_md"]
    if tipo == "legenda_figura" and (bloco["pagina"], bloco["numero"]) in legendas_com_figura:
        return None  # a legenda sai dentro do bloco da figura
    if tipo == "definicao":
        info = interpretar_definicao(texto)
        if info:
            cabecalho = f"{'#' * _nivel(info['numero'])} {info['numero']} {info['termo']}"
            return cabecalho + (f"\n\n{info['definicao']}" if info["definicao"] else "")
        return texto
    if tipo == "titulo_secao":
        titulo = _sem_negrito(texto)
        numero = bloco["numero"]
        if numero and _nivel(numero) > 6:
            return f"**{numero}** {titulo.replace(numero, '', 1).strip()}"
        if numero:
            titulo = re.sub(rf"^{re.escape(numero)}\s+", "", titulo, count=1)
            return f"{'#' * _nivel(numero)} {numero} {titulo}"
        return f"## {titulo}"
    if tipo == "anexo":
        return f"## {_sem_negrito(texto)}"
    if tipo == "item_lista":
        if texto[:1] in _MARCADOR_ITEM:
            return f"- {texto[1:].strip()}"
        return f"- {texto}"  # "a) texto" já traz a letra
    if tipo in ("nota", "exemplo"):
        casa = _RE_NOTA.match(texto)
        if casa:
            rotulo = (casa.group(1) + (casa.group(2) or "")).strip()
            resto = (casa.group(3) or "").strip()
            return f"> **{rotulo}** {resto}".rstrip()
        return f"> {texto}"
    if tipo in ("rodape",):
        sem_numero = re.sub(r"^\d+\)\s*", "", texto, count=1)
        return f"[^p{bloco['pagina']}-{bloco['numero']}]: {sem_numero}"
    if tipo == "figura":
        partes = texto.split("\n")
        if partes and partes[0].startswith("!["):
            imagem, resto = partes[0], "\n".join(partes[1:])
        else:
            imagem, resto = None, texto
        legenda = bloco["extra"].get("legenda")
        cabecalho = f"{imagem}\n\n**{legenda}**" if imagem else f"**{legenda}**"
        return f"{cabecalho}\n\n{resto}"
    return texto


def _front_matter(capa: dict, extracao: dict, manifest_contagens: dict) -> str:
    dados = {
        "norma": "ABNT NBR 5410",
        "id": "nbr-5410",
        "norma_completa": capa.get("norma_completa"),
        "titulo": capa.get("titulo"),
        "titulo_en": capa.get("titulo_en"),
        "edicao": capa.get("edicao"),
        "data_publicacao": capa.get("data_publicacao"),
        "valida_a_partir_de": capa.get("valida_a_partir_de"),
        "versao_corrigida": capa.get("versao_corrigida"),
        "ics": capa.get("ics"),
        "palavras_chave": capa.get("palavras_chave"),
        "paginas_pdf": extracao.get("paginas_pdf"),
        "fonte_pdf_sha256": extracao.get("sha256"),
        "conversor_versao": __version__,
        "data_conversao": date.today().isoformat(),
        "marcacoes": {
            "[imagem] ... [/imagem]": "descrição de figura escrita por IA, não revisada; não é texto normativo",
            "[imagem revisada] ... [/imagem]": "descrição de figura revisada por pessoa; não é texto normativo",
            "[formula] ... [/formula]": "fórmula transcrita por IA a partir de imagem, não revisada",
            "[formula revisada] ... [/formula]": "fórmula transcrita e revisada por pessoa",
            "[simbolo] ... [/simbolo]": "símbolo ainda não transcrito; pendência de revisão",
            "[rodape] ... [/rodape]": "definição de nota de rodapé não localizada; pendência de revisão",
        },
    }
    return "---\n" + yaml.safe_dump(dados, allow_unicode=True, sort_keys=False) + "---\n"


def montar(saida: dict, extracao: dict, norma_id: str = "nbr-5410") -> dict:
    """Monta o Markdown completo e os arquivos por seção.

    Devolve {"markdown": str, "secoes": [(nome_arquivo, texto)], "paginas": [...]}.
    """
    blocos = saida["blocos"]
    legendas_com_figura = {
        (b["pagina"], b["numero"]) for b in blocos if b["tipo"] == "figura" and b["numero"]
    }
    contagens = {
        "tabelas": sum(1 for b in blocos if b["tipo"] == "tabela"),
        "figuras": sum(1 for b in blocos if b["tipo"] == "figura"),
        "formulas": sum(1 for b in blocos if b["tipo"] == "formula"),
        "simbolos": sum(1 for b in blocos if b["tipo"] == "simbolo"),
    }
    capa = saida["capa"]
    titulo = f"# {capa.get('norma_completa', 'ABNT NBR 5410')} — {capa.get('titulo', '')}"

    partes: list[str] = []
    pagina_marcada = None
    secoes: list[tuple[str, list[str]]] = [("00-preliminares", [])]
    secao_titulo = {"00-preliminares": "Preliminares"}
    for bloco in blocos:
        texto = renderizar_bloco(bloco, legendas_com_figura)
        if texto is None:
            continue
        primeira = bloco["paginas"][0]
        if primeira != pagina_marcada:
            partes.append(f"<!-- p. {primeira} -->")
            pagina_marcada = primeira
        partes.append(texto)
        if bloco["tipo"] in ("titulo_secao", "anexo") and _e_secao_principal(bloco):
            nome = _nome_secao(bloco)
            secoes.append((nome, []))
            secao_titulo[nome] = _sem_negrito(bloco["texto_md"])
        secoes[-1][1].append(texto)

    corpo = "\n\n".join([titulo, *partes]) + "\n"
    markdown = _front_matter(capa, extracao, contagens) + "\n" + corpo

    arquivos = []
    for nome, trechos in secoes:
        if not trechos:
            continue
        titulo_secao = secao_titulo.get(nome, nome)
        cabecalho = (
            "---\n"
            + yaml.safe_dump(
                {"norma": "ABNT NBR 5410:2004", "id": norma_id, "secao": nome, "titulo": titulo_secao},
                allow_unicode=True, sort_keys=False,
            )
            + "---\n"
            + f"\n[Arquivo único](../{norma_id}.md)\n\n"
        )
        conteudo = "\n\n".join(trechos).replace("(assets/", "(../assets/")
        arquivos.append((f"{nome}.md", cabecalho + conteudo + "\n"))
    return {"markdown": markdown, "secoes": arquivos, "contagens": contagens}


def _e_secao_principal(bloco: dict) -> bool:
    if bloco["tipo"] == "anexo":
        return True
    numero = bloco["numero"]
    return numero is None or "." not in numero


def _nome_secao(bloco: dict) -> str:
    if bloco["tipo"] == "anexo":
        return f"anexo-{bloco['numero'].lower()}"
    numero = bloco["numero"]
    if numero is None:
        return "00-preliminares"
    titulo = re.sub(rf"^{re.escape(numero)}\s+", "", _sem_negrito(bloco["texto_md"]), count=1)
    slug = _slug(titulo)
    return f"{int(numero):02d}-{slug}" if numero.isdigit() else f"{numero.lower()}-{slug}"


def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto[:60]


def gravar(
    norma_id: str,
    pasta_norma: Path,
    montagem: dict,
    manifest: dict,
) -> None:
    """Grava o Markdown, os arquivos por seção e o manifest em normas/<id>/."""
    pasta_norma.mkdir(parents=True, exist_ok=True)
    (pasta_norma / f"{norma_id}.md").write_text(montagem["markdown"], encoding="utf-8")
    secoes = pasta_norma / "secoes"
    secoes.mkdir(exist_ok=True)
    for nome, texto in montagem["secoes"]:
        (secoes / nome).write_text(texto, encoding="utf-8")
    (pasta_norma / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def gravar_llms(normas_dir: Path) -> Path:
    """normas/llms.txt: uma linha por norma convertida, com os caminhos do arquivo único e das seções."""
    linhas = ["# Normas técnicas convertidas", ""]
    for manifest in sorted(normas_dir.glob("*/manifest.json")):
        dados = json.loads(manifest.read_text(encoding="utf-8"))
        nid = dados["id"]
        linhas.append(f"- {dados['titulo']} ({dados['norma_completa']}) — id `{nid}`")
        linhas.append(f"  - arquivo único: {nid}/{nid}.md")
        linhas.append(f"  - seções: {nid}/secoes/")
    destino = normas_dir / "llms.txt"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino
