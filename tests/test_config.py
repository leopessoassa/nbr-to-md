from nbr2md.config import carregar_defaults, carregar_norma, mesclar


def test_mesclar_dicionarios_e_listas():
    base = {"a": {"x": 1, "lista": [1]}, "b": 2}
    extra = {"a": {"y": 3, "lista": [2]}, "b": 9}
    assert mesclar(base, extra) == {"a": {"x": 1, "y": 3, "lista": [1, 2]}, "b": 9}


def test_mesclar_nao_altera_a_base():
    base = {"lista": [1]}
    mesclar(base, {"lista": [2]})
    assert base == {"lista": [1]}


def test_norma_herda_defaults_e_sobrescreve_mapa_glifos():
    defaults = carregar_defaults()
    norma = carregar_norma("nbr-5410")

    # Herdado do padrão: a regex da marca d'água e a faixa de cabeçalho.
    assert norma["remover"]["cabecalho_rodape"]["faixa_superior"] == defaults[
        "remover"
    ]["cabecalho_rodape"]["faixa_superior"]
    assert norma["estrutura"]["regex_secao"] == defaults["estrutura"]["regex_secao"]

    # Específico da norma: glifos confirmados pela imagem da página.
    assert norma["mapa_glifos"]["ArialMT"][326] == "—"
    assert norma["mapa_glifos"]["SymbolMT"][100] == "≤"
    assert norma["id"] == "nbr-5410"


def test_norma_sem_config_falha_com_mensagem_clara(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        carregar_norma("nbr-inexistente", config_dir=tmp_path)
