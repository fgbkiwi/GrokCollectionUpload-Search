"""
Orquestrador do Dossiê de Prova.

Coordena os examinadores de prova (documental, pericial, oral)
e gera o dossiê completo.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from cartao_caso import CartaoDoCaso, Questao
from .schema import DossieProva, DossieQuestao
from .examinador_documental import ExaminadorDocumental
from .examinador_pericial import ExaminadorPericial
from .examinador_oral import ExaminadorOral


class OrquestradorDossie:
    """Orquestra a montagem do dossiê de prova."""
    
    def __init__(self, api_key: str, modelo: str = "grok-beta"):
        self.api_key = api_key
        self.modelo = modelo
        self.examinador_documental = ExaminadorDocumental(api_key, modelo)
        self.examinador_pericial = ExaminadorPericial(api_key, modelo)
        self.examinador_oral = ExaminadorOral(api_key, modelo)
    
    def montar_dossie(
        self,
        cartao: CartaoDoCaso,
        caminho_autos_md: Path,
        callback_progresso: Optional[callable] = None
    ) -> tuple[DossieProva, List[str]]:
        """
        Monta o dossiê completo de provas.
        
        Args:
            cartao: Cartão do caso confirmado
            caminho_autos_md: Caminho para o arquivo MD dos autos
            callback_progresso: Função callback(etapa: str, progresso: float)
            
        Returns:
            Tupla com (dossiê completo, lista de avisos gerais)
        """
        avisos_gerais = []
        
        if not caminho_autos_md.exists():
            raise FileNotFoundError(f"Arquivo de autos não encontrado: {caminho_autos_md}")
        
        conteudo_autos = caminho_autos_md.read_text(encoding="utf-8")
        
        segmentos = self._segmentar_autos(conteudo_autos)
        
        avisos_gerais.append(
            f"Autos segmentados: {len(segmentos['documental'])} chars documental, "
            f"{len(segmentos['pericial'])} chars pericial, "
            f"{len(segmentos['oral'])} chars oral"
        )
        
        dossies_por_questao = []
        questoes_filtradas = [q for q in cartao.questoes if q.mencionar_na_minuta]
        
        total_questoes = len(questoes_filtradas)
        
        for idx, questao in enumerate(questoes_filtradas):
            if callback_progresso:
                callback_progresso(
                    f"Analisando questão {questao.id}: {questao.titulo}",
                    (idx / total_questoes) * 0.9
                )
            
            dossie_questao, avisos_questao = self._montar_dossie_questao(
                questao,
                segmentos,
                cartao
            )
            
            dossies_por_questao.append(dossie_questao)
            avisos_gerais.extend([f"[{questao.id}] {av}" for av in avisos_questao])
        
        if callback_progresso:
            callback_progresso("Dossiê completo", 1.0)
        
        dossie = DossieProva(
            cartao_origem=cartao.arquivo_origem,
            arquivo_autos=caminho_autos_md.name,
            dossies_por_questao=dossies_por_questao,
            avisos_gerais=avisos_gerais
        )
        
        return dossie, avisos_gerais
    
    def _segmentar_autos(self, conteudo: str) -> Dict[str, str]:
        """
        Segmenta os autos em seções: documental, pericial, oral.
        
        Heurística simples: busca por marcadores típicos.
        Em produção, pode ser mais sofisticado.
        """
        conteudo_lower = conteudo.lower()
        
        segmentos = {
            "documental": "",
            "pericial": "",
            "oral": ""
        }
        
        marcadores_oral = ["depoimento", "audiência", "termo de depoimento", "testemunha"]
        marcadores_pericial = ["laudo", "perícia", "perito", "conclusão pericial"]
        
        linhas = conteudo.split("\n")
        secao_atual = "documental"
        
        for linha in linhas:
            linha_lower = linha.lower()
            
            if any(m in linha_lower for m in marcadores_oral):
                secao_atual = "oral"
            elif any(m in linha_lower for m in marcadores_pericial):
                secao_atual = "pericial"
            
            segmentos[secao_atual] += linha + "\n"
        
        if len(segmentos["oral"]) == 0 and len(segmentos["pericial"]) == 0:
            segmentos["documental"] = conteudo
        
        return segmentos
    
    def _montar_dossie_questao(
        self,
        questao: Questao,
        segmentos: Dict[str, str],
        cartao: CartaoDoCaso
    ) -> tuple[DossieQuestao, List[str]]:
        """Monta o dossiê para uma questão específica."""
        avisos = []
        
        impugnacoes = self._obter_impugnacoes_questao(questao, cartao)
        
        provas_doc, avisos_doc = self._examinar_documental(
            questao,
            segmentos["documental"],
            impugnacoes
        )
        avisos.extend(avisos_doc)
        
        provas_per, avisos_per = self.examinador_pericial.examinar(
            questao.id,
            questao.titulo,
            segmentos["pericial"]
        )
        avisos.extend(avisos_per)
        
        provas_oral, avisos_oral = self.examinador_oral.examinar(
            questao.id,
            questao.titulo,
            segmentos["oral"]
        )
        avisos.extend(avisos_oral)
        
        dossie_questao = DossieQuestao(
            questao_id=questao.id,
            questao_titulo=questao.titulo,
            provas_documentais=provas_doc,
            provas_periciais=provas_per,
            provas_orais=provas_oral,
            avisos=avisos
        )
        
        return dossie_questao, avisos
    
    def _obter_impugnacoes_questao(
        self,
        questao: Questao,
        cartao: CartaoDoCaso
    ) -> List[str]:
        """Obtém impugnações específicas relacionadas à questão."""
        impugnacoes = []
        
        for contestacao in cartao.contestacoes:
            if contestacao.pedido_id in questao.pedido_ids:
                if not contestacao.impugnacao_especifica:
                    impugnacoes.append(
                        f"Contestação ao pedido {contestacao.pedido_id}: "
                        "impugnação NÃO específica (art. 341 CPC)"
                    )
                impugnacoes.extend(contestacao.teses)
        
        return impugnacoes
    
    def _examinar_documental(
        self,
        questao: Questao,
        conteudo_documental: str,
        impugnacoes: List[str]
    ) -> tuple[List, List[str]]:
        """
        Examina prova documental, particionando em lotes se necessário.
        """
        MAX_CHARS_POR_CHAMADA = 400000
        
        if len(conteudo_documental) <= MAX_CHARS_POR_CHAMADA:
            return self.examinador_documental.examinar(
                questao.id,
                questao.titulo,
                conteudo_documental,
                impugnacoes
            )
        else:
            lotes = self._particionar_em_lotes(
                conteudo_documental,
                MAX_CHARS_POR_CHAMADA
            )
            return self.examinador_documental.examinar_em_lotes(
                questao.id,
                questao.titulo,
                lotes,
                impugnacoes
            )
    
    def _particionar_em_lotes(
        self,
        conteudo: str,
        tamanho_max: int,
        overlap: int = 5000
    ) -> List[str]:
        """
        Particiona conteúdo em lotes com overlap para evitar perder contexto.
        """
        if tamanho_max <= 0:
            return [conteudo]

        # Passo de avanço entre lotes. O max(1, ...) garante progresso mesmo
        # quando overlap >= tamanho_max, evitando laço infinito.
        passo = max(1, tamanho_max - overlap)

        lotes = []
        inicio = 0
        total = len(conteudo)

        while inicio < total:
            fim = min(inicio + tamanho_max, total)
            lotes.append(conteudo[inicio:fim])

            # O lote atual já alcançou o fim do conteúdo: encerra o laço.
            # (Antes o término dependia de `inicio = fim - overlap >= total`,
            # que nunca ocorre quando overlap > 0, causando laço infinito.)
            if fim >= total:
                break

            inicio += passo

        return lotes
