"""
Aba do Dossiê de Prova.
"""

import flet as ft
from pathlib import Path
from typing import Optional
from cartao_caso import CartaoDoCaso
from dossie_prova import OrquestradorDossie, PersistenciaDossie, DossieProva


class AbaDossie:
    """Aba para montagem do Dossiê de Prova."""
    
    def __init__(self, app):
        self.app = app
        self.cartao_confirmado: Optional[CartaoDoCaso] = None
        self.dossie_atual: Optional[DossieProva] = None
        self.caminho_autos: Optional[Path] = None
        self.persistencia = PersistenciaDossie()
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.texto_status_cartao = ft.Text(
            "Aguardando cartão confirmado...",
            size=14,
            color=ft.Colors.ORANGE
        )
        
        self.campo_autos = ft.Text(
            "Nenhum arquivo selecionado",
            size=14
        )
        
        self.btn_selecionar_autos = ft.ElevatedButton(
            "Escolher Autos (MD)",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._selecionar_autos,
            disabled=True
        )
        
        self.btn_montar = ft.ElevatedButton(
            "Montar Dossiê",
            icon=ft.Icons.BUILD,
            on_click=self._montar_dossie,
            disabled=True
        )
        
        self.btn_confirmar = ft.ElevatedButton(
            "Confirmar Dossiê",
            icon=ft.Icons.CHECK,
            on_click=self._confirmar_dossie,
            disabled=True
        )
        
        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_progresso = ft.Text("", size=12)
        
        self.area_dossie = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Dossiê de Prova", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.texto_status_cartao,
                            ft.Row([
                                self.btn_selecionar_autos,
                                self.campo_autos,
                            ]),
                            ft.Row([
                                self.btn_montar,
                                self.btn_confirmar,
                            ]),
                            self.progresso,
                            self.texto_progresso,
                        ]),
                        padding=20,
                    ),
                    ft.Divider(),
                    ft.Container(
                        content=self.area_dossie,
                        padding=20,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
        )
    
    def habilitar_montagem(self):
        """Habilita a montagem após cartão confirmado."""
        self.texto_status_cartao.value = f"Cartão confirmado: {self.cartao_confirmado.numero_processo or 'processo'}"
        self.texto_status_cartao.color = ft.Colors.GREEN
        self.btn_selecionar_autos.disabled = False
        self.app.page.update()
    
    async def _selecionar_autos(self, e):
        """Seleciona arquivo de autos."""
        picker = ft.FilePicker()
        files = await picker.pick_files(
            allowed_extensions=["md"],
            dialog_title="Selecione o arquivo MD dos autos",
            allow_multiple=False
        )
        
        if files:
            self.caminho_autos = Path(files[0].path)
            self.campo_autos.value = self.caminho_autos.name
            self.btn_montar.disabled = False
            self.app.page.update()
    
    async def _montar_dossie(self, e):
        """Monta o dossiê de prova."""
        if not self.cartao_confirmado or not self.caminho_autos:
            self.app.mostrar_erro("Cartão e autos são necessários")
            return
        
        if not self.app.api_key:
            self.app.mostrar_erro("Configure a API Key nas Configurações")
            return
        
        self.progresso.visible = True
        self.texto_progresso.value = "Montando dossiê..."
        self.btn_montar.disabled = True
        self.app.page.update()
        
        try:
            orquestrador = OrquestradorDossie(
                api_key=self.app.api_key,
                modelo="grok-beta"
            )
            
            self.dossie_atual, avisos = orquestrador.montar_dossie(
                self.cartao_confirmado,
                self.caminho_autos,
                callback_progresso=self._atualizar_progresso
            )
            
            self._exibir_dossie()
            
            self.btn_confirmar.disabled = False
            self.texto_progresso.value = "Dossiê montado! Revise e confirme."
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao montar dossiê: {str(ex)}")
            self.texto_progresso.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.btn_montar.disabled = False
            self.app.page.update()
    
    def _atualizar_progresso(self, mensagem: str, progresso: float):
        """Atualiza progresso."""
        self.texto_progresso.value = mensagem
        self.progresso.value = progresso
        self.app.page.update()
    
    def _exibir_dossie(self):
        """Exibe resumo do dossiê."""
        if not self.dossie_atual:
            return
        
        self.area_dossie.controls.clear()
        
        for dq in self.dossie_atual.dossies_por_questao:
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(
                            f"{dq.questao_id}: {dq.questao_titulo}",
                            size=16,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            f"Documentais: {len(dq.provas_documentais)} | "
                            f"Periciais: {len(dq.provas_periciais)} | "
                            f"Orais: {len(dq.provas_orais)}",
                            size=12
                        ),
                    ]),
                    padding=15,
                )
            )
            self.area_dossie.controls.append(card)
        
        self.app.page.update()
    
    async def _confirmar_dossie(self, e):
        """Confirma e salva o dossiê."""
        if not self.dossie_atual:
            return
        
        try:
            caminho_salvo = self.persistencia.salvar(self.dossie_atual)
            self.app.mostrar_info(f"Dossiê salvo em:\n{caminho_salvo}")
            
            self.app.aba_minuta.dossie_confirmado = self.dossie_atual
            self.app.aba_minuta.cartao_confirmado = self.cartao_confirmado
            self.app.aba_minuta.habilitar_geracao()
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar: {str(ex)}")
