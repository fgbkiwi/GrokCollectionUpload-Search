# Indexador de Sentenças Trabalhistas para xAI Collections

Sistema completo para indexação de sentenças trabalhistas em xAI Collections, com interface gráfica, extração automática de metadados e upload idempotente.

## 🎯 Funcionalidades

- **Extração automática** de sentenças de arquivos docx/odt
- **Quebra inteligente** da fundamentação em tópicos temáticos
- **Detecção de metadados**: processo, data, tipo de ação, reclamada
- **Detecção PF vs PJ**: só grava nome da reclamada se pelo menos uma parte for PJ
- **Upload idempotente**: não duplica documentos já indexados
- **Catálogo local**: SQLite para rastreamento de documentos enviados
- **Interface gráfica**: UI Flet em português
- **Gestão de Collections**: criar e selecionar Collections via UI

## 📋 Requisitos

- Python 3.8+
- Credenciais xAI:
  - API Key (para upload de arquivos)
  - Management Key (para gestão de Collections)

## 🚀 Instalação

```bash
# Clone o repositório (se ainda não estiver)
cd seu-workspace

# Instale as dependências
pip install -r requirements_indexador.txt
```

## ⚙️ Configuração

### Opção 1: Variáveis de ambiente (recomendado)

```bash
export XAI_API_KEY="xai-your-api-key"
export XAI_MANAGEMENT_KEY="xai-your-management-key"
```

### Opção 2: Inserir na UI

As credenciais podem ser inseridas diretamente na interface gráfica. Elas são mantidas apenas em memória durante a execução.

## 📖 Como Usar

### 1. Inicie o aplicativo

```bash
python IndexadorSentencas.py
```

### 2. Configure as credenciais

- Insira sua **API Key** e **Management Key**
- Clique em 🔄 para carregar a lista de Collections
- Selecione uma Collection existente ou crie uma nova

### 3. Prepare seus arquivos

- Organize suas sentenças em uma pasta
- Formatos suportados: `.docx`, `.odt`
- Nomes de arquivo devem conter número CNJ: `0001234-56.2023.5.10.0009_sentenca.docx`
- Arquivos com `dsp` no nome são ignorados automaticamente (despachos)

### 4. Indexe

1. ✅ Marque o checkbox: *"Declaro que estas sentenças são públicas..."*
2. 📁 Clique em **Selecionar Pasta** e escolha a pasta com as sentenças
3. 🔍 Clique em **Varrer Arquivos** para analisar os documentos
4. ✨ Revise a tabela de documentos detectados
5. 📤 Clique em **Indexar Selecionados** para enviar à Collection

### 5. Acompanhe o progresso

- A barra de progresso mostra o andamento
- O log exibe cada documento indexado
- Documentos já indexados são pulados automaticamente

## 🔧 Estrutura do Sistema

### Módulos

```
indexador/
├── extractor.py          # Extração de sentenças de docx/odt
├── catalog.py            # Catálogo SQLite local
└── xai_uploader.py       # Cliente xAI Collections API

IndexadorSentencas.py     # Interface Flet

tests/
└── test_extractor.py     # Testes unitários
```

### Catálogo Local

O indexador mantém um banco SQLite em `~/.indexador_sentencas/catalog.db` com registro de todos os documentos enviados. Isso garante:

- ✅ **Idempotência**: reexecutar sobre a mesma pasta não duplica
- 🔍 **Rastreamento**: histórico completo de uploads
- 📊 **Estatísticas**: processos, categorias, datas

### Extração de Dados

#### Metadados Extraídos

| Campo | Descrição | Origem |
|-------|-----------|--------|
| `numero_processo` | Número CNJ | Texto ou nome do arquivo |
| `categoria` | Tópico da fundamentação | Títulos detectados |
| `data_publicacao` | Data da sentença | Texto ou metadados do arquivo |
| `reclamada` | Nome do empregador | Detecção de padrões no texto |
| `tipo_acao` | Tipo de ação | Sigla no nome do arquivo |

#### Tipo de Ação

O sistema detecta o tipo de ação pela sigla no nome do arquivo:

- `.acp.` → Ação Civil Pública
- `.ms.` → Mandado de Segurança
- `.ed.` → Embargos de Declaração
- Sem sigla → Reclamação Trabalhista (padrão)

#### Detecção de Pessoa Física vs Jurídica

O sistema detecta automaticamente se a reclamada é PF ou PJ baseado em tokens como:
- LTDA, S.A., ME, EIRELI, EPP
- Município, União, Estado
- Hospital, Banco, Cooperativa, etc.

**Regra importante**: Se ambas as partes forem pessoas físicas, o nome da reclamada **não** é gravado nos metadados (proteção de privacidade).

#### Quebra em Tópicos

A fundamentação é dividida em tópicos temáticos usando padrões de títulos:

1. Numerados: `1. TÍTULO`, `1.1 TÍTULO`
2. Com letras: `A) TÍTULO`, `A. TÍTULO`
3. Maiúsculas: `TÍTULO EM MAIÚSCULAS`
4. Bullets: `a) título`

Cada tópico vira **um documento** na Collection (não há chunking de 2048 caracteres).

Se um tópico for muito grande (>50k caracteres), ele é dividido automaticamente com overlap, preservando os mesmos metadados.

## 🧪 Testes

