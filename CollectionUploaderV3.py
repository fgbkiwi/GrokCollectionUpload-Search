#!/usr/bin/env python3
"""
CollectionUploaderV3.py
Interface Flet para upload de MDs com metadados JSON para xAI Collections.
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


class CollectionUploaderV3:
    """Interface grafica para upload de MDs e metadados JSON."""

    REQUIRED_METADATA_KEYS = [
        "categoria",
        "reclamada",
        "numero_processo",
        "data_publicacao",
        "tipo_acao",
        "palavras-chave",
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Collection Uploader V3 - xAI"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20

        try:
            self.page.window.width = 1000
            self.page.window.height = 800
        except Exception:
            pass

        self.selected_md_files: List[str] = []
        self.output_directory: str = ""
        self.management_key: str = ""
        self.api_key: str = ""
        self.selected_model: str = ""
        self.selected_collection_id: str = ""
        self.collections_list: List[Dict[str, Any]] = []
        self.uploaded_files: List[str] = []

        self.config_file = "config.json"
        self.feedback_text: Optional[ft.TextField] = None
        self.dark_mode = False

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

                self.log("✅ Configuracao carregada do arquivo config.json")
                self.check_upload_button_state()
            else:
                self.log("ℹ️ Arquivo de configuracao nao encontrado. Usando padroes.")
        except Exception as exc:
            self.log(f"⚠️ Erro ao carregar configuracao: {str(exc)}")

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
            self.log("💾 Configuracao salva no arquivo config.json")
        except Exception as exc:
            self.log(f"⚠️ Erro ao salvar configuracao: {str(exc)}")

    def build_ui(self):
        title_text = ft.Text()
        title_text.value = "Collection Uploader V3 - xAI"
        title_text.size = 28
        title_text.weight = ft.FontWeight.BOLD
        title_text.color = "#1976D2"
        title_text.expand = True

        settings_button = ft.IconButton()
        settings_button.icon = ft.Icons.SETTINGS
        settings_button.icon_size = 30
        settings_button.icon_color = "#1976D2"
        settings_button.tooltip = "Configuracoes"
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

        self.create_collection_checkbox = ft.Checkbox(
            label="Criar nova collection",
            value=False,
            on_change=self.on_create_collection_toggle,
        )

        self.create_collection_name = ft.TextField()
        self.create_collection_name.label = "Nome da nova collection"
        self.create_collection_name.hint_text = "Ex: Precedentes TRT-10"
        self.create_collection_name.width = 450
        self.create_collection_name.disabled = True
        self.create_collection_name.on_change = self.on_create_collection_name_change  # type: ignore[attr-defined]

        self.create_collection_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.ADD), ft.Text(value="Criar Collection")]),
                tight=True,
            ),
            on_click=self.create_collection_click,
            disabled=True,
        )

        self.dark_mode_toggle = ft.Switch()
        self.dark_mode_toggle.label = "Dark Mode"
        self.dark_mode_toggle.value = self.dark_mode
        self.dark_mode_toggle.on_change = self.on_dark_mode_toggle  # type: ignore[attr-defined]

        close_button = ft.Button(
            content=ft.Text("Fechar"),
            on_click=self.close_config_dialog,
        )

        dialog_content = ft.Column(
            [
                ft.Text("⚙️ Configuracoes", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),
                ft.Text("Credenciais API", size=16, weight=ft.FontWeight.BOLD),
                self.dialog_management_key_field,
                ft.Row([self.dialog_load_collections_btn], spacing=10),
                self.dialog_collections_dropdown,
                ft.Divider(height=10),
                ft.Text("Nova Collection", size=16, weight=ft.FontWeight.BOLD),
                self.create_collection_checkbox,
                self.create_collection_name,
                ft.Row([self.create_collection_btn], spacing=10),
                ft.Divider(height=10),
                ft.Text("Aparência", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([self.dark_mode_toggle], spacing=10),
            ],
            spacing=15,
            width=600,
        )

        self.config_dialog = ft.AlertDialog()
        self.config_dialog.modal = False
        self.config_dialog.title = ft.Text("Configuracoes")
        self.config_dialog.content = dialog_content
        self.config_dialog.actions = [close_button]

    def open_config_dialog(self, e):
        self.dialog_management_key_field.value = self.management_key
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.update_collections_dropdown()
        self.sync_create_collection_state()

        if self.config_dialog not in self.page.overlay:
            self.page.overlay.append(self.config_dialog)
        self.config_dialog.open = True
        self.page.update()

    def close_config_dialog(self, e):
        self.log("🗂️ Fechando dialogo de configuracao...")
        self.selected_collection_id = str(self.dialog_collections_dropdown.value or "")
        if self.selected_collection_id:
            self.log(f"   Collection selecionada: {self.selected_collection_id}")
        self.save_config()
        self.check_upload_button_state()
        self.config_dialog.open = False
        self.page.update()

    def on_dialog_management_key_change(self, e):
        self.management_key = str(e.control.value or "")
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.sync_create_collection_state()
        self.save_config()
        self.page.update()

    def on_dialog_collection_change(self, e):
        self.selected_collection_id = str(e.control.value or "")
        self.save_config()
        self.check_upload_button_state()

    def on_create_collection_toggle(self, e):
        self.sync_create_collection_state()

    def on_create_collection_name_change(self, e):
        self.sync_create_collection_state()

    def sync_create_collection_state(self):
        create_enabled = bool(self.create_collection_checkbox.value)
        self.create_collection_name.disabled = not create_enabled
        has_name = bool(str(self.create_collection_name.value or "").strip())
        self.create_collection_btn.disabled = not (create_enabled and has_name and bool(self.management_key))
        self.page.update()

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

    def dialog_load_collections_click(self, e):
        self.log("🔄 Iniciando carregamento de collections via dialogo...")
        self.run_task(self._dialog_load_collections, e)

    async def _dialog_load_collections(self, e):
        await self.load_collections(e)
        try:
            self.update_collections_dropdown()
            self.page.update()
        except Exception as exc:
            self.log(f"❌ Erro ao atualizar dropdown: {str(exc)}")

    def create_files_section(self) -> ft.Container:
        self.md_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.INSERT_DRIVE_FILE), ft.Text(value="Selecionar Arquivos MD")]),
                tight=True,
            ),
            on_click=self.pick_md_files,
            width=250,
        )

        self.md_files_list = ft.Text("Nenhum arquivo selecionado", size=12, color="#616161")

        self.folder_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.FOLDER_OPEN), ft.Text(value="Selecionar Pasta de Saida")]),
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
                    ft.Row([self.md_picker_btn, self.folder_picker_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10),
                    self.md_files_list,
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
            on_click=self.generate_not_available,
            disabled=True,
            bgcolor="#1976D2",
            color="#FFFFFF",
            tooltip="Use MD_GenerationV3.py para gerar MDs",
        )

        self.upload_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.CLOUD_UPLOAD), ft.Text(value="Upload para Collection")]),
                tight=True,
            ),
            on_click=self.upload_to_collection_click,
            disabled=True,
            bgcolor="#388E3C",
            color="#FFFFFF",
        )

        self.progress_bar = ft.ProgressBar(width=800, visible=False)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("🚀 Ações", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([self.generate_md_btn, self.upload_btn], spacing=20),
                    self.progress_bar,
                ],
                spacing=15,
            ),
            padding=20,
            border=ft.Border.all(1, "#FFCC80"),
            border_radius=10,
        )

    async def pick_md_files(self, e):
        def open_file_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            files = filedialog.askopenfilenames(
                parent=root,
                title="Selecione os arquivos MD",
                filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
            )
            root.destroy()
            return files

        files = await asyncio.to_thread(open_file_dialog)

        if files:
            self.selected_md_files = list(files)
            files_text = "\n".join([f"• {os.path.basename(path)}" for path in files])
            self.md_files_list.value = f"Arquivos selecionados:\n{files_text}"
            self.md_files_list.color = "#388E3C"
            self.check_upload_button_state()
        else:
            self.selected_md_files = []
            self.md_files_list.value = "Nenhum arquivo selecionado"
            self.md_files_list.color = "#616161"

        self.page.update()

    async def pick_output_folder(self, e):
        def open_folder_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.lift()
            root.focus_force()
            path = filedialog.askdirectory(parent=root, title="Selecione a pasta de saida")
            root.destroy()
            return path

        path = await asyncio.to_thread(open_folder_dialog)

        if path:
            self.output_directory = str(path)
            self.output_folder_text.value = f"Pasta: {self.output_directory}"
            self.output_folder_text.color = "#388E3C"
            self.check_upload_button_state()
        else:
            self.output_directory = ""
            self.output_folder_text.value = "Nenhuma pasta selecionada"
            self.output_folder_text.color = "#616161"

        self.page.update()

    def check_upload_button_state(self):
        has_md_files = False
        if self.output_directory:
            try:
                output_path = Path(self.output_directory)
                has_md_files = output_path.exists() and any(output_path.glob("*.md"))
            except Exception:
                has_md_files = False

        can_upload = (
            (len(self.selected_md_files) > 0 or has_md_files)
            and len(self.selected_collection_id) > 0
            and len(self.management_key) > 0
        )
        self.upload_btn.disabled = not can_upload
        self.page.update()

    def generate_not_available(self, e):
        self.log("ℹ️ Geração não disponível aqui. Use MD_GenerationV3.py.")

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

    def upload_to_collection_click(self, e):
        self.log("🖱️ Clique em 'Upload para Collection' recebido...")
        self.run_task(self.upload_to_collection, e)

    async def load_collections(self, e):
        self.log("🔄 Carregando collections disponiveis...")

        if not self.management_key:
            self.log("⚠️ Management Key nao configurada.")
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

    def create_collection_click(self, e):
        self.log("🆕 Criacao de collection iniciada...")
        self.run_task(self.create_collection, e)

    async def create_collection(self, e):
        collection_name = str(self.create_collection_name.value or "").strip()
        if not collection_name:
            self.log("⚠️ Nome da collection nao informado.")
            return

        if not self.management_key:
            self.log("⚠️ Management Key nao configurada.")
            return

        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }

        field_definitions = [
            {"key": key, "inject_into_chunk": True} for key in self.REQUIRED_METADATA_KEYS
        ]

        payload = {
            "collection_name": collection_name,
            "field_definitions": field_definitions,
        }

        try:
            response = requests.post(
                "https://management-api.x.ai/v1/collections",
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in [200, 201]:
                data = response.json()
                new_id = (
                    data.get("collection_id")
                    or data.get("id")
                    or (data.get("collection", {}) if isinstance(data.get("collection"), dict) else {}).get("collection_id")
                )
                self.log("✅ Collection criada com sucesso!")
                if new_id:
                    self.selected_collection_id = str(new_id)
                    self.save_config()
                await self.load_collections(None)
                self.update_collections_dropdown()
                self.show_snackbar("Collection criada", success=True)
            else:
                self.log(f"❌ Falha ao criar collection: {response.status_code}")
                self.log(f"   {response.text[:200]}")
                self.show_snackbar("Falha ao criar collection", success=False)

        except Exception as exc:
            self.log(f"❌ Erro ao criar collection: {str(exc)}")
            self.show_snackbar("Erro ao criar collection", success=False)

    async def fetch_collection_schema(self, collection_id: str) -> Optional[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"https://management-api.x.ai/v1/collections/{collection_id}",
                headers=headers,
                timeout=20,
            )
            if response.status_code == 200:
                return response.json()

            self.log(f"❌ Erro ao obter schema da collection: {response.status_code}")
            self.log(f"   {response.text[:200]}")
            return None

        except Exception as exc:
            self.log(f"❌ Erro ao obter schema da collection: {str(exc)}")
            return None

    def extract_collection_keys(self, data: Dict[str, Any]) -> List[str]:
        field_defs = None

        if "field_definitions" in data:
            field_defs = data.get("field_definitions")
        elif "collection" in data and isinstance(data.get("collection"), dict):
            field_defs = data["collection"].get("field_definitions")
        elif "data" in data and isinstance(data.get("data"), dict):
            field_defs = data["data"].get("field_definitions")

        if not isinstance(field_defs, list):
            return []

        keys = []
        for field_def in field_defs:
            if isinstance(field_def, dict) and "key" in field_def:
                keys.append(str(field_def["key"]))

        return keys

    def collect_md_files(self) -> List[str]:
        md_files = list(self.selected_md_files)
        if not md_files and self.output_directory:
            output_path = Path(self.output_directory)
            if output_path.exists():
                md_files = [str(p) for p in output_path.glob("*.md")]
        return sorted(md_files)

    def find_metadata_path(self, md_file: str) -> str:
        md_path = Path(md_file)
        return str(md_path.with_name(f"{md_path.stem}_metadata.json"))

    def read_metadata(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return None
        except Exception as exc:
            self.log(f"❌ Erro ao ler metadados {os.path.basename(metadata_path)}: {str(exc)}")
            return None

    def validate_metadata_keys(self, md_files: List[str], collection_keys: List[str]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        expected_keys = set(collection_keys)

        for md_file in md_files:
            metadata_path = self.find_metadata_path(md_file)
            if not os.path.exists(metadata_path):
                errors.append(f"Metadados ausentes: {os.path.basename(metadata_path)}")
                continue

            metadata = self.read_metadata(metadata_path)
            if metadata is None:
                errors.append(f"Metadados invalidos: {os.path.basename(metadata_path)}")
                continue

            metadata_keys = set(metadata.keys())
            missing = expected_keys - metadata_keys
            extra = metadata_keys - expected_keys

            if missing or extra:
                missing_text = ", ".join(sorted(missing)) if missing else "-"
                extra_text = ", ".join(sorted(extra)) if extra else "-"
                errors.append(
                    f"Chaves divergentes em {os.path.basename(md_file)} (faltando: {missing_text}; extras: {extra_text})"
                )

        return len(errors) == 0, errors

    async def upload_to_collection(self, e):
        if not self.selected_collection_id:
            self.log("⚠️ Nenhuma Collection selecionada. Abra as Configuracoes e escolha uma Collection.")
            return

        self.log("\n" + "=" * 70)
        self.log("☁️ Iniciando upload para Collection...")

        self.progress_bar.visible = True
        self.upload_btn.disabled = True
        self.page.update()

        base_url = "https://management-api.x.ai/v1"
        headers = {"Authorization": f"Bearer {self.management_key}"}

        uploaded = 0
        failed = 0

        try:
            md_files = self.collect_md_files()
            if not md_files:
                self.log("⚠️ Nenhum arquivo MD encontrado para upload.")
                return

            schema = await self.fetch_collection_schema(self.selected_collection_id)
            if not schema:
                self.log("❌ Nao foi possivel validar o schema da collection.")
                self.show_snackbar("Erro no schema", success=False)
                return

            collection_keys = self.extract_collection_keys(schema)
            if not collection_keys:
                self.log("⚠️ Nenhum campo de metadados definido na collection.")
                self.show_snackbar("Collection sem metadados", success=False)
                return

            valid, errors = self.validate_metadata_keys(md_files, collection_keys)
            if not valid:
                self.log("❌ Validacao de metadados falhou. Upload cancelado.")
                for error in errors[:10]:
                    self.log(f"   - {error}")
                if len(errors) > 10:
                    self.log(f"   ... e mais {len(errors) - 10} erro(s)")
                self.show_snackbar("Metadados divergentes", success=False)
                return

            for idx, md_file in enumerate(md_files, start=1):
                try:
                    basename = os.path.basename(md_file)
                    safe_basename = self.to_ascii_filename(basename)
                    with open(md_file, "rb") as f:
                        file_bytes = f.read()

                    metadata_path = self.find_metadata_path(md_file)
                    metadata = self.read_metadata(metadata_path)
                    if metadata is None:
                        failed += 1
                        continue

                    data_payload = {
                        "name": safe_basename,
                        "content_type": "text/markdown",
                        "fields": json.dumps(metadata, ensure_ascii=False),
                    }

                    resp = requests.post(
                        f"{base_url}/collections/{self.selected_collection_id}/documents",
                        headers=headers,
                        data=data_payload,
                        files={"data": (safe_basename, file_bytes, "text/markdown")},
                        timeout=60,
                    )

                    if resp.status_code in [200, 201]:
                        uploaded += 1
                    else:
                        failed += 1
                        self.log(
                            f"❌ Falha no upload de {os.path.basename(md_file)}: {resp.status_code} - {resp.text[:200]}"
                        )

                    if (uploaded + failed) % 10 == 0:
                        self.log(f"⏳ Processados: {uploaded + failed}/{len(md_files)}")
                    await asyncio.sleep(0.1)

                except Exception as exc:
                    failed += 1
                    self.log(f"❌ Erro no upload de {os.path.basename(md_file)}: {str(exc)}")

            self.log("\n" + "=" * 70)
            self.log("✅ Upload concluido!")
            self.log(f"   Sucesso: {uploaded}")
            self.log(f"   Falhas: {failed}")
            self.log("=" * 70)
            self.show_snackbar("Upload concluido", success=failed == 0)

        except Exception as exc:
            self.log(f"\n❌ Erro durante upload: {str(exc)}")
            self.show_snackbar("Erro no upload", success=False)

        finally:
            self.progress_bar.visible = False
            self.upload_btn.disabled = False
            self.page.update()

    def sanitize_filename(self, text: str) -> str:
        text = re.sub(r"[<>:\"/\\|?*]", "", text)
        text = re.sub(r"[\s\-—]+", "_", text)
        return text[:100] or "document"

    def to_ascii_filename(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return self.sanitize_filename(ascii_text) or "document"

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
    CollectionUploaderV3(page)


if __name__ == "__main__":
    try:
        ft.run(main)
    except (KeyboardInterrupt, RuntimeError):
        pass
