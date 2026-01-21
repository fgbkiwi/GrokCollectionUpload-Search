# Collection Uploader UI - Interface Gráfica

Interface gráfica em Flet para processar arquivos JSON de sentenças trabalhistas e fazer upload para xAI Collections.

## 🎯 Funcionalidades

### ⚙️ Configurações
- **Management Key**: Chave de gerenciamento da xAI Collection (campo com senha oculta)
- **API Key**: Chave de API do Grok para geração inteligente de keywords (campo com senha oculta)
- **Modelo Grok**: Seleção do modelo para geração de keywords via dropdown
  - `grok-beta` (padrão - rápido e econômico)
  - `grok-2-1212`
  - `grok-2-vision-1212`
  - `grok-vision-beta`
- **Carregar Collections**: Botão para buscar collections disponíveis
- **Dropdown de Collections**: Seleciona a collection de destino para upload

### 📁 Seleção de Arquivos
- **File Picker Multi-seleção**: Seleciona múltiplos arquivos JSON simultaneamente
  - Suporta extensões: `.json`, `.txt`
  - Exibe lista de arquivos selecionados
- **Folder Picker**: Seleciona pasta de destino para os arquivos MD gerados

### 🚀 Ações Separadas
1. **Gerar Arquivos MD**
   - Processa todos os JSONs selecionados
   - Gera keywords usando o modelo Grok selecionado
   - Cria arquivos MD com metadados estruturados
   - Permite avaliação da qualidade antes do upload
   
2. **Upload para Collection**
   - Disponível apenas após gerar MDs
   - Faz upload dos arquivos para a collection selecionada
   - Mostra progresso em tempo real

### 📊 Janela de Feedback
- Log em tempo real com timestamps
- Informações sobre processamento (sentenças, chunks, categorias)
- Estatísticas detalhadas ao final
- Mensagens de erro e avisos
- Fundo escuro para melhor legibilidade

## 🚀 Como Usar

### 1. Instalação

```bash
pip install -r requirements_uploader_ui.txt
```

Ou instale manualmente:
```bash
pip install flet requests
```

### 2. Executar a Aplicação

```bash
python CollectionUploaderUI.py
```

### 3. Workflow Completo

#### Passo 1: Configurar API Keys
1. Cole sua **Management Key** da xAI Collection
2. Cole sua **API Key** do Grok
3. Selecione o **modelo** para geração de keywords (recomendado: `grok-beta`)
4. Clique em **"Carregar Collections"**
5. Selecione a **Collection** de destino no dropdown

#### Passo 2: Selecionar Arquivos
1. Clique em **"Selecionar Arquivos JSON"**
2. Escolha um ou mais arquivos JSON com sentenças
3. Clique em **"Selecionar Pasta de Saída"**
4. Escolha onde salvar os arquivos MD

#### Passo 3: Gerar Arquivos MD
1. Clique em **"Gerar Arquivos MD"**
2. Acompanhe o progresso no log
3. Revise as estatísticas ao final
4. *(Opcional)* Abra a pasta de saída e inspecione os MDs gerados

#### Passo 4: Upload para Collection
1. Se os MDs estiverem OK, clique em **"Upload para Collection"**
2. Aguarde o upload de todos os arquivos
3. Verifique o resumo (sucessos/falhas)

## 📋 Estrutura dos Arquivos MD Gerados

```markdown
---
categoria: HORAS EXTRAORDINÁRIAS
reclamada: Empresa XYZ LTDA
numero_processo: 0000123-45.2023.5.10.0009
data_publicacao: 2023-06-15
tipo_acao: Reclamação Trabalhista
keywords: horas_extras, clt, art_59, adicional, jornada_trabalho
---
# HORAS EXTRAORDINÁRIAS

[Conteúdo da fundamentação...]
```

### Keywords Inteligentes

As keywords são geradas pelo modelo Grok analisando:
- Leis e artigos citados (CLT, Súmulas, Constituição)
- Conceitos trabalhistas (horas extras, insalubridade, FGTS, etc.)
- Termos jurídicos específicos do texto
- Categoria da sentença

## 🎨 Interface

### Seções da UI

1. **⚙️ Configurações** (borda azul)
   - Management Key + botão de carregar
   - Dropdown de Collections
   - API Key
   - Dropdown de Modelos

2. **📁 Seleção de Arquivos** (borda verde)
   - Botão de file picker (JSON)
   - Lista de arquivos selecionados
   - Botão de folder picker
   - Pasta de saída

