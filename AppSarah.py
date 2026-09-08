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
from typing import Optional

from aba_indexador import AbaIndexador
from aba_cartao import AbaCartao
from aba_dossie import AbaDossie
from aba_minuta import AbaMinuta
from aba_configuracoes import AbaConfiguracoes


class AppSarah:
    """Aplicação principal Sarah."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Sarah - Sistema de Assistência Judicial"
        self.page.window_width = 1600
        self.page.window_height = 1000
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.api_key = ""
        self.management_key = ""
        
        self.aba_indexador = AbaIndexador(self)
        self.aba_cartao = AbaCartao(self)
        self.aba_dossie = AbaDossie(self)
        self.aba_minuta = AbaMinuta(self)
        self.aba_config = AbaConfiguracoes(self)
        
        self._construir_ui()
    
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
                ft.TextButton("OK", on_click=lambda e: self._fechar_dialogo(dlg))
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    def mostrar_info(self, mensagem: str):
        """Mostra diálogo de informação."""
        dlg = ft.AlertDialog(
            title=ft.Text("Informação"),
            content=ft.Text(mensagem),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self._fechar_dialogo(dlg))
            ],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    def _fechar_dialogo(self, dialogo):
        """Fecha diálogo."""
        dialogo.open = False
        self.page.update()


def main(page: ft.Page):
    """Ponto de entrada da aplicação."""
    app = AppSarah(page)


if __name__ == "__main__":
    ft.app(target=main)
