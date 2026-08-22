# Cartão do Caso - Extração Estruturada de Autos

**Módulo de extração estruturada de autos trabalhistas usando API Grok**

---

## 📋 Visão Geral

O **Cartão do Caso** é o segundo entregável da refatoração do sistema de indexação de sentenças trabalhistas. Este módulo extrai automaticamente a estrutura jurídica de autos já convertidos para Markdown, gerando um "cartão" JSON validável que o juiz pode revisar e confirmar antes de qualquer redação de minuta.

### O Que Este Módulo FAZ

✅ Lê arquivos Markdown de autos (já convertidos de PDF para MD externamente)  
✅ Extrai estrutura JSON com pedidos, defesas, questões e mapeamentos  
✅ Valida schema com Pydantic  
✅ Apresenta tabelas editáveis em UI Flet para o juiz confirmar  
✅ Persiste cartões localmente com cópia MD de auditoria  
✅ Preserva IDs do PJe e referências a folhas  

### O Que Este Módulo NÃO FAZ

❌ **NÃO** faz OCR ou lê PDFs  
❌ **NÃO** indexa em xAI Collections  
❌ **NÃO** faz busca de precedentes  
❌ **NÃO** redige minutas de sentenças  
❌ **NÃO** implementa examinadores de prova (documental/pericial/oral)  
❌ **NÃO** contém biblioteca de modelos temáticos (juros/FGTS)  
❌ **NÃO** altera o indexador de sentenças da PR #2  

---

## 🎯 Objetivo

O juiz já converte os autos de PDF para Markdown (fora deste aplicativo). Este módulo:

1. Lê esse MD
2. Extrai uma estrutura JSON validável (o "cartão")
3. Mostra tabelas para o juiz confirmar antes de qualquer redação de minuta

**Nada dos autos vai para xAI Collections.** A Collection existente de sentenças publicadas só será usada na fase 4 (minuta). Aqui a API do Grok serve apenas para extração estruturada.

---

## 📊 Schema JSON do Cartão

O cartão possui um schema estável e versionado (`cartao_schema_version: 1`) com:

### Campos Principais

- **numero_processo**: Número do processo (ex: "0001234-56.2023.5.10.0001")
- **partes**: Lista de reclamantes e reclamadas como constam nos autos
- **peticao_inicial**:
  - `causa_pedir`: Resumo da causa de pedir
  - `pedidos`: Lista de pedidos com:
    - `id`: P1, P2, P3...
    - `descricao`: Descrição do pedido
    - `periodo`: Período se aplicável
    - `valor`: Valor se especificado
    - `reflexos`: true/false (se há pedido de reflexos em 13º, férias, FGTS)
    - `fontes`: Trechos + ID do PJe + folhas
- **contestacoes**: Lista de contestações por pedido com:
  - `pedido_id`: ID do pedido contestado
  - `impugnacao_especifica`: true/false (art. 341 CPC - deve ter grau de detalhe equivalente ao da inicial)
  - `teses`: Lista de teses de defesa
  - `fontes`: Trechos + IDs/folhas
- **replica**: Se existe e pontos principais
- **questoes**: Lista de questões a decidir com:
  - `id`: Q1, Q2, Q3...
  - `titulo`: Título da questão
  - `tipo`: fato | direito | mista
  - `natureza_fatica`: constitutivo | impeditivo | modificativo | extintivo | irrelevante
  - `momento`: pressuposto_processual | condicao_da_acao | incidental | preliminar | merito
  - `de_oficio`: true/false (competência, capacidade, prescrição, etc.)
  - `arguida_na_defesa`: true/false
  - `acarreta_extincao`: true/false
  - `mencionar_na_minuta`: true/false (REGRA: questões de ofício só devem constar se foram arguidas na defesa OU se acarretam extinção)
  - `pedido_ids`: IDs dos pedidos relacionados
  - `fontes`: Trechos + IDs/folhas
- **mapa_pedido_defesa_questao**: Mapeamento entre pedidos, defesas e questões
- **avisos**: Lista de avisos sobre:
  - Falta de impugnação específica
  - Possível irrelevância (ex: ciência da gravidez vs Súmula 244)
  - Falta de ID do PJe ou folhas
  - Dados ausentes

### Exemplo de Cartão

