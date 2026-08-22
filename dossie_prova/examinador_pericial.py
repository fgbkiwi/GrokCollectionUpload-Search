"""
Examinador de Provas Periciais.
"""

import json
import requests
from typing import List
from .schema import ProvaPericial


class ExaminadorPericial:
    """Examina provas periciais dos autos (laudos)."""
    
    def __init__(self, api_key: str, modelo: str = "grok-beta"):
        self.api_key = api_key
        self.modelo = modelo
        self.base_url = "https://api.x.ai/v1"
    
    def examinar(
        self,
        questao_id: str,
        questao_titulo: str,
        conteudo_pericial: str
    ) -> tuple[List[ProvaPericial], List[str]]:
        """
        Examina laudos periciais relacionados a uma questão.
        
        Args:
            questao_id: ID da questão
            questao_titulo: Título da questão
            conteudo_pericial: Conteúdo de laudos em Markdown
            
        Returns:
            Tupla com (lista de provas periciais, lista de avisos)
        """
        if not conteudo_pericial or len(conteudo_pericial.strip()) < 50:
            return [], ["Nenhum conteúdo pericial fornecido ou conteúdo muito curto"]
        
        prompt = self._construir_prompt(questao_titulo, conteudo_pericial)
        
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
            for p in dados.get("provas_periciais", []):
                try:
                    prova = ProvaPericial(**p)
                    provas.append(prova)
                except Exception as e:
                    avisos = dados.get("avisos", [])
                    avisos.append(f"Erro ao validar prova pericial: {e}")
            
            avisos = dados.get("avisos", [])
            return provas, avisos
            
        except Exception as e:
            return [], [f"Erro ao examinar provas periciais: {str(e)}"]
    
    def _get_prompt_sistema(self) -> str:
        """Retorna o prompt de sistema para o examinador pericial."""
        return """Você é um assistente jurídico especializado em análise de provas periciais trabalhistas.

Sua tarefa é identificar e extrair trechos relevantes de laudos periciais para uma questão específica.

REGRAS DE VALORAÇÃO PERICIAL:
1. Laudo pericial norteia questões técnicas (insalubridade, periculosidade, etc.) salvo prova robusta em contrário
2. Conclusões do perito têm presunção de veracidade
3. Impugnação ao laudo requer contra-prova técnica consistente
4. NUNCA invente ID do PJe, número de folhas, conclusões ou dados técnicos que não estejam no laudo
5. Se não houver ID ou folhas, deixe null e avise
6. Transcreva literalmente trechos relevantes do laudo

FORMATO DE SAÍDA (JSON):
{
  "provas_periciais": [
    {
      "trecho": "texto literal do laudo",
      "id_pje": "ID xxxxx" ou null,
      "folhas": "fls. XX" ou null,
      "relevancia": "alta|media|baixa",
      "favoravel_a": "autor|reu|neutro",
      "tipo_laudo": "médico|ambiental|contábil|engenharia|etc",
      "observacao": "observações sobre conclusões, impugnações, etc."
    }
  ],
  "avisos": ["avisos sobre dados ausentes, conflitos, etc."]
}"""
    
    def _construir_prompt(self, questao_titulo: str, conteudo: str) -> str:
        """Constrói o prompt para o modelo."""
        return f"""Analise os laudos periciais para a seguinte questão:

QUESTÃO: {questao_titulo}

CONTEÚDO PERICIAL DOS AUTOS:
{conteudo}

---

Extraia as provas periciais relevantes para esta questão, seguindo rigorosamente as regras de valoração.
Retorne JSON válido."""
