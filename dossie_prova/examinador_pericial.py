"""
Examinador de Provas Periciais.
"""

from .examinador_base import ExaminadorBase
from .schema import ProvaPericial


class ExaminadorPericial(ExaminadorBase):
    """Examina provas periciais dos autos (laudos)."""

    TIPO = "pericial"
    ROTULO_CONTEUDO = "CONTEÚDO PERICIAL DOS AUTOS (laudos e esclarecimentos)"
    CHAVE_PROVAS = "provas_periciais"
    MODELO_PROVA = ProvaPericial
    MIN_CHARS = 50
    AVISO_SEM_CONTEUDO = "Nenhum conteúdo pericial fornecido ou conteúdo muito curto"

    def _regras(self) -> str:
        return """Você é um assistente jurídico especializado em análise de provas periciais trabalhistas.

Sua tarefa é identificar e extrair trechos relevantes de laudos periciais para cada questão indicada.

REGRAS DE VALORAÇÃO PERICIAL:
1. Laudo pericial norteia questões técnicas (insalubridade, periculosidade, etc.) salvo prova robusta em contrário
2. Conclusões do perito têm presunção de veracidade
3. Impugnação ao laudo requer contra-prova técnica consistente
4. NUNCA invente ID do PJe, número de folhas, conclusões ou dados técnicos que não estejam no laudo
5. ID do PJe: string alfanumérica de 7 caracteres (ex.: b9283dd). Aparece somente na última página da peça, nos 7 caracteres finais da linha de assinatura eletrônica. Se não houver, null (não escreva "não informado")
6. Transcreva literalmente trechos relevantes do laudo"""

    def _exemplo_item(self) -> str:
        return """        {
          "trecho": "texto literal do laudo",
          "id_pje": "b9283dd" ou null,
          "folhas": "fls. XX" ou null,
          "relevancia": "alta|media|baixa",
          "favoravel_a": "autor|reu|neutro",
          "tipo_laudo": "médico|ambiental|contábil|engenharia|etc",
          "observacao": "observações sobre conclusões, impugnações, etc."
        }"""