```json
{
  "cartao_schema_version": 1,
  "numero_processo": "0001234-56.2023.5.10.0001",
  "partes": [
    {
      "tipo": "reclamante",
      "nome": "João da Silva"
    },
    {
      "tipo": "reclamada",
      "nome": "Empresa ABC LTDA"
    }
  ],
  "peticao_inicial": {
    "causa_pedir": "Trabalho em jornada extraordinária habitual sem pagamento",
    "pedidos": [
      {
        "id": "P1",
        "descricao": "Horas extraordinárias",
        "periodo": "01/2020 a 12/2022",
        "valor": "R$ 50.000,00",
        "reflexos": true,
        "fontes": [
          {
            "trecho": "jornada extraordinária habitual de 2 horas diárias",
            "id_pje": "ID 12345678",
            "folhas": "fls. 10"
          }
        ]
      }
    ]
  },
  "questoes": [
    {
      "id": "Q1",
      "titulo": "Existência de jornada extraordinária habitual",
      "tipo": "fato",
      "natureza_fatica": "constitutivo",
      "momento": "merito",
      "de_oficio": false,
      "mencionar_na_minuta": true,
      "pedido_ids": ["P1"]
    }
  ]
}
```

---

## 🧠 Método Jurídico Embutido

O prompt de extração incorpora método jurídico trabalhista:

### Questões

- **Questão de fato**: Eventos a provar (jornada, iniciativa da rescisão, pagamento, dano)
- **Questão de direito**: Norma, interpretação, consequências (adicional aplicável, falta grave 482/483, quitação, culpa)
- **Questão mista**: Combina fato e direito

### Fatos Juridicamente Relevantes

Fatos só importam se forem:
- **Constitutivos**: Criam direito (ex: trabalho em jornada extra)
- **Impeditivos**: Impedem direito (ex: prescrição)
- **Modificativos**: Modificam direito (ex: acordo)
- **Extintivos**: Extinguem direito (ex: quitação)

**Exemplo de fato irrelevante**: Ciência da gravidez pelo empregador não é relevante para estabilidade gestante (Súmula 244 TST).

### Impugnação Específica (Art. 341 CPC)

A defesa deve impugnar especificamente os fatos da inicial com grau de detalhe equivalente. **Negativa genérica NÃO basta**.

Exemplo:
- ❌ **Negativa genérica**: "Nega a existência de horas extras" → `impugnacao_especifica: false`
- ✅ **Impugnação específica**: "Nega horas extras porque o reclamante cumpria jornada de 8h controlada por ponto biométrico conforme docs fls. 50-60" → `impugnacao_especifica: true`

### Questões de Ofício

Questões cognoscíveis de ofício (competência, capacidade, prescrição, validade de atos, pressupostos processuais, condições da ação, inépcia):

**REGRA**: Questões de ofício só devem constar no cartão como "mencionar na minuta" se:
1. Foram arguidas na defesa, **OU**
2. Acarretam extinção de algum pedido

Caso contrário: `mencionar_na_minuta: false`

### Prova

Nesta fase, apenas localize onde está a prova no MD (se o texto distinguir entre prova oral/documental/pericial) e quais questões ela aparentemente toca, **sem valorar depoimentos**. A valoração será feita nas fases posteriores.

---

## 🚀 Como Usar

### Pré-requisitos

- Python 3.8+
- API Key do xAI (Grok)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/fgbkiwi/GrokCollectionUpload-Search.git
cd GrokCollectionUpload-Search

# Checkout da branch do Cartão do Caso
git checkout cursor/cartao-caso-entregavel-2-3b1b

# Instale as dependências
pip install -r requirements_cartao.txt
```

### Executar a Aplicação

```bash
python CartaoDoCaso.py
```

### Fluxo de Uso

1. **Configurar API Key**
   - Informe sua API Key do xAI (Grok)
   - Selecione o modelo (padrão: `grok-beta`)
   - A chave NÃO é gravada no JSON do cartão

2. **Escolher Arquivo/Pasta MD**
   - Clique em "Escolher Arquivo/Pasta MD"
   - Selecione um arquivo `.md` ou pasta com múltiplos `.md`
   - Os arquivos devem ser autos já convertidos para Markdown

3. **Extrair Cartão**
   - Clique em "Extrair Cartão"
   - Acompanhe o progresso na interface
   - A API Grok processará o MD e retornará o JSON estruturado

4. **Validar nas Tabelas**
   - **Aba Pedidos**: Tabela com pedidos × defesas, mostrando se houve impugnação específica
   - **Aba Questões**: Tabela de questões (fato/direito, momento, de ofício, mencionar ou não)
     - Você pode desmarcar questões que não devem ser mencionadas na minuta
   - **Aba Avisos**: Lista de avisos sobre a extração
   - **Aba JSON**: Visualização do JSON completo

5. **Confirmar ou Voltar**
   - **Confirmar Cartão**: Grava JSON + cópia MD de auditoria em `~/.indexador_sentencas/cartoes/`
   - **Voltar a Extrair**: Descarta o cartão atual e volta para tela inicial
   - **Exportar JSON**: Exporta o JSON para um local específico

### Estrutura de Arquivos Salvos

```
~/.indexador_sentencas/cartoes/
├── 20250119_184530_0001234-56_2023_5_10_0001_confirmado.json
├── 20250119_184530_0001234-56_2023_5_10_0001_rascunho.json
└── autos_md/
    └── 20250119_184530_0001234-56_2023_5_10_0001.md
