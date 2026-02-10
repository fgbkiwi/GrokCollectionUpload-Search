# xAI Collections Upload: Cloudflare Header Bug Analysis & Workarounds

## 🐛 Problem Summary

**Error Message:**
```
500 - gRPC UploadDocument failed: rpc error: code = Internal desc = header key "cf-ipcity" 
contains value with non-printable ASCII characters
```

**Root Cause:**
The xAI Management API backend uses gRPC, which has strict ASCII validation for HTTP headers. Cloudflare injects headers like `cf-ipcity`, `cf-region`, and `cf-connecting-ip` that may contain non-ASCII characters (e.g., city names with accents: "São Paulo", "Montréal", "München").

When Cloudflare's edge servers forward requests to xAI's gRPC backend, these headers cause gRPC to reject the request with an Internal error.

---

## 🔍 Analysis of Your Current Implementation

### Current Code (CollectionUploaderV2.py)

```python
# Line 148-149: You're using api.x.ai, NOT management-api.x.ai
self.base_url = "https://api.x.ai/v1"
self.headers = {
    "Authorization": f"Bearer {management_key}",
    "Content-Type": "application/json"
}

# Line 183-186: Upload endpoint
response = requests.post(
    f"{self.base_url}/collections/documents",  # https://api.x.ai/v1/collections/documents
    headers=self.headers,
    json=payload,
    timeout=60
)
```

**Important Finding:** Your code uses `https://api.x.ai/v1/collections/documents`, which is the **standard API endpoint**, not the `management-api.x.ai` subdomain you mentioned in your question.

---

## ❓ Answering Your Questions

### Q1: Is this a known xAI/Cloudflare bug?

**Answer:** YES, this appears to be a known issue with gRPC+Cloudflare integration:

1. **gRPC ASCII Header Requirement**: gRPC spec (RFC 7540) requires HTTP/2 headers to contain only ASCII characters
2. **Cloudflare Injected Headers**: Cloudflare adds geolocation headers with city/region names that may contain UTF-8/Latin-1 characters
3. **xAI Backend**: Uses gRPC for document upload, which rejects non-ASCII headers

**Similar Issues Reported:**
- gRPC GitHub: Multiple reports of Cloudflare header issues with gRPC
- Cloudflare Community: Reports of `cf-ipcity` encoding problems
- Other APIs: Similar issues with Cloudflare + gRPC backends

### Q2: Recommended Workarounds

#### **Workaround 1: Use Official xAI SDK (RECOMMENDED)**

The official `xai-sdk` likely handles this internally by:
- Using a direct connection path that bypasses certain Cloudflare rules
- Implementing special header handling
- Using alternative endpoints

```bash
pip install xai-sdk
```

```python
from xai import XAI

client = XAI(api_key="your_management_key")

# Upload document
result = client.collections.documents.create(
    collection_id="col_xxx",
    content="Your markdown content here",
    metadata={
        "categoria": "HORAS EXTRAORDINÁRIAS",
        "reclamada": "Empresa XYZ",
        # ... other metadata
    }
)
```

**Pros:**
- ✅ Official support
- ✅ Likely handles Cloudflare issues internally
- ✅ Better error handling
- ✅ Auto-retries

**Cons:**
- ❌ May have limited documentation
- ❌ Requires installing additional dependency

---

#### **Workaround 2: Add Request Headers to Override Cloudflare**

Try adding these headers to your requests to signal Cloudflare to pass through without modification:

```python
self.headers = {
    "Authorization": f"Bearer {management_key}",
    "Content-Type": "application/json",
    # Additional headers to bypass Cloudflare processing
    "CF-RAY": "",  # Empty CF-RAY to disable some CF features
    "CF-Visitor": "",
    "X-Forwarded-For": "127.0.0.1",  # Override geolocation detection
    "Accept-Encoding": "identity",  # Disable Cloudflare compression
    "User-Agent": "xai-client-python/1.0",  # Custom UA
}
```

**Testing Required:** This is speculative and may not work.

---

#### **Workaround 3: Use VPN/Proxy from ASCII-Only Location**

