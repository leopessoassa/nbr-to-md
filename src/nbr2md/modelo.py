"""Estruturas intermediárias do pipeline (Seção 4 do plano).

Todas são dataclasses serializáveis em JSON, para testar cada etapa isoladamente
e inspecionar `build/`.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

_PREFIXO_SUBCONJUNTO = re.compile(r"^[A-Z]{6}\+")


def fonte_base(nome: str) -> str:
    """Remove o prefixo de subconjunto do nome da fonte.

    'IZWWBL+ArialMT' -> 'ArialMT'. Sem prefixo, devolve o nome intacto.
    É a chave usada em `mapa_glifos` (config/<id>/norma.yaml).
    """
    return _PREFIXO_SUBCONJUNTO.sub("", nome)


@dataclass
class Span:
    texto: str
    fonte: str                      # nome como aparece no PDF, sem normalizar
    tamanho: float
    negrito: bool
    italico: bool
    bbox: tuple[float, float, float, float]
    origem_x: float
    origem_y: float                 # linha de base (origin[1])
    direcao: tuple[float, float]    # direção da linha; (1.0, 0.0) = horizontal
    glifos_sem_unicode: list[dict] = field(default_factory=list)

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Linha:
    spans: list[Span]
    bbox: tuple[float, float, float, float]
    pagina: int
    direcao: tuple[float, float]

    @property
    def texto(self) -> str:
        return "".join(s.texto for s in self.spans)

    def para_dict(self) -> dict:
        return {
            "bbox": list(self.bbox),
            "direcao": list(self.direcao),
            "spans": [s.para_dict() for s in self.spans],
        }


@dataclass
class Bloco:
    """Bloco de texto (Etapa 6). `texto_md` já traz a marcação inline (Etapa 5)."""

    id: str                          # ex.: "p053-b007"
    tipo: str                        # titulo_secao, paragrafo_numerado, nota, item_lista...
    pagina: int
    paginas: list[int]               # mais de uma quando atravessa páginas
    bbox: tuple[float, float, float, float]
    texto_md: str
    numero: str | None = None        # "5.1.5.4.2", "A", "3.1.19"
    extra: dict = field(default_factory=dict)

    def para_dict(self) -> dict:
        return asdict(self)
