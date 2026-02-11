# 🔍 Grok Collection Upload & Search System

**Sistema completo de indexação e busca semântica de precedentes trabalhistas usando xAI Collections e Grok LLM**

[![Python](https://img.shields.io/badge/Python-3.7+-3776AB?logo=python)](https://www.python.org)
[![xAI](https://img.shields.io/badge/xAI-Collections-000000)](https://x.ai)

---

## 📋 Sobre o Projeto

Sistema desenvolvido para o Tribunal Regional do Trabalho da 10ª Região (TRT-10) que permite:
- 📤 **Upload inteligente** de sentenças trabalhistas para xAI Collections
- 🔍 **Busca semântica** de precedentes usando Grok LLM
- 🤖 **Keywords contextuais** geradas automaticamente via IA
- 📊 **Metadados estruturados** para filtragem avançada

---

## ✨ Componentes do Sistema

### 1. **Collection Uploader UI** (Flet)
Interface gráfica para processar e fazer upload de documentos.

**Características:**
- Geração de keywords via Grok LLM (contextual, não regex)
- Chunking inteligente (2048 chars, overlap 256)
- Upload direto para xAI Collections API
- Configurações persistentes
- Feedback visual em tempo real

### 2. **Collection Uploader CLI** (Python)
Versão linha de comando para processamento em lote.

**Características:**
- Mesmo motor de processamento da UI
- Ideal para automação e scripts
- Estatísticas detalhadas
- Configuração via JSON

### 3. **Precedente Search App** (Flet)
Aplicação de busca interativa de precedentes.

**Características:**
- Interface de chat com Grok
- Busca híbrida (semântica + keywords)
- Seleção dinâmica de Collections
- Anexar arquivos ao contexto
- Busca em tempo real (Web/X)
- Temas claro/escuro

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.7+
- Conta xAI ([console.x.ai](https://console.x.ai))
- API Key (Grok) e Management Key (Collections)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/yourusername/GrokCollectionUpload-Search
cd GrokCollectionUpload-Search

# Instale dependências
pip install -r requirements_uploader_ui.txt  # Para UI
pip install -r requirements_uploader.txt     # Para CLI
pip install -r requirements_app.txt          # Para busca
```

### Uso Rápido

#### **Opção 1: Interface Gráfica (Uploader)**

```bash
python CollectionUploaderV2UI.py
```

1. Configure credenciais em ⚙️ **Configurações**
2. Selecione arquivos JSON
3. Clique em **"1. Gerar Arquivos MD"**
4. Clique em **"2. Upload para Collection"**

#### **Opção 2: Linha de Comando (Uploader)**

```bash
# Configure config.json (use config_example.json como template)
cp config_example.json config.json

# Execute
python CollectionUploaderV2.py --config config.json --input sentencas.json
```

#### **Opção 3: Busca de Precedentes**

```bash
python PrecedenteSearchApp.py
```

1. Configure em ⚙️ **Configurações**
2. Selecione Collection
3. Pergunte ao Grok sobre precedentes

---

## 📊 Formato dos Dados

### Entrada (JSON)
```json
[
  {
    "categoria": "HORAS EXTRAORDINÁRIAS",
    "reclamada": "Empresa XYZ LTDA",
    "conteudo": "Texto da fundamentação jurídica...",
    "numero_processo": "0000123-45.2023.5.10.0009",
    "data_publicacao": "2023-06-15",
    "tipo_acao": "Reclamação Trabalhista"
  }
]
```

### Saída (Markdown)
```markdown
---
categoria: HORAS EXTRAORDINÁRIAS
reclamada: Empresa XYZ LTDA
numero_processo: 0000123-45.2023.5.10.0009
data_publicacao: 2023-06-15
tipo_acao: Reclamação Trabalhista
keywords: art. 59 CLT, horas extras, banco de horas, acordo coletivo
---
# HORAS EXTRAORDINÁRIAS

[Fundamentação jurídica...]
```

---

## 🎯 Funcionalidades

### **Upload Inteligente**
- ✅ Keywords geradas por Grok (não regex)
- ✅ Chunking otimizado para embeddings
- ✅ Metadados separados do conteúdo
- ✅ Upload direto via API

### **Busca Semântica**
- ✅ Compreende significado, não só palavras
- ✅ Busca híbrida (embeddings + keywords)
- ✅ Filtros por metadados (empresa, data, tipo)
- ✅ Citação automática de processos

### **Interface Amigável**
- ✅ UI Flet moderna e responsiva
- ✅ Feedback visual em tempo real
- ✅ Configurações persistentes
- ✅ Logs detalhados com timestamps

---

## 📁 Estrutura do Projeto

```
GrokCollectionUpload-Search/
├── CollectionUploaderV2.py       # CLI uploader
├── CollectionUploaderV2UI.py     # GUI uploader (Flet)
├── PrecedenteSearchApp.py        # Busca de precedentes (Flet)
├── config_example.json           # Template de configuração
├── requirements_*.txt            # Dependências
├── check_collection_schema.py    # Diagnóstico de Collection
├── check_processing_status.py    # Monitor de processamento
├── Uploaders/
│   └── archive/                  # Scripts legados arquivados
├── docs/
│   └── archive/                  # Documentação antiga
└── MDs_output/                   # Exemplos de saída
```

---

## 🔧 Configuração

### Arquivo `config.json`

```json
{
  "grok_api_key": "xai-...",
  "management_key": "xai-mgmt-...",
  "collection_id": "col_...",
  "grok_model": "grok-beta",
  "output_dir": "./sentencas_md",
  "save_local_md": true
}
```

### Criar Collection no xAI Console

1. Acesse [console.x.ai](https://console.x.ai)
2. Crie nova Collection
3. Configure:
   - **Chunk Size**: 2048 caracteres
   - **Chunk Overlap**: 256 caracteres
   - **Embedding Model**: Padrão xAI
4. Copie Management Key e Collection ID

---

## 📚 Documentação

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Guia completo de uso
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testes e diagnósticos
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Instruções para AI agents

---

## 🛠️ Ferramentas de Diagnóstico

### Verificar Schema da Collection
```bash
python check_collection_schema.py <management_key> <collection_id>
```

### Monitorar Status de Processamento
```bash
python check_processing_status.py <management_key> <collection_id>
```

---

## ❓ Perguntas Frequentes

**Q: Como obtenho API Keys?**  
A: Acesse [console.x.ai](https://console.x.ai) → Settings → API Keys

**Q: Quanto tempo leva o processamento?**  
A: Para 100 documentos: ~30-60 minutos (embedding é lento)

**Q: Posso usar sem interface gráfica?**  
A: Sim, use `CollectionUploaderV2.py` (CLI)

**Q: Como adiciono novas sentenças?**  
A: Processe novo JSON e faça upload incremental

Mais perguntas? Consulte [USAGE_GUIDE.md](USAGE_GUIDE.md)

---

## 🔐 Segurança

- ⚠️ **Nunca** compartilhe suas API Keys
- ✅ Keys são armazenadas localmente em `app_config.json` e `config.json`
- ✅ Remova informações sensíveis antes do upload
- ✅ Conforme LGPD para dados pessoais

---

## 🚦 Status do Projeto

| Componente | Status | Versão |
|------------|--------|--------|
| Collection Uploader UI | ✅ Ativo | 2.1 |
| Collection Uploader CLI | ✅ Ativo | 2.0 |
| Precedente Search App | ✅ Ativo | 1.0 |
| SmartUploader | 📦 Arquivado | - |
| RobustUploader | 📦 Arquivado | - |

---

## 📝 Licença

Desenvolvido especificamente para uso no Tribunal Regional do Trabalho da 10ª Região.

---

## 🤝 Suporte

Para questões sobre:
- **Uso do sistema**: Consulte [USAGE_GUIDE.md](USAGE_GUIDE.md)
- **Problemas técnicos**: Consulte [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **xAI API**: Contate support@x.ai

---

**Desenvolvido para modernizar a busca de precedentes judiciais com IA** 🚀
