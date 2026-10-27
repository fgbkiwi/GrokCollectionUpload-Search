"""
Orquestrador do Dossiê de Prova.

Coordena os examinadores de prova (documental, pericial, oral)
e gera o dossiê completo.
"""

import uuid
from pathlib import Path
from typing import List, Dict, Optional
from cartao_caso import CartaoDoCaso, Questao
from log_execucao import etapa
from .schema import DossieProva, DossieQuestao
from .examinador_base import QuestaoAlvo, ResultadoQuestao
from .examinador_documental import ExaminadorDocumental
from .examinador_pericial import ExaminadorPericial
from .examinador_oral import ExaminadorOral
from .segmentacao import segmentar_autos


class OrquestradorDossie:
    """Orquestra a montagem do dossiê de prova."""
    
    MAX_CHARS_POR_CHAMADA = 400_000
    
    def __init__(
        self,
        api_key: str,
        modelo: str = "grok-4.6",
        reasoning_effort: Optional[str] = None,
    ):
        self.api_key = api_key
        self.modelo = modelo
        self.reasoning_effort = reasoning_effort
        self.examinador_documental = ExaminadorDocumental(api_key, modelo, reasoning_effort)
        self.examinador_pericial = ExaminadorPericial(api_key, modelo, reasoning_effort)
        self.examinador_oral = ExaminadorOral(api_key, modelo, reasoning_effort)
    
    def montar_dossie(
        self,
        cartao: CartaoDoCaso,
        caminho_autos_md: Path,
        callback_progresso: Optional[callable] = None
    ) -> tuple[DossieProva, List[str]]:
        """
        Monta o dossiê completo de provas.
        
        Cada tipo de prova é examinado para todas as questões em poucas chamadas
        (grupos de questões), sem reenviar o mesmo conteúdo uma vez por questão.
        
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
        
        with etapa("dossie.leitura_autos", arquivo=caminho_autos_md.name) as reg:
            conteudo_autos = caminho_autos_md.read_text(encoding="utf-8")
            reg.atualizar(chars=len(conteudo_autos))
        
        with etapa("dossie.segmentacao") as reg:
            segmentos, blocos = segmentar_autos(conteudo_autos)
            reg.atualizar(
                **{f"chars_{k}": len(v) for k, v in segmentos.items()},
                **{f"blocos_{k}": n for k, n in blocos.items()},
            )
        
        avisos_gerais.append(
            f"Autos segmentados: {len(segmentos['documental'])} chars documental "
            f"({blocos['documental']} doc.), "
            f"{len(segmentos['pericial'])} chars pericial ({blocos['pericial']} doc.), "
            f"{len(segmentos['oral'])} chars oral ({blocos['oral']} doc.)"
        )
        
        questoes_filtradas = [q for q in cartao.questoes if q.mencionar_na_minuta]
        alvos: List[QuestaoAlvo] = [(q.id, q.titulo) for q in questoes_filtradas]
        impugnacoes = {
            q.id: self._obter_impugnacoes_questao(q, cartao) for q in questoes_filtradas
        }
        
        conv_id = f"sarah-dossie-{uuid.uuid4().hex[:12]}"
        for examinador in (
            self.examinador_documental,
            self.examinador_pericial,
            self.examinador_oral,
        ):
            examinador.conv_id = conv_id
        
        def progresso(mensagem: str, fracao: float) -> None:
            if callback_progresso:
                callback_progresso(mensagem, fracao)
        
        n = len(alvos)
        progresso(f"Examinando provas documentais ({n} questões)...", 0.05)
        with etapa(
            "dossie.exame_documental", questoes=n, chars=len(segmentos["documental"])
        ) as reg:
            res_doc = self._examinar_documental(alvos, segmentos["documental"], impugnacoes)
            reg.atualizar(provas=sum(len(p) for p, _ in res_doc.values()))
        
        progresso(f"Examinando provas periciais ({n} questões)...", 0.45)
        with etapa(
            "dossie.exame_pericial", questoes=n, chars=len(segmentos["pericial"])
        ) as reg:
            res_per = self.examinador_pericial.examinar_questoes(alvos, segmentos["pericial"])
            reg.atualizar(provas=sum(len(p) for p, _ in res_per.values()))
        
        progresso(f"Examinando provas orais ({n} questões)...", 0.75)
        with etapa(
            "dossie.exame_oral", questoes=n, chars=len(segmentos["oral"])
        ) as reg:
            res_oral = self.examinador_oral.examinar_questoes(alvos, segmentos["oral"])
            reg.atualizar(provas=sum(len(p) for p, _ in res_oral.values()))
        
        dossies_por_questao = []
        for questao in questoes_filtradas:
            provas_doc, avisos_doc = res_doc[questao.id]
            provas_per, avisos_per = res_per[questao.id]
            provas_oral, avisos_oral = res_oral[questao.id]
            avisos = avisos_doc + avisos_per + avisos_oral
            dossies_por_questao.append(
                DossieQuestao(
                    questao_id=questao.id,
                    questao_titulo=questao.titulo,
                    provas_documentais=provas_doc,
                    provas_periciais=provas_per,
                    provas_orais=provas_oral,
                    avisos=avisos,
                )
            )
            avisos_gerais.extend(f"[{questao.id}] {av}" for av in avisos)
        
        progresso("Dossiê completo", 1.0)
        
        dossie = DossieProva(
            cartao_origem=cartao.arquivo_origem,
            arquivo_autos=caminho_autos_md.name,
            dossies_por_questao=dossies_por_questao,
            avisos_gerais=avisos_gerais
        )
        
        return dossie, avisos_gerais
    
    def _segmentar_autos(self, conteudo: str) -> Dict[str, str]:
        """Segmenta os autos em documental, pericial e oral."""
        segmentos, _ = segmentar_autos(conteudo)
        return segmentos
    
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
        alvos: List[QuestaoAlvo],
        conteudo_documental: str,
        impugnacoes: Dict[str, List[str]],
    ) -> Dict[str, ResultadoQuestao]:
        """Examina prova documental, particionando em lotes se necessário."""
        if len(conteudo_documental) <= self.MAX_CHARS_POR_CHAMADA:
            return self.examinador_documental.examinar_questoes(
                alvos, conteudo_documental, impugnacoes
            )
        lotes = self._particionar_em_lotes(conteudo_documental, self.MAX_CHARS_POR_CHAMADA)
        return self.examinador_documental.examinar_questoes_em_lotes(
            alvos, lotes, impugnacoes
        )
    
    def _particionar_em_lotes(
        self,
        conteudo: str,
        tamanho_max: int,
        overlap: int = 5000
    ) -> List[str]:
        """
        Particiona o conteúdo sem descartar texto.

        Se houver várias peças do PJe, cada lote recebe peças inteiras, para o
        ID da última página não se separar do teor. Sem assinaturas, o corte é
        por tamanho, com sobreposição.
        """
        if tamanho_max <= 0:
            raise ValueError("tamanho_max deve ser positivo")
        if not 0 <= overlap < tamanho_max:
            raise ValueError("overlap deve estar entre 0 e tamanho_max - 1")

        from pje_ids import agrupar_pecas_em_lotes, dividir_em_pecas

        pecas = dividir_em_pecas(conteudo)
        if len(pecas) >= 2:
            # Cada lote leva peças inteiras, com o ID da última página junto do teor.
            return agrupar_pecas_em_lotes(pecas, tamanho_max)

        lotes = []
        inicio = 0
        total = len(conteudo)
        
        while inicio < total:
            fim = min(inicio + tamanho_max, total)
            lotes.append(conteudo[inicio:fim])
            if fim >= total:
                break
            inicio = fim - overlap
        
        return lotes
