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
    TipoTopico,
    MinutaTopico,
    MinutaDefinitiva,
    MinutaCompleta,
    Precedente,
)
from .kernel_sarah import KernelSarah
from .busca_precedentes import BuscaPrecedentes
from .modelos_tematicos import BibliotecaModelos
from pje_ids import extrair_ids_pje_do_texto, normalizar_id_pje


class OrquestradorMinuta:
    """Orquestra a geração da minuta da sentença."""
    
    def __init__(
        self,
        api_key: str,
        management_key: Optional[str] = None,
        modelo: str = "grok-4.6",
        reasoning_effort: Optional[str] = None,
    ):
        self.api_key = api_key
        self.management_key = management_key
        self.modelo = modelo
        self.reasoning_effort = reasoning_effort
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
        # Estrutura é JSON curto: reasoning alto/xhigh costuma estourar timeout
        # sem ganho; prévia/definitiva continuam com o nível escolhido na aba.
        reasoning_estrutura = self._limitar_reasoning_estrutura(self.reasoning_effort)
        if (
            self.reasoning_effort
            and reasoning_estrutura
            and reasoning_estrutura != str(self.reasoning_effort).strip().lower()
        ):
            avisos.append(
                f"Reasoning da estrutura limitado a '{reasoning_estrutura}' "
                f"(aba Minuta: '{self.reasoning_effort}') para evitar timeout."
            )
        
        try:
            resposta = self._chamar_api(
                prompt_sistema,
                prompt_estrutura,
                json_mode=True,
                reasoning_effort=reasoning_estrutura,
            )
            
            dados = json.loads(resposta)
            if not isinstance(dados, dict):
                raise ValueError("JSON da estrutura não é um objeto")

            lista_bruta = dados.get("topicos")
            if lista_bruta is None:
                for alt in ("tópicos", "topics", "estrutura", "secoes", "seções"):
                    if isinstance(dados.get(alt), list):
                        lista_bruta = dados[alt]
                        break
            if not isinstance(lista_bruta, list):
                lista_bruta = []

            topicos = []
            for t in lista_bruta:
                if not isinstance(t, dict):
                    continue
                qid = t.get("questao_id")
                if isinstance(qid, str) and qid.strip().lower() in ("null", "none", ""):
                    t["questao_id"] = None
                tipo_raw = t.get("tipo")
                if isinstance(tipo_raw, str) and tipo_raw.strip().lower() in ("null", "none", ""):
                    t.pop("tipo", None)
                try:
                    topico = TopicoEstrutura(**t)
                except Exception:
                    t["tipo"] = TipoTopico.OUTRO.value
                    try:
                        topico = TopicoEstrutura(**t)
                    except Exception as ex_topico:
                        avisos.append(f"Tópico ignorado por schema inválido: {ex_topico}")
                        continue
                topico = self._normalizar_tipo_topico(topico)
                topicos.append(topico)
            
            if not topicos:
                avisos.append(
                    "A API respondeu sem tópicos válidos. "
                    "Tente gerar de novo ou ajustar modelo/reasoning."
                )

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
        
        dossie_questao = self._obter_dossie_questao(topico, dossie)
        if (
            topico.tipo == TipoTopico.MERITO_QUESTAO
            and topico.questao_id
            and dossie_questao is None
        ):
            avisos.append(
                f"Nenhum dossiê encontrado para questao_id={topico.questao_id} "
                f"(tópico: {topico.titulo})"
            )
        
        prompt_previa = self._construir_prompt_previa(topico, cartao, dossie_questao, dossie)
        
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
        
        dossie_questao = self._obter_dossie_questao(topico, dossie)
        if (
            topico.tipo == TipoTopico.MERITO_QUESTAO
            and topico.questao_id
            and dossie_questao is None
        ):
            avisos.append(
                f"Nenhum dossiê encontrado para questao_id={topico.questao_id} "
                f"(tópico: {topico.titulo})"
            )
        
        precedentes = []
        if self.busca and criterios_busca and topico.tipo in (
            TipoTopico.MERITO_QUESTAO,
            TipoTopico.PRELIMINAR,
        ):
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
            dossie,
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
        json_mode: bool = False,
        reasoning_effort: Optional[str] = None,
        timeout: Optional[float] = None,
        tentativas: int = 2,
    ) -> str:
        """Chama a API xAI (com timeout por reasoning e 1 retry em timeout)."""
        import requests
        from xai_reasoning import aplicar_reasoning_effort
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        effort = (
            reasoning_effort
            if reasoning_effort is not None
            else self.reasoning_effort
        )
        timeout_s = timeout if timeout is not None else self._timeout_para_reasoning(effort)
        
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
        aplicar_reasoning_effort(payload, self.modelo, effort)

        ultimo_erro: Optional[Exception] = None
        for tentativa in range(1, max(1, tentativas) + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout_s,
                )
                response.raise_for_status()
                resultado = response.json()
                conteudo = self._extrair_texto_resposta(resultado)
                if json_mode:
                    conteudo = self._limpar_cerca_json(conteudo)
                return conteudo
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                ultimo_erro = e
                if tentativa >= tentativas:
                    break
                continue
            except requests.exceptions.RequestException:
                raise

        raise TimeoutError(
            f"Timeout após {tentativas} tentativa(s) "
            f"(limite {int(timeout_s)}s, reasoning={effort or 'padrão'}). "
            "Reduza o reasoning da Minuta ou tente novamente."
        ) from ultimo_erro

    @staticmethod
    def _timeout_para_reasoning(effort: Optional[str]) -> float:
        """Timeout de leitura proporcional ao nível de reasoning."""
        nivel = (effort or "").strip().lower()
        return {
            "none": 120.0,
            "low": 180.0,
            "medium": 300.0,
            "high": 480.0,
            "xhigh": 600.0,
        }.get(nivel, 300.0)

    @staticmethod
    def _limitar_reasoning_estrutura(effort: Optional[str]) -> Optional[str]:
        """Estrutura JSON: no máximo medium (evita timeout com high/xhigh)."""
        nivel = (effort or "").strip().lower()
        if not nivel:
            return "medium"
        if nivel in ("high", "xhigh"):
            return "medium"
        return nivel

    @staticmethod
    def _extrair_texto_resposta(data: Dict[str, Any]) -> str:
        """Obtém texto da resposta chat/completions (string ou blocos)."""
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Resposta da API sem choices/message: {e}") from e

        conteudo = message.get("content")
        if isinstance(conteudo, list):
            partes = []
            for bloco in conteudo:
                if isinstance(bloco, dict):
                    partes.append(bloco.get("text") or bloco.get("content") or "")
                else:
                    partes.append(str(bloco))
            conteudo = "".join(partes)

        if not conteudo or not str(conteudo).strip():
            # Alguns modelos com reasoning devolvem o útil em refusal/outros campos
            for alt in ("refusal", "reasoning_content"):
                alt_val = message.get(alt)
                if isinstance(alt_val, str) and alt_val.strip():
                    raise ValueError(
                        f"A API devolveu content vazio (campo '{alt}' presente). "
                        "Tente outro nível de reasoning ou modelo."
                    )
            raise ValueError(
                "A API devolveu content vazio. Tente novamente ou use outro modelo."
            )
        return str(conteudo)

    @staticmethod
    def _limpar_cerca_json(conteudo: str) -> str:
        """Remove cercas ```json se o modelo as incluir."""
        texto = (conteudo or "").strip()
        if texto.startswith("```"):
            texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\s*```$", "", texto)
        return texto
    
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
        resumo_dossie = self._resumo_dossie_para_estrutura(dossie)
        
        return f"""Gere a estrutura de tópicos da sentença trabalhista.

QUESTÕES A DECIDIR (use exatamente o ID indicado em questao_id):
{questoes_str}

RESUMO DO DOSSIÊ DE PROVAS (para orientar a ordem; NÃO invente provas):
{resumo_dossie}

REGRAS:
- Pressupostos e condições da ação SÓ se arguidos OU se extinguem
- Depois mérito na ordem trabalhista usual
- Níveis hierárquicos: 1 (seção principal), 2 (subseção), 3 (item)
- Inclua EXATAMENTE um tópico tipo "relatorio" (sem questao_id)
- Para cada questão listada acima, um tópico tipo "merito_questao" (ou "preliminar") com questao_id exato (Q1, Q2...)
- Inclua EXATAMENTE um tópico tipo "dispositivo" ao final (sem questao_id)
- NÃO crie tópico genérico "Mérito" sem questao_id
- Valores de tipo: "relatorio" | "preliminar" | "merito_questao" | "dispositivo"

FORMATO JSON:
{{
  "topicos": [
    {{
      "id": "T1",
      "titulo": "Relatório",
      "nivel": 1,
      "ordem": 1,
      "questao_id": null,
      "tipo": "relatorio"
    }},
    {{
      "id": "T2",
      "titulo": "Título da questão",
      "nivel": 1,
      "ordem": 2,
      "questao_id": "Q1",
      "tipo": "merito_questao"
    }},
    {{
      "id": "T3",
      "titulo": "Dispositivo",
      "nivel": 1,
      "ordem": 3,
      "questao_id": null,
      "tipo": "dispositivo"
    }}
  ]
}}

Retorne JSON válido."""
    
    def _resumo_dossie_para_estrutura(self, dossie: DossieProva) -> str:
        """Resumo curto do dossiê para a fase de estrutura."""
        if not dossie.dossies_por_questao:
            return "(nenhum dossiê por questão disponível)"
        linhas = []
        for dq in dossie.dossies_por_questao:
            linhas.append(
                f"- {dq.questao_id} ({dq.questao_titulo}): "
                f"{len(dq.provas_documentais)} doc, "
                f"{len(dq.provas_periciais)} per, "
                f"{len(dq.provas_orais)} oral"
            )
        return "\n".join(linhas)
    
    def _normalizar_tipo_topico(self, topico: TopicoEstrutura) -> TopicoEstrutura:
        """Infere/normaliza o papel do tópico quando a LLM omite ou erra o tipo."""
        titulo = self._normalizar_texto(topico.titulo)
        tipo = topico.tipo
        
        if tipo == TipoTopico.OUTRO or tipo is None:
            if "relatorio" in titulo or "relatório" in titulo:
                tipo = TipoTopico.RELATORIO
            elif "dispositivo" in titulo:
                tipo = TipoTopico.DISPOSITIVO
            elif topico.questao_id:
                if "preliminar" in titulo or "pressuposto" in titulo:
                    tipo = TipoTopico.PRELIMINAR
                else:
                    tipo = TipoTopico.MERITO_QUESTAO
            elif titulo in {"merito", "mérito"}:
                # Seção genérica sem questão: trata como outro (não injeta dossiê).
                tipo = TipoTopico.OUTRO
            else:
                tipo = TipoTopico.OUTRO
        
        if tipo in (TipoTopico.RELATORIO, TipoTopico.DISPOSITIVO):
            topico.questao_id = None
        elif tipo in (TipoTopico.MERITO_QUESTAO, TipoTopico.PRELIMINAR) and not topico.questao_id:
            # Mantém; o aviso virá na geração se não achar dossiê por título.
            pass
        
        topico.tipo = tipo
        return topico
    
    def _obter_dossie_questao(
        self,
        topico: TopicoEstrutura,
        dossie: DossieProva
    ) -> Optional[DossieQuestao]:
        """Localiza o dossiê da questão pelo ID; se falhar, tenta pelo título."""
        if topico.tipo in (TipoTopico.RELATORIO, TipoTopico.DISPOSITIVO):
            return None
        
        if topico.questao_id:
            for dq in dossie.dossies_por_questao:
                if dq.questao_id == topico.questao_id:
                    return dq
        
        if topico.tipo not in (TipoTopico.MERITO_QUESTAO, TipoTopico.PRELIMINAR, TipoTopico.OUTRO):
            return None
        
        titulo_norm = self._normalizar_texto(topico.titulo)
        if not titulo_norm:
            return None
        
        for dq in dossie.dossies_por_questao:
            titulo_dq = self._normalizar_texto(dq.questao_titulo)
            if titulo_norm == titulo_dq or titulo_norm in titulo_dq or titulo_dq in titulo_norm:
                return dq
        
        return None
    
    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        """Normaliza texto para comparação tolerante de títulos."""
        return re.sub(r"\s+", " ", (texto or "").strip().lower())
    
    def _formatar_prova_linha(self, prova: Any, prefixo: str = "", limite: int = 800) -> str:
        """Formata uma prova com trecho, ID e folhas para o prompt."""
        trecho = (prova.trecho or "").strip()
        if len(trecho) > limite:
            trecho = trecho[:limite].rstrip() + "..."
        
        partes_meta = []
        id_pje = normalizar_id_pje(getattr(prova, "id_pje", None))
        if id_pje:
            partes_meta.append(f"ID {id_pje}")
        folhas = getattr(prova, "folhas", None)
        if folhas:
            partes_meta.append(str(folhas))
        meta = f" ({', '.join(partes_meta)})" if partes_meta else ""
        
        if prefixo:
            return f"\n- [{prefixo}] {trecho}{meta}"
        return f"\n- {trecho}{meta}"
    
    def _formatar_bloco_provas(self, dossie_questao: DossieQuestao) -> str:
        """Monta o bloco de provas documentais, periciais e orais para o prompt."""
        linhas = []
        
        documentais = dossie_questao.provas_documentais[:10]
        linhas.append("PROVAS DOCUMENTAIS:")
        if documentais:
            for p in documentais:
                tipo = getattr(p, "tipo_documento", None) or "documento"
                linhas.append(self._formatar_prova_linha(p, prefixo=tipo, limite=600))
        else:
            linhas.append("\n(nenhuma prova documental neste dossiê)")
        
        periciais = dossie_questao.provas_periciais[:10]
        linhas.append("\n\nPROVAS PERICIAIS:")
        if periciais:
            for p in periciais:
                tipo = getattr(p, "tipo_laudo", None) or "laudo"
                # Laudos costumam ser o eixo da fundamentação: trechos mais longos.
                linhas.append(self._formatar_prova_linha(p, prefixo=tipo, limite=1200))
        else:
            linhas.append("\n(nenhuma prova pericial neste dossiê)")
        
        orais = [p for p in dossie_questao.provas_orais[:10] if not p.desconsiderada]
        linhas.append("\n\nPROVAS ORAIS:")
        if orais:
            for p in orais:
                prefixo = p.tipo_depoente
                if p.nome_depoente:
                    prefixo = f"{p.tipo_depoente} — {p.nome_depoente}"
                linhas.append(self._formatar_prova_linha(p, prefixo=prefixo, limite=600))
        else:
            linhas.append("\n(nenhuma prova oral utilizável neste dossiê)")
        
        return "".join(linhas) + "\n"
    
    def _resumo_cartao_para_relatorio(self, cartao: CartaoDoCaso) -> str:
        """Contexto narrativo para o tópico Relatório."""
        partes = ", ".join(f"{p.tipo}: {p.nome}" for p in (cartao.partes or []))
        questoes = "\n".join(
            f"- {q.id}: {q.titulo}"
            for q in cartao.questoes
            if q.mencionar_na_minuta
        )
        return f"""PARTES: {partes or '(não informadas)'}
NÚMERO DO PROCESSO: {cartao.numero_processo or '(não informado)'}
QUESTÕES A MENCIONAR NO RELATÓRIO:
{questoes or '(nenhuma)'}
"""
    
    def _construir_prompt_previa(
        self,
        topico: TopicoEstrutura,
        cartao: CartaoDoCaso,
        dossie_questao: Optional[DossieQuestao],
        dossie: Optional[DossieProva] = None,
    ) -> str:
        """Constrói prompt para minuta prévia conforme o papel do tópico."""
        if topico.tipo == TipoTopico.RELATORIO:
            return f"""Gere a minuta prévia do RELATÓRIO da sentença (apenas planejamento narrativo).

{self._resumo_cartao_para_relatorio(cartao)}

FORMATO JSON:
{{
  "tese": "síntese da pretensão autoral",
  "antitese": "síntese da defesa",
  "abordagem": "como narrar o relatório (partes, pedidos, defesa, provas produzidas)",
  "conclusao_preliminar": "o relatório deve permanecer narrativo, sem julgar o mérito"
}}

Retorne JSON válido."""
        
        if topico.tipo == TipoTopico.DISPOSITIVO:
            questoes = "\n".join(
                f"- {q.id}: {q.titulo}"
                for q in cartao.questoes
                if q.mencionar_na_minuta
            )
            return f"""Gere a minuta prévia do DISPOSITIVO final da sentença.

QUESTÕES CUJOS COMANDOS DEVEM SER ESPELHADOS:
{questoes}

FORMATO JSON:
{{
  "tese": "n/a",
  "antitese": "n/a",
  "abordagem": "como espelhar os comandos decisórios, custas e encargos",
  "conclusao_preliminar": "dispositivo consolida os comandos das questões de mérito já planejadas"
}}

Retorne JSON válido."""
        
        questao = None
        if topico.questao_id:
            for q in cartao.questoes:
                if q.id == topico.questao_id:
                    questao = q
                    break
        
        prompt = f"""Gere a minuta prévia para o tópico de mérito: {topico.titulo}

"""
        
        if questao:
            prompt += f"""QUESTÃO: {questao.titulo}
Tipo: {questao.tipo}
Momento: {questao.momento}

"""
        
        if dossie_questao:
            prompt += f"""RESUMO DAS PROVAS:
- {len(dossie_questao.provas_documentais)} documentais
- {len(dossie_questao.provas_periciais)} periciais
- {len(dossie_questao.provas_orais)} orais

{self._formatar_bloco_provas(dossie_questao)}
"""
        elif topico.tipo in (TipoTopico.MERITO_QUESTAO, TipoTopico.PRELIMINAR):
            prompt += """ORIENTAÇÃO INTERNA (não reproduzir na minuta): não há dossiê vinculado a esta questão; planeje a abordagem só com o cartão, sem inventar provas.

"""
        
        prompt += """FORMATO JSON:
{
  "tese": "tese do autor com densidade adequada",
  "antitese": "antítese da defesa com densidade adequada",
  "abordagem": "plano dialético: prova a valorar, direito aplicável, refutações",
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
        dossie: DossieProva,
        precedentes: List[Precedente],
        modelos_tema: List[str]
    ) -> str:
        """Constrói prompt para minuta definitiva conforme o papel do tópico."""
        if topico.tipo == TipoTopico.RELATORIO:
            return f"""Redija APENAS o RELATÓRIO da sentença trabalhista em MARKDOWN.

ABORDAGEM APROVADA:
{minuta_previa.abordagem}

{self._resumo_cartao_para_relatorio(cartao)}

REGRAS:
- Linguagem forense habitual de relatório judicial
- Narrativa contínua (sem subtítulos I/II/III de Fundamentação/Dispositivo)
- NÃO julgue o mérito, NÃO escreva fundamentação nem dispositivo
- NÃO mencione ausência de dossiê nem instruções internas
- Não invente IDs; cite folhas ou IDs só se estiverem no material acima
"""
        
        if topico.tipo == TipoTopico.DISPOSITIVO:
            questoes = "\n".join(
                f"- {q.id}: {q.titulo}"
                for q in cartao.questoes
                if q.mencionar_na_minuta
            )
            return f"""Redija APENAS o DISPOSITIVO final da sentença trabalhista em MARKDOWN.

ABORDAGEM APROVADA:
{minuta_previa.abordagem}

CONCLUSÃO PRELIMINAR:
{minuta_previa.conclusao_preliminar}

QUESTÕES A ESPELHAR:
{questoes}

REGRAS:
- Espelhe os comandos decisórios em voz passiva pronominal / terceira pessoa
- Inclua custas, recolhimentos e honorários quando cabível
- NÃO repita relatório nem fundamentação
- NÃO use placeholders do tipo "[a definir]" ou "conforme diretrizes do juízo"
- NÃO mencione ausência de dossiê
"""
        
        prompt = f"""Redija a FUNDAMENTAÇÃO dialética do tópico: {topico.titulo}

ABORDAGEM APROVADA:
{minuta_previa.abordagem}

CONCLUSÃO PRELIMINAR:
{minuta_previa.conclusao_preliminar}

"""
        
        if dossie_questao:
            prompt += self._formatar_bloco_provas(dossie_questao)
        else:
            prompt += (
                "ORIENTAÇÃO INTERNA (não reproduzir na minuta): "
                "não há dossiê vinculado; fundamente só com o cartão/abordagem, "
                "sem inventar IDs, folhas ou trechos de prova.\n\n"
            )
        
        if precedentes:
            prompt += "\nPRECEDENTES RELEVANTES:\n"
            for p in precedentes[:3]:
                prompt += f"\n- {p.processo_numero}: {p.ementa[:200]}..."
        
        if modelos_tema:
            prompt += "\n\nMODELOS TEMÁTICOS DISPONÍVEIS:\n"
            for modelo in modelos_tema:
                prompt += f"\n{modelo}\n"
        
        prompt += """
---

REGRAS DE REDAÇÃO DESTE TÓPICO:
- Escreva SOMENTE a fundamentação desta questão (não reinicie Relatório nem Dispositivo completo)
- Densidade de decisão judicial: desenvolva alegações das partes, valoração da prova e subsunção
- Transcreva literalmente trechos de prova relevantes
- Cite ID e folhas apenas quando constarem do material; se faltar ID, cite só as folhas
- NÃO escreva "ID não informado" nem "Não há dossiê de provas vinculado a este tópico"
- Markdown forense, sem metalinguagem
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
        """Extrai IDs do PJe citados na minuta (numéricos ou alfanuméricos)."""
        return extrair_ids_pje_do_texto(texto)
    
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
        disponiveis = [
            (normalizar_id_pje(i) or i or "").lower()
            for i in ids_disponiveis
            if i
        ]
        
        for id_citado in ids_citados:
            citado = (normalizar_id_pje(id_citado) or id_citado or "").lower()
            if not citado:
                continue
            encontrado = any(
                citado in disp or disp in citado
                for disp in disponiveis
            )
            if not encontrado:
                ids_invalidos.append(id_citado)
        
        return len(ids_invalidos) == 0, ids_invalidos
