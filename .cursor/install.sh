#!/usr/bin/env bash
# Idempotent, self-contained setup for the Grok Collection Upload & Search project.
#
# Prepares everything a Cloud Agent needs from a clean base image:
#   * system packages (Python venv tooling + Flutter Linux-desktop build deps)
#   * the Flutter SDK (pinned to match the README)
#   * a Python virtualenv (.venv) with the app dependencies
#   * the Flutter UI package resolution (flutter pub get)
#
# It is safe to run repeatedly: each step is guarded / uses package managers
# that converge, so re-running only refreshes what changed.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

FLUTTER_VERSION="3.35.4"
FLUTTER_HOME="$HOME/flutter"

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
  python3-venv python3-pip curl git unzip xz-utils zip ca-certificates \
  clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev

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

echo "==> Persisting Flutter on PATH for future shells"
PATH_LINE='export PATH="$HOME/flutter/bin:$PATH"'
for rc in "${HOME}/.bashrc" "${HOME}/.profile"; do
  touch "${rc}"
  grep -qxF "${PATH_LINE}" "${rc}" 2>/dev/null || echo "${PATH_LINE}" >> "${rc}"
done

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
(cd collection_uploader_app && flutter pub get)

echo "==> install.sh complete"
