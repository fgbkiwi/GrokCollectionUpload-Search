"""
Suporte ao parâmetro reasoning_effort da API xAI (Chat Completions).

Documentação: https://docs.x.ai/developers/model-capabilities/text/reasoning
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

# Níveis por família de modelo (só incluir quando a API aceitar o parâmetro).
# grok-4.7 / grok-4.6: low/medium/high/xhigh (default high)
# grok-4.5: low/medium/high (default high; não desativa)
# grok-4.3: none/low/medium/high (via AI SDK / suporte configurável)
# *-non-reasoning e demais: parâmetro não é enviado
# Ordem: prefixos mais específicos primeiro (startswith).
_REASONING_POR_PREFIXO: Sequence[tuple[str, List[str]]] = (
    ("grok-4.7", ["low", "medium", "high", "xhigh"]),
    ("grok-4.6", ["low", "medium", "high", "xhigh"]),
    ("grok-4.5", ["low", "medium", "high"]),
    ("grok-4.3", ["none", "low", "medium", "high"]),
)

DEFAULT_REASONING_EFFORT = "high"

LABELS_REASONING = {
    "none": "Nenhum (sem reasoning)",
    "low": "Baixo (rápido)",
    "medium": "Médio",
    "high": "Alto (padrão)",
    "xhigh": "Máximo (xhigh)",
}


def normalizar_modelo(modelo: Optional[str]) -> str:
    return (modelo or "").strip().lower()


def niveis_reasoning_para_modelo(modelo: Optional[str]) -> List[str]:
    """Retorna níveis aceitos pelo modelo, ou lista vazia se não suportado."""
    nome = normalizar_modelo(modelo)
    if not nome or "non-reasoning" in nome:
        return []

    # Preferir capabilities da última listagem dinâmica da API.
    try:
        from xai_models import niveis_reasoning_em_cache

        em_cache = niveis_reasoning_em_cache(modelo)
        if em_cache is not None:
            return em_cache
    except Exception:
        pass

    for prefixo, niveis in _REASONING_POR_PREFIXO:
        if nome.startswith(prefixo):
            return list(niveis)
    return []


def modelo_suporta_reasoning(modelo: Optional[str]) -> bool:
    return bool(niveis_reasoning_para_modelo(modelo))


def normalizar_reasoning_effort(
    modelo: Optional[str],
    effort: Optional[str],
) -> Optional[str]:
    """
    Valida o nível para o modelo.
    Retorna None se o modelo não aceitar o parâmetro ou se effort for inválido/vazio.
    """
    niveis = niveis_reasoning_para_modelo(modelo)
    if not niveis:
        return None

    padrao = DEFAULT_REASONING_EFFORT
    try:
        from xai_models import default_reasoning_em_cache

        em_cache = default_reasoning_em_cache(modelo)
        if em_cache and em_cache in niveis:
            padrao = em_cache
    except Exception:
        pass

    valor = (effort or "").strip().lower()
    if not valor:
        return padrao if padrao in niveis else niveis[-1]
    if valor not in niveis:
        return padrao if padrao in niveis else niveis[-1]
    return valor


def aplicar_reasoning_effort(
    payload: Dict[str, Any],
    modelo: Optional[str] = None,
    effort: Optional[str] = None,
) -> Dict[str, Any]:
    """Inclui reasoning_effort no payload apenas quando o modelo permitir."""
    modelo_ref = modelo if modelo is not None else payload.get("model")
    nivel = normalizar_reasoning_effort(modelo_ref, effort)
    if nivel is not None:
        payload["reasoning_effort"] = nivel
    else:
        payload.pop("reasoning_effort", None)
    return payload
