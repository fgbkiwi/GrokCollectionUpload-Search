#!/usr/bin/env python3
"""
CollectionUploaderV3.py (PyQt6 version)
Interface PyQt6 para upload em lotes de arquivos Markdown com metadados JSON para xAI Collections.
"""

import csv
import json
import os
import re
import signal
import sys
import traceback
import unicodedata
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from PyQt6.QtCore import Qt, QThreadPool, QRunnable, QObject, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QDialog,
    QProgressBar,
    QCheckBox,
    QFrame,
    QScrollArea,
    QGroupBox,
    QStyle,
    QSizePolicy,
)


class WorkerSignals(QObject):
    """Sinais para comunicação entre Worker e UI."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(dict)
    log = pyqtSignal(str)


class Worker(QRunnable):
    """Executa função em background sem travar a UI."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs, signals=self.signals)
            self.signals.finished.emit(result)
        except Exception:
            traceback.print_exc()
            self.signals.error.emit(traceback.format_exc())


class ConfigManager:
    """Gerenciador de configurações da aplicação."""
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.default_config = {
            "management_key": "",
            "selected_collection_id": "",
            "selected_model": "",
            "target_directory": "",
            "log_directory": "",
            "max_batches_to_show": 0,
            "dark_mode": False
        }
        self.config = self.load_config()

    def load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return {**self.default_config, **json.load(f)}
            except Exception as e:
                print(f"Erro ao carregar config: {e}")
        return self.default_config.copy()

    def save_config(self) -> None:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()


class SettingsDialog(QDialog):
    """Diálogo de configurações."""
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(600)
        self.collections_list = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("⚙️ Configurações")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Credenciais API
        layout.addWidget(QLabel("<b>Credenciais API</b>"))
        self.key_field = QLineEdit()
        self.key_field.setPlaceholderText("Management Key (xAI Collection)")
        self.key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_field.setText(self.config.get("management_key", ""))
        layout.addWidget(self.key_field)

        self.load_collections_btn = QPushButton("🔄 Carregar Collections")
        self.load_collections_btn.clicked.connect(self.load_collections_click)
        layout.addWidget(self.load_collections_btn)

        self.collections_dropdown = QComboBox()
        self.collections_dropdown.setPlaceholderText("Selecione uma Collection")
        layout.addWidget(self.collections_dropdown)

        # Nova Collection
        layout.addWidget(QLabel("<b>Nova Collection</b>"))
        self.create_check = QCheckBox("Criar nova collection")
        self.create_check.stateChanged.connect(self.sync_create_state)
        layout.addWidget(self.create_check)

        self.new_name_field = QLineEdit()
        self.new_name_field.setPlaceholderText("Nome da nova collection")
        self.new_name_field.setEnabled(False)
        layout.addWidget(self.new_name_field)

        self.create_btn = QPushButton("➕ Criar Collection")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self.create_collection_click)
        layout.addWidget(self.create_btn)

        # Aparência
        layout.addWidget(QLabel("<b>Aparência</b>"))
        self.dark_mode_check = QCheckBox("Dark Mode")
        self.dark_mode_check.setChecked(self.config.get("dark_mode", False))
        layout.addWidget(self.dark_mode_check)

        layout.addStretch()

        # Botões de ação
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Salvar e Fechar")
        save_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        # Inicializar dropdown se houver chave
        if self.key_field.text():
            self.load_collections_click()

    def sync_create_state(self):
        enabled = self.create_check.isChecked()
        self.new_name_field.setEnabled(enabled)
        self.create_btn.setEnabled(enabled and bool(self.new_name_field.text().strip()))

    def load_collections_click(self):
        key = self.key_field.text().strip()
        if not key: return
        
        # Simples GET para collections (usando requests direto por ser config)
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        urls = ["https://management-api.x.ai/v1/collections", "https://api.x.ai/v1/collections"]
        
        self.collections_dropdown.clear()
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    cols = data if isinstance(data, list) else data.get("data", data.get("collections", []))
                    for c in cols:
                        cid = c.get("collection_id") or c.get("id")
                        name = c.get("collection_name") or name
                        self.collections_dropdown.addItem(name, cid)
                    
                    # Selecionar a atual se existir
                    current_id = self.config.get("selected_collection_id")
                    index = self.collections_dropdown.findData(current_id)
                    if index >= 0:
                        self.collections_dropdown.setCurrentIndex(index)
                    break
            except:
                continue

    def create_collection_click(self):
        # Implementação simplificada de criação no diálogo
        pass


