"""Peças do PJe: o ID fica na última página e nenhum teor é omitido."""

import json
from unittest.mock import MagicMock, patch

from cartao_caso import ExtratorCartao
from dossie_prova import OrquestradorDossie
from pje_ids import (
    agrupar_pecas_em_lotes,
    dividir_em_pecas,
    extrair_ids_pje_do_texto,
    inferir_id_proximo_ao_trecho,
)


def _assinatura(id_pje: str) -> str:
    return (
        f"Documento assinado eletronicamente por NOME, "
        f"em 25/06/2026, às 18:10:53 - {id_pje}\n"
    )


def test_id_alfanumerico_no_fim_da_assinatura():
    texto = (
        "Documento assinado eletronicamente por MIGUEL FERREIRA DE MELO JUNIOR, "
        "em 25/06/2026, às 18:10:53 - bfaaldf"
    )
    assert extrair_ids_pje_do_texto(texto) == ["bfaaldf"]


def test_hifen_do_nome_nao_rouba_o_id():
    texto = (
        "Documento assinado eletronicamente por PROCEDIMENTO AUTOMATIZADO - PJE, "
        "em 12/06/2026, às 00:32:38 - 4ac9a65"
    )
    assert extrair_ids_pje_do_texto(texto) == ["4ac9a65"]


def test_peca_reune_paginas_ate_a_assinatura_final():
    texto = (
        "Página 1 da contestação. Teses do réu.\n"
        "## Página 2 — Fls.: 532\n"
        "Continuação das teses até a última página.\n"
        + _assinatura("4ac9a65")
        + "## Página 3 — Fls.: 543\n"
        + "Parecer do MPT.\n"
        + _assinatura("c7df676")
    )
    pecas = dividir_em_pecas(texto)
    assert [peca.id_pje for peca in pecas] == ["4ac9a65", "c7df676"]
    assert "Página 1 da contestação" in pecas[0].texto
    assert "Continuação das teses" in pecas[0].texto
    assert "Parecer do MPT" not in pecas[0].texto
    assert "".join(peca.texto for peca in pecas) == texto


def test_id_da_peca_mesmo_quando_a_assinatura_esta_longe():
    corpo = "Contestação do réu impugna o pedido. " + ("tese específica. " * 400)
    texto = corpo + "\n" + _assinatura("4ac9a65")
    assert len(corpo) > 3_000
    assert inferir_id_proximo_ao_trecho(texto, "Contestação do réu impugna o pedido.") == "4ac9a65"


def test_lotes_levam_pecas_inteiras_sem_omitir_texto():
    peca_a = "CONTESTACAO " + ("a" * 120) + "\n" + _assinatura("4ac9a65")
    peca_b = "PARECER MPT " + ("b" * 120) + "\n" + _assinatura("c7df676")
    peca_c = "ACORDO " + ("c" * 120) + "\n" + _assinatura("afff086")
    texto = peca_a + peca_b + peca_c
    pecas = dividir_em_pecas(texto)
    lotes = agrupar_pecas_em_lotes(pecas, max_chars=len(peca_a) + len(peca_b) - 1)

    assert "".join(lotes) == texto
    for peca in pecas:
        assert sum(peca.texto in lote for lote in lotes) == 1


def test_dossie_nao_corta_peca_no_meio():
    peca = "Laudo pericial com conclusão.\n" + ("metodologia. " * 40) + _assinatura("08896fe")
    outra = "Decisão de tutela.\n" + _assinatura("4a41ac2")
    texto = peca + outra
    lotes = OrquestradorDossie("fake")._particionar_em_lotes(
        texto, tamanho_max=len(peca) + 5, overlap=10
    )
    assert any(peca in lote for lote in lotes)
    assert "".join(lotes) == texto


def _resposta(corpo: dict) -> MagicMock:
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(corpo)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }
    return resp


