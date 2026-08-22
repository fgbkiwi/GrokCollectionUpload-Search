"""
Dossiê de Prova - Análise e catalogação de provas dos autos.

Este pacote fornece funcionalidades para:
- Exame de provas documentais, periciais e orais
- Aplicação de regras de valoração probatória
- Montagem de dossiê estruturado por questão
- Persistência local de dossiês
"""

__version__ = "1.0.0"

from .schema import (
    DossieProva,
    DossieQuestao,
    ProvaDocumental,
    ProvaPericial,
    ProvaOral,
)
from .examinador_documental import ExaminadorDocumental
from .examinador_pericial import ExaminadorPericial
from .examinador_oral import ExaminadorOral
from .orquestrador import OrquestradorDossie
from .persistencia import PersistenciaDossie

__all__ = [
    "DossieProva",
    "DossieQuestao",
    "ProvaDocumental",
    "ProvaPericial",
    "ProvaOral",
    "ExaminadorDocumental",
    "ExaminadorPericial",
    "ExaminadorOral",
    "OrquestradorDossie",
    "PersistenciaDossie",
]
