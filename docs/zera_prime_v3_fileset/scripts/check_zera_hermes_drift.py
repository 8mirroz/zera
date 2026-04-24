#!/usr/bin/env python3
from pathlib import Path
import os, sys, json

HERMES = Path("/Users/user/.hermes")
ZERA_CORE = Path("/Users/user/zera-core")

violations = []
warnings = []

def exists(path):
    return Path(path).exists()

def collect(pattern):
    if not HERMES.exists():
        return []
    return list(HERMES.rglob(pattern))

# 1. Zera-core required directories
for required in [
    "identity",
    "governance",
    "interfaces",
]:
    if not (ZERA_CORE / required).exists():
        violations.append(f"Missing zera-core/{required}")

# 2. Persona files inside Hermes should not exist as real files
for p in collect("*zera*persona*") + collect("*core-zera*"):
    if p.is_file() and not p.is_symlink():
        violations.append(f"Persona duplicate inside Hermes: {p}")

# 3. Multiple zera profiles
profiles = HERMES / "profiles"
if profiles.exists():
    zera_profiles = [p for p in profiles.iterdir() if p.is_dir() and p.name.startswith("zera") and p.name != ".archive"]
    if len(zera_profiles) > 1:
        warnings.append(f"Multiple Zera profiles detected: {[p.name for p in zera_profiles]}")

# 4. Vault copies in Hermes profiles
if profiles.exists():
    vaults = [p for p in profiles.rglob("vault") if p.is_dir() and not p.is_symlink()]
    if vaults:
        warnings.append(f"Vault copies inside Hermes profiles: {[str(v) for v in vaults[:10]]}")

# 5. SOUL.md persona language warning
soul = HERMES / "SOUL.md"
if soul.exists():
    txt = soul.read_text(errors="ignore").lower()
    if "persona" in txt or "identity" in txt:
        warnings.append(".hermes/SOUL.md may still contain persona/identity language")

report = {
    "status": "fail" if violations else "warn" if warnings else "pass",
    "violations": violations,
    "warnings": warnings,
}

print(json.dumps(report, indent=2, ensure_ascii=False))
sys.exit(1 if violations else 0)
