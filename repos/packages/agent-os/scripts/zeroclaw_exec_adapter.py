#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.background_job_planner import select_background_jobs

try:
    import mlx_lm
    from mlx_lm import load
    HAS_MLX = True
except ImportError:
    HAS_MLX = False


def _repo_root() -> Path:
    return Path.cwd()


def _zero_bin_version() -> str | None:
    raw = (os.getenv("ZEROCLAW_BIN") or "").strip()
    candidate = None
    if raw:
        candidate = raw if os.path.isabs(raw) else shutil.which(raw)
    if not candidate:
        candidate = shutil.which("zeroclaw")
    if not candidate:
        return None
    try:
        proc = subprocess.run(
            [candidate, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or proc.stderr or "").strip() or None


def _initiative_proposals(mode: str, objective: str, background_profile: str | None) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    objective_lower = objective.lower()
    if mode in {"plan", "analysis"}:
        proposals.append(
            {
                "title": f"Convert objective into actionable plan: {objective[:80]}",
                "action_type": "task_follow_up",
                "rationale": "Structured follow-up increases completion rate for hybrid companion-operator flows.",
            }
        )
    if mode in {"research", "analysis"}:
        proposals.append(
            {
                "title": "Schedule evidence refresh loop",
                "action_type": "research_refresh",
                "rationale": "Refresh evidence before acting on stale assumptions.",
            }
        )
    if background_profile == "zera-companion":
        proposals.append(
            {
                "title": "Review active personal goals",
                "action_type": "goal_review",
                "rationale": "Bounded proactive support for existing plans.",
            }
        )
    if any(token in objective_lower for token in ["email", "contact", "message", "reach out", "write to"]):
        proposals.append(
            {
                "title": "Prepare an external contact proposal for operator approval",
                "action_type": "external_contact",
                "rationale": "External outreach must stay gated and visible.",
            }
        )
    if any(token in objective_lower for token in ["trade", "buy", "sell", "wallet", "defi"]):
        proposals.append(
            {
                "title": "Prepare a finance simulation only",
                "action_type": "financial_commitment",
                "rationale": "Financial actions must never execute autonomously in production.",
            }
        )
    return proposals


def _relative_dependency_ref(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _build_self_reflection(route: dict[str, Any], repo_root: Path) -> dict[str, Any] | None:
    if str(route.get("background_job_type") or "") != "self_reflection":
        return None

    system_rules_path = repo_root / "configs/tooling/reflection_agent_system.md"
    dependency_refs = ["configs/tooling/self_reflection_schema.json"]
    if system_rules_path.exists():
        dependency_refs.append(_relative_dependency_ref(system_rules_path, repo_root))

    return {
        "summary": "The reflection run found an execution-clarity gap that should stay in evaluation mode until reviewed.",
        "improvement_area": "execution",
        "problem_statement": "Self-reflection can identify actionability gaps, but the current runtime should not turn those findings into silent behavior changes.",
        "root_cause_hypothesis": "Reflection output is structurally richer than the existing runtime gate, so safe proposals need an explicit review path before rollout.",
        "proposed_change": "Validate reflection proposals against the approved schema and route them to operator review unless they qualify for narrow memory-tag auto-apply.",
        "expected_benefit": "Reflection stays bounded, reviewable, and operationally useful without introducing hidden changes.",
        "risk_assessment": {
            "risk_level": "low",
            "main_risks": [
                "Over-gating could reduce iteration speed for harmless improvements.",
                "Operators may see more review traffic until thresholds are tuned."
            ],
            "safety_impact": "limited"
        },
        "bounded_action": {
            "action_type": "request_operator_review",
            "target": "reflection.runtime_gate",
            "limit": "Evaluate the gate only; do not auto-apply runtime behavior changes from this proposal."
        },
        "confidence": 0.50,
        "evidence_refs": [
            "trace:self_reflection_background_job"
        ],
        "validation_plan": {
            "method": "simulation",
            "checks": [
                "Reject payloads with forbidden fields or extra properties.",
                "Queue non-memory proposals for operator review."
            ]
        },
        "priority": "p2",
        "scope": "module",
        "affected_modules": [
            "runtime_providers.zeroclaw",
            "reflection_policy"
        ],
        "success_criteria": [
            "Self-reflection proposals are schema-valid before emission.",
            "No proposal from this run auto-applies a behavior change."
        ],
        "failure_modes": [
            "Review-only proposals could be mistaken for approved changes."
        ],
        "assumptions": [
            "The reflection gate is still under operator-supervised rollout."
        ],
        "notes_for_operator": "Review this proposal as a validation artifact, not as an approved change.",
        "change_type": "evaluation_only",
        "time_horizon": "short_term",
        "dependency_refs": dependency_refs
    }


def build_response(payload: dict[str, Any], profile: str) -> dict[str, Any]:
    route = payload.get("route_decision", {})
    route = route if isinstance(route, dict) else {}
    repo_root = _repo_root()
    objective = str(payload.get("objective") or "").strip()
    mode = str(route.get("mode") or route.get("selected_mode") or "plan")
    persona_id = str(route.get("persona_id") or "antigravity-default")
    persona_version = str(route.get("persona_version") or persona_id)
    background_profile = str(route.get("background_profile") or "") or None
    scheduler_profile = str(route.get("scheduler_profile") or "") or None
    self_reflection = _build_self_reflection(route, repo_root)
    
    # Smart Response Generation for ZeRa profiles
    is_zera_profile = profile.startswith("zera-")
    response_text = None
    
    if is_zera_profile and HAS_MLX:
        try:
            model_id = route.get("primary_model", "mlx-community/quantized-gemma-2b-it")
            if ":" in model_id:
                 model_id = model_id.split(":")[-1]
            
            model, tokenizer = load(model_id)
            persona_context = route.get("persona_context") or ""
            
            messages = []
            if persona_context:
                messages.append({"role": "user", "content": f"{persona_context}\n\n[USER OBJECTIVE]\n{objective}"})
            else:
                messages.append({"role": "user", "content": objective})
            
            if hasattr(tokenizer, "apply_chat_template"):
                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                prompt = messages[0]["content"]
            
            # Simple sync generate for the adapter
            response_text = mlx_lm.generate(model, tokenizer, prompt=prompt, max_tokens=1024)
        except Exception as e:
            response_text = f"Error during local inference: {e}"

    if not response_text:
        response_text = (
            f"Zera runtime handled the request in {mode} mode. "
            "I may be wrong on details, so let's verify external assumptions and keep the next step concrete."
        )
    meta: dict[str, Any] = {
        "adapter_version": "2026-03-11",
        "selected_mode": mode,
        "persona_id": persona_id,
        "persona_version": persona_version,
        "background_jobs": select_background_jobs(background_profile, mode, route),
        "initiative_proposals": _initiative_proposals(mode, objective, background_profile),
        "memory_updates": [
            {
                "key": f"run:{payload.get('run_id')}",
                "payload": {
                    "objective": objective,
                    "mode": mode,
                    "profile": profile,
                },
                "options": {
                    "memory_class": "working_memory",
                    "ttl_seconds": 86400,
                    "confidence": 0.82,
                },
            }
        ],
        "execution_contract": {
            "profile": profile,
            "scheduler_profile": scheduler_profile,
            "background_profile": background_profile,
            "zero_bin_version": _zero_bin_version(),
        },
    }
    if self_reflection is not None:
        meta["self_reflection"] = self_reflection
    return {
        "status": "completed",
        "diff_summary": f"ZeroClaw stdio adapter executed profile '{profile}' for objective '{objective[:80]}'.",
        "test_report": {
            "status": "not-run",
            "details": "ZeroClaw execution adapter returned a structured runtime contract.",
        },
        "artifacts": [],
        "next_action": "Promote the adapter contract to the real ZeroClaw binary integration once the target node is provisioned.",
        "response_text": response_text,
        "meta": meta,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ZeroClaw stdio execution adapter")
    parser.add_argument("--profile", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": f"invalid input: {exc}"}))
        return 1
    response = build_response(payload if isinstance(payload, dict) else {}, args.profile)
    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
