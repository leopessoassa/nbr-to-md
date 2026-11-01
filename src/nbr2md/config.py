"""Carregamento da configuração: config/defaults.yaml + config/<id>/norma.yaml.

Regras de merge (Etapa 2 do plano):
- dicionários são mesclados recursivamente; a chave da norma sobrescreve o padrão;
- listas são concatenadas (padrão primeiro, depois as da norma);
- escalares da norma substituem o padrão.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
CONFIG_DIR = RAIZ / "config"


def mesclar(base: Any, extra: Any) -> Any:
    """Retorna uma cópia de `base` com `extra` aplicado por cima (merge profundo)."""
    if isinstance(base, dict) and isinstance(extra, dict):
        resultado = copy.deepcopy(base)
        for chave, valor in extra.items():
            if chave in resultado:
                resultado[chave] = mesclar(resultado[chave], valor)
            else:
                resultado[chave] = copy.deepcopy(valor)
        return resultado
    if isinstance(base, list) and isinstance(extra, list):
        return copy.deepcopy(base) + copy.deepcopy(extra)
    return copy.deepcopy(extra)


def _ler_yaml(caminho: Path) -> dict:
    with caminho.open(encoding="utf-8") as arquivo:
        dados = yaml.safe_load(arquivo)
    return dados or {}


def carregar_defaults(config_dir: Path = CONFIG_DIR) -> dict:
    return _ler_yaml(config_dir / "defaults.yaml")


def carregar_norma(norma_id: str, config_dir: Path = CONFIG_DIR) -> dict:
    """Carrega defaults + ajustes da norma já mesclados.

    Lança FileNotFoundError se config/<id>/norma.yaml não existir.
    """
    caminho = config_dir / norma_id / "norma.yaml"
    if not caminho.is_file():
        raise FileNotFoundError(f"configuração da norma não encontrada: {caminho}")
    return mesclar(carregar_defaults(config_dir), _ler_yaml(caminho))
