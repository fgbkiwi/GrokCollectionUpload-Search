"""
Minuta - Geração de minuta de sentença trabalhista.

Este pacote fornece funcionalidades para:
- Kernel Sarah com prompt editável
- Biblioteca de modelos temáticos
- Busca de precedentes na Collection xAI
- Geração de minuta em etapas (estrutura → prévia → definitiva)
- Validação de IDs citados
- Persistência local de minutas
"""

__version__ = "1.0.0"

from .schema import (
    MinutaCompleta,
    EstruturaMinuta,
    TopicoEstrutura,
    TipoTopico,
    MinutaTopico,
    MinutaDefinitiva,
    Precedente,
    TipoPrecedente,
)
from .kernel_sarah import KernelSarah
from .kernel_pafuncio import KernelPafuncio
from .modelos_tematicos import BibliotecaModelos, ModeloTematico
from .busca_precedentes import BuscaPrecedentes
from .orquestrador import OrquestradorMinuta
from .persistencia import PersistenciaMinuta

__all__ = [
    "MinutaCompleta",
    "EstruturaMinuta",
    "TopicoEstrutura",
    "TipoTopico",
    "MinutaTopico",
    "MinutaDefinitiva",
    "Precedente",
    "TipoPrecedente",
    "KernelSarah",
    "KernelPafuncio",
    "BibliotecaModelos",
    "ModeloTematico",
    "BuscaPrecedentes",
    "OrquestradorMinuta",
    "PersistenciaMinuta",
]
