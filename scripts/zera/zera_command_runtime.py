#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _resolve_root() -> Path:
    for env_key in ("ZERA_REPO_ROOT", "AGENT_OS_REPO_ROOT"):
        candidate = os.getenv(env_key)
        if candidate:
            return Path(candidate).expanduser().resolve()
    script_path = Path(__file__).resolve()
    candidate = script_path.parents[2]
    if (candidate / "configs").exists() and (candidate / "repos").exists():
        return candidate
    return script_path.parents[1]


ROOT = _resolve_root()
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.observability import emit_zera_command_event
from agent_os.zera_command_os import ZeraCommandOS


def _read_objective(args: argparse.Namespace) -> str:
    if getattr(args, "objective_file", None):
        return Path(args.objective_file).read_text(encoding="utf-8")
    return str(getattr(args, "objective", "") or "")


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _execute_prompt(client_id: str, prompt: str) -> int:
    if client_id == "repo_native":
        proc = subprocess.run(["zera", "chat", "-q", prompt], check=False)
        return int(proc.returncode)
    if client_id == "hermes":
        proc = subprocess.run(["hermes", "-p", "zera", "chat", "-q", prompt], check=False)
        return int(proc.returncode)
    print("Execution for gemini is render-only in this pilot.", file=sys.stderr)
    return 2


