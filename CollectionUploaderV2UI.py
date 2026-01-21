#!/usr/bin/env python3
"""
CollectionUploaderV2UI.py - VERSÃO CORRIGIDA
Interface gráfica Flet para o CollectionUploader.py
Permite processar JSONs para MD e fazer upload para xAI Collections
"""

import flet as ft
import json
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import requests


class CollectionUploaderV2UI:
    """Interface gráfica para processamento e upload de sentenças."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Collection Uploader V2 - xAI (Upload Direto)"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        
        # Configurar janela (versão Flet 0.80+)
        try:
            self.page.window.width = 1000
            self.page.window.height = 800
        except:
            pass  # Fallback se window não estiver disponível
        
        # Estado da aplicação
        self.selected_json_files: List[str] = []
        self.output_directory: str = ""
        self.management_key: str = ""
        self.api_key: str = ""
        self.selected_model: str = "grok-beta"
        self.selected_collection_id: str = ""
        self.collections_list: List[Dict] = []
        self.generated_md_files: List[str] = []
        
        # Modelos disponíveis
        self.available_models = [
            "grok-beta",
            "grok-2-1212",
            "grok-2-vision-1212",
            "grok-vision-beta"
        ]
        
        # Estatísticas
        self.stats = {
            "total_processed": 0,
            "chunks_created": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }
        
        self.build_ui()
    
    def build_ui(self):
        """Constrói a interface do usuário."""
        
        # Título
        title = ft.Text(
            "Collection Uploader V2 - xAI (Upload Direto) Collections",
            size=28,
            weight=ft.FontWeight.BOLD,
            color="#1976D2"
        )
        
        # Seção de Configuração
        config_section = self.create_config_section()
        
        # Seção de Seleção de Arquivos
        files_section = self.create_files_section()
        
        # Seção de Ações
        actions_section = self.create_actions_section()
        
        # Janela de Feedback
        self.feedback_text = ft.TextField(
            label="Log de Execução",
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=15,
            bgcolor="#263238",
            color="#FFFFFF",
            border_color="#42A5F5"
        )
        
        # Layout principal
        self.page.add(
            ft.Column([
                title,
                ft.Divider(height=20),
                config_section,
                ft.Divider(height=20),
                files_section,
                ft.Divider(height=20),
                actions_section,
                ft.Divider(height=20),
                self.feedback_text
            ], spacing=10, scroll=ft.ScrollMode.AUTO)
        )
    
    def create_config_section(self) -> ft.Container:
        """Cria a seção de configuração."""
        
        # Campo Management Key
        self.management_key_field = ft.TextField(
            label="Management Key (xAI Collection)",
            hint_text="Chave de gerenciamento da Collection",
            password=True,
            can_reveal_password=True,
            width=450,
            on_change=self.on_management_key_change
        )
        
        # Campo API Key
        self.api_key_field = ft.TextField(
            label="API Key (Grok)",
            hint_text="Chave de API do Grok para geração de keywords",
            password=True,
            can_reveal_password=True,
            width=450,
            on_change=self.on_api_key_change
        )
        
        # Dropdown de Modelo
        self.model_dropdown = ft.Dropdown(
            label="Modelo para Geração de Keywords",
            hint_text="Selecione o modelo",
            options=[ft.dropdown.Option(model) for model in self.available_models],
            value="grok-beta",
            width=300,
            on_blur=self.on_model_change
        )
        
        # Botão para carregar Collections
        self.load_collections_btn = ft.ElevatedButton(
            "Carregar Collections",
            icon=ft.Icon(ft.icons.REFRESH),
            on_click=self.load_collections,
            disabled=True
        )
        
        # Dropdown de Collections
        self.collections_dropdown = ft.Dropdown(
            label="Collection para Upload",
            hint_text="Selecione a collection",
            options=[],
            width=450,
            on_blur=self.on_collection_change,
            disabled=True
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("⚙️ Configurações", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([self.management_key_field, self.load_collections_btn], spacing=10),
                self.collections_dropdown,
                ft.Row([self.api_key_field], spacing=10),
                ft.Row([self.model_dropdown], spacing=10),
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, "#90CAF9"),
            border_radius=10
        )
    
    def create_files_section(self) -> ft.Container:
        """Cria a seção de seleção de arquivos."""
        
        # Botão para selecionar JSON
        self.json_picker_btn = ft.ElevatedButton(
            "Selecionar Arquivos JSON",
            icon=ft.Icon(ft.icons.INSERT_DRIVE_FILE),
            on_click=self.pick_json_files
        )
        
        # Lista de arquivos selecionados
        self.json_files_list = ft.Text(
            "Nenhum arquivo selecionado",
            size=12,
            color="#616161"
        )
        
        # Botão para selecionar pasta de saída
        self.folder_picker_btn = ft.ElevatedButton(
            "Selecionar Pasta de Saída",
            icon=ft.Icon(ft.icons.FOLDER_OPEN),
            on_click=self.pick_output_folder
        )
        
        # Pasta de saída selecionada
        self.output_folder_text = ft.Text(
            "Nenhuma pasta selecionada",
            size=12,
            color="#616161"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 Seleção de Arquivos", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([self.json_picker_btn], spacing=10),
                self.json_files_list,
                ft.Divider(height=10),
                ft.Row([self.folder_picker_btn], spacing=10),
                self.output_folder_text,
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, "#A5D6A7"),
            border_radius=10
        )
    
    def create_actions_section(self) -> ft.Container:
        """Cria a seção de ações."""
        
        # Botão para gerar MDs
        self.generate_md_btn = ft.ElevatedButton(
            "Gerar Arquivos MD",
            icon=ft.Icon(ft.icons.CREATE_NEW_FOLDER),
            on_click=self.generate_md_files,
            disabled=True,
            bgcolor="#1976D2",
            color="#FFFFFF"
        )
        
        # Botão para fazer upload
        self.upload_btn = ft.ElevatedButton(
            "Upload para Collection",
            icon=ft.Icon(ft.icons.CLOUD_UPLOAD),
            on_click=self.upload_to_collection,
            disabled=True,
            bgcolor="#388E3C",
            color="#FFFFFF"
        )
        
        # Progress bar
        self.progress_bar = ft.ProgressBar(
            width=800,
            visible=False
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🚀 Ações", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.generate_md_btn,
                    self.upload_btn
                ], spacing=20),
                self.progress_bar
            ], spacing=15),
            padding=20,
            border=ft.border.all(1, "#FFCC80"),
            border_radius=10
        )
    
    # Callbacks
    
    def on_management_key_change(self, e):
        """Callback quando Management Key muda."""
        self.management_key = e.control.value
        self.load_collections_btn.disabled = len(self.management_key) == 0
        self.page.update()
    
    def on_api_key_change(self, e):
        """Callback quando API Key muda."""
        self.api_key = e.control.value
        self.check_generate_button_state()
    
    def on_model_change(self, e):
        """Callback quando modelo muda."""
        self.selected_model = e.control.value
    
    def on_collection_change(self, e):
        """Callback quando collection muda."""
        self.selected_collection_id = e.control.value
        self.check_upload_button_state()
    
    def pick_json_files(self, e):
        """Abre file picker para selecionar arquivos JSON."""
        def handle_result(e):
            self.on_json_files_selected(e)
        
        file_picker = ft.FilePicker(on_result=handle_result)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(
            dialog_title="Selecione os arquivos JSON",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json", "txt"]
        )
    
    def on_json_files_selected(self, e):
        """Callback quando arquivos JSON são selecionados."""
        if e.files:
            self.selected_json_files = [f.path for f in e.files]
            files_text = "\n".join([f"• {os.path.basename(path)}" for path in self.selected_json_files])
            self.json_files_list.value = f"Arquivos selecionados:\n{files_text}"
            self.json_files_list.color = "#388E3C"
            self.check_generate_button_state()
        else:
            self.selected_json_files = []
            self.json_files_list.value = "Nenhum arquivo selecionado"
            self.json_files_list.color = "#616161"
        
        self.page.update()
    
    def pick_output_folder(self, e):
        """Abre folder picker para selecionar pasta de saída."""
        def handle_result(e):
            self.on_output_folder_selected(e)
        
        folder_picker = ft.FilePicker(on_result=handle_result)
        self.page.overlay.append(folder_picker)
        self.page.update()
        folder_picker.get_directory_path(dialog_title="Selecione a pasta de saída")
    
    def on_output_folder_selected(self, e):
        """Callback quando pasta de saída é selecionada."""
        if e.path:
            self.output_directory = e.path
            self.output_folder_text.value = f"Pasta: {self.output_directory}"
            self.output_folder_text.color = "#388E3C"
            self.check_generate_button_state()
        else:
            self.output_directory = ""
            self.output_folder_text.value = "Nenhuma pasta selecionada"
            self.output_folder_text.color = "#616161"
        
        self.page.update()
    
    def check_generate_button_state(self):
        """Verifica se o botão de gerar MD pode ser habilitado."""
        can_generate = (
            len(self.selected_json_files) > 0 and
            len(self.output_directory) > 0 and
            len(self.api_key) > 0
        )
        self.generate_md_btn.disabled = not can_generate
        self.page.update()
    
    def check_upload_button_state(self):
        """Verifica se o botão de upload pode ser habilitado."""
        can_upload = (
            len(self.generated_md_files) > 0 and
            len(self.selected_collection_id) > 0 and
            len(self.management_key) > 0
        )
        self.upload_btn.disabled = not can_upload
        self.page.update()
    
    def log(self, message: str):
        """Adiciona mensagem ao log de feedback."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.feedback_text.value += log_entry
        self.page.update()
    
    async def load_collections(self, e):
        """Carrega lista de collections disponíveis."""
        self.log("🔄 Carregando collections disponíveis...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.x.ai/v1/collections",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.collections_list = data.get("collections", [])
                
                # Atualiza dropdown
                self.collections_dropdown.options = [
                    ft.dropdown.Option(
                        key=col["id"],
                        text=f"{col['name']} ({col['id'][:8]}...)"
                    )
                    for col in self.collections_list
                ]
                self.collections_dropdown.disabled = False
                
                self.log(f"✅ {len(self.collections_list)} collection(s) encontrada(s)")
            else:
                self.log(f"❌ Erro ao carregar collections: {response.status_code}")
                self.log(f"   {response.text}")
        
        except Exception as ex:
            self.log(f"❌ Erro ao carregar collections: {str(ex)}")
        
        self.page.update()
    
    async def generate_md_files(self, e):
        """Gera arquivos MD a partir dos JSONs selecionados."""
        self.log("=" * 70)
        self.log("🚀 Iniciando geração de arquivos MD...")
        
        self.progress_bar.visible = True
        self.generate_md_btn.disabled = True
        self.page.update()
        
        try:
            # Reset estatísticas
            self.stats = {
                "total_processed": 0,
                "chunks_created": 0,
                "categorias": set(),
                "tipos_acao": set(),
            }
            self.generated_md_files = []
            
            # Cria diretório de saída
            output_path = Path(self.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Processa cada arquivo JSON
            for json_file in self.selected_json_files:
                self.log(f"\n📄 Processando: {os.path.basename(json_file)}")
                
                # Carrega JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.log(f"   {len(data)} sentença(s) encontrada(s)")
                
                # Processa cada sentença
                for idx, item in enumerate(data, start=1):
                    await self.process_sentenca(item, idx, output_path)
                    
                    if idx % 5 == 0:
                        self.log(f"   ⏳ Processadas: {idx}/{len(data)}")
                        await asyncio.sleep(0.1)  # Permite atualização da UI
            
            self.log("\n✅ Geração de arquivos MD concluída!")
            self.print_statistics()
            
            # Habilita botão de upload
            self.check_upload_button_state()
            
        except Exception as ex:
            self.log(f"\n❌ Erro durante geração: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.progress_bar.visible = False
            self.generate_md_btn.disabled = False
            self.page.update()
    
    async def process_sentenca(self, item: Dict[str, Any], index: int, output_path: Path):
        """Processa uma sentença individual."""
        conteudo = item['conteudo'].strip()
        
        # Extrai keywords usando Grok
        keywords = await self.extract_keywords_with_grok(conteudo, item['categoria'])
        
        # Atualiza estatísticas
        self.stats['categorias'].add(item['categoria'])
        self.stats['tipos_acao'].add(item['tipo_acao'])
        
        # Divide em chunks
        chunks = self.chunk_text(conteudo)
        
        for chunk_idx, chunk in enumerate(chunks):
            # Cria nome de arquivo
            categoria_safe = self.sanitize_filename(item['categoria'])
            processo_safe = item['numero_processo'].replace('.', '_').replace('-', '_')
            
            if len(chunks) > 1:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx+1:02d}.md"
            else:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}.md"
            
            filepath = output_path / filename
            
            # Cria metadados
            metadata = self.create_metadata_header(item, keywords)
            
            # Adiciona indicador de chunk
            if len(chunks) > 1:
                chunk_info = f"\n**[Parte {chunk_idx+1} de {len(chunks)}]**\n\n"
            else:
                chunk_info = ""
            
            # Escreve arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(metadata)
                f.write(f"# {item['categoria']}\n\n")
                if chunk_info:
                    f.write(chunk_info)
                f.write(chunk)
            
            self.generated_md_files.append(str(filepath))
            self.stats['chunks_created'] += 1
        
        self.stats['total_processed'] += 1
    
    async def extract_keywords_with_grok(self, conteudo: str, categoria: str) -> List[str]:
        """Extrai keywords usando o modelo Grok."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Analise o seguinte texto jurídico trabalhista e extraia até 10 palavras-chave relevantes.
Foque em termos jurídicos, conceitos trabalhistas, leis citadas (CLT, Súmulas), e temas principais.

Categoria: {categoria}

Texto:
{conteudo[:1500]}

Retorne APENAS as palavras-chave separadas por vírgula, em minúsculas, usando underscore para espaços.
Exemplo: horas_extras, clt, adicional_noturno, art_71, sumula_437"""
            
            payload = {
                "model": self.selected_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                keywords_text = data["choices"][0]["message"]["content"].strip()
                keywords = [k.strip() for k in keywords_text.split(",")]
                return keywords[:10]
            else:
                # Fallback para keywords básicas
                return [categoria.lower().replace(" ", "_"), "clt", "trabalhista"]
        
        except Exception as ex:
            self.log(f"⚠️ Erro ao gerar keywords com Grok: {str(ex)}")
            return [categoria.lower().replace(" ", "_"), "clt", "trabalhista"]
    
    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        """Divide texto em chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def sanitize_filename(self, text: str) -> str:
        """Sanitiza nome de arquivo."""
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\s\-—]+', '_', text)
        return text[:100]
    
    def create_metadata_header(self, item: Dict[str, Any], keywords: List[str]) -> str:
        """Cria cabeçalho de metadados."""
        metadata_lines = [
            "---",
            f"categoria: {item['categoria']}",
            f"reclamada: {item['reclamada'] if item['reclamada'] else 'Não especificada'}",
            f"numero_processo: {item['numero_processo']}",
            f"data_publicacao: {item['data_publicacao'] if item['data_publicacao'] else 'Não informada'}",
            f"tipo_acao: {item['tipo_acao']}",
            f"keywords: {', '.join(keywords)}",
            "---",
            ""
        ]
        return "\n".join(metadata_lines)
    
    def print_statistics(self):
        """Imprime estatísticas."""
        self.log("\n" + "=" * 70)
        self.log("📊 ESTATÍSTICAS DO PROCESSAMENTO")
        self.log("=" * 70)
        self.log(f"Total de sentenças processadas:     {self.stats['total_processed']}")
        self.log(f"Total de arquivos MD criados:       {self.stats['chunks_created']}")
        self.log(f"Categorias únicas:                  {len(self.stats['categorias'])}")
        self.log(f"Tipos de ação únicos:               {len(self.stats['tipos_acao'])}")
        self.log("=" * 70)
    
    async def upload_to_collection(self, e):
        """Faz upload dos arquivos MD para a Collection."""
        self.log("\n" + "=" * 70)
        self.log("☁️ Iniciando upload para Collection...")
        
        self.progress_bar.visible = True
        self.upload_btn.disabled = True
        self.page.update()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.management_key}"
            }
            
            uploaded = 0
            failed = 0
            
            for md_file in self.generated_md_files:
                try:
                    with open(md_file, 'rb') as f:
                        files = {
                            'file': (os.path.basename(md_file), f, 'text/markdown')
                        }
                        
                        response = requests.post(
                            f"https://api.x.ai/v1/collections/{self.selected_collection_id}/files",
                            headers=headers,
                            files=files,
                            timeout=30
                        )
                        
                        if response.status_code in [200, 201]:
                            uploaded += 1
                        else:
                            failed += 1
                            self.log(f"❌ Falha no upload de {os.path.basename(md_file)}: {response.status_code}")
                    
                    if uploaded % 10 == 0:
                        self.log(f"⏳ Uploaded: {uploaded}/{len(self.generated_md_files)}")
                        await asyncio.sleep(0.1)
                
                except Exception as ex:
                    failed += 1
                    self.log(f"❌ Erro no upload de {os.path.basename(md_file)}: {str(ex)}")
            
            self.log("\n" + "=" * 70)
            self.log(f"✅ Upload concluído!")
            self.log(f"   Sucesso: {uploaded}")
            self.log(f"   Falhas: {failed}")
            self.log("=" * 70)
        
        except Exception as ex:
            self.log(f"\n❌ Erro durante upload: {str(ex)}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.progress_bar.visible = False
            self.upload_btn.disabled = False
            self.page.update()


def main(page: ft.Page):
    """Função principal."""
    app = CollectionUploaderV2UI(page)


if __name__ == "__main__":
    ft.app(target=main)
