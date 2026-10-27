"""
Extrator de Cartão do Caso usando API xAI Grok.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from .schema import CartaoDoCaso
from log_execucao import API, etapa
from xai_reasoning import aplicar_reasoning_effort
from xai_models import DEFAULT_MODEL as XAI_DEFAULT_MODEL
from xai_models import FALLBACK_MODELS, listar_modelos_xai


class ExtratorCartao:
    """Cliente HTTP para extrair estrutura jurídica de autos usando Grok."""
    
    API_BASE = "https://api.x.ai/v1"
    DEFAULT_MODEL = XAI_DEFAULT_MODEL
    TEMPERATURE = 0.1
    # Autos OCR passam de 1 milhão de tokens. Cada chamada leva peças inteiras
    # (até a assinatura da última página). O que não cabe segue em outro lote;
    # nenhum trecho é descartado.
    MAX_CHARS_ENVIO = 220_000
    TIMEOUT_API = 300
    
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
    ):
        """
        Inicializa o extrator.
        
        Args:
            api_key: Chave de API do xAI
            model: Modelo Grok a usar (padrão: grok-4.6)
            reasoning_effort: Nível de reasoning quando o modelo permitir
        """
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.reasoning_effort = reasoning_effort
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def listar_modelos(self) -> List[str]:
        """
        Lista modelos disponíveis na API.
        
        Returns:
            Lista de nomes de modelos
        """
        return listar_modelos_xai(self.api_key)
    
    def extrair_de_arquivo(self, caminho_md: Path, progresso_callback=None) -> CartaoDoCaso:
        """
        Extrai cartão de um arquivo Markdown.
        
        Args:
            caminho_md: Caminho para o arquivo .md
            progresso_callback: Função callback(mensagem: str) para reportar progresso
            
        Returns:
            CartaoDoCaso extraído e validado
        """
        if progresso_callback:
            progresso_callback(f"Lendo arquivo {caminho_md.name}...")
        
        with etapa("cartao.leitura_arquivo", arquivo=caminho_md.name) as reg:
            with open(caminho_md, 'r', encoding='utf-8') as f:
                conteudo_md = f.read()
            reg.atualizar(chars=len(conteudo_md))
        
        if progresso_callback:
            progresso_callback("Extraindo estrutura via Grok...")
        
        cartao_dict = self._extrair_estrutura(conteudo_md, progresso_callback)
        cartao_dict["arquivo_origem"] = str(caminho_md)
        
        if progresso_callback:
            progresso_callback("Validando schema...")
        
        with etapa("cartao.validacao_schema") as reg:
            cartao = CartaoDoCaso(**cartao_dict)
            self._garantir_conteudo_minimo(cartao)
            reg.atualizar(
                pedidos=self._contar_pedidos(cartao),
                questoes=len(cartao.questoes),
            )
        
        n_pedidos = self._contar_pedidos(cartao)
        if progresso_callback:
            progresso_callback(
                f"Cartão extraído: {n_pedidos} pedido(s), "
                f"{len(cartao.questoes)} questão(ões), {len(cartao.avisos)} aviso(s)"
            )
        
        return cartao
    
    def extrair_de_pasta(self, caminho_pasta: Path, progresso_callback=None) -> List[CartaoDoCaso]:
        """
        Extrai cartões de múltiplos arquivos MD em uma pasta.
        
        Args:
            caminho_pasta: Caminho para a pasta
            progresso_callback: Função callback(mensagem: str) para reportar progresso
            
        Returns:
            Lista de CartaoDoCaso extraídos
        """
        arquivos_md = list(caminho_pasta.glob("*.md"))
        
        if not arquivos_md:
            raise ValueError(f"Nenhum arquivo .md encontrado em {caminho_pasta}")
        
        if progresso_callback:
            progresso_callback(f"Encontrados {len(arquivos_md)} arquivo(s) .md")
        
        cartoes = []
        for i, arquivo in enumerate(arquivos_md, 1):
            if progresso_callback:
                progresso_callback(f"Processando arquivo {i}/{len(arquivos_md)}: {arquivo.name}")
            
            cartao = self.extrair_de_arquivo(arquivo, progresso_callback)
            cartoes.append(cartao)
        
        return cartoes
    
    def _extrair_estrutura(
        self,
        conteudo_md: str,
        progresso_callback=None,
    ) -> Dict[str, Any]:
        """
        Extrai estrutura JSON do conteúdo MD usando Grok.

        Autos maiores que a janela são distribuídos em lotes de peças completas.
        Cada peça inclui todas as páginas até a assinatura, onde está o ID.
        """
        from pje_ids import agrupar_pecas_em_lotes, dividir_em_pecas

        prompt = self._construir_prompt_extracao()
        with etapa("cartao.preparar_texto", chars_autos=len(conteudo_md)) as reg:
            pecas = dividir_em_pecas(conteudo_md)
            lotes = agrupar_pecas_em_lotes(pecas, self.MAX_CHARS_ENVIO) or [conteudo_md]
            ids_enviados = {peca.id_pje.lower() for peca in pecas if peca.id_pje}
            reg.atualizar(
                chars_envio=sum(len(lote) for lote in lotes),
                lotes=len(lotes),
                pecas=len(pecas),
                reduzido=False,
            )

        parciais = []
        for indice, lote in enumerate(lotes, 1):
            if progresso_callback:
                progresso_callback(
                    f"Extraindo lote {indice}/{len(lotes)} "
                    f"({len(lote)} caracteres; peças completas)..."
                )
            parciais.append(self._extrair_lote(prompt, lote, indice, len(lotes)))

        if len(parciais) == 1:
            cartao_dict = parciais[0]
        else:
            cartao_dict = self._fundir_cartoes(parciais, ids_enviados)
        self._enriquecer_ids_pje(cartao_dict, conteudo_md)
        return cartao_dict

    def _extrair_lote(
        self,
        prompt: str,
        texto: str,
        indice: int,
        total: int,
    ) -> Dict[str, Any]:
        """Chama o modelo para um lote e devolve o JSON já normalizado."""
        if total <= 1:
            instrucao = (
                "Extraia a estrutura jurídica destes autos. "
                "Preencha pedidos e questões sempre que houver pretensão, "
                "impugnação ou ponto controvertido no texto.\n\n"
            )
        else:
            instrucao = (
                f"Estes autos foram fracionados em {total} lotes para caber no "
                f"contexto. Este é o lote {indice} de {total}. "
                "Cada peça termina na linha de assinatura eletrônica; o ID "
                "(7 caracteres alfanuméricos) aparece só nessa última página, "
                "e todo o texto anterior da peça pertence a esse ID. "
                "Extraia pedidos, teses, decisões, pareceres e acordos que "
                "estiverem neste lote. É proibido avisar que a petição inicial, "
                "a contestação, a réplica, uma decisão, um parecer ou um acordo "
                "não está neste lote: outros lotes trazem o restante dos autos. "
                "Não crie aviso, de nenhum tipo, por essa ausência local.\n\n"
            )

        mensagens = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": instrucao + texto},
        ]
        payload = {
            "model": self.model,
            "messages": mensagens,
            "temperature": self.TEMPERATURE,
            "response_format": {"type": "json_object"},
        }
        aplicar_reasoning_effort(payload, self.model, self.reasoning_effort)

        try:
            with etapa(
                "cartao.chat_completions",
                categoria=API,
                modelo=self.model,
                reasoning=payload.get("reasoning_effort"),
                chars_prompt=len(prompt) + len(mensagens[1]["content"]),
                timeout_s=self.TIMEOUT_API,
                lote=indice,
                lotes=total,
            ) as reg:
                response = self.session.post(
                    f"{self.API_BASE}/chat/completions",
                    json=payload,
                    timeout=self.TIMEOUT_API,
                )
                reg.registrar_http(response)
                if not response.ok:
                    detalhe = self._formatar_erro_api(response)
                    raise RuntimeError(
                        f"Erro ao chamar API xAI ({response.status_code}) "
                        f"com modelo '{self.model}' no lote {indice}/{total}: {detalhe}"
                    )
                data = response.json()
                reg.registrar_uso(data)
            conteudo = self._extrair_texto_resposta(data)
            cartao_dict = self._parsear_json_resposta(conteudo)
            self._normalizar_resposta_llm(cartao_dict)
            return cartao_dict
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro ao chamar API xAI no lote {indice}/{total}: {e}")
        except (KeyError, json.JSONDecodeError, TypeError, ValueError) as e:
            raise RuntimeError(
                f"Erro ao processar resposta da API no lote {indice}/{total}: {e}"
            )

    @staticmethod
    def _extrair_texto_resposta(data: Dict[str, Any]) -> str:
        """Obtém o texto JSON da resposta chat/completions."""
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Resposta da API sem choices/message: {e}") from e

        conteudo = message.get("content")
        if isinstance(conteudo, list):
            # Alguns SDKs devolvem blocos [{type,text},...]
            partes = []
            for bloco in conteudo:
                if isinstance(bloco, dict):
                    partes.append(bloco.get("text") or bloco.get("content") or "")
                else:
                    partes.append(str(bloco))
            conteudo = "".join(partes)

        if not conteudo or not str(conteudo).strip():
            raise ValueError(
                "A API devolveu content vazio. Tente novamente ou use outro modelo."
            )
        return str(conteudo)

    @staticmethod
    def _parsear_json_resposta(conteudo: str) -> Dict[str, Any]:
        """Parseia JSON, tolerando cercas markdown."""
        texto = conteudo.strip()
        if texto.startswith("```"):
            texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\s*```$", "", texto)
        dados = json.loads(texto)
        if not isinstance(dados, dict):
            raise ValueError("JSON da API não é um objeto")
        return dados

    @staticmethod
    def _formatar_erro_api(response: requests.Response) -> str:
        """Extrai mensagem útil do corpo de erro da API xAI."""
        try:
            data = response.json()
            if isinstance(data, dict):
                return str(data.get("error") or data.get("message") or data)
        except Exception:
            pass
        return (response.text or response.reason or "sem detalhes")[:500]

    @staticmethod
    def _normalizar_resposta_llm(cartao_dict: Dict[str, Any]) -> None:
        """Garante estrutura mínima e recupera chaves alternativas da LLM."""
        avisos = cartao_dict.setdefault("avisos", [])
        if not isinstance(avisos, list):
            avisos = []
            cartao_dict["avisos"] = avisos

        # Aliases comuns
        if cartao_dict.get("peticao_inicial") is None:
            for alt in ("peticaoInicial", "inicial", "peticao"):
                if isinstance(cartao_dict.get(alt), dict):
                    cartao_dict["peticao_inicial"] = cartao_dict[alt]
                    break

        if cartao_dict.get("questoes") is None:
            for alt in ("questoes_a_decidir", "questions", "pontos_controvertidos"):
                if isinstance(cartao_dict.get(alt), list):
                    cartao_dict["questoes"] = cartao_dict[alt]
                    break

        if cartao_dict.get("peticao_inicial") is None:
            cartao_dict["peticao_inicial"] = {"causa_pedir": None, "pedidos": []}
            avisos.append({
                "tipo": "dado_ausente",
                "descricao": "peticao_inicial veio null da API; estrutura vazia foi assumida",
                "pedido_id": None,
                "questao_id": None,
            })
        elif isinstance(cartao_dict.get("peticao_inicial"), dict):
            pet = cartao_dict["peticao_inicial"]
            if pet.get("pedidos") is None and isinstance(pet.get("pedido"), list):
                pet["pedidos"] = pet["pedido"]
            if pet.get("pedidos") is None:
                pet["pedidos"] = []
            if pet.get("causa_pedir") is None and pet.get("causaDePedir"):
                pet["causa_pedir"] = pet["causaDePedir"]

        # Pedidos no nível raiz (modelo às vezes “escapa” a estrutura)
        pedidos_raiz = cartao_dict.get("pedidos")
        pet = cartao_dict.get("peticao_inicial")
        if isinstance(pedidos_raiz, list) and pedidos_raiz:
            if isinstance(pet, dict) and not (pet.get("pedidos") or []):
                pet["pedidos"] = pedidos_raiz
                avisos.append({
                    "tipo": "outro",
                    "descricao": "Pedidos recuperados do nível raiz da resposta da API",
                    "pedido_id": None,
                    "questao_id": None,
                })

        if cartao_dict.get("replica") is None:
            cartao_dict["replica"] = {
                "existe": False,
                "pontos_principais": [],
                "fontes": [],
            }

        for campo in (
            "partes",
            "contestacoes",
            "questoes",
            "mapa_pedido_defesa_questao",
        ):
            if cartao_dict.get(campo) is None:
                cartao_dict[campo] = []

        # Pontos controvertidos sem wrapper "questoes"
        if not cartao_dict.get("questoes") and isinstance(cartao_dict.get("pontos"), list):
            cartao_dict["questoes"] = cartao_dict["pontos"]

    @staticmethod
    def _chave_texto(valor: Optional[str]) -> str:
        if not valor:
            return ""
        return re.sub(r"\s+", " ", str(valor).casefold()).strip()

    @classmethod
    def _fundir_cartoes(
        cls,
        parciais: List[Dict[str, Any]],
        ids_enviados: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Reúne os cartões dos lotes sem descartar pedidos, teses ou questões.

        O ID citado num lote e extraído em outro deixa de gerar aviso de teor ausente.
        """
        from pje_ids import extrair_ids_pje_do_texto

        ids_ok = {item.lower() for item in (ids_enviados or set())}
        fundido: Dict[str, Any] = {
            "numero_processo": None,
            "partes": [],
            "peticao_inicial": {"causa_pedir": None, "pedidos": []},
            "contestacoes": [],
            "replica": {"existe": False, "pontos_principais": [], "fontes": []},
            "questoes": [],
            "mapa_pedido_defesa_questao": [],
            "avisos": [],
        }
        partes_vistas = set()
        n_pedido = 0
        n_questao = 0

        for parcial in parciais:
            if not isinstance(parcial, dict):
                continue
            if not fundido["numero_processo"] and parcial.get("numero_processo"):
                fundido["numero_processo"] = parcial["numero_processo"]

            for parte in parcial.get("partes") or []:
                if not isinstance(parte, dict) or not parte.get("nome"):
                    continue
                chave = (parte.get("tipo"), cls._chave_texto(parte.get("nome")))
                if chave in partes_vistas:
                    continue
                partes_vistas.add(chave)
                fundido["partes"].append(parte)

            pet = parcial.get("peticao_inicial") or {}
            if isinstance(pet, dict):
                causa = pet.get("causa_pedir")
                atual = fundido["peticao_inicial"]["causa_pedir"]
                if causa and (not atual or len(str(causa)) > len(str(atual))):
                    fundido["peticao_inicial"]["causa_pedir"] = causa

            mapa_pedido: Dict[str, str] = {}
            for pedido in (pet.get("pedidos") if isinstance(pet, dict) else None) or []:
                if not isinstance(pedido, dict):
                    continue
                descricao = cls._chave_texto(pedido.get("descricao"))
                existente = None
                if descricao:
                    existente = next(
                        (
                            item
                            for item in fundido["peticao_inicial"]["pedidos"]
                            if cls._chave_texto(item.get("descricao")) == descricao
                        ),
                        None,
                    )
                if existente:
                    if pedido.get("id"):
                        mapa_pedido[str(pedido["id"])] = existente["id"]
                    cls._estender_fontes(existente, pedido.get("fontes") or [])
                    continue
                n_pedido += 1
                novo_id = f"P{n_pedido}"
                if pedido.get("id"):
                    mapa_pedido[str(pedido["id"])] = novo_id
                copia = dict(pedido)
                copia["id"] = novo_id
                fundido["peticao_inicial"]["pedidos"].append(copia)

            for contestacao in parcial.get("contestacoes") or []:
                if not isinstance(contestacao, dict):
                    continue
                copia = dict(contestacao)
                antigo = str(copia.get("pedido_id") or "")
                copia["pedido_id"] = mapa_pedido.get(antigo, antigo)
                cls._anexar_contestacao(fundido["contestacoes"], copia)

            replica = parcial.get("replica") or {}
            if isinstance(replica, dict) and replica.get("existe"):
                fundido["replica"]["existe"] = True
                for ponto in replica.get("pontos_principais") or []:
                    if ponto and ponto not in fundido["replica"]["pontos_principais"]:
                        fundido["replica"]["pontos_principais"].append(ponto)
                cls._estender_fontes(fundido["replica"], replica.get("fontes") or [])

            mapa_questao: Dict[str, str] = {}
            for questao in parcial.get("questoes") or []:
                if not isinstance(questao, dict):
                    continue
                titulo = cls._chave_texto(questao.get("titulo"))
                existente = None
                if titulo:
                    existente = next(
                        (
                            item
                            for item in fundido["questoes"]
                            if cls._chave_texto(item.get("titulo")) == titulo
                        ),
                        None,
                    )
                if existente:
                    if questao.get("id"):
                        mapa_questao[str(questao["id"])] = existente["id"]
                    for pid in questao.get("pedido_ids") or []:
                        remap = mapa_pedido.get(str(pid), str(pid))
                        if remap and remap not in existente.setdefault("pedido_ids", []):
                            existente["pedido_ids"].append(remap)
                    cls._estender_fontes(existente, questao.get("fontes") or [])
                    continue
                n_questao += 1
                novo_id = f"Q{n_questao}"
                if questao.get("id"):
                    mapa_questao[str(questao["id"])] = novo_id
                copia = dict(questao)
                copia["id"] = novo_id
                copia["pedido_ids"] = [
                    mapa_pedido.get(str(pid), str(pid))
                    for pid in (questao.get("pedido_ids") or [])
                ]
                fundido["questoes"].append(copia)

            for mapa in parcial.get("mapa_pedido_defesa_questao") or []:
                if not isinstance(mapa, dict):
                    continue
                copia = dict(mapa)
                antigo = str(copia.get("pedido_id") or "")
                copia["pedido_id"] = mapa_pedido.get(antigo, antigo)
                copia["questao_ids"] = [
                    mapa_questao.get(str(qid), str(qid))
                    for qid in (copia.get("questao_ids") or [])
                ]
                cls._anexar_mapa(fundido["mapa_pedido_defesa_questao"], copia)

            for aviso in parcial.get("avisos") or []:
                if not isinstance(aviso, dict):
                    continue
                if cls._aviso_teor_coberto(aviso, ids_ok, extrair_ids_pje_do_texto):
                    continue
                if cls._aviso_ausencia_so_do_lote(aviso):
                    continue
                if aviso.get("pedido_id"):
                    aviso = dict(aviso)
                    aviso["pedido_id"] = mapa_pedido.get(
                        str(aviso["pedido_id"]), aviso["pedido_id"]
                    )
                if aviso.get("questao_id"):
                    aviso = dict(aviso)
                    aviso["questao_id"] = mapa_questao.get(
                        str(aviso["questao_id"]), aviso["questao_id"]
                    )
                fundido["avisos"].append(aviso)

        fundido["avisos"].append({
            "tipo": "outro",
            "descricao": (
                f"Autos fracionados em {len(parciais)} lote(s) de peças completas. "
                "Nenhuma peça foi omitida; o ID de cada uma está na última página."
            ),
            "pedido_id": None,
            "questao_id": None,
        })
        return fundido

    @staticmethod
    def _estender_fontes(destino: Dict[str, Any], fontes: List[Any]) -> None:
        lista = destino.setdefault("fontes", [])
        for fonte in fontes:
            if isinstance(fonte, dict) and fonte not in lista:
                lista.append(fonte)

    @staticmethod
    def _anexar_contestacao(lista: List[dict], nova: dict) -> None:
        pedido_id = nova.get("pedido_id")
        for existente in lista:
            if pedido_id and existente.get("pedido_id") == pedido_id:
                for tese in nova.get("teses") or []:
                    if tese and tese not in existente.setdefault("teses", []):
                        existente["teses"].append(tese)
                ExtratorCartao._estender_fontes(existente, nova.get("fontes") or [])
                if nova.get("impugnacao_especifica"):
                    existente["impugnacao_especifica"] = True
                return
        lista.append(nova)

    @staticmethod
    def _anexar_mapa(lista: List[dict], novo: dict) -> None:
        pedido_id = novo.get("pedido_id")
        for existente in lista:
            if pedido_id and existente.get("pedido_id") == pedido_id:
                for qid in novo.get("questao_ids") or []:
                    if qid and qid not in existente.setdefault("questao_ids", []):
                        existente["questao_ids"].append(qid)
                if novo.get("tem_contestacao"):
                    existente["tem_contestacao"] = True
                return
        lista.append(novo)

    @staticmethod
    def _aviso_teor_coberto(aviso: dict, ids_enviados: set, extrair_ids) -> bool:
        """Descarta aviso de teor ausente quando a peça foi enviada em algum lote."""
        if aviso.get("tipo") != "dado_ausente" or not ids_enviados:
            return False
        descricao = aviso.get("descricao") or ""
        if not re.search(
            r"n[aã]o\s+consta|n[aã]o\s+est[aá]\s+no\s+trecho|n[aã]o\s+teve\s+o\s+teor|"
            r"sem\s+teor|teor\s+integral|n[aã]o\s+foi\s+reproduz",
            descricao,
            flags=re.IGNORECASE,
        ):
            return False
        ids = extrair_ids(descricao)
        return bool(ids) and all(item.lower() in ids_enviados for item in ids)

    @staticmethod
    def _aviso_ausencia_so_do_lote(aviso: dict) -> bool:
        """
        Descarta aviso que só relata ausência dentro de um lote.

        Petição inicial, contestação e demais peças seguem em outros lotes.
        Esse recado, depois da fusão, parece dizer que a peça não existe.
        """
        descricao = aviso.get("descricao") or ""
        if not re.search(
            r"\b(?:n|d)?este lote\b|\boutros lotes\b|\btrecho analisado\b",
            descricao,
            flags=re.IGNORECASE,
        ):
            return False
        if re.search(
            r"n[uú]mero do processo.{0,60}n[aã]o\s+const|"
            r"n[aã]o\s+const.{0,50}n[uú]mero do processo|"
            r"nome do reclamante n[aã]o\s+const|"
            r"valor da causa.{0,60}n[aã]o\s+const",
            descricao,
            flags=re.IGNORECASE,
        ):
            return True
        pecas = (
            r"peti[cç][aã]o inicial|contesta[cç][aã]o|\br[eé]plica\b|"
            r"\bparecer\b|\bteor\b|corpo d[eoa]|\bpe[cç]as?\b|"
            r"(?<!valor do )\bacordo\b(?! de boca)"
        )
        ausencia = (
            r"n[aã]o\s+integra|n[aã]o\s+est[aáã]o?\b|n[aã]o\s+const|"
            r"n[aã]o\s+h[aá]\b|n[aã]o\s+exibe|n[aã]o\s+aparece|"
            r"n[aã]o\s+(?:foi\s+)?reproduz|sem o inteiro teor|"
            r"teor integral|podem estar em outros"
        )
        if re.search(
            r"(?:" + pecas + r").{0,90}(?:" + ausencia + r")",
            descricao,
            flags=re.IGNORECASE,
        ):
            return True
        if re.search(
            r"(?:" + ausencia + r").{0,45}(?:" + pecas + r")",
            descricao,
            flags=re.IGNORECASE,
        ):
            return True
        return bool(re.search(
            r"n[aã]o\s+h[aá],?\s+(?:n|d)?este lote,?\s+decis[aã]o|"
            r"decis[õo]es.{0,40}sem o inteiro teor",
            descricao,
            flags=re.IGNORECASE,
        ))

    @staticmethod
    def _contar_pedidos(cartao: CartaoDoCaso) -> int:
        pet = cartao.peticao_inicial or {}
        if isinstance(pet, dict):
            return len(pet.get("pedidos") or [])
        return len(getattr(pet, "pedidos", []) or [])

    def _garantir_conteudo_minimo(self, cartao: CartaoDoCaso) -> None:
        """Evita cartão 'válido' porém vazio passar silenciosamente na UI."""
        n_pedidos = self._contar_pedidos(cartao)
        n_questoes = len(cartao.questoes or [])
        if n_pedidos == 0 and n_questoes == 0:
            raise RuntimeError(
                "A extração não encontrou nenhum pedido nem questão. "
                "Isso costuma ocorrer quando (1) o arquivo é só uma decisão/minuta "
                "sem a petição/impugnação completa, (2) os autos são muito grandes "
                "e o modelo devolveu estrutura vazia, ou (3) a resposta da API veio "
                "incompleta. Use o MD completo dos autos (não só a decisão) e tente de novo."
            )

    def _enriquecer_ids_pje(self, cartao_dict: Dict[str, Any], texto_md: str) -> None:
        """Preenche id_pje ausentes nas fontes com o ID da peça que contém o trecho."""
        from pje_ids import dividir_em_pecas, enriquecer_fontes_dict

        pecas = dividir_em_pecas(texto_md)

        peticao = cartao_dict.get("peticao_inicial") or {}
        for pedido in peticao.get("pedidos") or []:
            if isinstance(pedido, dict):
                enriquecer_fontes_dict(pedido.get("fontes") or [], texto_md, pecas)

        for contestacao in cartao_dict.get("contestacoes") or []:
            if isinstance(contestacao, dict):
                enriquecer_fontes_dict(contestacao.get("fontes") or [], texto_md, pecas)

        replica = cartao_dict.get("replica") or {}
        if isinstance(replica, dict):
            enriquecer_fontes_dict(replica.get("fontes") or [], texto_md, pecas)

        for questao in cartao_dict.get("questoes") or []:
            if isinstance(questao, dict):
                enriquecer_fontes_dict(questao.get("fontes") or [], texto_md, pecas)
    
    def _construir_prompt_extracao(self) -> str:
        """Constrói prompt de extração com método jurídico."""
        return """Você é um assistente especializado em extração de estrutura jurídica de autos trabalhistas.

## TAREFA
Extraia do texto dos autos a seguinte estrutura JSON:

1. **numero_processo**: número do processo (ex: "0001234-56.2023.5.10.0001")
2. **partes**: lista de partes
   - tipo: "reclamante" ou "reclamada"
   - nome: nome como consta nos autos
   - Em cumprimento/execução: exequente → reclamante; executado(a) → reclamada
3. **peticao_inicial**:
   - causa_pedir: resumo da causa de pedir / pretensão executória
   - pedidos: lista de pedidos/pretensões com:
     - id: "P1", "P2", etc.
     - descricao: descrição do pedido
     - periodo: período se aplicável
     - valor: valor se especificado
     - reflexos: true/false (se há pedido de reflexos)
     - fontes: [{trecho, id_pje, folhas}]
4. **contestacoes**: lista de contestações/impugnações por pedido
   - pedido_id: id do pedido contestado
   - impugnacao_especifica: true/false (art. 341 CPC - deve ter grau de detalhe equivalente ao da inicial; negativa genérica NÃO basta)
   - teses: lista de teses de defesa
   - fontes: [{trecho, id_pje, folhas}]
5. **replica**:
   - existe: true/false
   - pontos_principais: lista de pontos principais
   - fontes: [{trecho, id_pje, folhas}]
6. **questoes**: lista de questões a decidir
   - id: "Q1", "Q2", etc.
   - titulo: título da questão
   - tipo: "fato" | "direito" | "mista"
   - natureza_fatica: "constitutivo" | "impeditivo" | "modificativo" | "extintivo" | "irrelevante" (se aplicável)
   - momento: "pressuposto_processual" | "condicao_da_acao" | "incidental" | "preliminar" | "merito"
   - de_oficio: true/false (competência, capacidade, prescrição, validade de atos, pressupostos, condições da ação, inépcia)
   - arguida_na_defesa: true/false
   - acarreta_extincao: true/false (se acarreta extinção de algum pedido)
   - mencionar_na_minuta: true/false (REGRA: questões de ofício só devem constar se foram arguidas na defesa OU se acarretam extinção)
   - pedido_ids: lista de IDs de pedidos relacionados
   - fontes: [{trecho, id_pje, folhas}]
7. **mapa_pedido_defesa_questao**: lista de mapeamentos
   - pedido_id: id do pedido
   - tem_contestacao: true/false
   - questao_ids: lista de IDs de questões relacionadas
8. **avisos**: lista de avisos
   - tipo: "falta_impugnacao_especifica" | "possivel_irrelevancia" | "falta_id_pje" | "falta_folhas" | "dado_ausente" | "outro"
   - descricao: descrição do aviso
   - pedido_id: id relacionado (se aplicável)
   - questao_id: id relacionado (se aplicável)

## MÉTODO JURÍDICO
- **Questão de fato**: eventos a provar (jornada, iniciativa da rescisão, pagamento, dano)
- **Questão de direito**: norma, interpretação, consequências (adicional aplicável, falta grave 482/483, quitação, culpa)
- **Fatos**: só importam se constitutivos, impeditivos, modificativos ou extintivos de direito
- **Irrelevância**: ex.: ciência da gravidez não é relevante para estabilidade gestante (Súmula 244 TST)
- **Impugnação específica** (art. 341 CPC): deve ter grau de detalhe equivalente ao da inicial; negativa genérica de jornada/intervalo NÃO basta
- **Prova**: nesta fase, apenas localize onde está a prova no MD (se distinguível), sem valorar depoimentos
- **Cumprimento / liquidação / impugnação aos cálculos**: NÃO devolva estruturas vazias. Trate cada pretensão do exequente e cada ponto da impugnação como pedido (P1, P2...) e gere questões correspondentes (preliminares e mérito)

## REGRAS IMPORTANTES
1. O ID do PJe é uma string alfanumérica de 7 caracteres (ex.: c7dbfbc, 4ac9a65, bfaa1df). Ele aparece somente na última página de cada peça, como os 7 caracteres finais da linha "Documento assinado eletronicamente por ..., em DD/MM/AAAA, às HH:MM:SS - XXXXXXX". Todo o texto desde a peça anterior até essa linha pertence a esse ID, mesmo que as páginas do meio não repitam o ID. Também pode aparecer como "ID XXXXXXX", "ID. XXXXXXX" ou "(ID XXXXXXX)". Nunca invente ID; se não achar, use null (não escreva "não informado").
2. Preserve folhas (ex: "fls. 12", "fls. 93")
3. NÃO invente fatos, valores ou IDs. Campos escalares ausentes → null + aviso. Objetos/listas estruturais NUNCA devem ser null: use objeto/lista vazios SOMENTE se, após varredura, realmente não houver dado. É PROIBIDO devolver peticao_inicial sem pedidos e questoes vazias quando o texto traz pretensões, pedidos, impugnações ou pontos controvertidos.
4. Temperature baixa (0.1): seja preciso e conservador
5. Questões de ofício NÃO mencionadas na defesa E que NÃO acarretam extinção: mencionar_na_minuta = false
6. Retorne APENAS o objeto JSON, sem texto adicional
7. OBRIGATÓRIO: para CADA pedido/pretensão extraída, crie ao menos uma questão de mérito em "questoes" (tipo fato/direito/mista, momento "merito"), mesmo quando a defesa for genérica
8. Preencha "contestacoes" por pedido quando houver contestação/impugnação; se a defesa for só negativa genérica, impugnacao_especifica=false e registre aviso "falta_impugnacao_especifica"
9. Se o documento for uma decisão/minuta, extraia do relatório/fundamentação as pretensões e os pontos decididos como pedidos e questões
10. Não registre aviso, de nenhum tipo, só porque o sumário ou outra peça cita um ID cujo corpo não está neste lote, nem porque a petição inicial, a contestação, a réplica, uma decisão, um parecer ou um acordo não aparecem neste lote. Outros lotes cobrem o restante. Se a peça está no texto recebido, extraia o teor até a linha de assinatura da última página.

## FORMATO DE SAÍDA
Retorne um objeto JSON válido seguindo exatamente a estrutura acima."""
    
    def selecionar_modelo_automatico(self) -> str:
        """
        Seleciona o melhor modelo disponível automaticamente.
        Tenta usar modelos mais recentes primeiro.
        
        Returns:
            Nome do modelo selecionado
        """
        modelos = self.listar_modelos()
        
        ordem_preferencia = list(FALLBACK_MODELS) + [
            "grok-4",
            "grok-3",
        ]
        
        for modelo_pref in ordem_preferencia:
            for modelo_disponivel in modelos:
                if modelo_pref in modelo_disponivel:
                    self.model = modelo_disponivel
                    return modelo_disponivel
        
        if modelos:
            self.model = modelos[0]
            return modelos[0]
        
        return self.DEFAULT_MODEL
