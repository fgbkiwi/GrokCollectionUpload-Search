# Archived uploaders

This folder keeps older uploader scripts that are not used by the current UI.
They are preserved for troubleshooting and reference.

## SmartCollectionUploader.py
Purpose: Uploads JSON sentences to xAI Collections while auto-detecting the
Collection schema and filtering metadata to only the allowed fields.

How it works:
- Calls GET /collections/{collection_id} and reads field_definitions.
- Filters metadata to only those fields before upload.
- Uses a single upload strategy: POST /collections/documents.
- Generates simple keywords by regex (no LLM).
- Splits text into 2048-char chunks with 256-char overlap.
- Adds optional chunk_info metadata per chunk.
- Prints basic stats and success/failure counts.

Why it exists:
- Helps avoid upload failures when Collections define strict metadata fields.
- Useful when the API rejects unknown fields.

Limits:
- No LLM keywords.
- No retry or Cloudflare workarounds.
- Uses the standard API endpoint only.

## RobustCollectionUploader.py
Purpose: Uploads JSON sentences to xAI Collections with multiple fallback
strategies to work around Cloudflare header issues and transient failures.

How it works:
- Tries multiple header strategies (default, cf_bypass, aggressive, minimal).
- Retries per strategy with exponential backoff.
- Tracks which strategy works and prefers it next.
- Supports optional Grok keywords via CollectionUploaderV2.GrokKeywordGenerator.
- Splits text into 2048-char chunks with 256-char overlap.
- Adds optional chunk_info metadata per chunk.
- Prints strategy stats and troubleshooting recommendations.

Why it exists:
- Helps when uploads fail with 500 errors or cf-ipcity header problems.
- Provides diagnostics and guidance for VPN/proxy workarounds.

Limits:
- Does not filter metadata fields based on Collection schema.
- Depends on CollectionUploaderV2.py for LLM keywords when enabled.

## check_icons.py
Purpose: Quick sanity check that Flet icon constants resolve correctly.

How it works:
- Instantiates ft.Icon with ft.Icons.REFRESH and prints success or error.

Why it exists:
- Useful when diagnosing Flet version mismatches or icon enum issues.

Limits:
- Not part of the uploader workflow.

## Current primary uploader
The current, functional upload flow is implemented inside CollectionUploaderV2UI.py
and does not use these scripts.
