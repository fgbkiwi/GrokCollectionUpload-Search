"""
Orquestrador da Minuta.

Coordena a geração da minuta em etapas:
1. Estrutura de tópicos
2. Minutas prévias por tópico
3. Minutas definitivas
"""

import json
import re
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from cartao_caso import CartaoDoCaso
from dossie_prova import DossieProva, DossieQuestao
from .schema import (
    EstruturaMinuta,
    TopicoEstrutura,
    MinutaTopico,
    MinutaDefinitiva,
    MinutaCompleta,
    Precedente,
)
from .kernel_sarah import KernelSarah
from .busca_precedentes import BuscaPrecedentes
from .modelos_tematicos import BibliotecaModelos


class OrquestradorMinuta:
    """Orquestra a geração da minuta da sentença."""
    
    def __init__(
        self,
        api_key: str,
        management_key: Optional[str] = None,
        modelo: str = "grok-beta"
    ):
        self.api_key = api_key
        self.management_key = management_key
        self.modelo = modelo
        self.kernel = KernelSarah()
        self.biblioteca = BibliotecaModelos()
        self.busca: Optional[BuscaPrecedentes] = None
        self.base_url = "https://api.x.ai/v1"
    
    def configurar_busca(self, collection_id: str):
        """Configura a busca de precedentes."""
        if not self.management_key:
            raise ValueError("Management key necessária para busca de precedentes")
        
        self.busca = BuscaPrecedentes(
            self.api_key,
            self.management_key,
            collection_id
        )
    
    def gerar_estrutura(
        self,
        cartao: CartaoDoCaso,
        dossie: DossieProva
    ) -> tuple[EstruturaMinuta, List[str]]:
        """
        Gera a estrutura de tópicos da sentença.
        
        Args:
            cartao: Cartão do caso
            dossie: Dossiê de provas
            
        Returns:
            Tupla com (estrutura, avisos)
        """
        avisos = []
        
        prompt_estrutura = self._construir_prompt_estrutura(cartao, dossie)
        
        prompt_sistema = self.kernel.obter_prompt()
        
        try:
            resposta = self._chamar_api(
                prompt_sistema,
                prompt_estrutura,
                json_mode=True
            )
            
            dados = json.loads(resposta)
            
            topicos = []
            for t in dados.get("topicos", []):
                topico = TopicoEstrutura(**t)
                topicos.append(topico)
            
            estrutura = EstruturaMinuta(topicos=topicos)
            
            return estrutura, avisos
            
        except Exception as e:
            avisos.append(f"Erro ao gerar estrutura: {str(e)}")
            return EstruturaMinuta(), avisos
    
    def gerar_minuta_previa(
        self,
        topico: TopicoEstrutura,
        cartao: CartaoDoCaso,
        dossie: DossieProva
    ) -> tuple[MinutaTopico, List[str]]:
        """
        Gera minuta prévia para um tópico.
        
        Args:
            topico: Tópico da estrutura
            cartao: Cartão do caso
            dossie: Dossiê de provas
            
        Returns:
            Tupla com (minuta prévia, avisos)
        """
        avisos = []
        
        dossie_questao = None
        if topico.questao_id:
            for dq in dossie.dossies_por_questao:
                if dq.questao_id == topico.questao_id:
                    dossie_questao = dq
                    break
        
        prompt_previa = self._construir_prompt_previa(topico, cartao, dossie_questao)
        
        prompt_sistema = self.kernel.obter_prompt()
        
        try:
            resposta = self._chamar_api(
                prompt_sistema,
                prompt_previa,
                json_mode=True
            )
            
            dados = json.loads(resposta)
            dados["topico_id"] = topico.id
            dados["titulo"] = topico.titulo
            
            minuta = MinutaTopico(**dados)
            
            return minuta, avisos
            
        except Exception as e:
            avisos.append(f"Erro ao gerar minuta prévia: {str(e)}")
            return MinutaTopico(
                topico_id=topico.id,
                titulo=topico.titulo,
                tese="",
                antitese="",
                abordagem="",
                conclusao_preliminar=""
            ), avisos
    
    def gerar_minuta_definitiva(
        self,
        topico: TopicoEstrutura,
        minuta_previa: MinutaTopico,
        cartao: CartaoDoCaso,
        dossie: DossieProva,
        criterios_busca: Optional[Dict[str, Any]] = None
    ) -> tuple[MinutaDefinitiva, List[str]]:
        """
        Gera minuta definitiva para um tópico.
        
        Args:
            topico: Tópico da estrutura
            minuta_previa: Minuta prévia aprovada
            cartao: Cartão do caso
            dossie: Dossiê de provas
            criterios_busca: Critérios de busca de precedentes
            
        Returns:
            Tupla com (minuta definitiva, avisos)
        """
        avisos = []
        
        dossie_questao = None
        if topico.questao_id:
            for dq in dossie.dossies_por_questao:
                if dq.questao_id == topico.questao_id:
                    dossie_questao = dq
                    break
        
        precedentes = []
        if self.busca and criterios_busca:
            precedentes, avisos_busca = self._buscar_precedentes(
                topico,
                criterios_busca
            )
            avisos.extend(avisos_busca)
        
        modelos_tema = self._obter_modelos_tematicos(topico.titulo)
        
        prompt_definitiva = self._construir_prompt_definitiva(
            topico,
            minuta_previa,
            cartao,
            dossie_questao,
            precedentes,
            modelos_tema
        )
        
        prompt_sistema = self.kernel.obter_prompt()
        
        try:
            resposta = self._chamar_api(
                prompt_sistema,
                prompt_definitiva,
                json_mode=False
            )
            
            ids_citados = self._extrair_ids_citados(resposta)
            
            ids_disponiveis = self._coletar_ids_disponiveis(
                cartao, dossie, precedentes
            )
            
            ids_validos, ids_invalidos = self._validar_ids(
                ids_citados, ids_disponiveis
            )
            
            minuta = MinutaDefinitiva(
                topico_id=topico.id,
                titulo=topico.titulo,
                conteudo=resposta,
                precedentes_citados=precedentes,
                ids_citados=ids_citados,
                validada=ids_validos,
                avisos_validacao=[]
            )
            
            if not ids_validos:
                minuta.avisos_validacao.append(
                    f"IDs inválidos citados: {', '.join(ids_invalidos)}"
                )
                avisos.append(f"ATENÇÃO: Minuta cita IDs inexistentes: {ids_invalidos}")
            
            return minuta, avisos
            
        except Exception as e:
            avisos.append(f"Erro ao gerar minuta definitiva: {str(e)}")
            return MinutaDefinitiva(
                topico_id=topico.id,
                titulo=topico.titulo,
                conteudo="",
                validada=False,
                avisos_validacao=[str(e)]
            ), avisos
    
    def _chamar_api(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        json_mode: bool = False
    ) -> str:
        """Chama a API xAI."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            "temperature": 0.2
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        
        resultado = response.json()
        return resultado["choices"][0]["message"]["content"]
    
    def _construir_prompt_estrutura(
        self,
        cartao: CartaoDoCaso,
        dossie: DossieProva
    ) -> str:
        """Constrói prompt para geração de estrutura."""
        questoes_str = "\n".join([
            f"- {q.id}: {q.titulo} (momento: {q.momento})"
            for q in cartao.questoes if q.mencionar_na_minuta
        ])
        
        return f"""Gere a estrutura de tópicos da sentença trabalhista.

