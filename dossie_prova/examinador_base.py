"""
Base comum dos examinadores de prova (documental, pericial, oral).

Cada chamada à API analisa um GRUPO de questões sobre o mesmo conteúdo, em vez
de reenviar o conteúdo inteiro uma vez por questão. O conteúdo vai no início da
mensagem e a lista de questões no fim: assim as chamadas de um mesmo segmento
compartilham o prefixo e aproveitam o cache de prompt da xAI.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

import requests
from pydantic import BaseModel

from log_execucao import API, etapa
from xai_reasoning import aplicar_reasoning_effort

QuestaoAlvo = Tuple[str, str]
ResultadoQuestao = Tuple[List[Any], List[str]]


class ExaminadorBase:
    """Lógica compartilhada; subclasses definem regras, chave e modelo da prova."""

    TIPO = ""
    ROTULO_CONTEUDO = ""
    CHAVE_PROVAS = ""
    MODELO_PROVA: Type[BaseModel] = BaseModel
    MIN_CHARS = 1
    AVISO_SEM_CONTEUDO = "Nenhum conteúdo fornecido"
    MAX_QUESTOES_POR_CHAMADA = 6
    TIMEOUT_BASE_S = 120
    TIMEOUT_POR_QUESTAO_S = 45
    TENTATIVAS = 2

    def __init__(
        self,
        api_key: str,
        modelo: str = "grok-4.6",
        reasoning_effort: Optional[str] = None,
        conv_id: Optional[str] = None,
    ):
        self.api_key = api_key
        self.modelo = modelo
        self.reasoning_effort = reasoning_effort
        self.conv_id = conv_id
        self.base_url = "https://api.x.ai/v1"

    def _regras(self) -> str:
        raise NotImplementedError

    def _exemplo_item(self) -> str:
        raise NotImplementedError

    def _instrucao_final(self) -> str:
        return "Extraia as provas relevantes seguindo rigorosamente as regras de valoração."

    def _get_prompt_sistema(self) -> str:
        return (
            f"{self._regras()}\n\n"
            "FORMATO DE SAÍDA (JSON):\n"
            "{\n"
            '  "por_questao": [\n'
            "    {\n"
            '      "questao_id": "Q1",\n'
            f'      "{self.CHAVE_PROVAS}": [\n{self._exemplo_item()}\n      ],\n'
            '      "avisos": ["avisos específicos desta questão"]\n'
            "    }\n"
            "  ],\n"
            '  "avisos_gerais": ["avisos que valem para todas as questões"]\n'
            "}\n\n"
            "Inclua em por_questao UMA entrada para CADA questão listada, mesmo sem provas "
            f'(nesse caso "{self.CHAVE_PROVAS}": []). Use exatamente os IDs de questão informados.'
        )

    def _construir_prompt(
        self,
        questoes: Sequence[QuestaoAlvo],
        conteudo: str,
        impugnacoes: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        linhas = [f"{self.ROTULO_CONTEUDO}:", conteudo, "", "---", "", "QUESTÕES A ANALISAR:"]
        for questao_id, titulo in questoes:
            linhas.append(f"- {questao_id}: {titulo}")
            for imp in (impugnacoes or {}).get(questao_id) or []:
                linhas.append(f"    • Impugnação da defesa: {imp}")
        linhas += ["", self._instrucao_final(), "Retorne JSON válido."]
        return "\n".join(linhas)

    def examinar(
        self,
        questao_id: str,
        questao_titulo: str,
        conteudo: str,
        impugnacoes: Optional[List[str]] = None,
    ) -> ResultadoQuestao:
        """Examina uma única questão (compatibilidade)."""
        resultado = self.examinar_questoes(
            [(questao_id, questao_titulo)],
            conteudo,
            {questao_id: impugnacoes or []},
        )
        return resultado[questao_id]

    def examinar_questoes(
        self,
        questoes: Sequence[QuestaoAlvo],
        conteudo: str,
        impugnacoes: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, ResultadoQuestao]:
        """Examina várias questões, agrupando-as em poucas chamadas."""
        resultado: Dict[str, ResultadoQuestao] = {qid: ([], []) for qid, _ in questoes}
        if not questoes:
            return resultado
        if not conteudo or len(conteudo.strip()) < self.MIN_CHARS:
            for qid, _ in questoes:
                resultado[qid][1].append(self.AVISO_SEM_CONTEUDO)
            return resultado

        tamanho = max(1, self.MAX_QUESTOES_POR_CHAMADA)
        grupos = [questoes[i:i + tamanho] for i in range(0, len(questoes), tamanho)]
        for indice, grupo in enumerate(grupos, 1):
            parcial = self._examinar_grupo(
                grupo, conteudo, impugnacoes, f"{indice}/{len(grupos)}"
            )
            for qid, (provas, avisos) in parcial.items():
                resultado[qid][0].extend(provas)
                resultado[qid][1].extend(avisos)
        return resultado

    def _examinar_grupo(
        self,
        grupo: Sequence[QuestaoAlvo],
        conteudo: str,
        impugnacoes: Optional[Dict[str, List[str]]],
        rotulo_grupo: str,
    ) -> Dict[str, ResultadoQuestao]:
        ids = [qid for qid, _ in grupo]
        prompt = self._construir_prompt(grupo, conteudo, impugnacoes)
        payload = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": self._get_prompt_sistema()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        aplicar_reasoning_effort(payload, self.modelo, self.reasoning_effort)
        timeout = self.TIMEOUT_BASE_S + self.TIMEOUT_POR_QUESTAO_S * (len(grupo) - 1)

        try:
            dados = self._chamar_api(payload, timeout, ids, rotulo_grupo, len(prompt))
        except Exception as e:
            erro = f"Erro ao examinar provas {self.TIPO}: {e}"
            return {qid: ([], [erro]) for qid in ids}
        return self._distribuir_resposta(dados, ids, conteudo)

    def _chamar_api(
        self,
        payload: Dict[str, Any],
        timeout: float,
        ids: List[str],
        rotulo_grupo: str,
        chars_prompt: int,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.conv_id:
            headers["x-grok-conv-id"] = self.conv_id

        ultimo_erro: Optional[Exception] = None
        for tentativa in range(1, self.TENTATIVAS + 1):
            try:
                with etapa(
                    f"dossie.{self.TIPO}.chat_completions",
                    categoria=API,
                    questoes=",".join(ids),
                    grupo=rotulo_grupo,
                    modelo=self.modelo,
                    reasoning=payload.get("reasoning_effort"),
                    chars_prompt=chars_prompt,
                    timeout_s=timeout,
                    tentativa=f"{tentativa}/{self.TENTATIVAS}",
                ) as reg:
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=timeout,
                    )
                    reg.registrar_http(response)
                    response.raise_for_status()
                    resultado = response.json()
                    reg.registrar_uso(resultado)
                conteudo = resultado["choices"][0]["message"]["content"]
                dados = json.loads(conteudo)
                if not isinstance(dados, dict):
                    raise ValueError("JSON da resposta não é um objeto")
                return dados
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                ultimo_erro = e
            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if not isinstance(status, int) or status < 500:
                    raise
                ultimo_erro = e
        raise RuntimeError(
            f"falha após {self.TENTATIVAS} tentativa(s): {ultimo_erro}"
        ) from ultimo_erro

    def _distribuir_resposta(
        self,
        dados: Dict[str, Any],
        ids: List[str],
        conteudo: str,
    ) -> Dict[str, ResultadoQuestao]:
        from pje_ids import enriquecer_id_em_objetos, normalizar_id_pje

        resultado: Dict[str, ResultadoQuestao] = {qid: ([], []) for qid in ids}
        avisos_gerais = [str(a) for a in dados.get("avisos_gerais") or []]

        entradas = dados.get("por_questao")
        if not isinstance(entradas, list):
            # Resposta no formato de questão única: {"<chave>": [...], "avisos": [...]}
            entradas = (
                [{"questao_id": ids[0], **dados}] if len(ids) == 1 else []
            )
            if not entradas:
                avisos_gerais.append("Resposta da API sem 'por_questao'")

        for entrada in entradas:
            if not isinstance(entrada, dict):
                continue
            qid = str(entrada.get("questao_id") or "").strip()
            if qid not in resultado:
                continue
            provas, avisos = resultado[qid]
            for item in entrada.get(self.CHAVE_PROVAS) or []:
                try:
                    provas.append(self.MODELO_PROVA(**item))
                except Exception as e:
                    avisos.append(f"Erro ao validar prova {self.TIPO}: {e}")
            avisos.extend(str(a) for a in entrada.get("avisos") or [])

        for qid in ids:
            provas, avisos = resultado[qid]
            for prova in provas:
                prova.id_pje = normalizar_id_pje(prova.id_pje)
            enriquecer_id_em_objetos(provas, conteudo)
            avisos.extend(avisos_gerais)
        return resultado
