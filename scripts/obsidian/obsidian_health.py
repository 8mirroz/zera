#!/usr/bin/env python3
"""
obsidian_health.py — Check Obsidian vault health and MCP connectivity.

Usage:
    python3 obsidian_health.py
    python3 obsidian_health.py --vault ~/my-vault
    python3 obsidian_health.py --check-mcp
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime


def check_vault_structure(vault_path: Path) -> dict:
    """Check that vault has required folders."""
    required = [
        ".obsidian/templates",
        "knowledge/design",
        "knowledge/ki",
        "knowledge/adr",
        "memory/decisions",
        "memory/patterns",
        "memory/sessions",
        "projects/antigravity-core",
    ]
    
    result = {"path": str(vault_path), "exists": vault_path.exists(), "folders": {}}
    
    for folder in required:
        full = vault_path / folder
        result["folders"][folder] = full.exists()
    
    return result


def check_files(vault_path: Path) -> dict:
    """Count files by category."""
    counts = {
        "templates": len(list((vault_path / ".obsidian" / "templates").glob("*.md")))
        if (vault_path / ".obsidian" / "templates").exists() else 0,
        "patterns": len(list((vault_path / "memory" / "patterns").glob("*.md")))
        if (vault_path / "memory" / "patterns").exists() else 0,
        "decisions": len(list((vault_path / "memory" / "decisions").glob("*.md")))
        if (vault_path / "memory" / "decisions").exists() else 0,
        "sessions": len(list((vault_path / "memory" / "sessions").glob("*.md")))
        if (vault_path / "memory" / "sessions").exists() else 0,
        "knowledge": len(list((vault_path / "knowledge").rglob("*.md")))
        if (vault_path / "knowledge").exists() else 0,
    }
    return counts


def check_mcp_config(vault_path: Path) -> dict:
    """Check MCP configuration files."""
    result = {"mcp_profiles": None, "router_config": None}
    
    repo_root = vault_path.parent.parent  # Assuming vault is ~/antigravity-vault, repo is ~/antigravity-core
    mcp_profiles = repo_root / "configs" / "tooling" / "mcp_profiles.json"
    router_config = repo_root / "configs" / "orchestrator" / "router.yaml"
    
    if mcp_profiles.exists():
        with open(mcp_profiles) as f:
            profiles = json.load(f)
        obsidian_servers = [k for k in profiles.keys() if "obsidian" in k.lower()]
        result["mcp_profiles"] = {
            "exists": True,
            "obsidian_servers": obsidian_servers,
        }
    
    if router_config.exists():
        with open(router_config) as f:
            content = f.read()
        result["router_config"] = {
            "exists": True,
            "has_hybrid": "hybrid" in content.lower(),
            "has_obsidian": "obsidian" in content.lower(),
        }
    
    return result


def check_frontmatter(vault_path: Path) -> dict:
    """Check that vault files have proper frontmatter."""
    issues = []
    md_files = list(vault_path.rglob("*.md"))
    
    for f in md_files:
        if f.parent.name == ".obsidian":
            continue
        content = f.read_text()
        if not content.startswith("---"):
            issues.append(f"Missing frontmatter: {f.relative_to(vault_path)}")
        elif "---\n" in content:
            # Check for required fields
            fm = content.split("---\n")[1]
            if "type:" not in fm:
                issues.append(f"Missing type: {f.relative_to(vault_path)}")
            if "created:" not in fm:
                issues.append(f"Missing created: {f.relative_to(vault_path)}")
    
    return {"total_files": len(md_files), "issues": issues, "healthy": len(issues) == 0}


def print_report(vault_path: Path, check_mcp: bool = False):
    """Print full health report."""
    print("🔮 Antigravity Vault Health Report")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Vault: {vault_path}")
    print()
    
    # Structure
    struct = check_vault_structure(vault_path)
    print("📁 Structure:")
    for folder, exists in struct["folders"].items():
        status = "✅" if exists else "❌"
        print(f"  {status} {folder}")
    print()
    
    # Files
    files = check_files(vault_path)
    print("📄 Files:")
    for category, count in files.items():
        print(f"  {category:15} {count}")
    print()
    
    # Frontmatter
    fm = check_frontmatter(vault_path)
    print("📋 Frontmatter:")
    print(f"  Total files: {fm['total_files']}")
    print(f"  Healthy: {'✅' if fm['healthy'] else '❌'}")
    if fm["issues"]:
        for issue in fm["issues"]:
            print(f"  ⚠️  {issue}")
    print()
    
    # MCP Config
    if check_mcp:
        mcp = check_mcp_config(vault_path)
        print("🔌 MCP Configuration:")
        if mcp["mcp_profiles"]:
            print(f"  Profiles: {'✅' if mcp['mcp_profiles']['exists'] else '❌'}")
            for server in mcp["mcp_profiles"].get("obsidian_servers", []):
                print(f"    • {server}")
        else:
            print("  Profiles: ❌ Not found")
        
        if mcp["router_config"]:
            print(f"  Router: {'✅' if mcp['router_config']['exists'] else '❌'}")
            print(f"  Hybrid retrieval: {'✅' if mcp['router_config']['has_hybrid'] else '❌'}")
            print(f"  Obsidian routing: {'✅' if mcp['router_config']['has_obsidian'] else '❌'}")
        else:
            print("  Router: ❌ Not found")
        print()
    
    # Overall
    all_folders = all(struct["folders"].values())
    all_healthy = fm["healthy"]
    overall = all_folders and all_healthy
    
    print("=" * 50)
    if overall:
        print("✅ Vault is healthy and ready")
    else:
        print("⚠️  Vault has issues — see report above")
    
    return 0 if overall else 1


def main():
    parser = argparse.ArgumentParser(description="Check Obsidian vault health")
    parser.add_argument("--vault", default=os.environ.get("VAULT_PATH", os.path.expanduser("~/antigravity-vault")),
                        help="Vault path (default: $VAULT_PATH or ~/antigravity-vault)")
    parser.add_argument("--check-mcp", action="store_true", help="Also check MCP configuration")
    
    args = parser.parse_args()
    vault_path = Path(args.vault).expanduser()
    
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        print("   Run setup_vault.sh first: bash templates/obsidian-vault/scripts/setup_vault.sh")
        sys.exit(1)
    
    exit_code = print_report(vault_path, check_mcp=args.check_mcp)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
