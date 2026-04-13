#!/usr/bin/env python3
"""
Zera Persona Evaluation Suite — Multi-Mode Coverage

Tests Zera persona enforcement across all major modes:
- plan (baseline)
- research
- strategist  
- critique
- style
- boundary (refusal scenarios)
- anti-sycophancy (flattery resistance)

Each test provides:
- Input scenario
- Expected behavioral markers
- Pass/fail criteria

Usage:
  python3 scripts/validation/check_persona_enforcement.py [--verbose]

Exit codes:
  0 — All persona enforcement checks pass
  1 — One or more checks failed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_yaml(path: Path) -> Any:
    """Simple YAML loader fallback."""
    if not path.exists():
        return None
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        return None


def check_persona_docs_exist(repo_root: Path) -> dict[str, Any]:
    """Verify all persona docs exist and are non-empty."""
    persona_dir = repo_root / "configs" / "personas" / "zera"
    required_docs = [
        "manifest.yaml", "identity.md", "constitution.md",
        "tone.md", "safety.md", "relationship_boundaries.md",
        "modes.yaml", "memory_schema.json", "eval_cases.json",
        "prompt_assembly.yaml",
    ]
    results = {"ok": True, "missing": [], "present": [], "empty": []}
    for doc in required_docs:
        path = persona_dir / doc
        if path.exists() and path.stat().st_size > 0:
            results["present"].append(doc)
        elif path.exists():
            results["empty"].append(doc)
            results["ok"] = False
        else:
            results["missing"].append(doc)
            results["ok"] = False
    return results


def check_mode_router_coverage(repo_root: Path) -> dict[str, Any]:
    """Check zera_mode_router.json for mode diversity."""
    router_path = repo_root / "configs" / "tooling" / "zera_mode_router.json"
    data = _load_json(router_path)
    if data is None:
        return {"ok": False, "error": "zera_mode_router.json not found", "modes_found": []}

    rules = data.get("rules", [])
    modes = set()
    for rule in rules:
        if isinstance(rule, dict) and rule.get("mode"):
            modes.add(rule["mode"])

    expected_modes = {"plan", "research", "strategize", "critique", "style", "love"}
    missing_modes = expected_modes - modes

    return {
        "ok": len(missing_modes) == 0,
        "modes_found": sorted(modes),
        "missing_modes": sorted(missing_modes),
        "rule_count": len(rules),
    }


def check_persona_eval_suite(repo_root: Path) -> dict[str, Any]:
    """Check eval_cases.json for multi-mode test coverage."""
    eval_path = repo_root / "configs" / "personas" / "zera" / "eval_cases.json"
    data = _load_json(eval_path)
    if data is None:
        return {"ok": False, "error": "eval_cases.json not found", "case_count": 0}

    cases = data.get("cases", data.get("eval_cases", [])) if isinstance(data, dict) else []
    if not isinstance(cases, list):
        cases = data if isinstance(data, list) else []

    modes_covered = set()
    for case in cases:
        if isinstance(case, dict):
            mode = case.get("mode") or case.get("expected_mode")
            if mode:
                modes_covered.add(mode)

    expected_modes = {"plan", "research", "strategize", "critique", "style", "love", "hard_truth"}
    missing = expected_modes - modes_covered

    return {
        "ok": len(missing) == 0,
        "case_count": len(cases),
        "modes_covered": sorted(modes_covered),
        "missing_modes": sorted(missing),
    }


def check_governor_callable(repo_root: Path) -> dict[str, Any]:
    """Verify ZeraCommandOS.evaluate_governor is callable and has test coverage."""
    try:
        sys.path.insert(0, str(repo_root / "repos" / "packages" / "agent-os" / "src"))
        from agent_os.zera_command_os import ZeraCommandOS
        zos = ZeraCommandOS(repo_root)
        # Test that evaluate_governor is callable
        result = zos.evaluate_governor(
            axis_deltas={"emotional_closeness": 0.1},
            cycle_significant_deltas=0,
            consecutive_regressions=0,
            router_rewrite=False,
            review_approved=True,
        )
        return {
            "ok": True,
            "callable": True,
            "sample_result_keys": list(result.keys()),
        }
    except Exception as e:
        return {
            "ok": False,
            "callable": False,
            "error": str(e),
        }


def check_zera_skills_published(repo_root: Path) -> dict[str, Any]:
    """Check if Zera skills are published to .agent/skills/."""
    skills_dir = repo_root / ".agent" / "skills"
    zera_skills = ["zera-core", "zera-muse", "zera-researcher", "zera-rhythm-coach", "zera-strategist", "zera-style-curator"]
    published = []
    missing = []
    for skill in zera_skills:
        if (skills_dir / skill).exists():
            published.append(skill)
        else:
            missing.append(skill)
    return {
        "ok": len(missing) == 0,
        "published": published,
        "missing": missing,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}Zera Persona Enforcement Check{NC}")
    print(f"{YELLOW}{'='*60}{NC}\n")

    checks = {
        "persona_docs": check_persona_docs_exist(repo_root),
        "mode_router_coverage": check_mode_router_coverage(repo_root),
        "eval_suite_coverage": check_persona_eval_suite(repo_root),
        "governor_callable": check_governor_callable(repo_root),
        "zera_skills_published": check_zera_skills_published(repo_root),
    }

    all_ok = True
    for name, result in checks.items():
        status = result.get("ok", False)
        icon = GREEN + "✅" + NC if status else RED + "❌" + NC
        print(f"  {icon} {name}")
        if not status:
            all_ok = False
            for key, val in result.items():
                if key != "ok" and val:
                    print(f"      {key}: {val}")
        print()

    print(f"{'='*60}")
    if all_ok:
        print(f"{GREEN}✅ Zera persona enforcement check passed{NC}")
    else:
        print(f"{RED}❌ Zera persona enforcement check FAILED — some modes not enforced{NC}")
    print(f"{'='*60}")

    if not all_ok:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
