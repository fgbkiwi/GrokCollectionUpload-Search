# Collection Uploader V2 - Sistema Avançado com Keywords Geradas por LLM

## 🎯 Novidades da Versão 2.0

### ✅ Keywords Inteligentes Geradas por Grok
- **Análise contextual** da fundamentação jurídica
- **Extração automática** de dispositivos legais específicos (arts., parágrafos, incisos)
- **Identificação** de conceitos jurídicos relevantes (não genéricos)
- **Reconhecimento** de súmulas e jurisprudência citadas
- **Detecção** de cláusulas de normas coletivas

### ✅ Upload Direto via xAI Collections API
- **Metadados separados** do conteúdo (não incluídos nos arquivos MD)
- **Melhor aproveitamento** do chunk size
- **Embeddings mais puros** sem "ruído" de metadados
- **Upload automático** durante processamento

### ✅ Interface Flutter Profissional
- **UI amigável** com campos para configuração
- **File picker** para múltiplos arquivos JSON
- **Folder picker** para diretório de saída
- **Progresso em tempo real** com logs detalhados
- **Configurações persistentes** (salvas automaticamente)

---

## 📁 Componentes do Sistema

### 1. CollectionUploaderV2.py

Script Python com geração inteligente de keywords via LLM e upload direto.

**Uso via linha de comando:**
```bash
python CollectionUploaderV2.py --config config.json --input "Sentenças.json"
```

**Arquivo config.json:**
```json
{
  "grok_api_key": "xai-xxx",
  "management_key": "xai-mgmt-xxx",
  "collection_id": "col_xxx",
  "grok_model": "grok-beta",
  "output_dir": "./sentencas_md",
  "save_local_md": true
}
```

### 2. Flutter App (collection_uploader_app)

Aplicação desktop com interface gráfica completa.

**Executar:**
```bash
cd collection_uploader_app
flutter run -d linux  # ou windows, macos
```

---

## 🔧 Configuração Inicial

### Passo 1: Instalar Dependências Python

```bash
pip install requests
```

### Passo 2: Obter Credenciais xAI

1. **Management Key**:
   - Acesse: https://console.x.ai/
   - Vá para Settings → API Keys
   - Clique em "Generate Management Key"
   - Copie a chave

2. **API Key (Grok)**:
   - Mesma página: Settings → API Keys
   - Clique em "Generate API Key"
   - Copie a chave

3. **Collection ID**:
   - Crie uma Collection em https://console.x.ai/
   - Configure: Chunk 2048, Overlap 256
   - Copie o Collection ID

### Passo 3: Executar Flutter App

```bash
cd collection_uploader_app
flutter pub get
flutter run -d linux
```

---

## 📊 Diferenças Entre V1 e V2

| Aspecto | V1 (Anterior) | V2 (Novo) |
|---------|---------------|-----------|
| **Keywords** | Regex patterns genéricos | LLM contextual (Grok) |
| **Exemplo Keywords V1** | `clt`, `legislacao`, `artigo_clt` | `art. 317 CLT`, `LDB Lei 9.394/1996`, `instrutor vs professor` |
| **Metadados** | Incluídos no arquivo MD | Separados (via API) |
| **Upload** | Manual (usuário faz) | Automático (via API) |
| **Chunk aproveitamento** | ~90% (10% metadados) | 100% conteúdo jurídico |
| **Interface** | Linha de comando | Flutter UI profissional |

---

## 🎯 Como as Keywords São Geradas

### Prompt Enviado ao Grok:

```
Analise esta fundamentação jurídica trabalhista e extraia palavras-chave relevantes.

INSTRUÇÕES:
1. Aspectos fundamentais da controvérsia
2. Dispositivos legais ESPECÍFICOS com artigos
   - Formato: "art. 317 CLT", "arts. 461-467 CLT"
   - Leis completas: "Lei 9.394/1996 (LDB)"
3. Conceitos jurídicos relevantes (não genéricos)
   - BOM: "instrutor técnico", "equiparação salarial entre professores"
   - EVITE: "legislação", "CLT" (sem artigo)
4. Súmulas: "Súmula 374 TST"
5. Cláusulas de normas coletivas
6. Limite: 10-15 keywords
```

### Exemplo de Keywords Geradas:

**Processo 0000006-73.2023.5.10.0009 - ATIVIDADE DE PROFESSOR**

**V1 (Regex - Genérico):**
```
keywords: atividade de professor — caracterização, artigo_clt, clt, 
          legislacao, direito_sindical
```

**V2 (LLM - Contextual):**
```
keywords: atividade de professor — caracterização, instrutor vs professor,
          arts. 317-323 CLT, Lei 9.394/1996 (LDB), art. 39 §2º LDB,
          educação profissional e tecnológica, Decreto 5.154/2004,
          estabelecimento particular de ensino, categoria profissional diferenciada
```

---

## 🚀 Workflow Completo