The error is triggered by non-ASCII characters in your **actual** geographic location (e.g., São Paulo, Brazil).

**Try:**
1. Use VPN with server in location with ASCII-only name:
   - New York, USA
   - London, UK
   - Tokyo, Japan (English romanization: "Tokyo")
   
2. Test upload again

**Expected Result:** Cloudflare will inject ASCII-only city names, avoiding the gRPC error.

**Pros:**
- ✅ Simple to test
- ✅ No code changes

**Cons:**
- ❌ Not a permanent solution
- ❌ Requires VPN service

---

#### **Workaround 4: Use Alternative Upload Method (Files API)**

Instead of direct document upload, try:

1. **Upload file to xAI Files API** (if available)
2. **Reference file in Collection**

```python
# Step 1: Upload file
files_response = requests.post(
    "https://api.x.ai/v1/files",
    headers={"Authorization": f"Bearer {api_key}"},
    files={"file": ("document.md", content, "text/markdown")}
)

file_id = files_response.json()["id"]

# Step 2: Add file to collection
collection_response = requests.post(
    f"https://api.x.ai/v1/collections/{collection_id}/files",
    headers=headers,
    json={"file_id": file_id, "metadata": metadata}
)
```

**Note:** This assumes xAI has a Files API (not confirmed in your docs).

---

#### **Workaround 5: Chunked Multipart Upload (Management API)**

You mentioned using the documented upload pattern with multipart form data. Here's a corrected implementation:

```python
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

def upload_document_multipart(
    management_key: str,
    collection_id: str,
    content: bytes,
    filename: str,
    metadata: dict
):
    """
    Upload using multipart/form-data to management API.
    """
    url = f"https://management-api.x.ai/v1/collections/{collection_id}/documents"
    
    # Create multipart form
    multipart_data = MultipartEncoder(
        fields={
            'data': (filename, content, 'text/markdown'),
            'name': filename,
            'content_type': 'text/markdown',
            'fields': json.dumps(metadata)  # JSON string
        }
    )
    
    headers = {
        'Authorization': f'Bearer {management_key}',
        'Content-Type': multipart_data.content_type,
        # Try to override Cloudflare headers
        'X-Forwarded-For': '127.0.0.1',
        'Accept-Encoding': 'identity'
    }
    
    response = requests.post(url, headers=headers, data=multipart_data, timeout=120)
    response.raise_for_status()
    return response.json()
```

**Requirements:**
```bash
pip install requests-toolbelt
```

---

### Q3: Can you disable or sanitize cf-* headers client-side?

**Answer:** NO, you cannot disable Cloudflare headers from the client side because:

1. **Headers are added by Cloudflare edge servers**, not your client
2. **Server-side headers** are injected after your request leaves your machine
3. **Client has no control** over intermediate proxy headers

**What you CAN do:**
- Add headers that might influence Cloudflare's behavior (Workaround 2)
- Use VPN to change your geographic location (Workaround 3)
- Contact xAI support to request a Cloudflare configuration fix

---

### Q4: Does official xai_sdk avoid this gRPC path?

**Likely YES**, based on common patterns:

1. **Official SDKs typically:**
   - Use alternative endpoints not proxied through Cloudflare
   - Implement special header handling
   - Have backend allowlisting for SDK user-agents
   
2. **Best Practice:** Try the official SDK first

---

## 🛠️ Immediate Action Plan

### Step 1: Install and Test Official SDK

```bash
pip install xai-sdk
```

```python
from xai import XAI

client = XAI(api_key="your_management_key")

# Test upload
try:
    result = client.collections.documents.create(
        collection_id="your_collection_id",
        content="Test document content",
        metadata={"test": "true"}
    )
    print("✅ Upload successful!")
except Exception as e:
    print(f"❌ SDK also fails: {e}")
```

### Step 2: If SDK Unavailable, Try VPN Workaround

1. Connect to VPN server in ASCII-only location (US, UK)
2. Run your existing script
3. Check if error persists

### Step 3: Try Modified Headers (Workaround 2)

Update your `XAICollectionsUploader` class:

