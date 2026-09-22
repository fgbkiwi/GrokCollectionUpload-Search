"""
Aba do Cartão do Caso.
"""

import json
from pathlib import Path
from typing import Optional, List, Any

import flet as ft

from cartao_caso import (
    ExtratorCartao,
    PersistenciaCartao,
    CartaoDoCaso,
    Pedido,
    Questao,
)


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
        self.campo_arquivo = ft.Text("Nenhum arquivo selecionado", size=14)

        self.btn_selecionar = ft.ElevatedButton(
            "Escolher Arquivo MD",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._selecionar_arquivo,
        )

        self.btn_extrair = ft.ElevatedButton(
            "Extrair Cartão",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._extrair_cartao,
            disabled=True,
        )

        self.btn_confirmar = ft.ElevatedButton(
            "Confirmar e Salvar",
            icon=ft.Icons.CHECK,
            on_click=self._confirmar_cartao,
            disabled=True,
        )

        self.progresso = ft.ProgressBar(visible=False, width=600)
        self.texto_status = ft.Text("", size=12)

        self.texto_resumo = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        self.texto_partes = ft.Text("", size=12, color=ft.Colors.GREY_700)

        self.abas_resultado = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            expand=True,
            visible=False,
            tabs=[
                ft.Tab(text="Pedidos", icon=ft.Icons.LIST_ALT, content=ft.Container(padding=10)),
                ft.Tab(text="Questões", icon=ft.Icons.QUESTION_ANSWER, content=ft.Container(padding=10)),
                ft.Tab(text="Avisos", icon=ft.Icons.WARNING, content=ft.Container(padding=10)),
                ft.Tab(text="JSON", icon=ft.Icons.CODE, content=ft.Container(padding=10)),
            ],
        )

        self.file_picker = ft.FilePicker(on_result=self._on_arquivo_selecionado)
        self.app.page.overlay.append(self.file_picker)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Extração do Cartão do Caso",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Divider(),
                                ft.Row([self.btn_selecionar, self.campo_arquivo]),
                                ft.Row([self.btn_extrair, self.btn_confirmar]),
                                self.progresso,
                                self.texto_status,
                                self.texto_resumo,
                                self.texto_partes,
                            ]
                        ),
                        padding=20,
                    ),
                    ft.Divider(),
                    ft.Container(
                        content=self.abas_resultado,
                        padding=10,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            expand=True,
        )

    def _selecionar_arquivo(self, e):
        """Abre diálogo de seleção de arquivo."""
        self.file_picker.pick_files(
            allowed_extensions=["md"],
            dialog_title="Selecione o arquivo MD dos autos",
            allow_multiple=False,
        )

    def _on_arquivo_selecionado(self, e: ft.FilePickerResultEvent):
        """Callback do FilePicker."""
        if e.files:
            self.caminho_arquivo = Path(e.files[0].path)
            self.campo_arquivo.value = self.caminho_arquivo.name
            self.btn_extrair.disabled = False
            self.app.page.update()

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
        self.btn_confirmar.disabled = True
        self.abas_resultado.visible = False
        self.app.page.update()

        try:
            self.extrator = ExtratorCartao(
                api_key=self.app.api_key,
                model=getattr(self.app, "modelo_grok", None) or "grok-4.6",
                reasoning_effort=getattr(self.app, "reasoning_effort", None),
            )

            self.cartao_atual = self.extrator.extrair_de_arquivo(
                self.caminho_arquivo,
                progresso_callback=lambda msg: self._atualizar_progresso(msg, None),
            )

            self._exibir_cartao()
            self.btn_confirmar.disabled = False
            self.texto_status.value = "Extração concluída! Revise as abas e confirme."

        except Exception as ex:
            self.app.mostrar_erro(f"Erro na extração: {str(ex)}")
            self.texto_status.value = f"Erro: {str(ex)}"
        finally:
            self.progresso.visible = False
            self.btn_extrair.disabled = False
            self.app.page.update()

    def _atualizar_progresso(self, mensagem: str, progresso: float | None = None):
        """Atualiza barra de progresso."""
        self.texto_status.value = mensagem
        if progresso is not None:
            self.progresso.value = progresso
        self.app.page.update()

    def _obter_pedidos(self) -> List[Any]:
        """Normaliza pedidos da petição inicial."""
        if not self.cartao_atual:
            return []
        peticao = self.cartao_atual.peticao_inicial or {}
        if isinstance(peticao, dict):
            return peticao.get("pedidos", []) or []
        return getattr(peticao, "pedidos", []) or []

    def _exibir_cartao(self):
        """Exibe o cartão extraído com abas de revisão."""
        if not self.cartao_atual:
            return

        pedidos = self._obter_pedidos()
        partes = ", ".join(
            f"{p.tipo}: {p.nome}" for p in (self.cartao_atual.partes or [])
        ) or "Partes não identificadas"

        causa = None
        if isinstance(self.cartao_atual.peticao_inicial, dict):
            causa = self.cartao_atual.peticao_inicial.get("causa_pedir")

        self.texto_resumo.value = (
            f"Processo: {self.cartao_atual.numero_processo or 'N/A'}  |  "
            f"Pedidos: {len(pedidos)}  |  "
            f"Questões: {len(self.cartao_atual.questoes)}  |  "
            f"Avisos: {len(self.cartao_atual.avisos)}"
        )
        self.texto_partes.value = partes
        if causa:
            self.texto_partes.value += f"\nCausa de pedir: {str(causa)[:240]}"

        self._construir_aba_pedidos()
        self._construir_aba_questoes()
        self._construir_aba_avisos()
        self._construir_aba_json()

        self.abas_resultado.visible = True
        self.abas_resultado.selected_index = 0
        self.app.page.update()

    def _construir_aba_pedidos(self):
        """Constrói aba de pedidos."""
        pedidos = self._obter_pedidos()

        if not pedidos:
            self.abas_resultado.tabs[0].content = ft.Container(
                content=ft.Text("Nenhum pedido encontrado", size=16),
                padding=20,
            )
            return

        linhas = []
        for pedido_dict in pedidos:
            pedido = Pedido(**pedido_dict) if isinstance(pedido_dict, dict) else pedido_dict
            contestacao = next(
                (c for c in self.cartao_atual.contestacoes if c.pedido_id == pedido.id),
                None,
            )
            descricao = pedido.descricao or "-"
            if len(descricao) > 100:
                descricao = descricao[:100] + "..."

            teses = ""
            if contestacao and contestacao.teses:
                teses = "; ".join(contestacao.teses[:2])
                if len(teses) > 80:
                    teses = teses[:80] + "..."

            linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(pedido.id)),
                        ft.DataCell(ft.Text(descricao, size=12)),
                        ft.DataCell(ft.Text(pedido.periodo or "-")),
                        ft.DataCell(ft.Text(pedido.valor or "-")),
                        ft.DataCell(ft.Text("Sim" if pedido.reflexos else "Não")),
                        ft.DataCell(
                            ft.Text(
                                "Sim" if contestacao and contestacao.impugnacao_especifica else "Não",
                                color=(
                                    ft.Colors.GREEN
                                    if contestacao and contestacao.impugnacao_especifica
                                    else ft.Colors.RED
                                ),
                            )
                        ),
                        ft.DataCell(ft.Text(teses or "-", size=11)),
                    ]
                )
            )

        self.abas_resultado.tabs[0].content = ft.Container(
            content=ft.Column(
                [
                    ft.Text(f"Total de pedidos: {len(pedidos)}", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.DataTable(
                                    columns=[
                                        ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Descrição", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Período", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Valor", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Reflexos", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Impugnação", weight=ft.FontWeight.BOLD)),
                                        ft.DataColumn(ft.Text("Teses", weight=ft.FontWeight.BOLD)),
                                    ],
                                    rows=linhas,
                                )
                            ],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        padding=10,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=10,
            expand=True,
        )

    def _construir_aba_questoes(self):
        """Constrói aba de questões."""
        questoes = self.cartao_atual.questoes if self.cartao_atual else []

        if not questoes:
            self.abas_resultado.tabs[1].content = ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Nenhuma questão encontrada", size=16),
                        ft.Text(
                            "A extração não identificou questões a decidir. "
                            "Revise o JSON ou reextrair com outro modelo.",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                    ]
                ),
                padding=20,
            )
            return

        linhas = []
        for questao in questoes:
            titulo = questao.titulo or "-"
            if len(titulo) > 70:
                titulo = titulo[:70] + "..."
            linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(questao.id)),
                        ft.DataCell(ft.Text(titulo, size=12)),
                        ft.DataCell(ft.Text(questao.tipo)),
                        ft.DataCell(ft.Text(questao.momento)),
                        ft.DataCell(ft.Checkbox(value=questao.de_oficio, disabled=True)),
                        ft.DataCell(
                            ft.Checkbox(
                                value=questao.mencionar_na_minuta,
                                on_change=lambda e, q=questao: self._toggle_mencionar(
                                    q, e.control.value
                                ),
                            )
                        ),
                    ]
                )
            )

        self.abas_resultado.tabs[1].content = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"Total de questões: {len(questoes)}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Você pode desmarcar questões que não devem constar na minuta",
                        size=12,
                        color=ft.Colors.BLUE_700,
                    ),
                    ft.Container(
                        content=ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Título", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Tipo", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Momento", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("De Ofício", weight=ft.FontWeight.BOLD)),
                                ft.DataColumn(ft.Text("Mencionar", weight=ft.FontWeight.BOLD)),
                            ],
                            rows=linhas,
                        ),
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        padding=10,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=10,
            expand=True,
        )

    def _toggle_mencionar(self, questao: Questao, valor: bool):
        """Toggle para mencionar questão na minuta."""
        questao.mencionar_na_minuta = bool(valor)

    def _construir_aba_avisos(self):
        """Constrói aba de avisos."""
        avisos = self.cartao_atual.avisos if self.cartao_atual else []

        if not avisos:
            self.abas_resultado.tabs[2].content = ft.Container(
                content=ft.Text(
                    "Nenhum aviso (extração completa)",
                    size=16,
                    color=ft.Colors.GREEN,
                ),
                padding=20,
            )
            return

        itens = []
        for aviso in avisos:
            cor = {
                "falta_impugnacao_especifica": ft.Colors.ORANGE,
                "possivel_irrelevancia": ft.Colors.YELLOW_700,
                "falta_id_pje": ft.Colors.BLUE,
                "falta_folhas": ft.Colors.BLUE,
                "dado_ausente": ft.Colors.RED,
                "outro": ft.Colors.GREY,
            }.get(aviso.tipo, ft.Colors.GREY)

            itens.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.WARNING, color=cor, size=24),
                            ft.Column(
                                [
                                    ft.Text(
                                        aviso.tipo.replace("_", " ").title(),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(aviso.descricao, size=12),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=10,
                    border=ft.border.all(1, cor),
                    border_radius=5,
                    bgcolor=ft.Colors.with_opacity(0.1, cor),
                )
            )

        self.abas_resultado.tabs[2].content = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"Total de avisos: {len(avisos)}",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Column(itens, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
                ],
                expand=True,
            ),
            padding=10,
            expand=True,
        )

    def _construir_aba_json(self):
        """Constrói aba com JSON do cartão."""
        json_str = json.dumps(
            self.cartao_atual.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )

        self.abas_resultado.tabs[3].content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("JSON do Cartão", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(
                            json_str,
                            selectable=True,
                            size=11,
                            font_family="Consolas",
                            color=ft.Colors.GREEN_ACCENT_100,
                        ),
                        bgcolor=ft.Colors.GREY_900,
                        padding=10,
                        border_radius=5,
                        expand=True,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=10,
            expand=True,
        )

    def _confirmar_cartao(self, e):
        """Confirma e salva o cartão."""
        if not self.cartao_atual:
            return

        try:
            caminho_salvo = self.persistencia.salvar_cartao(
                self.cartao_atual,
                md_origem=self.caminho_arquivo,
                confirmado=True,
            )
            self.app.mostrar_info(f"Cartão salvo em:\n{caminho_salvo}")

            self.app.aba_dossie.cartao_confirmado = self.cartao_atual
            self.app.aba_dossie.habilitar_montagem()

        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar: {str(ex)}")
