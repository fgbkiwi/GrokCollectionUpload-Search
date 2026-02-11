# 📖 README - Collection Uploader V2 UI

**Sistema completo de processamento e upload de sentenças trabalhistas para xAI Collections com geração inteligente de keywords via Grok LLM.**

---

## 🎯 Visão Geral

Interface gráfica Flet que:
1. Processa arquivos JSON de sentenças trabalhistas
2. Gera keywords contextuais usando Grok LLM (não regex)
3. Cria arquivos Markdown com YAML front matter
4. Faz upload direto para xAI Collections

**Público-Alvo**: Juízes do TRT-10, pesquisadores jurídicos, profissionais do Direito do Trabalho.

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.7+
- Chave de API xAI (Grok)
- Management Key xAI (Collections)

### Dependências

```bash
pip install -r requirements_uploader_ui.txt
```

**Conteúdo de `requirements_uploader_ui.txt`:**
```
flet>=0.23.0
requests>=2.31.0
```

---

## 💻 Uso

### Execução

```bash
python CollectionUploaderV2UI.py
```

### Workflow Completo

#### 1. Configuração Inicial (⚙️)

Abra o diálogo de configurações clicando no ícone de engrenagem:

**a) Configurar Credenciais**
- **Management Key**: Chave para gerenciar Collections
- **API Key**: Chave para usar Grok LLM

**b) Carregar Collections**
- Clique em "Carregar Collections"
- Selecione a Collection desejada no dropdown

**c) Atualizar Modelos Grok**
- Clique em "Atualizar Modelos"
- Selecione o modelo (padrão: primeiro disponível)

**d) Aparência**
- Ative/desative Dark Mode conforme preferência

#### 2. Processar Sentenças

**a) Selecionar Arquivos JSON**
- Botão "Selecionar Arquivos JSON"
- Escolha um ou mais arquivos
- Formato esperado: array de objetos com campos obrigatórios

**b) Escolher Pasta de Saída**
- Botão "Selecionar Pasta de Saída"
- Defina onde os MDs serão salvos

**c) Gerar Arquivos MD**
- Clique em "Gerar Arquivos MD"
- Aguarde processamento (feedback em tempo real)
- Estatísticas exibidas ao final

**d) Upload para Collection**
- Clique em "Upload para Collection"
- Monitore progresso no log
- Sucesso/falhas reportados ao final

---

## 📂 Estrutura de Dados

### Entrada (JSON)

**Campos Obrigatórios:**

```json
{
  "categoria": "HORAS EXTRAORDINÁRIAS",
  "reclamada": "Empresa XYZ LTDA",
  "conteudo": "Fundamentação jurídica completa...",
  "numero_processo": "0000123-45.2023.5.10.0009",
  "data_publicacao": "2023-06-15",
  "tipo_acao": "Reclamação Trabalhista"
}
```

### Saída (Markdown)

**Estrutura dos Arquivos:**

```markdown
---
categoria: HORAS EXTRAORDINÁRIAS
reclamada: Empresa XYZ LTDA
numero_processo: 0000123-45.2023.5.10.0009
data_publicacao: 2023-06-15
tipo_acao: Reclamação Trabalhista
palavras-chave: art. 59 CLT, adicional 50%, jornada extraordinária, horas extras
---
# HORAS EXTRAORDINÁRIAS

[Parte 1 de 2]

[Conteúdo da fundamentação...]
```

**Naming Convention:**
- Arquivo único: `0001_0000123_45_2023_5_10_0009_HORAS_EXTRAORDINARIAS.md`
- Com chunks: `0001_0000123_45_2023_5_10_0009_HORAS_EXTRAORDINARIAS_part01.md`

---

## 🔧 Funcionalidades

### ✅ Geração de Keywords Inteligente

**Método**: LLM-based (Grok) com prompt específico para jurisprudência trabalhista

**Prompt Pattern:**
```
Analise o seguinte texto jurídico trabalhista e extraia até 10 palavras-chave relevantes.
Foque em termos jurídicos, conceitos trabalhistas, leis citadas (CLT, Súmulas), e temas principais.
```

**Temperatura**: 0.3 (baixa para consistência)

**Fallback**: Se API falhar, retorna keywords básicas (categoria + "clt" + "trabalhista")

**Exemplo de Output:**
- ✅ `art. 59 CLT`, `Súmula 437 TST`, `adicional noturno`
- ❌ ~~`legislacao`~~, ~~`direito`~~, ~~`artigo_clt`~~ (genéricos - evitados)

### ✅ Chunking Adaptativo

**Parâmetros (baseados em análise do corpus):**
- **Tamanho**: 2048 caracteres (~512 tokens)
- **Overlap**: 256 caracteres (12.5%)
- **Quebra**: Em fim de sentença (`.`, `!`, `?`)

**Rationale:** 90.9% das sentenças cabem em 1 chunk; overlap preserva contexto jurídico.

### ✅ Upload Direto para Collections

**Endpoint**: `https://management-api.x.ai/v1/collections/{collection_id}/documents`

**Método**: Multipart form-data
- `name`: Nome do arquivo (ASCII-safe)
- `content_type`: `text/markdown`
- `fields`: JSON com metadata (alinhado ao schema da Collection)
- `data`: Conteúdo do arquivo

**Retry Logic**: 3 tentativas com backoff exponencial (2s, 4s, 8s)

---

## 🔑 Schema de Metadata

**Campos da Collection "Sentenças_de_Conhecimento":**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `categoria` | String | Sim | Categoria trabalhista |
| `reclamada` | String | Não | Nome da empresa reclamada |
| `numero_processo` | String | Sim | Número único do processo |
| `data_publicacao` | String | Não | Data de publicação (YYYY-MM-DD) |
| `tipo_acao` | String | Sim | Tipo de ação judicial |
| `palavras-chave` | String | Não | Keywords separadas por vírgula |

