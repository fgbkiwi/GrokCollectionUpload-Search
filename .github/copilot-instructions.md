# AI Coding Agent Instructions for Grok Collection Upload & Search System

## Project Overview
A complete system for semantic search and indexing of Brazilian labor law precedents using **xAI Collections API** and **Grok LLM**. The system processes legal documents (sentenças trabalhistas), generates metadata-enriched Markdown files, uploads to xAI Collections, and provides an interactive search interface.

**Target Users:** Labor court judges (TRT-10), legal researchers  
**Key Technologies:** Python, Flet UI, xAI API, Flutter (legacy)

---

## Architecture & Data Flow

### Three Core Components

1. **CollectionUploaderV2.py** (CLI uploader - CURRENT)
   - Accepts JSON file of legal sentences
   - Generates keywords via Grok LLM (contextual, not fixed patterns)
   - Creates chunked Markdown files with YAML front matter
   - Uploads directly to xAI Collections API

2. **PrecedenteSearchApp.py** (Search UI - PRIMARY APP)
   - Flet-based interactive search interface
   - Lists available Collections for selection
   - Hybrid search: semantic (embedding-based) + keyword filters
   - Persistent config storage (JSON)
   - Real-time web/X search integration

3. **CollectionUploaderV2UI.py** (Flet GUI uploader - LEGACY)
   - Desktop wrapper around V2 processing
   - File picker via tkinter.filedialog
   - Real-time feedback window with colored logs

**Data Flow:**
```
JSON Input → Grok Keywords + Chunking → Markdown Files → xAI Upload → Collections
                                              ↓
                                         Local Storage
                                              ↓
                                    PrecedenteSearchApp (Search UI)
```

---

## Critical Patterns & Conventions

### JSON Input Format
All sentence JSON must follow this structure:
```json
{
  "categoria": "HORAS EXTRAORDINÁRIAS",
  "reclamada": "Empresa LTDA",
  "conteudo": "Texto da fundamentação jurídica...",
  "numero_processo": "0000123-45.2023.5.10.0009",
  "data_publicacao": "2023-06-15",
  "tipo_acao": "Reclamação Trabalhista"
}
```

### Markdown Output Format
Generated files use YAML front matter + content (no chunking within single file):
```markdown
---
categoria: ADICIONAL DE INSALUBRIDADE
reclamada: Empresa XYZ LTDA
numero_processo: 0000006-73.2023.5.10.0009
data_publicacao: 2023-11-17
tipo_acao: Reclamação Trabalhista
keywords: art. 192 CLT, insalubridade, adicional, grau médio
---
# INSALUBRIDADE

[Content of fundamentação...]
```

### Chunking Strategy (DO NOT CHANGE)
- **Chunk Size:** 2048 characters (~512 tokens) - covers 90.9% of corpus in 1 chunk
- **Overlap:** 256 characters (12.5%) - preserves context at breaks
- **Break Point:** Sentence endings (`.`, `!`, `?`) - maintains legal terminology integrity
- **Rationale:** Based on corpus statistics (mean 1,973 chars, max 54,685 chars)

### Keyword Generation Approach
- **Method:** LLM-based (NOT regex patterns) using Grok
- **Specificity:** Extract actual articles ("art. 317 CLT", NOT "CLT")
- **Limit:** 10-15 keywords per document (enforced in code)
- **Fallback:** Returns only category if API fails (graceful degradation)

---

## Developer Workflows

### Running Uploader (V2)
```bash
# Requires: Python 3.7+, requests library
# Deps: pip install requests

python CollectionUploaderV2.py --config config.json
```

**Required `config.json` structure:**
```json
{
  "api_key": "xai_api_key_here",
  "management_key": "xai_management_key",
  "collection_id": "col_xxxxx",
  "model": "grok-beta",
  "input_file": "sentenças.json",
  "output_dir": "./sentencas_md"
}
```

### Running Search App (Primary Interface)
```bash
# Requires: Flet, requests, pyperclip
# Deps: pip install -r requirements_app.txt

python PrecedenteSearchApp.py
```

