# Exemplo de Arquivo MD Gerado

Este é um exemplo de como os arquivos Markdown são estruturados após o processamento do JSON.

## 📄 Arquivo: 0007_0000006_73_2023_5_10_0009_ADICIONAL_DE_INSALUBRIDADE.md

```markdown
---
categoria: ADICIONAL DE INSALUBRIDADE
reclamada: Não especificada
numero_processo: 0000006-73.2023.5.10.0009
data_publicacao: Não informada
tipo_acao: Reclamação Trabalhista
keywords: adicional de insalubridade, insalubridade, fgts, ferias
---
# ADICIONAL DE INSALUBRIDADE

A perita do juízo apresentou as seguintes conclusões em seu laudo (fls. 397, ID. bfb16bc):
Com base na perícia realizada e na constatação das atividades de de supervisão de 
estagiários, atuando em hospitais do GDF, conclui-se que a reclamante tinha contato 
direto com pacientes. O uso dos EPI's reduz os riscos de contaminação por agentes 
biológicos, mas nesse tipo de atividade não elimina, portanto, os procedimentos e 
intervenções de técnico de enfermagem em pacientes durante a supervisão de estagiários 
são Insalubres de Grau Médio (anexo n° 14 da NR-15 da Port.3.214/78).

Nos períodos em que o reclamante não realizou supervisão de estágios em hospitais, 
08/08/2018 a 31/12/2018 e 12/05/2020 a 18/11/2020, não havia exposição a agentes 
biológicos insalubres, e não há adicional de insalubridade a ser considerado nestes 
períodos.

Não houve impugnação da reclamada ao laudo pericial.

Defere-se, portanto, ao reclamante o pagamento do adicional de insalubridade 
correspondente a 20% do salário-mínimo legal, relativamente a todo o período trabalhado 
(08/08/2018 a 12/10/2022), com reflexos sobre férias acrescidas de 1/3, gratificações 
natalinas e FGTS (com a multa rescisória de 40%).
```

## 🔍 Estrutura Explicada

### 1️⃣ Bloco de Metadados (YAML Front Matter)

```yaml
---
categoria: ADICIONAL DE INSALUBRIDADE    # ← Categoria principal para filtro
reclamada: Não especificada              # ← Nome da empresa (para priorização)
numero_processo: 0000006-73.2023.5.10.0009  # ← ID único do processo
data_publicacao: Não informada           # ← Data para filtro temporal
tipo_acao: Reclamação Trabalhista        # ← Tipo de processo
keywords: adicional de insalubridade, insalubridade, fgts, ferias  # ← Keywords extraídas
---
```

**Como são usados:**
- `categoria`: Busca por tipo de tema jurídico
- `reclamada`: Prioriza precedentes da mesma empresa
- `numero_processo`: Citação precisa do precedente
- `data_publicacao`: Ordena por precedentes mais recentes
- `tipo_acao`: Filtra por tipo de processo
- `keywords`: Busca híbrida (semântica + palavras-chave)

### 2️⃣ Título do Documento

```markdown
# ADICIONAL DE INSALUBRIDADE
```

Corresponde exatamente ao campo `categoria` do JSON.

### 3️⃣ Conteúdo da Fundamentação

Texto completo da fundamentação jurídica, preservando formatação e estrutura original.

---

## 📄 Exemplo com Múltiplos Chunks

Para documentos longos (>2048 caracteres), o sistema divide em partes com overlap:

### Arquivo: 0003_0000006_73_2023_5_10_0009_ATIVIDADE_DE_PROFESSOR_CARACTERIZAÇÃO_part01.md

```markdown
---
categoria: ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO
reclamada: Não especificada
numero_processo: 0000006-73.2023.5.10.0009
data_publicacao: Não informada
tipo_acao: Reclamação Trabalhista
keywords: atividade de professor — caracterização, artigo_clt, clt, legislacao
---
# ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO

**[Parte 1 de 6]**    # ← Indicador de chunk

A disciplina do magistério nos arts. 317 a 323 da CLT foi concebida, 
historicamente, como aplicável aos estabelecimentos particulares de ensino...

[Conteúdo continua até ~2048 caracteres]
```

