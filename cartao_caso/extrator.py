"""
Extrator de Cartão do Caso usando API xAI Grok.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from .schema import CartaoDoCaso


class ExtratorCartao:
    """Cliente HTTP para extrair estrutura jurídica de autos usando Grok."""
    
    API_BASE = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-beta"
    TEMPERATURE = 0.1
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Inicializa o extrator.
        
        Args:
            api_key: Chave de API do xAI
            model: Modelo Grok a usar (padrão: grok-beta)
        """
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
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
        try:
            response = self.session.get(f"{self.API_BASE}/models", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            print(f"Aviso: não foi possível listar modelos ({e}). Usando padrão: {self.DEFAULT_MODEL}")
            return [self.DEFAULT_MODEL]
    
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
        
        if progresso_callback:
            progresso_callback(f"Cartão extraído: {len(cartao.questoes)} questões, {len(cartao.avisos)} avisos")
        
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
        
        mensagens = [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": f"Extraia a estrutura jurídica destes autos:\n\n{conteudo_md}"
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": mensagens,
            "temperature": self.TEMPERATURE,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = self.session.post(
                f"{self.API_BASE}/chat/completions",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            conteudo = data["choices"][0]["message"]["content"]
            
            return json.loads(conteudo)
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erro ao chamar API xAI: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Erro ao processar resposta da API: {e}")
    
    def _construir_prompt_extracao(self) -> str:
        """Constrói prompt de extração com método jurídico."""
        return """Você é um assistente especializado em extração de estrutura jurídica de autos trabalhistas.

## TAREFA
Extraia do texto dos autos a seguinte estrutura JSON:

1. **numero_processo**: número do processo (ex: "0001234-56.2023.5.10.0001")
2. **partes**: lista de partes
   - tipo: "reclamante" ou "reclamada"
   - nome: nome como consta nos autos
3. **peticao_inicial**:
   - causa_pedir: resumo da causa de pedir
   - pedidos: lista de pedidos com:
     - id: "P1", "P2", etc.
     - descricao: descrição do pedido
     - periodo: período se aplicável
     - valor: valor se especificado
     - reflexos: true/false (se há pedido de reflexos)
     - fontes: [{trecho, id_pje, folhas}]
4. **contestacoes**: lista de contestações por pedido
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

## REGRAS IMPORTANTES
1. Preserve IDs do PJe (ex: "ID 12345678") e folhas (ex: "fls. 12", "(ID 12345, fls. 34)")
2. NÃO invente dados: se não estiver no texto, deixe null e crie aviso
3. Temperature baixa (0.1): seja preciso e conservador
4. Questões de ofício NÃO mencionadas na defesa E que NÃO acarretam extinção: mencionar_na_minuta = false
5. Retorne APENAS o objeto JSON, sem texto adicional

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
        
        ordem_preferencia = [
            "grok-4.6",
            "grok-2-1212",
            "grok-beta",
            "grok-2-vision-1212"
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
