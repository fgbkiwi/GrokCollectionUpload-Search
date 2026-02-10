# 🚀 Guia Rápido - Collection Uploader V2 UI

**Interface gráfica Flet para processamento e upload de sentenças trabalhistas para xAI Collections com geração de keywords via Grok LLM.**

---

## ⚡ Início Rápido

### 1. Instalar Dependências

```bash
pip install -r requirements_uploader_ui.txt
```

### 2. Executar Interface

```bash
python CollectionUploaderV2UI.py
```

---

## 📋 Fluxo de Uso

### Configuração Inicial (Ícone ⚙️)

1. **Credenciais API**
   - **Management Key**: Chave de gerenciamento da Collection (xAI)
   - **API Key**: Chave de API do Grok para geração de keywords

2. **Carregar Collections**
   - Clique em "Carregar Collections"
   - Selecione a Collection desejada no dropdown

3. **Atualizar Modelos**
   - Clique em "Atualizar Modelos"
   - Selecione o modelo Grok (padrão: primeiro da lista)

### Processamento de Arquivos

1. **Selecionar Arquivos JSON**
   - Botão "Selecionar Arquivos JSON"
   - Escolha um ou mais arquivos com sentenças

2. **Selecionar Pasta de Saída**
   - Botão "Selecionar Pasta de Saída"
   - Defina onde os MDs serão salvos

3. **Gerar Arquivos MD**
   - Botão "Gerar Arquivos MD" (habilitado após seleção)
   - Aguarde processamento com feedback em tempo real

4. **Upload para Collection**
   - Botão "Upload para Collection" (habilitado após geração)
   - Monitore progresso no log de execução

---

## 🔧 Recursos

### ✅ **Características**

- ✅ **Persistência de Config**: Chaves e preferências salvas em `config.json`
- ✅ **Seleção Dinâmica**: Collections e modelos carregados via API
- ✅ **Keywords Contextuais**: Geradas por Grok LLM (não regex)
- ✅ **Chunking Inteligente**: 2048 chars com overlap de 256 (quebra em sentenças)
- ✅ **Dark Mode**: Alternância de tema na configuração
- ✅ **Feedback em Tempo Real**: Log colorido com timestamps
- ✅ **Upload Direto**: Envia MDs com metadata para Collections

### 📊 **Estatísticas**

Ao final do processamento:
- Total de sentenças processadas
- Arquivos MD criados (chunks)
- Categorias únicas
- Tipos de ação únicos

---

## 📂 Formato de Dados

### Entrada (JSON)

```json
[
  {
    "categoria": "HORAS EXTRAORDINÁRIAS",
    "reclamada": "Empresa LTDA",
    "conteudo": "Texto da fundamentação jurídica...",
    "numero_processo": "0000123-45.2023.5.10.0009",
    "data_publicacao": "2023-06-15",
    "tipo_acao": "Reclamação Trabalhista"
  }
]
```

### Saída (Markdown com YAML Front Matter)

```markdown
---
categoria: HORAS EXTRAORDINÁRIAS
reclamada: Empresa LTDA
numero_processo: 0000123-45.2023.5.10.0009
data_publicacao: 2023-06-15
tipo_acao: Reclamação Trabalhista
palavras-chave: art. 59 CLT, horas extras, adicional 50%, jornada extraordinária
---
# HORAS EXTRAORDINÁRIAS

[Conteúdo da fundamentação...]
```

**⚠️ Mudança Importante**: O campo de keywords agora usa `palavras-chave` (não `keywords`) para compatibilidade com o schema da Collection.

---

## 🔑 Metadados da Collection

A Collection "Sentenças_de_Conhecimento" espera os seguintes campos:

- `categoria`
- `reclamada`
- `numero_processo`
- `data_publicacao`
- `tipo_acao`
- `palavras-chave` ← **Nome correto do campo**

Campos extras são rejeitados pela API xAI com erro `InvalidArgument`.

---

## 🐛 Solução de Problemas

### ❌ Erro: "Unknown field 'keywords'"

**Causa**: Versão antiga do código usando nome de campo incorreto.

**Solução**: Atualize para versão mais recente (commit `682d107` ou posterior) que usa `palavras-chave`.

### ❌ Collections não carregam

1. Verifique Management Key
2. Conferir logs no feedback: testa múltiplos endpoints
3. Endpoint correto: `https://management-api.x.ai/v1/collections`

### ❌ Modelos não aparecem

1. Verifique API Key (Grok)
2. Endpoint: `https://api.x.ai/v1/models`

### ❌ Botão "Upload" desabilitado

Requisitos:
- ✅ MD files gerados (ou pasta com MDs existentes)
- ✅ Collection selecionada
- ✅ Management Key configurada

---

## 📚 Referências

- **Script Principal**: [CollectionUploaderV2UI.py](CollectionUploaderV2UI.py)
- **Instruções AI**: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Changelog**: [CHANGELOG_2026-01-31.md](CHANGELOG_2026-01-31.md)
- **Exemplos de MDs**: [sentencas_md_test_sample/](sentencas_md_test_sample/)

---

## 💡 Diferenças vs Versões Anteriores

| Aspecto | V1 (Regex) | V2 UI (Grok LLM) |
|---------|-----------|------------------|
| **Keywords** | Genéricas (`clt`, `legislacao`) | Específicas (`art. 59 CLT`, `Súmula 437 TST`) |
| **Upload** | Passo separado manual | Integrado na UI |
| **Config** | Manual (edição JSON) | Interface gráfica |
| **Feedback** | Console/terminal | Log visual em tempo real |
| **Metadata Field** | `keywords` (incorreto) | `palavras-chave` (correto) |

---

**Pronto para começar? Execute `python CollectionUploaderV2UI.py`**
