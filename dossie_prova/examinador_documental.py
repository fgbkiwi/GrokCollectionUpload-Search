"""
Examinador de Provas Documentais.
"""

import json
import requests
from typing import List, Optional
from .schema import ProvaDocumental


class ExaminadorDocumental:
    """Examina provas documentais dos autos."""
    
    def __init__(self, api_key: str, modelo: str = "grok-beta"):
        self.api_key = api_key
        self.modelo = modelo
        self.base_url = "https://api.x.ai/v1"
    
    def examinar(
        self,
        questao_id: str,
        questao_titulo: str,
        conteudo_documental: str,
        impugnacoes: Optional[List[str]] = None
    ) -> tuple[List[ProvaDocumental], List[str]]:
        """
        Examina documentos relacionados a uma questão.
        
        Args:
            questao_id: ID da questão
            questao_titulo: Título da questão
            conteudo_documental: Conteúdo documental em Markdown
            impugnacoes: Lista de impugnações específicas do cartão
            
        Returns:
            Tupla com (lista de provas documentais, lista de avisos)
        """
        prompt = self._construir_prompt(questao_titulo, conteudo_documental, impugnacoes)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.modelo,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_prompt_sistema()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            resultado = response.json()
            conteudo = resultado["choices"][0]["message"]["content"]
            dados = json.loads(conteudo)
            
            provas = []
            for p in dados.get("provas_documentais", []):
                try:
                    prova = ProvaDocumental(**p)
                    provas.append(prova)
                except Exception as e:
                    avisos = dados.get("avisos", [])
                    avisos.append(f"Erro ao validar prova documental: {e}")
            
            avisos = dados.get("avisos", [])
            return provas, avisos
            
        except Exception as e:
            return [], [f"Erro ao examinar provas documentais: {str(e)}"]
    
    def _get_prompt_sistema(self) -> str:
        """Retorna o prompt de sistema para o examinador documental."""
        return """Você é um assistente jurídico especializado em análise de provas documentais trabalhistas.

Sua tarefa é identificar e extrair provas documentais relevantes para uma questão específica.

REGRAS DE VALORAÇÃO DOCUMENTAL:
1. Documento prevalece sobre testemunha, salvo se houver vício ou simulação comprovada
2. Se a contestação NÃO impugnou especificamente uma irregularidade documental (ex: registros de ponto fraudulentos), 
   e o reclamante alegou a irregularidade, isso configura confissão ficta (art. 341 CPC, art. 167 §1º CC)
3. Impugnação específica deve ter grau de detalhe equivalente ao alegado
4. NUNCA invente ID do PJe, número de folhas, horário ou qualquer dado que não esteja no texto fornecido
5. Se não houver ID ou folhas, deixe null e avise
6. Transcreva literalmente trechos relevantes, não parafrasear

FORMATO DE SAÍDA (JSON):
{
  "provas_documentais": [
    {
      "trecho": "texto literal do documento",
      "id_pje": "ID xxxxx" ou null,
      "folhas": "fls. XX" ou null,
      "relevancia": "alta|media|baixa",
      "favoravel_a": "autor|reu|neutro",
      "tipo_documento": "tipo do documento",
      "observacao": "observações sobre valoração, vícios, impugnações"
    }
  ],
  "avisos": ["avisos sobre dados ausentes, conflitos, etc."]
}"""
    
    def _construir_prompt(
        self,
        questao_titulo: str,
        conteudo: str,
        impugnacoes: Optional[List[str]]
    ) -> str:
        """Constrói o prompt para o modelo."""
        prompt = f"""Analise as provas documentais para a seguinte questão:

QUESTÃO: {questao_titulo}

"""
        
        if impugnacoes:
            prompt += f"""IMPUGNAÇÕES ESPECÍFICAS DA DEFESA:
{chr(10).join(f"- {imp}" for imp in impugnacoes)}

"""
        
        prompt += f"""CONTEÚDO DOCUMENTAL DOS AUTOS:
{conteudo}

---

Extraia as provas documentais relevantes para esta questão, seguindo rigorosamente as regras de valoração.
Retorne JSON válido."""
        
        return prompt
    
    def examinar_em_lotes(
        self,
        questao_id: str,
        questao_titulo: str,
        lotes_documentais: List[str],
        impugnacoes: Optional[List[str]] = None,
        max_tokens_por_lote: int = 100000
    ) -> tuple[List[ProvaDocumental], List[str]]:
        """
        Examina documentos em lotes quando o conteúdo é muito grande.
        
        Args:
            questao_id: ID da questão
            questao_titulo: Título da questão
            lotes_documentais: Lista de blocos de conteúdo documental
            impugnacoes: Impugnações específicas
            max_tokens_por_lote: Máximo de tokens por lote (aprox. 4 chars = 1 token)
            
        Returns:
            Tupla com (lista consolidada de provas, lista de avisos)
        """
        todas_provas = []
        todos_avisos = []
        
        for i, lote in enumerate(lotes_documentais):
            avisos_lote = []
            
            if len(lote) > max_tokens_por_lote * 4:
                avisos_lote.append(
                    f"Lote {i+1} muito grande ({len(lote)} chars), considere particionar mais"
                )
            
            provas, avisos = self.examinar(
                questao_id,
                questao_titulo,
                lote,
                impugnacoes
            )
            
            todas_provas.extend(provas)
            todos_avisos.extend(avisos_lote)
            todos_avisos.extend(avisos)
        
        todos_avisos.insert(0, f"Análise documental em {len(lotes_documentais)} lote(s)")
        
        return todas_provas, todos_avisos
