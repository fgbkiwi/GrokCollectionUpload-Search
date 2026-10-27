"""
Testes das correções de desempenho/custo: Dossiê em lote, segmentação,
busca na Collection, minuta sem prévia e estimativa de custo da auditoria.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from auditoria_execucao import Etapa, carregar_precos, custo_chamada, PRECOS_PADRAO
from cartao_caso import CartaoDoCaso, Questao
from dossie_prova import ExaminadorDocumental, OrquestradorDossie
from dossie_prova.segmentacao import classificar_bloco, segmentar_autos


def _resposta(conteudo: dict) -> Mock:
    resp = Mock()
    resp.status_code = 200
    resp.ok = True
    resp.headers = {}
    resp.raise_for_status = Mock()
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(conteudo)}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 100},
    }
    return resp


# --------------------------------------------------------------------------- #
# Segmentação
# --------------------------------------------------------------------------- #

def test_peticao_que_menciona_pericia_e_testemunha_fica_documental():
    bloco = (
        "PETIÇÃO INICIAL\nO reclamante requer a produção de prova pericial e "
        "a oitiva de testemunha para comprovar a insalubridade."
    )
    assert classificar_bloco(bloco) == "documental"


def test_laudo_e_ata_de_audiencia_sao_classificados():
    laudo = (
        "LAUDO PERICIAL\nMetodologia: vistoria no local.\n"
        "Respostas aos quesitos do reclamante.\nConclusão pericial: insalubre."
    )
    ata = (
        "ATA DE AUDIÊNCIA\nPrimeira testemunha do reclamante: Maria, advertida e "
        "compromissada. Às perguntas do juízo, respondeu que a depoente trabalhava "
        "até as 20h. Nada mais disse."
    )
    assert classificar_bloco(laudo) == "pericial"
    assert classificar_bloco(ata) == "oral"


def test_segmentar_autos_por_titulos():
    autos = (
        "# Petição inicial\nPede horas extras e perícia.\n\n"
        "# Laudo pericial\nRespostas aos quesitos. Metodologia: vistoria.\n\n"
        "# Ata de audiência\nTestemunha do autor, compromissada. A depoente disse "
        "que saía às 20h. Nada mais disse.\n"
    )
    segmentos, contagem = segmentar_autos(autos)
    assert contagem == {"documental": 1, "pericial": 1, "oral": 1}
    assert "Pede horas extras" in segmentos["documental"]
    assert "quesitos" in segmentos["pericial"]
    assert "depoente" in segmentos["oral"]


@pytest.mark.parametrize("tamanho_max, overlap", [(0, 0), (100, 100), (100, 150), (100, -1)])
def test_particionar_rejeita_parametros_que_causariam_laco_infinito(tamanho_max, overlap):
    with pytest.raises(ValueError):
        OrquestradorDossie("fake_key")._particionar_em_lotes("x" * 1000, tamanho_max, overlap)


# --------------------------------------------------------------------------- #
# Dossiê: uma chamada para várias questões
# --------------------------------------------------------------------------- #

def test_examinar_questoes_faz_uma_chamada_e_distribui_por_questao():
    resposta = {
        "por_questao": [
            {"questao_id": "Q1", "provas_documentais": [{
                "trecho": "Cartões de ponto", "id_pje": "ID 1234567", "folhas": "fls. 10",
                "relevancia": "alta", "favoravel_a": "autor", "tipo_documento": "controle",
            }], "avisos": []},
            {"questao_id": "Q2", "provas_documentais": [], "avisos": ["Sem documentos"]},
        ],
        "avisos_gerais": ["Autos extensos"],
    }
    with patch("dossie_prova.examinador_base.requests.post",
               return_value=_resposta(resposta)) as mock_post:
        examinador = ExaminadorDocumental("fake_key", conv_id="conv-teste")
        resultado = examinador.examinar_questoes(
            [("Q1", "Horas extras"), ("Q2", "Adicional noturno")],
            "Conteúdo documental dos autos " * 10,
            {"Q1": ["Impugna os cartões"], "Q2": []},
        )

    assert mock_post.call_count == 1
    assert mock_post.call_args.kwargs["headers"]["x-grok-conv-id"] == "conv-teste"
    provas_q1, avisos_q1 = resultado["Q1"]
    provas_q2, avisos_q2 = resultado["Q2"]
    assert len(provas_q1) == 1 and provas_q1[0].trecho == "Cartões de ponto"
    assert provas_q2 == []
    assert "Sem documentos" in avisos_q2
    assert "Autos extensos" in avisos_q1 and "Autos extensos" in avisos_q2


def test_examinar_questoes_agrupa_acima_do_limite():
    questoes = [(f"Q{i}", f"Questão {i}") for i in range(1, 9)]
    with patch("dossie_prova.examinador_base.requests.post",
               return_value=_resposta({"por_questao": []})) as mock_post:
        ExaminadorDocumental("fake_key").examinar_questoes(questoes, "texto " * 50, {})
    assert mock_post.call_count == 2  # 8 questões, no máximo 6 por chamada


# --------------------------------------------------------------------------- #
# Busca na Collection
# --------------------------------------------------------------------------- #

def test_busca_collection_usa_formato_documents_search():
    from minuta.busca_precedentes import BuscaPrecedentes

    resp = Mock(status_code=200, ok=True, headers={}, text="")
    resp.json.return_value = {"matches": [{
        "file_id": "file_1", "chunk_id": "c1", "chunk_content": "Ementa: horas extras devidas.",
        "collection_ids": ["col_1"], "fields": {"numero_processo": "0001"}, "score": 0.9,
    }]}
    with patch("minuta.busca_precedentes.requests.post", return_value=resp) as mock_post:
        busca = BuscaPrecedentes("fake_key", "mgmt", collection_id="col_1")
        precedentes, avisos = busca.buscar(
            "horas extras", top_k=3, retrieval_mode="semantic", filtros={"tribunal": "TRT10"}
        )

    payload = mock_post.call_args.kwargs["json"]
    assert mock_post.call_args.args[0].endswith("/documents/search")
    assert payload["source"] == {"collection_ids": ["col_1"]}
    assert payload["limit"] == 3
    assert payload["retrieval_mode"] == {"type": "semantic"}
    assert payload["filter"] == 'tribunal = "TRT10"'
    assert len(precedentes) == 1
    assert not any(a.startswith("Erro") for a in avisos)


# --------------------------------------------------------------------------- #
# Minuta sem prévia e gravação parcial
# --------------------------------------------------------------------------- #

def test_prompt_definitiva_sem_previa_inclui_questao_e_instrucao_dialetica():
    from dossie_prova import DossieProva
    from minuta import OrquestradorMinuta
    from minuta.schema import TipoTopico, TopicoEstrutura

    cartao = CartaoDoCaso(
        arquivo_origem="autos.md",
        questoes=[Questao(id="Q1", titulo="Horas extras", tipo="fato", momento="merito",
                          mencionar_na_minuta=True, pedido_ids=[])],
    )
    topico = TopicoEstrutura(id="T1", titulo="Horas extras", nivel=1, ordem=1,
                             questao_id="Q1", tipo=TipoTopico.MERITO_QUESTAO)
    dossie = DossieProva(cartao_origem="autos.md", arquivo_autos="autos.md")

    prompt = OrquestradorMinuta("fake_key")._construir_prompt_definitiva(
        topico, None, cartao, None, dossie, [], []
    )
    assert "ABORDAGEM APROVADA" not in prompt
    assert "QUESTÃO: Horas extras" in prompt
    assert "dialeticamente" in prompt


def test_markdown_parcial_sinaliza_topico_nao_gerado():
    from aba_minuta import AbaMinuta
    from minuta.schema import MinutaDefinitiva

    md = AbaMinuta._montar_markdown([
        MinutaDefinitiva(topico_id="T1", titulo="Relatório", conteudo="Texto pronto."),
        MinutaDefinitiva(topico_id="T2", titulo="Horas extras", conteudo="",
                         avisos_validacao=["Erro ao gerar minuta: timeout"]),
    ])
    assert "## Relatório\n\nTexto pronto." in md
    assert "Tópico não gerado" in md and "timeout" in md


# --------------------------------------------------------------------------- #
# Custo estimado na auditoria
# --------------------------------------------------------------------------- #

def _etapa_api(**dados) -> Etapa:
    return Etapa(sessao="s", id="1", pai=None, categoria="api", nome="x",
                 inicio=datetime.now(), dados=dados)


def test_custo_chamada_faixa_normal_com_cache_e_reasoning():
    e = _etapa_api(modelo="grok-4.7", tokens_entrada=100_000, tokens_cache=40_000,
                   tokens_saida=10_000, tokens_reasoning=20_000)
    esperado = (60_000 * 2.00 + 40_000 * 0.50 + 30_000 * 6.00) / 1_000_000
    assert custo_chamada(e, PRECOS_PADRAO) == pytest.approx(esperado)


def test_custo_chamada_contexto_longo_dobra_tarifa():
    e = _etapa_api(modelo="grok-4.6", tokens_entrada=250_000, tokens_saida=1_000)
    esperado = (250_000 * 4.00 + 1_000 * 12.00) / 1_000_000
    assert custo_chamada(e, PRECOS_PADRAO) == pytest.approx(esperado)


def test_custo_chamada_modelo_sem_preco_retorna_none():
    assert custo_chamada(_etapa_api(modelo="outro", tokens_entrada=10), PRECOS_PADRAO) is None


def test_carregar_precos_de_arquivo(tmp_path):
    arquivo = tmp_path / "precos.json"
    arquivo.write_text(json.dumps({"grok-9": {"entrada": 1, "cache": 0.1, "saida": 3}}))
    precos = carregar_precos(str(arquivo))
    assert precos["grok-9"]["entrada_longo"] == 1.0
    assert "grok-4.7" in precos
    e = _etapa_api(modelo="grok-9", tokens_entrada=1_000_000, tokens_saida=1_000_000)
    assert custo_chamada(e, precos) == pytest.approx(4.0)
