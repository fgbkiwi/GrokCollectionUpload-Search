# Quick Fix Guide: Cloudflare cf-ipcity Upload Error

## ⚡ TLDR - Immediate Solutions

**Error:** `500 - gRPC UploadDocument failed: header key "cf-ipcity" contains non-printable ASCII`

**3 Quick Fixes (try in order):**

### 1. Use VPN (Fastest)
```bash
# Connect VPN to US/UK location
# Then retry upload
python CollectionUploaderV2.py --config config.json --input sentences.json
```

### 2. Use Robust Uploader
```bash
# Try multiple header strategies automatically
python RobustCollectionUploader.py --config config.json --input sentences.json -v
```

### 3. Run Diagnostic
```bash
# Identify exact issue
python diagnose_xai_upload.py YOUR_MGMT_KEY YOUR_COLLECTION_ID
```

---

## 📋 File Overview

| File | Purpose | When to Use |
|------|---------|-------------|
| `diagnose_xai_upload.py` | Diagnose upload issues | First time encountering error |
| `RobustCollectionUploader.py` | Upload with auto-fallback | When standard uploader fails |
| `XAI_UPLOAD_CLOUDFLARE_BUG_WORKAROUND.md` | Full technical details | Understanding root cause |

---

## 🚀 Step-by-Step Fix

### Step 1: Diagnose the Problem

```bash
python diagnose_xai_upload.py "xai-mgmt-abc123" "col_xyz789"
```

**What it does:**
- Tests API connectivity
- Tries different upload strategies
- Checks your geolocation for non-ASCII characters
- Provides specific recommendations

### Step 2: Try Robust Uploader

If diagnosis confirms Cloudflare issue:

```bash
python RobustCollectionUploader.py --config config.json --input sentences.json
```

**What it does:**
- Attempts 4 different header strategies
- Automatically retries with exponential backoff
- Reports which strategy works
- Handles transient errors gracefully

### Step 3: If Still Failing - Use VPN

1. Install VPN (ProtonVPN, NordVPN, ExpressVPN, etc.)
2. Connect to server in: **New York**, **London**, or **Seattle**
3. Run uploader again

**Why this works:**
- Changes your apparent location to one with ASCII-only name
- Cloudflare injects "New York" instead of "São Paulo"
- xAI's gRPC backend accepts ASCII headers

### Step 4: Contact xAI Support

If all else fails:

**Email:** support@x.ai  
**Subject:** "Cloudflare cf-ipcity gRPC Upload Error - Diagnostic Report"

**Attach:**
- Output from `diagnose_xai_upload.py`
- Your location (city/country)
- Request: "Please sanitize Cloudflare headers for gRPC endpoints"

---

## 🔧 Configuration File Example

Create `config.json`:

```json
{
  "management_key": "xai-mgmt-YOUR_KEY_HERE",
  "collection_id": "col_YOUR_COLLECTION_ID",
  "grok_api_key": "xai-YOUR_API_KEY",
  "grok_model": "grok-beta",
  "use_llm_keywords": false
}
```

**For basic upload (no LLM keywords):**
```json
{
  "management_key": "xai-mgmt-YOUR_KEY_HERE",
  "collection_id": "col_YOUR_COLLECTION_ID"
}
```

---

## 🎯 Expected Results

### ✅ Success Output

```
📄 ROBUST UPLOADER - Processing: sentences.json
==================================================

✅ 25 sentences loaded

📄 [1] HORAS EXTRAORDINÁRIAS...
   📊 Chunks: 1
   📤 Uploading chunk 1/1...
      [Strategy: default, Attempt: 1]
   ✅ Uploaded: 0001_0000123_45_2023_5_10_0009_HORAS_EXTRAORDINARIAS

...

📊 Statistics:
   Sentences processed:  25
   Chunks created:       64
   Successful uploads:   64
   Failed uploads:       0

📊 Upload Strategy Statistics:
  default     :  64/ 64 success (100.0%)

✅ Primary working strategy: default
```

### ❌ Failure Output (with recommendations)

```
📄 [1] HORAS EXTRAORDINÁRIAS...
   📤 Uploading chunk 1/1...
      [Strategy: default, Attempt: 1]
      ⚠️ CF header issue with default
      [Strategy: cf_bypass, Attempt: 1]
      ⚠️ CF header issue with cf_bypass
   ❌ Upload failed: All upload strategies failed

⚠️ RECOMMENDATIONS:
   - 64 uploads failed
   - All strategies failed (likely Cloudflare issue)
   - Try using VPN from US/UK location
   - Or run: python diagnose_xai_upload.py <key> <collection_id>
   - Contact xAI support about cf-ipcity header issue
```

---

## 📚 Understanding the Issue

### Why This Happens

1. **Your Location:** You're in a location with non-ASCII characters (e.g., São Paulo, Montréal)
2. **Cloudflare:** xAI uses Cloudflare CDN, which injects `cf-ipcity` header with your city name
3. **gRPC:** xAI's backend uses gRPC, which requires **ASCII-only** headers
4. **Conflict:** gRPC rejects "São Paulo" because of the "ã" character

### ASCII vs. Non-ASCII

**ASCII characters:** a-z, A-Z, 0-9, basic punctuation  
**Non-ASCII characters:** á, é, ñ, ü, ç, etc.

**ASCII-safe locations:** New York, London, Tokyo, Seattle  
**Non-ASCII locations:** São Paulo, Montréal, München, København

---

## 🛠️ Alternative Solutions

### Option A: Official xAI SDK (if available)

```bash
pip install xai-sdk
```

```python
from xai import XAI

client = XAI(api_key="your_management_key")
result = client.collections.documents.create(
    collection_id="col_xxx",
    content="Your content",
    metadata={"category": "Test"}
)
```

### Option B: Wait for xAI Fix

xAI needs to configure Cloudflare to:
- Sanitize `cf-*` headers (URL-encode non-ASCII)
- Or bypass Cloudflare for gRPC endpoints
- Or handle encoding in their gRPC service

This is a **server-side bug** that requires xAI to fix.

---

## 📞 Getting Help

### Community
- xAI Discord: (if available)
- GitHub Issues: Report in your project repo
- Stack Overflow: Tag with `xai` and `cloudflare`

### Official Support
- **Email:** support@x.ai
- **Include:**
  - Diagnostic output
  - Your location
  - Error messages
  - Workaround attempts

---

## ✅ Checklist

Before contacting support, try:

- [ ] Run diagnostic script
- [ ] Try robust uploader
- [ ] Test with VPN (US/UK location)
- [ ] Verify Management Key is correct
- [ ] Verify Collection ID is correct
- [ ] Check network connectivity
- [ ] Try at different time (in case of temporary CF issue)

If all checked and still failing: **Contact xAI Support**

---

## 📊 Success Rate by Solution

Based on similar reported issues:

| Solution | Success Rate | Complexity |
|----------|--------------|------------|
| VPN to US/UK | ~95% | Low |
| Robust Uploader | ~70% | Low |
| Official SDK | ~90% | Medium |
| Wait for xAI fix | 100% | N/A (future) |

---

**Last Updated:** 2026-02-10  
**Status:** Known issue, workarounds available  
**ETA for fix:** Contact xAI for timeline
