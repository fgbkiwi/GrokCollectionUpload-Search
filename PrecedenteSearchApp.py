#!/usr/bin/env python3
"""
PrecedenteSearchApp.py
Aplicação Flet para busca semântica de precedentes trabalhistas usando xAI Collections.

Funcionalidades:
- Interface gráfica para interação com modelo Grok
- Busca híbrida em xAI Collections com filtros de metadados
- Configurações persistentes (API keys, modelo, temperature)
- Anexar arquivos ao contexto do chat
- Copiar chat completo para clipboard
- Suporte a busca em tempo real (Web e X)
- Tema claro/escuro

Uso:
    python PrecedenteSearchApp.py
"""

import flet as ft
import json
import requests
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
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
            "realtime_web_search": False,
            "realtime_x_search": False,
            "url_citation": True,
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
                    # Merge com defaults para garantir todas as chaves
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
    ) -> Dict:
        """
        Envia requisição de chat completion para a API.
        
        Args:
            messages: Lista de mensagens do chat
            model: Modelo a ser usado
            temperature: Temperatura para geração
            tools: Lista de ferramentas disponíveis
            stream: Se deve usar streaming
            
        Returns:
            Resposta da API
        """
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
                return response  # Retorna objeto response para streaming
            else:
                return response.json()
        except Exception as e:
            raise Exception(f"Erro na requisição: {str(e)}")


