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
from ui_modelo_reasoning import SeletorModeloReasoning
from xai_models import DEFAULT_MODEL


class AbaMinuta:
    """Aba para geração da Minuta."""
    
    def __init__(self, app):
        self.app = app
        self.cartao_confirmado: Optional[CartaoDoCaso] = None
        self.dossie_confirmado: Optional[DossieProva] = None
        self.estrutura: Optional[EstruturaMinuta] = None
        self.collection_id: Optional[str] = None
        self.persistencia = PersistenciaMinuta()
        self.seletor_modelo: Optional[SeletorModeloReasoning] = None
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.texto_status = ft.Text(
            "Aguardando cartão e dossiê confirmados...",
            size=14,
            color=ft.Colors.ORANGE
        )

        self.seletor_modelo = SeletorModeloReasoning(self.app, "minuta")
        
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
            icon=ft.Icons.ACCOUNT_TREE,
            on_click=self._gerar_estrutura,
            disabled=True
        )
        
        self.btn_gerar_minuta = ft.ElevatedButton(
            "Gerar Minuta",
            icon=ft.Icons.CREATE,
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
                            ft.Row(
                                [
                                    *self.seletor_modelo.controles(),
                                    self.btn_gerar_estrutura,
                                    self.btn_gerar_minuta,
                                ],
                                wrap=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
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
        self.texto_status.color = ft.Colors.GREEN
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
            
            collections = [
                c for c in busca.listar_collections()
                if c.get("id")
            ]
            
            if not collections:
                self.app.mostrar_erro(
                    "Nenhuma Collection encontrada. Verifique a Management Key "
                    "ou crie uma Collection no console xAI."
                )
                return
            
            self.dropdown_collection.options = [
                ft.dropdown.Option(
                    key=c["id"],
                    text=c.get("name") or c["id"],
                )
                for c in collections
            ]
            
            preferida = getattr(self.app, "selected_collection_id", None)
            ids = {c["id"] for c in collections}
            if preferida and preferida in ids:
                escolhida = preferida
            else:
                escolhida = collections[0]["id"]
            
            self.dropdown_collection.value = escolhida
            self.collection_id = escolhida
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
        self.texto_progresso.value = (
            "Gerando estrutura... (pode levar alguns minutos; "
            "reasoning alto é limitado a medium nesta etapa)"
        )
        self.app.page.update()
        
        try:
            orquestrador = OrquestradorMinuta(
                api_key=self.app.api_key,
                management_key=self.app.management_key,
                modelo=getattr(self.app, "modelo_minuta", None) or DEFAULT_MODEL,
                reasoning_effort=getattr(self.app, "reasoning_minuta", None),
            )
            
            if self.collection_id:
                orquestrador.configurar_busca(self.collection_id)
            
            self.estrutura, avisos = orquestrador.gerar_estrutura(
                self.cartao_confirmado,
                self.dossie_confirmado
            )
            
            self._exibir_estrutura(avisos)

            n_topicos = len(self.estrutura.topicos) if self.estrutura else 0
            if n_topicos == 0:
                self.btn_gerar_minuta.disabled = True
                detalhe = "; ".join(avisos) if avisos else "nenhum tópico retornado"
                self.texto_progresso.value = (
                    f"Estrutura vazia — não foi possível listar tópicos ({detalhe})."
                )
                self.app.mostrar_erro(
                    "A estrutura veio vazia. Verifique modelo/reasoning da Minuta "
                    f"ou tente novamente.\n\n{detalhe}"
                )
            else:
                self.btn_gerar_minuta.disabled = False
                extra = f" ({len(avisos)} aviso(s))" if avisos else ""
                self.texto_progresso.value = (
                    f"Estrutura gerada com {n_topicos} tópico(s)! "
                    f"Revise e gere a minuta.{extra}"
                )
            
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao gerar estrutura: {str(ex)}")
            self.texto_progresso.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.app.page.update()
    
    def _exibir_estrutura(self, avisos: Optional[list] = None):
        """Exibe estrutura gerada."""
        self.area_resultado.controls.clear()

        self.area_resultado.controls.append(
            ft.Text("Estrutura da Sentença", size=18, weight=ft.FontWeight.BOLD)
        )

        if not self.estrutura or not self.estrutura.topicos:
            self.area_resultado.controls.append(
                ft.Text(
                    "Nenhum tópico para exibir.",
                    size=13,
                    color=ft.Colors.ORANGE_800,
                )
            )
            if avisos:
                for av in avisos:
                    self.area_resultado.controls.append(
                        ft.Text(f"• {av}", size=12, color=ft.Colors.RED_700)
                    )
            self.area_resultado.update()
            return

        for topico in sorted(
            self.estrutura.topicos,
            key=lambda t: (t.ordem, t.id),
        ):
            indent = "  " * max(0, (topico.nivel or 1) - 1)
            tamanho = max(11, 14 - max(1, topico.nivel or 1))
            tipo_txt = f" [{topico.tipo.value}]" if topico.tipo else ""
            qid_txt = f" ({topico.questao_id})" if topico.questao_id else ""
            self.area_resultado.controls.append(
                ft.Text(
                    f"{indent}{topico.ordem}. {topico.titulo}{tipo_txt}{qid_txt}",
                    size=tamanho,
                )
            )

        if avisos:
            self.area_resultado.controls.append(ft.Divider())
            for av in avisos:
                self.area_resultado.controls.append(
                    ft.Text(f"Aviso: {av}", size=11, color=ft.Colors.ORANGE_800)
                )

        try:
            self.area_resultado.update()
        except Exception:
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
                modelo=getattr(self.app, "modelo_minuta", None) or DEFAULT_MODEL,
                reasoning_effort=getattr(self.app, "reasoning_minuta", None),
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
