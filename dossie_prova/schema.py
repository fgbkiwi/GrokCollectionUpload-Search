"""
Schema JSON do Dossiê de Prova usando Pydantic para validação.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ProvaDocumental(BaseModel):
    """Prova documental relacionada a uma questão."""
    trecho: str = Field(..., description="Trecho literal do documento")
    id_pje: Optional[str] = Field(None, description="ID do PJe se encontrado")
    folhas: Optional[str] = Field(None, description="Referência a folhas")
    relevancia: Literal["alta", "media", "baixa"] = Field(..., description="Grau de relevância")
    favoravel_a: Literal["autor", "reu", "neutro"] = Field(..., description="Favorabilidade da prova")
    tipo_documento: Optional[str] = Field(None, description="Tipo do documento (ex: contrato, recibo, etc.)")
    observacao: Optional[str] = Field(None, description="Observações sobre a prova")


class ProvaPericial(BaseModel):
    """Prova pericial relacionada a uma questão."""
    trecho: str = Field(..., description="Trecho literal do laudo")
    id_pje: Optional[str] = Field(None, description="ID do PJe se encontrado")
    folhas: Optional[str] = Field(None, description="Referência a folhas")
    relevancia: Literal["alta", "media", "baixa"] = Field(..., description="Grau de relevância")
    favoravel_a: Literal["autor", "reu", "neutro"] = Field(..., description="Favorabilidade da prova")
    tipo_laudo: Optional[str] = Field(None, description="Tipo do laudo (ex: médico, ambiental, contábil)")
    observacao: Optional[str] = Field(None, description="Observações sobre a prova")


class ProvaOral(BaseModel):
    """Prova oral relacionada a uma questão."""
    trecho: str = Field(..., description="Trecho literal do depoimento com carimbo de tempo se existir")
    id_pje: Optional[str] = Field(None, description="ID do PJe se encontrado")
    folhas: Optional[str] = Field(None, description="Referência a folhas")
    relevancia: Literal["alta", "media", "baixa"] = Field(..., description="Grau de relevância")
    favoravel_a: Literal["autor", "reu", "neutro"] = Field(..., description="Favorabilidade da prova")
    tipo_depoente: Literal["reclamante", "reclamada", "preposto", "testemunha_autor", "testemunha_reu"] = Field(
        ..., description="Tipo de depoente"
    )
    nome_depoente: Optional[str] = Field(None, description="Nome do depoente")
    observacao: Optional[str] = Field(None, description="Observações sobre valoração")
    desconsiderada: bool = Field(False, description="Se a prova foi desconsiderada por alguma regra")
    motivo_desconsideracao: Optional[str] = Field(None, description="Motivo da desconsideração")


class DossieQuestao(BaseModel):
    """Dossiê de provas para uma questão específica."""
    questao_id: str = Field(..., description="ID da questão do cartão")
    questao_titulo: str = Field(..., description="Título da questão")
    provas_documentais: List[ProvaDocumental] = Field(default_factory=list, description="Provas documentais")
    provas_periciais: List[ProvaPericial] = Field(default_factory=list, description="Provas periciais")
    provas_orais: List[ProvaOral] = Field(default_factory=list, description="Provas orais")
    avisos: List[str] = Field(default_factory=list, description="Avisos sobre a análise de provas")


class DossieProva(BaseModel):
    """Dossiê completo de provas do processo."""
    dossie_schema_version: int = Field(1, description="Versão do schema do dossiê")
    data_criacao: datetime = Field(default_factory=datetime.now, description="Data e hora da criação")
    cartao_origem: str = Field(..., description="Nome do arquivo de cartão de origem")
    arquivo_autos: str = Field(..., description="Nome do arquivo MD dos autos")
    
    dossies_por_questao: List[DossieQuestao] = Field(
        default_factory=list,
        description="Dossiês de prova por questão"
    )
    
    avisos_gerais: List[str] = Field(
        default_factory=list,
        description="Avisos gerais sobre a análise"
    )
