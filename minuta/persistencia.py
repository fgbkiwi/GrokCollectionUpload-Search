"""
Persistência da Minuta.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from .schema import MinutaCompleta


class PersistenciaMinuta:
    """Gerencia persistência local de minutas."""
    
    def __init__(self, diretorio_base: Optional[Path] = None):
        if diretorio_base is None:
            diretorio_base = Path.home() / ".indexador_sentencas" / "minutas"
        
        self.diretorio_base = Path(diretorio_base)
        self.diretorio_base.mkdir(parents=True, exist_ok=True)
    
    def salvar(self, minuta: MinutaCompleta, nome_arquivo: Optional[str] = None) -> Path:
        """
        Salva uma minuta no formato JSON.
        
        Args:
            minuta: Minuta a ser salva
            nome_arquivo: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo salvo
        """
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = Path(minuta.cartao_origem).stem
            nome_arquivo = f"minuta_{nome_base}_{timestamp}.json"
        
        caminho = self.diretorio_base / nome_arquivo
        
        dados = minuta.model_dump(mode="json")
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        
        return caminho
    
    def carregar(self, caminho: Path) -> MinutaCompleta:
        """Carrega uma minuta de um arquivo JSON."""
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        return MinutaCompleta(**dados)
    
    def salvar_markdown(self, minuta: MinutaCompleta, nome_arquivo: Optional[str] = None) -> Path:
        """
        Salva a minuta final em formato Markdown.
        
        Args:
            minuta: Minuta completa
            nome_arquivo: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo salvo
        """
        if not minuta.minuta_final_md:
            raise ValueError("Minuta final em Markdown não disponível")
        
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = Path(minuta.cartao_origem).stem
            nome_arquivo = f"minuta_{nome_base}_{timestamp}.md"
        
        caminho = self.diretorio_base / nome_arquivo
        
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(minuta.minuta_final_md)
        
        return caminho
    
    def listar(self) -> List[tuple[Path, datetime]]:
        """
        Lista todas as minutas salvas.
        
        Returns:
            Lista de tuplas (caminho, data_modificacao)
        """
        arquivos = []
        
        for arquivo in self.diretorio_base.glob("minuta_*.json"):
            data_mod = datetime.fromtimestamp(arquivo.stat().st_mtime)
            arquivos.append((arquivo, data_mod))
        
        arquivos.sort(key=lambda x: x[1], reverse=True)
        
        return arquivos
    
    def excluir(self, caminho: Path) -> bool:
        """Exclui uma minuta."""
        try:
            caminho.unlink()
            caminho_md = caminho.with_suffix(".md")
            if caminho_md.exists():
                caminho_md.unlink()
            return True
        except Exception:
            return False
