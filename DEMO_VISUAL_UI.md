# 🎨 Demonstração Visual - Collection Uploader UI

## 📸 Layout da Interface

```
╔═══════════════════════════════════════════════════════════════════╗
║          Collection Uploader - xAI Collections                    ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ⚙️ Configurações                                                ║
║  ┌───────────────────────────────────────────────────────────┐   ║
║  │ Management Key (xAI Collection)                          │   ║
║  │ ┌─────────────────────────────────────┐ [👁️] [Carregar] │   ║
║  │ │ ********************* (oculto)      │                  │   ║
║  │ └─────────────────────────────────────┘                  │   ║
║  │                                                           │   ║
║  │ Collection para Upload                                   │   ║
║  │ ┌─────────────────────────────────────────────────────┐  │   ║
║  │ │ [Precedentes Trabalhistas (a3b8c9d1...) ▼]          │  │   ║
║  │ └─────────────────────────────────────────────────────┘  │   ║
║  │                                                           │   ║
║  │ API Key (Grok)                                           │   ║
║  │ ┌─────────────────────────────────────┐ [👁️]            │   ║
║  │ │ ************************* (oculto)  │                  │   ║
║  │ └─────────────────────────────────────┘                  │   ║
║  │                                                           │   ║
║  │ Modelo para Geração de Keywords                          │   ║
║  │ ┌─────────────────────────┐                              │   ║
║  │ │ [grok-beta ▼]          │                              │   ║
║  │ └─────────────────────────┘                              │   ║
║  └───────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  📁 Seleção de Arquivos                                          ║
║  ┌───────────────────────────────────────────────────────────┐   ║
║  │ [📂 Selecionar Arquivos JSON]                            │   ║
║  │                                                           │   ║
║  │ Arquivos selecionados:                                   │   ║
║  │ • sentencas_lote_1.json                                  │   ║
║  │ • sentencas_lote_2.json                                  │   ║
║  │ • sentencas_adicional.txt                                │   ║
║  │                                                           │   ║
║  │ [📁 Selecionar Pasta de Saída]                           │   ║
║  │                                                           │   ║
║  │ Pasta: /home/user/output/sentencas_md                    │   ║
║  └───────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  🚀 Ações                                                         ║
║  ┌───────────────────────────────────────────────────────────┐   ║
║  │ [📝 Gerar Arquivos MD]  [☁️ Upload para Collection]      │   ║
║  │                                                           │   ║
║  │ [████████████████████████████░░░░░░░░░░] 75%            │   ║
║  └───────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  📊 Log de Execução                                              ║
║  ┌───────────────────────────────────────────────────────────┐   ║
║  │ [14:23:10] ================================================ │   ║
║  │ [14:23:10] 🚀 Iniciando geração de arquivos MD...         │   ║
║  │ [14:23:11] 📄 Processando: sentencas_lote_1.json         │   ║
║  │ [14:23:11]    50 sentença(s) encontrada(s)               │   ║
║  │ [14:23:15]    ⏳ Processadas: 10/50                       │   ║
║  │ [14:23:20]    ⏳ Processadas: 20/50                       │   ║
║  │ [14:23:25]    ⏳ Processadas: 30/50                       │   ║
║  │ [14:23:30]    ⏳ Processadas: 40/50                       │   ║
║  │ [14:23:35] ✅ Geração de arquivos MD concluída!          │   ║
║  │ [14:23:35] ================================================ │   ║
║  │ [14:23:35] 📊 ESTATÍSTICAS DO PROCESSAMENTO              │   ║
║  │ [14:23:35] ================================================ │   ║
║  │ [14:23:35] Total de sentenças processadas:     50        │   ║
║  │ [14:23:35] Total de arquivos MD criados:       128       │   ║
║  │ [14:23:35] Categorias únicas:                  23        │   ║
║  │ [14:23:35] Tipos de ação únicos:               4         │   ║
║  │ [14:23:35] ================================================ │   ║
║  └───────────────────────────────────────────────────────────┘   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## 🎬 Fluxo de Uso Passo-a-Passo

### Tela Inicial (Campos Vazios)

```
⚙️ Configurações
├─ Management Key: [         ] (desabilitado para reveal) [Carregar]
├─ Collection:     [         ] (dropdown desabilitado)
├─ API Key:        [         ] (desabilitado para reveal)
└─ Modelo:         [grok-beta▼] (padrão)

