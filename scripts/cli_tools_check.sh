#!/usr/bin/env bash
set -euo pipefail

required_tools=(python3 uv git rg)
missing=0

for tool in "${required_tools[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "[missing] $tool"
    missing=1
  else
    echo "[ok] $tool -> $(command -v "$tool")"
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi
