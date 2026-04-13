#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
CONFIG_PATH="$ROOT_DIR/configs/tooling/notebooklm_integration.json"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: missing config $CONFIG_PATH" >&2
  exit 2
fi

PYTHON_BIN="$(python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('configs/tooling/notebooklm_integration.json').read_text(encoding='utf-8'))
print(cfg.get('python_bin', 'python3.12'))
PY
)"
VERSION_PIN="$(python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('configs/tooling/notebooklm_integration.json').read_text(encoding='utf-8'))
print(cfg.get('version_pin', '0.3.5'))
PY
)"
EXTRAS="$(python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('configs/tooling/notebooklm_integration.json').read_text(encoding='utf-8'))
print(cfg.get('install_extras', 'browser,cookies'))
PY
)"

cd "$ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN not found" >&2
  exit 2
fi

echo "[1/4] Installing notebooklm-py[$EXTRAS]==$VERSION_PIN with $PYTHON_BIN"
set +e
"$PYTHON_BIN" -m pip install --upgrade "notebooklm-py[$EXTRAS]==$VERSION_PIN"
PIP_INSTALL_CODE=$?
set -e

if [[ $PIP_INSTALL_CODE -ne 0 ]]; then
  echo "WARN: system pip install failed, falling back to isolated venv (PEP 668 safe mode)"
  VENV_DIR="$HOME/.antigravity/venvs/notebooklm-py-$VERSION_PIN"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  PIP_PROXY='' "$VENV_DIR/bin/python" -m pip install --upgrade pip
  PIP_PROXY='' "$VENV_DIR/bin/python" -m pip install --proxy '' "notebooklm-py[$EXTRAS]==$VERSION_PIN"
  PIP_PROXY='' "$VENV_DIR/bin/python" -m playwright install chromium
  mkdir -p "$HOME/.local/bin"
  ln -sf "$VENV_DIR/bin/notebooklm" "$HOME/.local/bin/notebooklm"
fi

echo "[2/4] Installing Playwright Chromium"
if command -v notebooklm >/dev/null 2>&1; then
  notebooklm --version >/dev/null 2>&1 || true
fi
if "$PYTHON_BIN" -c "import playwright" >/dev/null 2>&1; then
  "$PYTHON_BIN" -m playwright install chromium
else
  if [[ -x "$HOME/.local/bin/notebooklm" ]]; then
    "$HOME/.local/bin/notebooklm" --version >/dev/null
  fi
fi

echo "[3/4] Verifying notebooklm CLI"
if command -v notebooklm >/dev/null 2>&1; then
  CLI_VER_RAW="$(notebooklm --version || true)"
elif [[ -x "$HOME/.local/bin/notebooklm" ]]; then
  CLI_VER_RAW="$("$HOME/.local/bin/notebooklm" --version || true)"
else
  CLI_VER_RAW="$("$PYTHON_BIN" -m notebooklm.notebooklm_cli --version || true)"
fi
CLI_VER="$(echo "$CLI_VER_RAW" | tr -cd '0-9.\n' | head -n1)"
if [[ "$CLI_VER" != "$VERSION_PIN" ]]; then
  echo "ERROR: expected notebooklm version $VERSION_PIN, got '$CLI_VER_RAW'" >&2
  exit 2
fi

echo "[4/4] Bootstrap complete"
echo "OK: notebooklm-py $CLI_VER installed and chromium ready"