**⚠️ Importante**: O campo é `palavras-chave` (com hífen), **não** `keywords`.

---

## 🐛 Troubleshooting

### ❌ Erro 500: "Unknown field 'keywords'"

**Causa**: Versão do código usa nome de campo incorreto.

**Solução**:
1. Atualize para commit `682d107` ou posterior
2. Verifique que front matter usa `palavras-chave:`
3. Re-gere MDs se necessário

### ❌ Erro 500: "Unknown field 'original_filename'"

**Causa**: Código adiciona campo extra não definido no schema.

**Solução**: Atualizado em commit `682d107` - campo removido.

### ❌ Collections dropdown vazio

**Diagnóstico - Verifique no log**:
- Endpoint testado: `https://management-api.x.ai/v1/collections`
- Status HTTP: deve ser 200
- Formato da resposta: lista ou objeto com chave `data`/`collections`

**Soluções**:
1. Conferir Management Key (não confundir com API Key)
2. Tentar múltiplos endpoints (feature automática do código)
3. Verificar logs para erros de autenticação

### ❌ Modelos não carregam

**Endpoint**: `https://api.x.ai/v1/models`

**Soluções**:
1. Usar API Key (não Management Key)
2. Verificar quota/limite de API
3. Conferir conectividade (timeout 10s configurado)

### ❌ Botão "Gerar MD" desabilitado

**Requisitos**:
- ✅ JSON(s) selecionado(s)
- ✅ Pasta de saída selecionada
- ✅ API Key configurada

### ❌ Botão "Upload" desabilitado

**Requisitos**:
- ✅ MDs gerados (ou pasta com MDs existentes)
- ✅ Collection selecionada
- ✅ Management Key configurada

---

## 📊 Estatísticas

**Exemplo de Output Final:**

```
======================================================================
📊 ESTATÍSTICAS DO PROCESSAMENTO
======================================================================
Total de sentenças processadas:     25
Total de arquivos MD criados:       47
Categorias únicas:                  8
Tipos de ação únicos:              2
======================================================================

======================================================================
☁️ Upload concluído!
   Sucesso: 45
   Falhas: 2
======================================================================
```

---

## 🔄 Migração de Versões Anteriores

### De CollectionUploader.py (V1)

| Mudança | V1 | V2 UI |
|---------|-----|-------|
| **Interface** | CLI (argumentos) | GUI (Flet) |
| **Keywords** | Regex fixos | Grok LLM contextual |
| **Config** | Argumentos ou JSON manual | Diálogo de configuração |
| **Upload** | Passo separado | Integrado na UI |

### De CollectionUploaderUI.py (V1 UI - Deprecated)

**Melhorias no V2 UI:**
- ✅ Seleção dinâmica de Collections (carrega via API)
- ✅ Seleção dinâmica de Modelos (carrega via API)
- ✅ Upload direto (não usa etapa intermediária de Files API)
- ✅ Persistência de configuração em `config.json`
- ✅ Dark Mode
- ✅ Metadata fields corretos (`palavras-chave`)

---

## 📚 Arquivos do Projeto

### Scripts Principais

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| [CollectionUploaderV2UI.py](CollectionUploaderV2UI.py) | Interface gráfica Flet | ✅ Atual |
| [CollectionUploaderV2.py](CollectionUploaderV2.py) | CLI uploader (sem UI) | ✅ Atual |
| [PrecedenteSearchApp.py](PrecedenteSearchApp.py) | App de busca semântica | ✅ Atual |

### Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [QUICKSTART_V2UI.md](QUICKSTART_V2UI.md) | Guia rápido de uso |
| [README_V2UI.md](README_V2UI.md) | Este arquivo (referência completa) |
| [CHANGELOG_2026-01-31.md](CHANGELOG_2026-01-31.md) | Histórico de mudanças |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Instruções para AI assistants |

### Exemplos

| Diretório | Conteúdo |
|-----------|----------|
| [sentencas_md_test_sample/](sentencas_md_test_sample/) | 3 exemplos de MDs gerados |
| [MDs_output/](MDs_output/) | Saída de processamento (ignorado no Git) |

---

## 🔐 Segurança

- ✅ Credenciais armazenadas em `config.json` (no `.gitignore`)
- ✅ Campos de senha com opção "reveal password"
- ✅ Management Key ≠ API Key (separação de responsabilidades)

**⚠️ Não commite `config.json` no repositório!**

---

## 📞 Suporte

- **Issues**: Relate bugs ou solicite features no repositório GitHub
- **Documentação Técnica**: Consulte [.github/copilot-instructions.md](.github/copilot-instructions.md)
- **Exemplos de MDs**: [sentencas_md_test_sample/](sentencas_md_test_sample/)

---

## ✅ Checklist de Uso

- [ ] Python 3.7+ instalado
- [ ] Dependências instaladas (`pip install -r requirements_uploader_ui.txt`)
- [ ] Management Key xAI obtida
- [ ] API Key xAI (Grok) obtida
- [ ] Collection criada na xAI (com schema correto)
- [ ] Arquivos JSON de sentenças preparados
- [ ] Executar `python CollectionUploaderV2UI.py`
- [ ] Configurar credenciais (⚙️)
- [ ] Carregar Collections e Modelos
- [ ] Processar arquivos JSON → MDs
- [ ] Upload para Collection
- [ ] Verificar estatísticas e logs

---

**Desenvolvido para TRT-10 | Sistema de Busca Semântica de Precedentes Trabalhistas**