QUESTÕES A DECIDIR:
{questoes_str}

REGRAS:
- Pressupostos e condições da ação SÓ se arguidos OU se extinguem
- Depois mérito na ordem trabalhista usual
- Níveis hierárquicos: 1 (seção principal), 2 (subseção), 3 (item)

FORMATO JSON:
{{
  "topicos": [
    {{
      "id": "T1",
      "titulo": "Título",
      "nivel": 1,
      "ordem": 1,
      "questao_id": "Q1" ou null
    }}
  ]
}}

Retorne JSON válido."""
    
    def _construir_prompt_previa(
        self,
        topico: TopicoEstrutura,
        cartao: CartaoDoCaso,
        dossie_questao: Optional[DossieQuestao]
    ) -> str:
        """Constrói prompt para minuta prévia."""
        questao = None
        if topico.questao_id:
            for q in cartao.questoes:
                if q.id == topico.questao_id:
                    questao = q
                    break
        
        prompt = f"""Gere a minuta prévia para o tópico: {topico.titulo}

"""
        
        if questao:
            prompt += f"""QUESTÃO: {questao.titulo}
Tipo: {questao.tipo}
Momento: {questao.momento}

"""
        
        if dossie_questao:
            prompt += f"""PROVAS DISPONÍVEIS:
- {len(dossie_questao.provas_documentais)} documentais
- {len(dossie_questao.provas_periciais)} periciais
- {len(dossie_questao.provas_orais)} orais

"""
        
        prompt += """FORMATO JSON:
{
  "tese": "tese do autor resumidamente",
  "antitese": "antítese da defesa resumidamente",
  "abordagem": "como pretende abordar a questão",
  "conclusao_preliminar": "conclusão preliminar"
}

Retorne JSON válido."""
        
        return prompt
    
    def _construir_prompt_definitiva(
        self,
        topico: TopicoEstrutura,
        minuta_previa: MinutaTopico,
        cartao: CartaoDoCaso,
        dossie_questao: Optional[DossieQuestao],
        precedentes: List[Precedente],
        modelos_tema: List[str]
    ) -> str:
        """Constrói prompt para minuta definitiva."""
        prompt = f"""Redija a minuta definitiva do tópico: {topico.titulo}