3. **🚀 Ações** (borda laranja)
   - Botão "Gerar Arquivos MD" (azul)
   - Botão "Upload para Collection" (verde)
   - Progress bar

4. **📊 Log de Execução** (fundo escuro)
   - Feedback em tempo real
   - Timestamps
   - Estatísticas

## 🔒 Segurança

- **Campos de senha**: Management Key e API Key são ocultáveis
- **Armazenamento local**: Nenhuma credencial é salva permanentemente
- **HTTPS**: Todas as comunicações com xAI API são criptografadas

## 📊 Estatísticas Exibidas

Ao final do processamento, a UI mostra:
- Total de sentenças processadas
- Total de arquivos MD criados
- Número de categorias únicas
- Número de tipos de ação únicos
- Lista de categorias encontradas
- Lista de tipos de ação

## ⚠️ Avisos Importantes

1. **Geração de Keywords com IA**
   - Requer API Key do Grok válida
   - Consome créditos da API por sentença
   - Modelo `grok-beta` é mais econômico
   - Se falhar, usa keywords básicas como fallback

2. **Limites de Upload**
   - Arquivos muito grandes podem demorar
   - Timeout padrão: 30 segundos por arquivo
   - Falhas individuais não interrompem o processo

3. **Validação de Entrada**
   - Botões ficam desabilitados até que todos os campos necessários sejam preenchidos
   - "Gerar MD" requer: JSONs + pasta de saída + API Key
   - "Upload" requer: MDs gerados + Collection + Management Key

## 🐛 Solução de Problemas

### "Erro ao carregar collections"
- Verifique se a Management Key está correta
- Confirme que você tem permissões na Collection

### "Erro ao gerar keywords com Grok"
- Verifique se a API Key está correta
- Confirme que você tem créditos disponíveis
- O sistema usará keywords básicas como fallback

### "Falha no upload"
- Verifique conexão com internet
- Confirme que a Collection existe
- Verifique se os arquivos MD foram gerados corretamente

### Botões desabilitados
- "Gerar MD": Precisa de JSONs + pasta + API Key
- "Upload": Precisa de MDs gerados + Collection + Management Key
- "Carregar Collections": Precisa de Management Key

## 💡 Dicas de Uso

1. **Teste com poucos arquivos primeiro**: Selecione 1-2 JSONs para validar
2. **Revise os MDs gerados**: Abra a pasta de saída e inspecione alguns arquivos
3. **Use grok-beta para economia**: Modelo mais rápido e barato para keywords
4. **Monitore o log**: Acompanhe o processo em tempo real
5. **Upload em lotes**: Se tiver muitos arquivos, faça em várias sessões

## 📚 Diferenças do Script Original

### CollectionUploader.py (CLI)
- Interface de linha de comando
- Keywords extraídas por regex patterns
- Apenas gera arquivos MD
- Sem funcionalidade de upload

### CollectionUploaderUI.py (GUI)
- Interface gráfica amigável
- Keywords geradas por IA (Grok)
- Gera MDs **E** faz upload
- Feedback visual em tempo real
- Seleção de Collections disponíveis
- Validação de campos
- Estatísticas detalhadas

## 🔗 Recursos Relacionados

- **CollectionUploader.py**: Script CLI original
- **PrecedenteSearchApp.py**: App de busca de precedentes
- **README.md**: Documentação completa do sistema

## 📄 Exemplo de Uso Completo

```bash
# 1. Instalar dependências
pip install -r requirements_uploader_ui.txt

# 2. Executar aplicação
python CollectionUploaderUI.py

# 3. Na UI:
#    - Configure Management Key: xai-mgmt-xxxxx
#    - Configure API Key: xai-xxxxx
#    - Selecione modelo: grok-beta
#    - Clique "Carregar Collections"
#    - Selecione collection: "Precedentes Trabalhistas"
#    - Selecione JSONs: sentencas1.json, sentencas2.json
#    - Selecione pasta: /home/user/sentencas_md
#    - Clique "Gerar Arquivos MD"
#    - [Revise MDs gerados]
#    - Clique "Upload para Collection"
```

## 🎯 Próximos Passos

Após usar esta UI:
1. Acesse o xAI Console para verificar os arquivos
2. Configure campos de metadados na Collection
3. Use o **PrecedenteSearchApp.py** para buscar precedentes

---

**Desenvolvido para facilitar o processamento e upload de sentenças trabalhistas para xAI Collections**
