"""
Testes unitários para o módulo Cartão do Caso.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from cartao_caso import (
    CartaoDoCaso,
    Pedido,
    Contestacao,
    Questao,
    Parte,
    Fonte,
    Aviso,
    ExtratorCartao,
    PersistenciaCartao
)


MD_SINTETICO_AUTOS = """# PROCESSO Nº 0001234-56.2023.5.10.0001

## PETIÇÃO INICIAL

**RECLAMANTE:** João da Silva
**RECLAMADA:** Empresa ABC LTDA

### CAUSA DE PEDIR
O reclamante trabalhou como operador de produção no período de 01/01/2020 a 31/12/2022,
cumprindo jornada extraordinária habitual de 2 horas diárias sem o devido pagamento do adicional
de horas extras (ID 12345678, fls. 10).

### PEDIDOS
P1) Pagamento de horas extraordinárias não adimplidas no período de 01/2020 a 12/2022, com reflexos
em 13º salário, férias + 1/3, FGTS + 40%, no valor de R$ 50.000,00 (ID 12345678, fls. 12).

P2) Danos morais no valor de R$ 10.000,00 em razão do não pagamento das verbas rescisórias
(ID 12345678, fls. 15).

## CONTESTAÇÃO

A reclamada apresentou contestação arguindo:

### PRELIMINAR
Incompetência territorial desta Vara do Trabalho, pois o contrato foi firmado em Brasília (fls. 45).

### MÉRITO

**Quanto ao Pedido P1 (Horas Extras):**
Nega genericamente a existência de horas extras. Alega que o reclamante cumpria jornada normal
de 8 horas diárias (ID 23456789, fls. 50).

**Quanto ao Pedido P2 (Danos Morais):**
Impugna especificamente. Alega que todas as verbas rescisórias foram pagas e comprova com
recibos assinados pelo reclamante. Junta comprovantes de pagamento de FGTS, 13º e férias
proporcionais (ID 23456789, fls. 55-60).

### QUESTÃO DE OFÍCIO
A reclamada não arguiu prescrição, mas o juiz observa que parte das horas extras pleiteadas
pode estar prescrita (período anterior a 01/2021).