### Arquivo: 0003_0000006_73_2023_5_10_0009_ATIVIDADE_DE_PROFESSOR_CARACTERIZAÇÃO_part02.md

```markdown
---
categoria: ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO
reclamada: Não especificada
numero_processo: 0000006-73.2023.5.10.0009
data_publicacao: Não informada
tipo_acao: Reclamação Trabalhista
keywords: atividade de professor — caracterização, artigo_clt, clt, legislacao
---
# ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO

**[Parte 2 de 6]**    # ← Próximo chunk

...continuação com overlap dos últimos 256 caracteres da parte 1...

[Novo conteúdo até ~2048 caracteres]
```

**Benefícios do Chunking com Overlap:**
- ✅ Preserva contexto entre chunks
- ✅ Evita perda de informação em quebras
- ✅ Melhora busca semântica em documentos longos
- ✅ Embeddings capturam melhor o significado

---

## 🎯 Como xAI Collections Usa Esses Arquivos

### Etapa 1: Indexação
xAI Collections processa cada arquivo MD:
1. **Extrai metadados** do YAML front matter
2. **Gera embeddings** do conteúdo usando modelo de linguagem
3. **Indexa keywords** para busca híbrida
4. **Cria índice** para busca eficiente

### Etapa 2: Busca Híbrida

Quando você faz uma consulta como:
> "Precedentes sobre adicional de insalubridade para profissionais de saúde"

O sistema:
1. **Busca Semântica** (embeddings):
   - Calcula embedding da consulta
   - Compara com embeddings dos documentos
   - Identifica documentos semanticamente similares

2. **Busca por Keywords**:
   - Identifica keywords relevantes: `insalubridade`, `profissionais`, `saúde`
   - Busca documentos com essas keywords

3. **Combina Resultados** (hybrid search):
   - Ranqueia documentos por relevância
   - Retorna top-K mais relevantes (default: 5)

4. **Aplica Filtros** (metadados):
   - Filtra por `categoria LIKE "%INSALUBRIDADE%"`
   - Ordena por `data_publicacao DESC` (mais recentes primeiro)
   - Prioriza `reclamada = "Hospital XYZ"` se especificado

### Etapa 3: Geração de Resposta

Grok recebe:
- Consulta do usuário
- Top-5 precedentes mais relevantes (conteúdo completo)
- Metadados dos precedentes

E gera resposta fundamentada:
```
Com base nos precedentes encontrados, o adicional de insalubridade 
para profissionais de saúde que supervisionam estagiários em hospitais 
deve ser deferido em grau médio (20% do salário-mínimo), conforme 
fundamentado no processo 0000006-73.2023.5.10.0009:

[Citação do precedente]

Este entendimento está alinhado com o anexo 14 da NR-15...
```

---

## 💡 Dicas para Otimização

### Melhore a Qualidade dos Metadados:

1. **Preencha `reclamada`**: Sempre que possível
2. **Data precisa**: Informe `data_publicacao` para ordenação temporal
3. **Keywords customizadas**: Adicione termos específicos do caso

### Ajuste Chunking para Casos Específicos:

```python
# Para textos muito técnicos ou densos
processor = SentencaProcessor(chunk_size=1024, overlap=256)

# Para textos mais narrativos
processor = SentencaProcessor(chunk_size=3072, overlap=512)
```

### Organize Collections Tematicamente:

- **Collection 1**: Questões de CLT (horas extras, férias, etc.)
- **Collection 2**: Questões processuais (competência, prescrição)
- **Collection 3**: Questões sindicais (representação, negociação)

---

**Este formato estruturado permite busca semântica poderosa e precisa em grandes volumes de precedentes judiciais.**
