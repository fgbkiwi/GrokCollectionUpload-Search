#!/usr/bin/env python3
import sys
import json
import os
import re
import unicodedata
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QProgressBar, QFileDialog, 
    QCheckBox, QComboBox, QDialog, QLineEdit, QFormLayout, 
    QDialogButtonBox, QStyle, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRunnable, QThreadPool, QObject

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
            name = c.get("collection_name") or c.get("name") or c.get("collection_id", "Sem nome")
            cid = c.get("collection_id") or c.get("id", "")
            self.collection_combo.addItem(f"{name} ({cid})", cid)
        
        idx = self.collection_combo.findData(self.config.get("selected_collection_id", ""))
        if idx >= 0: self.collection_combo.setCurrentIndex(idx)
        form.addRow("Collection:", self.collection_combo)
        
        form.addRow(QFrame(frameShape=QFrame.Shape.HLine))
        
        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Key (Grok):", self.api_key_edit)
        
        self.refresh_models_btn = QPushButton("Atualizar Modelos")
        form.addRow("", self.refresh_models_btn)
        
        self.model_combo = QComboBox()
        for m in self.models: self.model_combo.addItem(m)
        idx = self.model_combo.findText(self.config.get("selected_model", ""))
        if idx >= 0: self.model_combo.setCurrentIndex(idx)
        form.addRow("Modelo:", self.model_combo)
        
        layout.addLayout(form)
        
        self.dark_mode_cb = QCheckBox("Dark Mode")
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

