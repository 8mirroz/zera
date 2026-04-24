#!/usr/bin/env bash
set -euo pipefail

ZERA_CORE="/Users/user/zera-core"
HERMES="/Users/user/.hermes"

mkdir -p "$HERMES/runtime"
mkdir -p "$HERMES/skills"

ln -sfn "$ZERA_CORE/identity" "$HERMES/runtime/zera_identity"
ln -sfn "$ZERA_CORE/governance" "$HERMES/runtime/zera_governance"
ln -sfn "$ZERA_CORE/interfaces" "$HERMES/runtime/zera_interfaces"

echo "Zera read-only references mounted into Hermes runtime."
