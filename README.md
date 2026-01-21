# Sistema de Busca Semântica de Precedentes Trabalhistas

Sistema completo para indexação e busca semântica em sentenças trabalhistas usando xAI Collections.

## 📋 Visão Geral

Este sistema foi desenvolvido para auxiliar juízes do trabalho na busca de precedentes em sentenças anteriores, utilizando busca semântica híbrida (embeddings + keywords) através da plataforma xAI Collections.

### Funcionalidades Principais

- **Processamento Inteligente de JSON**: Converte arquivo JSON de sentenças em arquivos Markdown estruturados
- **Chunking Otimizado**: Divide documentos longos preservando contexto com overlap
- **Metadados Jurídicos**: Extração automática de palavras-chave jurídicas relevantes
- **Interface Gráfica**: UI Flet para busca interativa com modelo Grok
- **Busca Híbrida**: Combina busca semântica e por palavras-chave
- **Filtros Avançados**: Filtragem por empresa reclamada, tipo de ação, data

## 🔧 Componentes do Sistema

### 1. CollectionUploader.py

Script para processar arquivo JSON de sentenças e preparar para upload em xAI Collections.

**Características:**
- Extração automática de palavras-chave jurídicas (CLT, súmulas, conceitos trabalhistas)
- Chunking inteligente com overlap para documentos longos
- Metadados estruturados (categoria, reclamada, número do processo, data, tipo de ação)
- Nomes de arquivo sanitizados e únicos
- Estatísticas detalhadas do processamento

**Uso:**
```bash
python CollectionUploader.py "Sentenças Indexadas Revisado.json" --output-dir ./sentencas_md
```

**Parâmetros Recomendados para xAI Collection:**
- **Chunk Size**: 2048 caracteres (~512 tokens)
- **Chunk Overlap**: 256 caracteres (~64 tokens)
- **Embedding Model**: Padrão xAI

### 2. PrecedenteSearchApp.py

Aplicação gráfica Flet para busca de precedentes usando xAI Collections e modelo Grok.

**Funcionalidades:**
- Interface de chat intuitiva
- Seleção de Collections disponíveis
- Toggle para habilitar/desabilitar busca na Collection
- Anexar arquivos ao contexto do chat
- Copiar histórico completo do chat
- Configurações persistentes (API keys, modelo, temperature)
- Suporte a busca em tempo real (Web e X)
- Temas claro/escuro

**Uso:**
```bash
python PrecedenteSearchApp.py
```

**Primeira Execução:**
1. Clique em ⚙️ **Configurações**
2. Configure:
   - **Management Key**: Chave de gerenciamento da xAI Collection
   - **API Key**: Chave de API do Grok
   - **Modelo**: Selecione o modelo (recomendado: grok-2-1212)
   - **Temperature**: 0.7 (padrão)
   - **System Prompt**: Customize conforme necessário
3. Salve as configurações

## 📊 Estrutura do Arquivo JSON de Entrada

```json
{
  "categoria": "HORAS EXTRAORDINÁRIAS",
  "reclamada": "Nome da Empresa LTDA",
  "conteudo": "Texto completo da fundamentação...",
  "numero_processo": "0000123-45.2023.5.10.0009",
  "data_publicacao": "2023-06-15",
  "tipo_acao": "Reclamação Trabalhista"
}
```

### Campos:

- **categoria**: Tópico da fundamentação (ex: JUSTA CAUSA, HORAS EXTRAS)
- **reclamada**: Nome da empresa reclamada (ou vazio)
- **conteudo**: Texto da fundamentação jurídica
- **numero_processo**: Número único do processo
- **data_publicacao**: Data de publicação da sentença
- **tipo_acao**: Tipo de ação (Reclamação Trabalhista, Mandado de Segurança, etc.)

## 🗂️ Estrutura dos Arquivos MD Gerados

```markdown
---
categoria: ADICIONAL DE INSALUBRIDADE
reclamada: Empresa XYZ LTDA
numero_processo: 0000006-73.2023.5.10.0009
data_publicacao: 2023-11-17
tipo_acao: Reclamação Trabalhista
keywords: insalubridade, adicional_noturno, clt, artigo_clt, fgts
---
# ADICIONAL DE INSALUBRIDADE

[Conteúdo da fundamentação...]
```

### Metadados:

