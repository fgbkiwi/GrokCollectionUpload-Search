"""
Aba do Indexador de Sentenças.
"""

import flet as ft
from pathlib import Path
from typing import Optional


class AbaIndexador:
    """Aba para indexação de sentenças na Collection xAI."""
    
    def __init__(self, app):
        self.app = app
        self.caminho_pasta: Optional[Path] = None
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.campo_pasta = ft.Text(
            "Nenhuma pasta selecionada",
            size=14
        )
        
        self.btn_selecionar_pasta = ft.ElevatedButton(
            "Escolher Pasta de Sentenças (MD)",
            icon=ft.icons.FOLDER_OPEN,
            on_click=self._selecionar_pasta
        )
        
        self.btn_indexar = ft.ElevatedButton(
            "Indexar na Collection",
            icon=ft.icons.UPLOAD,
            on_click=self._indexar,
            disabled=True
        )
        
        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_progresso = ft.Text("", size=12)
        
        self.area_log = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Indexador de Sentenças", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Indexa sentenças publicadas na Collection xAI para busca de precedentes",
                                size=12,
                                color=ft.colors.GREY_700
                            ),
                            ft.Divider(),
                            ft.Row([
                                self.btn_selecionar_pasta,
                                self.campo_pasta,
                            ]),
                            self.btn_indexar,
                            self.progresso,
                            self.texto_progresso,
                        ]),
                        padding=20,
                    ),
                    ft.Divider(),
                    ft.Container(
                        content=self.area_log,
                        padding=20,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
        )
    
    def _selecionar_pasta(self, e):
        """Seleciona pasta de sentenças."""
        def on_result(result: ft.FilePickerResultEvent):
            if result.path:
                self.caminho_pasta = Path(result.path)
                self.campo_pasta.value = str(self.caminho_pasta)
                self.btn_indexar.disabled = False
                self.app.page.update()
        
        picker = ft.FilePicker(on_result=on_result)
        self.app.page.overlay.append(picker)
        self.app.page.update()
        
        picker.get_directory_path(
            dialog_title="Selecione a pasta com sentenças em MD"
        )
    
    def _indexar(self, e):
        """Indexa sentenças na Collection."""
        if not self.caminho_pasta:
            return
        
        if not self.app.api_key or not self.app.management_key:
            self.app.mostrar_erro(
                "Configure as chaves de API e Management nas Configurações"
            )
            return
        
        self.progresso.visible = True
        self.texto_progresso.value = "Indexando sentenças..."
        self.btn_indexar.disabled = True
        self.area_log.controls.clear()
        self.app.page.update()
        
        try:
            from indexador import Catalog, Extractor, XaiUploader
            
            catalog = Catalog(self.caminho_pasta)
            documentos = catalog.listar_documentos()
            
            self._log(f"Encontrados {len(documentos)} documentos")
            
            extractor = Extractor()
            uploader = XaiUploader(
                api_key=self.app.api_key,
                management_key=self.app.management_key
            )
            
            collections = uploader.listar_collections()
            if not collections:
                self.app.mostrar_erro("Nenhuma Collection encontrada. Crie uma Collection primeiro.")
                return
            
            collection_id = collections[0]["id"]
            self._log(f"Usando Collection: {collections[0]['name']}")
            
            total = len(documentos)
            for i, doc_path in enumerate(documentos):
                self.texto_progresso.value = f"Processando {i+1}/{total}..."
                self.progresso.value = (i + 1) / total
                self.app.page.update()
                
                try:
                    dados = extractor.extrair_metadados(doc_path)
                    uploader.upload_documento(collection_id, dados)
                    self._log(f"✓ {doc_path.name}")
                except Exception as ex:
                    self._log(f"✗ {doc_path.name}: {str(ex)}", erro=True)
            
            self.texto_progresso.value = f"Indexação concluída! {total} documentos processados."
            self._log("\nIndexação concluída!")
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro na indexação: {str(ex)}")
            self._log(f"ERRO: {str(ex)}", erro=True)
        finally:
            self.progresso.visible = False
            self.btn_indexar.disabled = False
            self.app.page.update()
    
    def _log(self, mensagem: str, erro: bool = False):
        """Adiciona mensagem ao log."""
        cor = ft.colors.RED if erro else ft.colors.BLACK
        self.area_log.controls.append(
            ft.Text(mensagem, size=12, color=cor)
        )
        self.app.page.update()
