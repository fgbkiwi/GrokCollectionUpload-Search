"""
Busca de Precedentes na Collection xAI.
"""

from typing import List, Dict, Any, Optional, Literal
import requests
from .schema import Precedente, TipoPrecedente


class BuscaPrecedentes:
    """Busca precedentes na Collection xAI."""
    
    def __init__(
        self,
        api_key: str,
        management_key: str,
        collection_id: Optional[str] = None
    ):
        self.api_key = api_key
        self.management_key = management_key
        self.collection_id = collection_id
        self.base_url = "https://api.x.ai/v1"
        self.management_url = "https://management-api.x.ai"
    
    def listar_collections(self) -> List[Dict[str, Any]]:
        """Lista as Collections disponíveis."""
        headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.management_url}/v1/collections",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("collections", [])
            
        except Exception as e:
            return []
    
    def buscar(
        self,
        query: str,
        top_k: int = 5,
        retrieval_mode: Literal["hybrid", "keyword", "semantic"] = "hybrid",
        filtros: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Precedente], List[str]]:
        """
        Busca precedentes na Collection.
        
        Args:
            query: Consulta em linguagem natural
            top_k: Número máximo de resultados
            retrieval_mode: Modo de busca (hybrid, keyword, semantic)
            filtros: Filtros de metadados (categoria, reclamada, data, etc.)
            
        Returns:
            Tupla com (lista de precedentes, lista de avisos)
        """
        if not self.collection_id:
            return [], ["Nenhuma Collection selecionada"]
        
        avisos = []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "top_k": top_k,
            "retrieval_mode": retrieval_mode
        }
        
        if filtros:
            payload["filters"] = filtros
        
        try:
            response = requests.post(
                f"{self.base_url}/documents/search",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            resultados = data.get("results", [])
            
            precedentes = []
            
            for r in resultados:
                try:
                    precedente = self._extrair_precedente(r)
                    if precedente:
                        precedentes.append(precedente)
                except Exception as e:
                    avisos.append(f"Erro ao processar resultado: {e}")
            
            if len(precedentes) == 0:
                avisos.append("Nenhum precedente relevante encontrado")
            
            return precedentes, avisos
            
        except Exception as e:
            return [], [f"Erro na busca: {str(e)}"]
    
    def buscar_multiple_queries(
        self,
        queries: List[str],
        top_k: int = 3,
        retrieval_mode: Literal["hybrid", "keyword", "semantic"] = "hybrid"
    ) -> tuple[List[Precedente], List[str]]:
        """
        Busca múltiplas queries e consolida resultados.
        
        Útil para questões complexas que requerem múltiplas buscas.
        """
        todos_precedentes = []
        todos_avisos = []
        ids_vistos = set()
        
        for query in queries:
            precedentes, avisos = self.buscar(
                query,
                top_k=top_k,
                retrieval_mode=retrieval_mode
            )
            
            for p in precedentes:
                if p.id_collection and p.id_collection not in ids_vistos:
                    todos_precedentes.append(p)
                    ids_vistos.add(p.id_collection)
            
            todos_avisos.extend(avisos)
        
        todos_precedentes.sort(
            key=lambda x: x.relevancia_score if x.relevancia_score else 0,
            reverse=True
        )
        
        return todos_precedentes[:top_k * 2], todos_avisos
    
    def _extrair_precedente(self, resultado: Dict[str, Any]) -> Optional[Precedente]:
        """Extrai um Precedente de um resultado da busca."""
        content = resultado.get("content", "")
        metadata = resultado.get("metadata", {})
        score = resultado.get("score")
        doc_id = resultado.get("id")
        
        if not content:
            return None
        
        processo = metadata.get("numero_processo") or metadata.get("processo")
        
        tipo = TipoPrecedente.PROPRIO
        if metadata.get("tipo"):
            try:
                tipo = TipoPrecedente(metadata["tipo"])
            except ValueError:
                pass
        
        return Precedente(
            processo_numero=processo,
            ementa=content[:1000],
            relevancia_score=score,
            id_collection=doc_id,
            tipo=tipo
        )
    
    def validar_ids_citados(
        self,
        ids_citados: List[str],
        ids_disponiveis: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Valida se todos os IDs citados existem nos disponíveis.
        
        Args:
            ids_citados: IDs citados na minuta
            ids_disponiveis: IDs disponíveis no dossiê/cartão/precedentes
            
        Returns:
            Tupla com (todos válidos?, lista de IDs inválidos)
        """
        ids_invalidos = []
        
        for id_citado in ids_citados:
            id_limpo = id_citado.replace("ID", "").strip()
            
            encontrado = False
            for id_disp in ids_disponiveis:
                if id_limpo in id_disp or id_disp in id_limpo:
                    encontrado = True
                    break
            
            if not encontrado:
                ids_invalidos.append(id_citado)
        
        return len(ids_invalidos) == 0, ids_invalidos
