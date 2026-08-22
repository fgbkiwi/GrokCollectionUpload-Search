#!/usr/bin/env bash
# Idempotent, self-contained setup for the Grok Collection Upload & Search project.
#
# Prepares everything a Cloud Agent needs from a clean base image:
#   * system packages (Flutter Linux-desktop build deps + basic tooling)
#   * the uv package manager (fast, project's preferred tool)
#   * the Flutter SDK (pinned to match the README)
#   * a Python virtualenv (.venv) with every module's dependencies
#   * the Flutter UI package resolution (flutter pub get)
#
# Safe to run repeatedly: each step is guarded or uses tools that converge.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

FLUTTER_VERSION="3.35.4"
FLUTTER_HOME="$HOME/flutter"
LOCAL_BIN="$HOME/.local/bin"

if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
# The archive proxy occasionally returns a transient 400 for a single .deb, so
# retry update/install a couple of times before giving up.
apt_try() {
  for attempt in 1 2 3; do
    if $SUDO apt-get "$@"; then return 0; fi
    echo "apt-get $* failed (attempt $attempt); retrying..." >&2
    sleep 5
  done
  return 1
}
apt_try update -y -qq
apt_try install -y -qq --no-install-recommends --fix-missing \
  python3 python3-venv curl git unzip xz-utils zip ca-certificates \
  clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev

echo "==> Installing uv (Python package manager)"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "${LOCAL_BIN}/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="${LOCAL_BIN}:${PATH}"

echo "==> Installing Flutter ${FLUTTER_VERSION}"
if [ ! -x "${FLUTTER_HOME}/bin/flutter" ]; then
  tmp="$(mktemp -d)"
  curl -fSL --retry 5 --retry-delay 3 -o "${tmp}/flutter.tar.xz" \
    "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
  rm -rf "${FLUTTER_HOME}"
  tar xf "${tmp}/flutter.tar.xz" -C "${HOME}"
  rm -rf "${tmp}"
fi
export PATH="${FLUTTER_HOME}/bin:${PATH}"
git config --global --add safe.directory "${FLUTTER_HOME}" 2>/dev/null || true
flutter config --no-analytics >/dev/null 2>&1 || true
flutter config --enable-linux-desktop --enable-web >/dev/null 2>&1 || true

echo "==> Persisting uv and Flutter on PATH for future shells"
for line in 'export PATH="$HOME/.local/bin:$PATH"' 'export PATH="$HOME/flutter/bin:$PATH"'; do
  for rc in "${HOME}/.bashrc" "${HOME}/.profile"; do
    touch "${rc}"
    grep -qxF "${line}" "${rc}" 2>/dev/null || echo "${line}" >> "${rc}"
  done
done

echo "==> Creating Python virtualenv (.venv) with uv"
uv venv .venv
# Install every module's dependencies in a SINGLE resolution so the combined
# constraints pick one compatible Flet. The apps use the classic Flet control
# API (e.g. Dropdown(on_change=...)) removed in the 0.80+ rewrite, so
# requirements_app.txt pins flet<0.29; resolving all files together yields the
# newest classic release (0.28.3) that also satisfies the other modules'
# flet>=0.24/0.25 requirements.
VIRTUAL_ENV="${REPO_DIR}/.venv" uv pip install \
  -r requirements_app.txt \
  -r requirements_indexador.txt \
  -r requirements_cartao.txt \
  -r requirements_sarah.txt

echo "==> Fetching Flutter UI packages"
(cd collection_uploader_app && flutter pub get)

echo "==> install.sh complete"
