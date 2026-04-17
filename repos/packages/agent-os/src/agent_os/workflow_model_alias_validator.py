#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from agent_os.active_set_lib import parse_active_skills_md
from agent_os.yaml_compat import parse_simple_yaml


MODEL_ALIAS_RE = re.compile(r"\$(AGENT_MODEL_[A-Z0-9_]+)|\$\{(AGENT_MODEL_[A-Z0-9_]+)\}")
HARDCODED_MODEL_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:openrouter/)?"
    r"(?:openai|anthropic|google|deepseek|qwen|mistralai|meta-llama|moonshotai|zai)"
    r"/[A-Za-z0-9._:-]+"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_active_workflow_paths(root: Path) -> tuple[list[Path], list[str]]:
    cfg = json.loads((root / ".agents/config/workflow_sets.active.json").read_text(encoding="utf-8"))
    rels: list[str] = []

    for set_row in (cfg.get("sets") or {}).values():
        if not isinstance(set_row, dict):
            continue
        for key in ("sequence_paths", "post_action_paths"):
            for rel in set_row.get(key, []) or []:
                if isinstance(rel, str):
                    rels.append(rel)

    for key in ("always_run_preflight", "always_run_post_c3_plus"):
        for wf_name in cfg.get(key, []) or []:
            if isinstance(wf_name, str):
                name = wf_name if wf_name.endswith(".md") else f"{wf_name}.md"
                rels.append(f".agents/workflows/{name}")

    # de-duplicate preserving order
    out: list[Path] = []
    missing: list[str] = []
    seen: set[str] = set()
    for rel in rels:
        if rel in seen:
            continue
        seen.add(rel)
        p = root / rel
        if p.exists() and p.is_file():
            out.append(p)
        else:
            missing.append(rel)
    return out, missing


def _load_active_skill_files(root: Path) -> list[Path]:
    active_specs = parse_active_skills_md(root / "configs/skills/ACTIVE_SKILLS.md")
    out: list[Path] = []
    seen: set[str] = set()

    for spec in active_specs:
        # Validate source skill prompts (authoritative source)
        for p in spec.source_dir.rglob("*.md"):
            key = p.resolve().as_posix()
            if key not in seen and p.is_file():
                seen.add(key)
                out.append(p)
        # Validate published skills if present (runtime copy)
        published = root / ".agents/skills" / spec.name
        if published.exists():
            for p in published.rglob("*.md"):
                key = p.resolve().as_posix()
                if key not in seen and p.is_file():
                    seen.add(key)
                    out.append(p)
    return out


def _load_defined_model_aliases(root: Path) -> set[str]:
    models_yaml = parse_simple_yaml((root / "configs/orchestrator/models.yaml").read_text(encoding="utf-8"))
    models = models_yaml.get("models", {})
    if not isinstance(models, dict):
        return set()
    return set(str(k) for k in models.keys())


def _scan_file(path: Path, root: Path, defined_aliases: set[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    alias_refs: set[str] = set()
    for m in MODEL_ALIAS_RE.finditer(text):
        alias = m.group(1) or m.group(2)
        if alias:
            alias_refs.add(alias)

    unknown_aliases = sorted(a for a in alias_refs if a not in defined_aliases)

    hardcoded: list[str] = []
    for m in HARDCODED_MODEL_RE.finditer(text):
        token = m.group(0)
        if token not in hardcoded:
            hardcoded.append(token)

    return {
        "path": str(path.relative_to(root)),
        "alias_refs": sorted(alias_refs),
        "unknown_aliases": unknown_aliases,
        "hardcoded_models": hardcoded,
    }


def build_report(root: Path) -> dict[str, Any]:
    defined_aliases = _load_defined_model_aliases(root)
    workflow_files, missing_workflows = _load_active_workflow_paths(root)
    skill_files = _load_active_skill_files(root)

    scanned = [{"kind": "workflow", "path": p} for p in workflow_files] + [{"kind": "skill", "path": p} for p in skill_files]

    findings: list[dict[str, Any]] = []
    unknown_alias_total = 0
    hardcoded_total = 0

    for missing in missing_workflows:
        findings.append(
            {
                "severity": "error",
                "code": "MISSING_WORKFLOW_FILE",
                "kind": "workflow",
                "path": missing,
            }
        )

    for item in scanned:
        scan = _scan_file(item["path"], root, defined_aliases)
        if scan["unknown_aliases"]:
            unknown_alias_total += len(scan["unknown_aliases"])
            findings.append(
                {
                    "severity": "error",
                    "code": "UNKNOWN_MODEL_ALIAS",
                    "kind": item["kind"],
                    "path": scan["path"],
                    "aliases": scan["unknown_aliases"],
                }
            )
        if scan["hardcoded_models"]:
            hardcoded_total += len(scan["hardcoded_models"])
            findings.append(
                {
                    "severity": "warn",
                    "code": "HARDCODED_MODEL_ID",
                    "kind": item["kind"],
                    "path": scan["path"],
                    "models": scan["hardcoded_models"],
                }
            )

    severity = "ok"
    if any(f["severity"] == "error" for f in findings):
        severity = "error"
    elif findings:
        severity = "warn"

    migration_actions = [
        "Replace provider/model strings in active workflows/skills with $AGENT_MODEL_* aliases",
        "Add missing aliases to configs/orchestrator/models.yaml or update stale alias references in workflows/skills",
    ]

    return {
        "severity": severity,
        "summary": {
            "workflow_files_scanned": len(workflow_files),
            "workflow_files_missing": len(missing_workflows),
            "skill_files_scanned": len(skill_files),
            "defined_model_aliases": len(defined_aliases),
            "unknown_alias_refs": unknown_alias_total,
            "hardcoded_model_refs": hardcoded_total,
        },
        "findings": findings,
        "migration_actions": migration_actions,
        # One-cycle compat alias for older tooling conventions.
        "diff_spec_proposals": migration_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate active workflows/skills for model alias hygiene")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report = build_report(repo_root())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["severity"] != "error" else 1

    print(f"severity={report['severity']}")
    for k, v in report["summary"].items():
        print(f"{k}: {v}")
    if report["findings"]:
        print("findings:")
        for f in report["findings"]:
            print(f"- [{f['severity']}] {f['code']} {f.get('kind')} {f.get('path')}")
    else:
        print("findings: -")
    print("migration-actions:")
    for item in report.get("migration_actions", []):
        print(f"- {item}")
    return 0 if report["severity"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
