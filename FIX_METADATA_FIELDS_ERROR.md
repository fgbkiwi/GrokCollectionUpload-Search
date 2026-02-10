# Fix: Unknown Field Error in xAI Collections

## ✅ Good News: VPN Worked!

The Cloudflare `cf-ipcity` error is **GONE**. Now you have a different issue: missing metadata field definitions.

---

## 🐛 Current Error

```
500 - gRPC UploadDocument failed: rpc error: code = InvalidArgument desc = 
Unknown field 'keywords'. This field is not defined in the collection's field_definitions.

500 - gRPC UploadDocument failed: rpc error: code = InvalidArgument desc = 
Unknown field 'original_filename'. This field is not defined in the collection's field_definitions.
```

**Root Cause:** Your xAI Collection doesn't have `keywords` and `original_filename` fields defined in its schema.

---

## 🔧 Solution 1: Define Fields in xAI Console (RECOMMENDED)

### Step 1: Go to xAI Console
1. Visit: https://console.x.ai/
2. Navigate to your Collection
3. Go to **Settings** → **Metadata Fields**

### Step 2: Add Required Fields

Add these fields to your Collection:

#### Field 1: `keywords`
- **Field Name:** `keywords`
- **Type:** `array` (or `text` if array not supported)
- **Description:** "Palavras-chave jurídicas extraídas automaticamente"
- **Searchable:** ✅ Yes
- **Filterable:** ✅ Yes (optional)

#### Field 2: `original_filename`
- **Field Name:** `original_filename`
- **Type:** `string`
- **Description:** "Nome original do arquivo MD"
- **Searchable:** ❌ No
- **Filterable:** ❌ No

### Step 3: Keep Existing Fields
Make sure these are also defined (they should already exist):
- `categoria` (string)
- `reclamada` (string)
- `numero_processo` (string)
- `data_publicacao` (string or date)
- `tipo_acao` (string)
- `chunk_info` (string, optional)

### Step 4: Save and Retry Upload

After adding fields, retry your upload. It should work immediately.

---

## 🔧 Solution 2: Modify Uploader to Remove Extra Fields (QUICK FIX)

If you can't modify Collection settings, remove these fields from metadata:

### Option A: Use Simplified Metadata Script

Create `upload_simple_metadata.py`:

```python
#!/usr/bin/env python3
"""
Upload with only Collection-defined metadata fields.
Removes 'keywords' and 'original_filename' if Collection doesn't support them.
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

class SimpleMetadataUploader:
    """Uploader that only uses Collection-defined fields."""
    
    def __init__(self, management_key: str, collection_id: str):
        self.management_key = management_key
        self.collection_id = collection_id
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
        }
    
    def get_collection_schema(self) -> Dict[str, Any]:
        """Get Collection's field definitions."""
        response = requests.get(
            f"{self.base_url}/collections/{self.collection_id}",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract defined fields
        field_defs = data.get('field_definitions', {})
        return field_defs
    
    def filter_metadata(self, metadata: Dict[str, Any], allowed_fields: set) -> Dict[str, Any]:
        """Keep only Collection-defined fields."""
        return {k: v for k, v in metadata.items() if k in allowed_fields}
    
    def upload_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload with filtered metadata."""
        
        # Get Collection schema
        schema = self.get_collection_schema()
        allowed_fields = set(schema.keys())
        
        print(f"   ℹ️ Collection supports fields: {allowed_fields}")
        
        # Filter metadata
        filtered_metadata = self.filter_metadata(metadata, allowed_fields)
        
        print(f"   ℹ️ Using metadata fields: {set(filtered_metadata.keys())}")
        
        payload = {
            "collection_id": self.collection_id,
            "content": content,
            "metadata": filtered_metadata
        }
        
        if document_id:
            payload["document_id"] = document_id
        
        response = requests.post(
            f"{self.base_url}/collections/documents",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()


# Usage example
if __name__ == "__main__":
    uploader = SimpleMetadataUploader(
        management_key="your_key",
        collection_id="col_xxx"
    )
    
    # Test upload
    result = uploader.upload_document(
        content="Test content",
        metadata={
            "categoria": "TEST",
            "reclamada": "Test Co",
            "numero_processo": "0000000-00.0000.0.00.0000",
            "data_publicacao": "2024-01-01",
            "tipo_acao": "Test",
            "keywords": ["test"],  # Will be filtered out if not defined
            "original_filename": "test.md"  # Will be filtered out if not defined
        }
    )
    print(f"✅ Upload successful: {result}")
```