class CollectionUploaderV2App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collection Uploader V2 - xAI (Upload Direto)")
        self.resize(1000, 800)
        
        self.selected_json_files: List[str] = []
        self.output_directory: str = ""
        self.config_file = "config.json"
        self.config = {}
        self.available_models = []
        self.collections_list = []
        self.generated_md_files = []
        self.dark_mode = False
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
        title = QLabel("Collection Uploader V2 - xAI (Upload Direto)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1976D2;")
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
        files_layout.addWidget(QLabel("📁 Seleção de Arquivos e Pasta de Saída", styleSheet="font-size: 16px; font-weight: bold;"))
        
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
        actions_layout.addWidget(QLabel("🚀 Ações", styleSheet="font-size: 16px; font-weight: bold;"))
        
        act_row = QHBoxLayout()
        self.generate_btn = QPushButton(" Gerar Arquivos MD")
        self.generate_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 8px;")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_md_files_click)
        act_row.addWidget(self.generate_btn)
        
        self.upload_btn = QPushButton(" Upload para Collection")
        self.upload_btn.setStyleSheet("background-color: #388E3C; color: white; font-weight: bold; padding: 8px;")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.upload_to_collection_click)
        act_row.addWidget(self.upload_btn)
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

    def log(self, message):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{t}] {message}")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                self.log("✅ Configuração carregada.")
                self.check_generate_button_state()
                self.check_upload_button_state()
            except Exception as e: self.log(f"⚠️ Erro ao carregar config: {e}")

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.log("💾 Configuração salva.")
        except Exception as e: self.log(f"⚠️ Erro ao salvar config: {e}")

    def refresh_on_startup(self):
        if self.config.get("management_key"): self.run_background_task(self.fetch_collections_logic)
        if self.config.get("api_key"): self.run_background_task(self.fetch_models_logic)

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

    def check_generate_button_state(self):
        ok = (len(self.selected_json_files) > 0 and 
              self.output_directory and 
              self.config.get("api_key") and 
              self.config.get("selected_model"))
        self.generate_btn.setEnabled(bool(ok))

    def check_upload_button_state(self):
        ok = (len(self.generated_md_files) > 0 and 
              self.config.get("management_key") and 
              self.config.get("selected_collection_id"))
        self.upload_btn.setEnabled(bool(ok))

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
            self.check_upload_button_state()

    def apply_theme(self):
        if self.dark_mode:
            self.log_text.setStyleSheet("background-color: #1e1e1e; color: white; border: 1px solid #42A5F5;")
        else:
            self.log_text.setStyleSheet("background-color: #f5f5f5; color: black; border: 1px solid #42A5F5;")

    def run_background_task(self, fn, *args, dialog_update=None):
        worker = Worker(fn, *args)
        worker.signals.log.connect(self.log)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Erro", e))
        if dialog_update:
            def on_finished(result):
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and ("id" in result[0] or "collection_id" in result[0]):
                        self.collections_list = result
                        dialog_update.collection_combo.clear()
                        for c in result:
                            name = c.get("collection_name") or c.get("name") or c.get("collection_id")
                            cid = c.get("collection_id") or c.get("id")
                            dialog_update.collection_combo.addItem(f"{name} ({cid})", cid)
                    else:
                        self.available_models = result
                        dialog_update.model_combo.clear()
                        dialog_update.model_combo.addItems(result)
            worker.signals.finished.connect(on_finished)
        self.threadpool.start(worker)

    def fetch_collections_logic(self, signals):
        signals.log.emit("🔄 Carregando collections...")
        key = self.config.get("management_key")
        if not key: return []
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.get("https://management-api.x.ai/v1/collections", headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            cols = data.get("collections") or data.get("data") or []
            signals.log.emit(f"✅ {len(cols)} collections encontradas.")
            return cols
        return []

    def fetch_models_logic(self, signals):
        signals.log.emit("🔄 Buscando modelos...")
        key = self.config.get("api_key")
        if not key: return []
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.get("https://api.x.ai/v1/models", headers=headers, timeout=20)
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            signals.log.emit(f"✅ {len(models)} modelos encontrados.")
            return models
        return []

    def generate_md_files_click(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.generate_btn.setEnabled(False)
        self.generated_md_files = []
        
        worker = Worker(self.generate_logic)
        worker.signals.log.connect(self.log)
        worker.signals.progress.connect(lambda d: self.progress.setValue(int(d['percent'])))
        worker.signals.finished.connect(self.on_generation_finished)
        worker.signals.error.connect(self.on_generation_error)
        self.threadpool.start(worker)

    def on_generation_finished(self, result):
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.generated_md_files = result
        self.check_upload_button_state()
        QMessageBox.information(self, "Sucesso", f"Geração concluída! {len(result)} arquivos criados.")

    def on_generation_error(self, err):
        self.progress.setVisible(False)
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Erro", f"Erro na geração: {err}")

    def generate_logic(self, signals):
        output_path = Path(self.output_directory)
        generated = []
        total = len(self.selected_json_files)
        
        for i, json_file in enumerate(self.selected_json_files):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                items = data.get("data", []) if isinstance(data, dict) else data
                if not isinstance(items, list): continue
                
                for idx, item in enumerate(items):
                    conteudo = str(item.get("conteudo", "")).strip()
                    if not conteudo: continue
                    
                    safe_cat = re.sub(r"[<>:\"/\\|?*]", "", str(item.get("categoria", "sem_categoria")))
                    filename = f"{i}_{idx}_{safe_cat}.md"
                    filepath = output_path / filename
                    
                    with open(filepath, "w", encoding="utf-8") as f: f.write(conteudo)
                    
                    meta_path = filepath.with_name(f"{filepath.stem}_metadata.json")
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump({k: v for k, v in item.items() if k != "conteudo"}, f, indent=2, ensure_ascii=False)
                    
                    generated.append(str(filepath))
                
                signals.progress.emit({"percent": (i + 1) / total * 100})
                signals.log.emit(f"✅ Processado: {os.path.basename(json_file)}")
            except Exception as e: signals.log.emit(f"❌ Erro em {json_file}: {e}")
            
        return generated

    def upload_to_collection_click(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.upload_btn.setEnabled(False)
        
        worker = Worker(self.upload_logic)
        worker.signals.log.connect(self.log)
        worker.signals.progress.connect(lambda d: self.progress.setValue(int(d['percent'])))
        worker.signals.finished.connect(self.on_upload_finished)
        worker.signals.error.connect(self.on_upload_error)
        self.threadpool.start(worker)

    def on_upload_finished(self, result):
        self.progress.setVisible(False)
        self.upload_btn.setEnabled(True)
        QMessageBox.information(self, "Sucesso", "Upload concluído!")

    def on_upload_error(self, err):
        self.progress.setVisible(False)
        self.upload_btn.setEnabled(True)
        QMessageBox.critical(self, "Erro", f"Erro no upload: {err}")

    def upload_logic(self, signals):
        key = self.config.get("management_key")
        col_id = self.config.get("selected_collection_id")
        headers = {"Authorization": f"Bearer {key}"}
        total = len(self.generated_md_files)
        
        for i, md_file in enumerate(self.generated_md_files):
            try:
                meta_path = Path(md_file).with_name(f"{Path(md_file).stem}_metadata.json")
                with open(meta_path, "r", encoding="utf-8") as f: metadata = json.load(f)
                with open(md_file, "rb") as f: file_bytes = f.read()
                
                payload = {
                    "name": os.path.basename(md_file),
                    "content_type": "text/markdown",
                    "fields": json.dumps(metadata, ensure_ascii=False)
                }
                
                resp = requests.post(
                    f"https://management-api.x.ai/v1/collections/{col_id}/documents",
                    headers=headers,
                    data=payload,
                    files={"data": (os.path.basename(md_file), file_bytes, "text/markdown")},
                    timeout=60
                )
                
                if resp.status_code in [200, 201]:
                    signals.log.emit(f"✅ Upload: {os.path.basename(md_file)}")
                else:
                    signals.log.emit(f"❌ Falha {resp.status_code}: {os.path.basename(md_file)}")
                
                signals.progress.emit({"percent": (i + 1) / total * 100})
            except Exception as e: signals.log.emit(f"❌ Erro no upload de {md_file}: {e}")
            
        return True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CollectionUploaderV2App()
    window.show()
    sys.exit(app.exec())
