"""
Schema JSON da Minuta usando Pydantic para validação.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TipoPrecedente(str, Enum):
    """Tipos de precedentes."""
    PROPRIO = "proprio"
    TST = "tst"
    TRT = "trt"
    STF = "stf"
    OUTRO = "outro"


class Precedente(BaseModel):
    """Precedente recuperado da Collection."""
    processo_numero: Optional[str] = Field(None, description="Número do processo")
    ementa: str = Field(..., description="Ementa ou trecho relevante")
    relevancia_score: Optional[float] = Field(None, description="Score de relevância da busca")
    id_collection: Optional[str] = Field(None, description="ID na Collection")
    tipo: TipoPrecedente = Field(TipoPrecedente.PROPRIO, description="Tipo de precedente")


class TopicoEstrutura(BaseModel):
    """Tópico da estrutura da sentença."""
    id: str = Field(..., description="ID do tópico (ex: 'T1', 'T2')")
    titulo: str = Field(..., description="Título do tópico")
    nivel: int = Field(..., description="Nível hierárquico (1, 2, 3...)")
    ordem: int = Field(..., description="Ordem de apresentação")
    questao_id: Optional[str] = Field(None, description="ID da questão relacionada se aplicável")


class MinutaTopico(BaseModel):
    """Minuta de um tópico específico."""
    topico_id: str = Field(..., description="ID do tópico")
    titulo: str = Field(..., description="Título do tópico")
    tese: str = Field(..., description="Tese do autor")
    antitese: str = Field(..., description="Antítese da defesa")
    abordagem: str = Field(..., description="Abordagem proposta")
    conclusao_preliminar: str = Field(..., description="Conclusão preliminar")
    aprovada: bool = Field(False, description="Se foi aprovada pelo juiz")


class MinutaDefinitiva(BaseModel):
    """Minuta definitiva de um tópico."""
    topico_id: str = Field(..., description="ID do tópico")
    titulo: str = Field(..., description="Título do tópico")
    conteudo: str = Field(..., description="Conteudo em Markdown")
    precedentes_citados: List[Precedente] = Field(default_factory=list, description="Precedentes citados")
    ids_citados: List[str] = Field(default_factory=list, description="IDs do PJe citados")
    validada: bool = Field(False, description="Se passou pela validação")
    avisos_validacao: List[str] = Field(default_factory=list, description="Avisos da validação")


class EstruturaMinuta(BaseModel):
    """Estrutura completa da minuta."""
    topicos: List[TopicoEstrutura] = Field(default_factory=list, description="Tópicos organizados")
    aprovada: bool = Field(False, description="Se a estrutura foi aprovada")


class MinutaCompleta(BaseModel):
    """Minuta completa da sentença."""
    minuta_schema_version: int = Field(1, description="Versão do schema")
    data_criacao: datetime = Field(default_factory=datetime.now, description="Data de criação")
    cartao_origem: str = Field(..., description="Nome do arquivo de cartão")
    dossie_origem: str = Field(..., description="Nome do arquivo de dossiê")
    collection_id: Optional[str] = Field(None, description="ID da Collection usada")
    
    estrutura: EstruturaMinuta = Field(..., description="Estrutura aprovada")
    minutas_previas: List[MinutaTopico] = Field(default_factory=list, description="Minutas prévias")
    minutas_definitivas: List[MinutaDefinitiva] = Field(default_factory=list, description="Minutas definitivas")
    
    minuta_final_md: Optional[str] = Field(None, description="Minuta final em Markdown")
    
    criterios_busca: Dict[str, Any] = Field(
        default_factory=dict,
        description="Critérios de busca de precedentes usados"
    )
