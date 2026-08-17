#!/usr/bin/env python3
import sys
import json
import os
import re
import unicodedata
import time
import requests
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QProgressBar, QFileDialog, 
    QCheckBox, QComboBox, QDialog, QLineEdit, QFormLayout, 
    QDialogButtonBox, QStyle, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRunnable, QThreadPool, QObject
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

class WorkerSignals(QObject):
    progress = pyqtSignal(dict)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['signals'] = self.signals

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))

class ConfigDialog(QDialog):
    def __init__(self, parent=None, config=None, models=None, collections=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(500)
        self.config = config or {}
        self.models = models or []
        self.collections = collections or []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.mgmt_key_edit = QLineEdit(self.config.get("management_key", ""))
        self.mgmt_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Management Key:", self.mgmt_key_edit)
        
        self.load_collections_btn = QPushButton("Carregar Collections")
        form.addRow("", self.load_collections_btn)
        
        self.collection_combo = QComboBox()
        for c in self.collections:
            name = c.get("name", "Sem nome")
            cid = c.get("id", "")
            self.collection_combo.addItem(f"{name} ({cid})", cid)
        
        idx = self.collection_combo.findData(self.config.get("selected_collection_id", ""))
        if idx >= 0: self.collection_combo.setCurrentIndex(idx)
        form.addRow("Collection:", self.collection_combo)
        
        form.addRow(QFrame())
        
        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key (Grok):", self.api_key_edit)
        
        self.refresh_models_btn = QPushButton("Atualizar Modelos")
        form.addRow("", self.refresh_models_btn)
        
        self.model_combo = QComboBox()
        for m in self.models:
            self.model_combo.addItem(m)
        idx = self.model_combo.findText(self.config.get("selected_model", ""))
        if idx >= 0: self.model_combo.setCurrentIndex(idx)
        form.addRow("Modelo:", self.model_combo)
        
        layout.addLayout(form)
        
        self.dark_mode_cb = QCheckBox("Modo Escuro")
        self.dark_mode_cb.setChecked(self.parent().dark_mode if self.parent() else False)
        layout.addWidget(self.dark_mode_cb)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        return {
            "management_key": self.mgmt_key_edit.text(),
            "api_key": self.api_key_edit.text(),
            "selected_model": self.model_combo.currentText(),
            "selected_collection_id": self.collection_combo.currentData(),
            "dark_mode": self.dark_mode_cb.isChecked()
        }

class MDGenerationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MD Generation V3 - xAI")
        self.resize(1000, 800)
        
        self.selected_json_files: List[str] = []
        self.output_directory: str = ""
        self.config_file = "config.json"
        self.config = {}
        self.available_models = []
        self.collections_list = []
        self.dark_mode = False
        self.disable_chunking = False
        self.threadpool = QThreadPool()
        
        self.init_ui()
        self.load_config()
        self.refresh_on_startup()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("MD Generation V3 - xAI")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2;")
        header.addWidget(title)
        
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self.open_config_dialog)
        header.addWidget(self.settings_btn)
        layout.addLayout(header)
        
        layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))
        
        # Files Section
        files_group = QWidget()
        files_layout = QVBoxLayout(files_group)
        files_layout.addWidget(QLabel("📁 Seleção de Arquivos e Pasta de Saída", font=QFont("Arial", 14, QFont.Weight.Bold)))
        
        btns_row = QHBoxLayout()
        self.json_btn = QPushButton(" Selecionar Arquivos JSON")
        self.json_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.json_btn.clicked.connect(self.pick_json_files)
        btns_row.addWidget(self.json_btn)
        
        self.folder_btn = QPushButton(" Selecionar Pasta de Saída")
        self.folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.folder_btn.clicked.connect(self.pick_output_folder)
        btns_row.addWidget(self.folder_btn)
        files_layout.addLayout(btns_row)
        
        self.files_label = QLabel("Nenhum arquivo selecionado")
        self.files_label.setWordWrap(True)
        self.files_label.setStyleSheet("color: #616161;")
        files_layout.addWidget(self.files_label)
        
        self.folder_label = QLabel("Nenhuma pasta selecionada")
        self.folder_label.setStyleSheet("color: #616161;")
        files_layout.addWidget(self.folder_label)
        
        files_group.setStyleSheet("border: 1px solid #A5D6A7; border-radius: 10px; padding: 10px;")
        layout.addWidget(files_group)
        
        # Actions Section
        actions_group = QWidget()
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.addWidget(QLabel("🚀 Ações", font=QFont("Arial", 14, QFont.Weight.Bold)))
        
        act_row = QHBoxLayout()
        self.generate_btn = QPushButton(" Gerar Arquivos MD")
        self.generate_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 10px;")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_md_files_click)
        act_row.addWidget(self.generate_btn)
        
        self.chunk_cb = QCheckBox("do not chunk JSON objects")
        self.chunk_cb.stateChanged.connect(self.on_chunk_change)
        act_row.addWidget(self.chunk_cb)
        actions_layout.addLayout(act_row)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        actions_layout.addWidget(self.progress)
        
        actions_group.setStyleSheet("border: 1px solid #FFCC80; border-radius: 10px; padding: 10px;")
        layout.addWidget(actions_group)
        
        # Log Section
        layout.addWidget(QLabel("Log de Execução:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #42A5F5; border-radius: 5px;")
        layout.addWidget(self.log_text)

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                self.log("✅ Configuração carregada.")
                self.check_generate_button_state()
            except Exception as e:
                self.log(f"⚠️ Erro ao carregar config: {e}")

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.log("💾 Configuração salva.")
        except Exception as e:
            self.log(f"⚠️ Erro ao salvar config: {e}")

    def log(self, message):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {message}")

    def pick_json_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar Arquivos JSON", "", "JSON Files (*.json);;All Files (*)")
        if files:
            self.selected_json_files = files
            self.files_label.setText(f"Arquivos: {', '.join([os.path.basename(f) for f in files])}")
            self.files_label.setStyleSheet("color: #388E3C;")
        else:
            self.selected_json_files = []
            self.files_label.setText("Nenhum arquivo selecionado")
            self.files_label.setStyleSheet("color: #616161;")
        self.check_generate_button_state()

    def pick_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída")
        if folder:
            self.output_directory = folder
            self.folder_label.setText(f"Pasta: {folder}")
            self.folder_label.setStyleSheet("color: #388E3C;")
        else:
            self.output_directory = ""
            self.folder_label.setText("Nenhuma pasta selecionada")
            self.folder_label.setStyleSheet("color: #616161;")
        self.check_generate_button_state()

    def on_chunk_change(self, state):
        self.disable_chunking = (state == Qt.CheckState.Checked)
        self.log(f"ℹ️ Chunking desativado: {self.disable_chunking}")

    def check_generate_button_state(self):
        ok = (len(self.selected_json_files) > 0 and 
              self.output_directory and 
              self.config.get("api_key") and 
              self.config.get("selected_model"))
        self.generate_btn.setEnabled(bool(ok))

    def open_config_dialog(self):
        dialog = ConfigDialog(self, self.config, self.available_models, self.collections_list)
        dialog.load_collections_btn.clicked.connect(lambda: self.run_background_task(self.fetch_collections_logic, dialog_update=dialog))
        dialog.refresh_models_btn.clicked.connect(lambda: self.run_background_task(self.fetch_models_logic, dialog_update=dialog))
        
        if dialog.exec():
            new_config = dialog.get_config()
            self.dark_mode = new_config.pop("dark_mode")
            self.apply_theme()
            self.config.update(new_config)
            self.save_config()
            self.check_generate_button_state()

    def apply_theme(self):
        if self.dark_mode:
            palette = QPalette()
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            self.setPalette(palette)
            self.log_text.setStyleSheet("background-color: #1e1e1e; color: white; border: 1px solid #42A5F5;")
        else:
            self.setPalette(self.style().standardPalette())
            self.log_text.setStyleSheet("background-color: #f5f5f5; color: black; border: 1px solid #42A5F5;")

    def run_background_task(self, fn, *args, dialog_update=None):
        worker = Worker(fn, *args)
        worker.signals.log.connect(self.log)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Erro", e))
        if dialog_update:
            def on_finished(result):
                if isinstance(result, list) and len(result) > 0:
                    if "id" in result[0]: # Collections
                        self.collections_list = result
                        dialog_update.collection_combo.clear()
                        for c in result:
                            dialog_update.collection_combo.addItem(f"{c.get('name')} ({c.get('id')})", c.get('id'))
                    else: # Models
                        self.available_models = result
                        dialog_update.model_combo.clear()
                        dialog_update.model_combo.addItems(result)
            worker.signals.finished.connect(on_finished)
        self.threadpool.start(worker)

    def fetch_collections_logic(self, signals):
        signals.log.emit("🔄 Carregando collections...")
        key = self.config.get("management_key")
        if not key: raise Exception("Management Key ausente")
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.get("https://management-api.x.ai/v1/collections", headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            cols = data.get("collections", [])
            signals.log.emit(f"✅ {len(cols)} collections encontradas.")
            return cols
        raise Exception(f"Erro API: {resp.status_code}")

    def fetch_models_logic(self, signals):
        signals.log.emit("🔄 Buscando modelos...")
        key = self.config.get("api_key")
        if not key: raise Exception("API Key ausente")
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.get("https://api.x.ai/v1/models", headers=headers, timeout=20)
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            signals.log.emit(f"✅ {len(models)} modelos encontrados.")
            return models
        raise Exception(f"Erro API: {resp.status_code}")

    def refresh_on_startup(self):
        if self.config.get("management_key"):
            self.run_background_task(self.fetch_collections_logic)
        if self.config.get("api_key"):
            self.run_background_task(self.fetch_models_logic)

    def generate_md_files_click(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.generate_btn.setEnabled(False)
        
        worker = Worker(self.generate_logic)
        worker.signals.log.connect(self.log)
        worker.signals.progress.connect(lambda d: self.progress.setValue(int(d['percent'])))
        worker.signals.finished.connect(self.on_generation_finished)
        worker.signals.error.connect(self.on_generation_error)
        self.threadpool.start(worker)

    def on_generation_finished(self, result):
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        QMessageBox.information(self, "Sucesso", "Geração de MDs concluída!")

    def on_generation_error(self, err):
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Erro", f"Erro na geração: {err}")

    # --- Lógica de Geração (Adaptada do Original) ---
    def generate_logic(self, signals):
        signals.log.emit("=" * 70)
        signals.log.emit("🚀 Iniciando geração de arquivos MD...")
        
        self.stats = {
            "total_processed": 0,
            "chunks_created": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }
        
        output_path = Path(self.output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        total_files = len(self.selected_json_files)
        
        for i, json_file in enumerate(self.selected_json_files):
            signals.log.emit(f"\n📄 Processando: {os.path.basename(json_file)}")
            
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    data = data["data"]
                
                if not isinstance(data, list):
                    signals.log.emit("⚠️ Formato JSON inválido. Esperado lista de sentenças.")
                    continue
                
                signals.log.emit(f"   {len(data)} sentença(s) encontrada(s)")
                
                for idx, item in enumerate(data, start=1):
                    self.process_sentenca_sync(item, idx, output_path, signals)
                    
                    if idx % 5 == 0:
                        signals.log.emit(f"   ⏳ Processadas: {idx}/{len(data)}")
                        signals.progress.emit({"percent": ((i * 100 / total_files) + (idx / len(data) * (100 / total_files)))})
                
            except Exception as e:
                signals.log.emit(f"❌ Erro ao ler {json_file}: {e}")

        self.print_statistics_to_log(signals)
        return True

    def process_sentenca_sync(self, item: Dict[str, Any], index: int, output_path: Path, signals):
        conteudo = str(item.get("conteudo", "")).strip()
        if not conteudo:
            signals.log.emit("⚠️ Sentença sem conteúdo. Ignorando.")
            return

        categoria = str(item.get("categoria", ""))
        tipo_acao = str(item.get("tipo_acao", ""))
        
        # Extração de palavras-chave síncrona dentro da thread do worker
        keywords = self.extract_keywords_with_grok_sync(conteudo, categoria, signals)

        if categoria: self.stats["categorias"].add(categoria)
        if tipo_acao: self.stats["tipos_acao"].add(tipo_acao)

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

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(chunk)
                    if not chunk.endswith("\n"): f.write("\n")
                
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                self.stats["chunks_created"] += 1
            except Exception as e:
                signals.log.emit(f"❌ Erro ao gravar arquivo: {e}")

        self.stats["total_processed"] += 1

    def extract_keywords_with_grok_sync(self, conteudo: str, categoria: str, signals) -> List[str]:
        max_retries = 2
        last_error = None
        
        headers = {
            "Authorization": f"Bearer {self.config.get('api_key')}",
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
            "model": self.config.get("selected_model"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 200,
        }

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0: time.sleep(2 ** attempt)

                response = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90,
                )

                if response.status_code == 200:
                    data = response.json()
                    keywords_text = str(data["choices"][0]["message"]["content"]).strip()
                    keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]
                    return keywords[:10]
                
                last_error = f"Status {response.status_code}"
                if response.status_code not in [429, 500, 502, 503, 504]:
                    break
            except Exception as exc:
                last_error = str(exc)
                continue

        signals.log.emit(f"⚠️ Erro ao gerar palavras-chave (após {max_retries} tentativas): {last_error}")
        return self.default_keywords(categoria)

    def default_keywords(self, categoria: str) -> List[str]:
        fallback = categoria.lower().replace(" ", "_") if categoria else "trabalhista"
        return [fallback, "clt", "trabalhista"]

    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        if len(text) <= chunk_size: return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                last_period = text.rfind(".", start, end)
                if last_period > start + chunk_size // 2: end = last_period + 1
            chunk = text[start:end].strip()
            if chunk: chunks.append(chunk)
            start = end - overlap if end < len(text) else end
        return chunks

    def sanitize_filename(self, text: str) -> str:
        text = re.sub(r"[<>:\"/\\|?*]", "", text)
        text = re.sub(r"[\s\-—]+", "_", text)
        return text[:100] or "document"

    def build_metadata(self, item: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
        metadata = {k: v for k, v in item.items() if k != "conteudo"}
        metadata["palavras-chave"] = keywords
        cleaned: Dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None: cleaned[key] = ""
            elif isinstance(value, (str, int, float, bool, list, dict)): cleaned[key] = value
            else: cleaned[key] = str(value)
        return cleaned

    def print_statistics_to_log(self, signals):
        signals.log.emit("\n" + "=" * 70)
        signals.log.emit("📊 ESTATISTICAS DO PROCESSAMENTO")
        signals.log.emit("=" * 70)
        signals.log.emit(f"Total de sentenças processadas:     {self.stats['total_processed']}")
        signals.log.emit(f"Total de arquivos MD criados:       {self.stats['chunks_created']}")
        signals.log.emit(f"Categorias únicas:                  {len(self.stats['categorias'])}")
        signals.log.emit(f"Tipos de ação únicos:               {len(self.stats['tipos_acao'])}")
        signals.log.emit("=" * 70)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MDGenerationApp()
    window.show()
    sys.exit(app.exec())