class PrecedenteSearchApp:
    """Aplicação principal de busca de precedentes."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_manager = ConfigManager()
        self.xai_client = None
        self.messages = []  # Histórico de mensagens
        self.attached_files = []  # Arquivos anexados
        
        # Configuração da página
        self.page.title = "Busca de Precedentes Trabalhistas"
        self.page.theme_mode = ft.ThemeMode.DARK if self.config_manager.get("theme_dark") else ft.ThemeMode.LIGHT
        self.page.padding = 0
        
        # Inicializa cliente xAI
        self.update_xai_client()
        
        # Cria interface
        self.create_ui()
    
    def update_xai_client(self):
        """Atualiza o cliente xAI com as credenciais atuais."""
        api_key = self.config_manager.get("api_key")
        management_key = self.config_manager.get("management_key")
        if api_key:
            self.xai_client = XAIClient(api_key, management_key)
    
    def create_ui(self):
        """Cria a interface do usuário."""
        # Barra de ferramentas
        self.toolbar = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.icons.DELETE_SWEEP,
                    tooltip="Limpar chat",
                    on_click=self.clear_chat
                ),
                ft.IconButton(
                    icon=ft.icons.COPY_ALL,
                    tooltip="Copiar chat",
                    on_click=self.copy_chat
                ),
                ft.IconButton(
                    icon=ft.icons.ATTACH_FILE,
                    tooltip="Anexar arquivo",
                    on_click=self.attach_file
                ),
                ft.IconButton(
                    icon=ft.icons.SETTINGS,
                    tooltip="Configurações",
                    on_click=self.open_settings
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        
        # Área de mensagens (chat)
        self.chat_container = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True,
        )
        
        # Dropdown de Collections
        self.collection_dropdown = ft.Dropdown(
            label="Collection",
            hint_text="Selecione uma Collection",
            options=[],
            on_change=self.on_collection_changed,
            expand=True,
        )
        
        # Toggle para habilitar busca na Collection
        self.collection_search_toggle = ft.Switch(
            label="Buscar na Collection",
            value=False,
            on_change=self.on_collection_toggle_changed,
        )
        
        # Campo de entrada de mensagem
        self.message_input = ft.TextField(
            hint_text="Digite sua pergunta sobre precedentes trabalhistas...",
            multiline=True,
            min_lines=2,
            max_lines=5,
            expand=True,
            on_submit=self.send_message,
        )
        
        # Botão de enviar
        self.send_button = ft.ElevatedButton(
            text="Enviar",
            icon=ft.icons.SEND,
            on_click=self.send_message,
        )
        
        # Área de entrada
        input_area = ft.Row(
            controls=[
                self.message_input,
                self.send_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Collection controls
        collection_controls = ft.Row(
            controls=[
                self.collection_dropdown,
                self.collection_search_toggle,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Layout principal
        main_layout = ft.Column(
            controls=[
                ft.Container(
                    content=self.toolbar,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    padding=10,
                ),
                self.chat_container,
                ft.Divider(height=1),
                ft.Container(
                    content=collection_controls,
                    padding=10,
                ),
                ft.Container(
                    content=input_area,
                    padding=10,
                ),
            ],
            expand=True,
        )
        
        self.page.add(main_layout)
        
        # Carrega collections disponíveis
        self.refresh_collections()
        
        # Adiciona mensagem de boas-vindas
        self.add_system_message(
            "👨‍⚖️ **Sistema de Busca de Precedentes Trabalhistas**\n\n"
            "Bem-vindo, Vossa Excelência! Este sistema permite buscar precedentes "
            "nas sentenças indexadas usando busca semântica com xAI Collections.\n\n"
            "**Como usar:**\n"
            "1. Configure suas credenciais em ⚙️ Configurações\n"
            "2. Selecione uma Collection no menu suspenso\n"
            "3. Habilite 'Buscar na Collection' para usar busca semântica\n"
            "4. Digite sua consulta jurídica\n\n"
            "O sistema buscará precedentes relevantes e fornecerá fundamentação baseada nas suas sentenças."
        )
    
    def refresh_collections(self):
        """Atualiza lista de Collections disponíveis."""
        if not self.xai_client:
            return
        
        collections = self.xai_client.list_collections()
        self.collection_dropdown.options = [
            ft.dropdown.Option(key=col["id"], text=col.get("name", col["id"]))
            for col in collections
        ]
        
        # Restaura seleção anterior se disponível
        selected_id = self.config_manager.get("selected_collection_id")
        if selected_id and any(opt.key == selected_id for opt in self.collection_dropdown.options):
            self.collection_dropdown.value = selected_id
        
        self.page.update()
    
    def on_collection_changed(self, e):
        """Callback quando Collection é selecionada."""
        self.config_manager.set("selected_collection_id", self.collection_dropdown.value)
    
    def on_collection_toggle_changed(self, e):
        """Callback quando toggle de busca é alterado."""
        pass  # Nada a fazer aqui, valor é lido ao enviar mensagem
    
    def add_message(self, content: str, is_user: bool = True):
        """
        Adiciona mensagem ao chat.
        
        Args:
            content: Conteúdo da mensagem
            is_user: Se é mensagem do usuário ou do assistente
        """
        message_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(
                            name=ft.icons.PERSON if is_user else ft.icons.SMART_TOY,
                            size=20,
                        ),
                        ft.Text(
                            "Você" if is_user else "Grok",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                        ft.Text(
                            datetime.now().strftime("%H:%M"),
                            size=12,
                            color=ft.colors.GREY,
                        ),
                    ]),
                    ft.Markdown(
                        content,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
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
                content=ft.Markdown(
                    content,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
                padding=15,
                bgcolor=ft.colors.BLUE_GREY_900 if self.config_manager.get("theme_dark") else ft.colors.BLUE_GREY_100,
            ),
            elevation=1,
        )
        
        self.chat_container.controls.append(system_card)
        self.page.update()
    
    def clear_chat(self, e):
        """Limpa o histórico do chat."""
        self.chat_container.controls.clear()
        self.messages.clear()
        self.attached_files.clear()
        self.add_system_message("🔄 Chat resetado. Histórico limpo.")
        self.page.update()
    
    def copy_chat(self, e):
        """Copia todo o chat para o clipboard."""
        chat_text = []
        for msg in self.messages:
            role = "USUÁRIO" if msg["role"] == "user" else "GROK"
            chat_text.append(f"[{role}]\n{msg['content']}\n")
        
        full_text = "\n".join(chat_text)
        try:
            pyperclip.copy(full_text)
            self.add_system_message("✅ Chat copiado para o clipboard!")
        except Exception as ex:
            self.add_system_message(f"❌ Erro ao copiar: {str(ex)}")
    
    def attach_file(self, e):
        """Abre diálogo para anexar arquivo."""
        def on_file_selected(e: ft.FilePickerResultEvent):
            if e.files:
                for file in e.files:
                    self.attached_files.append(file.path)
                    self.add_system_message(f"📎 Arquivo anexado: {file.name}")
        
        file_picker = ft.FilePicker(on_result=on_file_selected)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(allow_multiple=True)
    
    def build_tools(self) -> Optional[List[Dict]]:
        """
        Constrói lista de tools para a API, incluindo Collection Search Tool se habilitado.
        
        Returns:
            Lista de ferramentas ou None
        """
        if not self.collection_search_toggle.value:
            return None
        
        collection_id = self.collection_dropdown.value
        if not collection_id:
            return None
        
        # Collection Search Tool conforme documentação xAI
        tools = [
            {
                "type": "collection_search",
                "collection_id": collection_id,
                "search_parameters": {
                    "search_type": "hybrid",  # Busca híbrida (semântica + keywords)
                    "top_k": 5,  # Retorna top 5 resultados mais relevantes
                }
            }
        ]
        
        return tools
    
    def send_message(self, e):
        """Envia mensagem para o modelo."""
        user_message = self.message_input.value.strip()
        if not user_message:
            return
        
        # Valida configurações
        if not self.config_manager.get("api_key"):
            self.add_system_message("❌ Configure sua API Key em ⚙️ Configurações")
            return
        
        # Adiciona mensagem do usuário ao chat
        self.add_message(user_message, is_user=True)
        
        # Limpa campo de entrada
        self.message_input.value = ""
        self.page.update()
        
        # Prepara mensagens
        messages = []
        
        # System prompt
        system_prompt = self.config_manager.get("system_prompt")
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Adiciona contexto de arquivos anexados
        if self.attached_files:
            file_context = "Arquivos anexados para contexto:\n"
            for filepath in self.attached_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()[:5000]  # Limita tamanho
                        file_context += f"\n--- {Path(filepath).name} ---\n{content}\n"
                except Exception as ex:
                    file_context += f"\n[Erro ao ler {filepath}: {ex}]\n"
            
            messages.append({
                "role": "system",
                "content": file_context
            })
        
        # Adiciona histórico de mensagens anteriores
        messages.extend(self.messages)
        
        # Adiciona mensagem atual
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Atualiza histórico
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Constrói tools
        tools = self.build_tools()
        
        # Mostra indicador de carregamento
        loading_indicator = ft.ProgressBar()
        self.chat_container.controls.append(loading_indicator)
        self.page.update()
        
        try:
            # Envia para API
            response = self.xai_client.chat_completion(
                messages=messages,
                model=self.config_manager.get("model"),
                temperature=self.config_manager.get("temperature"),
                tools=tools,
                stream=False
            )
            
            # Processa resposta
            assistant_message = response["choices"][0]["message"]["content"]
            
            # Adiciona resposta ao chat
            self.add_message(assistant_message, is_user=False)
            
            # Atualiza histórico
            self.messages.append({
                "role": "assistant",
                "content": assistant_message
            })
            
        except Exception as ex:
            self.add_system_message(f"❌ Erro ao enviar mensagem: {str(ex)}")
        finally:
            # Remove indicador de carregamento
            self.chat_container.controls.remove(loading_indicator)
            self.page.update()
    
    def open_settings(self, e):
        """Abre diálogo de configurações."""
        # Campos de configuração
        management_key_field = ft.TextField(
            label="Management Key (xAI Collections)",
            value=self.config_manager.get("management_key"),
            password=True,
            can_reveal_password=True,
            width=500,
        )
        
        api_key_field = ft.TextField(
            label="API Key (Grok)",
            value=self.config_manager.get("api_key"),
            password=True,
            can_reveal_password=True,
            width=500,
        )
        
        model_dropdown = ft.Dropdown(
            label="Modelo",
            value=self.config_manager.get("model"),
            options=[
                ft.dropdown.Option("grok-2-1212", "Grok 2 (Dezembro 2024)"),
                ft.dropdown.Option("grok-2-vision-1212", "Grok 2 Vision"),
                ft.dropdown.Option("grok-beta", "Grok Beta"),
            ],
            width=500,
        )
        
        temperature_slider = ft.Slider(
            min=0,
            max=2,
            divisions=20,
            value=self.config_manager.get("temperature"),
            label="Temperature: {value}",
            width=500,
        )
        
        system_prompt_field = ft.TextField(
            label="System Prompt",
            value=self.config_manager.get("system_prompt"),
            multiline=True,
            min_lines=3,
            max_lines=5,
            width=500,
        )
        
        realtime_web_toggle = ft.Switch(
            label="Real-time Web Search",
            value=self.config_manager.get("realtime_web_search"),
        )
        
        realtime_x_toggle = ft.Switch(
            label="Real-time X (Twitter) Search",
            value=self.config_manager.get("realtime_x_search"),
        )
        
        url_citation_toggle = ft.Switch(
            label="URL Source Citation",
            value=self.config_manager.get("url_citation"),
        )
        
        theme_toggle = ft.Switch(
            label="Tema Escuro",
            value=self.config_manager.get("theme_dark"),
        )
        
        def save_settings(e):
            """Salva configurações e fecha diálogo."""
            self.config_manager.set("management_key", management_key_field.value)
            self.config_manager.set("api_key", api_key_field.value)
            self.config_manager.set("model", model_dropdown.value)
            self.config_manager.set("temperature", temperature_slider.value)
            self.config_manager.set("system_prompt", system_prompt_field.value)
            self.config_manager.set("realtime_web_search", realtime_web_toggle.value)
            self.config_manager.set("realtime_x_search", realtime_x_toggle.value)
            self.config_manager.set("url_citation", url_citation_toggle.value)
            self.config_manager.set("theme_dark", theme_toggle.value)
            
            # Atualiza cliente xAI
            self.update_xai_client()
            
            # Atualiza tema
            self.page.theme_mode = ft.ThemeMode.DARK if theme_toggle.value else ft.ThemeMode.LIGHT
            
            # Atualiza collections
            self.refresh_collections()
            
            settings_dialog.open = False
            self.page.update()
            self.add_system_message("✅ Configurações salvas!")
        
        # Diálogo de configurações
        settings_dialog = ft.AlertDialog(
            title=ft.Text("⚙️ Configurações"),
            content=ft.Container(
                content=ft.Column([
                    management_key_field,
                    api_key_field,
                    model_dropdown,
                    ft.Row([ft.Text("Temperature:"), temperature_slider]),
                    system_prompt_field,
                    ft.Divider(),
                    realtime_web_toggle,
                    realtime_x_toggle,
                    url_citation_toggle,
                    theme_toggle,
                ], scroll=ft.ScrollMode.AUTO),
                width=550,
                height=600,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(settings_dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Salvar", on_click=save_settings),
            ],
        )
        
        self.page.dialog = settings_dialog
        settings_dialog.open = True
        self.page.update()


def main(page: ft.Page):
    """Função principal da aplicação."""
    PrecedenteSearchApp(page)


if __name__ == "__main__":
    ft.app(target=main)
