"""Etapa 9: revisões escritas pelo Kiro (config/<id>/revisoes.yaml).

O pipeline só lê o arquivo. Quem escreve é o Kiro (revisado_por: ia) ou o dono do
repositório (revisado_por: humano). Um item só é aplicado se o hash_recorte bater
com o PNG atual (ver blocos._integrar_figuras_e_notas).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from nbr2md.config import CONFIG_DIR

REVISADO_POR_VALIDOS = {"ia", "humano"}


def carregar(norma_id: str, config_dir: Path = CONFIG_DIR) -> dict:
    """Devolve {"figuras": {numero: item}, "equacoes": {...}}; vazio se o arquivo não existir."""
    caminho = config_dir / norma_id / "revisoes.yaml"
    if not caminho.is_file():
        return {}
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    for numero, item in (dados.get("figuras") or {}).items():
        if item.get("revisado_por") not in REVISADO_POR_VALIDOS:
            raise ValueError(f"figura {numero}: revisado_por inválido ({item.get('revisado_por')!r})")
    return dados
