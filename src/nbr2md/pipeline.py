"""Orquestração das etapas de M1 (extração e limpeza) e gravação em build/<id>/.

Só escreve dentro de build/<id>/. Nada é apagado fora disso.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pymupdf

from nbr2md import __version__
from nbr2md.config import CONFIG_DIR, RAIZ, carregar_norma
from nbr2md.extrair import extrair_pdf, resumir_glifos, sha256_arquivo
from nbr2md.limpar import chaves_proibidas_presentes, limpar

BUILD_DIR = RAIZ / "build"


def pasta_build(norma_id: str) -> Path:
    return BUILD_DIR / norma_id


def _gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def _limpar_pasta(pasta: Path) -> None:
    """Remove só os pagina-*.json anteriores, para não misturar execuções com --paginas."""
    if pasta.is_dir():
        for arquivo in pasta.glob("pagina-*.json"):
            arquivo.unlink()


def converter_etapas_1_a_4(
    norma_id: str,
    ate_etapa: int = 4,
    paginas: range | None = None,
) -> dict:
    """Executa a extração (Etapa 3) e a limpeza (Etapa 4) e grava os artefatos.

    Devolve um resumo com os números do relatório. `ate_etapa` 3 para antes da limpeza.
    """
    cfg = carregar_norma(norma_id)
    pdf = RAIZ / cfg["fonte"]
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF da norma não encontrado: {pdf}")

    pasta = pasta_build(norma_id)
    spans_dir = pasta / "01-spans"
    limpo_dir = pasta / "02-limpo"
    _limpar_pasta(spans_dir)

    extracao = extrair_pdf(pdf, paginas)
    for numero, dados in extracao.paginas.items():
        _gravar_json(spans_dir / f"pagina-{numero:04d}.json", dados)
    _gravar_json(
        pasta / "extracao.json",
        {
            "norma": norma_id,
            "pdf": str(pdf.relative_to(RAIZ)).replace("\\", "/"),
            "sha256": extracao.sha256,
            "paginas_pdf": extracao.total_paginas,
            "paginas_extraidas": sorted(extracao.paginas),
            "erros_extracao": extracao.erros,
            "conversor_versao": __version__,
        },
    )
    glifos = resumir_glifos(extracao, cfg["mapa_glifos"])
    _gravar_json(pasta / "glifos-desconhecidos.json", glifos)

    resumo = {
        "norma": norma_id,
        "paginas_extraidas": len(extracao.paginas),
        "erros_extracao": len(extracao.erros),
        "glifos": {
            "pares": glifos["total_pares"],
            "ocorrencias": glifos["total_ocorrencias"],
            "pares_nao_mapeados": sum(1 for p in glifos["pares"] if not p["mapeado"]),
        },
    }
    if ate_etapa <= 3:
        return resumo

    paginas_limpas, relatorio = limpar(
        extracao.paginas, cfg, erros_extracao=len(extracao.erros)
    )
    _limpar_pasta(limpo_dir)
    for numero, dados in paginas_limpas.items():
        _gravar_json(limpo_dir / f"pagina-{numero:04d}.json", dados)
    _gravar_json(pasta / "limpeza.json", relatorio.para_dict())
    resumo["limpeza"] = relatorio.para_dict()
    resumo["proibidos_restantes"] = chaves_proibidas_presentes(paginas_limpas)
    if ate_etapa < 6:
        return resumo

    from collections import Counter

    from nbr2md.blocos import processar

    # Recortes em PNG só saem na Etapa 8 (ver figuras.py).
    documento = pymupdf.open(pdf)
    pasta_norma = RAIZ / "normas" / norma_id
    try:
        renderizador = None
        if ate_etapa >= 8:
            _regenerar_pasta_norma(pasta_norma)
            renderizador = _renderizador(documento, pasta_norma)
        from nbr2md import revisoes as rv

        revisoes_ = rv.carregar(norma_id) if ate_etapa >= 8 else None
        saida = processar(paginas_limpas, cfg, renderizador=renderizador, revisoes=revisoes_)
        # Plano, Etapa 7 passo 1: legenda "Tabela N" sem tabela detectada ganha uma
        # tentativa com find_tables(strategy="text"), marcada com confianca baixa.
        if renderizador is not None and _completar_tabelas_por_texto(documento, paginas_limpas, saida):
            saida = processar(paginas_limpas, cfg, renderizador=renderizador, revisoes=revisoes_)
    finally:
        documento.close()
    _gravar_json(pasta / "03-blocos.json", saida)
    if ate_etapa >= 10:
        _gerar_saidas(norma_id, saida, pasta_norma, pasta)
        resumo["normas"] = str(pasta_norma.relative_to(RAIZ)).replace("\\", "/")
    resumo["blocos"] = {
        "total": len(saida["blocos"]),
        "por_tipo": dict(Counter(b["tipo"] for b in saida["blocos"])),
        "capa": saida["capa"],
        "paginas_ignoradas": saida["paginas_ignoradas"],
    }
    return resumo


def caminho_config_norma(norma_id: str) -> Path:
    return CONFIG_DIR / norma_id / "norma.yaml"


def _se_sobrepoe(a, b, folga: float = 2.0) -> bool:
    """Retângulos a e b se cruzam (com folga em pt)."""
    return (min(a[2], b[2]) - max(a[0], b[0]) > folga) and (min(a[3], b[3]) - max(a[1], b[1]) > folga)


def _completar_tabelas_por_texto(documento, paginas_limpas: dict, saida: dict) -> int:
    """Para cada legenda "Tabela N" sem tabela, tenta find_tables(strategy="text") na página.

    A tabela mais próxima logo abaixo da legenda entra em paginas_limpas[p]["tabelas"]
    com confianca "baixa". Devolve quantas tabelas foram acrescentadas.
    """
    numeros_com_tabela = {b["numero"] for b in saida["blocos"] if b["tipo"] == "tabela"}
    alvos: dict[int, list[dict]] = {}
    for b in saida["blocos"]:
        if (b["tipo"] == "legenda_tabela" and b["numero"]
                and b["numero"] not in numeros_com_tabela
                and not re.search(r"\((continuação|conclusão)\)", b["texto_md"])):
            alvos.setdefault(b["pagina"], []).append(b)
    acrescentadas = 0
    for pagina, legendas in alvos.items():
        if pagina not in paginas_limpas:
            continue
        pagina_pdf = documento[pagina - 1]
        dados = paginas_limpas[pagina]
        for legenda in legendas:
            base = legenda["bbox"][3]
            # Busca restrita à faixa abaixo da legenda: sem o recorte, a busca por texto
            # devolve uma caixa do tamanho da página inteira.
            recorte = pymupdf.Rect(30, base + 1, pagina_pdf.rect.width - 30, pagina_pdf.rect.height - 40)
            proximas = [t for t in pagina_pdf.find_tables(clip=recorte, strategy="text").tables
                        if t.bbox[1] - base <= 120]
            # Não pode cobrir legenda de figura nem imagem: esses elementos sairiam do fluxo.
            obstaculos = [b["bbox"] for b in saida["blocos"]
                          if b["pagina"] == pagina and b["tipo"] == "legenda_figura"]
            obstaculos += [img["bbox"] for img in dados.get("imagens", [])]
            proximas = [t for t in proximas
                        if not any(_se_sobrepoe(t.bbox, o) for o in obstaculos)]
            if not proximas:
                continue
            tabela = min(proximas, key=lambda t: t.bbox[1] - base)
            dados.setdefault("tabelas", []).append({
                "bbox": list(tabela.bbox),
                "linhas": tabela.extract(),
                "celulas": [list(c) if c else None for c in tabela.cells],
                "confianca": "baixa",
            })
            acrescentadas += 1
    return acrescentadas


def _regenerar_pasta_norma(pasta_norma: Path) -> None:
    """Apaga normas/<id>/ por completo antes de regenerar (plano, Etapa 12a, passo 4).

    Só apaga se o caminho estiver dentro de normas/.
    """
    import shutil

    raiz_normas = (RAIZ / "normas").resolve()
    alvo = pasta_norma.resolve()
    if raiz_normas not in alvo.parents:
        raise RuntimeError(f"recusado: {alvo} não está dentro de {raiz_normas}")
    if alvo.exists():
        shutil.rmtree(alvo)


def _gerar_saidas(norma_id: str, saida: dict, pasta_norma: Path, pasta_build: Path) -> None:
    """Etapa 10: Markdown, seções, chunks.jsonl, termos.json, manifest.json e llms.txt."""
    from nbr2md import chunks, renderizar

    extracao = json.loads((pasta_build / "extracao.json").read_text(encoding="utf-8"))
    capa = saida["capa"]
    montagem = renderizar.montar(saida, extracao, norma_id)
    contagens = montagem["contagens"]
    manifest = {
        "id": norma_id,
        "titulo": capa.get("titulo"),
        "norma_completa": capa.get("norma_completa"),
        "edicao": capa.get("edicao"),
        "fonte_pdf_sha256": extracao["sha256"],
        "paginas_pdf": extracao["paginas_pdf"],
        "conversor_versao": __version__,
        "data_conversao": date.today().isoformat(),
        "contagens": {
            "secoes": sum(1 for b in saida["blocos"] if b["tipo"] == "titulo_secao"),
            **contagens,
            "notas_rodape": sum(1 for b in saida["blocos"] if b["tipo"] == "rodape"),
            "pendencias_rodape": sum(1 for b in saida["blocos"] if b["tipo"] == "rodape_pendente"),
        },
    }
    renderizar.gravar(norma_id, pasta_norma, montagem, manifest)
    linhas_chunks = chunks.gerar_chunks(saida, norma_id, capa.get("norma_completa", norma_id))
    (pasta_norma / "chunks.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in linhas_chunks), encoding="utf-8"
    )
    termos = chunks.gerar_termos(saida)
    (pasta_norma / "termos.json").write_text(json.dumps(termos, ensure_ascii=False, indent=1), encoding="utf-8")
    renderizar.gravar_llms(RAIZ / "normas")


def validar_norma(norma_id: str) -> int:
    """Etapa 11: valida a saída, grava revisao.md e devolve 0 (sem bloqueantes) ou 1."""
    from nbr2md import validar

    res = validar.validar(norma_id)
    validar.gravar_revisao(norma_id, res)
    return 1 if res.bloqueantes else 0


def _renderizador(documento: pymupdf.Document, pasta_normas: Path):
    """Função que grava um recorte da página em normas/<id>/<arquivo> e devolve o sha256."""

    def renderizar(pagina: int, bbox, arquivo_rel: str) -> str:
        destino = pasta_normas / arquivo_rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        recorte = pymupdf.Rect(*bbox) & documento[pagina - 1].rect
        documento[pagina - 1].get_pixmap(clip=recorte, dpi=200).save(destino)
        return sha256_arquivo(destino)

    return renderizar


def gerar_recortes(norma_id: str) -> Path:
    """Converte até a Etapa 8, copia os PNGs para build/<id>/recortes/ e grava pendencias.yaml."""
    import shutil

    import yaml

    converter_etapas_1_a_4(norma_id, ate_etapa=8)
    pasta = pasta_build(norma_id)
    saida = json.loads((pasta / "03-blocos.json").read_text(encoding="utf-8"))
    destino = pasta / "recortes"
    destino.mkdir(parents=True, exist_ok=True)
    pendencias = []
    normas_dir = RAIZ / "normas" / norma_id
    for bloco in saida["blocos"]:
        if bloco["tipo"] not in ("figura", "formula"):
            continue
        arquivo = bloco["extra"].get("arquivo")
        origem = normas_dir / arquivo if arquivo else None
        if origem is not None and origem.is_file():
            shutil.copyfile(origem, destino / origem.name)
        pendencias.append(
            {
                "id": bloco["id"],
                "tipo": bloco["tipo"],
                "numero": bloco["numero"],
                "pagina": bloco["pagina"],
                "legenda": bloco["extra"].get("legenda"),
                "rotulos": bloco["extra"].get("rotulos", []),
                "arquivo": arquivo,
                "hash_recorte": bloco["extra"].get("sha256"),
                "revisado_por": None,
                "status": "pendente",
            }
        )
    caminho = destino / "pendencias.yaml"
    caminho.write_text(yaml.safe_dump(pendencias, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho
