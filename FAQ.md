# ❓ Perguntas Frequentes (FAQ)

## 📋 Índice

1. [Sobre o Sistema](#sobre-o-sistema)
2. [Configuração Inicial](#configuração-inicial)
3. [Uso do CollectionUploader.py](#uso-do-collectionuploaderpy)
4. [Uso do PrecedenteSearchApp.py](#uso-do-precedentesearchapppy)
5. [xAI Collections](#xai-collections)
6. [Busca e Resultados](#busca-e-resultados)
7. [Problemas Técnicos](#problemas-técnicos)
8. [Otimização e Performance](#otimização-e-performance)

---

## Sobre o Sistema

### Q1: O que este sistema faz?

**A:** O sistema permite buscar precedentes em sentenças trabalhistas usando busca semântica (IA). Em vez de procurar palavras-chave exatas, ele entende o significado da sua consulta e encontra precedentes relevantes, mesmo que usem termos diferentes.

### Q2: Por que usar busca semântica em vez de busca tradicional?

**A:** Busca tradicional por palavras-chave pode perder precedentes relevantes que usam sinônimos ou formulações diferentes. Busca semântica:
- ✅ Entende o significado, não só palavras exatas
- ✅ Encontra precedentes similares com termos diferentes
- ✅ Combina semântica + keywords (busca híbrida)
- ✅ Considera contexto jurídico

**Exemplo:**
- **Busca tradicional**: "justa causa por insubordinação" → só encontra documentos com essas palavras exatas
- **Busca semântica**: entende que "desrespeito à autoridade", "desobediência hierárquica", "conduta insubordinada" são semanticamente relacionados

### Q3: Preciso ter conhecimento técnico para usar?

**A:** 
- **Para usar a aplicação de busca**: NÃO. Interface simples tipo chat.
- **Para configuração inicial**: Conhecimento básico de Python e linha de comando.
- **Para manutenção**: Conhecimento intermediário de Python recomendado.

---

## Configuração Inicial

### Q4: Quais são os requisitos do sistema?

**A:**
- Python 3.8 ou superior
- Conta xAI (https://console.x.ai/)
- API Key do Grok
- Internet (para comunicação com xAI API)
- ~10 GB espaço em disco (para 10.000+ sentenças)

### Q5: Quanto custa usar xAI Collections?

**A:** Consulte pricing atualizado em: https://x.ai/pricing

**Fatores de custo:**
- Armazenamento de embeddings
- Número de consultas (queries)
- Tokens processados pelo Grok

**Dica**: Para testes iniciais, use arquivo de excerto (25 sentenças) para minimizar custos.

### Q6: Como obtenho API Key do Grok?

**A:**
1. Acesse: https://console.x.ai/
2. Faça login ou crie conta
3. Vá para **Settings** → **API Keys**
4. Clique em **Generate API Key**
5. Copie e guarde em local seguro

⚠️ **IMPORTANTE**: Nunca compartilhe sua API Key publicamente!

### Q7: Qual a diferença entre API Key e Management Key?

**A:**
- **API Key**: Para usar modelo Grok (chat completions)
- **Management Key**: Para gerenciar Collections (criar, editar, acessar)

Você precisa de **ambas** para o sistema funcionar completamente.

---

## Uso do CollectionUploader.py

### Q8: Como uso o CollectionUploader.py?

**A:**
```bash
python CollectionUploader.py "Sentenças Indexadas Revisado.json" --output-dir ./sentencas_md
```

### Q9: Qual deve ser a estrutura do arquivo JSON de entrada?

**A:**
```json
[
  {
    "categoria": "HORAS EXTRAORDINÁRIAS",
    "reclamada": "Empresa XYZ LTDA",
    "conteudo": "Texto da fundamentação...",
    "numero_processo": "0000123-45.2023.5.10.0009",
    "data_publicacao": "2023-06-15",
    "tipo_acao": "Reclamação Trabalhista"
  }
]
```

Todos os campos são obrigatórios. Use string vazia (`""`) para campos não aplicáveis.

### Q10: O que são "chunks" e por que são necessários?

**A:** Documentos muito longos (>2048 caracteres) são divididos em "chunks" (pedaços) para:
- ✅ Melhorar qualidade dos embeddings
- ✅ Permitir busca mais precisa
- ✅ Respeitar limites de tamanho do modelo

**Overlap** (sobreposição) entre chunks preserva contexto nas quebras.

### Q11: Posso processar o arquivo JSON completo de uma vez?

**A:** SIM! O script foi projetado para processar grandes volumes. Para ~10.000 sentenças, o processamento leva aproximadamente 5-10 minutos.

### Q12: Como adicionar novas sentenças depois?

**A:**
1. Adicione novos objetos ao arquivo JSON
2. Execute CollectionUploader.py novamente
3. Faça upload dos novos arquivos MD para a Collection

⚠️ **ATENÇÃO**: Evite duplicatas. Use números de processo únicos.

---

## Uso do PrecedenteSearchApp.py

### Q13: Como inicio a aplicação?

**A:**
```bash
python PrecedenteSearchApp.py
```

Na primeira vez, configure API Keys em ⚙️ Configurações.

### Q14: Posso usar sem interface gráfica?

**A:** Atualmente, a aplicação é desenvolvida com Flet (interface gráfica). Para uso sem interface, você pode:
1. Fazer requisições diretas à xAI API usando Python/requests
2. Modificar o código para uso CLI (linha de comando)

### Q15: Como anexo arquivos ao contexto?

**A:**
1. Clique no botão 📎 **Anexar arquivo**
2. Selecione arquivo(s) (petição, documento, etc.)
3. O conteúdo será incluído no contexto da próxima mensagem

⚠️ **LIMITE**: Arquivos grandes (>100KB) podem exceder contexto do modelo.

### Q16: Como copio o histórico do chat?

**A:** Clique no botão 📋 **Copiar chat**. Todo o histórico será copiado para o clipboard no formato:

```
[USUÁRIO]
Pergunta...

[GROK]
Resposta...
```

### Q17: O que faz o toggle "Buscar na Collection"?

**A:** 
- **Habilitado**: Grok busca precedentes na Collection e fundamenta resposta
- **Desabilitado**: Grok responde baseado apenas em conhecimento geral (sem precedentes específicos)

---

## xAI Collections

### Q18: Como crio uma Collection?

**A:**
1. Acesse: https://console.x.ai/
2. Vá para **Collections**
3. Clique em **Create Collection**
4. Configure:
   - **Name**: Precedentes Trabalhistas
   - **Chunk Size**: 2048
   - **Chunk Overlap**: 256
5. Clique em **Create**

### Q19: Como faço upload dos arquivos MD?

**A:**
1. Acesse sua Collection no xAI Console
2. Clique em **Upload Files**
3. Selecione todos os arquivos MD do diretório
4. Aguarde processamento (barra de progresso)

⏱️ **Tempo**: ~1-5 minutos para 100 arquivos, dependendo da conexão.

### Q20: Como configuro metadados na Collection?

**A:**
1. Acesse **Settings** da Collection
2. Vá para **Metadata Fields**
3. Adicione campos:
   - `categoria` (tipo: text, indexar como filtro)
   - `reclamada` (tipo: text, indexar como filtro)
   - `numero_processo` (tipo: text, indexar como filtro)
   - `data_publicacao` (tipo: date, indexar como filtro)
   - `tipo_acao` (tipo: text, indexar como filtro)
   - `keywords` (tipo: text, indexar para busca)

### Q21: Posso ter múltiplas Collections?

**A:** SIM! Você pode criar Collections temáticas:
- **Collection CLT**: Questões substantivas (horas extras, férias, etc.)
- **Collection Processual**: Questões processuais (competência, prescrição)
- **Collection Sindical**: Questões sindicais

Selecione a Collection desejada no dropdown da aplicação.

---

## Busca e Resultados

### Q22: Como formulo uma boa consulta?

**A:**

**✅ BOM:**
- "Como fundamentar adicional de insalubridade para profissionais de saúde em hospitais?"
- "Precedentes sobre justa causa por insubordinação envolvendo ofensas verbais"
- "Critérios para equiparação salarial entre professores de áreas diferentes"

**❌ EVITE:**
- "Insalubridade" (muito genérico)
- "O que você sabe sobre CLT?" (fora do escopo)
- Consultas longas demais (>200 palavras)

### Q23: Quantos precedentes são retornados?

**A:** Por padrão, o sistema retorna **top-5** precedentes mais relevantes. Você pode ajustar o parâmetro `top_k` no código se desejar mais ou menos resultados.

### Q24: Como priorizo precedentes de uma empresa específica?

**A:** Mencione a empresa na consulta:

```
Busque precedentes sobre adicional noturno envolvendo a empresa Petrobras
```

O sistema aplicará filtro `reclamada = "Petrobras"` e priorizará esses resultados.

### Q25: Como busco precedentes recentes?

**A:** Especifique período temporal:

```
Decisões sobre FGTS dos últimos 2 anos
```

ou

```
Precedentes sobre prescrição de 2022 em diante
```

### Q26: O Grok sempre cita os números de processo?

**A:** Depende do **System Prompt**. Para garantir citações, use:

```
Você é um assistente jurídico especializado em Direito do Trabalho. 
SEMPRE cite o número do processo ao mencionar precedentes. 
Formate citações como: "Conforme processo 0000123-45.2023.5.10.0009: [citação]"
```

---

## Problemas Técnicos

### Q27: Erro "Management Key inválida"

**A:**
1. Verifique se copiou a chave completa (sem espaços extras)
2. Confirme que a chave pertence à Collection correta
3. Regenere a chave se necessário (xAI Console → Settings → API Keys)

### Q28: Erro "Collection não encontrada"

**A:**
1. Aguarde processamento completo dos arquivos MD
2. Verifique se o Collection ID está correto
3. Refresh da lista de Collections na aplicação (reabra Configurações)

### Q29: Aplicação Flet não abre

**A:**
```bash
# Reinstale Flet
pip uninstall flet
pip install flet --upgrade

# Teste novamente
python PrecedenteSearchApp.py
```

### Q30: Erro "Connection timeout"

**A:**
- Verifique sua conexão com internet
- xAI API pode estar temporariamente indisponível
- Tente novamente após alguns minutos
- Aumente timeout no código se conexão for lenta

### Q31: Busca não retorna resultados relevantes

**A:**
1. **Verifique indexação**: Confirme que arquivos foram processados
2. **Ajuste consulta**: Use termos mais específicos
3. **Aumente top_k**: Configure para retornar mais resultados (ex: 10)
4. **Verifique metadados**: Confirme que campos estão configurados corretamente
5. **Teste com consulta simples**: "Adicional de insalubridade" (deve retornar resultados)

### Q32: "Chunk size muito grande" ao criar Collection

**A:** 
- Reduza chunk_size para 1024 caracteres
- Processe novamente com CollectionUploader.py usando chunk_size menor:
```python
processor = SentencaProcessor(output_dir, chunk_size=1024, overlap=256)
```

---

## Otimização e Performance

### Q33: Como otimizar para grandes volumes (10.000+ sentenças)?

**A:**
1. **Processamento**: Execute CollectionUploader.py em lotes (2.000-5.000 por vez)
2. **Upload**: Use upload em paralelo se disponível
3. **Indexação**: Aguarde indexação completa antes de buscar
4. **Consultas**: Use filtros de metadados para reduzir escopo de busca

### Q34: Como melhorar qualidade das respostas?

**A:**
1. **System Prompt**: Customize para seu estilo de fundamentação
2. **Temperature**: 
   - 0.3-0.5: Respostas mais conservadoras e precisas
   - 0.7-0.9: Respostas mais criativas e elaboradas
3. **Top-K**: Aumente para considerar mais precedentes
4. **Filtros**: Use metadados para restringir busca ao contexto relevante

### Q35: Como reduzir custos de API?

**A:**
1. **Cache local**: Salve respostas frequentes
2. **Batching**: Agrupe consultas relacionadas
3. **Filtros eficientes**: Use metadados para reduzir tokens processados
4. **Modelo adequado**: Use grok-2-1212 (não necessariamente o mais caro)

### Q36: Posso usar offline?

**A:** NÃO. O sistema requer:
- Acesso à xAI API (online)
- Processamento de embeddings (cloud)
- Modelo Grok (cloud)

Para uso offline, considere alternativas como modelos locais (Ollama, LLaMA).

### Q37: Como organizo Collections para melhor performance?

**A:**

**Estratégia 1: Por Tema**
- Collection CLT (direito material)
- Collection Processual (direito processual)
- Collection Sindical (direito coletivo)

**Estratégia 2: Por Período**
- Collection 2020-2021
- Collection 2022-2023
- Collection 2024+

**Estratégia 3: Por Tipo de Ação**
- Collection Reclamações Trabalhistas
- Collection Mandados de Segurança
- Collection Tutelas de Urgência

Selecione a estratégia que melhor atende seu fluxo de trabalho.

### Q38: Quantas consultas posso fazer por dia?

**A:** Depende do plano xAI contratado. Consulte:
- https://x.ai/pricing
- xAI Console → Usage & Billing

---

## Avançado

### Q39: Como integro com outros sistemas?

**A:** Use a xAI API diretamente:

```python
import requests

api_key = "sua_api_key"
collection_id = "col_xxx"

response = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "grok-2-1212",
        "messages": [{"role": "user", "content": "sua consulta"}],
        "tools": [{
            "type": "collection_search",
            "collection_id": collection_id,
            "search_parameters": {"search_type": "hybrid", "top_k": 5}
        }]
    }
)
```

### Q40: Como contribuo para o projeto?

**A:**
- Sugira melhorias
- Reporte bugs
- Compartilhe casos de uso
- Desenvolva extensões

---

## 📞 Suporte Adicional

**Não encontrou sua pergunta?**

1. Consulte documentação completa: `README.md`
2. Verifique guia rápido: `QUICKSTART.md`
3. Analise diagramas: `DIAGRAMA.md`
4. Veja exemplos: `EXEMPLO_MD.md`

**Recursos externos:**
- xAI Documentation: https://docs.x.ai/
- xAI Console: https://console.x.ai/
- Flet Documentation: https://flet.dev/docs/

---

**Sistema desenvolvido para modernizar a busca de precedentes judiciais com IA.**
