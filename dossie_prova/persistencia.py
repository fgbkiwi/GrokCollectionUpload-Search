"""
Persistência do Dossiê de Prova.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from .schema import DossieProva


class PersistenciaDossie:
    """Gerencia persistência local de dossiês."""
    
    def __init__(self, diretorio_base: Optional[Path] = None):
        if diretorio_base is None:
            diretorio_base = Path.home() / ".indexador_sentencas" / "dossies"
        
        self.diretorio_base = Path(diretorio_base)
        self.diretorio_base.mkdir(parents=True, exist_ok=True)
    
    def salvar(self, dossie: DossieProva, nome_arquivo: Optional[str] = None) -> Path:
        """
        Salva um dossiê no formato JSON.
        
        Args:
            dossie: Dossiê a ser salvo
            nome_arquivo: Nome do arquivo (opcional, usa timestamp se não fornecido)
            
        Returns:
            Caminho do arquivo salvo
        """
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = Path(dossie.cartao_origem).stem
            nome_arquivo = f"dossie_{nome_base}_{timestamp}.json"
        
        caminho = self.diretorio_base / nome_arquivo
        
        dados = dossie.model_dump(mode="json")
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        
        return caminho
    
    def carregar(self, caminho: Path) -> DossieProva:
        """
        Carrega um dossiê de um arquivo JSON.
        
        Args:
            caminho: Caminho do arquivo
            
        Returns:
            Dossiê carregado
        """
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        return DossieProva(**dados)
    
    def listar(self) -> List[tuple[Path, datetime]]:
        """
        Lista todos os dossiês salvos.
        
        Returns:
            Lista de tuplas (caminho, data_modificacao)
        """
        arquivos = []
        
        for arquivo in self.diretorio_base.glob("dossie_*.json"):
            data_mod = datetime.fromtimestamp(arquivo.stat().st_mtime)
            arquivos.append((arquivo, data_mod))
        
        arquivos.sort(key=lambda x: x[1], reverse=True)
        
        return arquivos
    
    def excluir(self, caminho: Path) -> bool:
        """
        Exclui um dossiê.
        
        Args:
            caminho: Caminho do arquivo
            
        Returns:
            True se excluído com sucesso
        """
        try:
            caminho.unlink()
            return True
        except Exception:
            return False
