"""
Aba da Minuta.
"""

import flet as ft
from typing import Optional, Dict, Any
from cartao_caso import CartaoDoCaso
from dossie_prova import DossieProva
from minuta import (
    OrquestradorMinuta,
    PersistenciaMinuta,
    EstruturaMinuta,
    MinutaCompleta,
    MinutaTopico,
)


class AbaMinuta:
    """Aba para geração da Minuta."""
    
    def __init__(self, app):
        self.app = app
        self.cartao_confirmado: Optional[CartaoDoCaso] = None
        self.dossie_confirmado: Optional[DossieProva] = None
        self.estrutura: Optional[EstruturaMinuta] = None
        self.collection_id: Optional[str] = None
        self.persistencia = PersistenciaMinuta()
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.texto_status = ft.Text(
            "Aguardando cartão e dossiê confirmados...",
            size=14,
            color=ft.colors.ORANGE
        )
        
        self.dropdown_collection = ft.Dropdown(
            label="Collection de Precedentes",
            width=400,
            disabled=True,
            on_change=self._selecionar_collection
        )
        
        self.campo_top_k = ft.TextField(
            label="Top K",
            value="5",
            width=100
        )
        
        self.dropdown_mode = ft.Dropdown(
            label="Modo de Busca",
            width=150,
            value="hybrid",
            options=[
                ft.dropdown.Option("hybrid", "Híbrido"),
                ft.dropdown.Option("keyword", "Palavra-chave"),
                ft.dropdown.Option("semantic", "Semântico"),
            ]
        )
        
        self.btn_gerar_estrutura = ft.ElevatedButton(
            "Gerar Estrutura",
            icon=ft.icons.ACCOUNT_TREE,
            on_click=self._gerar_estrutura,
            disabled=True
        )
        
        self.btn_gerar_minuta = ft.ElevatedButton(
            "Gerar Minuta",
            icon=ft.icons.CREATE,
            on_click=self._gerar_minuta,
            disabled=True
        )
        
        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_progresso = ft.Text("", size=12)
        
        self.area_resultado = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Geração de Minuta", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            self.texto_status,
                            self.dropdown_collection,
                            ft.Row([
                                self.campo_top_k,
                                self.dropdown_mode,
                            ]),
                            ft.Row([
                                self.btn_gerar_estrutura,
                                self.btn_gerar_minuta,
                            ]),
                            self.progresso,
                            self.texto_progresso,
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
    
    def habilitar_geracao(self):
        """Habilita geração após dossiê confirmado."""
        self.texto_status.value = "Cartão e dossiê confirmados! Configure a Collection."
        self.texto_status.color = ft.colors.GREEN
        self.dropdown_collection.disabled = False
        self._carregar_collections()
        self.app.page.update()
    
    def _carregar_collections(self):
        """Carrega lista de collections."""
        if not self.app.management_key:
            self.app.mostrar_erro("Configure a Management Key nas Configurações")
            return
        
        try:
            from minuta import BuscaPrecedentes
            busca = BuscaPrecedentes(
                self.app.api_key,
                self.app.management_key
            )
            
            collections = busca.listar_collections()
            
            self.dropdown_collection.options = [
                ft.dropdown.Option(c["id"], c["name"])
                for c in collections
            ]
            
            if collections:
                self.dropdown_collection.value = collections[0]["id"]
                self.collection_id = collections[0]["id"]
                self.btn_gerar_estrutura.disabled = False
            
            self.app.page.update()
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao carregar collections: {str(ex)}")
    
    def _selecionar_collection(self, e):
        """Seleciona collection."""
        self.collection_id = self.dropdown_collection.value
        self.btn_gerar_estrutura.disabled = False
        self.app.page.update()
    
    def _gerar_estrutura(self, e):
        """Gera estrutura de tópicos."""
        if not self.cartao_confirmado or not self.dossie_confirmado:
            return
        
        if not self.app.api_key:
            self.app.mostrar_erro("Configure a API Key nas Configurações")
            return
        
        self.progresso.visible = True
        self.texto_progresso.value = "Gerando estrutura..."
        self.app.page.update()
        
        try:
            orquestrador = OrquestradorMinuta(
                api_key=self.app.api_key,
                management_key=self.app.management_key,
                modelo="grok-beta"
            )
            
            if self.collection_id:
                orquestrador.configurar_busca(self.collection_id)
            
            self.estrutura, avisos = orquestrador.gerar_estrutura(
                self.cartao_confirmado,
                self.dossie_confirmado
            )
            
            self._exibir_estrutura()
            
            self.btn_gerar_minuta.disabled = False
            self.texto_progresso.value = "Estrutura gerada! Revise e gere a minuta."
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao gerar estrutura: {str(ex)}")
            self.texto_progresso.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.app.page.update()
    
    def _exibir_estrutura(self):
        """Exibe estrutura gerada."""
        if not self.estrutura:
            return
        
        self.area_resultado.controls.clear()
        
        self.area_resultado.controls.append(
            ft.Text("Estrutura da Sentença", size=18, weight=ft.FontWeight.BOLD)
        )
        
        for topico in self.estrutura.topicos:
            indent = "  " * (topico.nivel - 1)
            self.area_resultado.controls.append(
                ft.Text(
                    f"{indent}{topico.ordem}. {topico.titulo}",
                    size=14 - topico.nivel
                )
            )
        
        self.app.page.update()
    
    def _gerar_minuta(self, e):
        """Gera minuta completa."""
        if not self.estrutura:
            self.app.mostrar_erro("Gere a estrutura primeiro")
            return
        
        self.progresso.visible = True
        self.texto_progresso.value = "Gerando minuta..."
        self.app.page.update()
        
        try:
            orquestrador = OrquestradorMinuta(
                api_key=self.app.api_key,
                management_key=self.app.management_key,
                modelo="grok-beta"
            )
            
            if self.collection_id:
                orquestrador.configurar_busca(self.collection_id)
            
            criterios = {
                "top_k": int(self.campo_top_k.value or "5"),
                "retrieval_mode": self.dropdown_mode.value,
            }
            
            minutas_definitivas = []
            
            for i, topico in enumerate(self.estrutura.topicos):
                self.texto_progresso.value = f"Gerando minuta {i+1}/{len(self.estrutura.topicos)}..."
                self.app.page.update()
                
                minuta_previa, _ = orquestrador.gerar_minuta_previa(
                    topico,
                    self.cartao_confirmado,
                    self.dossie_confirmado
                )
                
                minuta_previa.aprovada = True
                
                minuta_def, _ = orquestrador.gerar_minuta_definitiva(
                    topico,
                    minuta_previa,
                    self.cartao_confirmado,
                    self.dossie_confirmado,
                    criterios
                )
                
                minutas_definitivas.append(minuta_def)
            
            minuta_final_md = "\n\n".join([
                f"## {m.titulo}\n\n{m.conteudo}"
                for m in minutas_definitivas
            ])
            
            minuta_completa = MinutaCompleta(
                cartao_origem=self.cartao_confirmado.arquivo_origem,
                dossie_origem=self.dossie_confirmado.arquivo_autos,
                collection_id=self.collection_id,
                estrutura=self.estrutura,
                minutas_definitivas=minutas_definitivas,
                minuta_final_md=minuta_final_md,
                criterios_busca=criterios
            )
            
            caminho_json = self.persistencia.salvar(minuta_completa)
            caminho_md = self.persistencia.salvar_markdown(minuta_completa)
            
            self.texto_progresso.value = f"Minuta salva em:\n{caminho_md}"
            
            self.area_resultado.controls.clear()
            self.area_resultado.controls.append(
                ft.Text("Minuta Gerada", size=18, weight=ft.FontWeight.BOLD)
            )
            self.area_resultado.controls.append(
                ft.Text(minuta_final_md[:2000] + "...", size=12)
            )
            
            self.app.mostrar_info(f"Minuta salva:\nJSON: {caminho_json}\nMD: {caminho_md}")
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao gerar minuta: {str(ex)}")
            self.texto_progresso.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.app.page.update()
