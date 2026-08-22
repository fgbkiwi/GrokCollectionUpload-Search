"""
Aba de Configurações.
"""

import flet as ft
from minuta import KernelSarah, BibliotecaModelos, ModeloTematico
from datetime import datetime


class AbaConfiguracoes:
    """Aba de configurações do sistema."""
    
    def __init__(self, app):
        self.app = app
        self.kernel = KernelSarah()
        self.biblioteca = BibliotecaModelos()
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.campo_api_key = ft.TextField(
            label="API Key xAI",
            password=True,
            can_reveal_password=True,
            width=500,
            on_change=self._atualizar_api_key
        )
        
        self.campo_management_key = ft.TextField(
            label="Management Key xAI",
            password=True,
            can_reveal_password=True,
            width=500,
            on_change=self._atualizar_management_key
        )
        
        self.campo_prompt = ft.TextField(
            label="Prompt de Sistema (Kernel Sarah)",
            multiline=True,
            min_lines=10,
            max_lines=20,
            expand=True,
            value=self.kernel.obter_prompt()
        )
        
        self.btn_salvar_prompt = ft.ElevatedButton(
            "Salvar Prompt",
            icon=ft.icons.SAVE,
            on_click=self._salvar_prompt
        )
        
        self.btn_restaurar_prompt = ft.ElevatedButton(
            "Restaurar Padrão",
            icon=ft.icons.RESTORE,
            on_click=self._restaurar_prompt
        )
        
        self.lista_modelos = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.btn_novo_modelo = ft.ElevatedButton(
            "Novo Modelo Temático",
            icon=ft.icons.ADD,
            on_click=self._novo_modelo
        )
        
        self._carregar_modelos()
        
        tabs_config = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    text="API Keys",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Configure suas chaves de API xAI",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Divider(),
                            self.campo_api_key,
                            self.campo_management_key,
                            ft.Text(
                                "As chaves são armazenadas em memória apenas durante a sessão",
                                size=12,
                                color=ft.colors.GREY_700
                            ),
                        ]),
                        padding=20,
                    )
                ),
                ft.Tab(
                    text="Kernel Sarah",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Prompt de Sistema da Sarah",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Divider(),
                            self.campo_prompt,
                            ft.Row([
                                self.btn_salvar_prompt,
                                self.btn_restaurar_prompt,
                            ]),
                        ]),
                        padding=20,
                        expand=True,
                    )
                ),
                ft.Tab(
                    text="Modelos Temáticos",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Biblioteca de Modelos Temáticos",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Divider(),
                            self.btn_novo_modelo,
                            self.lista_modelos,
                        ]),
                        padding=20,
                        expand=True,
                    )
                ),
            ],
            expand=True,
        )
        
        return ft.Container(
            content=tabs_config,
            expand=True,
        )
    
    def _atualizar_api_key(self, e):
        """Atualiza API Key."""
        self.app.api_key = self.campo_api_key.value
    
    def _atualizar_management_key(self, e):
        """Atualiza Management Key."""
        self.app.management_key = self.campo_management_key.value
    
    def _salvar_prompt(self, e):
        """Salva prompt personalizado."""
        try:
            self.kernel.salvar_prompt(self.campo_prompt.value)
            self.app.mostrar_info("Prompt salvo com sucesso!")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar prompt: {str(ex)}")
    
    def _restaurar_prompt(self, e):
        """Restaura prompt padrão."""
        try:
            self.kernel.restaurar_default()
            self.campo_prompt.value = self.kernel.obter_prompt()
            self.app.page.update()
            self.app.mostrar_info("Prompt restaurado para o padrão")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao restaurar prompt: {str(ex)}")
    
    def _carregar_modelos(self):
        """Carrega lista de modelos temáticos."""
        self.lista_modelos.controls.clear()
        
        modelos = self.biblioteca.listar()
        
        for modelo in modelos:
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(modelo.nome, size=14, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.icons.EDIT,
                                on_click=lambda e, m=modelo: self._editar_modelo(m)
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                on_click=lambda e, m=modelo: self._excluir_modelo(m)
                            ),
                        ]),
                        ft.Text(f"Tema: {modelo.tema}", size=12),
                        ft.Text(
                            modelo.texto[:100] + "...",
                            size=11,
                            color=ft.colors.GREY_700
                        ),
                    ]),
                    padding=15,
                )
            )
            self.lista_modelos.controls.append(card)
        
        self.app.page.update()
    
    def _novo_modelo(self, e):
        """Cria novo modelo temático."""
        self.app.mostrar_info("Funcionalidade de criação de modelo em desenvolvimento")
    
    def _editar_modelo(self, modelo: ModeloTematico):
        """Edita modelo temático."""
        self.app.mostrar_info(f"Editar modelo: {modelo.nome}")
    
    def _excluir_modelo(self, modelo: ModeloTematico):
        """Exclui modelo temático."""
        try:
            self.biblioteca.excluir(modelo.id)
            self._carregar_modelos()
            self.app.mostrar_info(f"Modelo '{modelo.nome}' excluído")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao excluir modelo: {str(ex)}")
