#!/usr/bin/env python3
"""
PrecedenteSearchApp.py
Aplicação PyQt6 para busca semântica de precedentes trabalhistas usando xAI Collections.
"""

import json
import requests
import os
import sys
import re
import time
import logging
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QTextBrowser,
    QPushButton,
    QToolButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QDialog,
    QProgressBar,
    QSlider,
    QCheckBox,
    QFrame,
    QStyle,
    QScrollArea,
)


# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PrecedentSearchApp")


def check_network_connectivity(host="8.8.8.8", port=53, timeout=3):
    """Verifica conectividade básica de rede."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def check_api_reachability(url="https://api.x.ai/v1/models", timeout=5):
    """Verifica se o endpoint da API está acessível."""
    try:
        response = requests.get(url, timeout=timeout)
        return True, response.status_code
    except Exception as e:
        return False, str(e)


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
        self.mgmt_url = "https://management-api.x.ai/v1"
        self.last_collections_error = ""
        self.last_models_error = ""
        self.last_search_error = ""
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PrecedentSearchApp/1.0"
        }
        logger.info("XAIClient inicializado")

    def validate_keys(self) -> Dict[str, bool]:
        """Verifica se as chaves API e Management são válidas."""
        results = {"api": False, "management": False}
        
        # Testar API Key
        try:
            resp = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=10)
            results["api"] = (resp.status_code == 200)
            if not results["api"]:
                logger.warning(f"Validação da API Key falhou: Status {resp.status_code}")
        except Exception as e:
            logger.error(f"Erro ao validar API Key: {e}")
            
        # Testar Management Key
        if self.management_key:
            try:
                mgmt_headers = {
                    "Authorization": f"Bearer {self.management_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "PrecedentSearchApp/1.0"
                }
                resp = requests.get(f"{self.mgmt_url}/collections", headers=mgmt_headers, timeout=10)
                results["management"] = (resp.status_code == 200)
                if not results["management"]:
                    logger.warning(f"Validação da Management Key falhou: Status {resp.status_code}")
            except Exception as e:
                logger.error(f"Erro ao validar Management Key: {e}")
        
        return results

    def _log_request_error(self, method: str, url: str, response: Optional[requests.Response], error: Exception):
        """Loga detalhes de um erro de requisição."""
        error_msg = f"Erro na requisição {method} {url}: {str(error)}"
        if response is not None:
            error_msg += f"\nStatus Code: {response.status_code}"
            error_msg += f"\nHeaders: {dict(response.headers)}"
            
            # Tratamento específico para erros comuns
            if response.status_code == 401:
                error_msg += "\n[DICA]: Erro 401 indica chave inválida, expirada ou falta de permissão."
            elif response.status_code == 403:
                error_msg += "\n[DICA]: Erro 403 indica acesso proibido. Verifique se sua conta tem acesso a este endpoint ou região."
            
            try:
                error_msg += f"\nCorpo: {response.text[:500]}"
            except:
                pass
        logger.error(error_msg)

    def _check_all_connectivity(self):
        """Verifica múltiplos pontos de conectividade."""
        results = {
            "google_dns": check_network_connectivity("8.8.8.8", 53),
            "cloudflare_dns": check_network_connectivity("1.1.1.1", 53),
            "xai_api": check_api_reachability("https://api.x.ai/v1/models")[0],
            "xai_mgmt": check_api_reachability("https://management-api.x.ai/v1/collections")[0],
            "google_http": check_api_reachability("https://www.google.com")[0]
        }
        logger.info(f"Status de conectividade: {results}")
        return results

    def list_collections(self) -> List[Dict]:
        """Lista todas as Collections disponíveis usando a Management API."""
        if not self.management_key:
            self.last_collections_error = "Management Key não configurada."
            logger.warning(self.last_collections_error)
            return []

        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PrecedentSearchApp/1.0"
        }
        
        # O endpoint correto para Management Key é estritamente via management-api.x.ai
        url = f"{self.mgmt_url}/collections"
        
        try:
            logger.info(f"Tentando listar collections via: {url}")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                collections = []
                if isinstance(data, list):
                    collections = data
                elif isinstance(data, dict):
                    if isinstance(data.get("data"), list):
                        collections = data["data"]
                    elif isinstance(data.get("collections"), list):
                        collections = data["collections"]
                
                if collections:
                    logger.info(f"Sucesso ao listar {len(collections)} collections")
                    return collections
                else:
                    logger.info("Nenhuma collection encontrada.")
                    return []

            if response.status_code == 401:
                self.last_collections_error = "Management Key inválida ou expirada."
            elif response.status_code == 403:
                self.last_collections_error = "Acesso negado à Management API (403)."
            else:
                self.last_collections_error = f"Erro ao carregar collections (Status {response.status_code})."
            
            self._log_request_error("GET", url, response, Exception(self.last_collections_error))
        
        except requests.exceptions.ConnectionError as ex:
            self.last_collections_error = "Erro de conexão com o servidor da xAI."
            logger.error(f"{self.last_collections_error}: {str(ex)}")
        except Exception as ex:
            self.last_collections_error = f"Erro inesperado: {str(ex)}"
            self._log_request_error("GET", url, None, ex)

        return []


    def list_models(self) -> List[str]:
        """Lista modelos disponíveis."""
        if not self.api_key:
            self.last_models_error = "API Key não configurada."
            return []

        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            if response.status_code != 200:
                self._log_request_error("GET", f"{self.base_url}/models", response, Exception("Status != 200"))
                self.last_models_error = f"{response.status_code}: {response.text[:200]}"
                return []

            data = response.json()
            models = data.get("data", []) if isinstance(data, dict) else []
            model_ids = [str(m["id"]) for m in models if isinstance(m, dict) and m.get("id") is not None]
            return model_ids
        except Exception as e:
            self._log_request_error("GET", f"{self.base_url}/models", None, e)
            self.last_models_error = str(e)
            self._check_all_connectivity()
            return []

    def search_documents(self, query: str, collection_id: str, max_retries: int = 3) -> List[Dict[str, Any]]:
        """Busca documentos em uma collection usando busca semântica com suporte a retentativas exponenciais."""
        if not self.api_key:
            self.last_search_error = "API Key não configurada."
            return []

        payload = {
            "query": query,
            "source": {"collection_ids": [collection_id]},
            "retrieval_mode": {"type": "semantic"},
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) + (time.time() % 1) # Exponential backoff with jitter
                    logger.info(f"Retentativa de busca {attempt}/{max_retries} em {wait_time:.2f}s...")
                    time.sleep(wait_time)

                response = requests.post(
                    f"{self.base_url}/documents/search",
                    headers=self.headers,
                    json=payload,
                    timeout=45,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("Busca de documentos realizada com sucesso")
                    # ... normalização ...
                    normalized = []
                    results = []
                    if isinstance(data, dict):
                        if isinstance(data.get("data"), list):
                            results = data["data"]
                        elif isinstance(data.get("results"), list):
                            results = data["results"]
                        elif isinstance(data.get("matches"), list):
                            for match in data["matches"]:
                                if not isinstance(match, dict): continue
                                doc = match.get("document") if isinstance(match.get("document"), dict) else match
                                if isinstance(doc, dict):
                                    item = dict(doc)
                                    if "document_id" not in item and "id" in item:
                                        item["document_id"] = item.get("id")
                                    if "score" not in item and "score" in match:
                                        item["score"] = match.get("score")
                                    normalized.append(item)
                            return normalized
                    return results if results else []
                
                self._log_request_error("POST", f"{self.base_url}/documents/search", response, Exception(f"Status {response.status_code}"))
                last_error = f"Erro {response.status_code}: {response.text[:200]}"
                
                if response.status_code not in [429, 500, 502, 503, 504]:
                    break
                    
            except requests.exceptions.RequestException as e:
                self._log_request_error("POST", f"{self.base_url}/documents/search", None, e)
                last_error = f"Erro de conexão na tentativa {attempt + 1}: {str(e)}"
                if attempt == max_retries:
                    self._check_all_connectivity()

        self.last_search_error = last_error or "Erro desconhecido na busca."
        return []

    def chat_completion(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        max_retries: int = 4
    ) -> Any:
        """Envia requisição de chat completion com retry exponencial e logging detalhado."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if tools: payload["tools"] = tools
        if stream: payload["stream"] = True
        
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    logger.info(f"Retentativa de chat {attempt}/{max_retries} em {wait_time:.2f}s...")
                    time.sleep(wait_time)

                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                    stream=stream
                )
                
                if response.status_code != 200:
                    self._log_request_error("POST", f"{self.base_url}/chat/completions", response, Exception(f"Status {response.status_code}"))
                    response.raise_for_status()
                
                logger.info(f"Chat completion sucesso (tentativa {attempt + 1})")
                return response if stream else response.json()

            except requests.exceptions.ReadTimeout as e:
                logger.warning(f"Timeout na tentativa {attempt + 1}")
                last_exception = Exception(f"Timeout de leitura (120s) na tentativa {attempt + 1}. O servidor x.ai está lento.")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Erro de conexão na tentativa {attempt + 1}: {str(e)}")
                last_exception = Exception(f"Erro de conexão na tentativa {attempt + 1}. Verifique sua internet e DNS.")
                if attempt == max_retries:
                    self._check_all_connectivity()
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                if status_code in [429, 500, 502, 503, 504]:
                    last_exception = Exception(f"Erro HTTP {status_code} na tentativa {attempt + 1}: {e.response.text[:200]}")
                    continue
                else:
                    raise Exception(f"Erro HTTP fatal {status_code}: {e.response.text[:200]}")
            except Exception as e:
                logger.error(f"Erro inesperado: {str(e)}")
                raise Exception(f"Erro inesperado na requisição: {str(e)}")
        
        raise last_exception or Exception("Falha após múltiplas tentativas.")

    def responses_with_collection(
        self,
        input_messages: List[Dict],
        model: str,
        temperature: float,
        collection_id: str,
        max_results: int = 10,
        max_retries: int = 4,
    ) -> str:
        """Usa o endpoint /v1/responses com file_search para RAG grounded na collection.

        Conforme documentação oficial (https://docs.x.ai/developers/tools/collections-search):
        o tool 'file_search' com 'vector_store_ids' faz o modelo buscar automaticamente
        na collection antes de responder, evitando alucinações.

        Returns:
            Texto da resposta do assistente com citações embutidas.
        """
        payload = {
            "model": model,
            "temperature": temperature,
            "input": input_messages,
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": [collection_id],
                    "max_num_results": max_results,
                }
            ],
        }

        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    logger.info(f"Retentativa de responses {attempt}/{max_retries} em {wait_time:.2f}s...")
                    time.sleep(wait_time)

                response = requests.post(
                    f"{self.base_url}/responses",
                    headers=self.headers,
                    json=payload,
                    timeout=120,
                )

                if response.status_code != 200:
                    self._log_request_error("POST", f"{self.base_url}/responses", response, Exception(f"Status {response.status_code}"))
                    response.raise_for_status()

                data = response.json()
                logger.info(f"Responses API sucesso (tentativa {attempt + 1})")

                # Extrai o texto da resposta do formato Responses API
                # output é uma lista de items; procura o item de mensagem do assistente
                text_parts = []
                for item in data.get("output", []):
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        for content_block in item.get("content", []):
                            if content_block.get("type") == "output_text":
                                text_parts.append(content_block.get("text", ""))
                return "\n".join(text_parts) if text_parts else ""

            except requests.exceptions.ReadTimeout as e:
                logger.warning(f"Timeout na tentativa {attempt + 1}")
                last_exception = Exception(f"Timeout de leitura (120s) na tentativa {attempt + 1}.")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Erro de conexão na tentativa {attempt + 1}: {str(e)}")
                last_exception = Exception(f"Erro de conexão na tentativa {attempt + 1}.")
                if attempt == max_retries:
                    self._check_all_connectivity()
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                if status_code in [429, 500, 502, 503, 504]:
                    last_exception = Exception(f"Erro HTTP {status_code} na tentativa {attempt + 1}: {e.response.text[:200]}")
                    continue
                else:
                    raise Exception(f"Erro HTTP fatal {status_code}: {e.response.text[:200]}")
            except Exception as e:
                logger.error(f"Erro inesperado: {str(e)}")
                raise Exception(f"Erro inesperado na requisição: {str(e)}")

        raise last_exception or Exception("Falha após múltiplas tentativas.")


