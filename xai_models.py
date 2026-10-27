"""
Listagem de modelos disponíveis na API xAI (somente com reasoning).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests

API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.7"

# Fallback estático (só famílias com reasoning) quando não há chave ou a API falha.
FALLBACK_MODELS: List[str] = [
    "grok-4.7",
    "grok-4.6",
    "grok-4.5",
    "grok-4.3",
]

# Cache preenchido na última consulta bem-sucedida à API.
_niveis_por_modelo: Dict[str, List[str]] = {}
_default_por_modelo: Dict[str, str] = {}


@dataclass(frozen=True)
class ModeloXai:
    id: str
    reasoning_effort: List[str] = field(default_factory=list)
    default_reasoning_effort: Optional[str] = None

    @property
    def tem_reasoning(self) -> bool:
        return bool(self.reasoning_effort)


def rotulo_modelo(model_id: str) -> str:
    """Rótulo amigável para o dropdown (marca o recomendado)."""
    mid = (model_id or "").strip()
    if mid.startswith("grok-4.7"):
        return f"{mid} (Recomendado)"
    return mid


def _extrair_capabilities(item: dict) -> Tuple[List[str], Optional[str]]:
    caps = item.get("capabilities")
    if not isinstance(caps, dict):
        return [], None
    raw = caps.get("reasoning_effort") or []
    niveis = [str(n).strip().lower() for n in raw if n]
    default = caps.get("default_reasoning_effort")
    default_norm = str(default).strip().lower() if default else None
    return niveis, default_norm


def _atualizar_cache(modelos: List[ModeloXai]) -> None:
    _niveis_por_modelo.clear()
    _default_por_modelo.clear()
    for m in modelos:
        if m.reasoning_effort:
            _niveis_por_modelo[m.id] = list(m.reasoning_effort)
            if m.default_reasoning_effort:
                _default_por_modelo[m.id] = m.default_reasoning_effort


def niveis_reasoning_em_cache(modelo: Optional[str]) -> Optional[List[str]]:
    """Níveis vindos da última consulta à API, ou None se desconhecido."""
    mid = (modelo or "").strip()
    if not mid:
        return None
    if mid in _niveis_por_modelo:
        return list(_niveis_por_modelo[mid])
    mid_l = mid.lower()
    for key, niveis in _niveis_por_modelo.items():
        if key.lower() == mid_l:
            return list(niveis)
    return None


def default_reasoning_em_cache(modelo: Optional[str]) -> Optional[str]:
    mid = (modelo or "").strip()
    if not mid:
        return None
    if mid in _default_por_modelo:
        return _default_por_modelo[mid]
    mid_l = mid.lower()
    for key, valor in _default_por_modelo.items():
        if key.lower() == mid_l:
            return valor
    return None


def buscar_modelos_reasoning_xai(
    api_key: Optional[str],
    timeout: float = 10.0,
) -> Optional[List[ModeloXai]]:
    """
    Consulta GET /v1/models e retorna só modelos com capabilities.reasoning_effort.

    Returns:
        Lista de ModeloXai, ou None se não houver chave / a requisição falhar.
    """
    key = (api_key or "").strip()
    if not key:
        return None

    try:
        from log_execucao import API, etapa

        with etapa("xai.listar_modelos", categoria=API, timeout_s=timeout) as reg:
            response = requests.get(
                f"{API_BASE}/models",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json",
                },
                timeout=timeout,
            )
            reg.registrar_http(response)
            response.raise_for_status()
            data = response.json()
        vistos = set()
        modelos: List[ModeloXai] = []
        for item in data.get("data", []):
            if not isinstance(item, dict):
                continue
            mid = item.get("id")
            if not mid or mid in vistos:
                continue
            niveis, default = _extrair_capabilities(item)
            if not niveis:
                continue
            vistos.add(mid)
            modelos.append(
                ModeloXai(
                    id=mid,
                    reasoning_effort=niveis,
                    default_reasoning_effort=default,
                )
            )
        modelos.sort(key=lambda m: m.id.lower())
        _atualizar_cache(modelos)
        return modelos
    except Exception as e:
        print(f"Aviso: não foi possível listar modelos xAI ({e}).")
        return None


def buscar_modelos_xai(
    api_key: Optional[str],
    timeout: float = 10.0,
) -> Optional[List[str]]:
    """IDs de modelos com reasoning, ou None em falha."""
    modelos = buscar_modelos_reasoning_xai(api_key, timeout=timeout)
    if modelos is None:
        return None
    return [m.id for m in modelos]


def listar_modelos_xai(api_key: Optional[str], timeout: float = 10.0) -> List[str]:
    """
    Lista IDs de modelos com reasoning disponíveis para a API key.

    Em caso de chave ausente/inválida ou falha de rede, retorna FALLBACK_MODELS.
    """
    modelos = buscar_modelos_xai(api_key, timeout=timeout)
    return modelos if modelos is not None else list(FALLBACK_MODELS)


def listar_modelos_para_ui(
    api_key: Optional[str],
    timeout: float = 10.0,
) -> Tuple[List[str], str]:
    """
    Retorna (modelos_com_reasoning, mensagem_status) para popular menus da interface.
    """
    key = (api_key or "").strip()
    if not key:
        return list(FALLBACK_MODELS), (
            "Informe a API Key para carregar os modelos com reasoning da xAI."
        )

    modelos = buscar_modelos_reasoning_xai(key, timeout=timeout)
    if modelos is None:
        return list(FALLBACK_MODELS), (
            "Não foi possível consultar a xAI; exibindo lista padrão (com reasoning)."
        )
    ids = [m.id for m in modelos]
    if not ids:
        return list(FALLBACK_MODELS), (
            "A API não retornou modelos com reasoning; exibindo lista padrão."
        )
    return ids, f"{len(ids)} modelo(s) com reasoning carregado(s) da xAI."
