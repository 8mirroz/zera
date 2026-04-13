#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT_DIR"

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
NODE_VER="$(node -v 2>/dev/null || true)"
HF_CLI="$(command -v hf 2>/dev/null || true)"

if [[ "$PY_VER" != 3.12* ]]; then
  echo "WARN: python3 is $PY_VER (expected 3.12.x)" >&2
else
  echo "OK: python3 is $PY_VER"
fi

if [[ -z "$NODE_VER" ]]; then
  echo "WARN: node is not installed" >&2
else
  echo "OK: node is $NODE_VER"
fi

if [[ -z "$HF_CLI" ]]; then
  echo "WARN: hf CLI not installed (pip install huggingface_hub)" >&2
else
  echo "OK: hf CLI is available"
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARN: HF_TOKEN not set (Hugging Face Hub actions may be rate-limited)" >&2
else
  echo "OK: HF_TOKEN is set"
fi

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "OK: created .env from .env.example"
fi

python3 repos/packages/agent-os/scripts/swarmctl.py doctor || true