## PROVAS
- Testemunha do reclamante: José Santos, colega de trabalho (arrolada fls. 18)
- Documental: Cartões de ponto (ID 12345678, fls. 20-40)
- Documental da reclamada: Recibos de pagamento (ID 23456789, fls. 55-60)
"""


@pytest.fixture
def md_autos_temp(tmp_path):
    """Cria arquivo MD temporário para testes."""
    arquivo = tmp_path / "autos_teste.md"
    arquivo.write_text(MD_SINTETICO_AUTOS, encoding='utf-8')
    return arquivo


@pytest.fixture
def mock_response_api():
    """Mock da resposta da API xAI."""
    return {
        "numero_processo": "0001234-56.2023.5.10.0001",
        "partes": [
            {"tipo": "reclamante", "nome": "João da Silva"},
            {"tipo": "reclamada", "nome": "Empresa ABC LTDA"}
        ],
        "peticao_inicial": {
            "causa_pedir": "Trabalho em jornada extraordinária habitual sem pagamento",
            "pedidos": [
                {
                    "id": "P1",
                    "descricao": "Horas extraordinárias",
                    "periodo": "01/2020 a 12/2022",
                    "valor": "R$ 50.000,00",
                    "reflexos": True,
                    "fontes": [
                        {
                            "trecho": "jornada extraordinária habitual de 2 horas diárias",
                            "id_pje": "ID 12345678",
                            "folhas": "fls. 10"
                        }
                    ]
                },
                {
                    "id": "P2",
                    "descricao": "Danos morais",
                    "periodo": None,
                    "valor": "R$ 10.000,00",
                    "reflexos": False,
                    "fontes": [
                        {
                            "trecho": "não pagamento das verbas rescisórias",
                            "id_pje": "ID 12345678",
                            "folhas": "fls. 15"
                        }
                    ]
                }
            ]
        },
        "contestacoes": [
            {
                "pedido_id": "P1",
                "impugnacao_especifica": False,
                "teses": ["Nega genericamente horas extras", "Jornada normal de 8 horas"],
                "fontes": [
                    {
                        "trecho": "Nega genericamente a existência de horas extras",
                        "id_pje": "ID 23456789",
                        "folhas": "fls. 50"
                    }
                ]
            },
            {
                "pedido_id": "P2",
                "impugnacao_especifica": True,
                "teses": ["Todas as verbas foram pagas", "Junta comprovantes"],
                "fontes": [
                    {
                        "trecho": "comprova com recibos assinados",
                        "id_pje": "ID 23456789",
                        "folhas": "fls. 55-60"
                    }
                ]
            }
        ],
        "replica": {
            "existe": False,
            "pontos_principais": [],
            "fontes": []
        },
        "questoes": [
            {
                "id": "Q1",
                "titulo": "Competência territorial",
                "tipo": "direito",
                "natureza_fatica": None,
                "momento": "pressuposto_processual",
                "de_oficio": True,
                "arguida_na_defesa": True,
                "acarreta_extincao": False,
                "mencionar_na_minuta": True,
                "pedido_ids": [],
                "fontes": [
                    {
                        "trecho": "contrato foi firmado em Brasília",
                        "id_pje": None,
                        "folhas": "fls. 45"
                    }
                ]
            },
            {
                "id": "Q2",
                "titulo": "Existência de jornada extraordinária habitual",
                "tipo": "fato",
                "natureza_fatica": "constitutivo",
                "momento": "merito",
                "de_oficio": False,
                "arguida_na_defesa": False,
                "acarreta_extincao": False,
                "mencionar_na_minuta": True,
                "pedido_ids": ["P1"],
                "fontes": []
            },
            {
                "id": "Q3",
                "titulo": "Prescrição parcial das horas extras",
                "tipo": "direito",
                "natureza_fatica": "extintivo",
                "momento": "preliminar",
                "de_oficio": True,
                "arguida_na_defesa": False,
                "acarreta_extincao": True,
                "mencionar_na_minuta": True,
                "pedido_ids": ["P1"],
                "fontes": []
            },
            {
                "id": "Q4",
                "titulo": "Questão de ofício não arguida sem extinção",
                "tipo": "direito",
                "natureza_fatica": None,
                "momento": "preliminar",
                "de_oficio": True,
                "arguida_na_defesa": False,
                "acarreta_extincao": False,
                "mencionar_na_minuta": False,
                "pedido_ids": [],
                "fontes": []
            }
        ],
        "mapa_pedido_defesa_questao": [
            {
                "pedido_id": "P1",
                "tem_contestacao": True,
                "questao_ids": ["Q2", "Q3"]
            },
            {
                "pedido_id": "P2",
                "tem_contestacao": True,
                "questao_ids": []
            }
        ],
        "avisos": [
            {
                "tipo": "falta_impugnacao_especifica",
                "descricao": "Pedido P1 não teve impugnação específica (art. 341 CPC)",
                "pedido_id": "P1",
                "questao_id": None
            }
        ]
    }


class TestSchema:
    """Testes do schema Pydantic."""
    
    def test_cartao_valido(self, mock_response_api):
        """Testa criação de cartão válido."""
        mock_response_api["arquivo_origem"] = "teste.md"
        cartao = CartaoDoCaso(**mock_response_api)
        
        assert cartao.numero_processo == "0001234-56.2023.5.10.0001"
        assert len(cartao.partes) == 2
        assert len(cartao.questoes) == 4
        assert cartao.cartao_schema_version == 1
    
    def test_pedido_com_reflexos(self):
        """Testa pedido com reflexos."""
        pedido = Pedido(
            id="P1",
            descricao="Horas extras",
            reflexos=True,
            fontes=[]
        )
        
        assert pedido.reflexos is True
        assert pedido.id == "P1"
    
    def test_questao_de_oficio_nao_mencionar(self):
        """Testa questão de ofício que NÃO deve ser mencionada."""
        questao = Questao(
            id="Q1",
            titulo="Questão de ofício não arguida",
            tipo="direito",
            momento="preliminar",
            de_oficio=True,
            arguida_na_defesa=False,
            acarreta_extincao=False,
            mencionar_na_minuta=False,
            fontes=[]
        )
        
        assert questao.de_oficio is True
        assert questao.mencionar_na_minuta is False
    
    def test_questao_de_oficio_com_extincao_mencionar(self):
        """Testa questão de ofício com extinção que DEVE ser mencionada."""
        questao = Questao(
            id="Q2",
            titulo="Prescrição (de ofício)",
            tipo="direito",
            momento="preliminar",
            de_oficio=True,
            arguida_na_defesa=False,
            acarreta_extincao=True,
            mencionar_na_minuta=True,
            fontes=[]
        )
        
        assert questao.de_oficio is True
        assert questao.acarreta_extincao is True
        assert questao.mencionar_na_minuta is True


class TestExtrator:
    """Testes do extrator."""
    
    @patch('cartao_caso.extrator.requests.Session')
    def test_extrair_de_arquivo_mock(self, mock_session_class, md_autos_temp, mock_response_api):
        """Testa extração de arquivo com mock da API."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(mock_response_api)
                    }
                }
            ]
        }
        mock_session.post.return_value = mock_response
        
        extrator = ExtratorCartao(api_key="test-key")
        
        cartao = extrator.extrair_de_arquivo(md_autos_temp)
        
        assert cartao.numero_processo == "0001234-56.2023.5.10.0001"
        assert len(cartao.questoes) == 4
        
        questao_nao_mencionar = next(
            (q for q in cartao.questoes if q.id == "Q4"),
            None
        )
        assert questao_nao_mencionar is not None
        assert questao_nao_mencionar.mencionar_na_minuta is False
    
    def test_listar_modelos_fallback(self):
        """Testa fallback quando não consegue listar modelos."""
        extrator = ExtratorCartao(api_key="test-key")
        
        with patch.object(extrator.session, 'get', side_effect=Exception("Network error")):
            modelos = extrator.listar_modelos()
            
            assert "grok-beta" in modelos