class WorkerSignals(QObject):
    """Sinais para worker em background."""

    finished = pyqtSignal(object)


class Worker(QRunnable):
    """Executa função em background sem travar a UI."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        result = self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit(result)


class PrecedentSearchApp(QMainWindow):
    """Aplicação principal de busca de precedentes."""

    INPUT_BASE_HEIGHT = 56
    INPUT_MAX_MULTIPLIER = 4
    RESPONSE_BASE_HEIGHT = 75
    RESPONSE_MAX_MULTIPLIER = 4

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.xai_client: Optional[XAIClient] = None
        self.messages: List[Dict] = []
        self.attached_files: List[str] = []
        self.available_models: List[str] = []
        self.previous_collection_id: str = ""
        self.thread_pool = QThreadPool()
        self._updating_collection = False
        self.typing_card: Optional[QWidget] = None
        self.loading_card: Optional[QWidget] = None

        self.setWindowTitle("Busca de Precedentes Trabalhistas")
        self.resize(1200, 860)

        self.update_xai_client()
        self.create_ui()
        self.schedule_startup_refresh()

    def schedule_startup_refresh(self):
        """Agenda o refresh inicial das collections."""
        QTimer.singleShot(200, self.refresh_collections)

    def update_xai_client(self):
        """Atualiza o cliente xAI."""
        api_key = str(self.config_manager.get("api_key") or "")
        management_key = str(self.config_manager.get("management_key") or "")
        if api_key or management_key:
            self.xai_client = XAIClient(api_key, management_key)
        else:
            self.xai_client = None

    def apply_theme(self):
        """Aplica tema claro/escuro na janela e em toda a aplicação."""
        is_dark = bool(self.config_manager.get("theme_dark"))
        app = QApplication.instance()
        if not app:
            return

        if is_dark:
            style = """
                QMainWindow, QDialog { background-color: #1f1f1f; color: #e8e8e8; }
                QWidget { color: #e8e8e8; }
                
                /* Área Central e Scroll */
                QScrollArea, QScrollArea > QWidget > QWidget { background-color: #1f1f1f; border: none; }
                QScrollArea #qt_scrollarea_viewport { background-color: #1f1f1f; }
                
                /* Message Cards */
                QFrame#messageCard { border-radius: 8px; border: 1px solid #444; }
                QFrame#messageCard[cardType="user"] { background-color: #303030; }
                QFrame#messageCard[cardType="assistant"] { background-color: #2b2b2b; }
                QFrame#messageCard[cardType="system"] { background-color: #1a1a1a; border-color: #333; }
                QFrame#messageCard[cardType="typing"] { background-color: #2b2b2b; border-style: dashed; }
                
                QTextEdit, QTextBrowser, QLineEdit, QComboBox {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    selection-background-color: #404040;
                }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                    selection-background-color: #3d3d3d;
                }
                QPushButton, QToolButton {
                    background-color: #333333;
                    color: #f0f0f0;
                    border: 1px solid #4a4a4a;
                    border-radius: 4px;
                    padding: 6px;
                }
                QPushButton:hover, QToolButton:hover { background-color: #3d3d3d; }
                QPushButton:pressed, QToolButton:pressed { background-color: #444444; }
                QFrame#toolbarFrame { background-color: #333333; border-bottom: 1px solid #444; }
                QLabel#statusLabel { color: #a0a0a0; }
                QScrollBar:vertical {
                    border: none;
                    background: #2b2b2b;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #4a4a4a;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QCheckBox { spacing: 5px; }
                QCheckBox::indicator { width: 18px; height: 18px; }
            """
        else:
            style = """
                QMainWindow, QDialog { background-color: #f7f7f7; color: #1a1a1a; }
                QWidget { color: #1a1a1a; }

                /* Área Central e Scroll */
                QScrollArea, QScrollArea > QWidget > QWidget { background-color: #f7f7f7; border: none; }
                QScrollArea #qt_scrollarea_viewport { background-color: #f7f7f7; }

                /* Message Cards */
                QFrame#messageCard { border-radius: 8px; border: 1px solid #ddd; }
                QFrame#messageCard[cardType="user"] { background-color: #ffffff; }
                QFrame#messageCard[cardType="assistant"] { background-color: #f9f9f9; }
                QFrame#messageCard[cardType="system"] { background-color: #f0f0f0; border-color: #e0e0e0; }
                QFrame#messageCard[cardType="typing"] { background-color: #f9f9f9; border-style: dashed; }

                QTextEdit, QTextBrowser, QLineEdit, QComboBox {
                    background-color: #ffffff;
                    color: #1a1a1a;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    selection-background-color: #e0e0e0;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #1a1a1a;
                    selection-background-color: #f0f0f0;
                }
                QPushButton, QToolButton {
                    background-color: #f5f5f5;
                    color: #1a1a1a;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px;
                }
                QPushButton:hover, QToolButton:hover { background-color: #e8e8e8; }
                QPushButton:pressed, QToolButton:pressed { background-color: #d0d0d0; }
                QFrame#toolbarFrame { background-color: #f5f5f5; border-bottom: 1px solid #ddd; }
                QLabel#statusLabel { color: #666666; }
                QScrollBar:vertical {
                    border: none;
                    background: #f0f0f0;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #ccc;
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
        app.setStyleSheet(style)
        # Forçar atualização de widgets existentes
        for widget in app.allWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def create_ui(self):
        """Cria a interface do usuário."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbarFrame")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        toolbar_layout.setSpacing(8)

        clear_button = QToolButton()
        clear_button.setToolTip("Limpar chat")
        clear_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        clear_button.clicked.connect(self.clear_chat)

        copy_button = QToolButton()
        copy_button.setToolTip("Copiar chat")
        copy_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        copy_button.clicked.connect(self.copy_chat)

        attach_button = QToolButton()
        attach_button.setToolTip("Anexar arquivo")
        attach_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        attach_button.clicked.connect(self.attach_file)

        settings_button = QToolButton()
        settings_button.setToolTip("Configurações")
        # Usando ícone de ferramenta/configurações padrão do sistema
        settings_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        settings_button.clicked.connect(self.open_settings)

        toolbar_layout.addWidget(clear_button)
        toolbar_layout.addWidget(copy_button)
        toolbar_layout.addWidget(attach_button)
        toolbar_layout.addWidget(settings_button)
        toolbar_layout.addStretch(1)

        # Collection selection
        collection_wrapper = QWidget()
        collection_wrapper_layout = QVBoxLayout(collection_wrapper)
        collection_wrapper_layout.setContentsMargins(10, 10, 10, 10)
        collection_wrapper_layout.setSpacing(5)

        collection_row = QHBoxLayout()
        collection_row.setSpacing(8)

        self.collection_dropdown = QComboBox()
        self.collection_dropdown.setEditable(False)
        self.collection_dropdown.currentIndexChanged.connect(self.on_collection_changed)

        self.collection_refresh_button = QToolButton()
        self.collection_refresh_button.setToolTip("Atualizar collections")
        self.collection_refresh_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.collection_refresh_button.clicked.connect(self.refresh_collections_click)

        collection_row.addWidget(QLabel("Collection"))
        collection_row.addWidget(self.collection_dropdown, 1)
        collection_row.addWidget(self.collection_refresh_button)

        self.collection_status_text = QLabel("")
        self.collection_status_text.setObjectName("statusLabel")

        collection_wrapper_layout.addLayout(collection_row)
        collection_wrapper_layout.addWidget(self.collection_status_text)

        # Input
        input_wrapper = QWidget()
        input_wrapper_layout = QHBoxLayout(input_wrapper)
        input_wrapper_layout.setContentsMargins(10, 10, 10, 10)
        input_wrapper_layout.setSpacing(8)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Digite sua mensagem...")
        self.message_input.setMinimumHeight(self.INPUT_BASE_HEIGHT)
        self.message_input.setMaximumHeight(self.INPUT_BASE_HEIGHT * self.INPUT_MAX_MULTIPLIER)
        self.message_input.textChanged.connect(self.adjust_message_input_height)

        self.send_button = QPushButton("Enviar")
        self.send_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.send_button.clicked.connect(self.send_message_click)

        input_wrapper_layout.addWidget(self.message_input, 1)
        input_wrapper_layout.addWidget(self.send_button)

        # Status row
        status_wrapper = QWidget()
        status_layout = QHBoxLayout(status_wrapper)
        status_layout.setContentsMargins(10, 10, 10, 10)
        status_layout.setSpacing(6)

        self.response_status_ring = QProgressBar()
        self.response_status_ring.setRange(0, 0)
        self.response_status_ring.setFixedWidth(90)
        self.response_status_ring.setFixedHeight(12)
        self.response_status_ring.setVisible(False)

        self.response_status_text = QLabel("")
        self.response_status_text.setObjectName("statusLabel")

        status_layout.addWidget(self.response_status_ring)
        status_layout.addWidget(self.response_status_text)
        status_layout.addStretch(1)

        # Chat cards container
        self.chat_cards = QWidget()
        self.chat_cards_layout = QVBoxLayout(self.chat_cards)
        self.chat_cards_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_cards_layout.setSpacing(10)
        self.chat_cards_layout.addStretch(1)

        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll_area.setWidget(self.chat_cards)

        main_layout.addWidget(toolbar_frame)
        main_layout.addWidget(self.chat_scroll_area, 1)
        main_layout.addWidget(collection_wrapper)
        main_layout.addWidget(input_wrapper)
        main_layout.addWidget(status_wrapper)

        self.adjust_message_input_height()

        send_action = QAction(self)
        send_action.setShortcut("Ctrl+Return")
        send_action.triggered.connect(self.send_message_click)
        self.addAction(send_action)

        self.apply_theme()
        self.add_system_message("👨‍⚖️ **Sistema de Busca de Precedentes Trabalhistas**")

    def remove_chat_stretch(self):
        """Remove stretch final para inserir mensagem."""
        count = self.chat_cards_layout.count()
        if count and self.chat_cards_layout.itemAt(count - 1).spacerItem() is not None:
            spacer = self.chat_cards_layout.takeAt(count - 1)
            del spacer

    def restore_chat_stretch(self):
        """Restaura stretch para mensagens ficarem no topo."""
        count = self.chat_cards_layout.count()
        if not count or self.chat_cards_layout.itemAt(count - 1).spacerItem() is None:
            self.chat_cards_layout.addStretch(1)

    def scroll_to_bottom(self):
        """Mantém o scroll no fim após novas mensagens."""
        QTimer.singleShot(0, lambda: self.chat_scroll_area.verticalScrollBar().setValue(self.chat_scroll_area.verticalScrollBar().maximum()))

    def create_message_card(
        self,
        header_text: str,
        markdown_text: str,
        card_type: str = "assistant",
        elevation: int = 2,
        enable_copy_buttons: bool = False,
    ) -> QWidget:
        """Cria cartão visual de mensagem com Markdown selecionável."""
        card = QFrame()
        card.setObjectName("messageCard")
        card.setProperty("cardType", card_type)
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(8)

        if header_text or enable_copy_buttons:
            header_row = QHBoxLayout()
            header_row.setSpacing(8)

            if header_text:
                header = QLabel(header_text)
                header.setTextFormat(Qt.TextFormat.PlainText)
                header.setStyleSheet("font-weight: 600;")
                header_row.addWidget(header)

            header_row.addStretch(1)

            if enable_copy_buttons:
                md_button = QToolButton()
                md_button.setText("MD")
                md_button.setToolTip("Copiar resposta em Markdown")
                md_button.clicked.connect(lambda _, txt=markdown_text: self.copy_text_as_md(txt))

                rtf_button = QToolButton()
                rtf_button.setText("RTF")
                rtf_button.setToolTip("Copiar resposta em RTF")
                rtf_button.clicked.connect(lambda _, txt=markdown_text: self.copy_text_as_rtf(txt))

                header_row.addWidget(md_button)
                header_row.addWidget(rtf_button)

            card_layout.addLayout(header_row)

        body = QTextBrowser()
        body.setReadOnly(True)
        body.setOpenExternalLinks(False)
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setMarkdown(markdown_text)
        body.setMinimumHeight(self.RESPONSE_BASE_HEIGHT)
        body.setMaximumHeight(self.RESPONSE_BASE_HEIGHT * self.RESPONSE_MAX_MULTIPLIER)
        self.adjust_text_widget_height(body, markdown_text, self.RESPONSE_BASE_HEIGHT, self.RESPONSE_MAX_MULTIPLIER)
        body.setStyleSheet("background: transparent; border: none;")
        card_layout.addWidget(body)

        return card

    def calculate_dynamic_height(self, text: str, base_height: int, max_multiplier: int, line_spacing: int) -> int:
        """Calcula altura dinâmica com limite máximo baseado em multiplicador."""
        max_height = base_height * max_multiplier
        line_count = max(1, len(str(text or "").splitlines()) or 1)
        content_height = (line_count * line_spacing) + 24
        return max(base_height, min(max_height, content_height))

    def adjust_text_widget_height(self, widget: QTextEdit, text: str, base_height: int, max_multiplier: int) -> None:
        """Aplica altura dinâmica em widgets de texto com limite de crescimento."""
        line_spacing = widget.fontMetrics().lineSpacing()
        target_height = self.calculate_dynamic_height(text, base_height, max_multiplier, line_spacing)
        widget.setFixedHeight(target_height)

    def adjust_message_input_height(self) -> None:
        """Ajusta dinamicamente o campo de pergunta conforme quantidade de linhas."""
        self.adjust_text_widget_height(
            self.message_input,
            self.message_input.toPlainText(),
            self.INPUT_BASE_HEIGHT,
            self.INPUT_MAX_MULTIPLIER,
        )

    def clear_chat_cards(self):
        """Remove todos os cards de chat."""
        while self.chat_cards_layout.count():
            item = self.chat_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.chat_cards_layout.addStretch(1)

    def refresh_collections(self):
        """Atualiza collections."""
        if not self.xai_client:
            self.collection_status_text.setText("Configure a Management Key para carregar collections.")
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
            options.append((str(col_name), str(col_id)))

        self._updating_collection = True
        self.collection_dropdown.blockSignals(True)
        self.collection_dropdown.clear()
        for name, cid in options:
            self.collection_dropdown.addItem(name, cid)
        self.collection_dropdown.blockSignals(False)
        self._updating_collection = False

        if not options:
            error_msg = self.xai_client.last_collections_error or "Nenhuma collection retornada pela API."
            self.add_system_message(f"⚠️ Não foi possível carregar collections: {error_msg}")
            self.collection_status_text.setText(f"Falha ao carregar: {error_msg}")
        else:
            self.collection_status_text.setText(f"Collections carregadas: {len(options)}")

        selected_id = self.config_manager.get("selected_collection_id")
        if selected_id:
            for idx in range(self.collection_dropdown.count()):
                if self.collection_dropdown.itemData(idx) == str(selected_id):
                    self.collection_dropdown.setCurrentIndex(idx)
                    break
            self.previous_collection_id = str(selected_id)
        elif self.collection_dropdown.count() > 0:
            self.previous_collection_id = str(self.collection_dropdown.itemData(self.collection_dropdown.currentIndex()) or "")

    def refresh_collections_click(self, *_):
        """Callback para botão de atualizar collections."""
        self.update_xai_client()
        self.refresh_collections()

    def refresh_models(self, model_dropdown: QComboBox, status_text: QLabel):
        """Atualiza a lista de modelos na UI de configurações."""
        if not self.xai_client:
            status_text.setText("Configure a API Key para carregar modelos.")
            return

        model_ids = self.xai_client.list_models()
        self.available_models = model_ids

        if not model_ids:
            error_msg = self.xai_client.last_models_error or "Nenhum modelo retornado pela API."
            status_text.setText(f"Falha ao carregar: {error_msg}")
            model_dropdown.clear()
            return

        model_dropdown.clear()
        model_dropdown.addItems(model_ids)
        current_model = str(self.config_manager.get("model") or "")
        if current_model in model_ids:
            model_dropdown.setCurrentText(current_model)
        else:
            model_dropdown.setCurrentIndex(0)
        status_text.setText(f"Modelos carregados: {len(model_ids)}")

    def has_active_conversation(self) -> bool:
        """Verifica se há conversa ativa (com resposta do assistant)."""
        return any(msg.get("role") == "assistant" for msg in self.messages)

    def on_collection_changed(self, *_):
        """Callback quando a collection é alterada."""
        if self._updating_collection:
            return

        new_collection_id = str(self.collection_dropdown.currentData() or "")

        # Se não houve mudança real, ignora
        if new_collection_id == self.previous_collection_id:
            return

        # Se há conversa ativa, pede confirmação
        if self.has_active_conversation():
            self.confirm_collection_change(new_collection_id)
        else:
            # Sem conversa ativa, aplica diretamente
            self.apply_collection_change(new_collection_id)

    def confirm_collection_change(self, new_collection_id: str):
        """Abre modal de confirmação para troca de collection."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("⚠️ Alterar Collection")
        msg.setText("Alterar a collection reiniciará o chat atual e todo o contexto será perdido. Deseja continuar?")
        msg.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        response = msg.exec()

        if response == QMessageBox.StandardButton.Ok:
            self.apply_collection_change(new_collection_id)
            # Reseta o chat
            self.clear_chat_cards()
            self.messages.clear()
            self.attached_files.clear()
            self.add_system_message("🔄 Chat resetado devido à mudança de collection.")
            self.add_system_message("👨‍⚖️ **Sistema de Busca de Precedentes Trabalhistas**")
        else:
            self.collection_dropdown.blockSignals(True)
            for idx in range(self.collection_dropdown.count()):
                if self.collection_dropdown.itemData(idx) == self.previous_collection_id:
                    self.collection_dropdown.setCurrentIndex(idx)
                    break
            self.collection_dropdown.blockSignals(False)

    def apply_collection_change(self, new_collection_id: str):
        """Aplica a mudança de collection."""
        self.previous_collection_id = new_collection_id
        self.config_manager.set("selected_collection_id", new_collection_id)

    def add_message(self, content: str, is_user: bool = True):
        """Adiciona mensagem ao chat."""
        who = "Você" if is_user else "Grok"
        timestamp = datetime.now().strftime("%H:%M")
        header = f"{who} • {timestamp}"
        card_type = "user" if is_user else "assistant"
        card = self.create_message_card(
            header,
            content,
            card_type,
            elevation=2,
            enable_copy_buttons=not is_user,
        )
        self.remove_chat_stretch()
        self.chat_cards_layout.addWidget(card)
        self.restore_chat_stretch()
        self.scroll_to_bottom()

    def _rtf_escape(self, text: str) -> str:
        """Escapa texto para RTF com suporte a Unicode."""
        output = []
        for ch in str(text or ""):
            code = ord(ch)
            if ch == "\\":
                output.append("\\\\")
            elif ch == "{":
                output.append("\\{")
            elif ch == "}":
                output.append("\\}")
            elif ch == "\t":
                output.append("\\tab ")
            elif 32 <= code <= 126:
                output.append(ch)
            else:
                signed = code if code <= 32767 else code - 65536
                output.append(f"\\u{signed}?")
        return "".join(output)

    def _format_inline_markdown_rtf(self, text: str) -> str:
        """Converte marcações inline de Markdown para controles RTF."""
        result = []
        s = str(text or "")
        i = 0

        while i < len(s):
            if s.startswith("**", i):
                end = s.find("**", i + 2)
                if end != -1:
                    content = self._rtf_escape(s[i + 2:end])
                    result.append(f"\\b {content}\\b0 ")
                    i = end + 2
                    continue
            if s.startswith("__", i):
                end = s.find("__", i + 2)
                if end != -1:
                    content = self._rtf_escape(s[i + 2:end])
                    result.append(f"\\b {content}\\b0 ")
                    i = end + 2
                    continue
            if s[i] == "*":
                end = s.find("*", i + 1)
                if end != -1:
                    content = self._rtf_escape(s[i + 1:end])
                    result.append(f"\\i {content}\\i0 ")
                    i = end + 1
                    continue
            if s[i] == "_":
                end = s.find("_", i + 1)
                if end != -1:
                    content = self._rtf_escape(s[i + 1:end])
                    result.append(f"\\i {content}\\i0 ")
                    i = end + 1
                    continue
            if s[i] == "`":
                end = s.find("`", i + 1)
                if end != -1:
                    content = self._rtf_escape(s[i + 1:end])
                    result.append(f"\\f1 {content}\\f0 ")
                    i = end + 1
                    continue
            if s[i] == "[":
                close_bracket = s.find("]", i + 1)
                if close_bracket != -1 and close_bracket + 1 < len(s) and s[close_bracket + 1] == "(":
                    close_paren = s.find(")", close_bracket + 2)
                    if close_paren != -1:
                        label = self._rtf_escape(s[i + 1:close_bracket])
                        url = self._rtf_escape(s[close_bracket + 2:close_paren])
                        result.append(f"\\ul\\cf1 {label}\\ul0\\cf0  ({url})")
                        i = close_paren + 1
                        continue

            next_special = len(s)
            for marker in ("**", "__", "*", "_", "`", "["):
                pos = s.find(marker, i + 1)
                if pos != -1:
                    next_special = min(next_special, pos)

            result.append(self._rtf_escape(s[i:next_special]))
            i = next_special

        return "".join(result)

    def markdown_to_rtf(self, markdown_text: str) -> str:
        """Converte markdown para RTF preservando formatações principais."""
        lines = str(markdown_text or "").splitlines()
        rtf_lines: List[str] = []
        in_code_block = False

        for raw_line in lines:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                rtf_lines.append(f"\\pard\\li480\\f1 {self._rtf_escape(line)}\\f0\\li0\\par")
                continue

            if not stripped:
                rtf_lines.append("\\par")
                continue

            heading = re.match(r"^(#{1,6})\\s+(.*)$", stripped)
            if heading:
                level = len(heading.group(1))
                text = heading.group(2)
                size_map = {1: 36, 2: 32, 3: 28, 4: 26, 5: 24, 6: 22}
                fs = size_map.get(level, 22)
                rtf_lines.append(f"\\pard\\b\\fs{fs} {self._format_inline_markdown_rtf(text)}\\b0\\fs22\\par")
                continue

            unordered = re.match(r"^\s*[-*+]\s+(.*)$", line)
            if unordered:
                item = unordered.group(1)
                rtf_lines.append(f"\\pard\\li360\\tx360 \\bullet\\tab {self._format_inline_markdown_rtf(item)}\\par")
                continue

            ordered = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
            if ordered:
                num = ordered.group(1)
                item = ordered.group(2)
                rtf_lines.append(f"\\pard\\li360\\tx360 {num}.\\tab {self._format_inline_markdown_rtf(item)}\\par")
                continue

            quote = re.match(r"^\s*>\s?(.*)$", line)
            if quote:
                rtf_lines.append(f"\\pard\\li480\\i {self._format_inline_markdown_rtf(quote.group(1))}\\i0\\li0\\par")
                continue

            if re.match(r"^\s*([-*_])\1{2,}\s*$", stripped):
                rtf_lines.append("\\pard\\qc ________________________________\\par\\pard")
                continue

            rtf_lines.append(f"\\pard {self._format_inline_markdown_rtf(line)}\\par")

        header = (
            "{\\rtf1\\ansi\\deff0\n"
            "{\\fonttbl{\\f0 Segoe UI;}{\\f1 Consolas;}}\n"
            "{\\colortbl ;\\red0\\green102\\blue204;}\n"
        )
        body = "\n".join(rtf_lines)
        return header + body + "\n}"

    def _copy_to_clipboard(self, text: str, format_name: str):
        """Helper para copiar texto para o clipboard com feedback."""
        try:
            clipboard = QApplication.clipboard()
            if not clipboard:
                raise Exception("Clipboard não disponível")
            
            clipboard.setText(str(text or ""))
            
            # Feedback visual no label de status
            self.response_status_text.setText(f"✅ Resposta copiada em {format_name}!")
            
            # Limpar feedback após 3 segundos
            QTimer.singleShot(3000, lambda: self.response_status_text.setText("") if self.response_status_text.text().startswith("✅") else None)
            
        except Exception as ex:
            logging.error(f"Erro ao copiar para clipboard: {ex}")
            self.add_system_message(f"❌ Erro ao copiar {format_name}: {ex}")

    def copy_text_as_md(self, markdown_text: str):
        """Copia texto markdown para o clipboard."""
        self._copy_to_clipboard(markdown_text, "MD")

    def copy_text_as_rtf(self, markdown_text: str):
        """Copia texto em formato RTF para o clipboard."""
        try:
            rtf_text = self.markdown_to_rtf(markdown_text)
            self._copy_to_clipboard(rtf_text, "RTF")
        except Exception as ex:
            self.add_system_message(f"❌ Erro ao processar RTF: {ex}")

    def add_system_message(self, content: str):
        """Adiciona mensagem do sistema."""
        card = self.create_message_card("", content, "system", elevation=1)
        self.remove_chat_stretch()
        self.chat_cards_layout.addWidget(card)
        self.restore_chat_stretch()
        self.scroll_to_bottom()

    def clear_chat(self, *_):
        """Limpa o chat."""
        self.clear_chat_cards()
        self.messages.clear()
        self.attached_files.clear()
        self.add_system_message("🔄 Chat resetado.")

    def copy_chat(self, *_):
        """Copia chat para o clipboard."""
        chat_text = [f"[{'USUÁRIO' if msg['role'] == 'user' else 'GROK'}]\n{msg['content']}\n" for msg in self.messages]
        self._copy_to_clipboard("\n".join(chat_text), "Chat")

    def attach_file(self, *_):
        """Anexa um arquivo."""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Selecione os arquivos para anexar",
                "",
                "Text files (*.txt);;Markdown files (*.md);;All files (*.*)",
            )
            if files:
                for file_path in files:
                    self.attached_files.append(str(file_path))
                    file_name = os.path.basename(file_path)
                    self.add_system_message(f"📎 Arquivo anexado: {file_name}")
        except Exception as ex:
            print(f"Erro ao anexar arquivo: {ex}")
            self.add_system_message(f"❌ Erro ao anexar arquivo: {ex}")

    def create_typing_card(self) -> QWidget:
        """Cria cartão temporário de digitação."""
        timestamp = datetime.now().strftime("%H:%M")
        return self.create_message_card(f"Grok • {timestamp}", "digitando...", "typing", elevation=2)

    def create_loading_card(self) -> QWidget:
        """Cria card de progresso durante consulta."""
        card = QFrame()
        card.setObjectName("messageCard")
        card.setProperty("cardType", "typing")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        layout.addWidget(bar)
        return card

    def send_message_click(self, *_):
        """Inicia envio da mensagem."""
        self.send_message()

    def send_message(self):
        """Envia uma mensagem."""
        user_message = self.message_input.toPlainText().strip()
        if not user_message or not self.config_manager.get("api_key"):
            return

        self.add_message(user_message, is_user=True)
        self.message_input.setPlainText("")
        self.response_status_text.setText("Preparando consulta...")
        self.response_status_ring.setVisible(True)

        self.typing_card = self.create_typing_card()
        self.loading_card = self.create_loading_card()
        self.remove_chat_stretch()
        self.chat_cards_layout.addWidget(self.typing_card)
        self.chat_cards_layout.addWidget(self.loading_card)
        self.restore_chat_stretch()
        self.scroll_to_bottom()

        history_before = list(self.messages)
        self.messages.append({"role": "user", "content": user_message})

        collection_id = str(self.collection_dropdown.currentData() or "")
        self.response_status_text.setText("Consultando o modelo...")

        worker = Worker(
            self._perform_request,
            user_message,
            history_before,
            list(self.attached_files),
            collection_id,
        )
        worker.signals.finished.connect(self._on_send_finished)
        self.thread_pool.start(worker)

    def _perform_request(
        self,
        user_message: str,
        history_before: List[Dict[str, str]],
        attached_files: List[str],
        collection_id: str,
    ) -> Dict[str, str]:
        """Executa completion em background.

        Quando uma collection está selecionada, utiliza o endpoint /v1/responses com o
        tool 'file_search', conforme documentação oficial xAI. Isso permite que o modelo
        busque automaticamente na collection antes de responder (RAG grounded), evitando
        alucinações. Sem collection, usa o chat/completions tradicional.
        """
        if not self.xai_client:
            return {"answer": "", "error": "Cliente não inicializado", "search_error": ""}

        system_prompt = str(self.config_manager.get("system_prompt") or "")
        model = str(self.config_manager.get("model") or "grok-2-1212")
        temperature = float(self.config_manager.get("temperature") or 0.7)

        # Constrói lista de mensagens base (sistema + histórico + nova pergunta)
        base_messages: List[Dict] = [{"role": "system", "content": system_prompt}]

        if attached_files:
            ctx = "Arquivos anexados:\n"
            for f in attached_files:
                try:
                    with open(f, 'r', encoding='utf-8') as f_content:
                        ctx += f"\n--- {Path(f).name} ---\n{f_content.read()[:5000000]}\n"
                except Exception:
                    pass
            base_messages.append({"role": "system", "content": ctx})

        base_messages.extend(history_before)
        base_messages.append({"role": "user", "content": user_message})

        search_error = ""
        if not collection_id:
            search_error = "⚠️ Nenhuma collection selecionada. A resposta será gerada sem contexto de precedentes."

        try:
            if collection_id:
                # Caminho principal: Responses API com file_search (RAG grounded)
                ans = self.xai_client.responses_with_collection(
                    input_messages=base_messages,
                    model=model,
                    temperature=temperature,
                    collection_id=collection_id,
                )
            else:
                # Fallback: chat/completions sem grounding
                response = self.xai_client.chat_completion(
                    base_messages,
                    model,
                    temperature,
                    None,
                )
                ans = str(response["choices"][0]["message"]["content"])

            return {"answer": ans, "error": "", "search_error": search_error}
        except Exception as ex:
            return {"answer": "", "error": str(ex), "search_error": search_error}

    def _on_send_finished(self, result: Dict[str, str]):
        """Finaliza atualização de UI após resposta da API."""
        if self.typing_card is not None:
            self.typing_card.deleteLater()
            self.typing_card = None
        if self.loading_card is not None:
            self.loading_card.deleteLater()
            self.loading_card = None
        self.scroll_to_bottom()

        if result.get("search_error"):
            self.add_system_message(result["search_error"])

        if result.get("error"):
            self.add_system_message(f"❌ Erro: {result['error']}")
        else:
            ans = str(result.get("answer") or "")
            self.add_message(ans, is_user=False)
            self.messages.append({"role": "assistant", "content": ans})

        self.response_status_text.setText("")
        self.response_status_ring.setVisible(False)
        self.scroll_to_bottom()

    def open_settings(self, *_):
        """Abre o diálogo de configurações."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Configurações")
        dlg.resize(700, 560)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        m_key_label = QLabel("Management Key")
        m_key = QLineEdit(str(self.config_manager.get("management_key") or ""))
        m_key.setEchoMode(QLineEdit.EchoMode.Password)

        a_key_label = QLabel("API Key")
        a_key = QLineEdit(str(self.config_manager.get("api_key") or ""))
        a_key.setEchoMode(QLineEdit.EchoMode.Password)

        model_label = QLabel("Modelo")
        model = QComboBox()
        model.setEditable(False)

        model_status = QLabel("Clique para atualizar modelos.")
        model_status.setObjectName("statusLabel")

        refresh_models_button = QToolButton()
        refresh_models_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_models_button.setToolTip("Atualizar modelos")
        refresh_models_button.clicked.connect(lambda: self.refresh_models(model, model_status))

        model_row = QHBoxLayout()
        model_row.addWidget(model, 1)
        model_row.addWidget(refresh_models_button)

        temp_label = QLabel("Temperature: 0.00")
        temp_slider = QSlider(Qt.Orientation.Horizontal)
        temp_slider.setMinimum(0)
        temp_slider.setMaximum(20)
        current_temp = float(self.config_manager.get("temperature") or 0.7)
        temp_slider.setValue(int(round(current_temp * 10)))
        temp_label.setText(f"Temperature: {temp_slider.value() / 10:.2f}")
        temp_slider.valueChanged.connect(lambda v: temp_label.setText(f"Temperature: {v / 10:.2f}"))

        sys_p_label = QLabel("System Prompt")
        sys_p = QTextEdit()
        sys_p.setPlainText(str(self.config_manager.get("system_prompt") or ""))
        sys_p.setMinimumHeight(160)

        theme = QCheckBox("Tema Escuro")
        theme.setChecked(bool(self.config_manager.get("theme_dark")))

        save_button = QPushButton("Salvar")

        def save():
            self.config_manager.set("management_key", m_key.text())
            self.config_manager.set("api_key", a_key.text())
            self.config_manager.set("model", model.currentText())
            self.config_manager.set("temperature", temp_slider.value() / 10)
            self.config_manager.set("system_prompt", sys_p.toPlainText())
            self.config_manager.set("theme_dark", theme.isChecked())
            self.update_xai_client()
            self.apply_theme()
            self.refresh_collections()
            dlg.accept()

        save_button.clicked.connect(save)

        layout.addWidget(m_key_label)
        layout.addWidget(m_key)
        layout.addWidget(a_key_label)
        layout.addWidget(a_key)
        layout.addWidget(model_label)
        layout.addLayout(model_row)
        layout.addWidget(model_status)
        layout.addWidget(temp_label)
        layout.addWidget(temp_slider)
        layout.addWidget(sys_p_label)
        layout.addWidget(sys_p)
        layout.addWidget(theme)
        layout.addWidget(save_button)

        self.update_xai_client()
        self.refresh_models(model, model_status)
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    window = PrecedentSearchApp()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
