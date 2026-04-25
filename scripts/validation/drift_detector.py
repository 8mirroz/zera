import os
import yaml
import sys
from pathlib import Path

def find_workspace_root() -> Path:
    curr = Path.cwd()
    for _ in range(5):
        if (curr / "configs").is_dir() and (curr / "repos").is_dir():
            return curr
        curr = curr.parent
    return Path.cwd()

def check_drift():
    root = find_workspace_root()
    manifest_path = root / "configs/tooling/workspace_manifest.yaml"
    
    if not manifest_path.exists():
        print(f"FAIL: Manifest missing at {manifest_path}")
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        manifest = yaml.safe_load(f)
        
    errors = []
    
    # Check root
    manifest_root = manifest.get("workspace", {}).get("root")
    if manifest_root and str(root) != manifest_root:
        errors.append(f"Root drift: manifest={manifest_root}, actual={root}")
        
    # Check env vars
    secret_policy = manifest.get("governance", {}).get("secret_policy")
    if secret_policy == "env_ref_only":
        if not os.getenv("HERMES_ZERA_API_KEY"):
            errors.append("Governance drift: HERMES_ZERA_API_KEY is not set (policy=env_ref_only)")
            
    # Check integrations
    for integration in manifest.get("integrations", []):
        path = root / integration.get("path")
        if not path.exists():
            errors.append(f"Integration drift: {integration.get('id')} path missing at {path}")

    if errors:
        print("--- DRIFT DETECTED ---")
        for err in errors:
            print(f"❌ {err}")
        sys.exit(1)
    else:
        print("✅ No drift detected between manifest and runtime environment.")
        sys.exit(0)

if __name__ == "__main__":
    check_drift()
