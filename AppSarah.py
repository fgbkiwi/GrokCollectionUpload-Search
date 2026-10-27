#!/usr/bin/env python3
"""
AppSarah - Sistema Unificado de Assistência Judicial

Integra:
- Indexador de Sentenças
- Cartão do Caso
- Dossiê de Prova
- Minuta de Sentença
- Configurações
"""

import flet as ft
from pathlib import Path

from aba_indexador import AbaIndexador
from aba_cartao import AbaCartao
from aba_dossie import AbaDossie
from aba_minuta import AbaMinuta
from aba_configuracoes import AbaConfiguracoes
from xai_models import DEFAULT_MODEL
from ui_modelo_reasoning import FASES


class AppSarah:
    """Aplicação principal Sarah."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Sarah - Sistema de Assistência Judicial"
        self.page.window.width = 1600
        self.page.window.height = 1000
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.api_key = ""
        self.management_key = ""
        # Padrão global (Configurações) + por fase
        self.modelo_grok = DEFAULT_MODEL
        self.reasoning_effort = "high"
        self.modelo_cartao = DEFAULT_MODEL
        self.reasoning_cartao = "medium"
        self.modelo_dossie = DEFAULT_MODEL
        self.reasoning_dossie = "low"
        self.modelo_minuta = DEFAULT_MODEL
        self.reasoning_minuta = "high"
        self.gerar_previa_minuta = False
        self.selected_collection_id = ""
        self._config_path = Path(__file__).resolve().parent / "app_config.json"
        self._carregar_config_persistida()
        
        self.aba_indexador = AbaIndexador(self)
        self.aba_cartao = AbaCartao(self)
        self.aba_dossie = AbaDossie(self)
        self.aba_minuta = AbaMinuta(self)
        self.aba_config = AbaConfiguracoes(self)
        
        self._construir_ui()

    def _carregar_config_persistida(self):
        """Carrega chaves/modelo de app_config.json, se existir."""
        if not self._config_path.exists():
            return
        try:
            import json
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            self.api_key = data.get("api_key") or self.api_key
            self.management_key = data.get("management_key") or self.management_key
            self.modelo_grok = data.get("model") or self.modelo_grok
            self.reasoning_effort = data.get("reasoning_effort") or self.reasoning_effort
            self.selected_collection_id = data.get("selected_collection_id") or ""
            self.gerar_previa_minuta = bool(data.get("gerar_previa_minuta", False))

            # Migração: se só houver chaves legadas, copiar para as três fases
            tem_por_fase = any(
                data.get(f"model_{fase}") or data.get(f"reasoning_{fase}")
                for fase in FASES
            )
            for fase, (attr_m, attr_r, default_r) in FASES.items():
                modelo_fase = data.get(f"model_{fase}")
                reasoning_fase = data.get(f"reasoning_{fase}")
                if not tem_por_fase:
                    modelo_fase = modelo_fase or self.modelo_grok
                    reasoning_fase = reasoning_fase or default_r
                setattr(self, attr_m, modelo_fase or DEFAULT_MODEL)
                setattr(self, attr_r, reasoning_fase or default_r)
        except Exception:
            pass

    def aplicar_padrao_global_as_fases(self):
        """Copia modelo/reasoning globais para Cartão, Dossiê e Minuta."""
        modelo = self.modelo_grok or DEFAULT_MODEL
        reasoning = self.reasoning_effort or "high"
        for attr_m, attr_r, _default_r in FASES.values():
            setattr(self, attr_m, modelo)
            setattr(self, attr_r, reasoning)
        self.salvar_config_persistida()
        # Atualiza dropdowns das abas, se já construídos
        for aba_nome in ("aba_cartao", "aba_dossie", "aba_minuta"):
            aba = getattr(self, aba_nome, None)
            seletor = getattr(aba, "seletor_modelo", None) if aba else None
            if seletor is not None:
                seletor.sincronizar(atualizar_page=False)
        if getattr(self, "page", None):
            try:
                self.page.update()
            except Exception:
                pass

    def salvar_config_persistida(self):
        """Persiste chaves/modelo/reasoning em app_config.json (merge)."""
        import json
        data = {}
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["api_key"] = self.api_key or data.get("api_key", "")
        data["management_key"] = self.management_key or data.get("management_key", "")
        data["model"] = self.modelo_grok or data.get("model", DEFAULT_MODEL)
        data["reasoning_effort"] = self.reasoning_effort or data.get(
            "reasoning_effort", "high"
        )
        for fase, (attr_m, attr_r, default_r) in FASES.items():
            data[f"model_{fase}"] = getattr(self, attr_m, None) or DEFAULT_MODEL
            data[f"reasoning_{fase}"] = getattr(self, attr_r, None) or default_r
        data["gerar_previa_minuta"] = bool(self.gerar_previa_minuta)
        if self.selected_collection_id:
            data["selected_collection_id"] = self.selected_collection_id
        self._config_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    
    def _construir_ui(self):
        """Constrói a interface principal."""
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Cartão do Caso",
                    icon=ft.Icons.DESCRIPTION,
                    content=self.aba_cartao.construir()
                ),
                ft.Tab(
                    text="Dossiê de Prova",
                    icon=ft.Icons.FOLDER_COPY,
                    content=self.aba_dossie.construir()
                ),
                ft.Tab(
                    text="Minuta",
                    icon=ft.Icons.EDIT_DOCUMENT,
                    content=self.aba_minuta.construir()
                ),
                ft.Tab(
                    text="Indexador",
                    icon=ft.Icons.UPLOAD_FILE,
                    content=self.aba_indexador.construir()
                ),
                ft.Tab(
                    text="Configurações",
                    icon=ft.Icons.SETTINGS,
                    content=self.aba_config.construir()
                ),
            ],
        )
        
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.GAVEL, size=32, color=ft.Colors.BLUE_700),
                    ft.Text(
                        "Sarah - Sistema de Assistência Judicial",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_700
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=20,
            bgcolor=ft.Colors.BLUE_50,
        )
        
        self.page.add(
            ft.Column(
                [
                    header,
                    ft.Divider(height=1),
                    self.tabs,
                ],
                expand=True,
                spacing=0,
            )
        )
    
    def mostrar_erro(self, mensagem: str):
        """Mostra diálogo de erro."""
        dlg = ft.AlertDialog(
            title=ft.Text("Erro"),
            content=ft.Text(mensagem),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.page.close(dlg))
            ],
        )
        self.page.open(dlg)
    
    def mostrar_info(self, mensagem: str):
        """Mostra diálogo de informação."""
        dlg = ft.AlertDialog(
            title=ft.Text("Informação"),
            content=ft.Text(mensagem),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.page.close(dlg))
            ],
        )
        self.page.open(dlg)


def main(page: ft.Page):
    """Ponto de entrada da aplicação."""
    AppSarah(page)


if __name__ == "__main__":
    ft.app(target=main)