- **categoria**: Categoria jurídica da fundamentação
- **reclamada**: Empresa para filtros prioritários
- **numero_processo**: Identificador único
- **data_publicacao**: Para priorizar precedentes recentes
- **tipo_acao**: Tipo de processo
- **keywords**: Palavras-chave jurídicas extraídas automaticamente

## 🔍 Palavras-chave Jurídicas Reconhecidas

O sistema identifica automaticamente:

### Legislação e Normas
- Artigos da CLT (`art. 317`, `CLT`)
- Leis (`Lei 9.394/1996`)
- Súmulas (`Súmula 374/TST`)
- Jurisprudência (TST, STF)

### Conceitos Trabalhistas
- Horas extras, adicional noturno
- Insalubridade, periculosidade
- FGTS, férias, 13º salário
- Rescisão, justa causa, reintegração
- Equiparação salarial, prescrição
- Honorários advocatícios, justiça gratuita
- Danos moral e material
- Intervalos, repousos semanais
- Categorias profissionais, direito sindical
- Normas coletivas

## 📈 Estatísticas do Chunking

Com base na análise do corpus de sentenças:

- **Média de caracteres**: 1.973 (~500 tokens)
- **Desvio padrão**: 3.298 caracteres
- **90.90%** dos documentos dentro de 1 DP
- **Range**: 19 a 54.685 caracteres

### Estratégia de Chunking

**Chunk Size: 2048 caracteres**
- Captura bem a maioria dos conteúdos médios
- Mantém contexto suficiente para embeddings
- Evita fragmentação excessiva

**Chunk Overlap: 256 caracteres (12.5%)**
- Preserva continuidade entre chunks
- Evita perda de contexto em quebras
- Ideal para textos jurídicos densos

## 🚀 Workflow Completo

### Passo 1: Processar Sentenças

```bash
python CollectionUploader.py "Sentenças Indexadas Revisado.json" --output-dir ./sentencas_md
```

**Resultado:**
- Arquivos MD criados em `./sentencas_md/`
- Estatísticas detalhadas exibidas no console
- Metadados estruturados em cada arquivo

### Passo 2: Criar Collection no xAI Console

1. Acesse: https://console.x.ai/
2. Crie nova Collection:
   - **Name**: Precedentes Trabalhistas
   - **Chunk Size**: 2048 caracteres
   - **Chunk Overlap**: 256 caracteres
   - **Embedding Model**: Padrão xAI

3. Configure campos de metadados:
   - `categoria` (filtro)
   - `reclamada` (filtro - priorização)
   - `numero_processo` (filtro)
   - `data_publicacao` (filtro - recentes primeiro)
   - `tipo_acao` (filtro)
   - `keywords` (busca híbrida)

4. Gere **Management Key** para a Collection

### Passo 3: Upload dos Arquivos MD

1. No xAI Console, acesse sua Collection
2. Faça upload dos arquivos do diretório `./sentencas_md/`
3. Aguarde processamento dos embeddings

### Passo 4: Configurar Aplicação de Busca

```bash
python PrecedenteSearchApp.py
```

1. Clique em ⚙️ **Configurações**
2. Configure:
   - **Management Key**: Chave da Collection criada
   - **API Key**: Chave de API do Grok
   - **Modelo**: grok-2-1212
   - **Temperature**: 0.7
   - **System Prompt**: 
   ```
   Você é um assistente jurídico especializado em Direito do Trabalho brasileiro. 
   Analise precedentes e fundamente respostas com base na CLT, jurisprudência e 
   doutrina trabalhista. Ao citar precedentes, sempre mencione o número do processo.
   ```

### Passo 5: Realizar Buscas

1. Selecione a Collection no menu suspenso
2. Habilite "Buscar na Collection"
3. Digite consultas como:
   - "Como fundamentar adicional de insalubridade para profissionais de saúde?"
   - "Precedentes sobre justa causa por insubordinação"
   - "Critérios para equiparação salarial entre professores"
   - "Prescrição em ações de consignação em pagamento"

## 🎯 Busca Híbrida com Filtros

### Exemplo de Consulta Avançada:

**Pergunta:**
> "Busque precedentes sobre adicional de insalubridade em hospitais, priorizando processos da empresa Hospital XYZ dos últimos 2 anos"

