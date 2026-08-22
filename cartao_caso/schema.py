"""
Schema JSON do Cartão do Caso usando Pydantic para validação.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class Fonte(BaseModel):
    """Fonte de informação nos autos."""
    trecho: str = Field(..., description="Trecho relevante do texto")
    id_pje: Optional[str] = Field(None, description="ID do PJe se encontrado (ex: 'ID 12345678')")
    folhas: Optional[str] = Field(None, description="Referência a folhas se encontrada (ex: 'fls. 12')")


class Parte(BaseModel):
    """Parte no processo (reclamante ou reclamada)."""
    tipo: Literal["reclamante", "reclamada"] = Field(..., description="Tipo da parte")
    nome: str = Field(..., description="Nome como consta nos autos")


class Pedido(BaseModel):
    """Pedido formulado na petição inicial."""
    id: str = Field(..., description="Identificador do pedido (ex: 'P1', 'P2')")
    descricao: str = Field(..., description="Descrição do pedido")
    periodo: Optional[str] = Field(None, description="Período se aplicável (ex: '01/2020 a 12/2022')")
    valor: Optional[str] = Field(None, description="Valor se especificado")
    reflexos: bool = Field(False, description="Se há pedido de reflexos (13º, férias, FGTS, etc.)")
    fontes: List[Fonte] = Field(default_factory=list, description="Fontes nos autos")


class Contestacao(BaseModel):
    """Contestação da defesa."""
    pedido_id: str = Field(..., description="ID do pedido contestado")
    impugnacao_especifica: bool = Field(
        ...,
        description="Se houve impugnação específica com grau de detalhe equivalente (art. 341 CPC)"
    )
    teses: List[str] = Field(default_factory=list, description="Teses de defesa")
    fontes: List[Fonte] = Field(default_factory=list, description="Fontes nos autos")


class Questao(BaseModel):
    """Questão a ser decidida."""
    id: str = Field(..., description="Identificador da questão (ex: 'Q1', 'Q2')")
    titulo: str = Field(..., description="Título da questão")
    tipo: Literal["fato", "direito", "mista"] = Field(..., description="Tipo da questão")
    natureza_fatica: Optional[Literal[
        "constitutivo", "impeditivo", "modificativo", "extintivo", "irrelevante"
    ]] = Field(None, description="Natureza fática se aplicável")
    momento: Literal[
        "pressuposto_processual",
        "condicao_da_acao",
        "incidental",
        "preliminar",
        "merito"
    ] = Field(..., description="Momento processual")
    de_oficio: bool = Field(
        False,
        description="Se é questão de ofício (competência, capacidade, prescrição, etc.)"
    )
    arguida_na_defesa: bool = Field(
        False,
        description="Se foi arguida pela defesa"
    )
    acarreta_extincao: bool = Field(
        False,
        description="Se acarreta extinção de algum pedido"
    )
    mencionar_na_minuta: bool = Field(
        ...,
        description=(
            "Se deve ser mencionada na minuta. "
            "Questões de ofício só devem constar se foram arguidas na defesa "
            "OU se acarretam extinção de algum pedido"
        )
    )
    pedido_ids: List[str] = Field(default_factory=list, description="IDs dos pedidos relacionados")
    fontes: List[Fonte] = Field(default_factory=list, description="Fontes nos autos")


class Replica(BaseModel):
    """Réplica da parte autora."""
    existe: bool = Field(False, description="Se existe réplica nos autos")
    pontos_principais: List[str] = Field(default_factory=list, description="Pontos principais da réplica")
    fontes: List[Fonte] = Field(default_factory=list, description="Fontes nos autos")


class Aviso(BaseModel):
    """Avisos sobre a extração."""
    tipo: Literal[
        "falta_impugnacao_especifica",
        "possivel_irrelevancia",
        "falta_id_pje",
        "falta_folhas",
        "dado_ausente",
        "outro"
    ] = Field(..., description="Tipo do aviso")
    descricao: str = Field(..., description="Descrição do aviso")
    pedido_id: Optional[str] = Field(None, description="ID do pedido relacionado se aplicável")
    questao_id: Optional[str] = Field(None, description="ID da questão relacionada se aplicável")


class MapaPedidoDefesa(BaseModel):
    """Mapeamento entre pedido, defesa e questões."""
    pedido_id: str = Field(..., description="ID do pedido")
    tem_contestacao: bool = Field(..., description="Se há contestação específica")
    questao_ids: List[str] = Field(default_factory=list, description="IDs das questões relacionadas")


class CartaoDoCaso(BaseModel):
    """Schema completo do Cartão do Caso."""
    cartao_schema_version: int = Field(
        1,
        description="Versão do schema do cartão"
    )
    data_extracao: datetime = Field(
        default_factory=datetime.now,
        description="Data e hora da extração"
    )
    arquivo_origem: str = Field(..., description="Nome do arquivo MD de origem")
    
    numero_processo: Optional[str] = Field(None, description="Número do processo")
    partes: List[Parte] = Field(default_factory=list, description="Partes no processo")
    
    peticao_inicial: dict = Field(
        default_factory=lambda: {
            "causa_pedir": None,
            "pedidos": []
        },
        description="Petição inicial com causa de pedir e pedidos"
    )
    
    contestacao_geral: Optional[dict] = Field(
        None,
        description="Informações gerais da contestação"
    )
    
    contestacoes: List[Contestacao] = Field(
        default_factory=list,
        description="Contestações específicas por pedido"
    )
    
    replica: Replica = Field(
        default_factory=Replica,
        description="Réplica se existir"
    )
    
    questoes: List[Questao] = Field(
        default_factory=list,
        description="Questões a serem decididas"
    )
    
    mapa_pedido_defesa_questao: List[MapaPedidoDefesa] = Field(
        default_factory=list,
        description="Mapa relacionando pedidos, defesas e questões"
    )
    
    avisos: List[Aviso] = Field(
        default_factory=list,
        description="Avisos sobre a extração"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cartao_schema_version": 1,
                "numero_processo": "0001234-56.2023.5.10.0001",
                "partes": [
                    {
                        "tipo": "reclamante",
                        "nome": "João da Silva"
                    },
                    {
                        "tipo": "reclamada",
                        "nome": "Empresa XYZ LTDA"
                    }
                ],
                "peticao_inicial": {
                    "causa_pedir": "Reclamante trabalhou em jornada extraordinária habitual sem pagamento",
                    "pedidos": [
                        {
                            "id": "P1",
                            "descricao": "Horas extraordinárias",
                            "periodo": "01/2020 a 12/2022",
                            "valor": "R$ 50.000,00",
                            "reflexos": True,
                            "fontes": []
                        }
                    ]
                }
            }
        }
    )
