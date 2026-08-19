"""
Aba do Cartão do Caso.
"""

import flet as ft
from pathlib import Path
from typing import Optional
from cartao_caso import ExtratorCartao, PersistenciaCartao, CartaoDoCaso


class AbaCartao:
    """Aba para extração e visualização do Cartão do Caso."""
    
    def __init__(self, app):
        self.app = app
        self.caminho_arquivo: Optional[Path] = None
        self.cartao_atual: Optional[CartaoDoCaso] = None
        self.extrator: Optional[ExtratorCartao] = None
        self.persistencia = PersistenciaCartao()
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.campo_arquivo = ft.Text(
            "Nenhum arquivo selecionado",
            size=14
        )
        
        self.btn_selecionar = ft.ElevatedButton(
            "Escolher Arquivo MD",
            icon=ft.icons.FOLDER_OPEN,
            on_click=self._selecionar_arquivo
        )
        
        self.btn_extrair = ft.ElevatedButton(
            "Extrair Cartão",
            icon=ft.icons.PLAY_ARROW,
            on_click=self._extrair_cartao,
            disabled=True
        )
        
        self.btn_confirmar = ft.ElevatedButton(
            "Confirmar e Salvar",
            icon=ft.icons.CHECK,
            on_click=self._confirmar_cartao,
            disabled=True
        )
        
        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_status = ft.Text("", size=12)
        
        self.area_resultado = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Extração do Cartão do Caso", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.Row([
                                self.btn_selecionar,
                                self.campo_arquivo,
                            ]),
                            ft.Row([
                                self.btn_extrair,
                                self.btn_confirmar,
                            ]),
                            self.progresso,
                            self.texto_status,
                        ]),
                        padding=20,
                    ),
                    ft.Divider(),
                    ft.Container(
                        content=self.area_resultado,
                        padding=20,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
        )
    
    def _selecionar_arquivo(self, e):
        """Abre diálogo de seleção de arquivo."""
        def on_result(result: ft.FilePickerResultEvent):
            if result.files:
                self.caminho_arquivo = Path(result.files[0].path)
                self.campo_arquivo.value = self.caminho_arquivo.name
                self.btn_extrair.disabled = False
                self.app.page.update()
        
        picker = ft.FilePicker(on_result=on_result)
        self.app.page.overlay.append(picker)
        self.app.page.update()
        
        picker.pick_files(
            allowed_extensions=["md"],
            dialog_title="Selecione o arquivo MD dos autos"
        )
    
    def _extrair_cartao(self, e):
        """Extrai o cartão do caso."""
        if not self.caminho_arquivo:
            self.app.mostrar_erro("Selecione um arquivo primeiro")
            return
        
        if not self.app.api_key:
            self.app.mostrar_erro("Configure a API Key nas Configurações")
            return
        
        self.progresso.visible = True
        self.texto_status.value = "Extraindo cartão..."
        self.btn_extrair.disabled = True
        self.app.page.update()
        
        try:
            self.extrator = ExtratorCartao(
                api_key=self.app.api_key,
                modelo="grok-beta"
            )
            
            self.cartao_atual = self.extrator.extrair(
                self.caminho_arquivo,
                callback_progresso=self._atualizar_progresso
            )
            
            self._exibir_cartao()
            
            self.btn_confirmar.disabled = False
            self.texto_status.value = "Extração concluída! Revise e confirme."
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro na extração: {str(ex)}")
            self.texto_status.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.btn_extrair.disabled = False
            self.app.page.update()
    
    def _atualizar_progresso(self, mensagem: str, progresso: float):
        """Atualiza barra de progresso."""
        self.texto_status.value = mensagem
        self.progresso.value = progresso
        self.app.page.update()
    
    def _exibir_cartao(self):
        """Exibe o cartão extraído."""
        if not self.cartao_atual:
            return
        
        self.area_resultado.controls.clear()
        
        self.area_resultado.controls.append(
            ft.Text(
                f"Processo: {self.cartao_atual.numero_processo or 'N/A'}",
                size=16,
                weight=ft.FontWeight.BOLD
            )
        )
        
        self.area_resultado.controls.append(
            ft.Text(f"Total de Pedidos: {len(self.cartao_atual.peticao_inicial.get('pedidos', []))}")
        )
        
        self.area_resultado.controls.append(
            ft.Text(f"Total de Questões: {len(self.cartao_atual.questoes)}")
        )
        
        if self.cartao_atual.avisos:
            self.area_resultado.controls.append(ft.Divider())
            self.area_resultado.controls.append(
                ft.Text("Avisos:", weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE)
            )
            for aviso in self.cartao_atual.avisos[:5]:
                self.area_resultado.controls.append(
                    ft.Text(f"• {aviso.descricao}", size=12, color=ft.colors.ORANGE_700)
                )
        
        self.app.page.update()
    
    def _confirmar_cartao(self, e):
        """Confirma e salva o cartão."""
        if not self.cartao_atual:
            return
        
        try:
            caminho_salvo = self.persistencia.salvar(self.cartao_atual)
            self.app.mostrar_info(f"Cartão salvo em:\n{caminho_salvo}")
            
            self.app.aba_dossie.cartao_confirmado = self.cartao_atual
            self.app.aba_dossie.habilitar_montagem()
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar: {str(ex)}")