**Sistema:**
1. Realiza busca semântica na Collection (embeddings)
2. Combina com busca por keywords (`insalubridade`, `hospital`)
3. Aplica filtros:
   - `reclamada = "Hospital XYZ"` (prioridade)
   - `data_publicacao >= 2022-01-01`
   - `categoria LIKE "%INSALUBRIDADE%"`
4. Retorna top-5 precedentes mais relevantes
5. Grok analisa e fundamenta resposta com base nos precedentes

## 📝 Boas Práticas de Uso

### Para Juízes:

1. **Seja específico nas consultas**: Inclua conceitos jurídicos específicos
2. **Use termos técnicos**: O sistema reconhece terminologia trabalhista
3. **Priorize por empresa**: Mencione a empresa reclamada quando relevante
4. **Contexto temporal**: Especifique período se quiser precedentes recentes
5. **Anexe arquivos**: Adicione petições ou documentos ao contexto quando necessário

### Para Manutenção do Sistema:

1. **Atualize regularmente**: Processe novas sentenças periodicamente
2. **Monitore qualidade**: Verifique se keywords estão sendo extraídas corretamente
3. **Ajuste chunks**: Se necessário, experimente com chunk size/overlap
4. **Backup**: Mantenha backup dos arquivos MD e configurações

## 🔐 Segurança e Privacidade

- **API Keys**: Armazenadas localmente em `app_config.json`
- **Dados sensíveis**: Remova informações pessoais antes do processamento
- **Controle de acesso**: Use Management Key separada por usuário
- **Conformidade**: Garanta conformidade com LGPD ao indexar sentenças

## 📦 Dependências

### CollectionUploader.py:
```bash
pip install -r requirements_uploader.txt
```

**Pacotes:**
- `json` (built-in)
- `pathlib` (built-in)
- `argparse` (built-in)

### PrecedenteSearchApp.py:
```bash
pip install -r requirements_app.txt
```

**Pacotes:**
- `flet>=0.20.0`
- `requests>=2.31.0`
- `pyperclip>=1.8.2`

## 🆘 Solução de Problemas

### Erro: "Chunk size muito grande"
**Solução**: Reduza chunk_size para 1024 caracteres

### Erro: "Management Key inválida"
**Solução**: Verifique se a chave foi copiada corretamente do xAI Console

### Erro: "Collection não encontrada"
**Solução**: Certifique-se de que a Collection foi criada e o upload dos arquivos foi concluído

### Busca não retorna resultados relevantes
**Solução**: 
1. Verifique se os metadados foram configurados corretamente na Collection
2. Tente reformular a consulta com termos mais específicos
3. Aumente o `top_k` na configuração de busca (padrão: 5)

## 📚 Recursos Adicionais

- **Documentação xAI Collections**: https://docs.x.ai/docs/guides/using-collections/
- **API Reference**: https://docs.x.ai/docs/guides/tools/collections-search-tool
- **xAI Console**: https://console.x.ai/

## 📊 Resultados do Teste (Excerto)

```
Total de sentenças processadas:     25
Total de arquivos MD criados:       64
Categorias únicas:                  18
Tipos de ação únicos:               3
Tamanho médio por arquivo:          ~2048 caracteres
```

### Categorias Encontradas:
- ADICIONAL DE INSALUBRIDADE
- ATIVIDADE DE PROFESSOR — CARACTERIZAÇÃO
- DIFERENÇAS SALARIAIS
- EQUIPARAÇÃO SALARIAL
- HONORÁRIOS ADVOCATÍCIOS
- HORAS EXTRAORDINÁRIAS
- JUSTA CAUSA. VERBAS RESCISÓRIAS
- JUSTIÇA GRATUITA
- PRESCRIÇÃO
- REINTEGRAÇÃO
- E mais...

## 🎓 Sobre o Sistema

Este sistema foi desenvolvido para modernizar a busca de precedentes judiciais, substituindo busca por palavras-chave tradicionais por busca semântica baseada em embeddings de linguagem natural. A combinação de embeddings (captura significado) com keywords (precisão terminológica) oferece resultados superiores para pesquisa jurídica.

## 📄 Licença

Este sistema foi desenvolvido especificamente para uso no Tribunal Regional do Trabalho.

---

**Desenvolvido para auxiliar a magistratura trabalhista brasileira na fundamentação de decisões com base em precedentes próprios.**
