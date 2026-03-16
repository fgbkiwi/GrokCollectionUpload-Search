# 🧪 Guia de Testes e Diagnosticos

**Guia completo para testes, validação e diagnósticos do sistema**

---

## 📋 Índice

1. [Testes Funcionais](#testes-funcionais)
2. [Diagnósticos de Collection](#diagnósticos-de-collection)
3. [Tempos de Processamento](#tempos-de-processamento)
4. [Solução de Problemas](#solução-de-problemas)
5. [Ferramentas de Diagnóstico](#ferramentas-de-diagnóstico)

---

## Testes Funcionais

### Pré-requisitos

- [ ] Python 3.7+ instalado
- [ ] Dependências instaladas (`pip install -r requirements_*.txt`)
- [ ] Credenciais xAI (API Key + Management Key)
- [ ] Collection criada no xAI Console
- [ ] Arquivo JSON de teste (recomendado: 25 sentenças)

### Teste 1: Configuração e Carregamento

**Objetivo**: Verificar se credenciais e Collections são carregadas corretamente.

```bash
# Executar geracao de MD
python MD_GenerationV3.py
```

**Passos**:
1. Abrir ⚙️ Configurações
2. Preencher Management Key e API Key
3. Selecionar modelo Grok
4. Fechar e reabrir app
5. Verificar se configuracoes foram salvas

**Resultado esperado**:
- ✅ Collections listadas no dropdown
- ✅ Credenciais restauradas após reinício
- ✅ Logs mostram: `[HH:MM:SS] ✅ X Collection(s) encontrada(s)`

### Teste 2: Geracao de Markdown

**Objetivo**: Validar geração de keywords e arquivos .md.

**Passos**:
1. Selecionar arquivo JSON de teste
2. Selecionar diretório de saída
3. (Opcional) Marcar "do not chunk JSON objects"
4. Clicar em "Gerar Arquivos MD"
4. Observar progresso em tempo real
5. Aguardar conclusão (~2-5 min)
6. Abrir diretório de saída e inspecionar arquivos .md

**Resultado esperado**:
- ✅ Arquivos .md criados no diretório
- ✅ Arquivos .md com conteudo puro
- ✅ Arquivos _metadata.json para cada MD
- ✅ Keywords contextuais (não genéricas)
- ✅ Conteúdo chunking adequado (~2048 chars)
- ✅ Logs mostram: `[HH:MM:SS] 🎉 ARQUIVOS MD GERADOS COM SUCESSO!`

**Validacao de Keywords**:
```bash
# Verificar keywords geradas nos metadados
cd <diretorio_saida>
grep "palavras-chave" *_metadata.json | head -10
```

Boas keywords: `art. 317 CLT`, `Lei 9.394/1996`, `Súmula 374 TST`  
Ruins (genéricas): `CLT`, `direito`, `legislação`

### Teste 3: Upload para Collection (V3)

**Objetivo**: Confirmar upload e indexação na Collection.

**Passos**:
1. Executar `python CollectionUploaderV3.py`
2. Selecionar ou criar Collection em Configuracoes
3. Selecionar arquivos MD ou pasta de saida
4. Clicar em "Upload para Collection"
5. Observar progresso
6. Aguardar conclusao (~2-5 min)
7. Verificar janela de feedback final

**Resultado esperado**:
- ✅ Upload sem erros
- ✅ Logs mostram: `[HH:MM:SS] ✅ Upload concluido!`
- ✅ Número de documentos enviados correto

### Teste 4: Verificacao no xAI Console

**Objetivo**: Confirmar documentos indexados corretamente.

**Passos**:
1. Abrir [console.x.ai](https://console.x.ai)
2. Navegar para sua Collection
3. Verificar contagem de documentos
4. Testar busca rápida por termo (ex: "professor")
5. Verificar metadados de documentos

**Resultado esperado**:
- ✅ Contagem de docs corresponde ao upload
- ✅ Status: "Ready" ou "Processing"
- ✅ Busca retorna resultados relevantes
- ✅ Metadados visíveis e corretos

### Teste 5: Busca de Precedentes

**Objetivo**: Validar busca semântica no Search App.

```bash
python PrecedentSearchApp.py
```

**Passos**:
1. Configurar credenciais
2. Selecionar Collection no dropdown
3. Fazer consulta: "precedentes sobre insalubridade"
4. Verificar resposta do Grok
5. Testar mudança de collection durante conversa ativa (deve exibir modal de confirmação)

**Resultado esperado**:
- ✅ Grok retorna precedentes relevantes da collection selecionada
- ✅ Cita números de processo
- ✅ Fundamenta com base nos documentos
- ✅ Resposta específica ao domínio trabalhista
- ✅ Sem collection: exibe alerta e continua chat sem contexto
- ✅ Troca de collection com conversa ativa: pede confirmação e reseta chat

---

## Diagnósticos de Collection

### Ferramenta 1: Verificar Schema

Verifica quais campos de metadados estão definidos.

```bash
python check_collection_schema.py <management_key> <collection_id>
```

**Saída esperada**:
```
🔍 Checking xAI Collection Schema
======================================================================

✅ Collection found!
   Name: Precedentes Trabalhistas
   ID: col_xxxxx
   Created: 2024-01-15

📋 Defined Metadata Fields (6):
----------------------------------------------------------------------
   ✅ categoria                       (text)
   ✅ reclamada                       (text)
   ✅ numero_processo                 (text)
   ✅ data_publicacao                 (date)
   ✅ tipo_acao                       (text)
   ✅ palavras-chave                  (array)

⚙️  Collection Settings:
----------------------------------------------------------------------
   Chunk Size: 2048
   Chunk Overlap: 256
   Embedding Model: default

💡 Recommendations:
======================================================================
✅ All recommended fields are defined!
   Your Collection is properly configured for uploads
```

**Problemas comuns**:
- ❌ Campos faltando → Adicione no xAI Console
- ❌ Tipos incorretos → Recrie Collection
- ❌ Chunk size muito grande → Use 1024 ou 2048

### Ferramenta 2: Monitorar Processamento

Monitora status de documentos sendo processados.

```bash
# Check único
python check_processing_status.py <management_key> <collection_id>

# Modo monitor (atualiza a cada 30s)
python check_processing_status.py <management_key> <collection_id> --monitor
```

**Saída esperada**:
```
🔍 Checking xAI Collection Processing Status
======================================================================
Collection ID: col_xxxxx
Timestamp: 2024-01-15 14:30:00

✅ Collection: Precedentes Trabalhistas
   Created: 2024-01-15 10:00:00
   Updated: 2024-01-15 14:25:00

⚙️  Embedding Settings:
   Model: default
   Chunk Size: 2048

📄 Fetching documents...
✅ Found 64 documents

📊 Document Status Summary:
----------------------------------------------------------------------
   ✅ completed         :  64 documents
   ⏳ processing        :   0 documents
   ❌ failed            :   0 documents

💡 Diagnosis:
======================================================================
✅ ALL DOCUMENTS PROCESSED SUCCESSFULLY!
   Your Collection is ready to use for search.
```

**Estados possíveis**:
- ✅ `completed`: Documento indexado e pronto
- ⏳ `processing`: Aguardando embedding
- ❌ `failed`: Erro no processamento
- ⏸️ `pending`: Na fila

---

## Tempos de Processamento

### O que é Normal?

| Fase | Pequeno (<100 docs) | Médio (100-500 docs) | Grande (>500 docs) |
|------|-------------------|---------------------|-------------------|
| **Geração MD** | 2-5 min | 5-15 min | 15-45 min |
| **Upload** | 2-5 min | 10-20 min | 30-60 min |
| **Embedding** | 15-30 min | 30-90 min | 1-3 horas |
| **Total** | 20-40 min | 45-120 min | 2-4 horas |

### Quando Suspeitar de Problema?

**Normal** (aguarde):
- ⏳ Processing < 1 hora para batches pequenos
- ⏳ Alguns docs "completed", outros "processing"
- ⏳ Progresso visível entre checks

**Preocupante** (investigue):
- ⚠️ Processing > 1 hora sem progresso
- ⚠️ Todos docs stuck em "processing"
- ⚠️ Erros no console log

**Bug** (contate suporte):
- 🐛 Processing > 2 horas estagnado
- 🐛 Docs em estado "failed" sem explicação
- 🐛 Collection inacessível após 3+ horas

### Por que Embedding É Lento?

1. **Modelo compute-intensive**: Cada chunk processa em ~1-2s
2. **Queue processing**: Outros usuários na frente
3. **Batch optimization**: xAI agrupa para eficiência
4. **Horário de pico**: 9am-5pm ET = mais lento

**Dica**: Upload fora de horário de pico para processar mais rápido.

---

## Solução de Problemas

### Erro: "Management Key inválida"

**Causa**: Key incorreta, expirada ou sem permissões.

**Solução**:
1. Verifique se copiou chave completa (sem espaços)
2. Confirme que key pertence à Collection correta
3. Regenere key no xAI Console se necessário
4. Verifique permissões da key

### Erro: "Collection não encontrada"

**Causa**: Collection ID incorreto ou Collection foi deletada.

**Solução**:
1. Verifique Collection ID no xAI Console
2. Recarregue lista de Collections na UI
3. Confirme que Management Key tem acesso à Collection

### Erro: "Grok keyword generation failed"

**Causa**: Rate limit, timeout ou API Key inválida.

**Solução**:
1. Verifique API Key do Grok
2. Aguarde 1-2 minutos e tente novamente
3. Use modelo mais simples (grok-beta em vez de grok-2-1212)
4. Fallback: Sistema usa apenas categoria como keyword

### Upload lento ou travado

**Causa**: Queue na API, rede lenta, batch muito grande.

**Solução**:
1. Aguarde até 60 minutos antes de preocupar
2. Use check_processing_status.py para monitorar
3. Tente upload em horário fora de pico
4. Divida batch grande em lotes menores (50-100 docs)

### Keywords genéricas ("CLT", "direito")

**Causa**: Modelo Grok não está sendo específico.

**Solução**:
1. Use grok-2-1212 (melhor qualidade)
2. Verifique prompt de keywords no código
3. Aumente temperature para 0.4-0.5
4. Valide manualmente alguns arquivos .md

### Busca não retorna resultados relevantes

**Causa**: Embeddings ruins, metadados incorretos, consulta muito genérica.

**Solução**:
1. Reformule consulta com termos mais específicos
2. Use filtros de metadados (empresa, data)
3. Aumente top_k (padrão: 5 → tente 10)
4. Verifique se documentos foram indexados (xAI Console)
5. Recrie Collection se embeddings estiverem ruins

---

## Ferramentas de Diagnóstico

### check_collection_schema.py

**Uso**:
```bash
python check_collection_schema.py <management_key> <collection_id>
```

**Fornece**:
- Lista de campos de metadados definidos
- Config de chunk size e embedding model
- Recomendações de campos faltando

### check_processing_status.py

**Uso**:
```bash
# Check único
python check_processing_status.py <management_key> <collection_id>

# Modo monitor
python check_processing_status.py <management_key> <collection_id> --monitor --interval 60
```

**Fornece**:
- Status de cada documento (processing, completed, failed)
- Tempo de processamento
- Diagnóstico (normal vs. bug)
- Recomendações

### diagnose_xai_upload.py

_(Se existir no repositório)_

**Uso**:
```bash
python diagnose_xai_upload.py <api_key>collection_id>
```

**Fornece**:
- Teste de conectividade com xAI API
- Validação de credenciais
- Teste de upload de documento simples
- Diagnóstico de headers (Cloudflare)

---

## Checklist de Validação

### Pré-Upload
- [ ] Arquivos JSON estão no formato correto
- [ ] Todos os campos obrigatórios preenchidos
- [ ] Collection criada e configurada no xAI Console
- [ ] Credenciais (API Key + Management Key) válidas
- [ ] Diretório de saída criado e acessível

### Pós-Upload
- [ ] Todos os arquivos .md foram criados
- [ ] Keywords geradas são contextuais (não genéricas)
- [ ] Upload concluído sem erros
- [ ] Documentos visíveis no xAI Console
- [ ] Status "completed" para todos (ou aguardar)

### Validação de Busca
- [ ] Precedente Search App conecta à Collection
- [ ] Busca retorna resultados relevantes
- [ ] Grok cita números de processo
- [ ] Filtros por metadados funcionam
- [ ] Respostas são específicas ao domínio trabalhista

---

## Contato para Suporte

**xAI Support**:
- Email: support@x.ai
- Console: [console.x.ai](https://console.x.ai)
- Docs: [docs.x.ai](https://docs.x.ai)

**Repositório**:
- Issues: GitHub Issues (se repositório público)
- Pull Requests: Contribuições bem-vindas

---

**Última atualização**: 2026-02-11  
**Versão do sistema**: 2.1
