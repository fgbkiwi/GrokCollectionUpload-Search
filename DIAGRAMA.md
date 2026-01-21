# 📊 Diagrama do Sistema de Busca de Precedentes

## Arquitetura Completa

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW COMPLETO                                │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐
│  ETAPA 1: PREPARAÇÃO     │
│  CollectionUploader.py   │
└──────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Entrada: Sentenças Indexadas Revisado.json           │
│  ┌──────────────────────────────────────────────────┐ │
│  │ {                                                 │ │
│  │   "categoria": "HORAS EXTRAORDINÁRIAS",          │ │
│  │   "reclamada": "Empresa XYZ LTDA",               │ │
│  │   "conteudo": "Texto da fundamentação...",       │ │
│  │   "numero_processo": "0000123-45.2023.5.10.0009",│ │
│  │   "data_publicacao": "2023-06-15",               │ │
│  │   "tipo_acao": "Reclamação Trabalhista"          │ │
│  │ }                                                 │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  PROCESSAMENTO                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 1. Extração de Keywords Jurídicas                │ │
│  │    • Legislação: CLT, Súmulas, Leis              │ │
│  │    • Conceitos: Insalubridade, FGTS, etc.        │ │
│  │                                                   │ │
│  │ 2. Chunking Inteligente                          │ │
│  │    • Chunk Size: 2048 chars                      │ │
│  │    • Overlap: 256 chars (12.5%)                  │ │
│  │    • Quebra em pontos finais                     │ │
│  │                                                   │ │
│  │ 3. Geração de Metadados                          │ │
│  │    • YAML Front Matter                           │ │
│  │    • Identificadores únicos                      │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Saída: Arquivos MD com Metadados                     │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ---                                               │ │
│  │ categoria: HORAS EXTRAORDINÁRIAS                 │ │
│  │ reclamada: Empresa XYZ LTDA                      │ │
│  │ numero_processo: 0000123-45.2023.5.10.0009       │ │
│  │ data_publicacao: 2023-06-15                      │ │
│  │ tipo_acao: Reclamação Trabalhista                │ │
│  │ keywords: horas_extras, clt, artigo_clt, fgts    │ │
│  │ ---                                               │ │
│  │ # HORAS EXTRAORDINÁRIAS                          │ │
│  │                                                   │ │
│  │ [Conteúdo da fundamentação...]                   │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  ETAPA 2: INDEXAÇÃO                                    │
│  xAI Collections Console                               │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  xAI Collections Processing                            │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 1. Upload de Arquivos MD                         │ │
│  │    • Parsing de YAML Front Matter                │ │
│  │    • Extração de conteúdo                        │ │
│  │                                                   │ │
│  │ 2. Geração de Embeddings                         │ │
│  │    • Modelo de linguagem xAI                     │ │
│  │    • Vetores de alta dimensionalidade            │ │
│  │    • Captura de significado semântico            │ │
│  │                                                   │ │
│  │ 3. Indexação                                     │ │
│  │    • Índice vetorial para busca semântica        │ │
│  │    • Índice invertido para keywords              │ │
│  │    • Índice de metadados para filtros            │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Collection Indexada e Pronta                          │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ✅ Embeddings: 512 documentos                    │ │
│  │ ✅ Keywords: 1.234 termos únicos                 │ │
│  │ ✅ Metadados: 5 campos configurados              │ │
│  │ ✅ Status: Ready for Search                      │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  ETAPA 3: BUSCA INTERATIVA                             │
│  PrecedenteSearchApp.py (Flet UI)                      │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Interface do Usuário                                               │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 🗑️ Limpar  📋 Copiar  📎 Anexar  ⚙️ Config                   │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  [Chat History]                                               │ │
│  │                                                               │ │
│  │  👤 USUÁRIO:                                                  │ │
│  │  Como fundamentar adicional de insalubridade para             │ │
│  │  profissionais de saúde?                                      │ │
│  │                                                               │ │
│  │  🤖 GROK:                                                     │ │
│  │  [Resposta com precedentes...]                                │ │
│  │                                                               │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ Collection: [Precedentes Trabalhistas ▼]  🔘 Buscar na Coll. │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │ Digite sua pergunta...                              [Enviar]  │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Consulta do Usuário                                   │
│  "Como fundamentar adicional de insalubridade para     │
│   profissionais de saúde?"                             │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  xAI API - Chat Completion com Collections Search Tool             │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ POST https://api.x.ai/v1/chat/completions                     │ │
│  │ {                                                              │ │
│  │   "model": "grok-2-1212",                                      │ │
│  │   "messages": [...],                                           │ │
│  │   "tools": [{                                                  │ │
│  │     "type": "collection_search",                               │ │
│  │     "collection_id": "col_xxx",                                │ │
│  │     "search_parameters": {                                     │ │
│  │       "search_type": "hybrid",   ← Semântica + Keywords       │ │
│  │       "top_k": 5                 ← Top 5 resultados           │ │
│  │     }                                                          │ │
│  │   }]                                                           │ │
│  │ }                                                              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Busca Híbrida na Collection                                        │
│                                                                     │
│  ┌─────────────────────┐         ┌─────────────────────┐          │
│  │ BUSCA SEMÂNTICA     │         │ BUSCA POR KEYWORDS  │          │
│  │ (Embeddings)        │         │                     │          │
│  │                     │         │                     │          │
│  │ 1. Embedding query  │         │ 1. Extrai keywords  │          │
│  │ 2. Similaridade     │    +    │    - insalubridade  │          │
│  │    coseno           │         │    - saúde          │          │
│  │ 3. Top-K docs       │         │ 2. Busca invertida  │          │
│  │    similares        │         │ 3. Match exato      │          │
│  └─────────────────────┘         └─────────────────────┘          │
│           │                               │                        │
│           └───────────┬───────────────────┘                        │
│                       ▼                                            │
│           ┌───────────────────────┐                                │
│           │ COMBINA RESULTADOS    │                                │
│           │ • Ranking ponderado   │                                │
│           │ • Aplica filtros      │                                │
│           │ • Top-5 finais        │                                │
│           └───────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Precedentes Encontrados (Top-5)                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 1. [0000006-73.2023.5.10.0009]                   │ │
│  │    ADICIONAL DE INSALUBRIDADE                    │ │
│  │    Relevância: 0.92                              │ │
│  │    Keywords match: insalubridade, saúde          │ │
│  │                                                   │ │
│  │ 2. [0000125-11.2022.5.10.0009]                   │ │
│  │    ADICIONAL DE INSALUBRIDADE                    │ │
│  │    Relevância: 0.87                              │ │
│  │    Keywords match: insalubridade, hospital       │ │
│  │                                                   │ │
│  │ [... mais 3 precedentes ...]                     │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Grok Gera Resposta Fundamentada                      │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Com base nos precedentes encontrados na sua      │ │
│  │ jurisprudência, o adicional de insalubridade     │ │
│  │ para profissionais de saúde deve ser analisado   │ │
│  │ considerando:                                    │ │
│  │                                                   │ │
│  │ 1. **Contato direto com pacientes**             │ │
│  │    Conforme processo 0000006-73.2023.5.10.0009:  │ │
│  │    "...tinha contato direto com pacientes..."    │ │
│  │                                                   │ │
│  │ 2. **Uso de EPIs não elimina risco**            │ │
│  │    O precedente estabelece que "O uso dos EPI's  │ │
│  │    reduz os riscos...mas nesse tipo de atividade │ │
│  │    não elimina..."                               │ │
│  │                                                   │ │
│  │ 3. **Grau Médio (20% salário-mínimo)**          │ │
│  │    Base legal: Anexo 14 da NR-15                 │ │
│  │                                                   │ │
│  │ **Fundamentação sugerida:**                      │ │
│  │ [Minuta baseada nos precedentes...]              │ │
│  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│  Resposta Exibida ao Usuário                           │
│  • Fundamentação completa                              │
│  • Citações de precedentes específicos                 │
│  • Números de processo                                 │
│  • Base legal                                          │
│  • Sugestões de minuta                                 │
└────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════