@patch("cartao_caso.extrator.requests.Session")
def test_extracao_distribui_lotes_e_preserva_a_contestacao(mock_session_class, tmp_path):
    inicial = "PETIÇÃO INICIAL\nPedido de anulação da eleição.\n" + _assinatura("111aaa1")
    defesa = "CONTESTAÇÃO\nTese de incompetência da vara.\n" + _assinatura("4ac9a65")
    arquivo = tmp_path / "autos.md"
    arquivo.write_text(inicial + defesa, encoding="utf-8")

    enviados = []

    def post(url, json=None, timeout=None):
        texto = json["messages"][1]["content"]
        enviados.append(texto)
        if "4ac9a65" in texto:
            corpo = {
                "contestacoes": [{
                    "pedido_id": "P1",
                    "impugnacao_especifica": True,
                    "teses": ["Incompetência da vara"],
                    "fontes": [{
                        "trecho": "Tese de incompetência da vara.",
                        "id_pje": None,
                        "folhas": "fls. 531",
                    }],
                }],
                "avisos": [{
                    "tipo": "dado_ausente",
                    "descricao": (
                        "O sumário registra ID 111aaa1, mas o teor não consta do trecho."
                    ),
                    "pedido_id": None,
                    "questao_id": None,
                }],
            }
        else:
            corpo = {
                "numero_processo": "0000678-76.2026.5.10.0009",
                "peticao_inicial": {
                    "causa_pedir": "Representação sindical",
                    "pedidos": [{
                        "id": "P1",
                        "descricao": "Anulação da eleição",
                        "reflexos": False,
                        "fontes": [{
                            "trecho": "Pedido de anulação da eleição.",
                            "id_pje": None,
                            "folhas": "fls. 3",
                        }],
                    }],
                },
                "questoes": [{
                    "id": "Q1",
                    "titulo": "Validade da eleição",
                    "tipo": "mista",
                    "momento": "merito",
                    "de_oficio": False,
                    "arguida_na_defesa": True,
                    "acarreta_extincao": False,
                    "mencionar_na_minuta": True,
                    "pedido_ids": ["P1"],
                    "fontes": [],
                }],
                "avisos": [{
                    "tipo": "dado_ausente",
                    "descricao": (
                        "O sumário registra Contestação de ID 4ac9a65, "
                        "mas o seu teor não consta do trecho disponibilizado."
                    ),
                    "pedido_id": None,
                    "questao_id": None,
                }],
            }
        return _resposta(corpo)

    mock_session_class.return_value.post.side_effect = post
    extrator = ExtratorCartao("test-key")
    extrator.MAX_CHARS_ENVIO = len(inicial) + 8

    cartao = extrator.extrair_de_arquivo(arquivo)

    assert len(enviados) == 2
    assert any("Pedido de anulação da eleição." in texto for texto in enviados)
    assert any("Tese de incompetência da vara." in texto and "4ac9a65" in texto for texto in enviados)
    assert cartao.peticao_inicial["pedidos"][0]["descricao"] == "Anulação da eleição"
    assert cartao.contestacoes[0].teses == ["Incompetência da vara"]
    assert cartao.contestacoes[0].fontes[0].id_pje == "4ac9a65"
    assert not any("não consta" in aviso.descricao for aviso in cartao.avisos)
    assert any("Nenhuma peça foi omitida" in aviso.descricao for aviso in cartao.avisos)


def test_aviso_de_peca_ausente_so_no_lote_e_descartado_na_fusao():
    avisos = [
        {
            "tipo": "outro",
            "descricao": "A petição inicial não integra este lote; P1 a P3 foram extraídos do relatório da decisão.",
        },
        {
            "tipo": "outro",
            "descricao": "Não há contestação nem réplica neste lote.",
        },
        {
            "tipo": "outro",
            "descricao": "A petição inicial e a contestação formal não estão neste lote.",
        },
        {
            "tipo": "outro",
            "descricao": (
                "A COBRAPOL expressamente reservou a contestação de mérito para 12/06/2026; "
                "a manifestação de fls. 236-242 não impugna o mérito da ação."
            ),
        },
        {
            "tipo": "outro",
            "descricao": (
                "Divergência de CNPJ da COBRAPOL: a petição inicial indica 37.116.480/0001-38."
            ),
        },
    ]
    fundido = ExtratorCartao._fundir_cartoes(
        [{"avisos": avisos, "peticao_inicial": {"pedidos": []}, "questoes": []}],
        {"4ac9a65"},
    )
    textos = [aviso["descricao"] for aviso in fundido["avisos"]]
    assert not any("não integra este lote" in texto for texto in textos)
    assert not any("Não há contestação nem réplica neste lote" in texto for texto in textos)
    assert not any("não estão neste lote" in texto for texto in textos)
    assert any("reservou a contestação" in texto for texto in textos)
    assert any("Divergência de CNPJ" in texto for texto in textos)
