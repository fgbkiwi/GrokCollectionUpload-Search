# 🎨 Collection Uploader V2 - Flutter UI (Versão Atualizada)

**Data:** 20 de Janeiro de 2025  
**Versão:** 2.1 (com feedback avançado e menus suspensos)

---

## 📋 Recursos Implementados

### ✅ 1. Janela de Feedback Detalhada

A UI agora possui **feedback completo** em tempo real durante todas as operações:

#### **Durante Processamento:**
- ✅ **Barra de progresso** mostrando percentual de conclusão (0-100%)
- ✅ **Log de processamento** estilo terminal (fundo preto, texto verde)
- ✅ **Status em tempo real** com mensagens descritivas:
  - "Gerando MD do arquivo 1/3..."
  - "Upload do arquivo 2/3..."
  - Logs timestamped: `[19:45:32] ✅ 3 Collection(s) encontrada(s)`

#### **Após Geração de MD:**
- ✅ **Janela de feedback** automática com:
  - Total de arquivos MD criados
  - Localização dos arquivos
  - Informação sobre keywords inteligentes
  - Botões de ação: "OK" ou "Upload Agora"

#### **Após Upload:**
- ✅ **Janela de confirmação** com:
  - Nome da Collection de destino
  - Total de documentos enviados
  - Link para verificar no xAI Console
  - SnackBar de sucesso (verde, 5 segundos)

---

### ✅ 2. Menus Suspensos (Dropdowns)

#### **Menu 1: Modelo Grok para Keywords**
```dart
DropdownButtonFormField<String>(
  value: _selectedModel,
  items: [
    'grok-beta' → 'Rápido e eficiente (Recomendado)',
    'grok-2-1212' → 'Melhor qualidade (mais lento)',
    'grok-2-vision-1212' → 'Com suporte a visão',
  ],
)
```

**Características:**
- ✅ Exibe nome do modelo e descrição
- ✅ Modelo padrão: `grok-beta`
- ✅ Configuração persistente (salva preferência)
- ✅ Ícone: `psychology` (cérebro)

#### **Menu 2: Collection para Upload**
```dart
DropdownButtonFormField<String>(
  value: _selectedCollectionId,
  items: _availableCollections.map((collection) {
    return DropdownMenuItem(
      value: collection['id'],
      child: Column(
        children: [
          Text(collection['name']),  // Nome da Collection
          Text('ID: ${collection['id']}'),  // ID (em cinza)
        ],
      ),
    );
  }).toList(),
)
```

**Características:**
- ✅ Carrega Collections automaticamente da xAI API
- ✅ Exibe nome e ID de cada Collection
- ✅ Botão "Carregar Collections" manual se necessário
- ✅ Configuração persistente (restaura última seleção)
- ✅ Ícone: `collections_bookmark`

---

### ✅ 3. Botões Separados (Fluxo em 2 Etapas)

#### **Botão 1: Gerar Arquivos MD**
```dart
ElevatedButton.icon(
  onPressed: _generateMdFiles,
  icon: Icon(Icons.create),
  label: Text('1. Gerar Arquivos MD'),
  style: ElevatedButton.styleFrom(
    backgroundColor: Colors.blue,  // Azul
    padding: EdgeInsets.symmetric(vertical: 20),
  ),
)
```

**Função:**
- ✅ Processa JSON → gera arquivos MD localmente
- ✅ Usa Grok API para gerar keywords inteligentes
- ✅ Salva arquivos no diretório de saída
- ✅ Mostra feedback com estatísticas
- ✅ **NÃO faz upload** - permite revisão manual

**Validação:**
- Requer API Key do Grok
- Requer arquivo(s) JSON selecionado(s)
- Requer diretório de saída

#### **Botão 2: Upload para Collection**
```dart
ElevatedButton.icon(
  onPressed: _uploadToCollection,
  icon: Icon(Icons.cloud_upload),
  label: Text('2. Upload para Collection'),
  style: ElevatedButton.styleFrom(
    backgroundColor: Colors.green,  // Verde
    padding: EdgeInsets.symmetric(vertical: 20),
  ),
)
```

**Função:**
- ✅ Faz upload dos arquivos MD gerados
- ✅ Envia para Collection selecionada
- ✅ Exibe confirmação antes do upload
- ✅ Mostra feedback de sucesso
- ✅ **Habilitado APENAS após geração de MD**

**Validação:**
- Requer Management Key
- Requer Collection selecionada
- Requer arquivos MD gerados previamente

---

## 🎯 Fluxo de Uso Completo

### **1. Configuração Inicial**
1. Informe **Management Key** (xAI Collections)
2. Clique no ícone de "nuvem com seta" para carregar Collections
3. Informe **API Key** (Grok)
4. Selecione **modelo Grok** no dropdown (padrão: grok-beta)
5. Selecione **Collection** de destino no dropdown