```

---

## 📂 Estrutura do Código

```
cartao_caso/
├── __init__.py           # Exports do pacote
├── schema.py             # Schema Pydantic do cartão
├── extrator.py           # Cliente HTTP para API Grok
└── persistencia.py       # Persistência local de cartões

tests/
├── __init__.py
└── test_cartao_caso.py   # Testes unitários com MD sintético

CartaoDoCaso.py           # Aplicação Flet (UI principal)
requirements_cartao.txt   # Dependências Python
README_CARTAO.md          # Esta documentação
```

---

## 🧪 Testes

Os testes unitários usam MD sintético curto (inicial + contestação de jornada, uma preliminar, uma questão de ofício não arguida que NÃO deve ir para minuta).

A API Grok é mockada nos testes - não requer chaves reais.

### Executar Testes

```bash
# Instalar pytest
pip install pytest pytest-mock

# Rodar testes
pytest tests/test_cartao_caso.py -v
```

### Cobertura de Testes

- ✅ Validação de schema Pydantic
- ✅ Extração de arquivo com mock da API
- ✅ Regra de questão de ofício não mencionada
- ✅ Salvar e carregar cartões
- ✅ Listagem de cartões (confirmados/rascunhos)
- ✅ Exportação de cartão
- ✅ Estatísticas de persistência

---

## ⚙️ Configuração Avançada

### Modelo Grok

Você pode escolher entre os modelos disponíveis:
- `grok-beta` (padrão, recomendado): Rápido e eficiente
- `grok-2-1212`: Melhor qualidade (mais lento)
- `grok-4.6`: Modelo mais recente (se disponível)

### Temperature

A extração usa `temperature=0.1` (baixa) para ser precisa e conservadora. Não inventa dados.

### Structured Output

Se a API xAI oferecer, usa `response_format: {"type": "json_object"}` para forçar resposta JSON válida.

---

## 🔒 Segurança

- ✅ API Key é obscurecida no campo (password)
- ✅ API Key **NÃO** é gravada no JSON do cartão
- ✅ Cartões salvos localmente em `~/.indexador_sentencas/cartoes/`
- ✅ Cópia MD de auditoria para rastreabilidade
- ✅ Validação de schema com Pydantic

---

## 🎯 Critério de Pronto

**Dado** um arquivo MD sintético de autos,  
**Quando** o app processa e extrai o cartão,  
**Então**:
- O cartão JSON contém pedidos, defesas e questões tipificadas
- O juiz pode editar/confirmar nas tabelas
- Questão de ofício não arguida e sem extinção fica marcada `mencionar_na_minuta: false`
- O arquivo persistido reflete a confirmação do juiz

---

## 📝 Roadmap (Próximas Fases)

Este é o **Entregável 2** do projeto. As próximas fases incluirão:

### Fase 3: Examinadores de Prova
- Examinador documental
- Examinador pericial
- Examinador oral (depoimentos)

### Fase 4: Minuta Automatizada
- Usar Collection de sentenças publicadas (PR #2)
- Buscar precedentes relevantes
- Gerar fundamentação
- Biblioteca de modelos temáticos (juros/FGTS)

### Fase 5: Minutador Completo
- Integração com Sarah (kernel de raciocínio jurídico)
- Geração de minuta completa em Markdown
- Exportação para Word/PDF

---

## 🐛 Solução de Problemas

### Erro: "API Key inválida"
**Solução**: Verifique se a chave começa com `xai-` e foi copiada corretamente do console xAI.

### Erro: "Nenhum arquivo .md encontrado"
**Solução**: Certifique-se de que o arquivo/pasta selecionada contém arquivos `.md` de autos convertidos.

### Erro: "Erro ao processar resposta da API"
**Solução**: A API pode ter retornado texto ao invés de JSON. Tente usar um modelo diferente (ex: `grok-2-1212`).

### Aviso: "Dados ausentes"
**Esperado**: Se o MD não contém alguma informação (ex: número do processo), o cartão deixará o campo nulo e criará um aviso.

---

## 📚 Referências

- **xAI API Docs**: https://docs.x.ai/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Flet Docs**: https://flet.dev/
- **CPC Art. 341**: Ônus de impugnação especificada
- **Súmula 244 TST**: Estabilidade gestante independe de ciência do empregador

---

## 📄 Licença

Este sistema foi desenvolvido especificamente para uso no Tribunal Regional do Trabalho.

---

**Desenvolvido para auxiliar a magistratura trabalhista brasileira na análise estruturada de autos e preparação de decisões fundamentadas.**
