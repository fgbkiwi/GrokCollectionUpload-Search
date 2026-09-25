"""
Aba de Configurações.
"""

import flet as ft
from minuta import KernelSarah, KernelPafuncio, BibliotecaModelos, ModeloTematico
from xai_models import DEFAULT_MODEL, FALLBACK_MODELS, listar_modelos_para_ui, rotulo_modelo
from xai_reasoning import (
    LABELS_REASONING,
    DEFAULT_REASONING_EFFORT,
    modelo_suporta_reasoning,
    niveis_reasoning_para_modelo,
    normalizar_reasoning_effort,
)


class AbaConfiguracoes:
    """Aba de configurações do sistema."""
    
    def __init__(self, app):
        self.app = app
        self.kernel = KernelSarah()
        self.kernel_pafuncio = KernelPafuncio()
        self.biblioteca = BibliotecaModelos()
    
    def construir(self) -> ft.Container:
        """Constrói a interface da aba."""
        self.campo_api_key = ft.TextField(
            label="API Key xAI",
            password=True,
            can_reveal_password=True,
            width=500,
            value=self.app.api_key or "",
            on_change=self._atualizar_api_key,
            on_blur=self._ao_sair_api_key,
        )
        
        self.campo_management_key = ft.TextField(
            label="Management Key xAI",
            password=True,
            can_reveal_password=True,
            width=500,
            value=self.app.management_key or "",
            on_change=self._atualizar_management_key
        )

        modelo_atual = getattr(self.app, "modelo_grok", None) or DEFAULT_MODEL
        self.dropdown_modelo = ft.Dropdown(
            label="Modelo padrão (global)",
            width=500,
            value=modelo_atual,
            options=[
                ft.dropdown.Option(m, rotulo_modelo(m)) for m in FALLBACK_MODELS
            ],
            on_change=self._atualizar_modelo
        )
        self.btn_atualizar_modelos = ft.OutlinedButton(
            "Atualizar lista",
            icon=ft.Icons.REFRESH,
            on_click=self._atualizar_lista_modelos_click,
        )
        self.texto_modelos = ft.Text(size=12, color=ft.Colors.GREY_700)

        self.dropdown_reasoning = ft.Dropdown(
            label="Reasoning padrão (global)",
            width=500,
            on_change=self._atualizar_reasoning,
        )
        self.texto_reasoning = ft.Text(size=12, color=ft.Colors.GREY_700)
        self.btn_aplicar_fases = ft.OutlinedButton(
            "Aplicar às três fases",
            icon=ft.Icons.CONTENT_COPY,
            on_click=self._aplicar_as_tres_fases,
        )
        self.texto_aplicar = ft.Text(
            "Copia o modelo e o reasoning padrão para Cartão, Dossiê e Minuta. "
            "Cada aba também permite ajuste independente.",
            size=12,
            color=ft.Colors.GREY_700,
        )
        self._sincronizar_dropdown_modelos()
        self._sincronizar_dropdown_reasoning()

        self.campo_prompt = ft.TextField(
            label="Instruções da Sarah (conhecimento)",
            multiline=True,
            min_lines=10,
            max_lines=20,
            expand=True,
            value=self.kernel.obter_prompt()
        )
        self.aviso_kernel_sarah = ft.Text(size=12, color=ft.Colors.ORANGE_800)
        self._atualizar_aviso_kernel_sarah()
        
        self.btn_salvar_prompt = ft.ElevatedButton(
            "Salvar Prompt",
            icon=ft.Icons.SAVE,
            on_click=self._salvar_prompt
        )
        
        self.btn_restaurar_prompt = ft.ElevatedButton(
            "Restaurar Padrão",
            icon=ft.Icons.RESTORE,
            on_click=self._restaurar_prompt
        )

        self.campo_prompt_pafuncio = ft.TextField(
            label="Instruções do Pafúncio (liquidação)",
            multiline=True,
            min_lines=10,
            max_lines=20,
            expand=True,
            value=self.kernel_pafuncio.obter_prompt()
        )
        self.btn_salvar_pafuncio = ft.ElevatedButton(
            "Salvar Prompt",
            icon=ft.Icons.SAVE,
            on_click=self._salvar_prompt_pafuncio
        )
        self.btn_restaurar_pafuncio = ft.ElevatedButton(
            "Restaurar Padrão",
            icon=ft.Icons.RESTORE,
            on_click=self._restaurar_prompt_pafuncio
        )
        
        self.lista_modelos = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.btn_novo_modelo = ft.ElevatedButton(
            "Novo Modelo Temático",
            icon=ft.Icons.ADD,
            on_click=self._novo_modelo
        )
        
        self._carregar_modelos()
        
        tabs_config = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    text="API Keys",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Configure suas chaves de API xAI",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Divider(),
                            self.campo_api_key,
                            self.campo_management_key,
                            ft.Row(
                                [
                                    self.dropdown_modelo,
                                    self.btn_atualizar_modelos,
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.END,
                            ),
                            self.texto_modelos,
                            self.dropdown_reasoning,
                            self.texto_reasoning,
                            ft.Row(
                                [self.btn_aplicar_fases],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            self.texto_aplicar,
                            ft.Text(
                                "As chaves são carregadas de app_config.json quando disponível",
                                size=12,
                                color=ft.Colors.GREY_700
                            ),
                        ]),
                        padding=20,
                    )
                ),
                ft.Tab(
                    text="Instruções Sarah",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Instruções da Sarah (sentença de conhecimento)",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                "Usadas pela orquestração de minuta (cartão → dossiê → estrutura → tópicos).",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Divider(),
                            self.aviso_kernel_sarah,
                            self.campo_prompt,
                            ft.Row([
                                self.btn_salvar_prompt,
                                self.btn_restaurar_prompt,
                            ]),
                        ]),
                        padding=20,
                        expand=True,
                    )
                ),
                ft.Tab(
                    text="Instruções Pafúncio",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Instruções do Pafúncio (liquidação/execução)",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                "Slot separado. Não substitui a Sarah na geração de minuta de conhecimento.",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Divider(),
                            self.campo_prompt_pafuncio,
                            ft.Row([
                                self.btn_salvar_pafuncio,
                                self.btn_restaurar_pafuncio,
                            ]),
                        ]),
                        padding=20,
                        expand=True,
                    )
                ),
                ft.Tab(
                    text="Modelos Temáticos",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(
                                "Biblioteca de Modelos Temáticos",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Divider(),
                            self.btn_novo_modelo,
                            self.lista_modelos,
                        ]),
                        padding=20,
                        expand=True,
                    )
                ),
            ],
            expand=True,
        )
        
        return ft.Container(
            content=tabs_config,
            expand=True,
        )
    
    def _persistir_config(self):
        """Persiste chaves/modelo/reasoning quando o app permitir."""
        salvar = getattr(self.app, "salvar_config_persistida", None)
        if callable(salvar):
            try:
                salvar()
            except Exception:
                pass

    def _sincronizar_dropdown_modelos(self) -> None:
        """Popula o dropdown só com modelos com reasoning (API ou fallback)."""
        api_key = getattr(self.app, "api_key", None) or ""
        modelos, msg = listar_modelos_para_ui(api_key)
        atual = getattr(self.app, "modelo_grok", None) or DEFAULT_MODEL

        self.dropdown_modelo.options = [
            ft.dropdown.Option(m, rotulo_modelo(m)) for m in modelos
        ]
        if atual in modelos:
            self.dropdown_modelo.value = atual
        else:
            self.dropdown_modelo.value = modelos[0] if modelos else DEFAULT_MODEL
        self.app.modelo_grok = self.dropdown_modelo.value

        if hasattr(self, "texto_modelos"):
            self.texto_modelos.value = msg

    def _atualizar_lista_modelos_click(self, e):
        """Recarrega a lista de modelos sob demanda."""
        self._sincronizar_dropdown_modelos()
        self._sincronizar_dropdown_reasoning()
        self._sincronizar_seletores_fases()
        self._persistir_config()
        self.app.page.update()

    def _sincronizar_dropdown_reasoning(self):
        """Atualiza opções/estado do dropdown conforme o modelo atual."""
        modelo = self.dropdown_modelo.value or getattr(self.app, "modelo_grok", None) or DEFAULT_MODEL
        niveis = niveis_reasoning_para_modelo(modelo)
        if not niveis:
            self.dropdown_reasoning.options = [
                ft.dropdown.Option("", "Não disponível para este modelo")
            ]
            self.dropdown_reasoning.value = ""
            self.dropdown_reasoning.disabled = True
            self.texto_reasoning.value = (
                "Este modelo não aceita o parâmetro reasoning_effort."
            )
            return

        self.dropdown_reasoning.disabled = False
        self.dropdown_reasoning.options = [
            ft.dropdown.Option(nivel, LABELS_REASONING.get(nivel, nivel))
            for nivel in niveis
        ]
        atual = normalizar_reasoning_effort(
            modelo,
            getattr(self.app, "reasoning_effort", None) or DEFAULT_REASONING_EFFORT,
        )
        self.dropdown_reasoning.value = atual
        self.app.reasoning_effort = atual
        self.texto_reasoning.value = (
            "Padrão global: profundidade de raciocínio (latência × qualidade). "
            "Use «Aplicar às três fases» para propagar."
        )

    def _sincronizar_seletores_fases(self) -> None:
        """Atualiza dropdowns de modelo/reasoning nas abas Cartão/Dossiê/Minuta."""
        for aba_nome in ("aba_cartao", "aba_dossie", "aba_minuta"):
            aba = getattr(self.app, aba_nome, None)
            seletor = getattr(aba, "seletor_modelo", None) if aba else None
            if seletor is not None:
                seletor.sincronizar(atualizar_page=False)

    def _aplicar_as_tres_fases(self, e):
        """Copia o padrão global para as três fases."""
        aplicar = getattr(self.app, "aplicar_padrao_global_as_fases", None)
        if callable(aplicar):
            aplicar()
            self.app.mostrar_info(
                "Modelo e reasoning padrão aplicados a Cartão, Dossiê e Minuta."
            )
        else:
            self.app.mostrar_erro("Aplicação não disponível nesta sessão.")

    def _atualizar_api_key(self, e):
        """Atualiza API Key (persistência; lista de modelos no blur/botão)."""
        self.app.api_key = self.campo_api_key.value
        self._persistir_config()

    def _ao_sair_api_key(self, e):
        """Recarrega modelos ao sair do campo da API Key."""
        self.app.api_key = self.campo_api_key.value
        self._sincronizar_dropdown_modelos()
        self._sincronizar_dropdown_reasoning()
        self._sincronizar_seletores_fases()
        self._persistir_config()
        self.app.page.update()

    def _atualizar_management_key(self, e):
        """Atualiza Management Key."""
        self.app.management_key = self.campo_management_key.value
        self._persistir_config()

    def _atualizar_modelo(self, e):
        """Atualiza modelo Grok padrão global."""
        self.app.modelo_grok = self.dropdown_modelo.value or DEFAULT_MODEL
        self._sincronizar_dropdown_reasoning()
        self._persistir_config()
        self.app.page.update()

    def _atualizar_reasoning(self, e):
        """Atualiza nível de reasoning padrão quando o modelo permitir."""
        modelo = self.app.modelo_grok or DEFAULT_MODEL
        if not modelo_suporta_reasoning(modelo):
            return
        self.app.reasoning_effort = normalizar_reasoning_effort(
            modelo,
            self.dropdown_reasoning.value,
        ) or DEFAULT_REASONING_EFFORT
        self._persistir_config()
    
    def _atualizar_aviso_kernel_sarah(self):
        """Alerta se o prompt da Sarah parecer o Pafúncio."""
        prompt = self.campo_prompt.value or self.kernel.obter_prompt()
        if KernelSarah.parece_pafuncio(prompt):
            self.aviso_kernel_sarah.value = (
                "Atenção: este texto parece as instruções do Pafúncio (liquidação). "
                "Use a aba Instruções Pafúncio e restaure o padrão da Sarah — "
                "caso contrário a minuta de conhecimento degrada."
            )
            self.aviso_kernel_sarah.visible = True
        else:
            self.aviso_kernel_sarah.value = ""
            self.aviso_kernel_sarah.visible = False

    def _salvar_prompt(self, e):
        """Salva prompt personalizado da Sarah."""
        try:
            prompt = self.campo_prompt.value or ""
            if KernelSarah.parece_pafuncio(prompt):
                self.app.mostrar_erro(
                    "Este texto parece as instruções do Pafúncio. Salve-o na aba "
                    "Instruções Pafúncio e restaure o padrão da Sarah."
                )
                self._atualizar_aviso_kernel_sarah()
                self.app.page.update()
                return
            self.kernel.salvar_prompt(prompt)
            self._atualizar_aviso_kernel_sarah()
            self.app.mostrar_info("Prompt da Sarah salvo com sucesso!")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar prompt: {str(ex)}")
    
    def _restaurar_prompt(self, e):
        """Restaura prompt padrão da Sarah."""
        try:
            self.kernel.restaurar_default()
            self.campo_prompt.value = self.kernel.obter_prompt()
            self._atualizar_aviso_kernel_sarah()
            self.app.page.update()
            self.app.mostrar_info("Prompt da Sarah restaurado para o padrão")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao restaurar prompt: {str(ex)}")

    def _salvar_prompt_pafuncio(self, e):
        """Salva prompt do Pafúncio."""
        try:
            self.kernel_pafuncio.salvar_prompt(self.campo_prompt_pafuncio.value or "")
            self.app.mostrar_info("Prompt do Pafúncio salvo com sucesso!")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao salvar prompt do Pafúncio: {str(ex)}")

    def _restaurar_prompt_pafuncio(self, e):
        """Restaura prompt padrão do Pafúncio."""
        try:
            self.kernel_pafuncio.restaurar_default()
            self.campo_prompt_pafuncio.value = self.kernel_pafuncio.obter_prompt()
            self.app.page.update()
            self.app.mostrar_info("Prompt do Pafúncio restaurado para o padrão")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao restaurar prompt do Pafúncio: {str(ex)}")
    
    def _carregar_modelos(self):
        """Carrega lista de modelos temáticos."""
        self.lista_modelos.controls.clear()
        
        modelos = self.biblioteca.listar()
        
        for modelo in modelos:
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(modelo.nome, size=14, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                on_click=lambda e, m=modelo: self._editar_modelo(m)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                on_click=lambda e, m=modelo: self._excluir_modelo(m)
                            ),
                        ]),
                        ft.Text(f"Tema: {modelo.tema}", size=12),
                        ft.Text(
                            modelo.texto[:100] + "...",
                            size=11,
                            color=ft.Colors.GREY_700
                        ),
                    ]),
                    padding=15,
                )
            )
            self.lista_modelos.controls.append(card)
    
    def _novo_modelo(self, e):
        """Cria novo modelo temático."""
        self.app.mostrar_info("Funcionalidade de criação de modelo em desenvolvimento")
    
    def _editar_modelo(self, modelo: ModeloTematico):
        """Edita modelo temático."""
        self.app.mostrar_info(f"Editar modelo: {modelo.nome}")
    
    def _excluir_modelo(self, modelo: ModeloTematico):
        """Exclui modelo temático."""
        try:
            self.biblioteca.excluir(modelo.id)
            self._carregar_modelos()
            self.app.page.update()
            self.app.mostrar_info(f"Modelo '{modelo.nome}' excluído")
        except Exception as ex:
            self.app.mostrar_erro(f"Erro ao excluir modelo: {str(ex)}")
