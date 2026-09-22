"""
Extração determinística de IDs do PJe.

Formatos comuns nos autos:
- "Documento assinado eletronicamente por NOME, em DD/MM/AAAA, às HH:MM:SS - c7dbfbc"
- "ID c7dbfbc", "ID. c7dbfbc", "(ID b9283dd)"
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Set

# Hash típico do PJe: 7 caracteres hexadecimais (aceita maiúsculas/minúsculas).
_ID_TOKEN = r"[0-9a-fA-F]{7}"

RE_ASSINATURA = re.compile(
    r"Documento\s+assinado\s+eletronicamente[^\n]*?-\s*(" + _ID_TOKEN + r")\b",
    re.IGNORECASE,
)
RE_ID_EXPLICITO = re.compile(
    r"\bID[.\s:]+(" + _ID_TOKEN + r")\b",
    re.IGNORECASE,
)
RE_ID_PARENTESES = re.compile(
    r"\(\s*ID\s+(" + _ID_TOKEN + r")\b",
    re.IGNORECASE,
)
# Aceita também IDs numéricos longos legados (8+ dígitos) em citações "(ID 12345678".
RE_ID_NUMERICO = re.compile(
    r"\(\s*ID\s+(\d{6,})\b",
    re.IGNORECASE,
)

INSTRUCAO_IDS_PJE = (
    "ID do PJe: string alfanumérica de 7 caracteres (ex.: c7dbfbc, b9283dd), "
    "extraída tipicamente do final da linha "
    "'Documento assinado eletronicamente por ..., em DD/MM/AAAA, às HH:MM:SS - XXXXXXX'. "
    "Também pode aparecer como 'ID XXXXXXX', 'ID. XXXXXXX' ou '(ID XXXXXXX)'. "
    "Nunca invente ID; se não encontrar, use null (não escreva 'não informado')."
)


def normalizar_id_pje(valor: Optional[str]) -> Optional[str]:
    """Normaliza ID removendo prefixo 'ID' e espaços; retorna None se vazio."""
    if not valor:
        return None
    texto = str(valor).strip()
    texto = re.sub(r"^ID[.\s:]+", "", texto, flags=re.IGNORECASE).strip()
    if not texto or texto.lower() in {"null", "none", "não informado", "nao informado"}:
        return None
    return texto


def extrair_ids_pje_do_texto(texto: str) -> List[str]:
    """Extrai IDs únicos preservando a ordem de aparição."""
    if not texto:
        return []
    vistos: Set[str] = set()
    ordenados: List[str] = []
    for padrao in (RE_ASSINATURA, RE_ID_EXPLICITO, RE_ID_PARENTESES, RE_ID_NUMERICO):
        for match in padrao.finditer(texto):
            id_norm = normalizar_id_pje(match.group(1))
            if id_norm and id_norm.lower() not in vistos:
                vistos.add(id_norm.lower())
                ordenados.append(id_norm)
    return ordenados


def inferir_id_proximo_ao_trecho(
    texto_completo: str,
    trecho: str,
    janela: int = 1200,
) -> Optional[str]:
    """
    Procura ID na vizinhança do trecho (preferência: após o trecho, linha de assinatura).
    """
    if not texto_completo or not trecho:
        return None

    trecho_limpo = trecho.strip()
    if len(trecho_limpo) < 20:
        ancora = trecho_limpo
    else:
        ancora = trecho_limpo[:80]

    pos = texto_completo.find(ancora)
    if pos < 0:
        # fallback: busca casefold
        pos = texto_completo.casefold().find(ancora.casefold())
    if pos < 0:
        ids_no_trecho = extrair_ids_pje_do_texto(trecho)
        return ids_no_trecho[0] if ids_no_trecho else None

    inicio = max(0, pos - 200)
    fim = min(len(texto_completo), pos + len(ancora) + janela)
    vizinhanca = texto_completo[inicio:fim]

    # Preferir assinatura eletrônica na janela posterior ao trecho.
    depois = texto_completo[pos : fim]
    m = RE_ASSINATURA.search(depois)
    if m:
        return normalizar_id_pje(m.group(1))

    ids = extrair_ids_pje_do_texto(vizinhanca)
    if ids:
        return ids[-1]  # o mais próximo do fim da janela costuma ser a assinatura

    ids_no_trecho = extrair_ids_pje_do_texto(trecho)
    return ids_no_trecho[0] if ids_no_trecho else None


def enriquecer_id_em_objetos(
    objetos: Iterable[object],
    texto_fonte: str,
    attr_trecho: str = "trecho",
    attr_id: str = "id_pje",
) -> int:
    """
    Preenche id_pje ausente em objetos com atributo trecho.
    Retorna quantidade de IDs preenchidos.
    """
    preenchidos = 0
    for obj in objetos:
        atual = normalizar_id_pje(getattr(obj, attr_id, None))
        if atual:
            if getattr(obj, attr_id, None) != atual:
                setattr(obj, attr_id, atual)
            continue
        trecho = getattr(obj, attr_trecho, None) or ""
        inferido = inferir_id_proximo_ao_trecho(texto_fonte, trecho)
        if inferido:
            setattr(obj, attr_id, inferido)
            preenchidos += 1
    return preenchidos


def enriquecer_fontes_dict(fontes: List[dict], texto_fonte: str) -> int:
    """Preenche id_pje em listas de fontes no formato dict (cartão)."""
    preenchidos = 0
    for fonte in fontes or []:
        if not isinstance(fonte, dict):
            continue
        atual = normalizar_id_pje(fonte.get("id_pje"))
        if atual:
            fonte["id_pje"] = atual
            continue
        trecho = fonte.get("trecho") or ""
        inferido = inferir_id_proximo_ao_trecho(texto_fonte, trecho)
        if inferido:
            fonte["id_pje"] = inferido
            preenchidos += 1
    return preenchidos
