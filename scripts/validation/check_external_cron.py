#!/usr/bin/env python3
"""
External Cron Governance Check

Identifies and validates external cron jobs that influence Hermes/Zera behavior
outside repo governance.

Exit codes:
  0 — No unmanaged external cron found, or all known external cron documented
  1 — Unmanaged external cron detected
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def _expand_home(path: str) -> Path:
    return Path(path).expanduser().resolve()


def check_external_cron(repo_root: Path) -> dict[str, Any]:
    """Check for external cron jobs affecting Hermes/Zera."""
    results: dict[str, Any] = {
        "ok": True,
        "surfaces_checked": [],
        "surfaces_found": [],
        "surfaces_missing": [],
        "warnings": [],
    }

    home = Path.home()

    # Check known external cron locations
    external_paths = [
        {
            "path": home / ".hermes" / "profiles" / "zera" / "cron" / "jobs.json",
            "name": "Zera cron jobs (jobs.json)",
            "risk": "high",
        },
        {
            "path": home / ".hermes" / "profiles" / "zera" / "cron",
            "name": "Zera cron directory",
            "risk": "high",
            "is_dir": True,
        },
        {
            "path": home / ".hermes" / "profiles" / "zera" / "config.yaml",
            "name": "Hermes zera profile config",
            "risk": "medium",
        },
        {
            "path": home / ".gemini" / "zera" / "mcp_config.json",
            "name": "Gemini zera MCP config",
            "risk": "medium",
        },
        {
            "path": home / ".hermes" / "profiles" / "antigravity" / "config.yaml",
            "name": "Hermes legacy antigravity profile config",
            "risk": "low",
        },
        {
            "path": home / ".gemini" / "antigravity" / "mcp_config.json",
            "name": "Gemini legacy antigravity MCP config",
            "risk": "medium",
        },
    ]

    for surface in external_paths:
        path = surface["path"]
        name = surface["name"]
        risk = surface.get("risk", "medium")
        is_dir = surface.get("is_dir", False)

        results["surfaces_checked"].append(name)

        if is_dir:
            if path.exists() and path.is_dir():
                files = sorted(f.name for f in path.iterdir() if f.is_file())
                results["surfaces_found"].append({
                    "name": name,
                    "path": str(path),
                    "risk": risk,
                    "files": files,
                    "status": "detected",
                })
                if files:
                    results["warnings"].append(f"{name}: {len(files)} cron file(s) detected outside repo governance")
            else:
                results["surfaces_missing"].append(name)
        else:
            if path.exists():
                results["surfaces_found"].append({
                    "name": name,
                    "path": str(path),
                    "risk": risk,
                    "status": "detected",
                })
                results["warnings"].append(f"{name}: exists outside repo governance")
            else:
                results["surfaces_missing"].append(name)

    # Check if external surfaces are documented in repo
    governance_doc = repo_root / "docs" / "remediation" / "hermes-zera" / "2026-04-10__stabilization-program" / "artifacts" / "external_governance_decision.md"
    if governance_doc.exists():
        results["governance_documented"] = True
    else:
        results["governance_documented"] = False
        results["warnings"].append("No external governance decision document found")

    # Overall: ok if all detected surfaces are documented
    if results["surfaces_found"] and not results.get("governance_documented"):
        results["ok"] = False

    return results


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}External Cron Governance Check{NC}")
    print(f"{YELLOW}{'='*60}{NC}\n")

    results = check_external_cron(repo_root)

    print(f"Surfaces checked: {len(results['surfaces_checked'])}")
    for name in results["surfaces_checked"]:
        print(f"  🔍 {name}")

    if results["surfaces_found"]:
        print(f"\n{YELLOW}⚠️  External surfaces detected: {len(results['surfaces_found'])}{NC}")
        for s in results["surfaces_found"]:
            print(f"  {YELLOW}• {s['name']} (risk: {s['risk']}) — {s['status']}{NC}")
            if "files" in s:
                for f in s["files"]:
                    print(f"    - {f}")

    if results["surfaces_missing"]:
        print(f"\n{GREEN}✅ External surfaces not present: {len(results['surfaces_missing'])}{NC}")
        for name in results["surfaces_missing"]:
            print(f"  {GREEN}• {name}{NC}")

    if results.get("governance_documented"):
        print(f"\n{GREEN}✅ External governance documented{NC}")
    else:
        print(f"\n{YELLOW}⚠️  External governance NOT documented{NC}")

    if results["warnings"]:
        print(f"\n{YELLOW}⚠️  Warnings: {len(results['warnings'])}{NC}")
        for w in results["warnings"]:
            print(f"  • {w}")

    print(f"\n{'='*60}")
    if results["ok"]:
        print(f"{GREEN}✅ External cron governance check passed{NC}")
    else:
        print(f"{RED}❌ External cron governance check FAILED — unmanaged external cron detected{NC}")
        print(f"   Run: cp external_cron_config.json docs/remediation/hermes-zera/*/artifacts/")
        print(f"   Or: rm -rf ~/.hermes/profiles/zera/cron/ if not needed")
    print(f"{'='*60}")

    if not results["ok"]:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
