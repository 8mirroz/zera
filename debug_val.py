import sys
from pathlib import Path

# Add swarmctl.py directory to path to import helpers if needed, 
# but we can just copy the logic here for debugging.
repo_root = Path("/Users/user/antigravity-core")
registry_path = repo_root / "configs/rules/rules.registry.yaml"
rules_dir = repo_root / "configs/rules"

print(f"Registry path: {registry_path} (exists: {registry_path.exists()})")
print(f"Rules dir: {rules_dir} (exists: {rules_dir.exists()})")

import yaml # We need to use what's available or parse manually
# swarmctl uses parse_simple_yaml which is likely a local helper.

# Minimal manual YAML parser for entries path
active_paths = set()
if registry_path.exists():
    content = registry_path.read_text()
    import re
    # Simple regex to find path: "..."
    matches = re.findall(r'path:\s*"(.*?)"', content)
    for m in matches:
        p = repo_root / m
        abs_p = str(p.resolve())
        active_paths.add(abs_p)
        print(f"Active path: {abs_p}")

if rules_dir.exists():
    for f in rules_dir.iterdir():
        if f.is_dir() or f.name.startswith(".") or f.name == "rules.registry.yaml":
            continue
        if f.suffix not in {".md", ".yaml"}:
            print(f"Skipping (suffix): {f.name}")
            continue
        
        abs_f = str(f.resolve())
        is_old = f.name.endswith(".old")
        print(f"Checking file: {f.name} (abs: {abs_f}) - is_old: {is_old}")
        if abs_f not in active_paths and not is_old:
            print(f"DRIFT DETECTED: {f.name}")
