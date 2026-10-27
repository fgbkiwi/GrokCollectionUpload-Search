#!/usr/bin/env python3
"""
PrecedenteSearchApp.py
Aplicação Flet para busca semântica de precedentes trabalhistas usando xAI Collections.

Funcionalidades:
- Interface gráfica para interação com modelo Grok
- Busca híbrida em xAI Collections com filtros de metadados
- Configurações persistentes (API keys, modelo, temperature)
- Lista de modelos das configurações atualizada em tempo real pela API xAI
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
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pyperclip


class ConfigManager:
    """Gerenciador de configurações da aplicação."""
    
    def __init__(self, config_file: str = "app_config.json"):
        self.config_file = Path(config_file)
        self.default_config = {
            "management_key": "",
            "api_key": "",
            "model": "grok-4.6",
            "temperature": 0.7,
            "reasoning_effort": "high",
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


def preparar_tools(tools: Optional[List[Dict]]) -> Tuple[Optional[List[Dict]], bool]:
    """Converte a busca em collection para o formato aceito pela API.

    Chat Completions só aceita tools ``function`` e ``live_search``.
    A busca em collection usa ``file_search`` em ``POST /v1/responses``.
    """
    if not tools:
        return None, False

    convertidas: List[Dict] = []
    usar_responses = False
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        tipo = tool.get("type")
        if tipo == "collection_search":
            colecao = tool.get("collection_id")
            ids = [colecao] if isinstance(colecao, str) and colecao else []
            ids.extend(tool.get("vector_store_ids") or [])
            parametros = tool.get("search_parameters") or {}
            limite = parametros.get("top_k") or tool.get("max_num_results") or 5
            convertidas.append({
                "type": "file_search",
                "vector_store_ids": ids,
                "max_num_results": limite,
            })
            usar_responses = True
            continue
        convertidas.append(tool)
        if tipo == "file_search":
            usar_responses = True
    return convertidas or None, usar_responses


def extrair_texto_resposta(data: Dict) -> str:
    """Lê o texto do assistente em Chat Completions ou na Responses API."""
    if not isinstance(data, dict):
        return ""

    choices = data.get("choices")
    if choices:
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            partes = [
                str(bloco.get("text"))
                for bloco in content
                if isinstance(bloco, dict) and bloco.get("text")
            ]
            return "\n".join(partes).strip()

    partes: List[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for bloco in item.get("content") or []:
            if isinstance(bloco, dict) and bloco.get("text"):
                partes.append(str(bloco["text"]))
    return "\n".join(partes).strip()


def normalizar_resposta_chat(data: Dict) -> Dict:
    """Devolve o formato de chat completion usado pela interface."""
    if isinstance(data, dict) and data.get("choices"):
        return data
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": extrair_texto_resposta(data),
                }
            }
        ]
    }


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
                "https://management-api.x.ai/v1/collections",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            brutas = data.get("collections") or data.get("data") or []
            normalizadas = []
            for col in brutas:
                if not isinstance(col, dict):
                    continue
                cid = col.get("id") or col.get("collection_id")
                name = col.get("name") or col.get("collection_name") or cid
                item = dict(col)
                if cid:
                    item["id"] = cid
                if name:
                    item["name"] = name
                normalizadas.append(item)
            return normalizadas
        except Exception as e:
            print(f"Erro ao listar collections: {e}")
            return []
    
    def chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        reasoning_effort: Optional[str] = None,
    ) -> Any:
        """
        Envia requisição de chat completion para a API.
        
        Args:
            messages: Lista de mensagens do chat
            model: Modelo a ser usado
            temperature: Temperatura para geração
            tools: Lista de ferramentas disponíveis
            stream: Se deve usar streaming
            reasoning_effort: Nível de reasoning quando o modelo permitir
            
        Returns:
            Resposta da API
        """
        from xai_reasoning import aplicar_reasoning_effort

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if stream:
            payload["stream"] = True

        tools_api, usar_responses = preparar_tools(tools)
        if tools_api:
            payload["tools"] = tools_api

        aplicar_reasoning_effort(payload, model, reasoning_effort)

        if usar_responses:
            payload["input"] = payload.pop("messages")
            url = f"{self.base_url}/responses"
        else:
            url = f"{self.base_url}/chat/completions"
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=120 if usar_responses else 60,
                stream=stream
            )
        except requests.RequestException as e:
            detalhe = ""
            resposta = getattr(e, "response", None)
            if resposta is not None and resposta.text:
                detalhe = " " + resposta.text.strip().replace("\n", " ")[:500]
            raise Exception(f"Erro na requisição: {e}.{detalhe}") from e

        if not response.ok:
            detalhe = (response.text or "").strip().replace("\n", " ")
            if len(detalhe) > 500:
                detalhe = detalhe[:500] + "..."
            raise Exception(
                f"Erro na requisição: {response.status_code} {response.reason} "
                f"for url: {response.url}. {detalhe}"
            )

        if stream:
            return response  # Retorna objeto response para streaming
        return normalizar_resposta_chat(response.json())


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

        self.file_picker = ft.FilePicker(on_result=self._on_file_selected)
        self.page.overlay.append(self.file_picker)
        
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
        toolbar_controls: List[Any] = [
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
        ]
        self.toolbar = ft.Row(
            controls=toolbar_controls,
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
            on_change=self.on_collection_changed, # type: ignore
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
            icon=ft.Icons.SEND,
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
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
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
        row_controls: List[Any] = [
            ft.Icon(
                ft.Icons.PERSON if is_user else ft.Icons.SMART_TOY,
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
                color=ft.Colors.GREY,
            ),
        ]
        message_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row(controls=row_controls),
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
                bgcolor=ft.Colors.BLUE_GREY_900 if self.config_manager.get("theme_dark") else ft.Colors.BLUE_GREY_100,
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
        self.file_picker.pick_files(allow_multiple=True)

    def _on_file_selected(self, e: ft.FilePickerResultEvent):
        """Callback do FilePicker."""
        if e.files:
            for file in e.files:
                self.attached_files.append(file.path)
                self.add_system_message(f"📎 Arquivo anexado: {file.name}")
    
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
        
        # file_search é o formato atual da busca em Collections (Responses API).
        tools = [
            {
                "type": "file_search",
                "vector_store_ids": [collection_id],
                "max_num_results": 5,
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
            if self.xai_client is None:
                raise Exception("Cliente xAI não inicializado. Verifique sua API Key.")

            response = self.xai_client.chat_completion(
                messages=messages,
                model=self.config_manager.get("model"),
                temperature=self.config_manager.get("temperature"),
                tools=tools,
                stream=False,
                reasoning_effort=self.config_manager.get("reasoning_effort"),
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
        from xai_models import (
            DEFAULT_MODEL,
            FALLBACK_MODELS,
            listar_modelos_para_ui,
            rotulo_modelo,
        )
        from xai_reasoning import (
            LABELS_REASONING,
            DEFAULT_REASONING_EFFORT,
            modelo_suporta_reasoning,
            niveis_reasoning_para_modelo,
            normalizar_reasoning_effort,
        )

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

        modelo_inicial = self.config_manager.get("model") or DEFAULT_MODEL
        opcoes_iniciais = list(FALLBACK_MODELS)
        if modelo_inicial not in opcoes_iniciais:
            opcoes_iniciais = [modelo_inicial, *opcoes_iniciais]

        model_dropdown = ft.Dropdown(
            label="Modelo",
            value=modelo_inicial,
            options=[
                ft.dropdown.Option(m, rotulo_modelo(m)) for m in opcoes_iniciais
            ],
            width=500,
        )
        modelos_status = ft.Text(size=12, color=ft.Colors.GREY_700)

        reasoning_dropdown = ft.Dropdown(
            label="Nível de reasoning",
            width=500,
        )
        reasoning_hint = ft.Text(size=12, color=ft.Colors.GREY_700)

        dialogo_ativo = {"ok": True}
        carga_modelos = {"geracao": 0}
        debounce_modelos: Dict[str, Optional[threading.Timer]] = {"timer": None}

        def sync_reasoning_options(_e=None):
            modelo = model_dropdown.value or DEFAULT_MODEL
            niveis = niveis_reasoning_para_modelo(modelo)
            if not niveis:
                reasoning_dropdown.options = [
                    ft.dropdown.Option("", "Não disponível para este modelo")
                ]
                reasoning_dropdown.value = ""
                reasoning_dropdown.disabled = True
                reasoning_hint.value = "Este modelo não aceita o parâmetro reasoning_effort."
            else:
                reasoning_dropdown.disabled = False
                reasoning_dropdown.options = [
                    ft.dropdown.Option(nivel, LABELS_REASONING.get(nivel, nivel))
                    for nivel in niveis
                ]
                preferido = (
                    reasoning_dropdown.value
                    or self.config_manager.get("reasoning_effort")
                    or DEFAULT_REASONING_EFFORT
                )
                reasoning_dropdown.value = normalizar_reasoning_effort(modelo, preferido)
                reasoning_hint.value = (
                    "Controla a profundidade de raciocínio (latência × qualidade)."
                )
            try:
                self.page.update()
            except Exception:
                pass

        def aplicar_lista_modelos(modelos: List[str], msg: str) -> None:
            """Substitui as opções do dropdown e preserva a seleção atual."""
            atual = model_dropdown.value or modelo_inicial
            ids = list(modelos)
            if atual and atual not in ids:
                ids = [atual, *ids]
            vindos_da_api = set(modelos)
            model_dropdown.options = [
                ft.dropdown.Option(
                    m,
                    rotulo_modelo(m) if m in vindos_da_api else f"{m} (atual)",
                )
                for m in ids
            ]
            if atual in ids:
                model_dropdown.value = atual
            elif ids:
                model_dropdown.value = ids[0]
            else:
                model_dropdown.value = DEFAULT_MODEL
            modelos_status.value = msg
            sync_reasoning_options()

        def carregar_modelos(api_key: str) -> None:
            """Consulta a xAI e atualiza o dropdown sem travar a interface."""
            if not dialogo_ativo["ok"]:
                return
            key = (api_key or "").strip()
            carga_modelos["geracao"] += 1
            geracao = carga_modelos["geracao"]

            if not key:
                modelos, msg = listar_modelos_para_ui("")
                if dialogo_ativo["ok"] and geracao == carga_modelos["geracao"]:
                    aplicar_lista_modelos(modelos, msg)
                return

            modelos_status.value = "Consultando modelos na xAI..."
            try:
                self.page.update()
            except Exception:
                pass

            def worker() -> None:
                modelos, msg = listar_modelos_para_ui(key)
                if not dialogo_ativo["ok"] or geracao != carga_modelos["geracao"]:
                    return
                aplicar_lista_modelos(modelos, msg)

            threading.Thread(target=worker, daemon=True).start()

        def agendar_modelos(api_key: str) -> None:
            timer = debounce_modelos["timer"]
            if timer is not None:
                timer.cancel()
            timer = threading.Timer(0.5, lambda: carregar_modelos(api_key))
            timer.daemon = True
            debounce_modelos["timer"] = timer
            timer.start()

        def ao_mudar_api_key(_e=None) -> None:
            agendar_modelos(api_key_field.value or "")

        def ao_confirmar_api_key(_e=None) -> None:
            timer = debounce_modelos["timer"]
            if timer is not None:
                timer.cancel()
                debounce_modelos["timer"] = None
            carregar_modelos(api_key_field.value or "")

        api_key_field.on_change = ao_mudar_api_key
        api_key_field.on_blur = ao_confirmar_api_key
        api_key_field.on_submit = ao_confirmar_api_key

        model_dropdown.on_change = sync_reasoning_options
        sync_reasoning_options()
        
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
        
        def encerrar_consulta_modelos(_e=None) -> None:
            dialogo_ativo["ok"] = False
            timer = debounce_modelos["timer"]
            if timer is not None:
                timer.cancel()
                debounce_modelos["timer"] = None

        def cancelar_settings(_e=None) -> None:
            encerrar_consulta_modelos()
            self.close_dialog(settings_dialog)

        def save_settings(e):
            """Salva configurações e fecha diálogo."""
            encerrar_consulta_modelos()
            self.config_manager.set("management_key", management_key_field.value)
            self.config_manager.set("api_key", api_key_field.value)
            self.config_manager.set("model", model_dropdown.value)
            modelo = model_dropdown.value or DEFAULT_MODEL
            if modelo_suporta_reasoning(modelo):
                self.config_manager.set(
                    "reasoning_effort",
                    normalizar_reasoning_effort(modelo, reasoning_dropdown.value)
                    or DEFAULT_REASONING_EFFORT,
                )
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
            
            self.close_dialog(settings_dialog)
            self.add_system_message("✅ Configurações salvas!")
        
        # Diálogo de configurações
        settings_dialog = ft.AlertDialog(
            title=ft.Text("⚙️ Configurações"),
            content=ft.Container(
                content=ft.Column([
                    management_key_field,
                    api_key_field,
                    model_dropdown,
                    modelos_status,
                    reasoning_dropdown,
                    reasoning_hint,
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
                ft.TextButton("Cancelar", on_click=cancelar_settings),
                ft.ElevatedButton("Salvar", on_click=save_settings),
            ],
            on_dismiss=encerrar_consulta_modelos,
        )
        
        self.open_dialog(settings_dialog)
        carregar_modelos(api_key_field.value or "")

    def open_dialog(self, dialog):
        """Abre um diálogo de forma compatível."""
        if hasattr(self.page, "open"):
            self.page.open(dialog) # type: ignore
        else:
            setattr(self.page, "dialog", dialog)
            dialog.open = True
            self.page.update()

    def close_dialog(self, dialog):
        """Fecha um diálogo de forma compatível."""
        if hasattr(self.page, "close"):
            self.page.close(dialog) # type: ignore
        else:
            dialog.open = False
            self.page.update()


def main(page: ft.Page):
    """Função principal da aplicação."""
    PrecedenteSearchApp(page)


if __name__ == "__main__":
    ft.app(target=main)
