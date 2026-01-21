# 🎯 GUIA COMPLETO - Como Usar o Sistema

**Última Atualização:** 21 de Janeiro de 2025

---

## 📦 O SISTEMA TEM 2 COMPONENTES SEPARADOS

### **1️⃣ COLLECTION UPLOADER (Upload de Documentos)**
- **Interface:** Flutter (UI gráfica moderna)
- **Backend:** Python (CLI - executado automaticamente pela UI)
- **Função:** Gerar arquivos MD e fazer upload para xAI Collections

### **2️⃣ PRECEDENTE SEARCH (Busca de Precedentes)**
- **Interface:** Flet (UI Python)
- **Função:** Buscar precedentes nas Collections usando Grok

---

## 🚀 COMO USAR: COLLECTION UPLOADER

### **OPÇÃO 1: Flutter UI (RECOMENDADO ⭐)**

Esta é a interface gráfica completa com todos os recursos solicitados.

#### **Pré-requisitos:**
```bash
# Instalar Flutter (se ainda não tiver)
# Windows: https://docs.flutter.dev/get-started/install/windows
# Linux: https://docs.flutter.dev/get-started/install/linux
# macOS: https://docs.flutter.dev/get-started/install/macos

# Verificar instalação
flutter doctor
```

#### **Executar:**
```bash
# 1. Navegar para o diretório
cd GrokCollectionUpload-Search/collection_uploader_app

# 2. Instalar dependências
flutter pub get

# 3. Executar aplicação
flutter run -d linux    # Linux
flutter run -d windows  # Windows
flutter run -d macos    # macOS
flutter run -d chrome   # Web (navegador)
```

#### **Usar a Interface:**

1. **Preencher credenciais:**
   - Management Key (xai-mgmt-...)
   - API Key (xai-...)

2. **Configurar:**
   - Clicar no ícone de "nuvem" para carregar Collections
   - Selecionar modelo Grok no dropdown
   - Selecionar Collection no dropdown

3. **Selecionar arquivos:**
   - Escolher arquivo(s) JSON de sentenças
   - Escolher diretório de saída para MD

4. **Gerar MD:**
   - Clicar "1. Gerar Arquivos MD" (botão azul)
   - Aguardar processamento (log em tempo real)

5. **Revisar (opcional):**
   - Abrir diretório de saída
   - Verificar qualidade dos arquivos MD

6. **Upload:**
   - Clicar "2. Upload para Collection" (botão verde)
   - Confirmar no diálogo
   - Aguardar conclusão

---

### **OPÇÃO 2: Python CLI (Linha de Comando)**

Use esta opção se preferir linha de comando ou não puder instalar Flutter.

#### **Pré-requisitos:**
```bash
# Instalar dependências Python
cd GrokCollectionUpload-Search
pip install -r requirements_uploader.txt
```

#### **Configurar:**

Crie um arquivo `config.json` baseado no exemplo:

```bash
cp config_example.json config.json
```

Edite `config.json` com suas credenciais:

```json
{
  "grok_api_key": "xai-...",
  "management_key": "xai-mgmt-...",
  "collection_id": "col_...",
  "grok_model": "grok-beta",
  "output_dir": "./md_output",
  "save_local_md": true,
  "upload_enabled": true
}
```

#### **Executar:**

```bash
# Processar e fazer upload
python3 CollectionUploaderV2.py \
  --config config.json \
  --input sentencas.json

# Ou processar múltiplos arquivos
python3 CollectionUploaderV2.py \
  --config config.json \
  --input "arquivo1.json,arquivo2.json,arquivo3.json"
```

#### **Parâmetros do Script:**

```
--config CONFIG_FILE       # Arquivo de configuração JSON (obrigatório)
--input INPUT_FILES        # Arquivo(s) JSON separados por vírgula (obrigatório)
--output-dir OUTPUT_DIR    # Sobrescreve output_dir do config (opcional)
```

---

## 🔍 COMO USAR: PRECEDENTE SEARCH (Busca)

Este componente **SIM tem interface Flet**.

### **Pré-requisitos:**
```bash
# Instalar dependências
cd GrokCollectionUpload-Search
pip install -r requirements_app.txt
```

### **Executar:**

```bash
python3 PrecedenteSearchApp.py
```

### **Interface Flet:**

A aplicação abrirá uma janela gráfica (Flet) com:

1. **Tela de Configuração:**
   - Management Key
   - Grok API Key
   - Modelo Grok
   - System prompt
   - Temperatura
   - Toggles: Real-time Search, URL Citation, Tema escuro

2. **Tela Principal:**
   - Chat com o modelo Grok
   - Botão para limpar chat
   - Botão para copiar chat
   - Anexar arquivo ao contexto
   - Dropdown para selecionar Collection
   - Toggle para habilitar busca na Collection
   - Textarea para interação

