#!/usr/bin/env python3
"""
IndexadorSentencas.py
Interface Flet para indexação de sentenças trabalhistas em xAI Collections.

Funcionalidades:
- Seleção de pasta com sentenças docx/odt
- Varredura e preview de documentos
- Upload idempotente para xAI Collections
- Relatório de indexação
- Configuração segura de credenciais
"""

import flet as ft
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import threading

# Importa módulos do indexador
from indexador.extractor import ExtratorSentenca, processar_pasta
from indexador.catalog import CatalogoLocal
from indexador.xai_uploader import XAICollectionsClient, criar_field_definitions_padrao


# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerenciador de configurações (sem API keys em texto claro)."""
    
    def __init__(self, config_file: str = "indexador_config.json"):
        # Usa diretório home do usuário
        home = Path.home()
        config_dir = home / '.indexador_sentencas'
        config_dir.mkdir(exist_ok=True)
        
        self.config_file = config_dir / config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Carrega configurações (sem API keys)."""
        default = {
            "selected_collection_id": "",
            "ultima_pasta": ""
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
            except Exception as e:
                logger.error(f"Erro ao carregar config: {e}")
        
        return default
    
    def save_config(self) -> None:
        """Salva configurações."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()


class IndexadorSentencasApp:
    """Aplicação principal de indexação."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.config_manager = ConfigManager()
        self.catalogo = CatalogoLocal()
        
        # Estado da aplicação
        self.api_key = ""
        self.management_key = ""
        self.selected_collection_id = self.config_manager.get("selected_collection_id")
        self.pasta_selecionada: Optional[Path] = None
        self.documentos_para_indexar: List[Dict] = []
        self.xai_client: Optional[XAICollectionsClient] = None
        
        # Configuração da página
        self.page.title = "Indexador de Sentenças Trabalhistas"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.window_width = 1200
        self.page.window_height = 800
        
        # Cria interface
        self.create_ui()
    
    def create_ui(self):
        """Cria a interface do usuário."""
        # Título
        titulo = ft.Text(
            "📚 Indexador de Sentenças Trabalhistas",
            size=24,
            weight=ft.FontWeight.BOLD,
        )
        
        # Seção de configurações
        self.api_key_field = ft.TextField(
            label="API Key (xAI)",
            password=True,
            can_reveal_password=True,
            width=400,
            on_change=self.on_credentials_changed,
        )
        
        self.management_key_field = ft.TextField(
            label="Management Key (xAI)",
            password=True,
            can_reveal_password=True,
            width=400,
            on_change=self.on_credentials_changed,
        )
        
        self.collection_dropdown = ft.Dropdown(
            label="Collection",
            hint_text="Selecione ou crie uma Collection",
            width=400,
            on_change=self.on_collection_changed,
        )
        
        self.btn_refresh_collections = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Atualizar lista de Collections",
            on_click=self.refresh_collections,
        )
        
        self.btn_new_collection = ft.ElevatedButton(
            text="Nova Collection",
            icon=ft.Icons.ADD,
            on_click=self.criar_nova_collection,
        )
        
        config_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("⚙️ Configurações", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.api_key_field,
                    self.management_key_field,
                    ft.Row([
                        self.collection_dropdown,
                        self.btn_refresh_collections,
                        self.btn_new_collection,
                    ]),
                ]),
                padding=20,
            ),
        )
        
        # Aviso de privacidade
        self.privacy_checkbox = ft.Checkbox(
            label="Declaro que estas sentenças são públicas e não estão em segredo de justiça",
            value=False,
        )
        
        privacy_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE, size=40),
                    ft.Text(
                        "⚠️ AVISO IMPORTANTE",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ORANGE,
                    ),
                    ft.Text(
                        "Indexe apenas sentenças públicas. "
                        "Não inclua processos em segredo de justiça nem autos de processos em curso.",
                        size=12,
                    ),
                    self.privacy_checkbox,
                ]),
                padding=15,
                bgcolor=ft.Colors.ORANGE_50,
            ),
        )
        
        # Seleção de pasta
        self.pasta_text = ft.Text("Nenhuma pasta selecionada", size=14)
        
        self.btn_select_folder = ft.ElevatedButton(
            text="Selecionar Pasta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.selecionar_pasta,
        )
        
        self.btn_scan = ft.ElevatedButton(
            text="Varrer Arquivos",
            icon=ft.Icons.SEARCH,
            on_click=self.varrer_arquivos,
            disabled=True,
        )
        
        folder_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📁 Seleção de Arquivos", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.pasta_text,
                    ft.Row([
                        self.btn_select_folder,
                        self.btn_scan,
                    ]),
                ]),
                padding=20,
            ),
        )
        
        # Tabela de documentos
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Sel.", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Arquivo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Processo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tópicos", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Empregador", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
        )
        
        self.table_container = ft.Container(
            content=ft.Column([
                self.table,
            ], scroll=ft.ScrollMode.AUTO),
            height=300,
        )
        
        table_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📄 Documentos Detectados", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.table_container,
                ]),
                padding=20,
            ),
        )
        
        # Botões de ação
        self.btn_indexar = ft.ElevatedButton(
            text="Indexar Selecionados",
            icon=ft.Icons.UPLOAD,
            on_click=self.iniciar_indexacao,
            disabled=True,
        )
        
        self.progress_bar = ft.ProgressBar(visible=False)
        self.progress_text = ft.Text("", size=12)
        
        # Log de atividades
        self.log_text = ft.Text("", size=12, selectable=True)
        self.log_container = ft.Container(
            content=ft.Column([
                self.log_text,
            ], scroll=ft.ScrollMode.AUTO),
            height=150,
            bgcolor=ft.Colors.GREY_100,
            padding=10,
            border_radius=5,
        )
        
        log_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📋 Log de Atividades", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.log_container,
                ]),
                padding=20,
            ),
        )
        
        # Layout principal
        main_layout = ft.Column([
            titulo,
            ft.Divider(),
            config_section,
            privacy_section,
            folder_section,
            table_section,
            ft.Row([
                self.btn_indexar,
            ]),
            self.progress_bar,
            self.progress_text,
            log_section,
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.page.add(main_layout)
        
        # Carrega configurações salvas
        self.carregar_credenciais_env()
    
    def carregar_credenciais_env(self):
        """Carrega credenciais de variáveis de ambiente."""
        api_key = os.getenv("XAI_API_KEY", "")
        management_key = os.getenv("XAI_MANAGEMENT_KEY", "")
        
        if api_key:
            self.api_key_field.value = api_key
            self.api_key = api_key
        
        if management_key:
            self.management_key_field.value = management_key
            self.management_key = management_key
        
        if api_key and management_key:
            self.atualizar_cliente()
            self.refresh_collections(None)
        
        self.page.update()
    
    def on_credentials_changed(self, e):
        """Callback quando credenciais mudam."""
        self.api_key = self.api_key_field.value
        self.management_key = self.management_key_field.value
        
        if self.api_key and self.management_key:
            self.atualizar_cliente()
    
    def atualizar_cliente(self):
        """Atualiza cliente xAI."""
        try:
            self.xai_client = XAICollectionsClient(
                self.api_key,
                self.management_key
            )
            self.log("✅ Cliente xAI configurado com sucesso")
        except Exception as e:
            self.log(f"❌ Erro ao configurar cliente: {e}")
    
    def refresh_collections(self, e):
        """Atualiza lista de Collections."""
        if not self.xai_client:
            self.log("⚠️ Configure as credenciais primeiro")
            return
        
        try:
            collections = self.xai_client.listar_collections()
            
            self.collection_dropdown.options = [
                ft.dropdown.Option(key=col["id"], text=col.get("name", col["id"]))
                for col in collections
            ]
            
            # Restaura seleção anterior
            if self.selected_collection_id:
                self.collection_dropdown.value = self.selected_collection_id
            
            self.page.update()
            self.log(f"✅ {len(collections)} Collections carregadas")
        
        except Exception as e:
            self.log(f"❌ Erro ao carregar Collections: {e}")
    
    def on_collection_changed(self, e):
        """Callback quando Collection é selecionada."""
        self.selected_collection_id = self.collection_dropdown.value
        self.config_manager.set("selected_collection_id", self.selected_collection_id)
        self.log(f"✅ Collection selecionada: {self.selected_collection_id}")
    
    def criar_nova_collection(self, e):
        """Abre diálogo para criar nova Collection."""
        nome_field = ft.TextField(
            label="Nome da Collection",
            hint_text="Ex: Sentenças TRT10 2024",
            width=400,
        )
        
        descricao_field = ft.TextField(
            label="Descrição (opcional)",
            multiline=True,
            min_lines=2,
            width=400,
        )
        
        def criar(e):
            nome = nome_field.value
            if not nome:
                self.log("⚠️ Nome da Collection é obrigatório")
                return
            
            try:
                field_defs = criar_field_definitions_padrao()
                nova_col = self.xai_client.criar_collection(
                    name=nome,
                    description=descricao_field.value or None,
                    field_definitions=field_defs
                )
                
                self.log(f"✅ Collection criada: {nova_col['id']}")
                self.refresh_collections(None)
                self.collection_dropdown.value = nova_col['id']
                self.selected_collection_id = nova_col['id']
                self.config_manager.set("selected_collection_id", self.selected_collection_id)
                
                dialog.open = False
                self.page.update()
            
            except Exception as ex:
                self.log(f"❌ Erro ao criar Collection: {ex}")
        
        dialog = ft.AlertDialog(
            title=ft.Text("Nova Collection"),
            content=ft.Column([
                nome_field,
                descricao_field,
                ft.Text(
                    "Os campos de metadados padrão serão criados automaticamente:\n"
                    "- numero_processo (obrigatório)\n"
                    "- categoria (obrigatório)\n"
                    "- data_publicacao\n"
                    "- reclamada\n"
                    "- tipo_acao",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self.fechar_dialog(dialog)),
                ft.ElevatedButton("Criar", on_click=criar),
            ],
        )
        
        self.abrir_dialog(dialog)
    
    def selecionar_pasta(self, e):
        """Abre diálogo para selecionar pasta."""
        def on_folder_selected(e: Any):
            if e.path:
                self.pasta_selecionada = Path(e.path)
                self.pasta_text.value = f"📁 {self.pasta_selecionada}"
                self.btn_scan.disabled = False
                self.config_manager.set("ultima_pasta", str(self.pasta_selecionada))
                self.page.update()
                self.log(f"Pasta selecionada: {self.pasta_selecionada}")
        
        folder_picker = ft.FilePicker(on_result=on_folder_selected)
        self.page.overlay.append(folder_picker)
        self.page.update()
        
        try:
            folder_picker.get_directory_path(
                dialog_title="Selecione a pasta com as sentenças"
            )
        except Exception:
            pass
    
    def varrer_arquivos(self, e):
        """Varre pasta e exibe arquivos detectados."""
        if not self.pasta_selecionada:
            self.log("⚠️ Selecione uma pasta primeiro")
            return
        
        self.log("🔍 Varrendo arquivos...")
        self.page.update()
        
        try:
            # Processa pasta
            registros, relatorio = processar_pasta(self.pasta_selecionada)
            
            # Agrupa registros por arquivo
            arquivos_map = {}
            for reg in registros:
                path = reg['source_path']
                if path not in arquivos_map:
                    arquivos_map[path] = {
                        'registros': [],
                        'arquivo': Path(path).name,
                        'processo': reg['numero_processo'],
                        'reclamada': reg['reclamada'],
                    }
                arquivos_map[path]['registros'].append(reg)
            
            # Verifica status de cada registro no catálogo
            self.documentos_para_indexar = []
            self.table.rows.clear()
            
            for path, info in arquivos_map.items():
                # Verifica se documentos já existem
                novos = 0
                existentes = 0
                
                for reg in info['registros']:
                    doc = self.catalogo.documento_existe(
                        reg['content_hash'],
                        reg['numero_processo'],
                        reg['categoria']
                    )
                    
                    reg['existe_no_catalogo'] = doc is not None
                    reg['selecionado'] = doc is None  # Seleciona apenas novos por padrão
                    
                    if doc is None:
                        novos += 1
                    else:
                        existentes += 1
                    
                    self.documentos_para_indexar.append(reg)
                
                # Status
                if novos > 0 and existentes == 0:
                    status = f"✨ Novo ({len(info['registros'])} tópicos)"
                    status_color = ft.Colors.GREEN
                elif novos == 0:
                    status = "✅ Já indexado"
                    status_color = ft.Colors.GREY
                else:
                    status = f"⚠️ Parcial ({novos} novos, {existentes} existentes)"
                    status_color = ft.Colors.ORANGE
                
                # Cria checkbox para seleção
                checkbox = ft.Checkbox(value=novos > 0, data=path)
                
                self.table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(checkbox),
                        ft.DataCell(ft.Text(info['arquivo'], size=11)),
                        ft.DataCell(ft.Text(info['processo'], size=11)),
                        ft.DataCell(ft.Text(str(len(info['registros'])), size=11)),
                        ft.DataCell(ft.Text(info['reclamada'] or "-", size=11)),
                        ft.DataCell(ft.Text(status, size=11, color=status_color)),
                    ])
                )
            
            self.btn_indexar.disabled = False
            self.page.update()
            
            self.log(f"✅ {len(arquivos_map)} arquivos encontrados, "
                    f"{len(registros)} tópicos extraídos")
            
            # Log de ignorados e erros
            if relatorio['arquivos_ignorados']:
                self.log(f"⚠️ {len(relatorio['arquivos_ignorados'])} arquivos ignorados")
            if relatorio['arquivos_erro']:
                self.log(f"❌ {len(relatorio['arquivos_erro'])} arquivos com erro")
        
        except Exception as ex:
            self.log(f"❌ Erro ao varrer arquivos: {ex}")
            import traceback
            logger.error(traceback.format_exc())
    
    def iniciar_indexacao(self, e):
        """Inicia processo de indexação."""
        # Validações
        if not self.privacy_checkbox.value:
            self.log("⚠️ Você deve confirmar que as sentenças são públicas")
            return
        
        if not self.selected_collection_id:
            self.log("⚠️ Selecione uma Collection")
            return
        
        if not self.xai_client:
            self.log("⚠️ Configure as credenciais primeiro")
            return
        
        # Coleta documentos selecionados
        docs_selecionados = []
        
        for i, row in enumerate(self.table.rows):
            checkbox = row.cells[0].content
            if checkbox.value:
                path = checkbox.data
                # Adiciona todos os registros deste arquivo
                docs_selecionados.extend([
                    doc for doc in self.documentos_para_indexar
                    if doc['source_path'] == path and not doc['existe_no_catalogo']
                ])
        
        if not docs_selecionados:
            self.log("⚠️ Nenhum documento novo selecionado")
            return
        
        self.log(f"🚀 Iniciando indexação de {len(docs_selecionados)} tópicos...")
        
        # Desabilita botões
        self.btn_indexar.disabled = True
        self.btn_scan.disabled = True
        self.progress_bar.visible = True
        self.page.update()
        
        # Executa indexação em thread separada
        thread = threading.Thread(
            target=self.executar_indexacao,
            args=(docs_selecionados,)
        )
        thread.start()
    
    def executar_indexacao(self, documentos: List[Dict]):
        """Executa indexação (roda em thread separada)."""
        total = len(documentos)
        sucesso = 0
        erros = 0
        
        for idx, doc in enumerate(documentos):
            try:
                # Atualiza progresso
                self.progress_bar.value = (idx + 1) / total
                self.progress_text.value = f"Indexando {idx + 1}/{total}: {doc['categoria'][:50]}..."
                self.page.update()
                
                # Chunka se necessário
                chunks = self.xai_client.chunkar_conteudo_grande(doc['conteudo'])
                
                # Upload de cada chunk
                for chunk_idx, chunk in enumerate(chunks):
                    parte = chunk_idx + 1 if len(chunks) > 1 else None
                    total_partes = len(chunks) if len(chunks) > 1 else None
                    
                    file_id = self.xai_client.upload_documento_completo(
                        collection_id=self.selected_collection_id,
                        categoria=doc['categoria'],
                        conteudo=chunk,
                        numero_processo=doc['numero_processo'],
                        data_publicacao=doc['data_publicacao'],
                        reclamada=doc['reclamada'],
                        tipo_acao=doc['tipo_acao'],
                        parte_indice=parte,
                        total_partes=total_partes
                    )
                    
                    # Registra no catálogo
                    self.catalogo.adicionar_documento(
                        content_hash=doc['content_hash'],
                        file_id=file_id,
                        collection_id=self.selected_collection_id,
                        numero_processo=doc['numero_processo'],
                        categoria=doc['categoria'],
                        source_path=doc['source_path'],
                        reclamada=doc['reclamada'],
                        tipo_acao=doc['tipo_acao'],
                        data_publicacao=doc['data_publicacao']
                    )
                
                sucesso += 1
                self.log(f"✅ [{idx+1}/{total}] {doc['categoria'][:50]}")
            
            except Exception as e:
                erros += 1
                self.log(f"❌ [{idx+1}/{total}] Erro: {e}")
                logger.error(f"Erro ao indexar: {e}", exc_info=True)
        
        # Finaliza
        self.progress_bar.visible = False
        self.progress_text.value = ""
        self.btn_indexar.disabled = False
        self.btn_scan.disabled = False
        
        self.log(f"\n{'='*60}")
        self.log(f"✅ Indexação concluída!")
        self.log(f"   Sucesso: {sucesso}")
        self.log(f"   Erros: {erros}")
        self.log(f"   Total: {total}")
        self.log(f"{'='*60}\n")
        
        self.page.update()
    
    def log(self, mensagem: str):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.value += f"[{timestamp}] {mensagem}\n"
        self.page.update()
    
    def abrir_dialog(self, dialog):
        """Abre diálogo."""
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def fechar_dialog(self, dialog):
        """Fecha diálogo."""
        dialog.open = False
        self.page.update()


def main(page: ft.Page):
    """Função principal."""
    IndexadorSentencasApp(page)


if __name__ == "__main__":
    ft.app(target=main)
