#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_templates(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "configs/tooling/notebooklm_agent_router_templates.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _state_details(workflow: str) -> list[dict[str, str]]:
    if workflow == "research_artifacts":
        return [
            {"state": "ingest", "goal": "collect objective and source constraints", "exit": "objective+scope confirmed"},
            {"state": "research", "goal": "run deep research and import sources", "exit": "sources imported"},
            {"state": "synthesis", "goal": "produce concise factual synthesis", "exit": "summary + open questions"},
            {"state": "metadata_extraction", "goal": "extract notebook metadata and source status", "exit": "metadata.json generated"},
            {"state": "artifact_generation", "goal": "generate report/audio/video/cinematic as requested", "exit": "artifact completed"},
            {"state": "final_review", "goal": "quality gate and delivery packet", "exit": "approved output"},
        ]
    if workflow == "ide_assist":
        return [
            {"state": "ingest", "goal": "collect task and codebase context", "exit": "task boundaries fixed"},
            {"state": "context_mapping", "goal": "map docs to project modules", "exit": "module-to-doc map"},
            {"state": "implementation_guidance", "goal": "produce actionable coding guidance", "exit": "implementation plan"},
            {"state": "verification", "goal": "define test and acceptance checks", "exit": "validation checklist"},
            {"state": "handoff", "goal": "handoff compact output for IDE execution", "exit": "ready-to-code packet"},
        ]
    return [
        {"state": "ingest", "goal": "collect bug report and artifacts", "exit": "failure scope fixed"},
        {"state": "failure_isolation", "goal": "isolate failing subsystem", "exit": "failure boundary identified"},
        {"state": "root_cause_hypothesis", "goal": "propose top root-cause hypotheses", "exit": "ranked hypotheses"},
        {"state": "fix_plan", "goal": "build minimal-risk fix strategy", "exit": "stepwise remediation plan"},
        {"state": "validation", "goal": "define regression checks and rollback", "exit": "verified rollout checklist"},
    ]


def _commands_for_workflow(workflow: str, objective: str, output_path: str) -> list[str]:
    common = [
        'notebooklm create "AG Router Session"',
        f'notebooklm source add-research "{objective}" --mode deep --no-wait',
        "notebooklm research wait --import-all --timeout 300",
    ]
    if workflow == "research_artifacts":
        return [
            *common,
            "notebooklm ask \"Provide structured synthesis with key risks and unknowns\"",
            "notebooklm metadata > ./notebook_metadata.json",
            "notebooklm generate report --format briefing-doc --wait --retry 3",
            "notebooklm generate video --format cinematic --wait --retry 3",
            f"notebooklm download report {output_path} --latest --force",
        ]
    if workflow == "ide_assist":
        return [
            *common,
            "notebooklm ask \"Map findings to implementation tasks and modules\"",
            "notebooklm ask \"Provide acceptance tests and edge cases\"",
            f"notebooklm ask \"Export concise execution checklist to markdown-style text\" > {output_path}",
        ]
    return [
        *common,
        "notebooklm ask \"Identify likely root causes and confidence for each\"",
        "notebooklm ask \"Propose minimal-risk fix plan and test matrix\"",
        f"notebooklm ask \"Produce final bug triage report\" > {output_path}",
    ]


def build_router_packet(
    repo_root: Path,
    *,
    workflow: str,
    objective: str,
    output_path: str = "./notebooklm-router-output.md",
    with_checkpoints: bool = True,
) -> dict[str, Any]:
    templates = _load_templates(repo_root)
    workflows = templates.get("workflows", {})
    if workflow not in workflows:
        raise ValueError(f"Unknown workflow: {workflow}")

    states = _state_details(workflow)
    checkpoints = [
        "After each state, confirm: Approve? (y/n/next)",
        "On fail: return to previous state with delta fixes only",
        "No claims beyond NotebookLM sources",
    ] if with_checkpoints else []

    router_prompt = (
        "You are a stateful workflow router for NotebookLM-grounded execution.\n"
        f"Workflow: {workflow}.\n"
        f"Objective: {objective}.\n"
        "Rules:\n"
        "1. Execute states strictly in order.\n"
        "2. Output only state result and transition decision.\n"
        "3. If evidence is insufficient, return NEED_INPUT with exact missing source.\n"
        "4. Do not hallucinate; cite only available notebook evidence.\n"
        "5. Stop only after final review is approved."
    )

    return {
        "workflow": workflow,
        "description": workflows[workflow].get("description"),
        "objective": objective,
        "states": states,
        "checkpoints": checkpoints,
        "quality_gates": {
            "grounded": "All key claims traceable to notebook sources",
            "actionable": "Output has concrete next steps",
            "bounded": "Unknowns and risks are explicitly listed",
        },
        "commands": _commands_for_workflow(workflow, objective, output_path),
        "router_prompt": router_prompt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate NotebookLM router prompt packets")
    parser.add_argument("workflow", choices=["research_artifacts", "ide_assist", "debug_triage"])
    parser.add_argument("objective")
    parser.add_argument("--output-path", default="./notebooklm-router-output.md")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-checkpoints", action="store_true")
    args = parser.parse_args()

    packet = build_router_packet(
        _repo_root(),
        workflow=args.workflow,
        objective=args.objective,
        output_path=args.output_path,
        with_checkpoints=not args.no_checkpoints,
    )

    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(f"Workflow: {packet['workflow']}")
        print(f"Objective: {packet['objective']}")
        print("\nStates:")
        for state in packet["states"]:
            print(f"- {state['state']}: {state['goal']} -> exit: {state['exit']}")
        print("\nCommands:")
        for cmd in packet["commands"]:
            print(f"- {cmd}")
        print("\nRouter Prompt:\n")
        print(packet["router_prompt"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
