# 📖 Guia de Uso - Collection Upload & Search System

**Guia completo para usar todos os componentes do sistema**

---

## 📋 Índice

1. [Componentes do Sistema](#componentes-do-sistema)
2. [Collection Uploader UI (Flet)](#collection-uploader-ui-flet)
3. [Collection Uploader CLI (Python)](#collection-uploader-cli-python)
4. [Precedente Search App (Flet)](#precedente-search-app-flet)
5. [Formato de Dados](#formato-de-dados)
6. [Configuração de Collections](#configuração-de-collections)
7. [Perguntas Frequentes](#perguntas-frequentes)

---

## Componentes do Sistema

Este sistema possui **3 componentes principais**:

| Componente | Interface | Função | Quando Usar |
|------------|-----------|--------|-------------|
| **MD Generation UI (V3)** | Flet (GUI) | Gerar MD + metadados | Geracao de arquivos com IA |
| **Collection Uploader UI (V3)** | Flet (GUI) | Upload de documentos | Envio com validacao de metadados |
| **Collection Uploader CLI** | Terminal | Upload de documentos | Automação, scripts, lotes grandes |
| **Precedente Search App** | Flet (GUI) | Busca de precedentes | Consultas interativas, chat com Grok |

---

## MD Generation UI (V3)

### Instalação e Execução

```bash
# Instalar dependências
pip install -r requirements_uploader_ui.txt

# Executar
python MD_GenerationV3.py
```

### Workflow Completo

#### 1. **Configuracao Inicial**

Ao abrir, clique em ⚙️ **Configurações** e preencha:

- **API Key**: xai-... (para gerar keywords com Grok)
- **Modelo Grok**: Selecione no dropdown (recomendado: grok-beta)

Clique em **"Carregar Collections"** para listar suas Collections disponíveis.

#### 2. **Selecao de Arquivos**

- **Arquivos JSON**: Clique e selecione um ou mais arquivos .json com sentenças
- **Diretório de Saída**: Escolha onde salvar os arquivos .md gerados

#### 3. **Geracao de Markdown**

Clique no botão azul **"1. Gerar Arquivos MD"**

O sistema ira:
- Ler cada sentença do JSON
- Gerar keywords contextuais via Grok LLM
- Dividir em chunks (2048 chars, overlap 256) ou gerar um unico arquivo por sentenca
- Criar arquivos .md apenas com conteudo
- Criar arquivos .json separados com metadados

**Tempo estimado**: 2-5 minutos para 25 sentenças

#### 4. **Upload para Collection (V3)**

Execute:

```bash
python CollectionUploaderV3.py
```

Clique no botao verde **"Upload para Collection"**

- Selecione ou crie uma Collection nas Configuracoes
- Aguarde upload (~2-5 minutos)
- Verifique conclusão no log
- **Recomendacao**: se houver erro HTTP 500 relacionado a proxy/CDN, use VPN durante o upload

**Resultado**: Documentos indexados na Collection prontos para busca

### Recursos da UI

- ✅ Dropdown de Collections (carrega automaticamente)
- ✅ Dropdown de Modelos (grok-beta, grok-2-1212, etc.)
- ✅ Criacao de Collection com metadados pre-definidos
- ✅ Validacao de schema de metadados
- ✅ Progresso em tempo real
- ✅ Logs com timestamps coloridos
- ✅ Configurações salvas automaticamente
- ✅ Validação de campos obrigatórios
- ✅ Feedback visual (SnackBars, diálogos)

---

## Collection Uploader CLI (Python)

### Instalação e Execução

```bash
# Instalar dependências
pip install -r requirements_uploader.txt

# Configurar
cp config_example.json config.json
# Edite config.json com suas credenciais

# Executar
python CollectionUploaderV2.py --config config.json --input sentencas.json
```

### Arquivo config.json

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

### Parâmetros da Linha de Comando

```bash
python CollectionUploaderV2.py \
  --config config.json \      # Arquivo de configuração (obrigatório)
  --input arquivo.json        # Arquivo JSON de entrada (obrigatório)
```

### Saída do Processamento

```
======================================================================
📄 PROCESSANDO ARQUIVO: sentencas.json
📁 Diretório MD local: ./sentencas_md
======================================================================

✅ 25 sentenças encontradas

📄 Processando sentença 1: HORAS EXTRAORDINÁRIAS...
   🤖 Gerando keywords com Grok...
   ✅ Keywords geradas: art. 59 CLT, horas extras, banco de horas...
   📤 Uploading chunk 1/1 para xAI Collections...
   ✅ Upload concluído: 0001_0000123_45_2023_5_10_0009_HORAS_EXTRAS

...

======================================================================
✅ PROCESSAMENTO CONCLUÍDO!
======================================================================

📊 ESTATÍSTICAS DO PROCESSAMENTO
Sentenças processadas:          25
Documentos uploaded (xAI):      64
Chunks criados:                 64
Keywords geradas (total):       320
Erros de upload:                0
Categorias únicas:              18
Tipos de ação únicos:           3
Tempo total:                    156.32s
Tempo médio por sentença:       6.25s
```

---

## Precedente Search App (Flet)

### Instalação e Execução

```bash
# Instalar dependências
pip install -r requirements_app.txt

# Executar
python PrecedenteSearchApp.py
```

### Configuração

Clique em ⚙️ **Configurações** e preencha:

- **Management Key**: Para acessar Collections
- **API Key**: Para usar Grok
- **Modelo**: Selecione (recomendado: grok-2-1212 para busca)
- **Temperature**: 0.7 (padrão) - menor = mais conservador
- **System Prompt**: Customize o comportamento do Grok

**Nota**: Code Execution está sempre ativo, permitindo ao Grok executar cálculos trabalhistas complexos (horas extras, verbas rescisórias, etc.)

**System Prompt recomendado:**
```
Você é um assistente jurídico especializado em Direito do Trabalho brasileiro. 
Analise precedentes e fundamente respostas com base na CLT, jurisprudência e 
doutrina trabalhista. SEMPRE cite o número do processo ao mencionar precedentes.
```

### Uso

1. **Selecione Collection**: Dropdown no topo (obrigatório para busca com contexto)
2. **Digite consulta**: Exemplo: "Como fundamentar justa causa por insubordinação?"
3. **Receba resposta**: Grok analisa precedentes da collection selecionada e responde

**Nota**: Se nenhuma collection estiver selecionada, o chat funcionará normalmente mas sem contexto de precedentes, utilizando apenas o conhecimento geral do modelo.

**Atenção**: Alterar a collection durante uma conversa ativa reiniciará o chat e todo o contexto será perdido.

### Recursos

- ✅ Chat interativo com histórico
- ✅ Anexar arquivos ao contexto (petições, documentos)
- ✅ Copiar histórico completo do chat
- ✅ Busca semântica automática na collection selecionada
- ✅ Temas claro/escuro
- ✅ Limpar chat

### Exemplos de Consultas

**Boa consulta (específica):**
```
Busque precedentes sobre adicional de insalubridade para profissionais 
de saúde em hospitais, com base no art. 192 CLT
```

**Consulta com filtro por empresa:**
```
Decisões sobre horas extras envolvendo a empresa Petrobras
```

**Consulta temporal:**
```
Precedentes recentes (últimos 2 anos) sobre equiparação salarial
```

---

## Formato de Dados

### JSON de Entrada

Estrutura **obrigatória**:

```json
[
  {
    "categoria": "HORAS EXTRAORDINÁRIAS",
    "reclamada": "Empresa XYZ LTDA",
    "conteudo": "Texto completo da fundamentação jurídica...",
    "numero_processo": "0000123-45.2023.5.10.0009",
    "data_publicacao": "2023-06-15",
    "tipo_acao": "Reclamação Trabalhista"
  },
  {
    "categoria": "ADICIONAL DE INSALUBRIDADE",
    ...
  }
]
```

**Campos:**
- `categoria` (string): Tópico da fundamentação
- `reclamada` (string): Nome da empresa (ou vazio "")
- `conteudo` (string): Texto da fundamentação completo
- `numero_processo` (string): Número único do processo
- `data_publicacao` (string): Data formato YYYY-MM-DD (ou vazio)
- `tipo_acao` (string): Tipo de ação judicial

### Markdown Gerado

```markdown
[Texto da fundamentação...]
```

**Observações:**
- Conteudo puro (sem YAML front matter)
- Metadados armazenados em JSON separado
- Chunks separados em arquivos quando >2048 chars (opcional)

### Metadata JSON Gerado

```json
{
  "categoria": "ADICIONAL DE INSALUBRIDADE",
  "reclamada": "Hospital XYZ LTDA",
  "numero_processo": "0000006-73.2023.5.10.0009",
  "data_publicacao": "2023-11-17",
  "tipo_acao": "Reclamação Trabalhista",
  "palavras-chave": ["art. 192 CLT", "insalubridade", "adicional", "grau medio"]
}
```

---

## Configuração de Collections

### Criar Collection no xAI Console

1. Acesse [console.x.ai](https://console.x.ai)
2. Login com conta xAI
3. Vá para **Collections** → **Create Collection**
4. Configure:
   - **Name**: Precedentes Trabalhistas TRT-10
   - **Description**: Sentenças trabalhistas para busca semântica
   - **Chunk Size**: 2048 caracteres
   - **Chunk Overlap**: 256 caracteres
   - **Embedding Model**: Default (xAI)

5. Clique em **Create**

### Configurar Metadados

1. Acesse **Collection Settings** → **Metadata Fields**
2. Adicione campos:

| Campo | Tipo | Searchable | Filterable |
|-------|------|------------|------------|
| categoria | text | ✅ Yes | ✅ Yes |
| reclamada | text | ✅ Yes | ✅ Yes |
| numero_processo | text | ❌ No | ✅ Yes |
| data_publicacao | date | ❌ No | ✅ Yes |
| tipo_acao | text | ❌ No | ✅ Yes |
| palavras-chave | array | ✅ Yes | ❌ No |

3. Salve configurações

### Gerar Management Key

1. **Collection Settings** → **API Access**
2. **Generate Management Key**
3. Copie e guarde em local seguro
4. Use esta key em `config.json` e na UI

---

## Perguntas Frequentes

### Perguntas Gerais

**Q: Preciso processar arquivos MD localmente antes do upload?**  
A: Sim, o sistema gera .md locais para review e backup, depois faz upload via API.

**Q: Posso fazer upload direto do JSON sem gerar MD?**  
A: Não. O processo atual é: JSON → MD (conteudo) + metadata JSON → Upload.

**Q: Como adiciono novas sentenças?**  
A: Processe novo JSON e faça upload incremental. Evite duplicatas.

**Q: Quanto custa usar xAI Collections?**  
A: Consulte [x.ai/pricing](https://x.ai/pricing). Custos incluem storage e queries.

### Problemas Técnicos

**Q: Management Key inválida**  
A: Verifique se copiou corretamente. Regenere se necessário no xAI Console.

**Q: Collection não encontrada**  
A: Aguarde processamento. Verifique Collection ID. Recarregue lista.

**Q: Keywords genéricas (ex: "CLT", "direito")**  
A: Use modelo grok-2-1212 (melhor qualidade). Verifique prompt no código.

**Q: Upload lento (>1h para 100 docs)**  
A: Normal. Embedding é lento (~30-60min para 100 docs). Consulte [TESTING_GUIDE.md](TESTING_GUIDE.md).

**Q: Erro "Chunk size muito grande"**  
A: Reduza chunk_size para 1024 no código ou recrie Collection com tamanho menor.

### Otimização

**Q: Como acelerar processamento?**  
A: Use batches menores (50-100 docs), upload fora de horário de pico, otimize chunk size.

**Q: Melhor modelo para keywords?**  
A: grok-beta (rápido), grok-2-1212 (melhor qualidade mas mais lento).

**Q: Como melhorar qualidade de busca?**  
A: Use Filters por metadados, aumente top_k, customize system prompt.

---

**Dúvidas?** Consulte [TESTING_GUIDE.md](TESTING_GUIDE.md) ou abra uma issue no repositório.
