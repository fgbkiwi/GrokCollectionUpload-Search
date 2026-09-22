"""
Extrator de Cartão do Caso usando API xAI Grok.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from .schema import CartaoDoCaso
from xai_reasoning import aplicar_reasoning_effort
from xai_models import DEFAULT_MODEL as XAI_DEFAULT_MODEL
from xai_models import FALLBACK_MODELS, listar_modelos_xai


class ExtratorCartao:
    """Cliente HTTP para extrair estrutura jurídica de autos usando Grok."""
    
    API_BASE = "https://api.x.ai/v1"
    DEFAULT_MODEL = XAI_DEFAULT_MODEL
    TEMPERATURE = 0.1
    # Autos OCR completos passam facilmente de 1MB; a API tolera contexto longo,
    # mas respostas rasas/vazias são comuns se mandarmos tudo de uma vez.
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
        
        with open(caminho_md, 'r', encoding='utf-8') as f:
            conteudo_md = f.read()
        
        if progresso_callback:
            progresso_callback("Extraindo estrutura via Grok...")
        
        cartao_dict = self._extrair_estrutura(conteudo_md)
        cartao_dict["arquivo_origem"] = str(caminho_md)
        
        if progresso_callback:
            progresso_callback("Validando schema...")
        
        cartao = CartaoDoCaso(**cartao_dict)
        self._garantir_conteudo_minimo(cartao)
        
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
    
    def _extrair_estrutura(self, conteudo_md: str) -> Dict[str, Any]:
        """
        Extrai estrutura JSON do conteúdo MD usando Grok.
        
        Args:
            conteudo_md: Conteúdo do arquivo Markdown
            
        Returns:
            Dicionário com estrutura extraída
        """
        prompt = self._construir_prompt_extracao()
        texto_envio, aviso_reducao = self._preparar_texto_para_envio(conteudo_md)
        
        mensagens = [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": (
                    "Extraia a estrutura jurídica destes autos. "
                    "Preencha pedidos e questões sempre que houver pretensão, "
                    "impugnação ou ponto controvertido no texto.\n\n"
                    f"{texto_envio}"
                ),
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": mensagens,
            "temperature": self.TEMPERATURE,
            "response_format": {"type": "json_object"}
        }
        aplicar_reasoning_effort(payload, self.model, self.reasoning_effort)
        
        try:
            response = self.session.post(
                f"{self.API_BASE}/chat/completions",
                json=payload,
                timeout=self.TIMEOUT_API
            )
            if not response.ok:
                detalhe = self._formatar_erro_api(response)
                raise RuntimeError(
                    f"Erro ao chamar API xAI ({response.status_code}) "
                    f"com modelo '{self.model}': {detalhe}"
                )
            
            data = response.json()
            conteudo = self._extrair_texto_resposta(data)
            cartao_dict = self._parsear_json_resposta(conteudo)
            self._normalizar_resposta_llm(cartao_dict)
            if aviso_reducao:
                avisos = cartao_dict.setdefault("avisos", [])
                if isinstance(avisos, list):
                    avisos.append({
                        "tipo": "outro",
                        "descricao": aviso_reducao,
                        "pedido_id": None,
                        "questao_id": None,
                    })
            self._enriquecer_ids_pje(cartao_dict, conteudo_md)
            return cartao_dict
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro ao chamar API xAI: {e}")
        except (KeyError, json.JSONDecodeError, TypeError, ValueError) as e:
            raise RuntimeError(f"Erro ao processar resposta da API: {e}")

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

    def _preparar_texto_para_envio(self, texto: str) -> tuple[str, Optional[str]]:
        """
        Reduz autos muito grandes preservando capa e trechos com marcadores úteis.
        """
        if len(texto) <= self.MAX_CHARS_ENVIO:
            return texto, None

        cabeca = 70_000
        cauda = 40_000
        orcamento_meio = max(40_000, self.MAX_CHARS_ENVIO - cabeca - cauda - 2_000)

        partes = [
            texto[:cabeca],
            "\n\n[... trecho intermediário omitido para caber no contexto ...]\n\n",
        ]

        marcadores = [
            r"peti[cç][aã]o\s+inicial",
            r"\bpedidos?\b",
            r"contest[aá][cç][aã]o",
            r"impugna[cç][aã]o",
            r"r[eé]plica",
            r"cumprimento\s+de\s+senten[cç]a",
            r"liquida[cç][aã]o",
            r"conta\s+de\s+liquida[cç][aã]o",
            r"fundamenta[cç][aã]o",
            r"\bdispositivo\b",
            r"preliminar",
        ]
        janela = 8_000
        usados = 0
        for padrao in marcadores:
            if usados >= orcamento_meio:
                break
            for match in re.finditer(padrao, texto, flags=re.IGNORECASE):
                if usados >= orcamento_meio:
                    break
                ini = max(0, match.start() - 500)
                fim = min(len(texto), match.start() + janela)
                # Evita repetir a cabeça
                if fim <= cabeca:
                    continue
                trecho = texto[ini:fim]
                partes.append(
                    f"\n\n--- TRECHO RELEVANTE ({match.group(0)}) ---\n{trecho}\n"
                )
                usados += len(trecho)

        partes.append(
            "\n\n[... trecho intermediário omitido ...]\n\n" + texto[-cauda:]
        )
        aviso = (
            f"Autos reduzidos para envio à API "
            f"({len(texto)} → ~{sum(len(p) for p in partes)} chars). "
            "Se faltar pedido/questão, use trecho menor dos autos ou extraia de novo."
        )
        return "".join(partes), aviso

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
        """Preenche id_pje ausentes nas fontes com parser determinístico das assinaturas PJe."""
        from pje_ids import enriquecer_fontes_dict

        peticao = cartao_dict.get("peticao_inicial") or {}
        for pedido in peticao.get("pedidos") or []:
            if isinstance(pedido, dict):
                enriquecer_fontes_dict(pedido.get("fontes") or [], texto_md)

        for contestacao in cartao_dict.get("contestacoes") or []:
            if isinstance(contestacao, dict):
                enriquecer_fontes_dict(contestacao.get("fontes") or [], texto_md)

        replica = cartao_dict.get("replica") or {}
        if isinstance(replica, dict):
            enriquecer_fontes_dict(replica.get("fontes") or [], texto_md)

        for questao in cartao_dict.get("questoes") or []:
            if isinstance(questao, dict):
                enriquecer_fontes_dict(questao.get("fontes") or [], texto_md)
    
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
1. Preserve IDs do PJe: string alfanumérica de 7 caracteres (ex.: c7dbfbc, b9283dd), tipicamente no final da linha "Documento assinado eletronicamente por ..., em DD/MM/AAAA, às HH:MM:SS - XXXXXXX". Também pode aparecer como "ID XXXXXXX", "ID. XXXXXXX" ou "(ID XXXXXXX)". Nunca invente ID; se não achar, use null (não escreva "não informado").
2. Preserve folhas (ex: "fls. 12", "fls. 93")
3. NÃO invente fatos, valores ou IDs. Campos escalares ausentes → null + aviso. Objetos/listas estruturais NUNCA devem ser null: use objeto/lista vazios SOMENTE se, após varredura, realmente não houver dado. É PROIBIDO devolver peticao_inicial sem pedidos e questoes vazias quando o texto traz pretensões, pedidos, impugnações ou pontos controvertidos.
4. Temperature baixa (0.1): seja preciso e conservador
5. Questões de ofício NÃO mencionadas na defesa E que NÃO acarretam extinção: mencionar_na_minuta = false
6. Retorne APENAS o objeto JSON, sem texto adicional
7. OBRIGATÓRIO: para CADA pedido/pretensão extraída, crie ao menos uma questão de mérito em "questoes" (tipo fato/direito/mista, momento "merito"), mesmo quando a defesa for genérica
8. Preencha "contestacoes" por pedido quando houver contestação/impugnação; se a defesa for só negativa genérica, impugnacao_especifica=false e registre aviso "falta_impugnacao_especifica"
9. Se o documento for uma decisão/minuta, extraia do relatório/fundamentação as pretensões e os pontos decididos como pedidos e questões

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
