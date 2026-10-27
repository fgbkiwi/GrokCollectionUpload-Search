"""
Segmentação dos autos em conteúdo documental, pericial e oral.

Os autos são divididos em documentos (pela linha de assinatura eletrônica do
PJe; na falta dela, por títulos Markdown ou blocos de parágrafos) e cada
documento é classificado individualmente. Petições que apenas *mencionam*
perícia ou testemunhas continuam no segmento documental.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from pje_ids import RE_ASSINATURA

TAMANHO_BLOCO_FALLBACK = 8_000

_RE_TITULO_MD = re.compile(r"^#{1,3}\s", re.MULTILINE)

_MARCADORES_ORAIS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"compromissad[ao]",
        r"advertid[ao]\s+(?:e\s+)?compromissad|advertid[ao]\s+das\s+penas",
        r"\binquirid[ao]",
        r"\bdepoente\b",
        r"nada\s+mais\s+(?:disse|foi\s+dito|havendo)",
        r"\breperguntas?\b",
        r"[àa]s\s+perguntas\s+d[oa]",
        r"\binterrogad[ao]\b",
        r"depoimento\s+pessoal\s+d[oa]\s+(?:reclamante|reclamad[ao]|preposto|autor|r[ée]u)",
        r"testemunha\s+(?:do|da|arrolad[ao]|ouvid[ao]|indicad[ao])",
        r"\[\d{1,2}:\d{2}(?::\d{2})?\]",
    )
]
_MARCADORES_ORAIS_NUCLEO = re.compile(
    r"depoente|testemunha|depoimento|interrogad", re.IGNORECASE
)

_MARCADORES_PERICIAIS_FORTES = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"laudo\s+pericial",
        r"laudo\s+t[ée]cnico",
        r"conclus[ãa]o\s+(?:pericial|do\s+laudo|do\s+perito)",
        r"respostas?\s+aos\s+quesitos",
        r"esclarecimentos\s+(?:periciais|do\s+perito)",
    )
]
_MARCADORES_PERICIAIS_APOIO = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"perit[oa]\s+(?:do\s+ju[ií]zo|judicial|nomead[oa]|oficial)",
        r"\bvistoria\b",
        r"\bmetodologia\b",
        r"\bquesitos?\b",
        r"assistente\s+t[ée]cnico",
    )
]


def dividir_em_blocos(texto: str) -> List[str]:
    """Divide os autos em documentos/blocos preservando a ordem."""
    fins = []
    for match in RE_ASSINATURA.finditer(texto):
        fim_linha = texto.find("\n", match.end())
        fins.append(len(texto) if fim_linha == -1 else fim_linha + 1)

    if len(fins) >= 2:
        blocos, inicio = [], 0
        for fim in fins:
            if fim > inicio:
                blocos.append(texto[inicio:fim])
                inicio = fim
        if texto[inicio:].strip():
            blocos.append(texto[inicio:])
        return blocos

    titulos = [m.start() for m in _RE_TITULO_MD.finditer(texto)]
    if len(titulos) >= 2:
        cortes = ([0] if titulos[0] > 0 else []) + titulos + [len(texto)]
        return [texto[a:b] for a, b in zip(cortes, cortes[1:]) if texto[a:b].strip()]

    blocos, atual = [], ""
    for paragrafo in re.split(r"(\n\s*\n)", texto):
        if len(atual) + len(paragrafo) > TAMANHO_BLOCO_FALLBACK and atual.strip():
            blocos.append(atual)
            atual = ""
        atual += paragrafo
    if atual.strip():
        blocos.append(atual)
    return blocos


def _titulo(bloco: str) -> str:
    for linha in bloco.strip().splitlines()[:3]:
        if linha.strip():
            return linha.strip().lower()
    return ""


def classificar_bloco(bloco: str) -> str:
    """Retorna 'oral', 'pericial' ou 'documental'."""
    titulo = _titulo(bloco)

    fortes = sum(1 for p in _MARCADORES_PERICIAIS_FORTES if p.search(bloco))
    apoio = sum(1 for p in _MARCADORES_PERICIAIS_APOIO if p.search(bloco))
    pericial = "laudo" in titulo or "esclarecimentos periciais" in titulo or (
        fortes >= 1 and fortes + apoio >= 3
    )

    orais = sum(1 for p in _MARCADORES_ORAIS if p.search(bloco))
    nucleo_oral = bool(_MARCADORES_ORAIS_NUCLEO.search(bloco))
    titulo_oral = any(
        t in titulo for t in ("depoimento", "ata de audiência", "termo de audiência", "audiência de instrução")
    )
    oral = nucleo_oral and (orais >= 3 or (titulo_oral and orais >= 1) or "depoimento" in titulo)

    if pericial and oral:
        return "pericial" if fortes + apoio >= orais else "oral"
    if pericial:
        return "pericial"
    if oral:
        return "oral"
    return "documental"


def segmentar_autos(conteudo: str) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Segmenta os autos; retorna (texto por segmento, nº de blocos por segmento)."""
    partes: Dict[str, List[str]] = {"documental": [], "pericial": [], "oral": []}
    for bloco in dividir_em_blocos(conteudo):
        partes[classificar_bloco(bloco)].append(bloco)
    segmentos = {k: "".join(v) for k, v in partes.items()}
    contagem = {k: len(v) for k, v in partes.items()}
    return segmentos, contagem
