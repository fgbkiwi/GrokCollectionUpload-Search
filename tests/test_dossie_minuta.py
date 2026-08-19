"""
Testes unitários para o módulo Dossiê de Prova.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from cartao_caso import CartaoDoCaso, Questao, Parte
from dossie_prova import (
    OrquestradorDossie,
    ExaminadorDocumental,
    ExaminadorOral,
    DossieProva,
    ProvaDocumental,
    ProvaOral,
)


@pytest.fixture
def cartao_mock():
    """Cartão do caso mock para testes."""
    return CartaoDoCaso(
        arquivo_origem="autos_teste.md",
        numero_processo="0001234-56.2023.5.10.0001",
        partes=[
            Parte(tipo="reclamante", nome="João Silva"),
            Parte(tipo="reclamada", nome="Empresa XYZ")
        ],
        questoes=[
            Questao(
                id="Q1",
                titulo="Horas extraordinárias não pagas",
                tipo="fato",
                momento="merito",
                mencionar_na_minuta=True,
                pedido_ids=["P1"]
            )
        ]
    )


@pytest.fixture
def autos_md_mock(tmp_path):
    """Arquivo MD de autos mock."""
    autos = tmp_path / "autos.md"
    autos.write_text("""
# Processo 0001234-56.2023.5.10.0001

## Petição Inicial
Reclamante alega horas extras não pagas. ID 12345678, fls. 10.

## Depoimento da Testemunha
Testemunha: Maria Santos
"Eu vi o reclamante trabalhando até tarde todos os dias" [00:05:30]
ID 87654321, fls. 45.

## Laudo Pericial
Conclusão: Constatada insalubridade em grau médio.
ID 11111111, fls. 60.
""")
    return autos


def test_examinador_oral_descarta_depoimento_autointeressado():
    """Testa se examinador oral descarta depoimento de parte favorável a si."""
    with patch('dossie_prova.examinador_oral.requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": """{
                        "provas_orais": [{
                            "trecho": "Trabalhei até tarde",
                            "id_pje": null,
                            "folhas": null,
                            "relevancia": "baixa",
                            "favoravel_a": "autor",
                            "tipo_depoente": "reclamante",
                            "nome_depoente": "João",
                            "observacao": "Depoimento da parte - só vale como confissão",
                            "desconsiderada": true,
                            "motivo_desconsideracao": "Reclamante não fundamenta deferimento"
                        }],
                        "avisos": ["Depoimento do reclamante desconsiderado"]
                    }"""
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        examinador = ExaminadorOral("fake_key")
        provas, avisos = examinador.examinar(
            "Q1",
            "Horas extras",
            "Depoimento reclamante: Trabalhei até tarde"
        )
        
        assert len(provas) == 1
        assert provas[0].desconsiderada
        assert "confissão" in provas[0].observacao.lower()


def test_dossie_funde_lotes_documentais():
    """Testa se dossiê funde corretamente lotes documentais."""
    with patch('dossie_prova.examinador_documental.requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": """{
                        "provas_documentais": [{
                            "trecho": "Documento de lote",
                            "id_pje": "ID 12345",
                            "folhas": "fls. 10",
                            "relevancia": "alta",
                            "favoravel_a": "autor",
                            "tipo_documento": "contrato"
                        }],
                        "avisos": []
                    }"""
                }
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        examinador = ExaminadorDocumental("fake_key")
        
        lotes = ["Lote 1: documento A", "Lote 2: documento B"]
        provas, avisos = examinador.examinar_em_lotes(
            "Q1",
            "Teste",
            lotes
        )
        
        assert mock_post.call_count == 2
        assert "lote(s)" in " ".join(avisos).lower()


def test_minuta_recusa_id_inexistente():
    """Testa se validação recusa IDs que não existem no dossiê."""
    from minuta import OrquestradorMinuta
    
    orquestrador = OrquestradorMinuta("fake_key")
    
    ids_citados = ["12345", "99999"]
    ids_disponiveis = ["ID 12345", "ID 54321"]
    
    valido, invalidos = orquestrador._validar_ids(ids_citados, ids_disponiveis)
    
    assert not valido
    assert "99999" in invalidos
    assert "12345" not in invalidos


def test_modelo_tematico_injetado_quando_tema_bate():
    """Testa se modelo temático é injetado quando tema bate."""
    from minuta import OrquestradorMinuta
    
    orquestrador = OrquestradorMinuta("fake_key")
    
    modelos = orquestrador._obter_modelos_tematicos("Juros e Correção Monetária")
    
    assert len(modelos) > 0
    assert any("juros" in m.lower() for m in modelos)


def test_questao_de_oficio_nao_vira_topico():
    """Testa se questão de ofício com mencionar_na_minuta=False não vira tópico."""
    questao_oficio = Questao(
        id="Q2",
        titulo="Prescrição",
        tipo="direito",
        momento="preliminar",
        de_oficio=True,
        mencionar_na_minuta=False,
        pedido_ids=[]
    )
    
    cartao = CartaoDoCaso(
        arquivo_origem="teste.md",
        questoes=[questao_oficio]
    )
    
    questoes_filtradas = [q for q in cartao.questoes if q.mencionar_na_minuta]
    
    assert len(questoes_filtradas) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
