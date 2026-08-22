"""
Cartão do Caso - Extração estruturada de autos trabalhistas.

Este pacote fornece funcionalidades para:
- Extração de estrutura JSON de autos em Markdown
- Validação de schema com Pydantic
- Persistência local de cartões
- UI Flet para revisão e confirmação
"""

__version__ = "1.0.0"

from .schema import (
    CartaoDoCaso,
    Parte,
    Pedido,
    Contestacao,
    Questao,
    Fonte,
    Aviso,
)
from .extrator import ExtratorCartao
from .persistencia import PersistenciaCartao

__all__ = [
    "CartaoDoCaso",
    "Parte",
    "Pedido",
    "Contestacao",
    "Questao",
    "Fonte",
    "Aviso",
    "ExtratorCartao",
    "PersistenciaCartao",
]