### **2. Seleção de Arquivos**
1. Clique em "Arquivos JSON de Sentenças"
   - Selecione múltiplos arquivos JSON (Ctrl+Clique)
   - Suporta extensões: `.json`, `.txt`
2. Clique em "Diretório de Saída (MD)"
   - Escolha onde salvar os arquivos MD gerados

### **3. Geração de MD (Etapa 1)**
1. Clique em **"1. Gerar Arquivos MD"** (botão azul)
2. Aguarde processamento:
   - Log em tempo real mostra progresso
   - Barra de progresso indica percentual
3. Janela de feedback aparece:
   - Total de arquivos criados
   - Localização dos arquivos
   - Opção: "OK" ou "Upload Agora"

### **4. Revisão Manual (Opcional)**
- Navegue até o diretório de saída
- Abra arquivos MD com editor de texto
- Verifique:
  - Qualidade das keywords geradas
  - Estrutura dos metadados
  - Conteúdo das fundamentações
  - Chunking adequado (2048 chars)

### **5. Upload (Etapa 2)**
1. Clique em **"2. Upload para Collection"** (botão verde)
2. Confirme o upload no diálogo
3. Aguarde processamento:
   - Log mostra uploads em tempo real
   - Barra de progresso indica percentual
4. Janela de feedback aparece:
   - Nome da Collection
   - Total de documentos enviados
   - Link para xAI Console
5. SnackBar verde confirma sucesso

---

## 📊 Indicadores Visuais

### **Status dos Botões**
- 🔵 **Botão Azul** (Gerar MD):
  - ✅ Habilitado: JSON e diretório selecionados
  - ❌ Desabilitado (cinza): faltam requisitos

- 🟢 **Botão Verde** (Upload):
  - ✅ Habilitado: MD gerados + Collection selecionada
  - ❌ Desabilitado (cinza): gere MD primeiro

### **Card de Status (Após Gerar MD)**
```
┌─────────────────────────────────────┐
│ ✅ Arquivos MD Prontos              │
│                                     │
│ Total: 64 arquivo(s)                │
│ Localização: /home/user/sentencas_md│
└─────────────────────────────────────┘
```

### **Ícones e Cores**
- 🔑 Management Key → `key` (amarelo)
- 🔐 API Key → `vpn_key` (azul)
- 🧠 Modelo → `psychology` (roxo)
- 📚 Collection → `collections_bookmark` (verde)
- 📄 JSON → `insert_drive_file` (cinza)
- 📁 Diretório → `folder_open` (laranja)
- ✅ Sucesso → `check_circle` (verde)
- ☁️ Upload → `cloud_upload` (verde)

---

## 🔄 Logs e Feedback

### **Formato de Logs**
```
[19:45:32] 🔍 Carregando Collections disponíveis...
[19:45:33] ✅ 3 Collection(s) encontrada(s)
[19:45:35] ✅ 2 arquivo(s) JSON selecionado(s)
[19:45:40] 📝 Configuração criada para geração de MD

[19:45:42] 📄 Processando: Sentenças.json
[19:45:42]    🐍 Executando script Python (geração MD)...
[19:45:50]    ✅ Geração MD concluída

[19:45:51] 🎉 ARQUIVOS MD GERADOS COM SUCESSO!
[19:45:51] 📊 Total de arquivos MD: 64
[19:45:51] 📁 Localização: /home/user/sentencas_md_test
```

---

## 🛡️ Validações e Tratamento de Erros

### **Validação de Geração MD**
```dart
if (_apiKeyController.text.isEmpty) {
  ❌ 'API Key do Grok é obrigatória para gerar keywords'
}
if (_selectedJsonFiles.isEmpty) {
  ❌ 'Selecione pelo menos um arquivo JSON'
}
if (_outputDirectory == null) {
  ❌ 'Selecione o diretório de saída'
}
```

### **Validação de Upload**
```dart
if (_managementKeyController.text.isEmpty) {
  ❌ 'Management Key é obrigatória para upload'
}
if (_selectedCollectionId == null) {
  ❌ 'Selecione uma Collection'
}
if (_generatedMdFiles.isEmpty) {
  ❌ 'Gere os arquivos MD primeiro antes de fazer upload'
}
```

### **Tratamento de Erros**
- ✅ SnackBar vermelho para erros críticos
- ✅ Card laranja para avisos (ex: "Nenhuma Collection encontrada")
- ✅ Logs detalhados no terminal (stderr capturado)
- ✅ Botão "Voltar" após conclusão com erro

---

## 📦 Configurações Persistentes

As seguintes configurações são salvas automaticamente:

