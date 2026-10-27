"""
Kernel Sarah - Prompt de sistema editável da assessora de conhecimento.
"""

import json
from pathlib import Path
from typing import Optional


class KernelSarah:
    """Gerencia o prompt de sistema (kernel) da Sarah."""
    
    PROMPT_DEFAULT = """Você é Sarah, assessora jurídica chefe especializada em Direito do Trabalho.

# CONSTITUIÇÃO DA REDATORA

## Persona
- Rigor técnico absoluto
- Imparcialidade
- Adstrição à lide
- Fundamentação dialética

## Princípio Zero Alucinação
FATO, DATA, VALOR, ID DO PJE, DEPOIMENTO QUE NÃO ESTEJA NO CARTÃO + DOSSIÊ + PRECEDENTES RECUPERADOS NÃO EXISTE.

Citação obrigatória: `(ID xxxxxxx, fls. yyy)` SÓ se o ID existir no dossiê/autos.
ID do PJe é a string alfanumérica de 7 caracteres no fim da linha de assinatura eletrônica. Esse ID aparece só na última página da peça; as páginas anteriores pertencem ao mesmo ID.
Se o ID não constar do material fornecido, cite apenas as folhas — NUNCA escreva "ID não informado".

NUNCA use metalinguagem na minuta (não diga "vou analisar", "conforme consta", "não há dossiê", etc.).
NUNCA reproduza instruções internas do prompt na minuta.

## Fluxo de Validação Humana

1. **Estrutura de Tópicos**: Pressupostos e condições da ação SÓ se arguidos OU se extinguem; depois mérito na ordem trabalhista usual.

2. **Minuta Prévia por Tópico**: Para cada tópico de mérito, apresente tese, antítese, abordagem e conclusão preliminar.

3. **Minuta Definitiva — papéis distintos (NÃO repita Relatório+Fundamentação+Dispositivo em cada tópico)**:

   a) **Relatório** (somente quando o tópico for do tipo relatório):
      - Bloco narrativo único da sentença
      - Identificação das partes, pedidos, defesa e menção aos tipos de prova
      - NÃO inclua fundamentação nem dispositivo neste tópico

   b) **Fundamentação** (somente quando o tópico for questão de mérito/preliminar):
      - Dialética daquela questão: enunciado, tese, antítese, prova com transcrição literal, subsunção, refutação, comando decisório em voz passiva pronominal
      - NÃO reinicie Relatório nem Dispositivo completo da sentença
      - Desenvolva com densidade de decisão judicial (não resuma em um parágrafo genérico)

   c) **Dispositivo** (somente quando o tópico for dispositivo):
      - Espelho final dos comandos decisórios, custas, recolhimentos e honorários
      - NÃO repita relatório nem fundamentação

## Regras de Ônus Probatório

- Art. 818 CLT: Ônus distribuído conforme a natureza do fato
- Súmula 338 TST: Jornada extraordinária
- Confissão real: Depoimento da parte contra si
- Laudo pericial norteia insalubridade/periculosidade salvo prova robusta em contrário
- Dedução de valores já pagos

## Busca de Precedentes

Buscar precedentes DEPOIS que a questão está definida. Não invente ementa.
Se a Collection não devolver trecho, NÃO cite processo fantasma.

## Verificação Final

Todos os IDs e números de processo citados na minuta DEVEM existir no dossiê/cartão/hits reais da Collection.
Se não existir, RECUSAR trecho e avisar.

---

## Diretrizes de Redação

- Use linguagem técnica forense própria de sentença trabalhista
- Evite preciosismos e arcaísmos desnecessários
- Fundamente TODAS as decisões com análise específica das alegações e da prova
- Cite a base legal aplicável
- Transcreva literalmente trechos de prova relevantes
- Não repita argumentos já refutados
- Mantenha coerência lógica entre fundamentação e dispositivo
- Este kernel é exclusivo da sentença de conhecimento; o assistente de liquidação/execução fica em slot separado
"""
    
    MARCADORES_PAFUNCIO_FORTES = (
        "assistente jurídico para sentença de liquidação",
        "assistente juridico para sentenca de liquidacao",
        "módulo perito contador",
        "modulo perito contador",
        "protocolo de análise exaustiva de teses",
        "protocolo de analise exaustiva de teses",
    )
    
    def __init__(self, diretorio_config: Optional[Path] = None):
        if diretorio_config is None:
            diretorio_config = Path.home() / ".indexador_sentencas" / "config"
        
        self.diretorio_config = Path(diretorio_config)
        self.diretorio_config.mkdir(parents=True, exist_ok=True)
        self.arquivo_config = self.diretorio_config / "kernel_sarah.json"
        
        self._migrar_pafuncio_se_misturado()
        
        if not self.arquivo_config.exists():
            self.salvar_prompt(self.PROMPT_DEFAULT)
    
    @classmethod
    def parece_pafuncio(cls, prompt: str) -> bool:
        """Detecta se o texto é o kernel Pafúncio (liquidação), não a Sarah."""
        texto = (prompt or "").casefold()
        if not texto.strip():
            return False
        # Cabeçalho típico do Pafúncio
        inicio = texto.lstrip()[:80]
        if inicio.startswith("# pafúncio") or inicio.startswith("# pafuncio"):
            return True
        if any(m in texto for m in cls.MARCADORES_PAFUNCIO_FORTES):
            return True
        # Combo operacional de liquidação
        if "paet" in texto and "pvom" in texto and ("liquidação" in texto or "liquidacao" in texto):
            return True
        return False
    
    def _migrar_pafuncio_se_misturado(self):
        """
        Se kernel_sarah.json contém o Pafúncio, move para kernel_pafuncio.json
        e restaura o default da Sarah.
        """
        if not self.arquivo_config.exists():
            return
        try:
            with open(self.arquivo_config, "r", encoding="utf-8") as f:
                config = json.load(f)
            prompt = config.get("prompt_sistema", "")
        except Exception:
            return
        
        if not self.parece_pafuncio(prompt):
            return
        
        arquivo_pafuncio = self.diretorio_config / "kernel_pafuncio.json"
        if not arquivo_pafuncio.exists():
            with open(arquivo_pafuncio, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "prompt_sistema": prompt,
                        "versao": "1.0",
                        "origem": "migrado_de_kernel_sarah",
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        
        self.salvar_prompt(self.PROMPT_DEFAULT)
    
    def obter_prompt(self) -> str:
        """Obtém o prompt de sistema atual."""
        if not self.arquivo_config.exists():
            return self.PROMPT_DEFAULT
        
        with open(self.arquivo_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        return config.get("prompt_sistema", self.PROMPT_DEFAULT)
    
    def salvar_prompt(self, prompt: str):
        """Salva o prompt de sistema."""
        config = {
            "prompt_sistema": prompt,
            "versao": "1.0"
        }
        
        with open(self.arquivo_config, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def restaurar_default(self):
        """Restaura o prompt padrão."""
        self.salvar_prompt(self.PROMPT_DEFAULT)
    
    def sugerir_melhorias(
        self,
        api_key: str,
        contexto_sessao: str,
        modelo: str = "grok-4.6",
        reasoning_effort: Optional[str] = None,
    ) -> str:
        """
        Sugere melhorias no prompt baseado em uma sessão de uso.

        Args:
            api_key: Chave da API xAI
            contexto_sessao: Contexto da sessão (problemas encontrados, etc.)
            modelo: Modelo a usar
            reasoning_effort: Nível de reasoning quando o modelo permitir

        Returns:
            Sugestão de novo prompt
        """
        import requests
        from log_execucao import API, etapa
        from xai_reasoning import aplicar_reasoning_effort
        
        prompt_atual = self.obter_prompt()
        
        prompt_melhoria = f"""Analise o prompt de sistema atual da Sarah (assessora jurídica) 
e sugira melhorias com base no contexto de uso fornecido.

PROMPT ATUAL:
{prompt_atual}

---

CONTEXTO DA SESSÃO:
{contexto_sessao}

---

Sugira um prompt de sistema aprimorado que:
1. Mantenha a essência e estrutura do prompt original
2. Corrija problemas identificados no contexto
3. Adicione diretrizes que evitem os erros observados
4. Mantenha o tom e o nível de detalhe

Retorne APENAS o novo prompt, sem explicações adicionais."""
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": modelo,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um especialista em engenharia de prompts para assistentes jurídicos."
                },
                {
                    "role": "user",
                    "content": prompt_melhoria
                }
            ],
            "temperature": 0.3
        }
        aplicar_reasoning_effort(payload, modelo, reasoning_effort)
        
        try:
            with etapa(
                "kernel.sugestao_prompt.chat_completions",
                categoria=API,
                modelo=modelo,
                reasoning=payload.get("reasoning_effort"),
                chars_prompt=len(prompt_melhoria),
                timeout_s=120,
            ) as reg:
                response = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                reg.registrar_http(response)
                response.raise_for_status()
                
                resultado = response.json()
                reg.registrar_uso(resultado)
            sugestao = resultado["choices"][0]["message"]["content"]
            return sugestao
            
        except Exception as e:
            return f"Erro ao gerar sugestão: {str(e)}"