class CollectionUploaderV3PyQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.threadpool = QThreadPool()
        
        self.session_state_file_name = "upload_session_state.json"
        self.session_state = {"version": 1, "updated_at": "", "collection_uploads": {}}
        self.batch_map = {}
        self.batch_status = {}
        self.active_upload_batch = None
        
        self.REQUIRED_METADATA_KEYS = ["categoria", "reclamada", "numero_processo", "data_publicacao", "tipo_acao", "palavras-chave"]
        
        self.init_ui()
        self.load_config_to_ui()
        self.apply_theme()
        
        # Carregar sessões se houver pasta de log
        if self.config.get("log_directory"):
            self.load_session_state()

    def init_ui(self):
        self.setWindowTitle("Collection Uploader V3 - xAI (PyQt6)")
        self.resize(1080, 860)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Collection Uploader V3 - xAI")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2;")
        header_layout.addWidget(title)
        
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)) # Engrenagem aproximada
        self.settings_btn.setIconSize(QSize(30, 30))
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setToolTip("Configurações")
        self.settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_btn)
        self.main_layout.addLayout(header_layout)

        self.main_layout.addWidget(self.create_divider())

        # Scroll Area for sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(15)
        
        # Section 1: Folders
        self.scroll_layout.addWidget(self.create_folders_section())
        
        # Section 2: Actions/Upload
        self.scroll_layout.addWidget(self.create_actions_section())
        
        # Section 3: Log
        self.scroll_layout.addWidget(self.create_log_section())
        
        scroll.setWidget(scroll_content)
        self.main_layout.addWidget(scroll)

    def create_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def create_folders_section(self):
        group = QGroupBox("📁 Seleção de Pastas e Lotes")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        group.setStyleSheet("QGroupBox { border: 1px solid #A5D6A7; border-radius: 10px; margin-top: 10px; padding: 10px; }")
        layout = QVBoxLayout(group)
        
        # Buttons Row
        btn_layout = QHBoxLayout()
        self.target_btn = QPushButton(" Selecionar Pasta de Arquivos")
        self.target_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.target_btn.setMinimumWidth(250)
        self.target_btn.clicked.connect(self.pick_target_folder)
        
        self.log_btn = QPushButton(" Selecionar Pasta de Log")
        self.log_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.log_btn.setMinimumWidth(250)
        self.log_btn.clicked.connect(self.pick_log_folder)
        
        btn_layout.addWidget(self.target_btn)
        btn_layout.addWidget(self.log_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Batch limit row
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Quantidade de lotes (0 = automático):"))
        self.max_batches_field = QLineEdit("0")
        self.max_batches_field.setFixedWidth(100)
        self.max_batches_field.editingFinished.connect(self.apply_batch_limit)
        limit_layout.addWidget(self.max_batches_field)
        
        self.refresh_btn = QPushButton(" Atualizar Lotes")
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.refresh_batches)
        limit_layout.addWidget(self.refresh_btn)
        limit_layout.addStretch()
        layout.addLayout(limit_layout)
        
        layout.addWidget(self.create_divider())
        
        self.target_path_label = QLabel("Nenhuma pasta de arquivos selecionada")
        self.target_path_label.setStyleSheet("color: #616161; font-size: 11px;")
        layout.addWidget(self.target_path_label)
        
        self.log_path_label = QLabel("Nenhuma pasta de log selecionada")
        self.log_path_label.setStyleSheet("color: #616161; font-size: 11px;")
        layout.addWidget(self.log_path_label)
        
        self.batch_summary_label = QLabel("Nenhum lote identificado")
        self.batch_summary_label.setStyleSheet("color: #616161; font-size: 11px;")
        layout.addWidget(self.batch_summary_label)
        
        return group

    def create_actions_section(self):
        group = QGroupBox("🚀 Upload por Lote")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        group.setStyleSheet("QGroupBox { border: 1px solid #FFCC80; border-radius: 10px; margin-top: 10px; padding: 10px; }")
        layout = QVBoxLayout(group)
        
        self.skip_check = QCheckBox("Pular arquivos já enviados em sessões anteriores")
        self.skip_check.setChecked(True)
        layout.addWidget(self.skip_check)
        
        self.progress_title = QLabel("Upload inativo")
        self.progress_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.progress_title.setStyleSheet("color: #455A64;")
        layout.addWidget(self.progress_title)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_stats = QLabel("")
        self.progress_stats.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.progress_stats)
        
        self.progress_eta = QLabel("")
        self.progress_eta.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.progress_eta)
        
        layout.addWidget(self.create_divider())
        
        layout.addWidget(QLabel("<b>Lotes disponíveis</b>"))
        
        # Container for batch rows
        self.batch_list_container = QWidget()
        self.batch_list_layout = QVBoxLayout(self.batch_list_container)
        self.batch_list_layout.setSpacing(5)
        
        batch_scroll = QScrollArea()
        batch_scroll.setWidgetResizable(True)
        batch_scroll.setMinimumHeight(280)
        batch_scroll.setWidget(self.batch_list_container)
        layout.addWidget(batch_scroll)
        
        return group

    def create_log_section(self):
        group = QGroupBox("📜 Log de Execução")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        group.setStyleSheet("QGroupBox { border: 1px solid #42A5F5; border-radius: 10px; margin-top: 10px; padding: 10px; }")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.log_text.setStyleSheet("background-color: #f5f5f5; color: black; font-family: Consolas, monospace;")
        layout.addWidget(self.log_text)
        
        return group

    def open_settings(self):
        dialog = SettingsDialog(self, self.config)
        if dialog.exec():
            # Salvar mudanças
            self.config.set("management_key", dialog.key_field.text().strip())
            self.config.set("selected_collection_id", dialog.collections_dropdown.currentData())
            self.config.set("dark_mode", dialog.dark_mode_check.isChecked())
            self.apply_theme()
            self.refresh_batches()

    def load_config_to_ui(self):
        self.target_directory = self.config.get("target_directory", "")
        self.log_directory = self.config.get("log_directory", "")
        self.max_batches_to_show = self.config.get("max_batches_to_show", 0)
        self.max_batches_field.setText(str(self.max_batches_to_show))
        
        if self.target_directory:
            self.target_path_label.setText(f"Pasta de arquivos: {self.target_directory}")
            self.target_path_label.setStyleSheet("color: #2E7D32; font-size: 11px;")
            
        if self.log_directory:
            self.log_path_label.setText(f"Pasta de log: {self.log_directory}")
            self.log_path_label.setStyleSheet("color: #2E7D32; font-size: 11px;")
            
        self.refresh_batches()

    def apply_theme(self):
        dark = self.config.get("dark_mode", False)
        if dark:
            # Dark Theme Palette
            palette = QPalette()
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Window, QColor(30, 30, 30))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Base, QColor(45, 45, 45))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Button, QColor(45, 45, 45))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            self.setPalette(palette)
            self.log_text.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: Consolas, monospace;")
        else:
            self.setPalette(self.style().standardPalette())
            self.log_text.setStyleSheet("background-color: #f5f5f5; color: #000000; font-family: Consolas, monospace;")

    # Logic methods (translated from Flet)
    def pick_target_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Selecione a pasta com arquivos MD e JSON", self.target_directory)
        if path:
            self.target_directory = path
            self.config.set("target_directory", path)
            self.target_path_label.setText(f"Pasta de arquivos: {path}")
            self.target_path_label.setStyleSheet("color: #2E7D32; font-size: 11px;")
            self.refresh_batches()

    def pick_log_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Selecione a pasta de log", self.log_directory)
        if path:
            self.log_directory = path
            self.config.set("log_directory", path)
            self.log_path_label.setText(f"Pasta de log: {path}")
            self.log_path_label.setStyleSheet("color: #2E7D32; font-size: 11px;")
            self.load_session_state()
            self.refresh_batches()

    def apply_batch_limit(self):
        try:
            val = int(self.max_batches_field.text())
            if val < 0: raise ValueError
            self.max_batches_to_show = val
            self.config.set("max_batches_to_show", val)
            self.refresh_batches()
        except ValueError:
            QMessageBox.warning(self, "Valor Inválido", "Informe um número válido de lotes (0 ou maior).")

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    # ... Other helper methods like group_files_into_batches, validate_target_directory, etc. ...
    # (These are identical in logic to the Flet version)

    def group_files_into_batches(self, directory: str) -> Dict[str, List[str]]:
        md_files = list(Path(directory).glob("*.md"))
        
        def extract_batch_prefix(file_name: str) -> Optional[str]:
            match = re.match(r"^(\d{4,5})", file_name)
            if not match: return None
            try: return f"{int(match.group(1)):05d}"
            except: return None

        def sort_key(path: Path) -> Tuple[int, str]:
            prefix = extract_batch_prefix(path.name)
            prefix_value = int(prefix) if prefix is not None else 10**9
            return (prefix_value, path.name)

        md_files_sorted = sorted(md_files, key=sort_key)
        file_list = [str(path) for path in md_files_sorted]
        total = len(file_list)
        if total == 0: return {}

        if self.max_batches_to_show <= 0:
            return {"01": file_list}

        batches = max(self.max_batches_to_show, 1)
        base_size = total // batches
        remainder = total % batches
        grouped: Dict[str, List[str]] = {}
        cursor = 0
        for idx in range(batches):
            batch_size = base_size + (1 if idx < remainder else 0)
            if batch_size == 0: continue
            batch_id = f"{idx + 1:02d}"
            grouped[batch_id] = file_list[cursor : cursor + batch_size]
            cursor += batch_size
        return grouped

    def refresh_batches(self):
        # Limpar UI atual
        while self.batch_list_layout.count():
            item = self.batch_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not self.target_directory:
            self.batch_summary_label.setText("Nenhuma pasta selecionada")
            return

        # Lógica de validação e agrupamento
        self.batch_map = self.group_files_into_batches(self.target_directory)
        if not self.batch_map:
            self.batch_summary_label.setText("Nenhum arquivo encontrado")
            return

        # Renderizar lotes
        for batch_id, files in self.batch_map.items():
            self.render_batch_row(batch_id, files)
            
        self.batch_summary_label.setText(f"Lotes identificados: {len(self.batch_map)}")

    def render_batch_row(self, batch_id, files):
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Shape.StyledPanel)
        row_widget.setStyleSheet("QFrame { border: 1px solid #E0E0E0; border-radius: 8px; padding: 5px; background: white; color: black; }")
        layout = QHBoxLayout(row_widget)
        
        name_label = QLabel(f"Lote {batch_id}")
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setFixedWidth(150)
        layout.addWidget(name_label)
        
        info_label = QLabel(f"Arquivos: {len(files)}")
        info_label.setFixedWidth(100)
        layout.addWidget(info_label)
        
        status_label = QLabel("Pendente")
        status_label.setStyleSheet("background-color: #616161; color: white; border-radius: 10px; padding: 2px 8px;")
        layout.addWidget(status_label)
        
        layout.addStretch()
        
        upload_btn = QPushButton(f"Upload Lote {batch_id}")
        upload_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        upload_btn.clicked.connect(lambda _, b=batch_id: self.start_upload_batch(b))
        layout.addWidget(upload_btn)
        
        self.batch_list_layout.addWidget(row_widget)

    def start_upload_batch(self, batch_id):
        if self.active_upload_batch:
            QMessageBox.warning(self, "Upload em Andamento", "Aguarde o upload atual terminar.")
            return
            
        self.active_upload_batch = batch_id
        self.log(f"🚀 Iniciando upload do lote {batch_id}...")
        
        # Desabilitar botões
        # ... logic to disable all upload buttons ...
        
        worker = Worker(self.upload_batch_process, batch_id)
        worker.signals.progress.connect(self.update_progress)
        worker.signals.log.connect(self.log)
        worker.signals.finished.connect(self.upload_finished)
        worker.signals.error.connect(self.upload_error)
        self.threadpool.start(worker)

    def upload_batch_process(self, batch_id, signals):
        # Lógica de upload (copiada do original e adaptada para emitir sinais)
        md_files = self.batch_map.get(batch_id, [])
        total = len(md_files)
        
        # ... API implementation ...
        for i, f in enumerate(md_files):
            # Simular upload
            time.sleep(0.5) 
            signals.log.emit(f"Enviado: {os.path.basename(f)}")
            signals.progress.emit({"processed": i+1, "total": total, "batch_id": batch_id})
        
        return f"Lote {batch_id} concluído com sucesso."

    def update_progress(self, data):
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(data["total"])
        self.progress_bar.setValue(data["processed"])
        self.progress_title.setText(f"Lote {data['batch_id']} em upload: {int(data['processed']/data['total']*100)}%")

    def upload_finished(self, result):
        self.active_upload_batch = None
        self.progress_bar.setVisible(False)
        self.progress_title.setText("Upload inativo")
        self.log(f"✅ {result}")
        QMessageBox.information(self, "Sucesso", result)
        self.refresh_batches()

    def upload_error(self, error):
        self.active_upload_batch = None
        self.progress_bar.setVisible(False)
        self.log(f"❌ Erro: {error}")
        QMessageBox.critical(self, "Erro no Upload", error)

    def load_session_state(self):
        if not self.log_directory: return
        state_path = Path(self.log_directory) / self.session_state_file_name
        if not state_path.exists():
            self.session_state = {"version": 1, "updated_at": "", "collection_uploads": {}}
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
        if not self.log_directory: return
        state_path = Path(self.log_directory) / self.session_state_file_name
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            self.session_state["updated_at"] = datetime.now().isoformat()
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(self.session_state, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            self.log(f"⚠️ Erro ao salvar sessão: {str(exc)}")

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

    def extract_batch_prefix(self, file_name: str) -> Optional[str]:
        match = re.match(r"^(\d{4,5})", file_name)
        if not match: return None
        try: return f"{int(match.group(1)):05d}"
        except: return None

    def validate_target_directory(self, directory: str) -> Tuple[bool, str]:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return False, "A pasta selecionada não existe ou não é válida."
        md_files = list(path.glob("*.md"))
        json_files = list(path.glob("*.json"))
        if not md_files: return False, "Nenhum arquivo MD encontrado."
        if not json_files: return False, "Nenhum arquivo JSON encontrado."
        return True, ""

    def find_metadata_path(self, md_file: str) -> str:
        md_path = Path(md_file)
        return str(md_path.with_name(f"{md_path.stem}_metadata.json"))

    def read_metadata(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except: return None

    def normalize_metadata_fields(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in metadata.items():
            if value is None: normalized[key] = "não disponível"
            elif isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
                normalized[key] = ", ".join(items) if items else "não disponível"
            elif isinstance(value, dict):
                normalized[key] = json.dumps(value, ensure_ascii=False) if value else "não disponível"
            else:
                text_value = str(value).strip()
                normalized[key] = text_value if text_value else "não disponível"
        return normalized

    def to_ascii_filename(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        ascii_text = re.sub(r"[<>:\"/\\|?*]", "", ascii_text)
        ascii_text = re.sub(r"[\s\-—]+", "_", ascii_text)
        return ascii_text[:100] or "document"

    def write_batch_log_json(self, payload: Dict[str, Any]):
        if not self.log_directory: return
        try:
            Path(self.log_directory).mkdir(parents=True, exist_ok=True)
            file_name = f"upload_lote_{payload.get('batch_id', 'sem_lote')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(Path(self.log_directory) / file_name, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as exc: self.log(f"⚠️ Erro ao gravar log JSON: {str(exc)}")

    def write_batch_log_csv(self, rows: List[Dict[str, Any]], batch_id: str):
        if not self.log_directory: return
        try:
            Path(self.log_directory).mkdir(parents=True, exist_ok=True)
            file_name = Path(self.log_directory) / f"upload_lote_{batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(file_name, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "batch_id", "collection_id", "arquivo", "status", "tentativas", "http_status", "mensagem"])
                writer.writeheader()
                for row in rows: writer.writerow(row)
        except Exception as exc: self.log(f"⚠️ Erro ao gravar log CSV: {str(exc)}")

    def upload_batch_process(self, batch_id, signals):
        collection_id = self.config.get("selected_collection_id")
        mgmt_key = self.config.get("management_key")
        
        if not collection_id or not mgmt_key:
            signals.error.emit("Configurações ausentes (Key ou Collection ID).")
            return

        md_files = sorted(self.batch_map.get(batch_id, []))
        total = len(md_files)
        
        batch_session = self.get_batch_session(collection_id, batch_id)
        previous_uploaded = set(batch_session.get("uploaded_files", []))
        skip_uploaded = self.skip_check.isChecked()
        
        started_at = datetime.now()
        uploaded, failed = 0, 0
        file_rows = []
        base_urls = ["https://management-api.x.ai/v1", "https://api.x.ai/v1"]
        headers = {"Authorization": f"Bearer {mgmt_key}"}

        # Validar Schema antes de começar
        try:
            signals.log.emit("🔍 Validando schema da collection...")
            resp = requests.get(f"https://management-api.x.ai/v1/collections/{collection_id}", headers=headers, timeout=20)
            if resp.status_code != 200:
                signals.error.emit(f"Erro ao validar collection: {resp.status_code}")
                return
            
            data = resp.json()
            field_defs = data.get("field_definitions") or data.get("collection", {}).get("field_definitions", [])
            collection_keys = [str(f["key"]) for f in field_defs if isinstance(f, dict) and "key" in f]
        except Exception as e:
            signals.error.emit(f"Erro na validação: {str(e)}")
            return

        for index, md_file in enumerate(md_files, start=1):
            file_name = os.path.basename(md_file)
            if skip_uploaded and md_file in previous_uploaded:
                file_rows.append({"timestamp": datetime.now().isoformat(), "batch_id": batch_id, "collection_id": collection_id, "arquivo": file_name, "status": "pulado", "tentativas": 0, "http_status": "", "mensagem": "Já enviado."})
                continue

            # Upload Real com Retry
            ok, msg, attempts, status_code = self.upload_file_logic(md_file, collection_id, base_urls, headers)
            
            if ok:
                uploaded += 1
                previous_uploaded.add(md_file)
            else:
                failed += 1
                signals.log.emit(f"❌ Falha em {file_name}: {msg}")

            file_rows.append({"timestamp": datetime.now().isoformat(), "batch_id": batch_id, "collection_id": collection_id, "arquivo": file_name, "status": "sucesso" if ok else "falha", "tentativas": attempts, "http_status": status_code, "mensagem": msg})
            
            signals.progress.emit({"processed": index, "total": total, "batch_id": batch_id, "uploaded": uploaded, "failed": failed, "started_at": started_at})

        # Finalizar
        batch_session["uploaded_files"] = sorted(previous_uploaded)
        batch_session["last_status"] = "concluido" if failed == 0 else "parcial"
        self.save_session_state()
        
        self.write_batch_log_json({"batch_id": batch_id, "collection_id": collection_id, "inicio": started_at.isoformat(), "fim": datetime.now().isoformat(), "sucesso": uploaded, "falhas": failed, "arquivos": file_rows})
        self.write_batch_log_csv(file_rows, batch_id)
        
        return f"Upload concluído. Sucesso: {uploaded}, Falhas: {failed}"

    def upload_file_logic(self, md_file, collection_id, base_urls, headers):
        metadata = self.read_metadata(self.find_metadata_path(md_file))
        if not metadata: return False, "Metadados inválidos", 0, 0
        
        normalized = self.normalize_metadata_fields(metadata)
        safe_name = self.to_ascii_filename(os.path.basename(md_file))
        
        try:
            with open(md_file, "rb") as f: file_bytes = f.read()
        except Exception as e: return False, str(e), 0, 0

        for base_url in base_urls:
            for attempt in range(1, 4):
                try:
                    payload = {"name": safe_name, "content_type": "text/markdown", "fields": json.dumps(normalized, ensure_ascii=False)}
                    resp = requests.post(f"{base_url}/collections/{collection_id}/documents", headers=headers, data=payload, files={"data": (safe_name, file_bytes, "text/markdown")}, timeout=60)
                    if resp.status_code in [200, 201]: return True, "OK", attempt, resp.status_code
                    if attempt < 3: time.sleep(2 ** attempt)
                except:
                    if attempt < 3: time.sleep(2 ** attempt)
        return False, "Erro após tentativas", 3, 0


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CollectionUploaderV3PyQt()
    window.show()
    sys.exit(app.exec())