- ✅ Management Key (obscurecida)
- ✅ API Key (obscurecida)
- ✅ Modelo Grok selecionado
- ✅ Collection selecionada (ID)
- ✅ Diretório de saída
- ✅ Preferência de salvar MD local

**Armazenamento:** `SharedPreferences` (persistente entre sessões)

---

## 🚀 Como Executar

### **Opção 1: Linux Desktop**
```bash
cd /home/user/collection_uploader_app
flutter run -d linux
```

### **Opção 2: Web (Chrome)**
```bash
cd /home/user/collection_uploader_app
flutter run -d chrome
```

### **Opção 3: Build Release (Linux)**
```bash
cd /home/user/collection_uploader_app
flutter build linux --release
./build/linux/x64/release/bundle/collection_uploader
```

---

## 📝 Requisitos

### **Dependências Flutter**
```yaml
dependencies:
  flutter:
    sdk: flutter
  file_picker: ^8.1.6
  shared_preferences: 2.5.3
  http: 1.5.0
  process_run: ^1.2.4
```

### **Script Python Backend**
- Localização: `/home/user/CollectionUploaderV2.py`
- Requer: `python3`, `requests`, `xai-sdk`

### **Credenciais xAI**
- Management Key (xai-mgmt-...)
- API Key (xai-...)
- Collection ID (obtido via API)

---

## 🎨 Design e UX

### **Material Design 3**
- ✅ ColorScheme adaptativo (light/dark)
- ✅ Botões elevados com ícones
- ✅ Cards com sombras
- ✅ Transições suaves

### **Acessibilidade**
- ✅ Tooltips em todos os ícones
- ✅ Contraste adequado de cores
- ✅ Textos de ajuda descritivos
- ✅ Feedback visual e textual

### **Responsividade**
- ✅ SingleChildScrollView para telas pequenas
- ✅ Padding consistente (24px)
- ✅ Botões com altura mínima (20px vertical)

---

## 🔍 Diferenças V1 → V2.1

| Recurso | V1 | V2.1 |
|---------|----|----|
| **Janela de Feedback** | ❌ Não | ✅ Sim (completa) |
| **Menu Modelo Grok** | ❌ Fixo | ✅ Dropdown com 3 opções |
| **Menu Collection** | ❌ Campo texto | ✅ Dropdown dinâmico |
| **Botões Separados** | ❌ Um botão | ✅ Dois botões (MD + Upload) |
| **Log em Tempo Real** | ⚠️ Básico | ✅ Terminal estilo hacker |
| **Validação de Etapas** | ⚠️ Parcial | ✅ Validação completa |
| **Confirmação de Upload** | ❌ Não | ✅ Diálogo de confirmação |
| **Estatísticas MD** | ❌ Não | ✅ Card de status verde |
| **Auto-load Collections** | ❌ Não | ✅ Automático ao iniciar |
| **Persistência Config** | ⚠️ Parcial | ✅ Completa (SharedPrefs) |

---

## 📚 Recursos Adicionais

### **Documentação Relacionada**
- `README_V2.md` - Visão geral do sistema
- `COMPARACAO_V1_V2.md` - Diferenças entre versões
- `ENTREGA_V2_FINAL.md` - Relatório de entrega
- `config_example.json` - Exemplo de configuração Python

### **Scripts Python**
- `CollectionUploaderV2.py` - Backend principal
- `requirements_uploader.txt` - Dependências Python

---

## ✨ Próximas Melhorias Sugeridas

### **Versão 2.2 (Futuro)**
- ⏳ Estimativa de tempo de processamento
- 📊 Gráfico de distribuição de keywords
- 🔍 Visualização de MD inline (sem abrir pasta)
- 📤 Exportação de estatísticas (CSV/JSON)
- 🌐 Modo web completo (sem processo Python)
- 🔔 Notificações desktop (sucesso/erro)
- 📱 Suporte Android/iOS (mobile app)

---

## 🎯 Conclusão

A UI Flutter V2.1 implementa **TODOS** os requisitos solicitados:

✅ **Janela de feedback** com informações de execução  
✅ **Menu suspenso** para modelo Grok  
✅ **Menu suspenso** para seleção de Collection  
✅ **Botões separados** para Gerar MD e Upload  
✅ **Fluxo em 2 etapas** permite revisão manual  
✅ **Logs em tempo real** estilo terminal  
✅ **Validações completas** em cada etapa  
✅ **Configurações persistentes** entre sessões  

**Status:** ✅ **CONCLUÍDO E TESTADO**

---

**Desenvolvido para:** Sistema de Busca Semântica de Precedentes Trabalhistas  
**Tribunal:** Tribunal Regional do Trabalho da 10ª Região  
**Tecnologias:** Flutter 3.35.4, Dart 3.9.2, xAI Collections API, Grok LLM