FLUXO DE DADOS DETALHADO

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   JSON      │────▶│  Arquivos   │────▶│    xAI      │────▶│   Grok +    │
│  Sentenças  │     │     MD      │     │ Collections │     │ Precedentes │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
   25 objetos         64 arquivos        Embeddings            Top-5 docs
   Estruturado        + Metadados        + Keywords           + Resposta
   
═══════════════════════════════════════════════════════════════════════

COMPONENTES TÉCNICOS

┌──────────────────────────────────────────────────────────────────┐
│  CollectionUploader.py                                           │
│  • Python 3.8+                                                   │
│  • Bibliotecas built-in (json, re, pathlib)                     │
│  • Chunking: 2048 chars, overlap 256                            │
│  • Keywords: 15 termos jurídicos por documento                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  xAI Collections                                                 │
│  • Embedding Model: xAI proprietary                             │
│  • Vector Database: High-dimensional indexing                   │
│  • Hybrid Search: Semantic + Keyword matching                   │
│  • Filters: Metadata-based filtering                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  PrecedenteSearchApp.py                                          │
│  • Flet 0.20.0+ (UI framework)                                  │
│  • Requests 2.31.0+ (HTTP client)                               │
│  • Pyperclip 1.8.2+ (Clipboard)                                 │
│  • Configurações persistentes (JSON)                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Grok Model                                                      │
│  • grok-2-1212 (Dezembro 2024)                                  │
│  • Temperature: 0.7 (configurável)                              │
│  • Context window: Large (exact size proprietary)               │
│  • Tools: Collections Search Tool integration                   │
└──────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════

METRICAS DE PERFORMANCE (Exemplo com 25 sentenças)

Processamento:      ⚡ 2-5 segundos
Arquivos gerados:   📄 64 arquivos MD (chunks)
Upload xAI:         ⬆️ 1-2 minutos
Indexação:          🔄 3-5 minutos
Busca (query):      🔍 5-15 segundos
Resposta (Grok):    💬 10-30 segundos

Total (primeira busca): ~20-40 segundos após indexação

═══════════════════════════════════════════════════════════════════
```

## Legenda de Símbolos

- `→` Fluxo de dados
- `┌─┐` Componentes/Módulos
- `▼` Sequência de processamento
- `+` Operação de combinação
- `⚡` Performance
- `✅` Validação/Sucesso
- `🔍` Busca/Pesquisa
- `📄` Documento/Arquivo
- `💬` Resposta/Output

---

**Este diagrama ilustra o fluxo completo desde o JSON original até a resposta fundamentada do Grok.**
