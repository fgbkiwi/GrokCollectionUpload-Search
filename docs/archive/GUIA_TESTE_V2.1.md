# 🧪 GUIA DE TESTE - Sistema V2.1

**Data:** 20 de Janeiro de 2025  
**Objetivo:** Testar todos os recursos implementados da UI Flutter  

---

## ✅ PRÉ-REQUISITOS

### **1. Credenciais xAI (Obrigatórias)**
- [ ] **Management Key** (xai-mgmt-...)
  - Obtida em: https://console.x.ai/ → Account → API Keys
  - Permissões: Acesso a Collections
- [ ] **API Key** (xai-...)
  - Obtida em: https://console.x.ai/ → Account → API Keys
  - Permissões: Acesso ao modelo Grok

### **2. Collection de Teste (Obrigatória)**
- [ ] Criar Collection no xAI Console
  - Nome sugerido: "Teste Precedentes TRT-10"
  - Configurações:
    - Chunk Size: 2048 chars (~512 tokens)
    - Chunk Overlap: 256 chars (~64 tokens)
    - Embedding Model: Default (xAI)

### **3. Arquivos de Teste**
- [ ] Arquivo JSON disponível:
  - `/home/user/uploaded_files/Sentenças Indexadas Revisado (excerto).json.txt`
  - 25 sentenças de exemplo
  - Tamanho: ~140 KB

---

## 🚀 TESTE 1: CONFIGURAÇÃO INICIAL

### **Objetivo:** Verificar salvamento de configurações

#### **Passos:**
1. [ ] Executar Flutter app:
   ```bash
   cd /home/user/collection_uploader_app
   flutter run -d linux
   ```

2. [ ] Preencher campos:
   - [ ] Management Key: `xai-mgmt-...`
   - [ ] API Key: `xai-...`
   - [ ] Modelo Grok: Selecionar `grok-beta` (padrão)

3. [ ] Testar carregamento de Collections:
   - [ ] Clicar no ícone de "nuvem com seta" no campo Management Key
   - [ ] Ou: Clicar no botão "Carregar Collections" (se disponível)

4. [ ] Verificar dropdown de Collections:
   - [ ] Deve listar Collections criadas no xAI Console
   - [ ] Selecionar Collection de teste

5. [ ] Fechar e reabrir app:
   - [ ] Verificar se credenciais foram salvas
   - [ ] Verificar se Collection selecionada foi restaurada

#### **Resultado Esperado:**
- ✅ Collections carregadas com sucesso
- ✅ Dropdown mostra nome + ID de cada Collection
- ✅ Configurações persistem entre sessões
- ✅ Log mostra: `[HH:MM:SS] ✅ X Collection(s) encontrada(s)`

---

## 🚀 TESTE 2: SELEÇÃO DE ARQUIVOS

### **Objetivo:** Verificar seleção de arquivos e diretórios

#### **Passos:**
1. [ ] Clicar em "Arquivos JSON de Sentenças"
2. [ ] Selecionar arquivo de teste:
   - `/home/user/uploaded_files/Sentenças Indexadas Revisado (excerto).json.txt`
3. [ ] Verificar mensagem de confirmação
4. [ ] Clicar em "Diretório de Saída (MD)"
5. [ ] Selecionar/criar diretório:
   - Sugestão: `/home/user/sentencas_md_teste_v2`
6. [ ] Verificar mensagem de confirmação

#### **Resultado Esperado:**
- ✅ Card "Arquivos JSON" mostra "1 arquivo(s) selecionado(s)"
- ✅ Card "Diretório de Saída" mostra caminho completo
- ✅ Logs mostram:
  - `[HH:MM:SS] ✅ 1 arquivo(s) JSON selecionado(s)`
  - `[HH:MM:SS] ✅ Diretório de saída: /home/user/...`

---

## 🚀 TESTE 3: GERAÇÃO DE ARQUIVOS MD

### **Objetivo:** Verificar geração de MD com keywords inteligentes

#### **Passos:**
1. [ ] Verificar botão "1. Gerar Arquivos MD":
   - [ ] Deve estar habilitado (azul)
   - [ ] Texto: "1. Gerar Arquivos MD"