### Via Flutter App (Recomendado)

1. **Abrir App**:
   ```bash
   cd collection_uploader_app
   flutter run -d linux
   ```

2. **Configurar Credenciais**:
   - Management Key
   - API Key (Grok)
   - Collection ID
   - Modelo: `grok-beta` (default)

3. **Selecionar Arquivos**:
   - Clique em "Arquivos JSON de Sentenças"
   - Selecione um ou múltiplos arquivos .json
   - Clique em "Diretório de Saída (MD)"
   - Selecione pasta para arquivos MD locais

4. **Iniciar Upload**:
   - Clique em "Iniciar Upload"
   - Acompanhe progresso em tempo real
   - Veja logs detalhados

### Via Linha de Comando

1. **Criar config.json**:
   ```json
   {
     "grok_api_key": "xai-xxx",
     "management_key": "xai-mgmt-xxx",
     "collection_id": "col_xxx",
     "grok_model": "grok-beta",
     "output_dir": "./sentencas_md",
     "save_local_md": true
   }
   ```

2. **Executar**:
   ```bash
   python CollectionUploaderV2.py --config config.json --input "Sentenças.json"
   ```

---

## 📈 Performance Estimada

| Volume | Keywords (LLM) | Upload (API) | Total |
|--------|----------------|--------------|-------|
| 25 sentenças | 30-60s | 10-20s | 40-80s |
| 100 sentenças | 2-4min | 40-80s | 3-5min |
| 1.000 sentenças | 20-40min | 6-12min | 26-52min |

**Nota**: Tempo de keywords aumenta com LLM, mas qualidade é muito superior.

---

## 🔍 Benefícios das Keywords Geradas por LLM

### 1. Precisão Jurídica
✅ Identifica dispositivos legais específicos
✅ Reconhece nuances da controvérsia
✅ Detecta conceitos relevantes ao caso

### 2. Melhor Recuperação
✅ Buscas encontram precedentes mais relevantes
✅ Filtros por dispositivos legais funcionam melhor
✅ Busca híbrida (semântica + keywords) otimizada

### 3. Menos Ruído
❌ Elimina keywords genéricas ("legislação", "direito")
✅ Foca em termos específicos e úteis

---

## 📝 Estrutura dos Metadados na API

```json
{
  "content": "[Texto puro da fundamentação sem metadados]",
  "metadata": {
    "categoria": "ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO",
    "reclamada": "Nome da Empresa",
    "numero_processo": "0000006-73.2023.5.10.0009",
    "data_publicacao": "2023-11-17",
    "tipo_acao": "Reclamação Trabalhista",
    "keywords": [
      "atividade de professor — caracterização",
      "instrutor vs professor",
      "arts. 317-323 CLT",
      "Lei 9.394/1996 (LDB)",
      "art. 39 §2º LDB",
      "educação profissional e tecnológica",
      "Decreto 5.154/2004",
      "estabelecimento particular de ensino"
    ]
  }
}
```

**Vantagens:**
- ✅ Conteúdo 100% aproveitado para embedding
- ✅ Metadados indexados separadamente
- ✅ Busca otimizada (semântica no content, filtros nos metadados)

---

## 🛠️ Solução de Problemas

### Erro: "Timeout ao gerar keywords"
**Solução**: Grok está sobrecarregado. Tente novamente ou aumente timeout no código.

### Erro: "Management Key inválida"
**Solução**: Verifique se copiou corretamente do xAI Console. Regenere se necessário.

### Erro: "Collection não encontrada"
**Solução**: Verifique Collection ID. Confirme que Collection foi criada no xAI Console.

### Keywords ainda genéricas
**Solução**: 
1. Use modelo mais avançado: `grok-2-1212` (mais lento mas melhor)
2. Aumente contexto enviado ao Grok (modificar código)
3. Ajuste prompt no código para sua necessidade específica

---

## 📞 Recursos Adicionais

- **xAI Console**: https://console.x.ai/
- **xAI Collections API**: https://docs.x.ai/docs/guides/using-collections/api
- **Flutter Docs**: https://docs.flutter.dev/

---

## ✅ Checklist de Uso

### Primeira Vez
- [ ] Instalar Python e dependências
- [ ] Instalar Flutter
- [ ] Obter Management Key
- [ ] Obter API Key (Grok)
- [ ] Criar Collection no xAI
- [ ] Testar com arquivo de excerto

### Uso Regular
- [ ] Abrir Flutter App
- [ ] Configurar credenciais (salvas automaticamente)
- [ ] Selecionar arquivo(s) JSON
- [ ] Selecionar diretório de saída
- [ ] Iniciar upload
- [ ] Verificar logs de sucesso

---

**Desenvolvido para modernizar a indexação de precedentes judiciais com IA.**
**Sistema de Busca Semântica de Precedentes Trabalhistas v2.0**

🎯 **Keywords Inteligentes + Upload Automático + UI Profissional**
