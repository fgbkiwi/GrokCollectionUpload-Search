#!/usr/bin/env bash
# Idempotent dependency setup for the Grok Collection Upload & Search project.
# Prepares the Python virtualenv (CLI uploader + Flet search app) and, when the
# Flutter SDK is present in the base image, fetches the Flutter UI packages.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Setting up Python virtualenv (.venv)"
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
./.venv/bin/python -m pip install --upgrade pip
# requirements_app.txt covers every third-party import used by the Python
# scripts: flet (search UI), requests (xAI API for CollectionUploaderV2 and the
# search app) and pyperclip (chat copy).
./.venv/bin/pip install -r requirements_app.txt

echo "==> Fetching Flutter UI packages"
export PATH="$HOME/flutter/bin:$PATH"
if command -v flutter >/dev/null 2>&1; then
  (cd collection_uploader_app && flutter pub get)
else
  echo "WARN: flutter not found on PATH; skipping 'flutter pub get'." >&2
fi

echo "==> install.sh complete"
