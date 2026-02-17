#!/usr/bin/env python3
"""
MD_GenerationV3.py
Interface Flet para gerar arquivos MD e metadados JSON a partir de sentencas.
"""

import asyncio
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import flet as ft
import requests
import tkinter as tk
from tkinter import filedialog


class MDGenerationV3:
    """Interface grafica para gerar MDs e metadados JSON."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "MD Generation V3 - xAI"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20

        try:
            self.page.window.width = 1000
            self.page.window.height = 800
        except Exception:
            pass

        self.selected_json_files: List[str] = []
        self.output_directory: str = ""
        self.management_key: str = ""
        self.api_key: str = ""
        self.selected_model: str = ""
        self.selected_collection_id: str = ""
        self.collections_list: List[Dict[str, Any]] = []
        self.generated_md_files: List[str] = []

        self.available_models: List[str] = []

        self.stats = {
            "total_processed": 0,
            "chunks_created": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }

        self.config_file = "config.json"
        self.feedback_text: Optional[ft.TextField] = None
        self.dark_mode = False
        self.disable_chunking = False

        self.build_ui()
        self.clear_log()
        self.load_config()
        self.schedule_startup_refresh()

    def schedule_startup_refresh(self):
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(self.refresh_on_startup)
            else:
                asyncio.create_task(self.refresh_on_startup())
        except Exception:
            pass

    async def refresh_on_startup(self):
        self.clear_log()
        if self.management_key:
            await self.load_collections(None)
            self.update_collections_dropdown()

        if self.api_key:
            await self.fetch_models()
            self.update_models_dropdown()

        self.page.update()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                self.management_key = config.get("management_key", "")
                self.api_key = config.get("api_key", "")
                self.selected_model = config.get("selected_model", "")
                self.selected_collection_id = config.get("selected_collection_id", "")

                self.log("✅ Configuração carregada do arquivo config.json")
                self.check_generate_button_state()
            else:
                self.log("ℹ️ Arquivo de configuração não encontrado. Usando padrões.")
        except Exception as exc:
            self.log(f"⚠️ Erro ao carregar configuração: {str(exc)}")

    def save_config(self):
        try:
            config = {
                "management_key": self.management_key,
                "api_key": self.api_key,
                "selected_model": self.selected_model,
                "selected_collection_id": self.selected_collection_id,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.log("💾 Configuração salva no arquivo config.json")
        except Exception as exc:
            self.log(f"⚠️ Erro ao salvar configuração: {str(exc)}")

    def build_ui(self):
        title_text = ft.Text()
        title_text.value = "MD Generation V3 - xAI"
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

        files_section = self.create_files_section()
        actions_section = self.create_actions_section()

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
        self.feedback_text.width = 960

        self.page.add(
            ft.Column(
                [
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
                        padding=10,
                    ),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        )

        self.create_config_dialog()

    def create_config_dialog(self):
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
        self.dialog_api_key_field.hint_text = "Chave de API do Grok para geração de palavras-chave"
        self.dialog_api_key_field.password = True
        self.dialog_api_key_field.can_reveal_password = True
        self.dialog_api_key_field.width = 450
        self.dialog_api_key_field.value = self.api_key
        self.dialog_api_key_field.on_change = self.on_dialog_api_key_change  # type: ignore[attr-defined]

        self.dialog_model_dropdown = ft.Dropdown()
        self.dialog_model_dropdown.label = "Modelo para Geração de Palavras-chave"
        self.dialog_model_dropdown.options = [ft.dropdown.Option(model) for model in self.available_models]
        self.dialog_model_dropdown.value = self.selected_model
        self.dialog_model_dropdown.width = 300
        self.dialog_model_dropdown.on_change = self.on_dialog_model_change  # type: ignore[attr-defined]

        self.dialog_refresh_models_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.REFRESH), ft.Text(value="Atualizar Modelos")]),
                tight=True,
            ),
            on_click=self.dialog_refresh_models_click,
            disabled=len(self.api_key) == 0,
        )

        self.dialog_collections_dropdown = ft.Dropdown()
        self.dialog_collections_dropdown.label = "Collection para Upload"
        self.dialog_collections_dropdown.options = []
        self.dialog_collections_dropdown.on_change = self.on_dialog_collection_change  # type: ignore[attr-defined]
        self.dialog_collections_dropdown.on_blur = self.on_dialog_collection_change  # type: ignore[attr-defined]
        self.dialog_collections_dropdown.disabled = True
        self.dialog_collections_dropdown.width = 450

        self.dialog_load_collections_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.REFRESH), ft.Text(value="Carregar Collections")]),
                tight=True,
            ),
            on_click=self.dialog_load_collections_click,
            disabled=len(self.management_key) == 0,
        )

        self.dark_mode_toggle = ft.Switch()
        self.dark_mode_toggle.label = "Modo Escuro"
        self.dark_mode_toggle.value = self.dark_mode
        self.dark_mode_toggle.on_change = self.on_dark_mode_toggle  # type: ignore[attr-defined]

        close_button = ft.Button(
            content=ft.Text("Fechar"),
            on_click=self.close_config_dialog,
        )

        dialog_content = ft.Column(
            [
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
                ft.Row([self.dark_mode_toggle], spacing=10),
            ],
            spacing=15,
            width=600,
        )

        self.config_dialog = ft.AlertDialog()
        self.config_dialog.modal = False
        self.config_dialog.title = ft.Text("Configurações")
        self.config_dialog.content = dialog_content
        self.config_dialog.actions = [close_button]

    def open_config_dialog(self, e):
        self.dialog_management_key_field.value = self.management_key
        self.dialog_api_key_field.value = self.api_key
        self.update_models_dropdown()
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.dialog_refresh_models_btn.disabled = len(self.api_key) == 0
        self.update_collections_dropdown()

        if self.config_dialog not in self.page.overlay:
            self.page.overlay.append(self.config_dialog)
        self.config_dialog.open = True
        self.page.update()

    def close_config_dialog(self, e):
        self.log("🗂️ Fechando diálogo de configuração...")
        self.selected_collection_id = str(self.dialog_collections_dropdown.value or "")
        if self.selected_collection_id:
            self.log(f"   Collection selecionada: {self.selected_collection_id}")
        self.save_config()
        self.config_dialog.open = False
        self.page.update()

    def on_dialog_management_key_change(self, e):
        self.management_key = str(e.control.value or "")
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.save_config()
        self.page.update()

    def on_dialog_api_key_change(self, e):
        self.api_key = str(e.control.value or "")
        self.dialog_refresh_models_btn.disabled = len(self.api_key) == 0
        self.save_config()
        self.check_generate_button_state()
        self.page.update()

    def on_dialog_model_change(self, e):
        self.selected_model = str(e.control.value or "")
        self.save_config()
        self.check_generate_button_state()

    def on_dialog_collection_change(self, e):
        self.selected_collection_id = str(e.control.value or "")
        self.save_config()

    def on_dark_mode_toggle(self, e):
        self.dark_mode = e.control.value
        if self.dark_mode:
            self.page.theme_mode = ft.ThemeMode.DARK
            if self.feedback_text:
                self.feedback_text.bgcolor = "#1e1e1e"
                self.feedback_text.color = "#ffffff"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            if self.feedback_text:
                self.feedback_text.bgcolor = "#f5f5f5"
                self.feedback_text.color = "#000000"
        self.page.update()

    def dialog_refresh_models_click(self, e):
        self.log("🖱️ Clique em 'Atualizar Modelos' recebido...")
        self.run_task(self._dialog_refresh_models)

    async def _dialog_refresh_models(self):
        await self.fetch_models()
        if hasattr(self, "dialog_model_dropdown"):
            self.update_models_dropdown()
            self.page.update()

    def dialog_load_collections_click(self, e):
        self.log("🔄 Iniciando carregamento de collections via diálogo...")
        self.run_task(self._dialog_load_collections, e)

    async def _dialog_load_collections(self, e):
        await self.load_collections(e)
        try:
            self.update_collections_dropdown()
            self.page.update()
        except Exception as exc:
            self.log(f"❌ Erro ao atualizar dropdown: {str(exc)}")

    def create_files_section(self) -> ft.Container:
        self.json_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.INSERT_DRIVE_FILE), ft.Text(value="Selecionar Arquivos JSON")]),
                tight=True,
            ),
            on_click=self.pick_json_files,
            width=250,
        )

        self.json_files_list = ft.Text("Nenhum arquivo selecionado", size=12, color="#616161")

        self.folder_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.FOLDER_OPEN), ft.Text(value="Selecionar Pasta de Saída")]),
                tight=True,
            ),
            on_click=self.pick_output_folder,
            width=250,
        )

        self.output_folder_text = ft.Text("Nenhuma pasta selecionada", size=12, color="#616161")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("📁 Seleção de Arquivos e Pasta de Saída", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([self.json_picker_btn, self.folder_picker_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10),
                    self.json_files_list,
                    self.output_folder_text,
                ],
                spacing=15,
            ),
            padding=20,
            border=ft.Border.all(1, "#A5D6A7"),
            border_radius=10,
        )

    def create_actions_section(self) -> ft.Container:
        self.generate_md_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.CREATE_NEW_FOLDER), ft.Text(value="Gerar Arquivos MD")]),
                tight=True,
            ),
            on_click=self.generate_md_files_click,
            disabled=True,
            bgcolor="#1976D2",
            color="#FFFFFF",
        )

        self.no_chunk_checkbox = ft.Checkbox(
            label="do not chunk JSON objects",
            value=self.disable_chunking,
            on_change=self.on_disable_chunking_change,
        )

        self.progress_bar = ft.ProgressBar(width=800, visible=False)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("🚀 Ações", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([self.generate_md_btn, self.no_chunk_checkbox], spacing=20),
                    self.progress_bar,
                ],
                spacing=15,
            ),
            padding=20,
            border=ft.Border.all(1, "#FFCC80"),
            border_radius=10,
        )

    async def pick_json_files(self, e):
        def open_file_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            files = filedialog.askopenfilenames(
                parent=root,
                title="Selecione os arquivos JSON",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")],
            )
            root.destroy()
            return files

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

    async def pick_output_folder(self, e):
        def open_folder_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            path = filedialog.askdirectory(parent=root, title="Selecione a pasta de saída")
            root.destroy()
            return path

        path = await asyncio.to_thread(open_folder_dialog)

        if path:
            self.output_directory = str(path)
            self.output_folder_text.value = f"Pasta de Saída: {self.output_directory}"
            self.output_folder_text.color = "#388E3C"
            self.check_generate_button_state()
        else:
            self.output_directory = ""
            self.output_folder_text.value = "Nenhuma pasta de saída selecionada"
            self.output_folder_text.color = "#616161"

        self.page.update()

    def check_generate_button_state(self):
        can_generate = (
            len(self.selected_json_files) > 0
            and len(self.output_directory) > 0
            and len(self.api_key) > 0
            and len(self.selected_model) > 0
        )
        self.generate_md_btn.disabled = not can_generate
        self.page.update()

    def on_disable_chunking_change(self, e):
        self.disable_chunking = bool(e.control.value)
        self.log(f"ℹ️ Chunking desativado: {self.disable_chunking}")
        self.page.update()

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        if self.feedback_text:
            self.feedback_text.value += log_entry
            self.page.update()

    def run_task(self, async_fn, *args):
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(async_fn, *args)
            else:
                asyncio.create_task(async_fn(*args))
        except Exception:
            pass

    def clear_log(self):
        if self.feedback_text:
            self.feedback_text.value = ""
            self.page.update()

    def generate_md_files_click(self, e):
        self.log("🖱️ Clique em 'Gerar Arquivos MD' recebido...")
        self.run_task(self.generate_md_files, e)

    async def load_collections(self, e):
        self.log("🔄 Carregando collections disponiveis...")

        if not self.management_key:
            self.log("⚠️ Management Key não configurada.")
            return

        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}",
                "Content-Type": "application/json",
            }

            urls_to_try = [
                "https://management-api.x.ai/v1/collections",
                "https://api.x.ai/v1/collections",
                "https://management-api.x.ai/v1/collections/list",
                "https://api.x.ai/collections",
                "https://management-api.x.ai/collections",
                "https://api.x.ai/v1/collections/list",
                "https://management-api.x.ai/collections/list",
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

                        collections: List[Dict[str, Any]] = []
                        if isinstance(data, list):
                            collections = data
                        elif "data" in data and isinstance(data["data"], list):
                            collections = data["data"]
                        elif "collections" in data and isinstance(data["collections"], list):
                            collections = data["collections"]

                        if collections:
                            self.collections_list = collections
                            self.log(f"✅ {len(self.collections_list)} collection(s) encontrada(s)")
                            self.page.update()
                            return

                except Exception as exc:
                    last_error = str(exc)
                    continue

            if response:
                self.log(f"❌ Erro ao carregar collections: {response.status_code}")
                self.log(f"   {response.text[:200]}...")
            else:
                self.log(f"❌ Erro ao carregar collections: {last_error or 'Nenhum endpoint funcionou'}")

        except Exception as exc:
            self.log(f"❌ Erro ao carregar collections: {str(exc)}")

        self.page.update()

    async def fetch_models(self):
        if not self.api_key:
            self.log("⚠️ API Key não configurada. Configure para carregar modelos.")
            return

        self.log("🔄 Buscando modelos disponíveis...")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get("https://api.x.ai/v1/models", headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
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

        except Exception as exc:
            self.log(f"❌ Erro ao buscar modelos: {str(exc)}")
            self.available_models = []

    def update_models_dropdown(self):
        if not hasattr(self, "dialog_model_dropdown"):
            return

        model_options = list(self.available_models)
        if not model_options:
            self.dialog_model_dropdown.options = []
            self.dialog_model_dropdown.value = ""
            return

        if model_options and self.selected_model and self.selected_model not in model_options:
            self.selected_model = ""

        self.dialog_model_dropdown.options = [ft.dropdown.Option(model_id) for model_id in model_options]

        if not self.selected_model and model_options:
            self.selected_model = model_options[0]

        self.dialog_model_dropdown.value = self.selected_model

    def update_collections_dropdown(self):
        if not hasattr(self, "dialog_collections_dropdown"):
            return

        options = []
        if self.collections_list:
            options = [
                ft.dropdown.Option(
                    key=str(col.get("collection_id", "")),
                    text=str(col.get("collection_name", col.get("collection_id", ""))),
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

    async def generate_md_files(self, e):
        if not self.selected_model:
            self.log("⚠️ Nenhum modelo selecionado. Abra as Configurações e escolha um modelo.")
            return

        self.log("=" * 70)
        self.log("🚀 Iniciando geração de arquivos MD...")

        self.progress_bar.visible = True
        self.generate_md_btn.disabled = True
        self.page.update()

        try:
            self.stats = {
                "total_processed": 0,
                "chunks_created": 0,
                "categorias": set(),
                "tipos_acao": set(),
            }
            self.generated_md_files = []

            output_path = Path(self.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)

            for json_file in self.selected_json_files:
                self.log(f"\n📄 Processando: {os.path.basename(json_file)}")

                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    data = data["data"]

                if not isinstance(data, list):
                    self.log("⚠️ Formato JSON inválido. Esperado lista de sentenças.")
                    continue

                self.log(f"   {len(data)} sentença(s) encontrada(s)")

                for idx, item in enumerate(data, start=1):
                    await self.process_sentenca(item, idx, output_path)

                    if idx % 5 == 0:
                        self.log(f"   ⏳ Processadas: {idx}/{len(data)}")
                        await asyncio.sleep(0.1)

            self.log("\n✅ Geração de arquivos MD concluída!")
            self.print_statistics()
            self.show_snackbar("Geração concluída", success=True)

        except Exception as exc:
            self.log(f"\n❌ Erro durante geração: {str(exc)}")
            self.show_snackbar("Erro na geração", success=False)

        finally:
            self.progress_bar.visible = False
            self.generate_md_btn.disabled = False
            self.page.update()

    async def process_sentenca(self, item: Dict[str, Any], index: int, output_path: Path):
        conteudo = str(item.get("conteudo", "")).strip()

        if not conteudo:
            self.log("⚠️ Sentença sem conteúdo. Ignorando.")
            return

        categoria = str(item.get("categoria", ""))
        tipo_acao = str(item.get("tipo_acao", ""))

        keywords = await self.extract_keywords_with_grok(conteudo, categoria)

        if categoria:
            self.stats["categorias"].add(categoria)
        if tipo_acao:
            self.stats["tipos_acao"].add(tipo_acao)

        chunks = [conteudo] if self.disable_chunking else self.chunk_text(conteudo)

        for chunk_idx, chunk in enumerate(chunks):
            categoria_safe = self.sanitize_filename(categoria)
            processo_safe = str(item.get("numero_processo", "")).replace(".", "_").replace("-", "_")

            if len(chunks) > 1:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx + 1:02d}.md"
            else:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}.md"

            filepath = output_path / filename

            metadata = self.build_metadata(item, keywords)
            metadata_path = output_path / f"{filepath.stem}_metadata.json"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(chunk)
                if not chunk.endswith("\n"):
                    f.write("\n")

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.generated_md_files.append(str(filepath))
            self.stats["chunks_created"] += 1

        self.stats["total_processed"] += 1

    async def extract_keywords_with_grok(self, conteudo: str, categoria: str) -> List[str]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            prompt = (
                "Analise o seguinte texto jurídico trabalhista e extraia até 10 palavras-chave relevantes.\n"
                "Foque em termos jurídicos, conceitos trabalhistas, leis citadas (CLT, Súmulas), e temas principais.\n\n"
                f"Categoria: {categoria}\n\n"
                f"Texto:\n{conteudo[:1500]}\n\n"
                "Retorne APENAS as palavras-chave separadas por vírgula, em minúsculas, "
                "usando underscore para espaços.\n"
                "Exemplo: horas_extras, clt, adicional_noturno, art_71, sumula_437"
            )

            payload = {
                "model": self.selected_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            }

            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                keywords_text = str(data["choices"][0]["message"]["content"]).strip()
                keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]
                return keywords[:10]

            return self.default_keywords(categoria)

        except Exception as exc:
            self.log(f"⚠️ Erro ao gerar palavras-chave com Grok: {str(exc)}")
            return self.default_keywords(categoria)

    def default_keywords(self, categoria: str) -> List[str]:
        fallback = categoria.lower().replace(" ", "_") if categoria else "trabalhista"
        return [fallback, "clt", "trabalhista"]

    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                last_period = text.rfind(".", start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end < len(text) else end

        return chunks

    def sanitize_filename(self, text: str) -> str:
        text = re.sub(r"[<>:\"/\\|?*]", "", text)
        text = re.sub(r"[\s\-—]+", "_", text)
        return text[:100] or "document"

    def to_ascii_filename(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return self.sanitize_filename(ascii_text) or "document"

    def build_metadata(self, item: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
        metadata = {k: v for k, v in item.items() if k != "conteudo"}
        metadata["palavras-chave"] = keywords

        cleaned: Dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                cleaned[key] = ""
            elif isinstance(value, (str, int, float, bool, list, dict)):
                cleaned[key] = value
            else:
                cleaned[key] = str(value)

        return cleaned

    def print_statistics(self):
        self.log("\n" + "=" * 70)
        self.log("📊 ESTATISTICAS DO PROCESSAMENTO")
        self.log("=" * 70)
        self.log(f"Total de sentencas processadas:     {self.stats['total_processed']}")
        self.log(f"Total de arquivos MD criados:       {self.stats['chunks_created']}")
        self.log(f"Categorias unicas:                  {len(self.stats['categorias'])}")
        self.log(f"Tipos de acao unicos:               {len(self.stats['tipos_acao'])}")
        self.log("=" * 70)

    def show_snackbar(self, message: str, success: bool = True):
        bgcolor = "#2E7D32" if success else "#C62828"
        snack = ft.SnackBar(content=ft.Text(message), bgcolor=bgcolor)
        show_fn = getattr(self.page, "show_snack_bar", None)
        if callable(show_fn):
            show_fn(snack)
            return
        try:
            setattr(self.page, "snack_bar", snack)
            getattr(self.page, "snack_bar").open = True
            self.page.update()
        except Exception:
            pass


def main(page: ft.Page):
    MDGenerationV3(page)


if __name__ == "__main__":
    try:
        ft.run(main)
    except (KeyboardInterrupt, RuntimeError):
        pass
