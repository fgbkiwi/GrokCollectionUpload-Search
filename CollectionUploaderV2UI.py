#!/usr/bin/env python3
"""
CollectionUploaderV2UI.py - VERSÃO CORRIGIDA COM MELHORIAS
Interface gráfica Flet para o CollectionUploader.py
Permite processar JSONs para MD e fazer upload para xAI Collections

Melhorias implementadas:
1. FilePicker corrigido usando tkinter.filedialog
2. Armazenamento persistente de chaves API
3. Seleção dinâmica de collections
4. Seleção dinâmica de modelos
"""

import flet as ft
import json
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, cast
from datetime import datetime
import requests
import tkinter as tk
import unicodedata
from tkinter import filedialog


class CollectionUploaderV2UI:
    """Interface gráfica para processamento e upload de sentenças."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Collection Uploader V2 - xAI (Upload Direto)"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        
        # Configurar janela (versão Flet 0.80+)
        try:
            self.page.window.width = 1000
            self.page.window.height = 800
        except:
            pass  # Fallback se window não estiver disponível
        
        # Estado da aplicação
        self.selected_json_files: List[str] = []
        self.output_directory: str = ""
        self.management_key: str = ""
        self.api_key: str = ""
        self.selected_model: str = ""
        self.selected_collection_id: str = ""
        self.collections_list: List[Dict] = []
        self.generated_md_files: List[str] = []
        
        # Modelos disponíveis (populado via refresh na API)
        self.available_models: List[str] = []
        
        # Estatísticas
        self.stats = {
            "total_processed": 0,
            "chunks_created": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }
        
        # Configuração
        self.config_file = "config.json"
        
        # Inicializar feedback_text antes de carregar config
        self.feedback_text = None
        
        # Estado do tema (dark mode)
        self.dark_mode = False
        
        # Tkinter root para file dialogs (criado e mantido oculto)
        self.tk_root = None
        
        self.build_ui()

        # Limpa log logo apos construir a UI
        self.clear_log()
        
        # Carregar configuração salva (após UI construída)
        self.load_config()

        # Atualiza models/collections no startup como se o usuario clicasse nos botoes
        self.schedule_startup_refresh()

    def schedule_startup_refresh(self):
        """Agenda o refresh inicial de collections e modelos."""
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(self.refresh_on_startup)
            else:
                asyncio.create_task(self.refresh_on_startup())
        except Exception:
            # Evita falhas de inicializacao se o loop nao estiver pronto
            pass

    async def refresh_on_startup(self):
        """Atualiza collections e modelos no startup."""
        self.clear_log()
        if self.management_key:
            await self.load_collections(None)
            self.update_collections_dropdown()

        if self.api_key:
            await self.fetch_models()
            self.update_models_dropdown()

        self.page.update()
    
    def load_config(self):
        """Carrega configuração salva do arquivo config.json."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # Preenche campos com valores salvos
                    self.management_key = config.get("management_key", "")
                    self.api_key = config.get("api_key", "")
                    self.selected_model = config.get("selected_model", "")
                    # Collection selecionada anteriormente (se houver)
                    self.selected_collection_id = config.get("selected_collection_id", "")

                self.log("✅ Configuração carregada do arquivo config.json")

                # Atualiza estado inicial dos botões baseado na config carregada
                self.check_generate_button_state()
                self.check_upload_button_state()
            else:
                self.log("ℹ️ Arquivo de configuração não encontrado. Usando padrões.")
        except Exception as e:
            self.log(f"⚠️ Erro ao carregar configuração: {str(e)}")

    def save_config(self):
        """Salva configuração atual no arquivo config.json."""
        try:
            config = {
                "management_key": self.management_key,
                "api_key": self.api_key,
                "selected_model": self.selected_model,
                "selected_collection_id": self.selected_collection_id,
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log("💾 Configuração salva no arquivo config.json")
        except Exception as e:
            self.log(f"⚠️ Erro ao salvar configuração: {str(e)}")
    
    def build_ui(self):
        """Constrói a interface do usuário."""
        
        # Título com ícone de configuração
        title_text = ft.Text()
        title_text.value = "Collection Uploader V2 - xAI (Upload Direto)"
        title_text.size = 28
        title_text.weight = ft.FontWeight.BOLD
        title_text.color = "#1976D2"
        title_text.expand = True

        settings_button = ft.IconButton()
        settings_button.icon = ft.Icons.SETTINGS
        settings_button.icon_size = 30
        settings_button.icon_color = "#1976D2"
        settings_button.tooltip = "Configurações"
        settings_button.on_click = self.open_config_dialog

        title_row = ft.Row(
            controls=[title_text, settings_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Seção de Seleção de Arquivos (renomeada)
        files_section = self.create_files_section()
        
        # Seção de Ações
        actions_section = self.create_actions_section()
        
        # Janela de Feedback
        # Define cores baseado no modo inicial (light)
        if self.dark_mode:
            feedback_bgcolor = "#1e1e1e"
            feedback_color = "#ffffff"
        else:
            feedback_bgcolor = "#f5f5f5"
            feedback_color = "#000000"

        self.feedback_text = ft.TextField()
        self.feedback_text.label = "Log de Execução"
        self.feedback_text.multiline = True
        self.feedback_text.read_only = True
        self.feedback_text.min_lines = 10
        self.feedback_text.max_lines = 15
        self.feedback_text.bgcolor = feedback_bgcolor
        self.feedback_text.color = feedback_color
        self.feedback_text.border_color = "#42A5F5"
        self.feedback_text.expand = True
        self.feedback_text.width = 960  # Fixed width to avoid None arithmetic
        
        # Layout principal
        self.page.add(
            ft.Column([
                title_row,
                ft.Divider(height=20),
                files_section,
                ft.Divider(height=20),
                actions_section,
                ft.Divider(height=20),
                ft.Container(
                    content=self.feedback_text,
                    border=ft.Border.all(1, "#42A5F5"),
                    border_radius=10,
                    padding=10
                )
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        )
        
        # Criar diálogo de configuração (inicialmente oculto)
        self.create_config_dialog()
    
    def create_config_dialog(self):
        """Cria o diálogo de configuração."""
        # Campos para o diálogo
        self.dialog_management_key_field = ft.TextField()
        self.dialog_management_key_field.label = "Management Key (xAI Collection)"
        self.dialog_management_key_field.hint_text = "Chave de gerenciamento da Collection"
        self.dialog_management_key_field.password = True
        self.dialog_management_key_field.can_reveal_password = True
        self.dialog_management_key_field.width = 450
        self.dialog_management_key_field.value = self.management_key
        self.dialog_management_key_field.on_change = self.on_dialog_management_key_change  # type: ignore[attr-defined]
        
        self.dialog_api_key_field = ft.TextField()
        self.dialog_api_key_field.label = "API Key (Grok)"
        self.dialog_api_key_field.hint_text = "Chave de API do Grok para geração de keywords"
        self.dialog_api_key_field.password = True
        self.dialog_api_key_field.can_reveal_password = True
        self.dialog_api_key_field.width = 450
        self.dialog_api_key_field.value = self.api_key
        self.dialog_api_key_field.on_change = self.on_dialog_api_key_change  # type: ignore[attr-defined]
        
        # Dropdown de Modelo no diálogo
        self.dialog_model_dropdown = ft.Dropdown()
        self.dialog_model_dropdown.label = "Modelo para Geração de Keywords"
        self.dialog_model_dropdown.options = [ft.dropdown.Option(model) for model in self.available_models]
        self.dialog_model_dropdown.value = self.selected_model
        self.dialog_model_dropdown.width = 300
        self.dialog_model_dropdown.on_change = self.on_dialog_model_change  # type: ignore[attr-defined]
        
        # Botão para atualizar modelos no diálogo
        self.dialog_refresh_models_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.REFRESH), ft.Text(value="Atualizar Modelos")]),
                tight=True
            ),
            on_click=self.dialog_refresh_models_click,
            disabled=len(self.api_key) == 0
        )
        
        # Dropdown de Collections no diálogo (on_select garante que a seleção seja salva ao escolher)
        self.dialog_collections_dropdown = ft.Dropdown()
        self.dialog_collections_dropdown.label = "Collection para Upload"
        self.dialog_collections_dropdown.options = []
        self.dialog_collections_dropdown.on_change = self.on_dialog_collection_change  # type: ignore[attr-defined]
        self.dialog_collections_dropdown.on_blur = self.on_dialog_collection_change  # type: ignore[attr-defined]
        self.dialog_collections_dropdown.disabled = True
        self.dialog_collections_dropdown.width = 450
        
        # Botão para carregar Collections no diálogo
        self.dialog_load_collections_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.REFRESH), ft.Text(value="Carregar Collections")]),
                tight=True
            ),
            on_click=self.dialog_load_collections_click,
            disabled=len(self.management_key) == 0
        )
        
        # Toggle para Dark Mode
        self.dark_mode_toggle = ft.Switch()
        self.dark_mode_toggle.label = "Dark Mode"
        self.dark_mode_toggle.value = self.dark_mode
        self.dark_mode_toggle.on_change = self.on_dark_mode_toggle  # type: ignore[attr-defined]
        
        # Botão de fechar
        close_button = ft.Button(
            content=ft.Text("Fechar"),
            on_click=self.close_config_dialog
        )
        
        # Conteúdo do diálogo
        dialog_content = ft.Column([
            ft.Text("⚙️ Configurações", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10),
            ft.Text("Credenciais API", size=16, weight=ft.FontWeight.BOLD),
            self.dialog_management_key_field,
            ft.Row([self.dialog_load_collections_btn], spacing=10),
            self.dialog_collections_dropdown,
            ft.Divider(height=10),
            self.dialog_api_key_field,
            ft.Row([self.dialog_model_dropdown, self.dialog_refresh_models_btn], spacing=10),
            ft.Divider(height=10),
            ft.Text("Aparência", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.dark_mode_toggle], spacing=10)
        ], spacing=15, width=600)

        self.config_dialog = ft.AlertDialog()
        self.config_dialog.modal = False
        self.config_dialog.title = ft.Text("Configurações")
        self.config_dialog.content = dialog_content
        self.config_dialog.actions = [close_button]
    
    def open_config_dialog(self, e):
        """Abre o diálogo de configuração."""
        # Atualiza valores dos campos do diálogo
        self.dialog_management_key_field.value = self.management_key
        self.dialog_api_key_field.value = self.api_key
        self.update_models_dropdown()
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.dialog_refresh_models_btn.disabled = len(self.api_key) == 0

        # Atualiza dropdown de collections conforme estado atual
        self.update_collections_dropdown()
        
        # Adiciona diálogo ao overlay apenas se não estiver já presente
        if self.config_dialog not in self.page.overlay:
            self.page.overlay.append(self.config_dialog)
        self.config_dialog.open = True
        self.page.update()
    
    def close_config_dialog(self, e):
        """Fecha o diálogo de configuração."""
        self.log("🗂️ Fechando diálogo de configuração...")
        # Sincroniza a collection selecionada no dropdown para o estado da aplicação
        # (evita que a seleção se perca se o usuário fechar sem tirar o foco do dropdown)
        self.selected_collection_id = str(self.dialog_collections_dropdown.value or "")
        if self.selected_collection_id:
            self.log(f"   Collection selecionada: {self.selected_collection_id}")
        # Garante que a seleção de collection seja persistida ao fechar
        self.save_config()
        self.check_upload_button_state()
        self.config_dialog.open = False
        self.page.update()
    
    def on_dialog_management_key_change(self, e):
        """Callback quando Management Key muda no diálogo."""
        self.management_key = str(e.control.value or "")
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.save_config()
        self.page.update()
    
    def on_dialog_api_key_change(self, e):
        """Callback quando API Key muda no diálogo."""
        self.api_key = str(e.control.value or "")
        self.dialog_refresh_models_btn.disabled = len(self.api_key) == 0
        self.save_config()
        self.page.update()
    
    def on_dialog_model_change(self, e):
        """Callback quando modelo muda no diálogo."""
        self.selected_model = str(e.control.value or "")
        self.save_config()
    
    def on_dialog_collection_change(self, e):
        """Callback quando collection muda no diálogo."""
        self.selected_collection_id = str(e.control.value or "")
        # Persiste imediatamente a collection escolhida
        self.save_config()
        self.check_upload_button_state()
    
    def on_dark_mode_toggle(self, e):
        """Alterna entre light/dark mode."""
        self.dark_mode = e.control.value
        if self.dark_mode:
            self.page.theme_mode = ft.ThemeMode.DARK
            # Atualiza cores do feedback_text para dark mode
            if self.feedback_text:
                self.feedback_text.bgcolor = "#1e1e1e"
                self.feedback_text.color = "#ffffff"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            # Atualiza cores do feedback_text para light mode
            if self.feedback_text:
                self.feedback_text.bgcolor = "#f5f5f5"
                self.feedback_text.color = "#000000"
        self.page.update()
    
    def dialog_refresh_models_click(self, e):
        """Callback para botão de atualizar modelos no diálogo."""
        self.log("🖱️ Clique em 'Atualizar Modelos' recebido...")
        self.run_task(self._dialog_refresh_models)

    async def _dialog_refresh_models(self):
        await self.fetch_models()
        # Atualiza dropdown no diálogo após buscar modelos
        if hasattr(self, 'dialog_model_dropdown'):
            self.update_models_dropdown()
            self.page.update()
    
    def dialog_load_collections_click(self, e):
        """Callback para botão de carregar collections no diálogo."""
        self.log("🔄 Iniciando carregamento de collections via diálogo...")
        self.run_task(self._dialog_load_collections, e)

    async def _dialog_load_collections(self, e):
        await self.load_collections(e)
        # Atualiza dropdown no diálogo após carregar collections
        self.log(f"📋 Verificando collections_list: {len(self.collections_list) if self.collections_list else 0} itens")
        try:
            self.update_collections_dropdown()
            self.page.update()
        except Exception as ex:
            self.log(f"❌ Erro ao atualizar dropdown: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
    

    
    def create_files_section(self) -> ft.Container:
        """Cria a seção de seleção de arquivos e pasta de saída."""
        
        # Botão para selecionar JSON
        self.json_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.INSERT_DRIVE_FILE), ft.Text(value="Selecionar Arquivos JSON")]),
                tight=True
            ),
            on_click=self.pick_json_files,
            width=250
        )
        
        # Lista de arquivos selecionados
        self.json_files_list = ft.Text(
            "Nenhum arquivo selecionado",
            size=12,
            color="#616161"
        )
        
        # Botão para selecionar pasta de saída
        self.folder_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.FOLDER_OPEN), ft.Text(value="Selecionar Pasta de Saída")]),
                tight=True
            ),
            on_click=self.pick_output_folder,
            width=250
        )
        
        # Pasta de saída selecionada
        self.output_folder_text = ft.Text(
            "Nenhuma pasta selecionada",
            size=12,
            color="#616161"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 Seleção de Arquivos e Pasta de Saída", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([self.json_picker_btn, self.folder_picker_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10),
                self.json_files_list,
                self.output_folder_text,
            ], spacing=15),
            padding=20,
            border=ft.Border.all(1, "#A5D6A7"),
            border_radius=10
        )
    
    def create_actions_section(self) -> ft.Container:
        """Cria a seção de ações."""
        
        # Botão para gerar MDs
        self.generate_md_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.CREATE_NEW_FOLDER), ft.Text(value="Gerar Arquivos MD")]),
                tight=True
            ),
            on_click=self.generate_md_files_click,
            disabled=True,
            bgcolor="#1976D2",
            color="#FFFFFF"
        )
        
        # Botão para fazer upload
        self.upload_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.CLOUD_UPLOAD), ft.Text(value="Upload para Collection")]),
                tight=True
            ),
            on_click=self.upload_to_collection_click,
            disabled=True,
            bgcolor="#388E3C",
            color="#FFFFFF"
        )
        
        # Progress bar
        self.progress_bar = ft.ProgressBar(
            width=800,
            visible=False
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🚀 Ações", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.generate_md_btn,
                    self.upload_btn
                ], spacing=20),
                self.progress_bar
            ], spacing=15),
            padding=20,
            border=ft.Border.all(1, "#FFCC80"),
            border_radius=10
        )
    
    # Callbacks
    
    async def pick_json_files(self, e):
        """Abre file picker para selecionar arquivos JSON."""
        # Criar janela tkinter temporária e trazer para frente
        def open_file_dialog():
            root = tk.Tk()
            root.withdraw()  # Esconder janela principal
            root.attributes('-topmost', True)  # Trazer para frente
            root.lift()
            root.focus_force()
            files = filedialog.askopenfilenames(
                parent=root,
                title="Selecione os arquivos JSON",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            root.destroy()
            return files
        
        # Usar tkinter filedialog em thread separada para não bloquear
        files = await asyncio.to_thread(open_file_dialog)

        if files:
            self.selected_json_files = list(files)
            files_text = "\n".join([f"• {os.path.basename(path)}" for path in files])
            self.json_files_list.value = f"Arquivos selecionados:\n{files_text}"
            self.json_files_list.color = "#388E3C"
            self.check_generate_button_state()
        else:
            self.selected_json_files = []
            self.json_files_list.value = "Nenhum arquivo selecionado"
            self.json_files_list.color = "#616161"
        
        self.page.update()
    
    def on_json_files_selected(self, e: Any):
        """Callback quando arquivos JSON são selecionados."""
        if hasattr(e, "files") and e.files:
            self.selected_json_files = [str(f.path) for f in e.files if f.path]
            files_text = "\n".join([f"• {os.path.basename(path)}" for path in self.selected_json_files])
            self.json_files_list.value = f"Arquivos selecionados:\n{files_text}"
            self.json_files_list.color = "#388E3C"
            self.check_generate_button_state()
        else:
            self.selected_json_files = []
            self.json_files_list.value = "Nenhum arquivo selecionado"
            self.json_files_list.color = "#616161"
        
        self.page.update()
    
    async def pick_output_folder(self, e):
        """Abre folder picker para selecionar pasta de saída."""
        # Criar janela tkinter temporária e trazer para frente
        def open_folder_dialog():
            root = tk.Tk()
            root.withdraw()  # Esconder janela principal
            root.attributes('-topmost', True)  # Trazer para frente
            root.lift()
            root.focus_force()
            path = filedialog.askdirectory(
                parent=root,
                title="Selecione a pasta de saída"
            )
            root.destroy()
            return path
        
        # Usar tkinter filedialog em thread separada para não bloquear
        path = await asyncio.to_thread(open_folder_dialog)

        if path:
            self.output_directory = str(path)
            self.output_folder_text.value = f"Pasta: {self.output_directory}"
            self.output_folder_text.color = "#388E3C"
            self.check_generate_button_state()
            self.check_upload_button_state()
        else:
            self.output_directory = ""
            self.output_folder_text.value = "Nenhuma pasta selecionada"
            self.output_folder_text.color = "#616161"
        
        self.page.update()
    
    def on_output_folder_selected(self, e: Any):
        """Callback quando pasta de saída é selecionada."""
        if hasattr(e, "path") and e.path:
            self.output_directory = str(e.path)
            self.output_folder_text.value = f"Pasta: {self.output_directory}"
            self.output_folder_text.color = "#388E3C"
            self.check_generate_button_state()
            self.check_upload_button_state()
        else:
            self.output_directory = ""
            self.output_folder_text.value = "Nenhuma pasta selecionada"
            self.output_folder_text.color = "#616161"
        
        self.page.update()
    
    def check_generate_button_state(self):
        """Verifica se o botão de gerar MD pode ser habilitado."""
        can_generate = (
            len(self.selected_json_files) > 0 and
            len(self.output_directory) > 0 and
            len(self.api_key) > 0
        )
        self.generate_md_btn.disabled = not can_generate
        self.page.update()
    
    def check_upload_button_state(self):
        """Verifica se o botão de upload pode ser habilitado."""
        has_md_files = False
        if self.output_directory:
            try:
                output_path = Path(self.output_directory)
                has_md_files = output_path.exists() and any(output_path.glob("*.md"))
            except Exception:
                has_md_files = False

        can_upload = (
            (len(self.generated_md_files) > 0 or has_md_files) and
            len(self.selected_collection_id) > 0 and
            len(self.management_key) > 0
        )
        # Log de debug para entender por que o botão está (des)habilitado
        try:
            self.log(
                f"🔍 check_upload_button_state -> can_upload={can_upload} | "
                f"generated_md_files={len(self.generated_md_files)} | "
                f"selected_collection_id='{self.selected_collection_id}' | "
                f"management_key_set={bool(self.management_key)}"
            )
        except Exception:
            # Não queremos que um erro de log quebre a UI
            pass
        self.upload_btn.disabled = not can_upload
        self.page.update()
    
    def log(self, message: str):
        """Adiciona mensagem ao log de feedback."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        if self.feedback_text:
            self.feedback_text.value += log_entry
            self.page.update()

    def run_task(self, async_fn, *args):
        """Executa uma coroutine sem bloquear a UI."""
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(async_fn, *args)
            else:
                asyncio.create_task(async_fn(*args))
        except Exception:
            pass

    def clear_log(self):
        """Limpa o log de execucao."""
        if self.feedback_text:
            self.feedback_text.value = ""
            self.page.update()
    
    def load_collections_click(self, e):
        """Ponte para chamada async."""
        # Feedback imediato ao clicar no botão
        self.log("🖱️ Clique em 'Carregar Collections' recebido...")
        self.run_task(self.load_collections, e)

    def generate_md_files_click(self, e):
        """Ponte para chamada async."""
        # Feedback imediato ao clicar no botão
        self.log("🖱️ Clique em 'Gerar Arquivos MD' recebido...")
        self.run_task(self.generate_md_files, e)

    def upload_to_collection_click(self, e):
        """Ponte para chamada async."""
        # Feedback imediato ao clicar no botão
        self.log("🖱️ Clique em 'Upload para Collection' recebido...")
        self.run_task(self.upload_to_collection, e)

    async def load_collections(self, e):
        """Carrega lista de collections disponíveis."""
        self.log("🔄 Carregando collections disponíveis...")
        
        if not self.management_key:
            self.log("⚠️ Management Key não configurada. Configure a Management Key para carregar collections.")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}",
                "Content-Type": "application/json"
            }
            
            # Tenta primeiro o endpoint da API de gerenciamento
            urls_to_try = [
                "https://management-api.x.ai/v1/collections",
                "https://api.x.ai/v1/collections",
                "https://management-api.x.ai/v1/collections/list",
                "https://api.x.ai/collections",
                "https://management-api.x.ai/collections",
                "https://api.x.ai/v1/collections/list",
                "https://management-api.x.ai/collections/list"
            ]
            
            response = None
            last_error = None
            
            for url in urls_to_try:
                try:
                    self.log(f"   Tentando endpoint: {url}")
                    use_headers = True if "management-api" in url else False
                    response = requests.get(url, headers=headers if use_headers else {}, timeout=15)
                    self.log(f"   Status: {response.status_code} (with headers: {use_headers})")

                    if response.status_code == 200:
                        data = response.json()
                        self.log(f"   Resposta recebida: tipo={type(data)}, chaves={list(data.keys()) if isinstance(data, dict) else 'não dict'}")

                        # Tenta diferentes formatos de resposta
                        collections = []
                        if isinstance(data, list):
                            collections = data
                            self.log(f"   Dados são uma lista com {len(collections)} itens")
                        elif "data" in data and isinstance(data["data"], list):
                            collections = data["data"]
                            self.log(f"   Dados em 'data': lista com {len(collections)} itens")
                        elif "collections" in data and isinstance(data["collections"], list):
                            collections = data["collections"]
                            self.log(f"   Dados em 'collections': lista com {len(collections)} itens")
                        else:
                            self.log(f"   Formato de resposta não reconhecido: {data}")

                        if collections:
                            self.collections_list = collections
                            self.log(f"✅ {len(self.collections_list)} collection(s) encontrada(s)")
                            # Log primeiras collections para debug
                            for i, col in enumerate(collections[:3]):
                                self.log(f"   Collection {i+1}: {col}")
                                if isinstance(col, dict):
                                    self.log(f"     Keys: {list(col.keys())}")
                            self.page.update()
                            return
                
                except Exception as ex:
                    last_error = str(ex)
                    continue
            
            # Se chegou aqui, nenhum endpoint funcionou
            if response:
                self.log(f"❌ Erro ao carregar collections: {response.status_code}")
                self.log(f"   {response.text[:200]}...")
            else:
                self.log(f"❌ Erro ao carregar collections: {last_error or 'Nenhum endpoint funcionou'}")
            

        
        except Exception as ex:
            self.log(f"❌ Erro ao carregar collections: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
        
        self.page.update()

    async def fetch_models(self):
        """Busca modelos disponíveis da API xAI."""
        if not self.api_key:
            self.log("⚠️ API Key não configurada. Configure a API Key para carregar modelos.")
            return
            
        self.log("🔄 Buscando modelos disponíveis...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.x.ai/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                
                # Extrai IDs dos modelos
                self.available_models = [model.get("id") for model in models if model.get("id")]
                

                
                if self.available_models:
                    if not self.selected_model or self.selected_model not in self.available_models:
                        self.selected_model = self.available_models[0]
                        self.save_config()
                self.log(f"✅ {len(self.available_models)} modelo(s) encontrado(s)")
            else:
                self.log(f"❌ Erro ao buscar modelos: {response.status_code}")
                self.log(f"   {response.text}")
                self.available_models = []
                
        except Exception as ex:
            self.log(f"❌ Erro ao buscar modelos: {str(ex)}")
            self.available_models = []

    def update_models_dropdown(self):
        """Sincroniza dropdown de modelos com a lista atual."""
        if not hasattr(self, "dialog_model_dropdown"):
            return

        model_options = list(self.available_models)
        if not model_options:
            self.dialog_model_dropdown.options = []
            self.dialog_model_dropdown.value = ""
            return

        if model_options and self.selected_model and self.selected_model not in model_options:
            self.selected_model = ""

        self.dialog_model_dropdown.options = [
            ft.dropdown.Option(model_id) for model_id in model_options
        ]

        if not self.selected_model and model_options:
            self.selected_model = model_options[0]

        self.dialog_model_dropdown.value = self.selected_model

    def update_collections_dropdown(self):
        """Sincroniza dropdown de collections com a lista atual."""
        if not hasattr(self, "dialog_collections_dropdown"):
            return

        options = []
        if self.collections_list:
            options = [
                ft.dropdown.Option(
                    key=str(col.get("collection_id", "")),
                    text=str(col.get("collection_name", col.get("collection_id", "")))
                )
                for col in self.collections_list
            ]

        self.dialog_collections_dropdown.options = options
        self.dialog_collections_dropdown.disabled = len(options) == 0

        if options and self.selected_collection_id:
            keys = {str(opt.key) for opt in options if opt.key is not None}
            if self.selected_collection_id in keys:
                self.dialog_collections_dropdown.value = self.selected_collection_id
            else:
                self.dialog_collections_dropdown.value = ""
        elif not options:
            self.dialog_collections_dropdown.value = ""
        


    async def refresh_models_click(self, e):
        """Callback para botão de atualizar modelos."""
        await self.fetch_models()

    async def generate_md_files(self, e):
        """Gera arquivos MD a partir dos JSONs selecionados."""
        if not self.selected_model:
            self.log("⚠️ Nenhum modelo selecionado. Abra as Configurações e escolha um modelo para geração de keywords.")
            return
        self.log("=" * 70)
        self.log("🚀 Iniciando geração de arquivos MD...")
        
        self.progress_bar.visible = True
        self.generate_md_btn.disabled = True
        self.page.update()
        
        try:
            # Reset estatísticas
            self.stats = {
                "total_processed": 0,
                "chunks_created": 0,
                "categorias": set(),
                "tipos_acao": set(),
            }
            self.generated_md_files = []
            
            # Cria diretório de saída
            output_path = Path(self.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Processa cada arquivo JSON
            for json_file in self.selected_json_files:
                self.log(f"\n📄 Processando: {os.path.basename(json_file)}")
                
                # Carrega JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.log(f"   {len(data)} sentença(s) encontrada(s)")
                
                # Processa cada sentença
                for idx, item in enumerate(data, start=1):
                    await self.process_sentenca(item, idx, output_path)
                    
                    if idx % 5 == 0:
                        self.log(f"   ⏳ Processadas: {idx}/{len(data)}")
                        await asyncio.sleep(0.1)  # Permite atualização da UI
            
            self.log("\n✅ Geração de arquivos MD concluída!")
            self.print_statistics()
            
            # Habilita botão de upload
            self.check_upload_button_state()
            
        except Exception as ex:
            self.log(f"\n❌ Erro durante geração: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.progress_bar.visible = False
            self.generate_md_btn.disabled = False
            self.page.update()
    
    async def process_sentenca(self, item: Dict[str, Any], index: int, output_path: Path):
        """Processa uma sentença individual."""
        conteudo = str(item['conteudo']).strip()
        
        # Extrai keywords usando Grok
        keywords = await self.extract_keywords_with_grok(conteudo, str(item['categoria']))
        
        # Atualiza estatísticas
        self.stats['categorias'].add(item['categoria'])
        self.stats['tipos_acao'].add(item['tipo_acao'])
        
        # Divide em chunks
        chunks = self.chunk_text(conteudo)
        
        for chunk_idx, chunk in enumerate(chunks):
            # Cria nome de arquivo
            categoria_safe = self.sanitize_filename(str(item['categoria']))
            processo_safe = str(item['numero_processo']).replace('.', '_').replace('-', '_')
            
            if len(chunks) > 1:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx+1:02d}.md"
            else:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}.md"
            
            filepath = output_path / filename
            
            # Cria metadados
            metadata = self.create_metadata_header(item, keywords)
            
            # Adiciona indicador de chunk
            if len(chunks) > 1:
                chunk_info = f"\n**[Parte {chunk_idx+1} de {len(chunks)}]**\n\n"
            else:
                chunk_info = ""
            
            # Escreve arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(metadata)
                f.write(f"# {item['categoria']}\n\n")
                if chunk_info:
                    f.write(chunk_info)
                f.write(chunk)
            
            self.generated_md_files.append(str(filepath))
            self.stats['chunks_created'] += 1
        
        self.stats['total_processed'] += 1
    
    async def extract_keywords_with_grok(self, conteudo: str, categoria: str) -> List[str]:
        """Extrai keywords usando o modelo Grok."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Analise o seguinte texto jurídico trabalhista e extraia até 10 palavras-chave relevantes.
Foque em termos jurídicos, conceitos trabalhistas, leis citadas (CLT, Súmulas), e temas principais.

Categoria: {categoria}

Texto:
{conteudo[:1500]}

Retorne APENAS as palavras-chave separadas por vírgula, em minúsculas, usando underscore para espaços.
Exemplo: horas_extras, clt, adicional_noturno, art_71, sumula_437"""
            
            payload = {
                "model": self.selected_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                keywords_text = str(data["choices"][0]["message"]["content"]).strip()
                keywords = [k.strip() for k in keywords_text.split(",")]
                return keywords[:10]
            else:
                # Fallback para keywords básicas
                return [categoria.lower().replace(" ", "_"), "clt", "trabalhista"]
        
        except Exception as ex:
            self.log(f"⚠️ Erro ao gerar keywords com Grok: {str(ex)}")
            return [categoria.lower().replace(" ", "_"), "clt", "trabalhista"]
    
    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        """Divide texto em chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def sanitize_filename(self, text: str) -> str:
        """Sanitiza nome de arquivo."""
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\s\-—]+', '_', text)
        return text[:100]

    def to_ascii_filename(self, text: str) -> str:
        """Converte nome de arquivo para ASCII seguro."""
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return self.sanitize_filename(ascii_text) or "document.md"
    
    def create_metadata_header(self, item: Dict[str, Any], keywords: List[str]) -> str:
        """Cria cabeçalho de metadados."""
        metadata_lines = [
            "---",
            f"categoria: {item['categoria']}",
            f"reclamada: {item['reclamada'] if item['reclamada'] else 'Não especificada'}",
            f"numero_processo: {item['numero_processo']}",
            f"data_publicacao: {item['data_publicacao'] if item['data_publicacao'] else 'Não informada'}",
            f"tipo_acao: {item['tipo_acao']}",
            f"palavras-chave: {', '.join(keywords)}",
            "---",
            ""
        ]
        return "\n".join(metadata_lines)

    def split_front_matter(self, text: str) -> Tuple[Dict[str, str], str]:
        """Separa front matter YAML simples do corpo do texto."""
        if not text.startswith("---"):
            return {}, text

        lines = text.splitlines()
        if len(lines) < 3:
            return {}, text

        metadata: Dict[str, str] = {}
        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break
            if ":" in lines[i]:
                key, value = lines[i].split(":", 1)
                metadata[key.strip()] = value.strip()

        if end_index is None:
            return {}, text

        content = "\n".join(lines[end_index + 1:]).lstrip()
        return metadata, content
    
    def print_statistics(self):
        """Imprime estatísticas."""
        self.log("\n" + "=" * 70)
        self.log("📊 ESTATÍSTICAS DO PROCESSAMENTO")
        self.log("=" * 70)
        self.log(f"Total de sentenças processadas:     {self.stats['total_processed']}")
        self.log(f"Total de arquivos MD criados:       {self.stats['chunks_created']}")
        self.log(f"Categorias únicas:                  {len(self.stats['categorias'])}")
        self.log(f"Tipos de ação únicos:               {len(self.stats['tipos_acao'])}")
        self.log("=" * 70)
    
    async def upload_to_collection(self, e):
        """Faz upload dos arquivos MD para a Collection.
        Fluxo conforme documentação xAI: envio direto de documento com content + metadata."""
        if not self.selected_collection_id:
            self.log("⚠️ Nenhuma Collection selecionada. Abra as Configurações e escolha uma Collection antes de fazer upload.")
            return
        self.log("\n" + "=" * 70)
        self.log("☁️ Iniciando upload para Collection...")
        
        self.progress_bar.visible = True
        self.upload_btn.disabled = True
        self.page.update()
        
        base_url = "https://management-api.x.ai/v1"
        headers = {
            "Authorization": f"Bearer {self.management_key}"
        }
        
        uploaded = 0
        failed = 0
        
        try:
            if not self.generated_md_files and self.output_directory:
                output_path = Path(self.output_directory)
                if output_path.exists():
                    self.generated_md_files = [str(p) for p in output_path.glob("*.md")]

            if not self.generated_md_files:
                self.log("⚠️ Nenhum arquivo MD encontrado para upload.")
                return

            for idx, md_file in enumerate(self.generated_md_files):
                try:
                    basename = os.path.basename(md_file)
                    safe_basename = self.to_ascii_filename(basename)
                    with open(md_file, 'rb') as f:
                        file_bytes = f.read()

                    text_content = file_bytes.decode("utf-8", errors="ignore")
                    metadata, _ = self.split_front_matter(text_content)
                    if metadata is not None:
                        metadata = dict(metadata)
                        if "keywords" in metadata and "palavras-chave" not in metadata:
                            metadata["palavras-chave"] = metadata.pop("keywords")
                    fields = metadata if metadata else None
                    data_payload = {
                        "name": safe_basename,
                        "content_type": "text/markdown"
                    }
                    if fields:
                        data_payload["fields"] = json.dumps(fields, ensure_ascii=False)

                    resp = requests.post(
                        f"{base_url}/collections/{self.selected_collection_id}/documents",
                        headers=headers,
                        data=data_payload,
                        files={"data": (safe_basename, file_bytes, "text/markdown")},
                        timeout=60
                    )

                    if resp.status_code in [200, 201]:
                        uploaded += 1
                    else:
                        failed += 1
                        self.log(f"❌ Falha no upload de {os.path.basename(md_file)}: {resp.status_code} - {resp.text[:200]}")
                    
                    if (uploaded + failed) % 10 == 0:
                        self.log(f"⏳ Processados: {uploaded + failed}/{len(self.generated_md_files)}")
                    await asyncio.sleep(0.1)
                
                except Exception as ex:
                    failed += 1
                    self.log(f"❌ Erro no upload de {os.path.basename(md_file)}: {str(ex)}")
            
            self.log("\n" + "=" * 70)
            self.log(f"✅ Upload concluído!")
            self.log(f"   Sucesso: {uploaded}")
            self.log(f"   Falhas: {failed}")
            self.log("=" * 70)
        
        except Exception as ex:
            self.log(f"\n❌ Erro durante upload: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.progress_bar.visible = False
            self.upload_btn.disabled = False
            self.page.update()


def main(page: ft.Page):
    """Função principal."""
    app = CollectionUploaderV2UI(page)


if __name__ == "__main__":
    try:
        ft.run(main)
    except (KeyboardInterrupt, RuntimeError):
        # Suppress expected errors when closing application
        pass
