"""Critérios das Etapas 10 e 11 (M5) aplicados à ABNT NBR 5410.

Lê as saídas geradas em normas/nbr-5410/ (rodar `converter nbr-5410` antes).
Os critérios de NBR 5419 (validação das cinco normas, llms com todas) ficam para
"a verificar quando a norma 5419 for convertida".
"""

import json

import pytest

from nbr2md.config import RAIZ

NORMA = RAIZ / "normas" / "nbr-5410"


@pytest.fixture(scope="session")
def manifest():
    return json.loads((NORMA / "manifest.json").read_text(encoding="utf-8"))


def test_arquivos_da_definicao_de_pronto_existem():
    for nome in ("nbr-5410.md", "chunks.jsonl", "termos.json", "manifest.json", "revisao.md"):
        assert (NORMA / nome).is_file(), nome
    assert (NORMA / "secoes").is_dir()
    assert (NORMA / "assets").is_dir()


def test_llms_lista_a_norma():
    texto = (RAIZ / "normas" / "llms.txt").read_text(encoding="utf-8")
    assert "nbr-5410" in texto


def test_front_matter_tem_metadados_da_capa():
    md = (NORMA / "nbr-5410.md").read_text(encoding="utf-8")
    assert md.startswith("---\n")
    assert "norma_completa: ABNT NBR 5410:2004" in md
    assert "data_publicacao: '2004-09-30'" in md


def test_figuras_com_legenda_tem_bloco_de_descricao(manifest):
    md = (NORMA / "nbr-5410.md").read_text(encoding="utf-8")
    # conta só as linhas "[imagem]"; o front matter também cita a tag em "marcacoes"
    assert md.split("\n").count("[imagem]") == manifest["contagens"]["figuras"]
    from nbr2md import revisoes

    descritas = len(revisoes.carregar("nbr-5410").get("figuras", {}))
    assert md.count("PENDENTE: descrição não escrita") == manifest["contagens"]["figuras"] - descritas


def test_nota_de_rodape_pendente_fica_marcada():
    md = (NORMA / "nbr-5410.md").read_text(encoding="utf-8")
    assert "[rodape]\nPENDENTE: definição da nota [^p30-1] não localizada no PDF.\n[/rodape]" in md


def test_chunks_cobrem_clausulas(manifest):
    linhas = (NORMA / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(l) for l in linhas]
    assert any(c["secao"] == "1.2.3" for c in chunks)
    assert all(c["norma"] == "ABNT NBR 5410:2004" for c in chunks)


def test_termos_extraidos_da_secao_3():
    termos = json.loads((NORMA / "termos.json").read_text(encoding="utf-8"))
    assert len(termos) >= 20
    assert all(t["numero"].startswith("3.") for t in termos)


def test_validacao_sem_bloqueantes():
    from nbr2md.validar import validar

    res = validar("nbr-5410")
    assert res.bloqueantes == [], res.bloqueantes
    assert res.metricas["cobertura_pymupdf"] >= 0.995
    assert res.metricas["texto_extra"] <= 0.002
    assert res.metricas["cobertura_pdfplumber"] >= 0.99
