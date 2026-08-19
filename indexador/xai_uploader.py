#!/usr/bin/env python3
"""
xai_uploader.py
Cliente para xAI Collections API com upload idempotente.

Funcionalidades:
- Criação e gerenciamento de Collections
- Upload de documentos em dois passos (file + add to collection)
- Metadados estruturados com field_definitions
- Idempotência via catálogo local
- Retries automáticos com backoff
- Chunking inteligente para documentos muito grandes
"""

import requests
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging


logger = logging.getLogger(__name__)


class XAICollectionsClient:
    """Cliente para xAI Collections API."""
    
    # Tamanho máximo por documento (caracteres)
    # Se um tópico exceder, será dividido em partes
    MAX_DOCUMENT_SIZE = 50000  # ~12k tokens
    CHUNK_OVERLAP = 2000  # Overlap entre chunks
    
    def __init__(
        self,
        api_key: str,
        management_key: str,
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        Inicializa cliente.
        
        Args:
            api_key: API key do xAI (para uploads de arquivos)
            management_key: Management API key (para gestão de collections)
            max_retries: Número máximo de tentativas em caso de erro
            timeout: Timeout em segundos para requisições
        """
        self.api_key = api_key
        self.management_key = management_key
        self.max_retries = max_retries
        self.timeout = timeout
        
        self.base_url = "https://api.x.ai/v1"
        self.management_url = "https://management-api.x.ai/v1"
        
        self.headers_api = {
            "Authorization": f"Bearer {api_key}"
        }
        
        self.headers_management = {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json"
        }
    
    def _retry_request(
        self,
        method: str,
        url: str,
        headers: Dict,
        **kwargs
    ) -> requests.Response:
        """
        Executa requisição com retries automáticos.
        
        Args:
            method: Método HTTP (GET, POST, etc)
            url: URL completa
            headers: Headers da requisição
            **kwargs: Argumentos adicionais para requests
        
        Returns:
            Response object
        
        Raises:
            Exception: Se todas as tentativas falharem
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Se 429 (rate limit) ou 5xx, tenta novamente
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        # Backoff exponencial: 2s, 4s, 8s
                        wait_time = 2 ** (attempt + 1)
                        logger.warning(
                            f"Status {response.status_code}, tentando novamente em {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Erro na requisição, tentando novamente em {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Falha após {self.max_retries} tentativas: {e}")
        
        raise Exception(f"Falha após {self.max_retries} tentativas")
    
    def listar_collections(self) -> List[Dict]:
        """
        Lista todas as Collections disponíveis.
        
        Returns:
            Lista de dicionários com dados das collections
        """
        response = self._retry_request(
            "GET",
            f"{self.management_url}/collections",
            self.headers_management
        )
        
        data = response.json()
        return data.get("collections", [])
    
    def obter_collection(self, collection_id: str) -> Dict:
        """
        Obtém informações de uma Collection.
        
        Args:
            collection_id: ID da collection
        
        Returns:
            Dicionário com dados da collection
        """
        response = self._retry_request(
            "GET",
            f"{self.management_url}/collections/{collection_id}",
            self.headers_management
        )
        
        return response.json()
    
    def criar_collection(
        self,
        name: str,
        description: Optional[str] = None,
        field_definitions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Cria uma nova Collection.
        
        Args:
            name: Nome da collection
            description: Descrição (opcional)
            field_definitions: Definições de campos de metadados
        
        Returns:
            Dicionário com dados da collection criada
        """
        payload = {"name": name}
        
        if description:
            payload["description"] = description
        
        if field_definitions:
            payload["field_definitions"] = field_definitions
        
        response = self._retry_request(
            "POST",
            f"{self.management_url}/collections",
            self.headers_management,
            json=payload
        )
        
        return response.json()
    
    def atualizar_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        field_definitions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Atualiza uma Collection existente.
        
        Args:
            collection_id: ID da collection
            name: Novo nome (opcional)
            description: Nova descrição (opcional)
            field_definitions: Novas definições de campos (opcional)
        
        Returns:
            Dicionário com dados atualizados
        """
        payload = {}
        
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if field_definitions:
            payload["field_definitions"] = field_definitions
        
        response = self._retry_request(
            "PATCH",
            f"{self.management_url}/collections/{collection_id}",
            self.headers_management,
            json=payload
        )
        
        return response.json()
    
    def upload_file(self, content: str, filename: str = "document.md") -> str:
        """
        Faz upload de arquivo para xAI (passo 1 do upload).
        
        Args:
            content: Conteúdo do documento (texto)
            filename: Nome do arquivo
        
        Returns:
            file_id retornado pela API
        """
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.md',
            delete=False
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Upload do arquivo
            with open(tmp_path, 'rb') as f:
                files = {'file': (filename, f, 'text/markdown')}
                
                response = self._retry_request(
                    "POST",
                    f"{self.base_url}/files",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files
                )
            
            data = response.json()
            return data['id']
        
        finally:
            # Remove arquivo temporário
            Path(tmp_path).unlink(missing_ok=True)
    
    def adicionar_documento_a_collection(
        self,
        collection_id: str,
        file_id: str,
        fields: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Adiciona documento à Collection (passo 2 do upload).
        
        Args:
            collection_id: ID da collection
            file_id: ID do arquivo (retornado por upload_file)
            fields: Metadados do documento
        
        Returns:
            Resposta da API
        """
        payload = {}
        if fields:
            payload["fields"] = fields
        
        response = self._retry_request(
            "POST",
            f"{self.management_url}/collections/{collection_id}/documents/{file_id}",
            self.headers_management,
            json=payload if payload else None
        )
        
        return response.json()
    
    def remover_documento_da_collection(
        self,
        collection_id: str,
        file_id: str
    ) -> None:
        """
        Remove documento da Collection.
        
        Args:
            collection_id: ID da collection
            file_id: ID do arquivo
        """
        try:
            self._retry_request(
                "DELETE",
                f"{self.management_url}/collections/{collection_id}/documents/{file_id}",
                self.headers_management
            )
        except Exception as e:
            logger.warning(f"Erro ao remover documento {file_id}: {e}")
    
    def chunkar_conteudo_grande(self, conteudo: str) -> List[str]:
        """
        Divide conteúdo muito grande em chunks com overlap.
        
        Args:
            conteudo: Texto do documento
        
        Returns:
            Lista de chunks (se necessário) ou lista com conteúdo original
        """
        if len(conteudo) <= self.MAX_DOCUMENT_SIZE:
            return [conteudo]
        
        chunks = []
        start = 0
        
        while start < len(conteudo):
            end = start + self.MAX_DOCUMENT_SIZE
            
            # Tenta quebrar em ponto final
            if end < len(conteudo):
                last_period = conteudo.rfind('.', start, end)
                if last_period > start + self.MAX_DOCUMENT_SIZE // 2:
                    end = last_period + 1
            
            chunk = conteudo[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Próximo chunk começa com overlap
            start = end - self.CHUNK_OVERLAP if end < len(conteudo) else end
        
        return chunks
    
    def upload_documento_completo(
        self,
        collection_id: str,
        categoria: str,
        conteudo: str,
        numero_processo: str,
        data_publicacao: Optional[str],
        reclamada: str,
        tipo_acao: str,
        parte_indice: Optional[int] = None,
        total_partes: Optional[int] = None
    ) -> str:
        """
        Faz upload completo de um documento (2 passos: file + collection).
        
        Args:
            collection_id: ID da collection de destino
            categoria: Categoria do tópico
            conteudo: Conteúdo do documento
            numero_processo: Número do processo
            data_publicacao: Data de publicação
            reclamada: Nome da reclamada (pode ser vazio)
            tipo_acao: Tipo de ação
            parte_indice: Índice da parte (se dividido)
            total_partes: Total de partes (se dividido)
        
        Returns:
            file_id do documento criado
        """
        # Monta conteúdo em Markdown
        md_content = f"# {categoria}\n\n"
        
        if parte_indice is not None:
            md_content += f"**[Parte {parte_indice} de {total_partes}]**\n\n"
        
        md_content += conteudo
        
        # Passo 1: Upload do arquivo
        filename = f"{numero_processo.replace('.', '_').replace('-', '_')}_{categoria[:50]}.md"
        file_id = self.upload_file(md_content, filename)
        
        # Passo 2: Adiciona à collection com metadados
        fields = {
            "numero_processo": numero_processo,
            "categoria": categoria,
            "tipo_acao": tipo_acao
        }
        
        if data_publicacao:
            fields["data_publicacao"] = data_publicacao
        
        if reclamada:
            fields["reclamada"] = reclamada
        
        if parte_indice is not None:
            fields["parte"] = f"{parte_indice}/{total_partes}"
        
        self.adicionar_documento_a_collection(collection_id, file_id, fields)
        
        return file_id


def criar_field_definitions_padrao() -> List[Dict]:
    """
    Cria field_definitions padrão para Collections de sentenças.
    
    Returns:
        Lista de definições de campos
    """
    return [
        {
            "name": "numero_processo",
            "type": "string",
            "required": True,
            "inject_into_chunk": True,
            "description": "Número do processo (formato CNJ)"
        },
        {
            "name": "categoria",
            "type": "string",
            "required": True,
            "inject_into_chunk": True,
            "description": "Categoria/tópico da fundamentação"
        },
        {
            "name": "data_publicacao",
            "type": "string",
            "required": False,
            "inject_into_chunk": False,
            "description": "Data de publicação da sentença (YYYY-MM-DD)"
        },
        {
            "name": "reclamada",
            "type": "string",
            "required": False,
            "inject_into_chunk": False,
            "description": "Nome da empresa/órgão reclamada"
        },
        {
            "name": "tipo_acao",
            "type": "string",
            "required": True,
            "inject_into_chunk": False,
            "description": "Tipo de ação trabalhista"
        }
    ]
