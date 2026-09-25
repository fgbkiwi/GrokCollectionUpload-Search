"""
Dropdowns reutilizáveis de Modelo Grok + Nível de reasoning (por fase).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import flet as ft

from xai_models import DEFAULT_MODEL, FALLBACK_MODELS, listar_modelos_para_ui, rotulo_modelo
from xai_reasoning import (
    DEFAULT_REASONING_EFFORT,
    LABELS_REASONING,
    modelo_suporta_reasoning,
    niveis_reasoning_para_modelo,
    normalizar_reasoning_effort,
)

# Atributos no app por fase: (attr_modelo, attr_reasoning, reasoning_default)
FASES = {
    "cartao": ("modelo_cartao", "reasoning_cartao", "medium"),
    "dossie": ("modelo_dossie", "reasoning_dossie", "low"),
    "minuta": ("modelo_minuta", "reasoning_minuta", "high"),
}


class SeletorModeloReasoning:
    """Par de dropdowns vinculados a atributos do app para uma fase."""

    def __init__(
        self,
        app: Any,
        fase: str,
        *,
        width_modelo: int = 210,
        width_reasoning: int = 160,
        on_change: Optional[Callable[[], None]] = None,
    ):
        if fase not in FASES:
            raise ValueError(f"Fase desconhecida: {fase}")
        self.app = app
        self.fase = fase
        self.attr_modelo, self.attr_reasoning, self.reasoning_default = FASES[fase]
        self.on_change = on_change

        modelo_atual = getattr(app, self.attr_modelo, None) or DEFAULT_MODEL
        self.dropdown_modelo = ft.Dropdown(
            label="Modelo",
            width=width_modelo,
            value=modelo_atual,
            options=[ft.dropdown.Option(m, rotulo_modelo(m)) for m in FALLBACK_MODELS],
            on_change=self._ao_mudar_modelo,
        )
        self.dropdown_reasoning = ft.Dropdown(
            label="Reasoning",
            width=width_reasoning,
            on_change=self._ao_mudar_reasoning,
        )
        self.sincronizar()

    def controles(self) -> list[ft.Control]:
        """Controles para incluir numa Row."""
        return [self.dropdown_modelo, self.dropdown_reasoning]

    def sincronizar(self, atualizar_page: bool = False) -> None:
        """Recarrega opções a partir da API key e dos atributos do app."""
        api_key = getattr(self.app, "api_key", None) or ""
        modelos, _msg = listar_modelos_para_ui(api_key)
        atual = getattr(self.app, self.attr_modelo, None) or DEFAULT_MODEL

        self.dropdown_modelo.options = [
            ft.dropdown.Option(m, rotulo_modelo(m)) for m in modelos
        ]
        if atual in modelos:
            self.dropdown_modelo.value = atual
        else:
            self.dropdown_modelo.value = modelos[0] if modelos else DEFAULT_MODEL
        setattr(self.app, self.attr_modelo, self.dropdown_modelo.value)

        self._sincronizar_reasoning()
        if atualizar_page and getattr(self.app, "page", None):
            try:
                self.app.page.update()
            except Exception:
                pass

    def _sincronizar_reasoning(self) -> None:
        modelo = (
            self.dropdown_modelo.value
            or getattr(self.app, self.attr_modelo, None)
            or DEFAULT_MODEL
        )
        niveis = niveis_reasoning_para_modelo(modelo)
        if not niveis:
            self.dropdown_reasoning.options = [
                ft.dropdown.Option("", "N/A")
            ]
            self.dropdown_reasoning.value = ""
            self.dropdown_reasoning.disabled = True
            setattr(self.app, self.attr_reasoning, None)
            return

        self.dropdown_reasoning.disabled = False
        self.dropdown_reasoning.options = [
            ft.dropdown.Option(nivel, LABELS_REASONING.get(nivel, nivel))
            for nivel in niveis
        ]
        preferido = getattr(self.app, self.attr_reasoning, None) or self.reasoning_default
        atual = normalizar_reasoning_effort(modelo, preferido)
        self.dropdown_reasoning.value = atual
        setattr(self.app, self.attr_reasoning, atual)

    def _persistir(self) -> None:
        salvar = getattr(self.app, "salvar_config_persistida", None)
        if callable(salvar):
            try:
                salvar()
            except Exception:
                pass

    def _ao_mudar_modelo(self, e) -> None:
        setattr(
            self.app,
            self.attr_modelo,
            self.dropdown_modelo.value or DEFAULT_MODEL,
        )
        self._sincronizar_reasoning()
        self._persistir()
        if self.on_change:
            self.on_change()
        if getattr(self.app, "page", None):
            self.app.page.update()

    def _ao_mudar_reasoning(self, e) -> None:
        modelo = getattr(self.app, self.attr_modelo, None) or DEFAULT_MODEL
        if not modelo_suporta_reasoning(modelo):
            return
        valor = normalizar_reasoning_effort(
            modelo,
            self.dropdown_reasoning.value,
        ) or self.reasoning_default
        setattr(self.app, self.attr_reasoning, valor)
        self._persistir()
        if self.on_change:
            self.on_change()
