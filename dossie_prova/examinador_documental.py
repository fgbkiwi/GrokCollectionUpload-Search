"""
Examinador de Provas Documentais.
"""

from typing import Dict, List, Optional, Sequence

from .examinador_base import ExaminadorBase, QuestaoAlvo, ResultadoQuestao
from .schema import ProvaDocumental


class ExaminadorDocumental(ExaminadorBase):
    """Examina provas documentais dos autos."""

    TIPO = "documental"
    ROTULO_CONTEUDO = "CONTEÚDO DOCUMENTAL DOS AUTOS"
    CHAVE_PROVAS = "provas_documentais"
    MODELO_PROVA = ProvaDocumental

    def _regras(self) -> str:
        return """Você é um assistente jurídico especializado em análise de provas documentais trabalhistas.

Sua tarefa é identificar e extrair provas documentais relevantes para cada questão indicada.

REGRAS DE VALORAÇÃO DOCUMENTAL:
1. Documento prevalece sobre testemunha, salvo se houver vício ou simulação comprovada
2. Se a contestação NÃO impugnou especificamente uma irregularidade documental (ex: registros de ponto fraudulentos), 
   e o reclamante alegou a irregularidade, isso configura confissão ficta (art. 341 CPC, art. 167 §1º CC)
3. Impugnação específica deve ter grau de detalhe equivalente ao alegado
4. NUNCA invente ID do PJe, número de folhas, horário ou qualquer dado que não esteja no texto fornecido
5. ID do PJe: string alfanumérica de 7 caracteres (ex.: c7dbfbc, 4ac9a65). Aparece somente na última página da peça, nos 7 caracteres finais da linha "Documento assinado eletronicamente por ..., em DD/MM/AAAA, às HH:MM:SS - XXXXXXX". O texto das páginas anteriores da mesma peça pertence a esse ID. Também "ID XXXXXXX" / "(ID XXXXXXX)". Se não houver, deixe null (NÃO escreva "não informado") e avise
6. Transcreva literalmente trechos relevantes, não parafrasear"""

    def _exemplo_item(self) -> str:
        return """        {
          "trecho": "texto literal do documento",
          "id_pje": "c7dbfbc" ou null,
          "folhas": "fls. XX" ou null,
          "relevancia": "alta|media|baixa",
          "favoravel_a": "autor|reu|neutro",
          "tipo_documento": "tipo do documento",
          "observacao": "observações sobre valoração, vícios, impugnações"
        }"""

    def examinar_em_lotes(
        self,
        questao_id: str,
        questao_titulo: str,
        lotes_documentais: List[str],
        impugnacoes: Optional[List[str]] = None,
    ) -> ResultadoQuestao:
        """Examina uma questão em vários lotes de conteúdo (compatibilidade)."""
        resultado = self.examinar_questoes_em_lotes(
            [(questao_id, questao_titulo)],
            lotes_documentais,
            {questao_id: impugnacoes or []},
        )
        return resultado[questao_id]

    def examinar_questoes_em_lotes(
        self,
        questoes: Sequence[QuestaoAlvo],
        lotes: List[str],
        impugnacoes: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, ResultadoQuestao]:
        """Examina várias questões sobre conteúdo particionado em lotes."""
        resultado: Dict[str, ResultadoQuestao] = {
            qid: ([], [f"Análise documental em {len(lotes)} lote(s)"])
            for qid, _ in questoes
        }
        for lote in lotes:
            parcial = self.examinar_questoes(questoes, lote, impugnacoes)
            for qid, (provas, avisos) in parcial.items():
                resultado[qid][0].extend(provas)
                resultado[qid][1].extend(avisos)
        return resultado