📁 Seleção de Arquivos
├─ [Selecionar Arquivos JSON]
└─ [Selecionar Pasta de Saída]

🚀 Ações
├─ [Gerar Arquivos MD] (DESABILITADO - falta info)
└─ [Upload para Collection] (DESABILITADO - sem MDs)

📊 Log: (vazio)
```

### Após Configurar Keys

```
⚙️ Configurações
├─ Management Key: [***************] 👁️ [Carregar] ✅
├─ Collection:     [Precedentes... ▼] (lista carregada)
├─ API Key:        [**************] 👁️ ✅
└─ Modelo:         [grok-beta ▼] ✅

📁 Seleção de Arquivos
├─ [Selecionar Arquivos JSON]
└─ [Selecionar Pasta de Saída]

🚀 Ações
├─ [Gerar Arquivos MD] (DESABILITADO - falta arquivos)
└─ [Upload para Collection] (DESABILITADO - sem MDs)

📊 Log:
[14:20:05] 🔄 Carregando collections disponíveis...
[14:20:06] ✅ 3 collection(s) encontrada(s)
```

### Após Selecionar Arquivos

```
⚙️ Configurações
[Tudo configurado] ✅

📁 Seleção de Arquivos
├─ [Selecionar Arquivos JSON] ✅
│  Arquivos selecionados:
│  • sentencas1.json
│  • sentencas2.json
└─ [Selecionar Pasta de Saída] ✅
   Pasta: /home/user/output/md

🚀 Ações
├─ [Gerar Arquivos MD] (HABILITADO - pronto!) 🟢
└─ [Upload para Collection] (DESABILITADO - sem MDs)

📊 Log: [aguardando ação...]
```

### Durante Geração de MDs

```
🚀 Ações
├─ [Gerar Arquivos MD] (PROCESSANDO...) ⏳
└─ [Upload para Collection] (DESABILITADO)

[████████████████░░░░░░░░░░] 65%

📊 Log:
[14:25:10] ==================================================
[14:25:10] 🚀 Iniciando geração de arquivos MD...
[14:25:11] 📄 Processando: sentencas1.json
[14:25:11]    25 sentença(s) encontrada(s)
[14:25:15]    ⏳ Processadas: 5/25
[14:25:20]    ⏳ Processadas: 10/25
[14:25:25]    ⏳ Processadas: 15/25 << ATUAL
[14:25:30]    ⏳ Processadas: 20/25
```

### Após Gerar MDs

```
🚀 Ações
├─ [Gerar Arquivos MD] (COMPLETO) ✅
└─ [Upload para Collection] (HABILITADO - pronto!) 🟢

📊 Log:
[14:26:00] ✅ Geração de arquivos MD concluída!
[14:26:00] ==================================================
[14:26:00] 📊 ESTATÍSTICAS DO PROCESSAMENTO
[14:26:00] ==================================================
[14:26:00] Total de sentenças processadas:     25
[14:26:00] Total de arquivos MD criados:       64
[14:26:00] Categorias únicas:                  18
[14:26:00] Tipos de ação únicos:               3
[14:26:00] ==================================================
```

### Durante Upload

```
🚀 Ações
├─ [Gerar Arquivos MD] ✅
└─ [Upload para Collection] (UPLOADING...) ⏳

[████████████████████░░░░░░] 70%

