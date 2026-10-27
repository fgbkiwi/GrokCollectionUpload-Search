"""
Examinador de Provas Orais.

Implementa as regras específicas de valoração de depoimentos conforme
metodologia do juiz.
"""

from .examinador_base import ExaminadorBase
from .schema import ProvaOral


class ExaminadorOral(ExaminadorBase):
    """Examina provas orais dos autos (depoimentos)."""

    TIPO = "oral"
    ROTULO_CONTEUDO = "TRANSCRIÇÕES DE DEPOIMENTOS E ATAS DE AUDIÊNCIA"
    CHAVE_PROVAS = "provas_orais"
    MODELO_PROVA = ProvaOral
    MIN_CHARS = 50
    AVISO_SEM_CONTEUDO = "Nenhum conteúdo oral fornecido ou conteúdo muito curto"

    def _instrucao_final(self) -> str:
        return (
            "Extraia as provas orais relevantes para cada questão, aplicando RIGOROSAMENTE "
            "as regras de valoração oral. Marque como desconsiderada qualquer prova que "
            "viole as regras e explique o motivo."
        )

    def _regras(self) -> str:
        return """Você é um assistente jurídico especializado em análise de provas orais trabalhistas.

Sua tarefa é identificar e extrair depoimentos relevantes para cada questão indicada, aplicando rigorosamente as REGRAS DE VALORAÇÃO ORAL.

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

IMPORTANTE: Seja RIGOROSO na aplicação das regras. Melhor ter menos provas consistentes do que provas frágeis."""

    def _exemplo_item(self) -> str:
        return """        {
          "trecho": "texto literal com [timestamp] se existir",
          "id_pje": "c7dbfbc" ou null,
          "folhas": "fls. XX" ou null,
          "relevancia": "alta|media|baixa",
          "favoravel_a": "autor|reu|neutro",
          "tipo_depoente": "reclamante|reclamada|preposto|testemunha_autor|testemunha_reu",
          "nome_depoente": "nome se identificado",
          "observacao": "análise da valoração conforme as regras",
          "desconsiderada": true ou false,
          "motivo_desconsideracao": "motivo se desconsiderada"
        }"""