---

## 📊 COMPARAÇÃO DAS INTERFACES

| Aspecto | Flutter UI | Python CLI | Flet App |
|---------|-----------|-----------|----------|
| **Componente** | Collection Uploader | Collection Uploader | Precedente Search |
| **Interface Gráfica** | ✅ Sim (moderna) | ❌ Não (linha de comando) | ✅ Sim (Flet) |
| **Feedback Visual** | ✅ Janelas, logs, progresso | ⚠️ Texto no terminal | ✅ Chat interativo |
| **Facilidade de Uso** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Configuração** | ✅ Persistente (salva) | ⚠️ Manual (config.json) | ✅ Persistente |
| **Validações** | ✅ Completas | ⚠️ Básicas | ✅ Completas |
| **Multiplataforma** | ✅ Win/Mac/Linux/Web | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux |

---

## 🎯 WORKFLOW COMPLETO

### **Fase 1: Upload de Documentos (Collection Uploader)**

Use **Flutter UI** ou **Python CLI** para:

1. Gerar arquivos MD com keywords inteligentes
2. Fazer upload para xAI Collections
3. Indexar documentos para busca semântica

### **Fase 2: Busca de Precedentes (Precedente Search)**

Use **Flet App** para:

1. Conectar à Collection indexada
2. Fazer perguntas ao Grok
3. Buscar precedentes relevantes
4. Obter respostas com citações

---

## 📂 ESTRUTURA DE ARQUIVOS

```
GrokCollectionUpload-Search/
│
├── 📁 collection_uploader_app/      # ⭐ Flutter UI (Upload)
│   └── lib/main.dart                # Interface gráfica
│
├── 📄 CollectionUploaderV2.py       # Python CLI (Upload)
│
├── 📄 PrecedenteSearchApp.py        # ⭐ Flet App (Busca)
│
├── 📄 requirements_uploader.txt     # Deps para Upload
├── 📄 requirements_app.txt          # Deps para Busca
│
└── 📄 config_example.json           # Exemplo de config
```

---

## 🔧 TROUBLESHOOTING

### **Problema: Flutter não instalado**

**Solução:**
- Baixe Flutter em: https://flutter.dev/docs/get-started/install
- Ou use Python CLI (opção 2)

### **Problema: Dependências Python não instaladas**

**Solução:**
```bash
pip install -r requirements_uploader.txt  # Para Upload
pip install -r requirements_app.txt       # Para Busca
```

### **Problema: CollectionUploaderV2.py não encontrado**

**Solução:**
```bash
# Verificar se está no diretório correto
cd GrokCollectionUpload-Search
ls -la CollectionUploaderV2.py
```

### **Problema: PrecedenteSearchApp.py não abre interface**

**Solução:**
```bash
# Verificar se Flet está instalado
pip install flet>=0.24.0

# Executar novamente
python3 PrecedenteSearchApp.py
```

---

## 📖 DOCUMENTAÇÃO ADICIONAL

Consulte estes arquivos no repositório:

1. **README_MAIN.md** - Overview do sistema
2. **ENTREGA_V2.1_FINAL.md** - Relatório completo
3. **UI_FLUTTER_FEATURES.md** - Documentação da Flutter UI
4. **GUIA_TESTE_V2.1.md** - Guia de testes
5. **QUICKSTART.md** - Guia rápido

---

## 🎯 RESUMO

### **Para UPLOAD de documentos:**
- ✅ Use **Flutter UI** (collection_uploader_app) - Interface gráfica moderna
- ⚠️ Ou use **Python CLI** (CollectionUploaderV2.py) - Linha de comando

### **Para BUSCA de precedentes:**
- ✅ Use **Flet App** (PrecedenteSearchApp.py) - Interface gráfica Flet

### **NÃO existe:**
- ❌ Interface Flet para CollectionUploader
- ❌ Interface Flutter para PrecedenteSearch

---

## ❓ DÚVIDAS FREQUENTES

**Q: Por que o CollectionUploader não tem interface Flet?**  
**A:** A especificação do projeto solicitou uma UI Flutter completa com recursos específicos (menus suspensos, janelas de feedback, botões separados). O Flet foi usado apenas para o componente de busca.

**Q: Posso usar Python CLI em vez de Flutter?**  
**A:** Sim! O Python CLI (CollectionUploaderV2.py) tem todas as funcionalidades, mas sem a interface gráfica.

**Q: Qual é mais fácil de usar?**  
**A:** Flutter UI é mais intuitiva e visual. Python CLI é mais rápida para quem prefere linha de comando.

---

**🚀 Escolha a interface que preferir e comece a usar!**
