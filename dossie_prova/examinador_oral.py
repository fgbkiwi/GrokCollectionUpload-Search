"""
Examinador de Provas Orais.

Implementa as regras específicas de valoração de depoimentos conforme
metodologia do juiz.
"""

import json
from typing import List
from .schema import ProvaOral


class ExaminadorOral:
    """Examina provas orais dos autos (depoimentos)."""
    
    def __init__(self, api_key: str, modelo: str = "grok-beta"):
        self.api_key = api_key
        self.modelo = modelo
        self.base_url = "https://api.x.ai/v1"
    
    def examinar(
        self,
        questao_id: str,
        questao_titulo: str,
        conteudo_oral: str
    ) -> tuple[List[ProvaOral], List[str]]:
        """
        Examina depoimentos relacionados a uma questão.
        
        Args:
            questao_id: ID da questão
            questao_titulo: Título da questão
            conteudo_oral: Transcrições de depoimentos em Markdown
            
        Returns:
            Tupla com (lista de provas orais, lista de avisos)
        """
        import requests
        
        if not conteudo_oral or len(conteudo_oral.strip()) < 50:
            return [], ["Nenhum conteúdo oral fornecido ou conteúdo muito curto"]
        
        prompt = self._construir_prompt(questao_titulo, conteudo_oral)
        
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
            for p in dados.get("provas_orais", []):
                try:
                    prova = ProvaOral(**p)
                    provas.append(prova)
                except Exception as e:
                    avisos = dados.get("avisos", [])
                    avisos.append(f"Erro ao validar prova oral: {e}")
            
            avisos = dados.get("avisos", [])
            return provas, avisos
            
        except Exception as e:
            return [], [f"Erro ao examinar provas orais: {str(e)}"]
    
    def _get_prompt_sistema(self) -> str:
        """Retorna o prompt de sistema com as regras de valoração oral."""
        return """Você é um assistente jurídico especializado em análise de provas orais trabalhistas.

Sua tarefa é identificar e extrair depoimentos relevantes, aplicando rigorosamente as REGRAS DE VALORAÇÃO ORAL.

REGRAS DE VALORAÇÃO ORAL (MÉTODO DO JUIZ):

1. DEPOIMENTO DE PARTE:
   - Só vale como CONFISSÃO REAL (fato contrário à própria pretensão)
   - Preposto NÃO fundamenta indeferimento
   - Reclamante NÃO fundamenta deferimento
   
2. DEPOIMENTO DE TESTEMUNHA:
   - Tem valor qualquer que seja quem arrolou
   - Pode confirmar inicial, defesa ou fato não alegado
   
3. DESCONSIDERAR TESTEMUNHA SE:
   - Mente ou oculta fato relevante
   - Contradiz documento não impugnado
   - Excede limites da lide:
     * Versão PIOR para autor do que a defesa alegou, OU
     * Versão MELHOR para autor do que a inicial alegou
     * Ex: inicial diz "intervalo suprimido 2 dias/semana" mas testemunha diz "quase todos os dias"
   
4. VALOR LIGADO A CONHECIMENTO PESSOAL E DETALHE:
   - Ouvir dizer = ZERO
   - Dúvida = ZERO
   - Inferência só se consequência necessária
   - Sem detalhes = desconsiderar
   - Pergunta do advogado já cheia de fatos + sim/não = indução, desconsiderar os fatos da pergunta
   - Conceitos abstratos só com fatos presenciados
   
5. CONFLITO ENTRE TESTEMUNHAS:
   - Genérico vale menos que específico
   - Resposta impessoal ("a gente registra ponto") vale menos que pessoal
   - Declaração CONTRA quem arrolou vale MAIS
   
6. TRANSCRIÇÃO:
   - Ao basear-se em depoimento, transcrever trechos com carimbo de tempo entre colchetes [] se existir no MD
   - Ex: "Trabalhava das 8h às 18h sem pausa [00:03:45]"
   - NUNCA invente ID, folha, horário ou fala

FORMATO DE SAÍDA (JSON):
{
  "provas_orais": [
    {
      "trecho": "texto literal com [timestamp] se existir",
      "id_pje": "ID xxxxx" ou null,
      "folhas": "fls. XX" ou null,
      "relevancia": "alta|media|baixa",
      "favoravel_a": "autor|reu|neutro",
      "tipo_depoente": "reclamante|reclamada|preposto|testemunha_autor|testemunha_reu",
      "nome_depoente": "nome se identificado",
      "observacao": "análise da valoração conforme as regras",
      "desconsiderada": true ou false,
      "motivo_desconsideracao": "motivo se desconsiderada"
    }
  ],
  "avisos": ["avisos sobre valoração, conflitos, etc."]
}

IMPORTANTE: Seja RIGOROSO na aplicação das regras. Melhor ter menos provas consistentes do que provas frágeis."""
    
    def _construir_prompt(self, questao_titulo: str, conteudo: str) -> str:
        """Constrói o prompt para o modelo."""
        return f"""Analise os depoimentos para a seguinte questão:

QUESTÃO: {questao_titulo}

TRANSCRIÇÕES DE DEPOIMENTOS:
{conteudo}

---

Extraia as provas orais relevantes para esta questão, aplicando RIGOROSAMENTE as regras de valoração oral.
Marque como desconsiderada qualquer prova que viole as regras e explique o motivo.
Retorne JSON válido."""
