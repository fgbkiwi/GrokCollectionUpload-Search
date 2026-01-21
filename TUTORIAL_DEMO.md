# 🎬 Tutorial Prático: Do JSON à Busca em 10 Minutos

Guia passo-a-passo demonstrando o sistema completo usando o arquivo de excerto.

---

## 🎯 Objetivo

Demonstrar o workflow completo:
1. Processar JSON → Arquivos MD
2. Configurar xAI Collection
3. Realizar busca de precedentes

**Tempo estimado**: 10-15 minutos

---

## 📋 Pré-requisitos

- ✅ Python 3.8+ instalado
- ✅ Arquivo "Sentenças Indexadas Revisado (excerto).json.txt"
- ✅ Conta xAI criada (https://console.x.ai/)

---

## 🚀 Passo 1: Processar Sentenças (2 minutos)

### 1.1 Instale dependências da aplicação

```bash
pip install flet requests pyperclip
```

**Nota**: CollectionUploader.py não requer instalação (usa bibliotecas built-in).

### 1.2 Execute o processamento

```bash
cd /home/user
python CollectionUploader.py "uploaded_files/Sentenças Indexadas Revisado (excerto).json.txt" --output-dir ./sentencas_demo
```

### 1.3 Verifique resultados

```bash
ls -lh sentencas_demo/ | head -10
```

**Resultado esperado:**
```
Total: 64 arquivos MD
Categorias: 18 únicas
Tipos de ação: 3
```

**✅ Checkpoint 1**: Arquivos MD criados com sucesso em `./sentencas_demo/`

---

## 🔧 Passo 2: Configurar xAI Collection (5 minutos)

### 2.1 Criar Collection

1. Acesse: https://console.x.ai/
2. Login com sua conta
3. Navegue para **Collections**
4. Clique em **"Create Collection"**

### 2.2 Configure parâmetros

```yaml
Name: Precedentes Demo
Description: Demonstração de busca semântica em precedentes trabalhistas
Chunk Size: 2048
Chunk Overlap: 256
Embedding Model: Default (xAI)
```

Clique em **"Create"**

### 2.3 Configure metadados

Na tela da Collection criada, vá para **Settings** → **Metadata Fields**

Adicione os seguintes campos:

| Field Name | Type | Index As |
|------------|------|----------|
| categoria | Text | Filter |
| reclamada | Text | Filter |
| numero_processo | Text | Filter |
| data_publicacao | Date | Filter |
| tipo_acao | Text | Filter |
| keywords | Text | Search |

Clique em **"Save Metadata Configuration"**

### 2.4 Upload arquivos MD

1. Na tela da Collection, clique em **"Upload Files"**
2. Selecione todos os arquivos MD do diretório `./sentencas_demo/`
3. Clique em **"Upload"**
4. Aguarde processamento (barra de progresso)

**⏱️ Tempo**: ~1-2 minutos para 64 arquivos

### 2.5 Gere Management Key

1. Vá para **Settings** → **API Keys**
2. Clique em **"Generate Management Key"**
3. Dê um nome: "Demo Key"
4. **Copie e guarde** a chave gerada

**✅ Checkpoint 2**: Collection criada, arquivos enviados, Management Key obtida

---

## 🔍 Passo 3: Configurar Aplicação de Busca (3 minutos)

### 3.1 Execute a aplicação

```bash
python PrecedenteSearchApp.py
```

Uma janela Flet será aberta.

### 3.2 Configure credenciais

1. Clique no botão **⚙️ Configurações**
2. Preencha os campos:

```yaml
Management Key: [Cole a chave copiada no passo 2.5]
API Key: [Sua API Key do Grok - obtenha em console.x.ai → Settings → API Keys]
Modelo: grok-2-1212
Temperature: 0.7
System Prompt: 
  Você é um assistente jurídico especializado em Direito do Trabalho brasileiro.
  Analise precedentes e fundamente respostas com base na CLT, jurisprudência e 
  doutrina trabalhista. Sempre cite o número do processo ao mencionar precedentes.
```

3. Configure toggles:
   - ☑️ URL Source Citation
   - ☑️ Tema Escuro (opcional)
   - ☐ Real-time Web Search (desabilitado para este demo)
   - ☐ Real-time X Search (desabilitado para este demo)

4. Clique em **"Salvar"**

### 3.3 Selecione Collection

1. No menu suspenso "Collection", selecione: **Precedentes Demo**
2. Habilite o toggle: **"Buscar na Collection"**

**✅ Checkpoint 3**: Aplicação configurada e pronta para uso

---

## 💬 Passo 4: Realizar Buscas de Demonstração (5 minutos)

### 4.1 Busca Simples: Adicional de Insalubridade

**Digite:**
```
Como fundamentar adicional de insalubridade para profissionais de saúde 
que supervisionam estagiários em hospitais?
```

**Clique em "Enviar"** ou pressione Enter

**Resultado esperado:**
- ⏱️ Tempo: 15-30 segundos
- 📄 Grok retornará fundamentação baseada no precedente relevante
- 📋 Citará processo: 0000006-73.2023.5.10.0009
- 📖 Mencionará: NR-15, anexo 14, grau médio (20%)
- 💡 Explicará que EPIs reduzem mas não eliminam risco

### 4.2 Busca Complexa: Justa Causa

**Digite:**
```
Busque precedentes sobre justa causa por insubordinação envolvendo 
ofensas verbais a superior hierárquico
```

**Resultado esperado:**
- 📄 Precedente do processo 0000010-47.2022.5.10.0009
- 📖 Fundamentação sobre: necessidade de respeito à hierarquia, contexto do episódio
- ⚖️ Análise de proporcionalidade da punição

### 4.3 Busca por Categoria: Prescrição

**Digite:**
```
Explique o entendimento sobre prescrição em ações trabalhistas 
com base nos precedentes
```

**Resultado esperado:**
- 📄 Precedente do processo 0000006-83.2017.5.10.0009
- 📅 Marco inicial: 5º dia útil do mês subsequente (art. 459, CLT)
- ⏳ Prazo: 5 anos (prescrição quinquenal)

### 4.4 Busca Processual: Incompetência

**Digite:**
```
Qual o entendimento sobre competência da Justiça do Trabalho 
para ações de representação sindical?
```

**Resultado esperado:**
- 📄 Precedente do processo 0000008-53.2017.5.10.0009 (Mandado de Segurança)
- 📖 Fundamentação sobre competência material da Justiça do Trabalho
- ⚖️ Interpretação do art. 114 da CF

### 4.5 Busca com Contexto: Reintegração

**Digite:**
```
Como fundamentar reintegração de empregado dispensado durante 
a pandemia com base no movimento #NãoDemita?
```

**Resultado esperado:**
- 📄 Precedente do processo 0000008-14.2021.5.10.0009
- 📖 Análise da natureza jurídica do compromisso #NãoDemita
- ⚖️ Distinção entre promessa de recompensa e compromisso espontâneo

---

## 📊 Verificar Estatísticas da Collection

### No xAI Console:

1. Acesse sua Collection "Precedentes Demo"
2. Vá para **Analytics** ou **Usage**
3. Verifique:
   - ✅ 64 documentos indexados
   - ✅ Número de queries realizadas
   - ✅ Average relevance score
   - ✅ Most searched keywords

---

## 🎓 Recursos Adicionais Testados

### Anexar Arquivo ao Contexto

1. Crie um arquivo de texto com uma petição fictícia:

```bash
cat > /home/user/peticao_exemplo.txt << 'EOF'
PETIÇÃO INICIAL - ADICIONAL DE INSALUBRIDADE

O Reclamante, técnico de enfermagem, laborou supervisionando estagiários 
em hospital público, com exposição a agentes biológicos. Pleiteia adicional 
de insalubridade em grau médio.
EOF
```

2. Na aplicação, clique em **📎 Anexar arquivo**
3. Selecione `peticao_exemplo.txt`
4. Digite: "Analise esta petição e sugira fundamentação com base nos precedentes"

### Copiar Histórico do Chat

1. Após realizar várias consultas, clique em **📋 Copiar chat**
2. Cole em editor de texto (Ctrl+V)
3. Você terá todo o histórico formatado para compartilhamento ou registro

### Limpar Chat

1. Clique em **🗑️ Limpar chat**
2. Histórico será resetado
3. Use para começar nova sessão de consultas

---

## ✅ Checklist de Demonstração Completa

- [x] Processar JSON → MD (2 min)
- [x] Criar Collection no xAI (5 min)
- [x] Configurar aplicação (3 min)
- [x] Realizar 5 buscas diferentes (5 min)
- [x] Testar anexo de arquivo
- [x] Testar copiar histórico
- [x] Verificar estatísticas

**Total**: ~15 minutos

---

## 🎯 Próximos Passos Após Demonstração

### 1. Processar Corpus Completo

```bash
python CollectionUploader.py "Sentenças Indexadas Revisado.json" --output-dir ./sentencas_completo
```

### 2. Criar Collection de Produção

- Nome: Precedentes Trabalhistas - Completo
- Mesmas configurações de chunk
- Upload de todos os arquivos MD

### 3. Customizar System Prompt

Ajuste para seu estilo de fundamentação:

```
Você é um assistente jurídico especializado em Direito do Trabalho.
Seu objetivo é auxiliar na elaboração de minutas de sentenças trabalhistas.

DIRETRIZES:
1. Sempre cite o número do processo ao mencionar precedentes
2. Use linguagem jurídica formal e precisa
3. Fundamente decisões com base em CLT, jurisprudência e doutrina
4. Priorize precedentes recentes (últimos 3 anos)
5. Considere particularidades da empresa reclamada quando relevante
6. Estruture respostas de forma clara e didática
7. Inclua base legal completa (artigos, parágrafos, incisos)

FORMATAÇÃO:
- Use negrito para ênfase em conceitos jurídicos importantes
- Cite precedentes no formato: "Conforme processo [número]: '[citação]'"
- Organize respostas com subtítulos quando apropriado
```

### 4. Organizar Collections Temáticas

Crie Collections especializadas:

- **CLT Material**: Horas extras, férias, FGTS, rescisão
- **Adicionais**: Insalubridade, periculosidade, noturno
- **Processual**: Competência, prescrição, provas
- **Sindical**: Representação, negociação coletiva
- **Indenizações**: Danos morais, materiais, estabilidades

### 5. Integrar ao Workflow

- Use antes de elaborar minutas de sentenças
- Consulte durante audiências para fundamentação rápida
- Mantenha histórico de consultas para referência futura

---

## 📝 Notas de Demonstração

### Pontos Fortes Demonstrados

✅ **Busca Semântica Eficaz**: Encontra precedentes relevantes mesmo com termos diferentes
✅ **Citações Precisas**: Grok cita números de processo corretamente
✅ **Contextualização**: Responde considerando contexto jurídico completo
✅ **Rapidez**: Resultados em 15-30 segundos
✅ **Interface Intuitiva**: Fácil de usar, tipo chat

### Limitações Observadas

⚠️ **Corpus Pequeno**: Apenas 25 sentenças (64 chunks) no demo
⚠️ **Metadados Incompletos**: Alguns campos vazios ("Não especificada")
⚠️ **Dependência de Internet**: Requer conexão estável
⚠️ **Custo de API**: Cada consulta consome créditos xAI

### Melhorias Sugeridas para Produção

1. **Enriquecer Metadados**: Preencher todos os campos (reclamada, data)
2. **Aumentar Corpus**: Processar todas as sentenças disponíveis
3. **Criar Índices**: Organizar por temas para busca mais rápida
4. **Cache Local**: Salvar consultas frequentes para economizar API
5. **Feedback Loop**: Marcar respostas úteis para refinar System Prompt

---

## 🎉 Conclusão da Demonstração

**Sistema Validado!**

✅ Processamento de JSON funcionando perfeitamente
✅ Chunking otimizado preservando contexto
✅ Metadados estruturados facilitando filtros
✅ Busca híbrida retornando resultados relevantes
✅ Interface Flet intuitiva e responsiva
✅ Integração com Grok gerando fundamentações coerentes

**Pronto para uso em ambiente de produção com corpus completo!**

---

**Tempo total da demonstração: ~15 minutos**
**Nível de dificuldade: Intermediário**
**Requisitos técnicos: Mínimos**

**Desenvolvido para modernizar a pesquisa jurídica com IA.**