### Option B: Modify Your Existing Uploader

Edit the metadata section in your uploader code to only include basic fields:

```python
# Before (causes error):
metadata = {
    "categoria": categoria,
    "reclamada": item['reclamada'],
    "numero_processo": item['numero_processo'],
    "data_publicacao": item['data_publicacao'],
    "tipo_acao": item['tipo_acao'],
    "keywords": keywords,  # ❌ Not defined in Collection
    "original_filename": filename  # ❌ Not defined in Collection
}

# After (works):
metadata = {
    "categoria": categoria,
    "reclamada": item['reclamada'],
    "numero_processo": item['numero_processo'],
    "data_publicacao": item['data_publicacao'],
    "tipo_acao": item['tipo_acao']
}
```

---

## 🔧 Solution 3: Check Collection Schema

Run this to see what fields your Collection actually supports:

```python
import requests

management_key = "your_key"
collection_id = "col_xxx"

response = requests.get(
    f"https://api.x.ai/v1/collections/{collection_id}",
    headers={"Authorization": f"Bearer {management_key}"}
)

data = response.json()
print(json.dumps(data, indent=2))

# Look for 'field_definitions' in the output
```

This will show you exactly which fields are defined.

---

## 📊 Quick Comparison

| Solution | Pros | Cons | Time |
|----------|------|------|------|
| **Add fields in Console** | ✅ Keeps full functionality<br>✅ Uses keywords for search | ❌ Requires Console access | 5 min |
| **Remove extra fields** | ✅ Quick fix<br>✅ No Console needed | ❌ Loses keyword functionality | 2 min |
| **Use SimpleMetadataUploader** | ✅ Auto-detects fields<br>✅ Works with any Collection | ❌ Extra complexity | 10 min |

---

## 🚀 Recommended Workflow

### Step 1: Check Current Schema
```bash
python -c "
import requests, json
response = requests.get(
    'https://api.x.ai/v1/collections/YOUR_COLLECTION_ID',
    headers={'Authorization': 'Bearer YOUR_MGMT_KEY'}
)
print(json.dumps(response.json(), indent=2))
"
```

### Step 2: Add Missing Fields in xAI Console
1. Go to https://console.x.ai/
2. Open your Collection
3. Settings → Metadata Fields
4. Add `keywords` (array/text)
5. Add `original_filename` (string)
6. Save

### Step 3: Retry Upload
Your upload should now work!

---

## 💡 Why This Happened

xAI Collections require metadata fields to be **pre-defined** in the Collection schema before you can use them. Your uploader was trying to send:

```json
{
  "metadata": {
    "keywords": ["clt", "justa causa"],  // ❌ Not defined
    "original_filename": "doc.md"        // ❌ Not defined
  }
}
```

But your Collection only knew about:
```json
{
  "field_definitions": {
    "categoria": "string",
    "reclamada": "string",
    "numero_processo": "string",
    "data_publicacao": "string",
    "tipo_acao": "string"
  }
}
```

**Solution:** Add the missing fields to `field_definitions` in xAI Console.

---

## ✅ After Fixing

Once fields are added, your uploads will succeed and you'll see:

```
[15:40:50] 📤 Uploading 0001_file.md...
[15:40:51] ✅ Upload bem-sucedido: 0001_file.md
[15:40:52] 📤 Uploading 0002_file.md...
[15:40:53] ✅ Upload bem-sucedido: 0002_file.md
...
✅ Upload concluído!
   Sucesso: 64
   Falhas: 0
```

---

## 📚 Additional Info

### Why Keywords are Important
Keywords enable **hybrid search** (semantic + keyword matching):
- Better precision for legal terms
- Filter by specific concepts (CLT, súmulas, etc.)
- Improved relevance ranking

### Why Original Filename is Useful
Helps track source documents:
- Debugging upload issues
- Identifying document sources
- Audit trails

---

## 🎯 Summary

1. ✅ **VPN fixed** Cloudflare issue
2. ❌ **New issue:** Missing metadata field definitions
3. ✅ **Fix:** Add `keywords` and `original_filename` to Collection schema in xAI Console
4. ✅ **Alternative:** Remove these fields from uploader code

**Next step:** Add fields in xAI Console, then retry upload.

---

**Last Updated:** 2026-02-10
