"""
Persistência local de cartões do caso.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from .schema import CartaoDoCaso


class PersistenciaCartao:
    """Gerencia persistência local de cartões."""
    
    def __init__(self, diretorio_base: Optional[Path] = None):
        """
        Inicializa o gerenciador de persistência.
        
        Args:
            diretorio_base: Diretório base para salvar cartões.
                          Padrão: ~/.indexador_sentencas/cartoes/
        """
        if diretorio_base is None:
            diretorio_base = Path.home() / ".indexador_sentencas" / "cartoes"
        
        self.diretorio_base = Path(diretorio_base)
        self.diretorio_base.mkdir(parents=True, exist_ok=True)
    
    def salvar_cartao(
        self,
        cartao: CartaoDoCaso,
        md_origem: Optional[Path] = None,
        confirmado: bool = False
    ) -> Path:
        """
        Salva cartão localmente.
        
        Args:
            cartao: Cartão do caso a salvar
            md_origem: Arquivo MD de origem (será copiado para auditoria)
            confirmado: Se o cartão foi confirmado pelo juiz
            
        Returns:
            Caminho do arquivo JSON salvo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        numero_processo = cartao.numero_processo or "sem_numero"
        numero_processo_sanitizado = numero_processo.replace("/", "_").replace(".", "_")
        
        sufixo = "_confirmado" if confirmado else "_rascunho"
        nome_arquivo = f"{timestamp}_{numero_processo_sanitizado}{sufixo}.json"
        
        caminho_json = self.diretorio_base / nome_arquivo
        
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(
                cartao.model_dump(mode='json'),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        if md_origem and md_origem.exists():
            pasta_md = self.diretorio_base / "autos_md"
            pasta_md.mkdir(exist_ok=True)
            
            nome_md = f"{timestamp}_{numero_processo_sanitizado}.md"
            caminho_md_copia = pasta_md / nome_md
            shutil.copy2(md_origem, caminho_md_copia)
        
        return caminho_json
    
    def carregar_cartao(self, caminho_json: Path) -> CartaoDoCaso:
        """
        Carrega cartão de arquivo JSON.
        
        Args:
            caminho_json: Caminho do arquivo JSON
            
        Returns:
            CartaoDoCaso carregado
        """
        with open(caminho_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return CartaoDoCaso(**data)
    
    def listar_cartoes(self, apenas_confirmados: bool = False) -> list[Path]:
        """
        Lista cartões salvos.
        
        Args:
            apenas_confirmados: Se True, retorna apenas cartões confirmados
            
        Returns:
            Lista de caminhos de arquivos JSON, ordenados por data (mais recente primeiro)
        """
        if apenas_confirmados:
            pattern = "*_confirmado.json"
        else:
            pattern = "*.json"
        
        cartoes = sorted(
            self.diretorio_base.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        return cartoes
    
    def exportar_cartao(self, cartao: CartaoDoCaso, caminho_destino: Path) -> None:
        """
        Exporta cartão para um local específico.
        
        Args:
            cartao: Cartão a exportar
            caminho_destino: Caminho de destino do arquivo JSON
        """
        caminho_destino.parent.mkdir(parents=True, exist_ok=True)
        
        with open(caminho_destino, 'w', encoding='utf-8') as f:
            json.dump(
                cartao.model_dump(mode='json'),
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def obter_estatisticas(self) -> dict:
        """
        Obtém estatísticas sobre cartões salvos.
        
        Returns:
            Dicionário com estatísticas
        """
        confirmados = len(list(self.diretorio_base.glob("*_confirmado.json")))
        rascunhos = len(list(self.diretorio_base.glob("*_rascunho.json")))
        
        return {
            "total": confirmados + rascunhos,
            "confirmados": confirmados,
            "rascunhos": rascunhos,
            "diretorio": str(self.diretorio_base)
        }
