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
from typing import Dict, List, Optional, Any, cast
from datetime import datetime
import pyperclip


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
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def list_collections(self) -> List[Dict]:
        """Lista todas as Collections disponíveis."""
        if not self.management_key:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{self.base_url}/collections",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("collections", [])
        except Exception as e:
            print(f"Erro ao listar collections: {e}")
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
        
        self.page.title = "Busca de Precedentes Trabalhistas"
        self.page.theme_mode = ft.ThemeMode.DARK if self.config_manager.get("theme_dark") else ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        self.update_xai_client()
        self.create_ui()
    
    def update_xai_client(self):
        """Atualiza o cliente xAI."""
        api_key = str(self.config_manager.get("api_key") or "")
        management_key = str(self.config_manager.get("management_key") or "")
        if api_key:
            self.xai_client = XAIClient(api_key, management_key)
    
    def create_ui(self):
        """Cria a interface do usuário."""
        # Toolbar
        self.toolbar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=cast(Any, "delete_sweep"),
                    tooltip="Limpar chat",
                    on_click=self.clear_chat
                ),
                ft.IconButton(
                    icon=cast(Any, "copy_all"),
                    tooltip="Copiar chat",
                    on_click=self.copy_chat
                ),
                ft.IconButton(
                    icon=cast(Any, "attach_file"),
                    tooltip="Anexar arquivo",
                    on_click=self.attach_file
                ),
                ft.IconButton(
                    icon=cast(Any, "settings"),
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
            hint_text="Selecione uma Collection",
            options=[],
            on_blur=self.on_collection_changed,
            expand=True,
        )
        
        self.collection_search_toggle = ft.Switch(
            label="Buscar na Collection",
            value=False,
        )
        
        # Input
        self.message_input = ft.TextField(
            hint_text="Digite sua pergunta...",
            multiline=True,
            min_lines=2,
            max_lines=5,
            expand=True,
            on_submit=self.send_message_click,
        )
        
        self.send_button = ft.ElevatedButton(
            content=ft.Row([ft.Icon(icon=cast(Any, "send")), ft.Text("Enviar")], tight=True),
            on_click=self.send_message_click,
        )
        
        # Layouts
        input_area = ft.Row(
            controls=[self.message_input, self.send_button],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        collection_controls = ft.Row(
            controls=[self.collection_dropdown, self.collection_search_toggle],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        main_layout = ft.Column(
            controls=[
                ft.Container(content=self.toolbar, bgcolor="#333333", padding=10),
                self.chat_container,
                ft.Divider(height=1),
                ft.Container(content=collection_controls, padding=10),
                ft.Container(content=input_area, padding=10),
            ],
            expand=True,
        )
        
        self.page.add(main_layout)
        self.refresh_collections()
        self.add_system_message("👨‍⚖️ **Sistema de Busca de Precedentes Trabalhistas**")
    
    def refresh_collections(self):
        """Atualiza collections."""
        if not self.xai_client:
            return
        
        collections = self.xai_client.list_collections()
        self.collection_dropdown.options = [
            ft.dropdown.Option(key=str(col["id"]), text=str(col.get("name", col["id"])))
            for col in collections
        ]
        
        selected_id = self.config_manager.get("selected_collection_id")
        if selected_id and any(opt.key == selected_id for opt in self.collection_dropdown.options):
            self.collection_dropdown.value = str(selected_id)
        
        self.page.update()
    
    def on_collection_changed(self, e):
        """Callback quando a collection é alterada."""
        self.config_manager.set("selected_collection_id", self.collection_dropdown.value)
    
    def add_message(self, content: str, is_user: bool = True):
        """Adiciona mensagem ao chat."""
        row_controls = [
            ft.Icon(icon=cast(Any, "person" if is_user else "smart_toy"), size=20),
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
        file_picker = ft.FilePicker()
        self.page.overlay.append(file_picker)
        self.page.update()
        
        try:
            files = await file_picker.pick_files(allow_multiple=True)
            if files:
                for file in files:
                    if file.path:
                        self.attached_files.append(str(file.path))
                        self.add_system_message(f"📎 Arquivo anexado: {file.name}")
                self.page.update()
        except Exception as ex:
            print(f"Erro ao anexar arquivo: {ex}")
        finally:
            self.page.overlay.remove(file_picker)
            self.page.update()
    
    def build_tools(self) -> Optional[List[Dict]]:
        """Constrói as ferramentas da API."""
        if not self.collection_search_toggle.value or not self.collection_dropdown.value:
            return None
        return [{
            "type": "collection_search",
            "collection_id": str(self.collection_dropdown.value),
            "search_parameters": {"search_type": "hybrid", "top_k": 5}
        }]
    
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
        
        messages.extend(self.messages)
        messages.append({"role": "user", "content": user_message})
        self.messages.append({"role": "user", "content": user_message})
        
        loading = ft.ProgressBar()
        self.chat_container.controls.append(loading)
        self.page.update()
        
        try:
            if not self.xai_client: raise Exception("Cliente não inicializado")
            response = self.xai_client.chat_completion(
                messages=messages,
                model=str(self.config_manager.get("model") or "grok-2-1212"),
                temperature=float(self.config_manager.get("temperature") or 0.7),
                tools=self.build_tools(),
            )
            ans = str(response["choices"][0]["message"]["content"])
            self.add_message(ans, is_user=False)
            self.messages.append({"role": "assistant", "content": ans})
        except Exception as ex:
            self.add_system_message(f"❌ Erro: {ex}")
        finally:
            self.chat_container.controls.remove(loading)
            self.page.update()
    
    def open_settings(self, e):
        """Abre o diálogo de configurações."""
        m_key = ft.TextField(label="Management Key", value=str(self.config_manager.get("management_key") or ""), password=True, can_reveal_password=True)
        a_key = ft.TextField(label="API Key", value=str(self.config_manager.get("api_key") or ""), password=True, can_reveal_password=True)
        model = ft.Dropdown(label="Modelo", value=str(self.config_manager.get("model") or "grok-2-1212"), options=[
            ft.dropdown.Option("grok-2-1212"), ft.dropdown.Option("grok-2-vision-1212"), ft.dropdown.Option("grok-beta")
        ])
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
            content=ft.Column([m_key, a_key, model, ft.Text("Temperature:"), temp, sys_p, theme], scroll=ft.ScrollMode.AUTO, height=400),
            actions=[ft.ElevatedButton(content=ft.Text("Salvar"), on_click=save)]
        )
        self.open_dialog(dlg)

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
    ft.app(target=main)