2. [ ] Clicar no botão

3. [ ] Observar processamento:
   - [ ] Tela muda para "Processing View"
   - [ ] Barra de progresso aparece
   - [ ] Log em tempo real (fundo preto, texto verde)
   - [ ] Status: "Gerando MD do arquivo 1/1..."

4. [ ] Aguardar conclusão (~2-5 minutos)

5. [ ] Verificar janela de feedback:
   - [ ] Título: "✅ Arquivos MD Gerados"
   - [ ] Total de arquivos criados: ~64
   - [ ] Localização do diretório
   - [ ] Botões: "OK" e "Upload Agora"

6. [ ] Clicar em "OK" para fechar

7. [ ] Verificar card de status (verde):
   - [ ] Título: "✅ Arquivos MD Prontos"
   - [ ] Total: 64 arquivo(s)
   - [ ] Localização: [caminho do diretório]

#### **Resultado Esperado:**
- ✅ Processamento concluído sem erros
- ✅ Log mostra:
  ```
  [HH:MM:SS] 📝 Configuração criada para geração de MD
  [HH:MM:SS] 📄 Processando: Sentenças...json.txt
  [HH:MM:SS]    🐍 Executando script Python...
  [HH:MM:SS]    ✅ Geração MD concluída
  [HH:MM:SS] 🎉 ARQUIVOS MD GERADOS COM SUCESSO!
  [HH:MM:SS] 📊 Total de arquivos MD: 64
  ```
- ✅ Barra de progresso: 100%
- ✅ Status: "✅ Geração de MD concluída!"

---

## 🚀 TESTE 4: REVISÃO MANUAL DE ARQUIVOS MD

### **Objetivo:** Verificar qualidade das keywords geradas

#### **Passos:**
1. [ ] Abrir terminal/navegador de arquivos
2. [ ] Navegar até diretório de saída
3. [ ] Abrir 3-5 arquivos MD aleatórios
4. [ ] Verificar estrutura de cada arquivo:
   - [ ] Sem YAML front matter (metadados removidos)
   - [ ] Conteúdo puro da fundamentação
   - [ ] Sem caracteres especiais de metadados

5. [ ] Para verificar keywords geradas:
   ```bash
   cd /home/user/sentencas_md_teste_v2
   # Listar primeiros 20 caracteres de cada arquivo
   for f in *.md; do echo "=== $f ==="; head -20 "$f"; echo; done | less
   ```

6. [ ] Verificar exemplos de keywords esperadas:
   - [ ] Processo **0000006-73.2023.5.10.0009**:
     - ✅ "instrutor vs professor"
     - ✅ "arts. 317-323 CLT"
     - ✅ "LDB Lei 9.394/1996"
     - ❌ NÃO deve ter: "legislacao", "direito_sindical"

#### **Resultado Esperado:**
- ✅ Arquivos MD contêm apenas conteúdo (sem metadados)
- ✅ Keywords são específicas e contextuais
- ✅ Dispositivos legais são mencionados corretamente
- ✅ Chunking adequado (~2048 caracteres por arquivo)

---

## 🚀 TESTE 5: UPLOAD PARA COLLECTION

### **Objetivo:** Verificar upload com confirmação

#### **Passos:**
1. [ ] Verificar botão "2. Upload para Collection":
   - [ ] Deve estar habilitado (verde) após gerar MD
   - [ ] Texto: "2. Upload para Collection"

2. [ ] Clicar no botão

3. [ ] Verificar diálogo de confirmação:
   - [ ] Título: "Upload para Collection"
   - [ ] Mensagem: "Deseja fazer upload de 64 arquivo(s) para..."
   - [ ] Nome da Collection exibido
   - [ ] Botões: "Cancelar" e "Confirmar"

4. [ ] Clicar em "Confirmar"

5. [ ] Observar processamento:
   - [ ] Tela muda para "Processing View"
   - [ ] Barra de progresso aparece
   - [ ] Log em tempo real
   - [ ] Status: "Upload do arquivo 1/1..."

6. [ ] Aguardar conclusão (~2-5 minutos)