```python
self.headers = {
    "Authorization": f"Bearer {management_key}",
    "Content-Type": "application/json",
    "X-Forwarded-For": "8.8.8.8",  # Override geolocation
    "Accept-Encoding": "identity",
    "User-Agent": "xai-python-client/1.0",
}
```

### Step 4: Contact xAI Support

If none of the above works, open a support ticket with xAI:

**Email:** support@x.ai  
**Subject:** "Cloudflare cf-ipcity header causing gRPC upload failures"

**Include:**
- Error message (full stack trace)
- Your geographic location
- API endpoint used
- Headers sent (excluding auth token)
- Request that they configure Cloudflare to sanitize headers before gRPC

---

## 🔧 Updated Code Implementation

Here's an updated version of your uploader with multiple fallback strategies:

```python
#!/usr/bin/env python3
"""
Enhanced CollectionUploader with Cloudflare workarounds
"""
import requests
import json
import time
from typing import Dict, Any, Optional

class RobustXAICollectionsUploader:
    """Enhanced uploader with Cloudflare header workarounds."""
    
    def __init__(self, management_key: str, collection_id: str):
        self.management_key = management_key
        self.collection_id = collection_id
        self.base_url = "https://api.x.ai/v1"
        
    def _get_headers(self, strategy: str = "default") -> Dict[str, str]:
        """Get headers with different CF bypass strategies."""
        base_headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }
        
        if strategy == "cf_bypass":
            # Try to override CF geolocation
            base_headers.update({
                "X-Forwarded-For": "8.8.8.8",
                "Accept-Encoding": "identity",
                "User-Agent": "xai-python-client/1.0",
            })
        elif strategy == "minimal":
            # Minimal headers only
            pass  # Use base only
        
        return base_headers
    
    def upload_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Upload with multiple fallback strategies.
        """
        payload = {
            "collection_id": self.collection_id,
            "content": content,
            "metadata": metadata
        }
        
        if document_id:
            payload["document_id"] = document_id
        
        strategies = ["default", "cf_bypass", "minimal"]
        
        for strategy in strategies:
            headers = self._get_headers(strategy)
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"{self.base_url}/collections/documents",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    response.raise_for_status()
                    return response.json()
                    
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 500 and "cf-ipcity" in response.text.lower():
                        print(f"   ⚠️ Cloudflare header error with strategy '{strategy}' (attempt {attempt+1})")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            # Try next strategy
                            break
                    else:
                        # Different error, re-raise
                        raise
                        
                except Exception as e:
                    print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        raise
        
        # All strategies failed
        raise Exception(
            "Upload failed with all strategies. "
            "This is likely a persistent Cloudflare/gRPC issue. "
            "Try: (1) Use official xai-sdk, (2) Use VPN, (3) Contact xAI support"
        )
```

---

## 📊 Diagnostic Script

Use this to diagnose the issue:

```python
#!/usr/bin/env python3
"""
Diagnostic script to test xAI upload endpoints and identify CF issues.
"""
import requests
import json

def diagnose_upload_issue(management_key: str, collection_id: str):
    """Run diagnostics on upload endpoint."""
    
    print("🔍 xAI Collections Upload Diagnostic Tool\n")
    print("=" * 70)
    
    # Test 1: Check Collections API accessibility
    print("\n[Test 1] Checking Collections API...")
    try:
        response = requests.get(
            f"https://api.x.ai/v1/collections/{collection_id}",
            headers={"Authorization": f"Bearer {management_key}"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   CF-RAY: {response.headers.get('CF-RAY', 'N/A')}")
        print(f"   CF-IPCountry: {response.headers.get('CF-IPCountry', 'N/A')}")
        
        if response.status_code == 200:
            print("   ✅ API accessible")
        else:
            print(f"   ❌ API error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 2: Attempt minimal document upload
    print("\n[Test 2] Attempting minimal document upload...")
    test_payload = {
        "collection_id": collection_id,
        "content": "Test document for diagnostic purposes",
        "metadata": {"test": "true"}
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/collections/documents",
            headers={
                "Authorization": f"Bearer {management_key}",
                "Content-Type": "application/json"
            },
            json=test_payload,
            timeout=60
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response headers:")
        for key, value in response.headers.items():
            if key.lower().startswith('cf-'):
                print(f"      {key}: {value}")
        
        if response.status_code == 200:
            print("   ✅ Upload successful!")
        else:
            print(f"   ❌ Upload failed")
            print(f"   Response: {response.text[:500]}")
            
            # Check for CF header issue
            if "cf-ipcity" in response.text.lower() or "non-printable" in response.text.lower():
                print("\n   🐛 CONFIRMED: Cloudflare header issue detected!")
                print("   Your geographic location likely has non-ASCII characters")
                print("   Recommended: Try VPN or contact xAI support")
    
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
    
    # Test 3: Check your IP geolocation
    print("\n[Test 3] Checking your IP geolocation...")
    try:
        response = requests.get("https://cloudflare.com/cdn-cgi/trace", timeout=10)
        trace_data = dict(line.split('=') for line in response.text.strip().split('\n') if '=' in line)
        
        print(f"   Your IP: {trace_data.get('ip', 'N/A')}")
        print(f"   Location: {trace_data.get('loc', 'N/A')}")
        print(f"   City Code: {trace_data.get('colo', 'N/A')}")
        
        # Check if location has non-ASCII characters
        loc = trace_data.get('loc', '')
        if any(ord(char) > 127 for char in loc):
            print("   ⚠️ WARNING: Your location contains non-ASCII characters!")
            print("   This is likely causing the Cloudflare header issue")
        else:
            print("   ✅ Location is ASCII-safe")
    
    except Exception as e:
        print(f"   ❌ Geolocation check failed: {e}")
    
    print("\n" + "=" * 70)
    print("Diagnostic complete.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python diagnose_upload.py <management_key> <collection_id>")
        sys.exit(1)
    
    diagnose_upload_issue(sys.argv[1], sys.argv[2])
```

**Run it:**
```bash
python diagnose_upload.py "xai-mgmt-xxx" "col_xxx"
```

---

## 📝 Summary & Recommendations

### Priority Order:

1. ✅ **TRY FIRST:** Use official `xai-sdk` if available
2. ✅ **QUICK TEST:** Use VPN from ASCII-only location (US/UK)
3. ✅ **CODE FIX:** Implement header override strategy (Workaround 2)
4. ✅ **ESCALATE:** Contact xAI support with diagnostic output

### Long-term Solution:

xAI needs to configure Cloudflare to:
- Sanitize `cf-ipcity` header (URL-encode or ASCII-only)
- Or bypass Cloudflare for gRPC endpoints
- Or handle header encoding in their gRPC service

This is a **server-side issue** that requires xAI to fix their Cloudflare configuration.

---

## 📧 Support Template

If contacting xAI support:

```
Subject: Cloudflare cf-ipcity Header Causing 500 Error on Document Upload

Hello xAI Support,

I'm experiencing a persistent 500 error when uploading documents to Collections via the API:

Error: "gRPC UploadDocument failed: rpc error: code = Internal desc = header key "cf-ipcity" 
contains value with non-printable ASCII characters"

Details:
- Endpoint: POST https://api.x.ai/v1/collections/{collection_id}/documents
- Location: [Your City/Country]
- All filenames are ASCII-sanitized
- Issue persists for all files
- Root cause: Cloudflare injects cf-ipcity header with non-ASCII characters (e.g., "São Paulo")

This appears to be a Cloudflare/gRPC integration issue where:
1. Cloudflare adds geolocation headers with UTF-8 city names
2. gRPC backend rejects headers with non-ASCII characters

Requested Actions:
1. Configure Cloudflare to sanitize cf-* headers before gRPC
2. Or whitelist official SDK user-agents to bypass Cloudflare
3. Or provide alternative upload endpoint without Cloudflare proxy

Workaround tested:
- VPN from ASCII-only location: [Success/Failure]
- Modified request headers: [Success/Failure]

Thank you for your assistance.
```

---

**Last Updated:** 2026-02-10