def _emit_runtime_event(event_type: str, payload: dict) -> None:
    emit_zera_command_event(event_type, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo-native Zera command runtime bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_catalog = sub.add_parser("catalog")
    p_catalog.add_argument("--json", action="store_true")

    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("--client", default="repo_native")
    p_resolve.add_argument("--command", default=None)
    p_resolve.add_argument("--objective", default="")
    p_resolve.add_argument("--objective-file", default=None)
    p_resolve.add_argument("--json", action="store_true")

    p_render = sub.add_parser("render")
    p_render.add_argument("--client", default="repo_native")
    p_render.add_argument("--command", default=None)
    p_render.add_argument("--objective", default="")
    p_render.add_argument("--objective-file", default=None)
    p_render.add_argument("--branch-manifest-path", default=None)
    p_render.add_argument("--json", action="store_true")

    p_branch = sub.add_parser("branch-manifest")
    p_branch.add_argument("--client", default="repo_native")
    p_branch.add_argument("--command", required=True)
    p_branch.add_argument("--branch-type", required=True)
    p_branch.add_argument("--run-id", required=True)
    p_branch.add_argument("--objective", default="")
    p_branch.add_argument("--objective-file", default=None)
    p_branch.add_argument("--output", default=None)
    p_branch.add_argument("--json", action="store_true")

    p_source = sub.add_parser("source-card")
    p_source.add_argument("--source-id", required=True)
    p_source.add_argument("--source-name", required=True)
    p_source.add_argument("--components", default="")
    p_source.add_argument("--output", default=None)
    p_source.add_argument("--json", action="store_true")

    p_merge = sub.add_parser("branch-merge")
    p_merge.add_argument("--manifest-file", default=None)
    p_merge.add_argument("--manifest-json", default=None)
    p_merge.add_argument("--classification", required=True)
    p_merge.add_argument("--summary", required=True)
    p_merge.add_argument("--stable-memory-write", action="store_true")
    p_merge.add_argument("--personality-promotion", action="store_true")
    p_merge.add_argument("--output", default=None)
    p_merge.add_argument("--json", action="store_true")

    p_governor = sub.add_parser("governor-check")
    p_governor.add_argument("--axis-deltas-json", required=True)
    p_governor.add_argument("--cycle-significant-deltas", type=int, default=0)
    p_governor.add_argument("--consecutive-regressions", type=int, default=0)
    p_governor.add_argument("--router-rewrite", action="store_true")
    p_governor.add_argument("--review-approved", action="store_true")
    p_governor.add_argument("--json", action="store_true")

    p_import = sub.add_parser("import-validate")
    p_import.add_argument("--artifact-id", required=True)
    p_import.add_argument("--imported-files", default="")
    p_import.add_argument("--json", action="store_true")

    p_exec = sub.add_parser("execute")
    p_exec.add_argument("--client", default="repo_native")
    p_exec.add_argument("--command", default=None)
    p_exec.add_argument("--objective", default="")
    p_exec.add_argument("--objective-file", default=None)
    p_exec.add_argument("--branch-manifest-path", default=None)
    p_exec.add_argument("--print-only", action="store_true")
    p_exec.add_argument("--json", action="store_true")

    args = parser.parse_args()
    runtime = ZeraCommandOS(ROOT)

    if args.cmd == "catalog":
        payload = {"commands": runtime.command_catalog()}
        if args.json:
            _print_json(payload)
        else:
            for row in payload["commands"]:
                print(f"{row['command_id']}: {row['mode_binding']} / {row['loop_binding']} / {','.join(row['allowed_clients'])}")
        return 0

    if args.cmd == "resolve":
        payload = runtime.resolve_command(command_id=args.command, objective=_read_objective(args), client_id=args.client)
        _emit_runtime_event(
            "zera_command_resolved",
            {
                "command_id": payload["command_id"],
                "requested_command_id": payload.get("requested_command_id"),
                "client_id": payload["client_id"],
                "loop": payload["loop"],
                "candidate_class": payload.get("candidate_class"),
                "workflow_type": payload.get("workflow_type"),
                "decision": "degraded" if payload.get("degraded") else "resolved",
                "rollback_path": payload.get("rollback_path"),
                "approval_route": payload.get("approval_route"),
                "risk_level": payload.get("risk_level"),
                "mode": payload.get("mode"),
                "target_layer": "command_runtime",
                "message": f"Resolved {payload['command_id']}",
                "data": {
                    "decision_reason": payload.get("decision_reason"),
                    "confidence": payload.get("confidence"),
                    "degradation_reason": payload.get("degradation_reason"),
                },
            },
        )
        if args.json:
            _print_json(payload)
        else:
            print(payload["command_id"])
        return 0

    if args.cmd == "render":
        payload = runtime.render_prompt(
            command_id=args.command,
            objective=_read_objective(args),
            client_id=args.client,
            branch_manifest_path=args.branch_manifest_path,
        )
        _emit_runtime_event(
            "zera_command_rendered",
            {
                "command_id": payload["command_id"],
                "requested_command_id": payload.get("requested_command_id"),
                "client_id": payload["client_id"],
                "loop": payload["loop"],
                "candidate_class": payload.get("candidate_class"),
                "workflow_type": payload.get("workflow_type"),
                "decision": "rendered",
                "rollback_path": payload.get("rollback_path"),
                "approval_route": payload.get("approval_route"),
                "risk_level": payload.get("risk_level"),
                "mode": payload.get("mode"),
                "branch_type": None,
                "target_layer": "command_runtime",
                "message": f"Rendered {payload['command_id']}",
            },
        )
        if args.json:
            _print_json(payload)
        else:
            print(payload["prompt"])
        return 0

    if args.cmd == "branch-manifest":
        payload = runtime.create_branch_manifest(
            command_id=args.command,
            client_id=args.client,
            branch_type=args.branch_type,
            objective=_read_objective(args),
            run_id=args.run_id,
        )
        _emit_runtime_event(
            "zera_branch_created",
            {
                "command_id": payload["source_command"],
                "client_id": args.client,
                "loop": "branching",
                "candidate_class": None,
                "workflow_type": "branch_creation",
                "decision": "created",
                "rollback_path": "discard branch artifacts and revert to single-thread analysis",
                "approval_route": "review_required" if payload.get("requires_persona_review") else "allow_low_risk_after_eval",
                "risk_level": "medium",
                "branch_id": payload["branch_id"],
                "branch_type": payload["branch_type"],
                "target_layer": "branch_runtime",
                "message": f"Created branch {payload['branch_id']}",
            },
        )
        if args.output:
            Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json or not args.output:
            _print_json(payload)
        return 0

    if args.cmd == "source-card":
        components = [part.strip() for part in str(args.components).split(",") if part.strip()]
        payload = runtime.create_source_card(
            source_id=args.source_id,
            source_name=args.source_name,
            extracted_components=components,
        )
        _emit_runtime_event(
            "zera_source_card_created",
            {
                "command_id": "zera:foundry-ingest",
                "client_id": "repo_native",
                "loop": "capability",
                "candidate_class": "research_target",
                "workflow_type": "source_card_creation",
                "decision": "created",
                "rollback_path": "delete staged source card",
                "approval_route": "review_required",
                "risk_level": "low",
                "source_id": payload["source_id"],
                "import_lane": payload.get("import_lane"),
                "target_layer": "research_registry",
                "message": f"Created source card {payload['source_id']}",
            },
        )
        if args.output:
            Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json or not args.output:
            _print_json(payload)
        return 0

    if args.cmd == "branch-merge":
        if args.manifest_file:
            manifest = json.loads(Path(args.manifest_file).read_text(encoding="utf-8"))
        elif args.manifest_json:
            manifest = json.loads(args.manifest_json)
        else:
            raise SystemExit("branch-merge requires --manifest-file or --manifest-json")
        payload = runtime.create_branch_merge_record(
            manifest=manifest,
            candidate_classification=args.classification,
            summary=args.summary,
            stable_memory_write_requested=args.stable_memory_write,
            personality_promotion_requested=args.personality_promotion,
        )
        _emit_runtime_event(
            "zera_branch_merged",
            {
                "command_id": payload["source_command"],
                "client_id": "repo_native",
                "loop": "branching",
                "candidate_class": payload["candidate_classification"],
                "workflow_type": "branch_merge",
                "decision": payload["decision"],
                "rollback_path": payload["rollback_path"],
                "approval_route": "review_required" if payload["requires_review"] else "allow_low_risk_after_eval",
                "risk_level": "high" if payload["candidate_classification"] in {"mixed", "governance"} else "medium",
                "branch_id": payload["branch_id"],
                "branch_type": payload["branch_type"],
                "target_layer": "branch_runtime",
                "message": f"Recorded branch merge for {payload['branch_id']}",
            },
        )
        if args.output:
            Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.json or not args.output:
            _print_json(payload)
        return 0

    if args.cmd == "governor-check":
        payload = runtime.evaluate_governor(
            axis_deltas=json.loads(args.axis_deltas_json),
            cycle_significant_deltas=args.cycle_significant_deltas,
            consecutive_regressions=args.consecutive_regressions,
            router_rewrite=args.router_rewrite,
            review_approved=args.review_approved,
        )
        if args.json:
            _print_json(payload)
        else:
            print("blocked" if payload["blocked"] else "ok")
        return 0

    if args.cmd == "import-validate":
        imported_files = [part.strip() for part in str(args.imported_files).split(",") if part.strip()]
        payload = runtime.validate_import_activation(
            artifact_id=args.artifact_id,
            imported_files=imported_files,
        )
        if args.json:
            _print_json(payload)
        else:
            print("blocked" if payload["blocked"] else "ok")
        return 0

    if args.cmd == "execute":
        payload = runtime.render_prompt(
            command_id=args.command,
            objective=_read_objective(args),
            client_id=args.client,
            branch_manifest_path=args.branch_manifest_path,
        )
        if args.json:
            _print_json(payload)
        if args.print_only:
            if not args.json:
                print(payload["prompt"])
            return 0
        import time
        try:
            from scripts.tracing_collector import collector
        except ImportError:
            collector = None

        start_t = time.time()
        exit_code = _execute_prompt(args.client, payload["prompt"])
        duration = (time.time() - start_t) * 1000

        if collector:
            wf_name = payload.get("workflow_type") or payload["command_id"]
            collector.log_workflow_step(wf_name, "execute_prompt", duration, success=(exit_code == 0))
        _emit_runtime_event(
            "zera_command_executed",
            {
                "command_id": payload["command_id"],
                "requested_command_id": payload.get("requested_command_id"),
                "client_id": payload["client_id"],
                "loop": payload["loop"],
                "candidate_class": payload.get("candidate_class"),
                "workflow_type": payload.get("workflow_type"),
                "decision": "executed",
                "rollback_path": payload.get("rollback_path"),
                "approval_route": payload.get("approval_route"),
                "risk_level": payload.get("risk_level"),
                "mode": payload.get("mode"),
                "target_layer": "command_runtime",
                "status": "ok" if exit_code == 0 else "error",
                "message": f"Executed {payload['command_id']}",
                "data": {
                    "exit_code": exit_code,
                    "branch_manifest_path": args.branch_manifest_path,
                },
            },
        )
        return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