7. [ ] Verificar janela de feedback:
   - [ ] Título: "☁️ Upload Concluído"
   - [ ] Collection: [nome da Collection]
   - [ ] Total de documentos enviados: ~64
   - [ ] Link para xAI Console
   - [ ] Botão: "OK"

8. [ ] Verificar SnackBar verde:
   - [ ] Mensagem: "✅ Upload concluído! Documentos disponíveis na Collection."
   - [ ] Duração: 5 segundos

#### **Resultado Esperado:**
- ✅ Upload concluído sem erros
- ✅ Log mostra:
  ```
  [HH:MM:SS] 📝 Configuração criada para upload
  [HH:MM:SS] 📤 Uploading: Sentenças...json.txt
  [HH:MM:SS]    📤 Executando upload...
  [HH:MM:SS]    ✅ Upload concluído
  [HH:MM:SS] 🎉 UPLOAD CONCLUÍDO COM SUCESSO!
  [HH:MM:SS] 📊 Collection: [nome da Collection]
  ```
- ✅ Barra de progresso: 100%
- ✅ Status: "✅ Upload concluído!"

---

## 🚀 TESTE 6: VERIFICAÇÃO NO xAI CONSOLE

### **Objetivo:** Confirmar que documentos foram indexados

#### **Passos:**
1. [ ] Abrir navegador
2. [ ] Acessar: https://console.x.ai/
3. [ ] Fazer login com conta xAI
4. [ ] Navegar para "Collections"
5. [ ] Selecionar Collection de teste
6. [ ] Verificar estatísticas:
   - [ ] Total de documentos: ~64
   - [ ] Status: "Ready" ou "Indexing"
7. [ ] Testar busca rápida:
   - [ ] Buscar: "professor"
   - [ ] Verificar resultados relevantes
   - [ ] Buscar: "CLT 317"
   - [ ] Verificar resultados relevantes

#### **Resultado Esperado:**
- ✅ Collection contém ~64 documentos
- ✅ Documentos estão indexados
- ✅ Busca retorna resultados relevantes
- ✅ Metadados estão corretos

---

## 🚀 TESTE 7: DROPDOWN DE MODELOS GROK

### **Objetivo:** Verificar seleção de modelo

#### **Passos:**
1. [ ] Clicar no dropdown "Modelo Grok para Keywords"
2. [ ] Verificar opções disponíveis:
   - [ ] `grok-beta` - "Rápido e eficiente (Recomendado)"
   - [ ] `grok-2-1212` - "Melhor qualidade (mais lento)"
   - [ ] `grok-2-vision-1212` - "Com suporte a visão"
3. [ ] Selecionar `grok-2-1212`
4. [ ] Verificar que modelo foi atualizado
5. [ ] Fechar e reabrir app
6. [ ] Verificar se modelo selecionado foi restaurado

#### **Resultado Esperado:**
- ✅ Dropdown mostra 3 modelos
- ✅ Cada modelo tem nome + descrição
- ✅ Seleção é persistida
- ✅ Configuração salva automaticamente

---

## 🚀 TESTE 8: TRATAMENTO DE ERROS

### **Objetivo:** Verificar validações e mensagens de erro

#### **Cenário 1: Tentar gerar MD sem API Key**
1. [ ] Limpar campo "API Key"
2. [ ] Tentar clicar em "1. Gerar Arquivos MD"
3. [ ] Verificar SnackBar vermelho:
   - [ ] "API Key do Grok é obrigatória para gerar keywords"

#### **Cenário 2: Tentar upload sem Management Key**
1. [ ] Gerar MD com sucesso
2. [ ] Limpar campo "Management Key"
3. [ ] Tentar clicar em "2. Upload para Collection"
4. [ ] Verificar SnackBar vermelho:
   - [ ] "Management Key é obrigatória para upload"

#### **Cenário 3: Tentar upload sem gerar MD**
1. [ ] Reiniciar app (limpar estado)
2. [ ] Preencher credenciais
3. [ ] Selecionar arquivos
4. [ ] Tentar clicar em "2. Upload para Collection"
5. [ ] Verificar que botão está desabilitado (cinza)