📊 Log:
[14:28:00] ==================================================
[14:28:00] ☁️ Iniciando upload para Collection...
[14:28:05] ⏳ Uploaded: 10/64
[14:28:15] ⏳ Uploaded: 20/64
[14:28:25] ⏳ Uploaded: 30/64
[14:28:35] ⏳ Uploaded: 40/64 << ATUAL
[14:28:45] ⏳ Uploaded: 50/64
```

### Concluído

```
🚀 Ações
├─ [Gerar Arquivos MD] ✅
└─ [Upload para Collection] ✅

📊 Log:
[14:29:10] ==================================================
[14:29:10] ✅ Upload concluído!
[14:29:10]    Sucesso: 64
[14:29:10]    Falhas: 0
[14:29:10] ==================================================
```

## 🎨 Cores e Estilos

### Seções
- **Configurações**: Borda azul (#2196F3)
- **Arquivos**: Borda verde (#4CAF50)
- **Ações**: Borda laranja (#FF9800)
- **Log**: Fundo escuro (#263238)

### Botões
- **Gerar MD**: Azul (#1976D2) - Ação primária
- **Upload**: Verde (#388E3C) - Ação de confirmação
- **Carregar**: Cinza (#757575) - Ação secundária

### Estados
- ✅ **Sucesso**: Verde (#4CAF50)
- ❌ **Erro**: Vermelho (#F44336)
- ⏳ **Processando**: Laranja (#FF9800)
- 🔴 **Desabilitado**: Cinza (#BDBDBD)

## 📊 Exemplo de Keywords Geradas por IA

### Input (Sentença)
```
Categoria: HORAS EXTRAORDINÁRIAS
Conteúdo: "O reclamante laborava além da jornada normal sem 
receber o adicional previsto no art. 59 da CLT. A prova 
documental demonstra habitualidade no labor extraordinário, 
conforme Súmula 376 do TST..."
```

### Output (Keywords Grok)
```
keywords: horas_extras, art_59, clt, sumula_376, tst, 
          jornada_trabalho, adicional, labor_extraordinario,
          habitualidade, prova_documental
```

### vs. Output (Regex CLI)
```
keywords: horas_extraordinárias, artigo_clt, clt, 
          jurisprudencia_tst, sumula
```

## 🎯 Validação Visual de Campos

### Estado: Todos Desabilitados
```
❌ Gerar MD     - Falta: JSON + Pasta + API Key
❌ Upload       - Falta: MDs gerados
```

### Estado: Gerar MD Pronto
```
✅ Gerar MD     - Todos os campos preenchidos
❌ Upload       - Aguardando geração de MDs
```

### Estado: Tudo Pronto
```
✅ Gerar MD     - Disponível
✅ Upload       - MDs gerados + Collection selecionada
```

## 📱 Responsividade

- **Largura mínima**: 800px
- **Altura mínima**: 600px
- **Scroll**: Automático para conteúdo excedente
- **Log**: Limitado a 15 linhas visíveis (scroll interno)

## 🔐 Campos de Senha

```
Management Key: [xai-mgmt-abc123def456...] [👁️]
                ↓ Clique no olho
Management Key: [*********************...] [👁️]
```

## 🎉 Mensagens de Feedback

### Sucesso
```
✅ 25 collection(s) encontrada(s)
✅ Geração de arquivos MD concluída!
✅ Upload concluído!
```

### Erro
```
❌ Erro ao carregar collections: 401 Unauthorized
❌ Falha no upload de arquivo_123.md: Timeout
❌ Erro durante geração: Invalid JSON format
```

### Aviso
```
⚠️ Erro ao gerar keywords com Grok: Rate limit
   (usando keywords básicas como fallback)
```

### Informação
```
🔄 Carregando collections disponíveis...
⏳ Processadas: 15/50
📄 Processando: sentencas.json
```

---

**Interface intuitiva, feedback visual, e workflow guiado para melhor experiência do usuário!**
