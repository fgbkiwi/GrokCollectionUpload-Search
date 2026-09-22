"""
Testes do extrator de IDs PJe e papéis de tópico na minuta.
"""

from minuta import OrquestradorMinuta, TopicoEstrutura, TipoTopico
from pje_ids import (
    extrair_ids_pje_do_texto,
    inferir_id_proximo_ao_trecho,
    normalizar_id_pje,
)


def test_extrai_id_linha_assinatura():
    texto = (
        "Documento assinado eletronicamente por PROCEDIMENTO AUTOMATIZADO - PJE, "
        "em 12/06/2026, às 00:32:38 - c7dbfbc"
    )
    ids = extrair_ids_pje_do_texto(texto)
    assert "c7dbfbc" in ids


def test_extrai_id_explicito_e_parenteses():
    texto = "Conforme (ID b9283dd) e ID. 60b080d no acórdão."
    ids = extrair_ids_pje_do_texto(texto)
    assert "b9283dd" in ids
    assert "60b080d" in ids


def test_inferir_id_proximo_ao_trecho():
    texto = (
        "Planilha de cálculos do reclamante com total X.\n"
        "Documento assinado eletronicamente por PROCEDIMENTO AUTOMATIZADO - PJE, "
        "em 12/06/2026, às 00:32:38 - c7dbfbc\n"
    )
    trecho = "Planilha de cálculos do reclamante com total X."
    assert inferir_id_proximo_ao_trecho(texto, trecho) == "c7dbfbc"


def test_normalizar_id_remove_prefixo():
    assert normalizar_id_pje("ID c7dbfbc") == "c7dbfbc"
    assert normalizar_id_pje("não informado") is None


def test_normalizar_tipo_relatorio_dispositivo_merito():
    orch = OrquestradorMinuta("fake")
    r = orch._normalizar_tipo_topico(
        TopicoEstrutura(id="T1", titulo="Relatório", nivel=1, ordem=1)
    )
    assert r.tipo == TipoTopico.RELATORIO
    assert r.questao_id is None

    d = orch._normalizar_tipo_topico(
        TopicoEstrutura(id="T3", titulo="Dispositivo", nivel=1, ordem=3)
    )
    assert d.tipo == TipoTopico.DISPOSITIVO

    m = orch._normalizar_tipo_topico(
        TopicoEstrutura(
            id="T2",
            titulo="Correção da planilha",
            nivel=1,
            ordem=2,
            questao_id="Q1",
        )
    )
    assert m.tipo == TipoTopico.MERITO_QUESTAO


def test_formatar_prova_omite_id_ausente():
    orch = OrquestradorMinuta("fake")

    class P:
        trecho = "Trecho de prova"
        id_pje = None
        folhas = "fls. 93"

    linha = orch._formatar_prova_linha(P())
    assert "não informado" not in linha.lower()
    assert "fls. 93" in linha


def test_prompt_definitiva_relatorio_nao_pede_fundamentacao():
    orch = OrquestradorMinuta("fake")
    from cartao_caso import CartaoDoCaso, Questao
    from dossie_prova import DossieProva
    from minuta import MinutaTopico

    cartao = CartaoDoCaso(
        arquivo_origem="x.md",
        questoes=[
            Questao(
                id="Q1",
                titulo="Insalubridade",
                tipo="mista",
                momento="merito",
                mencionar_na_minuta=True,
            )
        ],
    )
    topico = TopicoEstrutura(
        id="T1",
        titulo="Relatório",
        nivel=1,
        ordem=1,
        tipo=TipoTopico.RELATORIO,
    )
    previa = MinutaTopico(
        topico_id="T1",
        titulo="Relatório",
        tese="a",
        antitese="b",
        abordagem="narrar",
        conclusao_preliminar="c",
    )
    prompt = orch._construir_prompt_definitiva(
        topico,
        previa,
        cartao,
        None,
        DossieProva(
            cartao_origem="cartao.json",
            arquivo_autos="a.md",
            dossies_por_questao=[],
        ),
        [],
        [],
    )
    assert "APENAS o RELATÓRIO" in prompt
    assert "Não há dossiê de provas vinculado" not in prompt


def test_extrair_ids_citados_alfanumericos():
    orch = OrquestradorMinuta("fake")
    texto = "Conforme laudo (ID b9283dd, fls. 19) e planilha ID c7dbfbc."
    ids = orch._extrair_ids_citados(texto)
    assert "b9283dd" in ids
    assert "c7dbfbc" in ids
