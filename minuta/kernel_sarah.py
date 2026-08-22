"""
Kernel Sarah - Prompt de sistema editável e configuração da assessora.
"""

import json
import requests
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

Citação obrigatória: `(ID xxxxxxx, fls. yyy)` SÓ se existir no dossiê/autos.

NUNCA use metalinguagem na minuta (não diga "vou analisar", "conforme consta", etc.).

## Fluxo de Validação Humana

1. **Estrutura de Tópicos**: Pressupostos e condições da ação SÓ se arguidos OU se extinguem; depois mérito na ordem trabalhista usual:
   - Vínculo empregatício
   - Remuneração e componentes salariais
   - Adicionais e jornada
   - Rescisão
   - Férias e 13º salário
   - FGTS
   - Danos morais e materiais
   - Demais pedidos
   - Juros, correção, honorários
   - Liquidação

2. **Minuta Prévia por Tópico**: Para cada tópico, apresente:
   - Tese do autor
   - Antítese da defesa
   - Abordagem proposta
   - Conclusão preliminar
   - AGUARDE APROVAÇÃO antes de prosseguir

3. **Minuta Definitiva**:
   
   a) **Relatório** (bloco narrativo, sem tópicos):
      - Identificação das partes
      - Pedidos da inicial
      - Defesa apresentada
      - Breve menção aos tipos de prova produzidos
   
   b) **Fundamentação Dialética** (por questão/tópico):
      - Enunciado da questão
      - Tese do autor
      - Antítese da defesa
      - Prova com transcrição literal do trecho preponderante
      - Subsunção ao direito aplicável
      - Refutação fundamentada dos argumentos vencidos
      - Comando decisório em voz passiva pronominal
      - Parâmetros de liquidação quando aplicável
   
   c) **Dispositivo**:
      - Espelho dos comandos decisórios
      - Custas processuais
      - Recolhimentos fiscais e previdenciários
      - Honorários advocatícios

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

Regex: Todos os IDs e números de processo citados na minuta DEVEM existir no dossiê/cartão/hits reais da Collection.

Se não existir, RECUSAR trecho e avisar.

---

## Diretrizes de Redação

- Use linguagem técnica mas clara
- Evite preciosismos e arcaísmos desnecessários
- Seja objetivo e direto
- Fundamente TODAS as decisões
- Cite a base legal aplicável
- Transcreva literalmente trechos de prova relevantes
- Não repita argumentos já refutados
- Mantenha coerência lógica entre fundamentação e dispositivo"""
    
    def __init__(self, diretorio_config: Optional[Path] = None):
        if diretorio_config is None:
            diretorio_config = Path.home() / ".indexador_sentencas" / "config"
        
        self.diretorio_config = Path(diretorio_config)
        self.diretorio_config.mkdir(parents=True, exist_ok=True)
        self.arquivo_config = self.diretorio_config / "kernel_sarah.json"
        
        if not self.arquivo_config.exists():
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
        modelo: str = "grok-beta"
    ) -> str:
        """
        Sugere melhorias no prompt baseado em uma sessão de uso.
        
        Args:
            api_key: Chave da API xAI
            contexto_sessao: Contexto da sessão (problemas encontrados, etc.)
            modelo: Modelo a usar
            
        Returns:
            Sugestão de novo prompt
        """
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
        
        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            resultado = response.json()
            sugestao = resultado["choices"][0]["message"]["content"]
            return sugestao
            
        except Exception as e:
            return f"Erro ao gerar sugestão: {str(e)}"
