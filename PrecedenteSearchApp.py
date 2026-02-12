#!/usr/bin/env python3
"""
PrecedenteSearchApp.py
Aplicação Flet para busca semântica de precedentes trabalhistas usando xAI Collections.
"""

import flet as ft
import json
import requests
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pyperclip
import tkinter as tk
from tkinter import filedialog


class ConfigManager:
    """Gerenciador de configurações da aplicação."""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = Path(config_file)
        self.default_config = {
            "management_key": "",
            "api_key": "",
            "model": "grok-2-1212",
            "temperature": 0.7,
            "system_prompt": "Você é um assistente jurídico especializado em Direito do Trabalho brasileiro. Analise precedentes e fundamente respostas com base na CLT, jurisprudência e doutrina trabalhista.",
            "theme_dark": True,
            "selected_collection_id": ""
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Carrega configurações do arquivo."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    return {**self.default_config, **loaded}
            except Exception as e:
                print(f"Erro ao carregar config: {e}")
        return self.default_config.copy()
    
    def save_config(self) -> None:
        """Salva configurações no arquivo."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Define valor de configuração."""
        self.config[key] = value
        self.save_config()


class XAIClient:
    """Cliente para comunicação com xAI API."""
    
    def __init__(self, api_key: str, management_key: str = ""):
        self.api_key = api_key
        self.management_key = management_key
        self.base_url = "https://api.x.ai/v1"
        self.last_collections_error = ""
        self.last_models_error = ""
        self.last_search_error = ""
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def list_collections(self) -> List[Dict]:
        """Lista todas as Collections disponíveis."""
        if not self.management_key:
            self.last_collections_error = "Management Key não configurada."
            return []

        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}",
                "Content-Type": "application/json"
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
                    use_headers = "management-api" in url
                    response = requests.get(
                        url,
                        headers=headers if use_headers else {},
                        timeout=15
                    )

                    if response.status_code != 200:
                        last_error = f"{response.status_code}: {response.text[:200]}"
                        continue

                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict):
                        if isinstance(data.get("data"), list):
                            return data["data"]
                        if isinstance(data.get("collections"), list):
                            return data["collections"]
                    last_error = "Formato de resposta não reconhecido"
                except Exception as ex:
                    last_error = str(ex)
                    continue

            if response:
                self.last_collections_error = last_error or f"{response.status_code}: {response.text[:200]}"
            else:
                self.last_collections_error = last_error or "Nenhum endpoint funcionou"
            print(f"Erro ao listar collections: {self.last_collections_error}")
            return []
        except Exception as e:
            self.last_collections_error = str(e)
            print(f"Erro ao listar collections: {e}")
            return []

    def list_models(self) -> List[str]:
        """Lista modelos disponíveis."""
        if not self.api_key:
            self.last_models_error = "API Key não configurada."
            return []

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            if response.status_code != 200:
                self.last_models_error = f"{response.status_code}: {response.text[:200]}"
                return []

            data = response.json()
            models = data.get("data", []) if isinstance(data, dict) else []
            model_ids = [str(m["id"]) for m in models if isinstance(m, dict) and m.get("id") is not None]
            return model_ids
        except Exception as e:
            self.last_models_error = str(e)
            return []

    def search_documents(self, query: str, collection_id: str) -> List[Dict[str, Any]]:
        """Busca documentos em uma collection usando busca semantica."""
        if not self.api_key:
            self.last_search_error = "API Key não configurada."
            return []

        try:
            payload = {
                "query": query,
                "source": {"collection_ids": [collection_id]},
                "retrieval_mode": {"type": "semantic"},
            }
            response = requests.post(
                f"{self.base_url}/documents/search",
                headers=self.headers,
                json=payload,
                timeout=20,
            )
            if response.status_code != 200:
                self.last_search_error = f"{response.status_code}: {response.text[:200]}"
                return []

            data = response.json()
            if isinstance(data, dict):
                if isinstance(data.get("data"), list):
                    return data["data"]
                if isinstance(data.get("results"), list):
                    return data["results"]
                nested = data.get("data")
                if isinstance(nested, dict):
                    if isinstance(nested.get("results"), list):
                        return nested["results"]
                self.last_search_error = f"Formato de resposta nao reconhecido (keys: {list(data.keys())})."
                return []
            if isinstance(data, list):
                return data
            self.last_search_error = f"Formato de resposta nao reconhecido (type: {type(data)})."
            return []
        except Exception as e:
            self.last_search_error = str(e)
            return []
    
    def chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Any:
        """Envia requisição de chat completion para a API."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if tools:
            payload["tools"] = tools
        
        if stream:
            payload["stream"] = True
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return response
            else:
                return response.json()
        except Exception as e:
            raise Exception(f"Erro na requisição: {str(e)}")


class PrecedenteSearchApp:
    """Aplicação principal de busca de precedentes."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_manager = ConfigManager()
        self.xai_client: Optional[XAIClient] = None
        self.messages: List[Dict] = []
        self.attached_files: List[str] = []
        self.available_models: List[str] = []
        
        self.page.title = "Busca de Precedentes Trabalhistas"
        self.page.theme_mode = ft.ThemeMode.DARK if self.config_manager.get("theme_dark") else ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        self.update_xai_client()
        self.create_ui()
        self.schedule_startup_refresh()

    def schedule_startup_refresh(self):
        """Agenda o refresh inicial das collections."""
        try:
            if hasattr(self.page, "run_task"):
                self.page.run_task(self.refresh_on_startup)
            else:
                asyncio.create_task(self.refresh_on_startup())
        except Exception:
            pass

    async def refresh_on_startup(self):
        """Atualiza collections no startup após a UI estar pronta."""
        await asyncio.sleep(0.2)
        self.refresh_collections()
    
    def update_xai_client(self):
        """Atualiza o cliente xAI."""
        api_key = str(self.config_manager.get("api_key") or "")
        management_key = str(self.config_manager.get("management_key") or "")
        if api_key or management_key:
            self.xai_client = XAIClient(api_key, management_key)
        else:
            self.xai_client = None
    
    def create_ui(self):
        """Cria a interface do usuário."""
        # Toolbar
        self.toolbar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.DELETE_SWEEP,
                    tooltip="Limpar chat",
                    on_click=self.clear_chat
                ),
                ft.IconButton(
                    icon=ft.Icons.COPY_ALL,
                    tooltip="Copiar chat",
                    on_click=self.copy_chat
                ),
                ft.IconButton(
                    icon=ft.Icons.ATTACH_FILE,
                    tooltip="Anexar arquivo",
                    on_click=self.attach_file
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Configurações",
                    on_click=self.open_settings
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        
        # Chat
        self.chat_container = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True,
        )
        
        # Collection selection
        self.collection_dropdown = ft.Dropdown(
            label="Collection",
            options=[],
            on_select=self.on_collection_changed,
            on_blur=self.on_collection_changed,
            expand=True,
        )

        self.collection_refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Atualizar collections",
            on_click=self.refresh_collections_click,
        )

        self.collection_search_toggle = ft.Switch(
            label="Buscar na collection",
            value=True,
        )

        self.collection_status_text = ft.Text("", size=12, color="grey")
        
        
        # Input
        self.message_input = ft.TextField(
            multiline=True,
            min_lines=2,
            max_lines=5,
            expand=True,
            on_submit=self.send_message_click,
        )
        
        self.send_button = ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.SEND), ft.Text("Enviar")], tight=True),
            on_click=self.send_message_click,
        )

        self.response_status_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        self.response_status_text = ft.Text("", size=12, color="grey")
        self.response_status_row = ft.Row(
            controls=[self.response_status_ring, self.response_status_text],
            spacing=6,
        )
        
        # Layouts
        input_area = ft.Row(
            controls=[self.message_input, self.send_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        collection_controls = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.collection_dropdown, self.collection_refresh_button, self.collection_search_toggle],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.collection_status_text,
            ],
            spacing=5,
        )
        
        main_layout = ft.Column(
            controls=[
                ft.Container(content=self.toolbar, bgcolor="#333333", padding=10),
                self.chat_container,
                ft.Divider(height=1),
                ft.Container(content=collection_controls, padding=10),
                ft.Container(content=input_area, padding=10),
                ft.Container(content=self.response_status_row, padding=10),
            ],
            expand=True,
        )
        
        self.page.add(main_layout)
        self.add_system_message("👨‍⚖️ **Sistema de Busca de Precedentes Trabalhistas**")
    
    def refresh_collections(self):
        """Atualiza collections."""
        if not self.xai_client:
            self.collection_status_text.value = "Configure a Management Key para carregar collections."
            self.page.update()
            return
        
        collections = self.xai_client.list_collections()
        options = []
        for col in collections:
            if not isinstance(col, dict):
                continue
            col_id = col.get("id") or col.get("collection_id") or col.get("collectionId")
            if not col_id:
                continue
            col_name = col.get("name") or col.get("collection_name") or col_id
            options.append(ft.dropdown.Option(key=str(col_id), text=str(col_name)))

        self.collection_dropdown.options = options
        if not options:
            error_msg = self.xai_client.last_collections_error or "Nenhuma collection retornada pela API."
            self.add_system_message(f"⚠️ Não foi possível carregar collections: {error_msg}")
            self.collection_status_text.value = f"Falha ao carregar: {error_msg}"
        else:
            self.collection_status_text.value = f"Collections carregadas: {len(options)}"
        
        selected_id = self.config_manager.get("selected_collection_id")
        if selected_id and any(opt.key == selected_id for opt in self.collection_dropdown.options):
            self.collection_dropdown.value = str(selected_id)
        
        self.page.update()

    def refresh_collections_click(self, e):
        """Callback para botão de atualizar collections."""
        self.update_xai_client()
        self.refresh_collections()

    def refresh_models(self, model_dropdown: ft.Dropdown, status_text: ft.Text):
        """Atualiza a lista de modelos na UI de configurações."""
        if not self.xai_client:
            status_text.value = "Configure a API Key para carregar modelos."
            self.page.update()
            return

        model_ids = self.xai_client.list_models()
        self.available_models = model_ids

        if not model_ids:
            error_msg = self.xai_client.last_models_error or "Nenhum modelo retornado pela API."
            status_text.value = f"Falha ao carregar: {error_msg}"
            model_dropdown.options = []
            model_dropdown.value = ""
            self.page.update()
            return

        model_dropdown.options = [ft.dropdown.Option(mid) for mid in model_ids]
        current_model = str(self.config_manager.get("model") or "")
        if current_model in model_ids:
            model_dropdown.value = current_model
        else:
            model_dropdown.value = model_ids[0]
        status_text.value = f"Modelos carregados: {len(model_ids)}"
        self.page.update()
    
    def on_collection_changed(self, e):
        """Callback quando a collection é alterada."""
        self.config_manager.set("selected_collection_id", self.collection_dropdown.value)
    
    def add_message(self, content: str, is_user: bool = True):
        """Adiciona mensagem ao chat."""
        row_controls = [
            ft.Icon(ft.Icons.PERSON if is_user else ft.Icons.SMART_TOY, size=20),
            ft.Text("Você" if is_user else "Grok", weight=ft.FontWeight.BOLD, size=14),
            ft.Text(datetime.now().strftime("%H:%M"), size=12, color="grey"),
        ]
        message_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row(controls=row_controls),
                    ft.Markdown(content, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB),
                ]),
                padding=15,
            ),
            elevation=2,
        )
        self.chat_container.controls.append(message_card)
        self.page.update()
    
    def add_system_message(self, content: str):
        """Adiciona mensagem do sistema."""
        system_card = ft.Card(
            content=ft.Container(
                content=ft.Markdown(content, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB),
                padding=15,
                bgcolor="#1a1a1a" if self.config_manager.get("theme_dark") else "#f0f0f0",
            ),
            elevation=1,
        )
        self.chat_container.controls.append(system_card)
        self.page.update()
    
    def clear_chat(self, e):
        """Limpa o chat."""
        self.chat_container.controls.clear()
        self.messages.clear()
        self.attached_files.clear()
        self.add_system_message("🔄 Chat resetado.")
        self.page.update()
    
    def copy_chat(self, e):
        """Copia chat para o clipboard."""
        chat_text = [f"[{'USUÁRIO' if msg['role'] == 'user' else 'GROK'}]\n{msg['content']}\n" for msg in self.messages]
        try:
            pyperclip.copy("\n".join(chat_text))
            self.add_system_message("✅ Chat copiado!")
        except Exception as ex:
            self.add_system_message(f"❌ Erro ao copiar: {ex}")
    
    async def attach_file(self, e):
        """Anexa um arquivo."""
        # Criar janela tkinter temporária e trazer para frente
        def open_file_dialog():
            root = tk.Tk()
            root.withdraw()  # Esconder janela principal
            root.attributes('-topmost', True)  # Trazer para frente
            root.lift()
            root.focus_force()
            files = filedialog.askopenfilenames(
                parent=root,
                title="Selecione os arquivos para anexar",
                filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
            )
            root.destroy()
            return files
        
        try:
            # Usar tkinter filedialog em thread separada para não bloquear
            files = await asyncio.to_thread(open_file_dialog)
            
            if files:
                for file_path in files:
                    if file_path:
                        self.attached_files.append(str(file_path))
                        file_name = os.path.basename(file_path)
                        self.add_system_message(f"📎 Arquivo anexado: {file_name}")
                self.page.update()
        except Exception as ex:
            print(f"Erro ao anexar arquivo: {ex}")
            self.add_system_message(f"❌ Erro ao anexar arquivo: {ex}")
    
    async def send_message_click(self, e):
        """Ponte para chamada async."""
        await self.send_message(e)

    async def send_message(self, e):
        """Envia uma mensagem."""
        user_message = str(self.message_input.value or "").strip()
        if not user_message or not self.config_manager.get("api_key"):
            return
        
        self.add_message(user_message, is_user=True)
        self.message_input.value = ""
        self.page.update()
        
        messages = [{"role": "system", "content": str(self.config_manager.get("system_prompt") or "")}]
        if self.attached_files:
            ctx = "Arquivos anexados:\n"
            for f in self.attached_files:
                try:
                    with open(f, 'r', encoding='utf-8') as f_content:
                        ctx += f"\n--- {Path(f).name} ---\n{f_content.read()[:5000]}\n"
                except Exception: pass
            messages.append({"role": "system", "content": ctx})

        collection_id = str(self.collection_dropdown.value or "")
        if self.collection_search_toggle.value and self.xai_client and collection_id:
            results = self.xai_client.search_documents(user_message, collection_id)
            if results:
                snippets = []
                for idx, item in enumerate(results[:5], start=1):
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content") or item.get("text") or item.get("snippet") or ""
                    title = item.get("name") or item.get("title") or item.get("document_id") or f"Documento {idx}"
                    content = str(content).strip()
                    if content:
                        snippets.append(f"[{idx}] {title}\n{content[:1200]}")
                if snippets:
                    search_ctx = "Resultados da busca semantica na collection selecionada:\n\n" + "\n\n".join(snippets)
                    messages.append({"role": "system", "content": search_ctx})
            else:
                if self.xai_client.last_search_error:
                    self.add_system_message(f"⚠️ Busca semantica falhou: {self.xai_client.last_search_error}")
        
        messages.extend(self.messages)
        messages.append({"role": "user", "content": user_message})
        self.messages.append({"role": "user", "content": user_message})
        
        loading = ft.ProgressBar()
        self.chat_container.controls.append(loading)
        self.response_status_text.value = "Consultando o modelo..."
        self.response_status_ring.visible = True
        self.page.update()
        
        try:
            if not self.xai_client:
                raise Exception("Cliente não inicializado")

            response = self.xai_client.chat_completion(
                messages=messages,
                model=str(self.config_manager.get("model") or "grok-2-1212"),
                temperature=float(self.config_manager.get("temperature") or 0.7),
            )
            ans = str(response["choices"][0]["message"]["content"])
            self.add_message(ans, is_user=False)
            self.messages.append({"role": "assistant", "content": ans})
        except Exception as ex:
            self.add_system_message(f"❌ Erro: {ex}")
        finally:
            self.chat_container.controls.remove(loading)
            self.response_status_text.value = ""
            self.response_status_ring.visible = False
            self.page.update()
    
    def open_settings(self, e):
        """Abre o diálogo de configurações."""
        m_key = ft.TextField(label="Management Key", value=str(self.config_manager.get("management_key") or ""), password=True, can_reveal_password=True)
        a_key = ft.TextField(label="API Key", value=str(self.config_manager.get("api_key") or ""), password=True, can_reveal_password=True)
        model = ft.Dropdown(label="Modelo", value=str(self.config_manager.get("model") or ""), options=[])
        model_status = ft.Text("Clique para atualizar modelos.", size=12, color="grey")
        refresh_models_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Atualizar modelos",
            on_click=lambda e: self.refresh_models(model, model_status),
        )
        temp = ft.Slider(min=0, max=2, divisions=20, value=float(self.config_manager.get("temperature") or 0.7), label="Temp: {value}")
        sys_p = ft.TextField(label="System Prompt", value=str(self.config_manager.get("system_prompt") or ""), multiline=True)
        theme = ft.Switch(label="Tema Escuro", value=bool(self.config_manager.get("theme_dark")))
        
        def save(e):
            self.config_manager.set("management_key", m_key.value)
            self.config_manager.set("api_key", a_key.value)
            self.config_manager.set("model", model.value)
            self.config_manager.set("temperature", temp.value)
            self.config_manager.set("system_prompt", sys_p.value)
            self.config_manager.set("theme_dark", theme.value)
            self.update_xai_client()
            self.page.theme_mode = ft.ThemeMode.DARK if theme.value else ft.ThemeMode.LIGHT
            self.refresh_collections()
            self.close_dialog(dlg)
            self.page.update()
            
        dlg = ft.AlertDialog(
            title=ft.Text("Configurações"),
            content=ft.Column([m_key, a_key, ft.Row([model, refresh_models_button], spacing=10), model_status, ft.Text("Temperature:"), temp, sys_p, theme], scroll=ft.ScrollMode.AUTO, height=400),
            actions=[ft.ElevatedButton(content=ft.Text("Salvar"), on_click=save)]
        )
        self.open_dialog(dlg)
        self.update_xai_client()
        self.refresh_models(model, model_status)

    def open_dialog(self, dlg):
        """Abre o diálogo."""
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def close_dialog(self, dlg):
        """Fecha o diálogo."""
        dlg.open = False
        self.page.update()


def main(page: ft.Page):
    PrecedenteSearchApp(page)

if __name__ == "__main__":
    ft.run(main)
