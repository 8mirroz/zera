#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .active_set_lib import parse_active_skills_md

INTERNAL_META_SKILLS = {
    "using-superpowers",
    "writing-skills",
}

OPTIONAL_UNPUBLISHED_CONFIG_SKILLS = {
    "openclaude",
    "zera-core",
    "zera-muse",
    "zera-researcher",
    "zera-rhythm-coach",
    "zera-strategist",
    "zera-style-curator",
}

OPTIONAL_EXTERNAL_ROUTING_SKILLS = {
    "generate-image",
    "photopea-automation",
    "hugging-face-cli",
    "hugging-face-datasets",
    "hugging-face-evaluation",
    "hugging-face-jobs",
    "hugging-face-model-trainer",
    "hugging-face-paper-publisher",
    "hugging-face-tool-builder",
    "hugging-face-trackio",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def list_agent_skills(root: Path) -> set[str]:
    skills_dir = root / ".agents/skills"
    if not skills_dir.exists():
        return set()
    return {
        p.name
        for p in skills_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }


def list_config_skills(root: Path) -> set[str]:
    base = root / "configs/skills"
    out: set[str] = set()
    for p in base.rglob("SKILL.md"):
        out.add(p.parent.name)
    return out


def list_external_skills(root: Path) -> set[str]:
    """
    Discover vendor skill packs under repos/skills/*/skills/*/SKILL.md.

    These are valid skill slugs for routing references, even if they are not
    currently published into `.agents/skills` via ACTIVE_SKILLS.md.
    """
    base = root / "repos/skills"
    out: set[str] = set()
    if not base.exists():
        return out
    for p in base.glob("*/skills/*/SKILL.md"):
        out.add(p.parent.name)
    return out


def extract_task_routing_skill_refs(root: Path) -> set[str]:
    path = root / "configs/rules/TASK_ROUTING.md"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    refs = set(re.findall(r"`([a-z0-9][a-z0-9-]*)`", text))
    ignore = {
        "writing-plans",
        "test-driven-development",
        "verification-before-completion",
        "executing-plans",
        "dispatching-parallel-agents",
        "subagent-driven-development",
        "systematic-debugging",
        "ui-premium",
        "design-system-architect",
        "visual-intelligence",
        "telegram-bot",
        "telegram-miniapp",
        "telegram-payments",
        "e-commerce",
        "requesting-code-review",
        "receiving-code-review",
        "using-git-worktrees",
        "finishing-a-development-branch",
        "brainstorming",
    }
    # Keep only strings that look like skill names and appear in known mapping rows.
    return {r for r in refs if r in ignore or "-" in r}


def build_report(root: Path) -> dict:
    active_md = root / "configs/skills/ACTIVE_SKILLS.md"
    active_specs = parse_active_skills_md(active_md)
    active = {s.name for s in active_specs}
    agent = list_agent_skills(root)
    config = list_config_skills(root)
    external = list_external_skills(root)
    routing_refs = extract_task_routing_skill_refs(root)
    known = config | agent | external | OPTIONAL_EXTERNAL_ROUTING_SKILLS

    missing_in_agent = sorted(active - agent)
    extra_in_agent = sorted(agent - active)
    referenced_but_unpublished = sorted((routing_refs & config) - agent)
    external_referenced_but_unpublished = sorted((routing_refs & external) - agent - config)
    referenced_unknown = sorted(routing_refs - known)
    config_unpublished = sorted(config - agent)
    ignored_unpublished = INTERNAL_META_SKILLS | OPTIONAL_UNPUBLISHED_CONFIG_SKILLS
    config_unpublished_internal_meta = sorted(set(config_unpublished) & ignored_unpublished)
    config_unpublished_actionable = sorted(set(config_unpublished) - ignored_unpublished)

    severity = "ok"
    # Hard-fail only when active skills are missing from published runtime copy.
    # Unknown routing refs are treated as warnings because TASK_ROUTING may include
    # optional external/vendor skill names not installed in the current workspace.
    if missing_in_agent:
        severity = "error"
    elif (
        extra_in_agent
        or referenced_but_unpublished
        or config_unpublished_actionable
        or referenced_unknown
    ):
        severity = "warn"

    migration_actions = [
        "Publish referenced skills to .agents/skills via ACTIVE_SKILLS.md, or remove references from TASK_ROUTING.md",
        "Keep internal meta skills unpublished (e.g. using-superpowers/writing-skills) and exclude them from active-set drift warnings",
        "Treat external vendor skill refs in TASK_ROUTING.md as optional unless they are promoted to active/published skills",
    ]

    return {
        "severity": severity,
        "counts": {
            "active": len(active),
            "agent": len(agent),
            "config": len(config),
            "external": len(external),
            "routing_refs": len(routing_refs),
        },
        "active_missing_in_agent": missing_in_agent,
        "agent_extra_not_in_active": extra_in_agent,
        "routing_refs_referenced_but_unpublished": referenced_but_unpublished,
        "routing_refs_external_known_unpublished": external_referenced_but_unpublished,
        "routing_refs_unknown": referenced_unknown,
        "config_skills_unpublished": config_unpublished,
        "config_skills_unpublished_actionable": config_unpublished_actionable,
        "config_skills_unpublished_internal_meta": config_unpublished_internal_meta,
        "migration_actions": migration_actions,
        "diff_spec_proposals": migration_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only validator for skills drift in Antigravity Agent OS")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report = build_report(repo_root())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["severity"] != "error" else 1

    print(f"severity={report['severity']}")
    for k, v in report["counts"].items():
        print(f"{k}: {v}")
    for key in (
        "active_missing_in_agent",
        "agent_extra_not_in_active",
        "routing_refs_referenced_but_unpublished",
        "routing_refs_external_known_unpublished",
        "routing_refs_unknown",
        "config_skills_unpublished",
        "config_skills_unpublished_actionable",
        "config_skills_unpublished_internal_meta",
    ):
        print(f"{key}: {', '.join(report[key]) if report[key] else '-'}")
    if report.get("migration_actions"):
        print("migration-actions:")
        for item in report["migration_actions"]:
            print(f"- {item}")
    return 0 if report["severity"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
