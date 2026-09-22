"""
Kernel Pafúncio - Prompt de sistema para sentença de liquidação/execução.

Slot separado da Sarah (conhecimento). Não deve ser usado como system prompt
da orquestração de minuta de conhecimento.
"""

import json
from pathlib import Path
from typing import Optional


def _carregar_default_empacotado() -> str:
    """Carrega o default de minuta/prompts/pafuncio_default.txt, se existir."""
    caminho = Path(__file__).resolve().parent / "prompts" / "pafuncio_default.txt"
    if caminho.exists():
        return caminho.read_text(encoding="utf-8")
    return (
        "# Pafúncio — Assistente Jurídico para Sentença de Liquidação\n\n"
        "Você é Pafúncio, assistente de liquidação/execução trabalhista. "
        "Este é um placeholder: salve o prompt completo na aba Instruções Pafúncio "
        "ou restaure a partir do arquivo empacotado."
    )


class KernelPafuncio:
    """Gerencia o prompt de sistema do Pafúncio (liquidação)."""

    PROMPT_DEFAULT = _carregar_default_empacotado()

    def __init__(self, diretorio_config: Optional[Path] = None):
        if diretorio_config is None:
            diretorio_config = Path.home() / ".indexador_sentencas" / "config"

        self.diretorio_config = Path(diretorio_config)
        self.diretorio_config.mkdir(parents=True, exist_ok=True)
        self.arquivo_config = self.diretorio_config / "kernel_pafuncio.json"

        if not self.arquivo_config.exists():
            self.salvar_prompt(self.PROMPT_DEFAULT)

    def obter_prompt(self) -> str:
        """Obtém o prompt de sistema atual do Pafúncio."""
        if not self.arquivo_config.exists():
            return self.PROMPT_DEFAULT

        with open(self.arquivo_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        return config.get("prompt_sistema", self.PROMPT_DEFAULT)

    def salvar_prompt(self, prompt: str):
        """Salva o prompt de sistema do Pafúncio."""
        config = {
            "prompt_sistema": prompt,
            "versao": "1.0",
            "assistente": "pafuncio",
        }
        with open(self.arquivo_config, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def restaurar_default(self):
        """Restaura o prompt padrão empacotado do Pafúncio."""
        # Recarrega do arquivo empacotado (pode ter sido atualizado).
        self.PROMPT_DEFAULT = _carregar_default_empacotado()
        self.salvar_prompt(self.PROMPT_DEFAULT)
