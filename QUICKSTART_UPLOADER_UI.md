# 🚀 Guia Rápido - Collection Uploader UI

## Início Rápido (3 minutos)

### 1. Instalação
```bash
pip install flet requests
```

### 2. Executar
```bash
python CollectionUploaderUI.py
```

### 3. Configurar
- **Management Key**: Cole a chave da xAI Collection
- **API Key**: Cole a chave da API Grok
- **Modelo**: Deixe `grok-beta` (mais rápido e econômico)
- Clique **"Carregar Collections"**
- Selecione sua collection

### 4. Processar
- **Selecionar Arquivos JSON**: Escolha seus arquivos
- **Selecionar Pasta de Saída**: Onde salvar os MDs
- Clique **"Gerar Arquivos MD"**
- *(Opcional)* Revise os MDs gerados
- Clique **"Upload para Collection"**

## 📸 Preview da Interface

```
┌─────────────────────────────────────────────────────────────┐
│  Collection Uploader - xAI Collections                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ⚙️ Configurações                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Management Key: ********************* [👁️] [Carregar] │  │
│  │ Collection: [Precedentes Trabalhistas ▼]              │  │
│  │ API Key: *************************** [👁️]             │  │
│  │ Modelo: [grok-beta ▼]                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  📁 Seleção de Arquivos                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [Selecionar Arquivos JSON]                            │  │
│  │ Arquivos: • sentencas1.json                           │  │
│  │           • sentencas2.json                           │  │
│  │ [Selecionar Pasta de Saída]                           │  │
│  │ Pasta: /home/user/sentencas_md                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  🚀 Ações                                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [Gerar Arquivos MD] [Upload para Collection]          │  │
│  │ [████████████████████░░░░░░] 80%                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  📊 Log de Execução                                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [14:32:15] 🚀 Iniciando geração de arquivos MD...     │  │
│  │ [14:32:16] 📄 Processando: sentencas1.json            │  │
│  │ [14:32:16]    25 sentença(s) encontrada(s)            │  │
│  │ [14:32:20]    ⏳ Processadas: 10/25                    │  │
│  │ [14:32:25] ✅ Geração de arquivos MD concluída!       │  │
│  │ [14:32:25] 📊 Total de arquivos MD criados: 64        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Recursos Principais

### ✅ Multi-seleção de JSON
Selecione quantos arquivos JSON quiser de uma vez

### 🤖 Keywords com IA
Grok analisa cada sentença e extrai keywords relevantes automaticamente

### 📊 Feedback em Tempo Real
Log com timestamps mostra cada etapa do processo

### 🔄 Ações Separadas
Gere MDs primeiro, revise, e só então faça upload

### 🎨 Interface Intuitiva
Botões desabilitados até que todos os campos necessários estejam preenchidos

## 📝 Exemplo de Output

### Log durante Geração
```
[14:32:15] ==================================================
[14:32:15] 🚀 Iniciando geração de arquivos MD...
[14:32:16] 📄 Processando: sentencas_exemplo.json
[14:32:16]    25 sentença(s) encontrada(s)
[14:32:20]    ⏳ Processadas: 5/25
[14:32:25]    ⏳ Processadas: 10/25
[14:32:30]    ⏳ Processadas: 15/25
[14:32:35]    ⏳ Processadas: 20/25
[14:32:40] ✅ Geração de arquivos MD concluída!
[14:32:40] ==================================================
[14:32:40] 📊 ESTATÍSTICAS DO PROCESSAMENTO
[14:32:40] ==================================================
[14:32:40] Total de sentenças processadas:     25
[14:32:40] Total de arquivos MD criados:       64
[14:32:40] Categorias únicas:                  18
[14:32:40] Tipos de ação únicos:               3
[14:32:40] ==================================================
```

### Log durante Upload
```
[14:35:10] ==================================================
[14:35:10] ☁️ Iniciando upload para Collection...
[14:35:15] ⏳ Uploaded: 10/64
[14:35:25] ⏳ Uploaded: 20/64
[14:35:35] ⏳ Uploaded: 30/64
[14:35:45] ⏳ Uploaded: 40/64
[14:35:55] ⏳ Uploaded: 50/64
[14:36:05] ⏳ Uploaded: 60/64
[14:36:10] ==================================================
[14:36:10] ✅ Upload concluído!
[14:36:10]    Sucesso: 64
[14:36:10]    Falhas: 0
[14:36:10] ==================================================
```

## ⚡ Dicas Pro

### 1. Use grok-beta
Mais rápido e econômico para keywords

### 2. Teste com Poucos Arquivos
Comece com 1-2 JSONs para validar

### 3. Revise os MDs
Abra a pasta de saída antes do upload

### 4. Monitore o Log
Acompanhe o progresso em tempo real

### 5. Upload em Lotes
Para muitos arquivos, divida em sessões

## 🔗 Próximos Passos

Após processar e fazer upload:
1. Acesse [xAI Console](https://console.x.ai/)
2. Configure metadados da Collection
3. Use `PrecedenteSearchApp.py` para buscar

## 📚 Documentação Completa

- **README_UPLOADER_UI.md**: Documentação detalhada
- **README.md**: Visão geral do sistema
- **CollectionUploader.py**: Script CLI original

---

**Pronto para começar? Execute `python CollectionUploaderUI.py`**