Execute os testes unitários:

```bash
pytest tests/
```

Ou com verbose:

```bash
pytest -v tests/
```

Os testes cobrem:
- ✅ Detecção de títulos de tópicos
- ✅ Extração de metadados
- ✅ Detecção PF vs PJ
- ✅ Ignorar despachos
- ✅ Processamento completo de arquivo sintético

## 📊 Field Definitions da Collection

Ao criar uma Collection, os seguintes campos de metadados são definidos:

```json
[
  {
    "name": "numero_processo",
    "type": "string",
    "required": true,
    "inject_into_chunk": true,
    "description": "Número do processo (formato CNJ)"
  },
  {
    "name": "categoria",
    "type": "string",
    "required": true,
    "inject_into_chunk": true,
    "description": "Categoria/tópico da fundamentação"
  },
  {
    "name": "data_publicacao",
    "type": "string",
    "required": false,
    "inject_into_chunk": false,
    "description": "Data de publicação da sentença (YYYY-MM-DD)"
  },
  {
    "name": "reclamada",
    "type": "string",
    "required": false,
    "inject_into_chunk": false,
    "description": "Nome da empresa/órgão reclamada"
  },
  {
    "name": "tipo_acao",
    "type": "string",
    "required": true,
    "inject_into_chunk": false,
    "description": "Tipo de ação trabalhista"
  }
]
```

## 🔒 Segurança e Privacidade

### API Keys

- ✅ As chaves **não** são salvas em arquivos de configuração
- ✅ Use variáveis de ambiente ou insira na UI (memória temporária)
- ❌ Nunca commite arquivos com chaves no Git

### Dados Sensíveis

- ✅ **Apenas sentenças públicas** devem ser indexadas
- ✅ O sistema **não grava** nomes de partes quando ambas são PF
- ❌ **Nunca** indexe processos em segredo de justiça
- ❌ **Nunca** indexe autos de processos em curso

### Privacidade xAI

De acordo com a documentação da xAI:
- Os dados em Collections **não são usados** para treinar modelos
- Collections são privadas por padrão

## 🐛 Troubleshooting

### Erro: "Extensão não suportada"

**Causa**: Arquivo não é docx nem odt, ou é WordPerfect (.wpd).

**Solução**: Converta o arquivo para docx ou odt antes de indexar.

### Erro: "Fundamentação não encontrada"

**Causa**: O arquivo não contém os marcadores "FUNDAMENTAÇÃO" ou "FUNDAMENTOS".

**Solução**: Verifique se o arquivo é uma sentença completa. Despachos e decisões interlocutórias podem não ter seção de fundamentação.

### Documentos marcados como "Já indexado"

**Causa**: O documento foi indexado anteriormente (baseado no hash do conteúdo).

**Solução**: Isso é o comportamento esperado (idempotência). Se você realmente quer reenviar, delete o documento da Collection pela interface da xAI e execute novamente, ou apague o catálogo local em `~/.indexador_sentencas/catalog.db`.

### Erro 429 (Rate Limit)

**Causa**: Muitas requisições em pouco tempo.

**Solução**: O sistema já implementa retries automáticos com backoff. Aguarde alguns segundos e tente novamente.

## 📝 Exemplos

### Criar Collection e Indexar Pasta

```bash
# 1. Configure variáveis de ambiente
export XAI_API_KEY="xai-xxx"
export XAI_MANAGEMENT_KEY="xai-mgmt-xxx"

# 2. Execute o indexador
python IndexadorSentencas.py

# 3. Na UI:
#    - Crie uma Collection: "Sentenças TRT10 2024"
#    - Selecione pasta: ~/Documentos/Sentencas_2024/
#    - Marque checkbox de privacidade
#    - Varre arquivos
#    - Indexe
```

### Testar com Arquivos de Exemplo

O repositório contém exemplos em Markdown na pasta `sentencas_md_test_sample/`:

```bash
# Estes arquivos já estão extraídos (formato MD)
# O indexador também pode processar docx/odt originais
ls sentencas_md_test_sample/
```

## 🔄 Compatibilidade com Fluxo Anterior

O indexador é compatível com o fluxo anterior:

- ✅ **JSON já extraído**: Se você tem um `Sentenças.json` do `Extrator.py` antigo, o indexador pode importá-lo (feature a ser implementada se necessário)
- ✅ **Markdown com frontmatter**: Arquivos MD com metadados YAML são reconhecidos
- ⚠️ **Sem double-chunking**: O indexador envia cada tópico como um documento, não faz chunks de 2048 caracteres

## 🚧 Limitações Conhecidas

- ❌ Não faz OCR de PDFs escaneados
- ❌ Não processa arquivos WordPerfect (.wpd) nativamente
- ⚠️ Detecção de PF vs PJ é baseada em heurística (pode ter falsos positivos/negativos)
- ⚠️ Títulos de tópicos em minúsculas podem não ser detectados

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique o **log de atividades** na interface
2. Execute os **testes**: `pytest -v tests/`
3. Consulte a **documentação da xAI**: https://docs.x.ai/developers/files/collections

## 📄 Licença

Este projeto é parte do sistema de busca de precedentes trabalhistas.

---

**Desenvolvido para auxiliar juízes do trabalho na indexação e busca de precedentes com xAI Collections.**
