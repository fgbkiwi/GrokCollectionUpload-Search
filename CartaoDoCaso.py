#!/usr/bin/env python3
"""
Cartão do Caso - Aplicação Flet

Interface gráfica para extração, validação e persistência de
cartões estruturados de autos trabalhistas.
"""

import flet as ft
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from cartao_caso import (
    CartaoDoCaso,
    ExtratorCartao,
    PersistenciaCartao,
    Pedido,
    Questao,
    Aviso
)


class CartaoDoCasoApp:
    """Aplicação principal do Cartão do Caso."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Cartão do Caso - Extração Estruturada de Autos"
        self.page.window_width = 1400
        self.page.window_height = 900
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.api_key = ""
        self.modelo_grok = "grok-beta"
        self.caminho_arquivo: Optional[Path] = None
        self.cartao_atual: Optional[CartaoDoCaso] = None
        
        self.extrator: Optional[ExtratorCartao] = None
        self.persistencia = PersistenciaCartao()
        
        self._construir_ui()
    
    def _construir_ui(self):
        """Constrói a interface do usuário."""
        self.campo_api_key = ft.TextField(
            label="API Key xAI (Grok)",
            hint_text="xai-...",
            password=True,
            can_reveal_password=True,
            width=400,
            on_change=self._atualizar_api_key
        )
        
        self.dropdown_modelo = ft.Dropdown(
            label="Modelo Grok",
            width=300,
            options=[
                ft.dropdown.Option("grok-beta", "grok-beta (Recomendado)"),
                ft.dropdown.Option("grok-2-1212", "grok-2-1212"),
                ft.dropdown.Option("grok-4.6", "grok-4.6"),
            ],
            value="grok-beta",
            on_change=self._atualizar_modelo
        )
        
        self.campo_arquivo = ft.Text(
            "Nenhum arquivo selecionado",
            size=14,
            color=ft.colors.GREY_700
        )
        
        self.btn_selecionar = ft.ElevatedButton(
            "Escolher Arquivo/Pasta MD",
            icon=ft.icons.FOLDER_OPEN,
            on_click=self._selecionar_arquivo
        )
        
        self.btn_extrair = ft.ElevatedButton(
            "Extrair Cartão",
            icon=ft.icons.PLAY_ARROW,
            on_click=self._extrair_cartao,
            disabled=True
        )
        
        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_progresso = ft.Text("", size=12, color=ft.colors.BLUE)
        
        self.abas = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Pedidos",
                    icon=ft.icons.LIST_ALT,
                    content=ft.Container(padding=10)
                ),
                ft.Tab(
                    text="Questões",
                    icon=ft.icons.QUESTION_ANSWER,
                    content=ft.Container(padding=10)
                ),
                ft.Tab(
                    text="Avisos",
                    icon=ft.icons.WARNING,
                    content=ft.Container(padding=10)
                ),
                ft.Tab(
                    text="JSON",
                    icon=ft.icons.CODE,
                    content=ft.Container(padding=10)
                ),
            ],
            visible=False
        )
        
        self.btn_confirmar = ft.ElevatedButton(
            "Confirmar Cartão",
            icon=ft.icons.CHECK_CIRCLE,
            on_click=self._confirmar_cartao,
            disabled=True,
            bgcolor=ft.colors.GREEN,
            color=ft.colors.WHITE
        )
        
        self.btn_voltar = ft.ElevatedButton(
            "Voltar a Extrair",
            icon=ft.icons.REFRESH,
            on_click=self._voltar_extrair,
            disabled=True
        )
        
        self.btn_exportar = ft.ElevatedButton(
            "Exportar JSON",
            icon=ft.icons.DOWNLOAD,
            on_click=self._exportar_json,
            disabled=True
        )
        
        cabecalho = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Cartão do Caso",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.BLUE_900
                ),
                ft.Text(
                    "Extração estruturada de autos trabalhistas",
                    size=14,
                    color=ft.colors.GREY_700
                ),
            ]),
            padding=20,
            bgcolor=ft.colors.BLUE_50,
        )
        
        painel_config = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("⚙️ Configuração", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([self.campo_api_key, self.dropdown_modelo]),
                    ft.Divider(),
                    ft.Text("📄 Selecionar Autos", size=18, weight=ft.FontWeight.BOLD),
                    self.btn_selecionar,
                    self.campo_arquivo,
                    ft.Divider(),
                    self.btn_extrair,
                    self.progresso,
                    self.texto_progresso,
                ]),
                padding=20
            )
        )
        
        painel_acoes = ft.Container(
            content=ft.Row([
                self.btn_confirmar,
                self.btn_voltar,
                self.btn_exportar,
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=10,
            visible=False
        )
        
        self.painel_acoes_container = painel_acoes
        
        self.page.add(
            cabecalho,
            painel_config,
            self.abas,
            painel_acoes
        )
    
    def _atualizar_api_key(self, e):
        """Atualiza API key."""
        self.api_key = e.control.value
        self._verificar_pode_extrair()
    
    def _atualizar_modelo(self, e):
        """Atualiza modelo selecionado."""
        self.modelo_grok = e.control.value
    
    def _verificar_pode_extrair(self):
        """Verifica se pode habilitar botão de extração."""
        self.btn_extrair.disabled = not (self.api_key and self.caminho_arquivo)
        self.page.update()
    
    def _selecionar_arquivo(self, e):
        """Abre diálogo para selecionar arquivo ou pasta."""
        def resultado_arquivo(result: ft.FilePickerResultEvent):
            if result.files:
                self.caminho_arquivo = Path(result.files[0].path)
                self.campo_arquivo.value = str(self.caminho_arquivo)
                self.campo_arquivo.color = ft.colors.GREEN_700
                self._verificar_pode_extrair()
            elif result.path:
                self.caminho_arquivo = Path(result.path)
                self.campo_arquivo.value = str(self.caminho_arquivo)
                self.campo_arquivo.color = ft.colors.GREEN_700
                self._verificar_pode_extrair()
            self.page.update()
        
        picker = ft.FilePicker(on_result=resultado_arquivo)
        self.page.overlay.append(picker)
        self.page.update()
        
        picker.pick_files(
            dialog_title="Escolher arquivo MD de autos",
            allowed_extensions=["md"],
            allow_multiple=False
        )
    
    def _mostrar_progresso(self, mensagem: str):
        """Mostra progresso."""
        self.texto_progresso.value = mensagem
        self.page.update()
    
    def _extrair_cartao(self, e):
        """Extrai cartão do arquivo selecionado."""
        if not self.api_key:
            self._mostrar_erro("Configure a API Key primeiro")
            return
        
        if not self.caminho_arquivo or not self.caminho_arquivo.exists():
            self._mostrar_erro("Arquivo não encontrado")
            return
        
        self.progresso.visible = True
        self.btn_extrair.disabled = True
        self.page.update()
        
        try:
            self.extrator = ExtratorCartao(self.api_key, self.modelo_grok)
            
            if self.caminho_arquivo.is_file():
                self.cartao_atual = self.extrator.extrair_de_arquivo(
                    self.caminho_arquivo,
                    self._mostrar_progresso
                )
            else:
                cartoes = self.extrator.extrair_de_pasta(
                    self.caminho_arquivo,
                    self._mostrar_progresso
                )
                if cartoes:
                    self.cartao_atual = cartoes[0]
            
            self._mostrar_cartao()
            self._mostrar_sucesso("Cartão extraído com sucesso!")
            
        except Exception as ex:
            self._mostrar_erro(f"Erro na extração: {ex}")
        
        finally:
            self.progresso.visible = False
            self.btn_extrair.disabled = False
            self.page.update()
    
    def _mostrar_cartao(self):
        """Mostra cartão nas abas."""
        if not self.cartao_atual:
            return
        
        self._construir_aba_pedidos()
        self._construir_aba_questoes()
        self._construir_aba_avisos()
        self._construir_aba_json()
        
        self.abas.visible = True
        self.painel_acoes_container.visible = True
        self.btn_confirmar.disabled = False
        self.btn_voltar.disabled = False
        self.btn_exportar.disabled = False
        
        self.page.update()
    
    def _construir_aba_pedidos(self):
        """Constrói aba de pedidos."""
        pedidos = self.cartao_atual.peticao_inicial.get("pedidos", [])
        
        if not pedidos:
            self.abas.tabs[0].content = ft.Container(
                content=ft.Text("Nenhum pedido encontrado", size=16),
                padding=20
            )
            return
        
        linhas = []
        
        for pedido_dict in pedidos:
            pedido = Pedido(**pedido_dict) if isinstance(pedido_dict, dict) else pedido_dict
            
            contestacao = next(
                (c for c in self.cartao_atual.contestacoes if c.pedido_id == pedido.id),
                None
            )
            
            linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(pedido.id)),
                        ft.DataCell(
                            ft.Text(pedido.descricao[:80] + "..." if len(pedido.descricao) > 80 else pedido.descricao)
                        ),
                        ft.DataCell(ft.Text(pedido.periodo or "-")),
                        ft.DataCell(ft.Text("Sim" if pedido.reflexos else "Não")),
                        ft.DataCell(
                            ft.Text(
                                "Sim" if contestacao and contestacao.impugnacao_especifica else "Não",
                                color=ft.colors.GREEN if contestacao and contestacao.impugnacao_especifica else ft.colors.RED
                            )
                        ),
                    ]
                )
            )
        
        tabela = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Descrição", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Período", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Reflexos", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Impugnação Específica", weight=ft.FontWeight.BOLD)),
            ],
            rows=linhas,
        )
        
        self.abas.tabs[0].content = ft.Container(
            content=ft.Column([
                ft.Text(f"Total de pedidos: {len(pedidos)}", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=tabela,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=5,
                    padding=10
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=10
        )
    
    def _construir_aba_questoes(self):
        """Constrói aba de questões."""
        questoes = self.cartao_atual.questoes
        
        if not questoes:
            self.abas.tabs[1].content = ft.Container(
                content=ft.Text("Nenhuma questão encontrada", size=16),
                padding=20
            )
            return
        
        linhas = []
        
        for questao in questoes:
            linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(questao.id)),
                        ft.DataCell(ft.Text(questao.titulo[:60] + "..." if len(questao.titulo) > 60 else questao.titulo)),
                        ft.DataCell(ft.Text(questao.tipo)),
                        ft.DataCell(ft.Text(questao.momento)),
                        ft.DataCell(
                            ft.Checkbox(
                                value=questao.de_oficio,
                                disabled=True
                            )
                        ),
                        ft.DataCell(
                            ft.Checkbox(
                                value=questao.mencionar_na_minuta,
                                disabled=False,
                                on_change=lambda e, q=questao: self._toggle_mencionar(q, e.control.value)
                            )
                        ),
                    ]
                )
            )
        
        tabela = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Título", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tipo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Momento", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("De Ofício", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Mencionar", weight=ft.FontWeight.BOLD)),
            ],
            rows=linhas,
        )
        
        self.abas.tabs[1].content = ft.Container(
            content=ft.Column([
                ft.Text(f"Total de questões: {len(questoes)}", size=16, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "✏️ Você pode desmarcar questões que não devem ser mencionadas na minuta",
                    size=12,
                    color=ft.colors.BLUE_700
                ),
                ft.Container(
                    content=tabela,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=5,
                    padding=10
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=10
        )
    
    def _toggle_mencionar(self, questao: Questao, valor: bool):
        """Toggle para mencionar questão na minuta."""
        questao.mencionar_na_minuta = valor
    
    def _construir_aba_avisos(self):
        """Constrói aba de avisos."""
        avisos = self.cartao_atual.avisos
        
        if not avisos:
            self.abas.tabs[2].content = ft.Container(
                content=ft.Text("✅ Nenhum aviso (extração completa)", size=16, color=ft.colors.GREEN),
                padding=20
            )
            return
        
        itens_avisos = []
        
        for aviso in avisos:
            cor_icone = {
                "falta_impugnacao_especifica": ft.colors.ORANGE,
                "possivel_irrelevancia": ft.colors.YELLOW_700,
                "falta_id_pje": ft.colors.BLUE,
                "falta_folhas": ft.colors.BLUE,
                "dado_ausente": ft.colors.RED,
                "outro": ft.colors.GREY
            }.get(aviso.tipo, ft.colors.GREY)
            
            itens_avisos.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING, color=cor_icone, size=24),
                        ft.Column([
                            ft.Text(aviso.tipo.replace("_", " ").title(), weight=ft.FontWeight.BOLD),
                            ft.Text(aviso.descricao, size=12),
                        ], spacing=2)
                    ]),
                    padding=10,
                    border=ft.border.all(1, cor_icone),
                    border_radius=5,
                    bgcolor=ft.colors.with_opacity(0.1, cor_icone)
                )
            )
        
        self.abas.tabs[2].content = ft.Container(
            content=ft.Column([
                ft.Text(f"Total de avisos: {len(avisos)}", size=16, weight=ft.FontWeight.BOLD),
                ft.Column(itens_avisos, spacing=10, scroll=ft.ScrollMode.AUTO)
            ]),
            padding=10
        )
    
    def _construir_aba_json(self):
        """Constrói aba com JSON do cartão."""
        import json
        
        json_str = json.dumps(
            self.cartao_atual.model_dump(mode='json'),
            ensure_ascii=False,
            indent=2
        )
        
        self.abas.tabs[3].content = ft.Container(
            content=ft.Column([
                ft.Text("JSON do Cartão", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(
                        json_str,
                        selectable=True,
                        size=11,
                        font_family="Courier"
                    ),
                    bgcolor=ft.colors.GREY_900,
                    padding=10,
                    border_radius=5
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=10
        )
    
    def _confirmar_cartao(self, e):
        """Confirma e salva o cartão."""
        if not self.cartao_atual:
            return
        
        try:
            caminho_salvo = self.persistencia.salvar_cartao(
                self.cartao_atual,
                self.caminho_arquivo,
                confirmado=True
            )
            
            self._mostrar_dialogo(
                "✅ Cartão Confirmado",
                f"Cartão salvo com sucesso!\n\nLocalização:\n{caminho_salvo}\n\nO arquivo MD de auditoria também foi copiado.",
                sucesso=True
            )
            
            estatisticas = self.persistencia.obter_estatisticas()
            print(f"Estatísticas: {estatisticas}")
            
        except Exception as ex:
            self._mostrar_erro(f"Erro ao salvar cartão: {ex}")
    
    def _voltar_extrair(self, e):
        """Volta para tela de extração."""
        self.abas.visible = False
        self.painel_acoes_container.visible = False
        self.cartao_atual = None
        self.page.update()
    
    def _exportar_json(self, e):
        """Exporta JSON para local escolhido pelo usuário."""
        def resultado_exportar(result: ft.FilePickerResultEvent):
            if result.path:
                try:
                    caminho_destino = Path(result.path)
                    if not caminho_destino.suffix:
                        caminho_destino = caminho_destino.with_suffix(".json")
                    
                    self.persistencia.exportar_cartao(self.cartao_atual, caminho_destino)
                    self._mostrar_sucesso(f"JSON exportado para: {caminho_destino}")
                except Exception as ex:
                    self._mostrar_erro(f"Erro ao exportar: {ex}")
        
        picker = ft.FilePicker(on_result=resultado_exportar)
        self.page.overlay.append(picker)
        self.page.update()
        
        picker.save_file(
            dialog_title="Exportar JSON do Cartão",
            file_name=f"cartao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            allowed_extensions=["json"]
        )
    
    def _mostrar_erro(self, mensagem: str):
        """Mostra snackbar de erro."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(mensagem, color=ft.colors.WHITE),
            bgcolor=ft.colors.RED_700
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _mostrar_sucesso(self, mensagem: str):
        """Mostra snackbar de sucesso."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(mensagem, color=ft.colors.WHITE),
            bgcolor=ft.colors.GREEN_700
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _mostrar_dialogo(self, titulo: str, mensagem: str, sucesso: bool = False):
        """Mostra diálogo modal."""
        cor = ft.colors.GREEN if sucesso else ft.colors.BLUE
        
        dlg = ft.AlertDialog(
            title=ft.Text(titulo, color=cor, weight=ft.FontWeight.BOLD),
            content=ft.Text(mensagem),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self._fechar_dialogo(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    def _fechar_dialogo(self, dialogo):
        """Fecha diálogo."""
        dialogo.open = False
        self.page.update()


def main(page: ft.Page):
    """Função principal da aplicação."""
    app = CartaoDoCasoApp(page)


if __name__ == "__main__":
    ft.app(target=main)