#### **Resultado Esperado:**
- ✅ Validações impedem ações inválidas
- ✅ Mensagens de erro são claras
- ✅ SnackBars vermelhos para erros críticos
- ✅ Botões desabilitados quando pré-requisitos não atendidos

---

## 📊 CHECKLIST DE VALIDAÇÃO FINAL

### **Funcionalidades Core**
- [ ] ✅ Geração de keywords via LLM (Grok)
- [ ] ✅ Chunking inteligente (2048 chars)
- [ ] ✅ Upload via xAI Collections API
- [ ] ✅ Metadados separados do conteúdo

### **UI Flutter**
- [ ] ✅ Campos de credenciais funcionam
- [ ] ✅ Dropdown de modelos funciona
- [ ] ✅ Dropdown de Collections funciona
- [ ] ✅ File picker funciona
- [ ] ✅ Folder picker funciona
- [ ] ✅ Botão "Gerar MD" funciona
- [ ] ✅ Botão "Upload" funciona
- [ ] ✅ Barra de progresso atualiza
- [ ] ✅ Log em tempo real funciona
- [ ] ✅ Janelas de feedback aparecem
- [ ] ✅ Diálogo de confirmação aparece
- [ ] ✅ Tratamento de erros funciona
- [ ] ✅ Configurações persistem

### **Qualidade de Keywords**
- [ ] ✅ Keywords são específicas (não genéricas)
- [ ] ✅ Dispositivos legais são mencionados
- [ ] ✅ Conceitos jurídicos são extraídos
- [ ] ✅ Súmulas/leis/decretos são identificados

---

## 🐛 PROBLEMAS CONHECIDOS E SOLUÇÕES

### **Problema 1: Collections não carregam**
**Causa:** Management Key inválida ou expirada  
**Solução:**
1. Verificar Management Key no xAI Console
2. Regenerar chave se necessário
3. Verificar log para mensagem de erro específica

### **Problema 2: Script Python não encontrado**
**Causa:** `CollectionUploaderV2.py` não está em `/home/user/`  
**Solução:**
```bash
# Verificar localização
ls -l /home/user/CollectionUploaderV2.py

# Se necessário, mover para local correto
mv CollectionUploaderV2.py /home/user/
```

### **Problema 3: Erro durante upload**
**Causa:** Collection ID inválida ou inexistente  
**Solução:**
1. Recarregar Collections (botão refresh)
2. Verificar se Collection existe no xAI Console
3. Recriar Collection se necessário

### **Problema 4: Keywords genéricas**
**Causa:** Modelo Grok não está gerando keywords contextuais  
**Solução:**
1. Tentar modelo `grok-2-1212` (mais lento, melhor qualidade)
2. Verificar se prompt de keywords está correto no script Python
3. Revisar logs para mensagens de erro da API Grok

---

## 📝 RELATÓRIO DE TESTE (Template)

### **Informações do Teste**
- Data: _______________
- Testador: _______________
- Versão: 2.1

### **Resultados**
- [ ] TESTE 1: Configuração Inicial - ✅ Passou / ❌ Falhou
- [ ] TESTE 2: Seleção de Arquivos - ✅ Passou / ❌ Falhou
- [ ] TESTE 3: Geração de MD - ✅ Passou / ❌ Falhou
- [ ] TESTE 4: Revisão Manual - ✅ Passou / ❌ Falhou
- [ ] TESTE 5: Upload - ✅ Passou / ❌ Falhou
- [ ] TESTE 6: Verificação xAI - ✅ Passou / ❌ Falhou
- [ ] TESTE 7: Dropdown Modelos - ✅ Passou / ❌ Falhou
- [ ] TESTE 8: Tratamento de Erros - ✅ Passou / ❌ Falhou

### **Observações**
_______________________________________________
_______________________________________________
_______________________________________________

### **Problemas Encontrados**
_______________________________________________
_______________________________________________
_______________________________________________

### **Status Final**
- [ ] ✅ SISTEMA APROVADO
- [ ] ⚠️ SISTEMA APROVADO COM RESSALVAS
- [ ] ❌ SISTEMA REPROVADO

---

**Boa sorte nos testes! 🚀**