class TestPersistencia:
    """Testes de persistência."""
    
    def test_salvar_e_carregar_cartao(self, tmp_path, mock_response_api):
        """Testa salvar e carregar cartão."""
        mock_response_api["arquivo_origem"] = "teste.md"
        cartao_original = CartaoDoCaso(**mock_response_api)
        
        persistencia = PersistenciaCartao(tmp_path)
        
        caminho_salvo = persistencia.salvar_cartao(
            cartao_original,
            confirmado=True
        )
        
        assert caminho_salvo.exists()
        assert "_confirmado.json" in caminho_salvo.name
        
        cartao_carregado = persistencia.carregar_cartao(caminho_salvo)
        
        assert cartao_carregado.numero_processo == cartao_original.numero_processo
        assert len(cartao_carregado.questoes) == len(cartao_original.questoes)
    
    def test_listar_cartoes(self, tmp_path, mock_response_api):
        """Testa listagem de cartões."""
        mock_response_api["arquivo_origem"] = "teste.md"
        cartao = CartaoDoCaso(**mock_response_api)
        
        persistencia = PersistenciaCartao(tmp_path)
        
        persistencia.salvar_cartao(cartao, confirmado=True)
        persistencia.salvar_cartao(cartao, confirmado=False)
        
        todos = persistencia.listar_cartoes(apenas_confirmados=False)
        assert len(todos) == 2
        
        confirmados = persistencia.listar_cartoes(apenas_confirmados=True)
        assert len(confirmados) == 1
    
    def test_exportar_cartao(self, tmp_path, mock_response_api):
        """Testa exportação de cartão."""
        mock_response_api["arquivo_origem"] = "teste.md"
        cartao = CartaoDoCaso(**mock_response_api)
        
        persistencia = PersistenciaCartao(tmp_path)
        
        destino = tmp_path / "exportado" / "cartao.json"
        persistencia.exportar_cartao(cartao, destino)
        
        assert destino.exists()
        
        cartao_exportado = persistencia.carregar_cartao(destino)
        assert cartao_exportado.numero_processo == cartao.numero_processo
    
    def test_estatisticas(self, tmp_path, mock_response_api):
        """Testa obtenção de estatísticas."""
        import time
        
        mock_response_api["arquivo_origem"] = "teste.md"
        cartao = CartaoDoCaso(**mock_response_api)
        
        persistencia = PersistenciaCartao(tmp_path)
        
        persistencia.salvar_cartao(cartao, confirmado=True)
        time.sleep(1.01)
        persistencia.salvar_cartao(cartao, confirmado=True)
        time.sleep(1.01)
        persistencia.salvar_cartao(cartao, confirmado=False)
        
        stats = persistencia.obter_estatisticas()
        
        assert stats["total"] == 3
        assert stats["confirmados"] == 2
        assert stats["rascunhos"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