ABORDAGEM APROVADA:
{minuta_previa.abordagem}

CONCLUSÃO PRELIMINAR:
{minuta_previa.conclusao_preliminar}

"""
        
        if dossie_questao:
            prompt += """PROVAS DOCUMENTAIS:
"""
            for p in dossie_questao.provas_documentais[:5]:
                prompt += f"\n- {p.trecho[:200]}... (ID {p.id_pje}, {p.folhas})"
            
            prompt += """\n\nPROVAS ORAIS:
"""
            for p in dossie_questao.provas_orais[:5]:
                if not p.desconsiderada:
                    prompt += f"\n- [{p.tipo_depoente}] {p.trecho[:200]}..."
        
        if precedentes:
            prompt += """\n\nPRECEDENTES RELEVANTES:
"""
            for p in precedentes[:3]:
                prompt += f"\n- {p.processo_numero}: {p.ementa[:200]}..."
        
        if modelos_tema:
            prompt += """\n\nMODELOS TEMÁTICOS DISPONÍVEIS:
"""
            for modelo in modelos_tema:
                prompt += f"\n{modelo}\n"
        
        prompt += """\n---

Redija a minuta em MARKDOWN, seguindo o kernel Sarah.
Cite IDs e folhas quando referenciar provas.
Se usar precedentes, cite o número do processo.
Transcreva literalmente trechos de prova relevantes.
"""
        
        return prompt
    
    def _buscar_precedentes(
        self,
        topico: TopicoEstrutura,
        criterios: Dict[str, Any]
    ) -> tuple[List[Precedente], List[str]]:
        """Busca precedentes para um tópico."""
        if not self.busca:
            return [], ["Busca não configurada"]
        
        query = f"{topico.titulo}"
        
        top_k = criterios.get("top_k", 5)
        mode = criterios.get("retrieval_mode", "hybrid")
        filtros = criterios.get("filtros")
        
        return self.busca.buscar(query, top_k, mode, filtros)
    
    def _obter_modelos_tematicos(self, titulo_topico: str) -> List[str]:
        """Obtém modelos temáticos relevantes."""
        titulo_lower = titulo_topico.lower()
        
        temas_mapeados = {
            "juros": "juros",
            "correção": "juros",
            "fgts": "fgts",
            "honorários": "honorarios",
            "honorários advocatícios": "honorarios",
            "recolhimentos": "recolhimentos",
            "contribuições": "recolhimentos",
        }
        
        modelos_texto = []
        
        for palavra_chave, tema in temas_mapeados.items():
            if palavra_chave in titulo_lower:
                modelos = self.biblioteca.buscar_por_tema(tema)
                for modelo in modelos:
                    modelos_texto.append(
                        f"### {modelo.nome}\n\n{modelo.texto}"
                    )
        
        return modelos_texto
    
    def _extrair_ids_citados(self, texto: str) -> List[str]:
        """Extrai IDs do PJe citados na minuta."""
        pattern = r'\(ID\s+\d+[,\s]+fls\.\s*\d+\)'
        matches = re.findall(pattern, texto)
        
        ids = []
        for match in matches:
            id_match = re.search(r'ID\s+(\d+)', match)
            if id_match:
                ids.append(id_match.group(1))
        
        return list(set(ids))
    
    def _coletar_ids_disponiveis(
        self,
        cartao: CartaoDoCaso,
        dossie: DossieProva,
        precedentes: List[Precedente]
    ) -> List[str]:
        """Coleta todos os IDs disponíveis."""
        ids = []
        
        for questao in cartao.questoes:
            for fonte in questao.fontes:
                if fonte.id_pje:
                    ids.append(fonte.id_pje)
        
        for dq in dossie.dossies_por_questao:
            for p in dq.provas_documentais:
                if p.id_pje:
                    ids.append(p.id_pje)
            for p in dq.provas_periciais:
                if p.id_pje:
                    ids.append(p.id_pje)
            for p in dq.provas_orais:
                if p.id_pje:
                    ids.append(p.id_pje)
        
        return ids
    
    def _validar_ids(
        self,
        ids_citados: List[str],
        ids_disponiveis: List[str]
    ) -> tuple[bool, List[str]]:
        """Valida IDs citados."""
        ids_invalidos = []
        
        for id_citado in ids_citados:
            encontrado = False
            for id_disp in ids_disponiveis:
                if id_citado in id_disp or id_disp in id_citado:
                    encontrado = True
                    break
            
            if not encontrado:
                ids_invalidos.append(id_citado)
        
        return len(ids_invalidos) == 0, ids_invalidos
