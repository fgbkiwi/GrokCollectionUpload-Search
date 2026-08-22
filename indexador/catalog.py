#!/usr/bin/env python3
"""
catalog.py
Gerenciador de catálogo SQLite para rastreamento de documentos indexados.

Mantém registro de documentos já enviados para xAI Collections para
garantir idempotência e evitar duplicatas.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime


class CatalogoLocal:
    """Gerenciador de catálogo SQLite de documentos indexados."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa catálogo.
        
        Args:
            db_path: Caminho do banco SQLite. Se None, usa diretório padrão do usuário.
        """
        if db_path is None:
            # Usa diretório padrão do usuário
            home = Path.home()
            data_dir = home / '.indexador_sentencas'
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / 'catalog.db'
        
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        self._criar_tabelas()
    
    def _criar_tabelas(self):
        """Cria tabelas do catálogo se não existirem."""
        cursor = self.conn.cursor()
        
        # Tabela de documentos indexados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                file_id TEXT NOT NULL,
                collection_id TEXT NOT NULL,
                numero_processo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                data_envio TEXT NOT NULL,
                source_path TEXT,
                reclamada TEXT,
                tipo_acao TEXT,
                data_publicacao TEXT,
                UNIQUE(content_hash, numero_processo, categoria)
            )
        """)
        
        # Índices para busca rápida
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash 
            ON documentos(content_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processo_categoria 
            ON documentos(numero_processo, categoria)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_id 
            ON documentos(file_id)
        """)
        
        self.conn.commit()
    
    def documento_existe(
        self, 
        content_hash: str, 
        numero_processo: str, 
        categoria: str
    ) -> Optional[Dict]:
        """
        Verifica se documento já foi indexado.
        
        Returns:
            Dicionário com dados do documento se existe, None caso contrário
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM documentos 
            WHERE content_hash = ? AND numero_processo = ? AND categoria = ?
        """, (content_hash, numero_processo, categoria))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def buscar_por_processo_categoria(
        self, 
        numero_processo: str, 
        categoria: str
    ) -> Optional[Dict]:
        """
        Busca documento por processo e categoria (independente do hash).
        
        Returns:
            Dicionário com dados do documento se existe, None caso contrário
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM documentos 
            WHERE numero_processo = ? AND categoria = ?
        """, (numero_processo, categoria))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def adicionar_documento(
        self,
        content_hash: str,
        file_id: str,
        collection_id: str,
        numero_processo: str,
        categoria: str,
        source_path: Optional[str] = None,
        reclamada: Optional[str] = None,
        tipo_acao: Optional[str] = None,
        data_publicacao: Optional[str] = None
    ) -> int:
        """
        Adiciona documento ao catálogo.
        
        Returns:
            ID do documento inserido
        """
        cursor = self.conn.cursor()
        data_envio = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO documentos (
                content_hash, file_id, collection_id, numero_processo, categoria,
                data_envio, source_path, reclamada, tipo_acao, data_publicacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_hash, file_id, collection_id, numero_processo, categoria,
            data_envio, source_path, reclamada, tipo_acao, data_publicacao
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def atualizar_documento(
        self,
        content_hash: str,
        file_id: str,
        collection_id: str,
        numero_processo: str,
        categoria: str,
        source_path: Optional[str] = None,
        reclamada: Optional[str] = None,
        tipo_acao: Optional[str] = None,
        data_publicacao: Optional[str] = None
    ) -> None:
        """
        Atualiza documento existente (usado quando conteúdo mudou).
        """
        cursor = self.conn.cursor()
        data_envio = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE documentos SET
                content_hash = ?,
                file_id = ?,
                collection_id = ?,
                data_envio = ?,
                source_path = ?,
                reclamada = ?,
                tipo_acao = ?,
                data_publicacao = ?
            WHERE numero_processo = ? AND categoria = ?
        """, (
            content_hash, file_id, collection_id, data_envio,
            source_path, reclamada, tipo_acao, data_publicacao,
            numero_processo, categoria
        ))
        
        self.conn.commit()
    
    def remover_documento(self, file_id: str) -> None:
        """Remove documento do catálogo por file_id."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documentos WHERE file_id = ?", (file_id,))
        self.conn.commit()
    
    def listar_documentos(
        self, 
        collection_id: Optional[str] = None,
        limite: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Lista documentos do catálogo.
        
        Args:
            collection_id: Filtrar por collection (opcional)
            limite: Número máximo de resultados
            offset: Offset para paginação
        
        Returns:
            Lista de dicionários com dados dos documentos
        """
        cursor = self.conn.cursor()
        
        if collection_id:
            cursor.execute("""
                SELECT * FROM documentos 
                WHERE collection_id = ?
                ORDER BY data_envio DESC
                LIMIT ? OFFSET ?
            """, (collection_id, limite, offset))
        else:
            cursor.execute("""
                SELECT * FROM documentos 
                ORDER BY data_envio DESC
                LIMIT ? OFFSET ?
            """, (limite, offset))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def contar_documentos(self, collection_id: Optional[str] = None) -> int:
        """Conta total de documentos no catálogo."""
        cursor = self.conn.cursor()
        
        if collection_id:
            cursor.execute(
                "SELECT COUNT(*) FROM documentos WHERE collection_id = ?",
                (collection_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM documentos")
        
        return cursor.fetchone()[0]
    
    def estatisticas(self, collection_id: Optional[str] = None) -> Dict:
        """
        Retorna estatísticas do catálogo.
        
        Returns:
            Dicionário com estatísticas
        """
        cursor = self.conn.cursor()
        
        where_clause = "WHERE collection_id = ?" if collection_id else ""
        params = (collection_id,) if collection_id else ()
        
        # Total de documentos
        cursor.execute(f"SELECT COUNT(*) FROM documentos {where_clause}", params)
        total = cursor.fetchone()[0]
        
        # Processos únicos
        cursor.execute(
            f"SELECT COUNT(DISTINCT numero_processo) FROM documentos {where_clause}",
            params
        )
        processos_unicos = cursor.fetchone()[0]
        
        # Categorias únicas
        cursor.execute(
            f"SELECT COUNT(DISTINCT categoria) FROM documentos {where_clause}",
            params
        )
        categorias_unicas = cursor.fetchone()[0]
        
        # Top categorias
        cursor.execute(f"""
            SELECT categoria, COUNT(*) as count
            FROM documentos {where_clause}
            GROUP BY categoria
            ORDER BY count DESC
            LIMIT 10
        """, params)
        top_categorias = [
            {'categoria': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Data do primeiro e último envio
        cursor.execute(
            f"SELECT MIN(data_envio), MAX(data_envio) FROM documentos {where_clause}",
            params
        )
        primeira_data, ultima_data = cursor.fetchone()
        
        return {
            'total_documentos': total,
            'processos_unicos': processos_unicos,
            'categorias_unicas': categorias_unicas,
            'top_categorias': top_categorias,
            'primeira_data': primeira_data,
            'ultima_data': ultima_data
        }
    
    def close(self):
        """Fecha conexão com o banco."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
