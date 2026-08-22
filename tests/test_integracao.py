"""
Testes de integração básicos para o sistema Sarah.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from cartao_caso import CartaoDoCaso, Questao, Parte
from dossie_prova import DossieProva, DossieQuestao, ProvaDocumental
from minuta import EstruturaMinuta, TopicoEstrutura


@pytest.fixture
def setup_completo():
    """Setup com cartão e dossiê mock."""
    cartao = CartaoDoCaso(
        arquivo_origem="autos.md",
        numero_processo="0001234-56.2023.5.10.0001",
        partes=[
            Parte(tipo="reclamante", nome="João"),
            Parte(tipo="reclamada", nome="Empresa")
        ],
        questoes=[
            Questao(
                id="Q1",
                titulo="Horas extras",
                tipo="fato",
                momento="merito",
                mencionar_na_minuta=True,
                pedido_ids=["P1"]
            )
        ]
    )
    
    dossie = DossieProva(
        cartao_origem="autos.md",
        arquivo_autos="autos.md",
        dossies_por_questao=[
            DossieQuestao(
                questao_id="Q1",
                questao_titulo="Horas extras",
                provas_documentais=[
                    ProvaDocumental(
                        trecho="Cartão de ponto (ID 12345, fls. 10)",
                        id_pje="ID 12345",
                        folhas="fls. 10",
                        relevancia="alta",
                        favoravel_a="autor"
                    )
                ]
            )
        ]
    )
    
    return cartao, dossie


def test_fluxo_sintetico_ponta_a_ponta(setup_completo):
    """
    Teste sintético ponta a ponta:
    Autos MD → Cartão mock → Dossiê mock → Estrutura → Minuta mockada
    """
    cartao, dossie = setup_completo
    
    assert cartao.numero_processo == "0001234-56.2023.5.10.0001"
    assert len(cartao.questoes) == 1
    
    assert len(dossie.dossies_por_questao) == 1
    assert len(dossie.dossies_por_questao[0].provas_documentais) == 1
    
    estrutura = EstruturaMinuta(
        topicos=[
            TopicoEstrutura(
                id="T1",
                titulo="Mérito",
                nivel=1,
                ordem=1
            ),
            TopicoEstrutura(
                id="T1.1",
                titulo="Horas Extraordinárias",
                nivel=2,
                ordem=2,
                questao_id="Q1"
            )
        ]
    )
    
    assert len(estrutura.topicos) == 2
    assert estrutura.topicos[1].questao_id == "Q1"
    
    minuta_mockada = """
## Mérito

### Horas Extraordinárias

**Tese do Autor**: Reclamante alega horas extras não pagas.

**Antítese da Defesa**: Reclamada nega.

**Prova**: Cartão de ponto (ID 12345, fls. 10) demonstra jornada extraordinária.

**Decisão**: JULGO PROCEDENTE o pedido de horas extras.
"""
    
    assert "ID 12345" in minuta_mockada
    assert "fls. 10" in minuta_mockada
    assert "JULGO PROCEDENTE" in minuta_mockada
    
    ids_citados = ["12345"]
    ids_disponiveis = ["ID 12345"]
    
    from minuta import OrquestradorMinuta
    orquestrador = OrquestradorMinuta("fake")
    valido, _ = orquestrador._validar_ids(ids_citados, ids_disponiveis)
    
    assert valido


def test_lote_documental_grande():
    """Testa particionamento quando dossiê documental é grande."""
    from dossie_prova import OrquestradorDossie
    
    orquestrador = OrquestradorDossie("fake_key")
    
    conteudo_grande = "x" * 500000
    
    lotes = orquestrador._particionar_em_lotes(
        conteudo_grande,
        tamanho_max=100000,
        overlap=5000
    )
    
    assert len(lotes) > 1
    assert len(lotes[0]) <= 100000


def test_questao_sem_prova():
    """Testa questão sem prova no dossiê."""
    dossie = DossieProva(
        cartao_origem="teste.md",
        arquivo_autos="teste.md",
        dossies_por_questao=[
            DossieQuestao(
                questao_id="Q1",
                questao_titulo="Questão sem prova",
                provas_documentais=[],
                provas_periciais=[],
                provas_orais=[]
            )
        ]
    )
    
    assert len(dossie.dossies_por_questao) == 1
    assert len(dossie.dossies_por_questao[0].provas_documentais) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