### Testing
No formal test suite exists. **Manual testing approach:**
- Sample data: [sentencas_md_test_sample/](sentencas_md_test_sample/) (3 example .md files)
- Verify chunking with [GUIA_TESTE_V2.1.md](GUIA_TESTE_V2.1.md)
- Config validation in [CollectionUploaderV2.py](CollectionUploaderV2.py) lines ~380-400

---

## Integration Points & APIs

### xAI Collections API
- **Endpoint:** `https://api.x.ai/v1`
- **Auth:** Bearer token (API key in headers)
- **Methods Used:**
  - `POST /collections/{collection_id}/documents` - upload
  - `GET /collections` - list (management key required)
- **Error Handling:** Retries with exponential backoff (3 attempts max)

### Grok LLM Integration
- **Model:** `grok-beta` (default), `grok-2-1212` (production)
- **Use Case:** Generate contextual keywords (not general chat)
- **Temp:** 0.3 (low) for consistency, 0.7 for search app responses
- **Prompt Pattern:** See [CollectionUploaderV2.py](CollectionUploaderV2.py) lines ~50-85

### Config Persistence
- **Storage:** JSON files in app directory
- **Files:** `config.json`, `app_config.json`
- **Pattern:** Load defaults, merge with saved config (prefer saved values)

---

## Domain-Specific Knowledge

### Brazilian Labor Law (CLT)
- **CLT** = Consolidação das Leis do Trabalho (labor code)
- **TST** = Tribunal Superior do Trabalho (superior labor court)
- **TRT** = Tribunal Regional do Trabalho (regional court, e.g., TRT-10 for Brasília)
- **Common Categories:** HORAS EXTRAORDINÁRIAS, INSALUBRIDADE, JUSTA CAUSA, EQUIPARAÇÃO SALARIAL
- **Keywords Must Include:** Specific article citations (e.g., "art. 461 CLT") not just "CLT"

### Legal Document Structure
- **Metadata Extraction:** Must preserve exact process numbers, company names, publication dates
- **Chunking Risk:** Legal reasoning can span 10K+ chars; split preserves reference integrity
- **Keywords:** Focus on statutory law (articles, laws) + jurisprudence (súmulas, court decisions)

---

## Common Issues & Solutions

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| Grok keyword generation fails | API rate limit or timeout | Implements 3-retry with 2s backoff |
| Keywords are generic ("CLT", "direito") | Poor prompt specificity | Ensure prompt requests article numbers |
| Chunk overflow in Collections | Misunderstanding chunk size | xAI chunks separately; our 2048 is pre-chunking |
| Config keys disappear after restart | Not saving config (old UI) | Always call `config.save_config()` after update |
| File picker crashes on Linux | Tkinter not available | Use tkinter.filedialog (installed as dep) or fallback to manual path |

---

## Key Files Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| [CollectionUploaderV2.py](CollectionUploaderV2.py) | Core uploader logic | `GrokKeywordGenerator`, `XAICollectionsUploader`, `SentenceProcessor` |
| [PrecedenteSearchApp.py](PrecedenteSearchApp.py) | Search UI (Flet) | `ConfigManager`, `XAIClient`, `ChatInterface` |
| [CollectionUploaderV2UI.py](CollectionUploaderV2UI.py) | GUI wrapper (legacy) | `CollectionUploaderV2UI` |
| [sentencas_md_test_sample/](sentencas_md_test_sample/) | Test data | 3 example Markdown files with correct structure |

---

## Asking for Help / Feedback

When making changes, ensure:
1. ✅ Keywords are generated by LLM (not hardcoded regex) with fallback to category only
2. ✅ Chunk size stays 2048 chars (validate in `processor.chunk_text()`)
3. ✅ Config persistence works: save → restart → load should restore all values
4. ✅ xAI API errors include retry logic with exponential backoff
5. ✅ File paths use `pathlib.Path` for cross-platform compatibility
