#!/usr/bin/env python3
"""
CollectionUploaderV3.py
Interface Flet para upload em lotes de arquivos Markdown com metadados JSON para xAI Collections.
"""

import asyncio
import csv
import json
import os
import re
import signal
import sys
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import flet as ft
import requests
import tkinter as tk
from tkinter import filedialog


class CollectionUploaderV3:
    """Interface gráfica para upload em lotes de MDs e metadados JSON."""

    DEFAULT_VISIBLE_BATCHES = 120

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
            self.page.window.width = 1080
            self.page.window.height = 860
        except Exception:
            pass

        self.config_file = "config.json"
        self.session_state_file_name = "upload_session_state.json"

        self.management_key: str = ""
        self.selected_collection_id: str = ""
        self.selected_model: str = ""
        self.target_directory: str = ""
        self.log_directory: str = ""
        self.max_batches_to_show: int = 0

        self.collections_list: List[Dict[str, Any]] = []
        self.batch_map: Dict[str, List[str]] = {}
        self.batch_status: Dict[str, str] = {}
        self.batch_buttons: Dict[str, ft.Button] = {}
        self.active_upload_batch: Optional[str] = None

        self.session_state: Dict[str, Any] = {
            "version": 1,
            "updated_at": "",
            "collection_uploads": {},
        }

        self.feedback_text: Optional[ft.TextField] = None
        self.batch_rows: Optional[ft.Column] = None
        self.progress_bar: Optional[ft.ProgressBar] = None
        self.progress_title: Optional[ft.Text] = None
        self.progress_stats: Optional[ft.Text] = None
        self.progress_eta: Optional[ft.Text] = None
        self.skip_uploaded_checkbox: Optional[ft.Checkbox] = None

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

        if self.log_directory:
            self.log_folder_text.value = f"Pasta de log: {self.log_directory}"
            self.log_folder_text.color = "#2E7D32"
            self.load_session_state()

        if self.target_directory:
            self.target_folder_text.value = f"Pasta de arquivos: {self.target_directory}"
            self.target_folder_text.color = "#2E7D32"
            self.refresh_batches()

        self.safe_update_ui()

    def load_config(self):
        try:
            if not os.path.exists(self.config_file):
                self.log("ℹ️ Arquivo de configuração não encontrado. Usando valores padrão.")
                return

            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.management_key = str(config.get("management_key", ""))
            self.selected_collection_id = str(config.get("selected_collection_id", ""))
            self.selected_model = str(config.get("selected_model", ""))
            self.target_directory = str(config.get("target_directory", ""))
            self.log_directory = str(config.get("log_directory", ""))
            self.max_batches_to_show = int(config.get("max_batches_to_show", 0) or 0)

            self.max_batches_field.value = str(self.max_batches_to_show if self.max_batches_to_show > 0 else 0)
            self.log("✅ Configuração carregada do arquivo config.json")
            self.check_upload_button_state()
        except Exception as exc:
            self.log(f"⚠️ Erro ao carregar configuração: {str(exc)}")

    def save_config(self):
        try:
            payload = {
                "management_key": self.management_key,
                "selected_collection_id": self.selected_collection_id,
                "selected_model": self.selected_model,
                "target_directory": self.target_directory,
                "log_directory": self.log_directory,
                "max_batches_to_show": self.max_batches_to_show,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            self.log("💾 Configuração salva no arquivo config.json")
        except Exception as exc:
            self.log(f"⚠️ Erro ao salvar configuração: {str(exc)}")

    def build_ui(self):
        title = ft.Text("Collection Uploader V3 - xAI", size=28, weight=ft.FontWeight.BOLD, color="#1976D2", expand=True)
        settings_btn = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_size=30,
            icon_color="#1976D2",
            tooltip="Configurações",
            on_click=self.open_config_dialog,
        )

        self.feedback_text = ft.TextField(
            label="Log de Execução",
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=15,
            bgcolor="#f5f5f5",
            color="#000000",
            border_color="#42A5F5",
            expand=True,
            width=1000,
        )

        self.page.add(
            ft.Column(
                [
                    ft.Row([title, settings_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=20),
                    self.create_files_section(),
                    ft.Divider(height=20),
                    self.create_actions_section(),
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

    def create_files_section(self) -> ft.Container:
        self.target_folder_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.FOLDER_OPEN), ft.Text(value="Selecionar Pasta de Arquivos")]),
                tight=True,
            ),
            on_click=self.pick_target_folder,
            width=320,
        )

        self.log_folder_picker_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.FOLDER_SPECIAL), ft.Text(value="Selecionar Pasta de Log")]),
                tight=True,
            ),
            on_click=self.pick_log_folder,
            width=280,
        )

        self.max_batches_field = ft.TextField(
            label="Quantidade de lotes",
            hint_text="0 = 1 lote",
            width=220,
            value="0",
            on_blur=self.apply_batch_limit,
        )

        self.refresh_batches_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.REFRESH), ft.Text(value="Atualizar Lotes")]),
                tight=True,
            ),
            on_click=self.refresh_batches_click,
            width=220,
        )

        self.target_folder_text = ft.Text("Nenhuma pasta de arquivos selecionada", size=12, color="#616161")
        self.log_folder_text = ft.Text("Nenhuma pasta de log selecionada", size=12, color="#616161")
        self.batch_summary_text = ft.Text("Nenhum lote identificado", size=12, color="#616161")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("📁 Seleção de Pastas e Lotes", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([self.target_folder_picker_btn, self.log_folder_picker_btn], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([self.max_batches_field, self.refresh_batches_btn], spacing=20),
                    ft.Divider(height=10),
                    self.target_folder_text,
                    self.log_folder_text,
                    self.batch_summary_text,
                ],
                spacing=15,
            ),
            padding=20,
            border=ft.Border.all(1, "#A5D6A7"),
            border_radius=10,
        )

    def create_actions_section(self) -> ft.Container:
        self.skip_uploaded_checkbox = ft.Checkbox(
            label="Pular arquivos já enviados em sessões anteriores",
            value=True,
        )

        self.progress_title = ft.Text("Upload inativo", size=16, weight=ft.FontWeight.BOLD, color="#455A64")
        self.progress_bar = ft.ProgressBar(width=960, visible=False, value=0)
        self.progress_stats = ft.Text("", size=13)
        self.progress_eta = ft.Text("", size=13)

        self.batch_rows = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=280)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("🚀 Upload por Lote", size=20, weight=ft.FontWeight.BOLD),
                    self.skip_uploaded_checkbox,
                    self.progress_title,
                    self.progress_bar,
                    self.progress_stats,
                    self.progress_eta,
                    ft.Divider(height=10),
                    ft.Text("Lotes disponíveis", size=16, weight=ft.FontWeight.BOLD),
                    self.batch_rows,
                ],
                spacing=15,
            ),
            padding=20,
            border=ft.Border.all(1, "#FFCC80"),
            border_radius=10,
        )

    def create_config_dialog(self):
        self.dialog_management_key_field = ft.TextField(
            label="Management Key (xAI Collection)",
            hint_text="Chave de gerenciamento da Collection",
            password=True,
            can_reveal_password=True,
            width=500,
            value=self.management_key,
            on_change=self.on_dialog_management_key_change,
        )

        self.dialog_collections_dropdown = ft.Dropdown(
            label="Collection para Upload",
            options=[],
            width=500,
            disabled=True,
            on_blur=self.on_dialog_collection_change,
        )

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

        self.create_collection_name = ft.TextField(
            label="Nome da nova collection",
            hint_text="Ex: Precedentes TRT-10",
            width=500,
            disabled=True,
            on_change=self.on_create_collection_name_change,
        )

        self.create_collection_btn = ft.Button(
            content=ft.Row(
                controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.ADD), ft.Text(value="Criar Collection")]),
                tight=True,
            ),
            on_click=self.create_collection_click,
            disabled=True,
        )

        self.dark_mode_toggle = ft.Switch(
            label="Dark Mode",
            value=self.dark_mode,
            on_change=self.on_dark_mode_toggle,
        )

        self.config_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Configurações"),
            content=ft.Column(
                [
                    ft.Text("⚙️ Configurações", size=24, weight=ft.FontWeight.BOLD),
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
                    self.dark_mode_toggle,
                ],
                spacing=15,
                width=640,
            ),
            actions=[ft.Button(content=ft.Text("Fechar"), on_click=self.close_config_dialog)],
        )

    def open_config_dialog(self, e):
        self.dialog_management_key_field.value = self.management_key
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.update_collections_dropdown()
        self.sync_create_collection_state()

        if self.config_dialog not in self.page.overlay:
            self.page.overlay.append(self.config_dialog)
        self.config_dialog.open = True
        self.safe_update_ui()

    def close_config_dialog(self, e):
        self.selected_collection_id = str(self.dialog_collections_dropdown.value or "")
        self.save_config()
        self.refresh_batches()
        self.config_dialog.open = False
        self.safe_update_ui()

    def on_dialog_management_key_change(self, e):
        self.management_key = str(e.control.value or "")
        self.dialog_load_collections_btn.disabled = len(self.management_key) == 0
        self.sync_create_collection_state()
        self.save_config()
        self.check_upload_button_state()

    def on_dialog_collection_change(self, e):
        self.selected_collection_id = str(e.control.value or "")
        self.save_config()
        self.refresh_batches()
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
        self.safe_update_ui()

    def on_dark_mode_toggle(self, e):
        self.dark_mode = bool(e.control.value)
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
        self.safe_update_ui()

    def dialog_load_collections_click(self, e):
        self.run_task(self._dialog_load_collections, e)

    async def _dialog_load_collections(self, e):
        await self.load_collections(e)
        self.update_collections_dropdown()
        self.safe_update_ui()

    async def load_collections(self, e):
        self.log("🔄 Carregando collections disponíveis...")

        if not self.management_key:
            self.log("⚠️ Management Key não configurada.")
            return

        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }

        urls_to_try = [
            "https://management-api.x.ai/v1/collections",
            "https://api.x.ai/v1/collections",
            "https://management-api.x.ai/v1/collections/list",
            "https://api.x.ai/collections",
        ]

        response = None
        last_error = None

        for url in urls_to_try:
            try:
                use_headers = "management-api" in url
                response = requests.get(url, headers=headers if use_headers else {}, timeout=15)
                if response.status_code != 200:
                    continue

                data = response.json()
                collections: List[Dict[str, Any]] = []

                if isinstance(data, list):
                    collections = data
                elif isinstance(data, dict):
                    if isinstance(data.get("data"), list):
                        collections = cast(List[Dict[str, Any]], data["data"])
                    elif isinstance(data.get("collections"), list):
                        collections = cast(List[Dict[str, Any]], data["collections"])

                if collections:
                    self.collections_list = collections
                    self.log(f"✅ {len(collections)} collection(s) encontrada(s)")
                    return
            except Exception as exc:
                last_error = str(exc)

        if response is not None:
            self.log(f"❌ Erro ao carregar collections: {response.status_code}")
        else:
            self.log(f"❌ Erro ao carregar collections: {last_error or 'Nenhum endpoint funcionou'}")

    def update_collections_dropdown(self):
        options = []
        for collection in self.collections_list:
            cid = str(collection.get("collection_id", ""))
            name = str(collection.get("collection_name", cid))
            if cid:
                options.append(ft.dropdown.Option(key=cid, text=name))

        self.dialog_collections_dropdown.options = options
        self.dialog_collections_dropdown.disabled = len(options) == 0

        if self.selected_collection_id:
            keys = {str(opt.key) for opt in options if opt.key is not None}
            if self.selected_collection_id in keys:
                self.dialog_collections_dropdown.value = self.selected_collection_id
            else:
                self.dialog_collections_dropdown.value = ""

    def create_collection_click(self, e):
        self.run_task(self.create_collection, e)

    async def create_collection(self, e):
        collection_name = str(self.create_collection_name.value or "").strip()
        if not collection_name:
            self.show_snackbar("Informe um nome para a nova collection.", success=False)
            return

        if not self.management_key:
            self.show_snackbar("Management Key não configurada.", success=False)
            return

        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "collection_name": collection_name,
            "field_definitions": [{"key": key, "inject_into_chunk": True} for key in self.REQUIRED_METADATA_KEYS],
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
                if new_id:
                    self.selected_collection_id = str(new_id)
                    self.save_config()

                await self.load_collections(None)
                self.update_collections_dropdown()
                self.refresh_batches()
                self.show_snackbar("Collection criada com sucesso.", success=True)
                self.log("✅ Collection criada com sucesso")
            else:
                self.show_snackbar("Falha ao criar collection.", success=False)
                self.log(f"❌ Falha ao criar collection: {response.status_code} - {response.text[:200]}")
        except Exception as exc:
            self.show_snackbar("Erro ao criar collection.", success=False)
            self.log(f"❌ Erro ao criar collection: {str(exc)}")

    def pick_target_folder(self, e):
        if self.active_upload_batch:
            self.show_snackbar("Upload em andamento. Aguarde para alterar a pasta de arquivos.", success=False)
            return

        try:
            root = tk.Tk()
            try:
                root.withdraw()
                root.attributes("-topmost", True)
                root.lift()
                root.focus_force()
                path = str(filedialog.askdirectory(title="Selecione a pasta com arquivos MD e JSON") or "").strip()
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass

            if path:
                self.target_directory = path
                self.target_folder_text.value = f"Pasta de arquivos: {self.target_directory}"
                self.target_folder_text.color = "#2E7D32"
                self.save_config()
                self.refresh_batches()
            else:
                self.target_directory = ""
                self.target_folder_text.value = "Nenhuma pasta de arquivos selecionada"
                self.target_folder_text.color = "#616161"
                self.batch_map = {}
                self.batch_status = {}
                self.render_batch_rows()

            self.check_upload_button_state()
        except Exception as exc:
            self.log(f"❌ Erro ao abrir seletor de pasta de arquivos: {str(exc)}")

    def pick_log_folder(self, e):
        if self.active_upload_batch:
            self.show_snackbar("Upload em andamento. Aguarde para alterar a pasta de log.", success=False)
            return

        try:
            root = tk.Tk()
            try:
                root.withdraw()
                root.attributes("-topmost", True)
                root.lift()
                root.focus_force()
                path = str(filedialog.askdirectory(title="Selecione a pasta de log") or "").strip()
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass

            if path:
                self.log_directory = path
                self.log_folder_text.value = f"Pasta de log: {self.log_directory}"
                self.log_folder_text.color = "#2E7D32"
                self.save_config()
                self.load_session_state()
                self.refresh_batches()
            else:
                self.log_directory = ""
                self.log_folder_text.value = "Nenhuma pasta de log selecionada"
                self.log_folder_text.color = "#616161"

            self.check_upload_button_state()
        except Exception as exc:
            self.log(f"❌ Erro ao abrir seletor de pasta de log: {str(exc)}")

    def refresh_batches_click(self, e):
        self.refresh_batches()
        self.check_upload_button_state()

    def apply_batch_limit(self, e):
        raw = str(self.max_batches_field.value or "0").strip()
        if not raw:
            raw = "0"

        try:
            value = int(raw)
            if value < 0:
                raise ValueError()
            self.max_batches_to_show = value
            self.save_config()
            self.refresh_batches()
            self.check_upload_button_state()
        except ValueError:
            self.show_snackbar("Informe um número válido de lotes (0 ou maior).", success=False)

    def extract_batch_prefix(self, file_name: str) -> Optional[str]:
        match = re.match(r"^(\d{4,5})", file_name)
        if not match:
            return None
        raw = match.group(1)
        try:
            return f"{int(raw):05d}"
        except ValueError:
            return None

    def validate_target_directory(self, directory: str) -> Tuple[bool, str]:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return False, "A pasta selecionada não existe ou não é válida."

        md_files = list(path.glob("*.md"))
        json_files = list(path.glob("*.json"))

        if not md_files:
            return False, "Nenhum arquivo MD encontrado na pasta selecionada."
        if not json_files:
            return False, "Nenhum arquivo JSON encontrado na pasta selecionada."

        md_prefixes = {self.extract_batch_prefix(p.name) for p in md_files if self.extract_batch_prefix(p.name)}
        json_prefixes = {self.extract_batch_prefix(p.name) for p in json_files if self.extract_batch_prefix(p.name)}

        if not md_prefixes:
            return False, "Não foi possível identificar prefixos de 5 dígitos nos arquivos MD."
        if not json_prefixes:
            return False, "Não foi possível identificar prefixos de 5 dígitos nos arquivos JSON."

        missing_metadata = 0
        for md_file in md_files:
            metadata_path = self.find_metadata_path(str(md_file))
            if not os.path.exists(metadata_path):
                missing_metadata += 1

        if missing_metadata == len(md_files):
            return False, "Nenhum arquivo *_metadata.json correspondente foi encontrado para os MDs."

        return True, ""

    def group_files_into_batches(self, directory: str) -> Dict[str, List[str]]:
        md_files = list(Path(directory).glob("*.md"))

        def sort_key(path: Path) -> Tuple[int, str]:
            prefix = self.extract_batch_prefix(path.name)
            prefix_value = int(prefix) if prefix is not None else 10**9
            return (prefix_value, path.name)

        md_files_sorted = sorted(md_files, key=sort_key)
        file_list = [str(path) for path in md_files_sorted]

        total = len(file_list)
        if total == 0:
            return {}

        if self.max_batches_to_show <= 0:
            return {"01": file_list}

        batches = max(self.max_batches_to_show, 1)
        base_size = total // batches
        remainder = total % batches

        grouped: Dict[str, List[str]] = {}
        cursor = 0
        for idx in range(batches):
            batch_size = base_size + (1 if idx < remainder else 0)
            if batch_size == 0:
                continue
            batch_id = f"{idx + 1:02d}"
            grouped[batch_id] = file_list[cursor : cursor + batch_size]
            cursor += batch_size

        return grouped

    def get_visible_batch_ids(self) -> List[str]:
        batch_ids = sorted(self.batch_map.keys())
        return batch_ids[: self.DEFAULT_VISIBLE_BATCHES]

    def get_batch_sequence(self, batch_id: str) -> int:
        ordered = sorted(self.batch_map.keys())
        try:
            return ordered.index(batch_id) + 1
        except ValueError:
            return 0

    def get_batch_prefix_range(self, batch_id: str) -> Tuple[str, str]:
        files = self.batch_map.get(batch_id, [])
        prefixes = [self.extract_batch_prefix(Path(path).name) for path in files]
        numeric_prefixes = [int(p) for p in prefixes if p is not None]

        if not numeric_prefixes:
            return "", ""

        start_prefix = f"{min(numeric_prefixes):05d}"
        end_prefix = f"{max(numeric_prefixes):05d}"
        return start_prefix, end_prefix

    def get_batch_sequence_range(self, batch_id: str) -> Tuple[str, str]:
        ordered = sorted(self.batch_map.keys())
        start_index = 1
        for current_id in ordered:
            size = len(self.batch_map.get(current_id, []))
            if current_id == batch_id:
                end_index = start_index + max(size - 1, 0)
                return f"{start_index:05d}", f"{end_index:05d}"
            start_index += size
        return "", ""

    def refresh_batches(self):
        if not self.target_directory:
            self.batch_map = {}
            self.batch_status = {}
            self.batch_summary_text.value = "Nenhum lote identificado"
            self.batch_summary_text.color = "#616161"
            self.render_batch_rows()
            return

        valid, message = self.validate_target_directory(self.target_directory)
        if not valid:
            self.batch_map = {}
            self.batch_status = {}
            self.batch_summary_text.value = message
            self.batch_summary_text.color = "#C62828"
            self.render_batch_rows()
            return

        self.batch_map = self.group_files_into_batches(self.target_directory)
        if not self.batch_map:
            self.batch_status = {}
            self.batch_summary_text.value = "Nenhum lote com prefixo de 5 dígitos foi encontrado."
            self.batch_summary_text.color = "#C62828"
            self.render_batch_rows()
            return

        json_prefixes: set[str] = set()
        for json_file in Path(self.target_directory).glob("*.json"):
            prefix = self.extract_batch_prefix(json_file.name)
            if prefix:
                json_prefixes.add(prefix)

        for batch_id in self.batch_map.keys():
            batch_session = self.get_batch_session(self.selected_collection_id, batch_id)
            uploaded_files = set(batch_session.get("uploaded_files", []))
            total_files = len(self.batch_map[batch_id])

            if total_files > 0 and len(uploaded_files) >= total_files:
                self.batch_status[batch_id] = "concluido"
            elif len(uploaded_files) > 0:
                self.batch_status[batch_id] = "parcial"
            else:
                self.batch_status[batch_id] = "pendente"

        visible = self.get_visible_batch_ids()
        if self.max_batches_to_show <= 0 and len(self.batch_map) > len(visible):
            self.batch_summary_text.value = (
                f"Lotes MD: {len(self.batch_map)} | Prefixos JSON: {len(json_prefixes)} | "
                f"Lotes exibidos: {len(visible)} (limite automático)"
            )
        else:
            self.batch_summary_text.value = (
                f"Lotes MD: {len(self.batch_map)} | Prefixos JSON: {len(json_prefixes)} | Lotes exibidos: {len(visible)}"
            )
        self.batch_summary_text.color = "#2E7D32"
        self.render_batch_rows()

    def format_batch_status(self, status: str) -> Tuple[str, str]:
        if status == "concluido":
            return "Concluído", "#2E7D32"
        if status == "parcial":
            return "Parcial", "#EF6C00"
        if status == "em_upload":
            return "Em upload", "#1565C0"
        if status == "falha":
            return "Falha", "#C62828"
        return "Pendente", "#616161"

    def render_batch_rows(self):
        if not self.batch_rows:
            return

        self.batch_buttons = {}
        controls: List[ft.Control] = []

        for batch_id in self.get_visible_batch_ids():
            files = self.batch_map.get(batch_id, [])
            status = self.batch_status.get(batch_id, "pendente")
            label, color = self.format_batch_status(status)
            batch_sequence = self.get_batch_sequence(batch_id)
            display_batch = f"{batch_sequence:02d}" if batch_sequence > 0 else batch_id
            seq_start, seq_end = self.get_batch_sequence_range(batch_id)
            prefix_start, prefix_end = self.get_batch_prefix_range(batch_id)

            batch_label_text = f"Lote {display_batch}"
            upload_button_text = f"Upload lote {display_batch}"
            if seq_start and seq_end:
                seq_text = f"Sequencial: {seq_start}-{seq_end}"
            else:
                seq_text = "Sequencial: -"

            if prefix_start and prefix_end:
                prefix_text = f"Prefixos: {prefix_start}-{prefix_end}"
            else:
                prefix_text = "Prefixos: -"

            button = ft.Button(
                content=ft.Row(
                    controls=cast(List[ft.Control], [ft.Icon(icon=ft.Icons.CLOUD_UPLOAD), ft.Text(value=upload_button_text)]),
                    tight=True,
                ),
                on_click=lambda e, b=batch_id: self.upload_batch_click(e, b),
                disabled=not self.is_ready_for_batch_upload() or bool(self.active_upload_batch),
                bgcolor="#2E7D32",
                color="#FFFFFF",
                width=220,
            )
            self.batch_buttons[batch_id] = button

            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(batch_label_text, width=180, weight=ft.FontWeight.BOLD),
                            ft.Column(
                                [
                                    ft.Text(seq_text, size=11, color="#616161"),
                                    ft.Text(prefix_text, size=11, color="#616161"),
                                ],
                                width=210,
                                spacing=2,
                            ),
                            ft.Text(f"Arquivos: {len(files)}", width=120),
                            ft.Container(
                                content=ft.Text(label, color="#FFFFFF", size=12),
                                bgcolor=color,
                                border_radius=15,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            ),
                            button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    border=ft.Border.all(1, "#E0E0E0"),
                    border_radius=8,
                    padding=10,
                )
            )

        if not controls:
            controls = [ft.Text("Nenhum lote para exibir.", color="#616161")]

        self.batch_rows.controls = controls
        self.safe_update_ui()

    def check_upload_button_state(self):
        self.render_batch_rows()

    def is_ready_for_batch_upload(self) -> bool:
        return bool(self.selected_collection_id and self.management_key and self.target_directory and self.log_directory)

    def upload_batch_click(self, e, batch_id: str):
        if not self.is_ready_for_batch_upload():
            self.show_snackbar(
                "Selecione pasta de arquivos, pasta de log, Management Key e Collection antes do upload.",
                success=False,
            )
            return
        self.run_task(self.upload_batch, batch_id)

    def set_all_batch_buttons_disabled(self, disabled: bool):
        for _, button in self.batch_buttons.items():
            button.disabled = disabled
        self.safe_update_ui()

    def collect_md_files(self, batch_id: str) -> List[str]:
        return sorted(self.batch_map.get(batch_id, []))

    def find_metadata_path(self, md_file: str) -> str:
        md_path = Path(md_file)
        return str(md_path.with_name(f"{md_path.stem}_metadata.json"))

    def read_metadata(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            self.log(f"❌ Erro ao ler metadados {os.path.basename(metadata_path)}: {str(exc)}")
            return None

    def normalize_metadata_fields(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in metadata.items():
            if value is None:
                normalized[key] = "não disponível"
                continue

            if isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
                normalized[key] = ", ".join(items) if items else "não disponível"
                continue

            if isinstance(value, dict):
                normalized[key] = json.dumps(value, ensure_ascii=False) if value else "não disponível"
                continue

            text_value = str(value).strip()
            normalized[key] = text_value if text_value else "não disponível"
        return normalized

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
        elif isinstance(data.get("collection"), dict):
            field_defs = cast(Dict[str, Any], data["collection"]).get("field_definitions")
        elif isinstance(data.get("data"), dict):
            field_defs = cast(Dict[str, Any], data["data"]).get("field_definitions")

        if not isinstance(field_defs, list):
            return []

        keys: List[str] = []
        for item in field_defs:
            if isinstance(item, dict) and "key" in item:
                keys.append(str(item["key"]))
        return keys

    def validate_metadata_keys(self, md_files: List[str], collection_keys: List[str]) -> Tuple[bool, List[str]]:
        expected = set(collection_keys)
        errors: List[str] = []

        for md_file in md_files:
            metadata_path = self.find_metadata_path(md_file)
            if not os.path.exists(metadata_path):
                errors.append(f"Metadados ausentes: {os.path.basename(metadata_path)}")
                continue

            metadata = self.read_metadata(metadata_path)
            if metadata is None:
                errors.append(f"Metadados inválidos: {os.path.basename(metadata_path)}")
                continue

            keys = set(metadata.keys())
            missing = expected - keys
            extra = keys - expected

            if missing or extra:
                missing_text = ", ".join(sorted(missing)) if missing else "-"
                extra_text = ", ".join(sorted(extra)) if extra else "-"
                errors.append(
                    f"Chaves divergentes em {os.path.basename(md_file)} (faltando: {missing_text}; extras: {extra_text})"
                )

        return len(errors) == 0, errors

    def sanitize_filename(self, text: str) -> str:
        text = re.sub(r"[<>:\"/\\|?*]", "", text)
        text = re.sub(r"[\s\-—]+", "_", text)
        return text[:100] or "document"

    def to_ascii_filename(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return self.sanitize_filename(ascii_text)

    async def upload_file_with_retry(
        self,
        md_file: str,
        collection_id: str,
        base_urls: List[str],
        headers: Dict[str, str],
        max_retries: int = 3,
    ) -> Tuple[bool, str, int, int]:
        metadata = self.read_metadata(self.find_metadata_path(md_file))
        if metadata is None:
            return False, "Metadados ausentes ou inválidos.", 0, 0

        normalized_metadata = self.normalize_metadata_fields(metadata)

        try:
            with open(md_file, "rb") as f:
                file_bytes = f.read()
        except Exception as exc:
            return False, f"Erro ao ler arquivo: {str(exc)}", 0, 0

        safe_basename = self.to_ascii_filename(os.path.basename(md_file))

        last_error = ""
        last_status = 0
        last_attempt = 0

        for base_url in base_urls:
            for attempt in range(1, max_retries + 1):
                last_attempt = attempt
                try:
                    data_payload = {
                        "name": safe_basename,
                        "content_type": "text/markdown",
                        "fields": json.dumps(normalized_metadata, ensure_ascii=False),
                    }

                    response = requests.post(
                        f"{base_url}/collections/{collection_id}/documents",
                        headers=headers,
                        data=data_payload,
                        files={"data": (safe_basename, file_bytes, "text/markdown")},
                        timeout=60,
                    )

                    if response.status_code in [200, 201]:
                        return True, "Upload realizado com sucesso.", attempt, response.status_code

                    last_status = response.status_code
                    last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                    if "cf-ipcity" in response.text and base_url != base_urls[-1]:
                        break

                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue

                    return False, last_error, attempt, response.status_code
                except Exception as exc:
                    last_error = str(exc)
                    last_status = 0
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return False, last_error, attempt, 0

        return False, last_error or "Falha desconhecida no upload.", last_attempt or max_retries, last_status

    def update_progress_ui(
        self,
        batch_id: str,
        processed: int,
        total: int,
        uploaded: int,
        failed: int,
        started_at: datetime,
    ):
        if not self.progress_bar or not self.progress_title or not self.progress_stats or not self.progress_eta:
            return

        percent = (processed / total) if total > 0 else 0
        elapsed = max((datetime.now() - started_at).total_seconds(), 1)
        rate = processed / elapsed
        remaining = max(total - processed, 0)
        eta_seconds = int(remaining / rate) if rate > 0 else 0

        self.progress_bar.visible = True
        self.progress_bar.value = percent
        self.progress_title.value = f"Lote {batch_id} em upload: {percent * 100:.1f}%"
        self.progress_stats.value = f"Processados: {processed}/{total} | Sucesso: {uploaded} | Falhas: {failed}"
        self.progress_eta.value = f"Tempo estimado restante: {eta_seconds // 60}m {eta_seconds % 60}s"
        self.safe_update_ui()

    async def upload_batch(self, batch_id: str):
        if not self.selected_collection_id:
            self.show_snackbar("Nenhuma Collection selecionada. Abra as configurações e escolha uma Collection.", success=False)
            return

        md_files = self.collect_md_files(batch_id)
        if not md_files:
            self.show_snackbar(f"Nenhum arquivo MD encontrado no lote {batch_id}.", success=False)
            return

        self.active_upload_batch = batch_id
        self.batch_status[batch_id] = "em_upload"
        self.render_batch_rows()
        self.set_all_batch_buttons_disabled(True)

        started_at = datetime.now()
        uploaded = 0
        failed = 0

        base_urls = ["https://management-api.x.ai/v1", "https://api.x.ai/v1"]
        headers = {"Authorization": f"Bearer {self.management_key}"}

        batch_session = self.get_batch_session(self.selected_collection_id, batch_id)
        previous_uploaded = set(batch_session.get("uploaded_files", []))
        skip_uploaded = bool(self.skip_uploaded_checkbox and self.skip_uploaded_checkbox.value)

        file_rows: List[Dict[str, Any]] = []
        files_to_process: List[str] = []

        for md_file in md_files:
            if skip_uploaded and md_file in previous_uploaded:
                file_rows.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "batch_id": batch_id,
                        "collection_id": self.selected_collection_id,
                        "arquivo": os.path.basename(md_file),
                        "status": "pulado",
                        "tentativas": 0,
                        "http_status": "",
                        "mensagem": "Arquivo já enviado em sessão anterior.",
                    }
                )
            else:
                files_to_process.append(md_file)

        if skip_uploaded and len(files_to_process) < len(md_files):
            self.log(f"ℹ️ Retomada de sessão: {len(md_files) - len(files_to_process)} arquivo(s) já enviado(s) serão pulados.")

        total_files = len(files_to_process)

        self.log("\n" + "=" * 70)
        self.log(f"☁️ Iniciando upload do lote {batch_id} para a collection {self.selected_collection_id}")

        try:
            schema = await self.fetch_collection_schema(self.selected_collection_id)
            if not schema:
                self.batch_status[batch_id] = "falha"
                self.show_snackbar("Erro ao validar schema da collection.", success=False)
                return

            collection_keys = self.extract_collection_keys(schema)
            if not collection_keys:
                self.batch_status[batch_id] = "falha"
                self.show_snackbar("Collection sem campos de metadados.", success=False)
                return

            valid, errors = self.validate_metadata_keys(files_to_process, collection_keys)
            if not valid:
                self.batch_status[batch_id] = "falha"
                self.log("❌ Validação de metadados falhou. Upload cancelado para este lote.")
                for error in errors[:10]:
                    self.log(f"   - {error}")
                if len(errors) > 10:
                    self.log(f"   ... e mais {len(errors) - 10} erro(s)")
                self.show_snackbar("Metadados incompatíveis com a collection.", success=False)
                return

            if total_files == 0:
                self.batch_status[batch_id] = "concluido"
                self.show_snackbar(f"Lote {batch_id} já estava concluído em sessão anterior.", success=True)
                return

            for index, md_file in enumerate(files_to_process, start=1):
                ok, msg, attempts, http_status = await self.upload_file_with_retry(
                    md_file=md_file,
                    collection_id=self.selected_collection_id,
                    base_urls=base_urls,
                    headers=headers,
                    max_retries=3,
                )

                if ok:
                    uploaded += 1
                    previous_uploaded.add(md_file)
                else:
                    failed += 1
                    self.log(f"❌ Falha no arquivo {os.path.basename(md_file)}: {msg}")

                file_rows.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "batch_id": batch_id,
                        "collection_id": self.selected_collection_id,
                        "arquivo": os.path.basename(md_file),
                        "status": "sucesso" if ok else "falha",
                        "tentativas": attempts,
                        "http_status": http_status,
                        "mensagem": msg,
                    }
                )

                self.update_progress_ui(batch_id, index, total_files, uploaded, failed, started_at)
                await asyncio.sleep(0.05)

            batch_session["uploaded_files"] = sorted(previous_uploaded)
            batch_session["failed_files"] = [r["arquivo"] for r in file_rows if r.get("status") == "falha"]
            batch_session["last_status"] = "concluido" if failed == 0 else "parcial"
            batch_session["last_updated"] = datetime.now().isoformat()
            self.save_session_state()

            batch_log = {
                "batch_id": batch_id,
                "collection_id": self.selected_collection_id,
                "inicio": started_at.isoformat(),
                "fim": datetime.now().isoformat(),
                "quantidade_arquivos_lote": len(md_files),
                "quantidade_processada": total_files,
                "sucesso": uploaded,
                "falhas": failed,
                "status_final": "concluido" if failed == 0 else "parcial",
                "arquivos": file_rows,
            }
            self.write_batch_log_json(batch_log)
            self.write_batch_log_csv(file_rows, batch_id)

            self.batch_status[batch_id] = "concluido" if failed == 0 else "parcial"
            self.log("=" * 70)
            self.log(f"✅ Lote {batch_id} concluído")
            self.log(f"   Arquivos no lote: {len(md_files)}")
            self.log(f"   Processados nesta execução: {total_files}")
            self.log(f"   Sucesso: {uploaded}")
            self.log(f"   Falhas: {failed}")
            self.log("=" * 70)

            self.show_snackbar(
                f"Upload do lote {batch_id} finalizado. Sucesso: {uploaded}, falhas: {failed}.",
                success=failed == 0,
            )

        except Exception as exc:
            self.batch_status[batch_id] = "falha"
            stack = traceback.format_exc()
            self.log(f"❌ Erro inesperado no lote {batch_id}: {str(exc)}")
            self.log(stack)
            self.write_batch_log_json(
                {
                    "batch_id": batch_id,
                    "collection_id": self.selected_collection_id,
                    "inicio": started_at.isoformat(),
                    "fim": datetime.now().isoformat(),
                    "status_final": "erro",
                    "erro": str(exc),
                    "stack_trace": stack,
                    "arquivos": file_rows,
                }
            )
            self.show_snackbar(f"Erro ao enviar lote {batch_id}. Verifique os logs.", success=False)

        finally:
            self.active_upload_batch = None
            if self.progress_bar:
                self.progress_bar.visible = False
                self.progress_bar.value = 0
            if self.progress_title:
                self.progress_title.value = "Upload inativo"
            if self.progress_stats:
                self.progress_stats.value = ""
            if self.progress_eta:
                self.progress_eta.value = ""

            self.refresh_batches()
            self.set_all_batch_buttons_disabled(False)
            self.safe_update_ui()

    def get_session_state_path(self) -> Optional[Path]:
        if not self.log_directory:
            return None
        return Path(self.log_directory) / self.session_state_file_name

    def get_collection_session(self, collection_id: str) -> Dict[str, Any]:
        uploads = self.session_state.setdefault("collection_uploads", {})
        key = collection_id or "__sem_collection__"
        if key not in uploads:
            uploads[key] = {"batches": {}}
        return cast(Dict[str, Any], uploads[key])

    def get_batch_session(self, collection_id: str, batch_id: str) -> Dict[str, Any]:
        collection_session = self.get_collection_session(collection_id)
        batches = collection_session.setdefault("batches", {})
        if batch_id not in batches:
            batches[batch_id] = {
                "uploaded_files": [],
                "failed_files": [],
                "last_status": "pendente",
                "last_updated": "",
            }
        return cast(Dict[str, Any], batches[batch_id])

    def load_session_state(self):
        state_path = self.get_session_state_path()
        if not state_path:
            return
        if not state_path.exists():
            self.session_state = {
                "version": 1,
                "updated_at": "",
                "collection_uploads": {},
            }
            return

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.session_state = data
                self.log("📌 Sessão anterior carregada com sucesso.")
        except Exception as exc:
            self.log(f"⚠️ Erro ao carregar sessão: {str(exc)}")

    def save_session_state(self):
        state_path = self.get_session_state_path()
        if not state_path:
            return

        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            self.session_state["updated_at"] = datetime.now().isoformat()
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(self.session_state, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self.log(f"⚠️ Erro ao salvar sessão: {str(exc)}")

    def write_batch_log_json(self, payload: Dict[str, Any]):
        if not self.log_directory:
            return
        try:
            Path(self.log_directory).mkdir(parents=True, exist_ok=True)
            file_name = f"upload_lote_{payload.get('batch_id', 'sem_lote')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(Path(self.log_directory) / file_name, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self.log(f"⚠️ Erro ao gravar log JSON: {str(exc)}")

    def write_batch_log_csv(self, rows: List[Dict[str, Any]], batch_id: str):
        if not self.log_directory:
            return

        try:
            Path(self.log_directory).mkdir(parents=True, exist_ok=True)
            file_name = Path(self.log_directory) / f"upload_lote_{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(file_name, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "timestamp",
                        "batch_id",
                        "collection_id",
                        "arquivo",
                        "status",
                        "tentativas",
                        "http_status",
                        "mensagem",
                    ],
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        except Exception as exc:
            self.log(f"⚠️ Erro ao gravar log CSV: {str(exc)}")

    def run_task(self, async_fn, *args):
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(async_fn, *args)
            else:
                asyncio.create_task(async_fn(*args))
        except Exception:
            pass

    def safe_update_ui(self):
        try:
            self.page.update()
        except Exception as exc:
            print(f"[CollectionUploaderV3] Erro em page.update(): {exc}")
            pass

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        if self.feedback_text:
            self.feedback_text.value += line
            self.safe_update_ui()

    def clear_log(self):
        if self.feedback_text:
            self.feedback_text.value = ""
            self.safe_update_ui()

    def show_snackbar(self, message: str, success: bool = True):
        color = "#2E7D32" if success else "#C62828"
        snack = ft.SnackBar(ft.Text(message))
        snack.bgcolor = color

        show_fn = getattr(self.page, "show_snack_bar", None)
        if callable(show_fn):
            show_fn(snack)
            return

        try:
            setattr(self.page, "snack_bar", snack)
            getattr(self.page, "snack_bar").open = True
            self.safe_update_ui()
        except Exception:
            pass


def main(page: ft.Page):
    CollectionUploaderV3(page)


if __name__ == "__main__":
    def _force_exit_on_sigint(signum, frame):
        os._exit(130)

    try:
        signal.signal(signal.SIGINT, _force_exit_on_sigint)
    except Exception:
        pass

    ft.run(main)
