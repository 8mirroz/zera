#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def catalog(root: Path) -> dict[str, Any]:
    return load_json(root / "configs/tooling/workflow_sets_catalog.json")


def _workflow_basename(path_str: str) -> str:
    return Path(path_str).name


def validate_catalog(root: Path) -> dict[str, Any]:
    data = catalog(root)
    wf_sets = data.get("workflow_sets", {})
    presets = data.get("presets", {})
    errors: list[str] = []
    warnings: list[str] = []

    for set_name, spec in wf_sets.items():
        seq = list(spec.get("sequence", []))
        post = list(spec.get("post_actions", []))
        for wf in seq + post:
            p = root / wf
            if not p.exists():
                errors.append(f"{set_name}: missing workflow file: {wf}")

    for preset_name, spec in presets.items():
        for set_name in spec.get("default_set_order", []):
            if set_name not in wf_sets:
                errors.append(f"{preset_name}: unknown set in default_set_order: {set_name}")
        for c_key, set_name in (spec.get("path_mapping") or {}).items():
            if set_name not in wf_sets:
                errors.append(f"{preset_name}: unknown set in path_mapping[{c_key}]={set_name}")
        for mode, set_name in (spec.get("explicit_modes") or {}).items():
            if set_name not in wf_sets:
                errors.append(f"{preset_name}: unknown set in explicit_modes[{mode}]={set_name}")

    # Check for duplicate workflow file usage for awareness (not error).
    usage_counts: dict[str, int] = {}
    for spec in wf_sets.values():
        for wf in list(spec.get("sequence", [])) + list(spec.get("post_actions", [])):
            usage_counts[wf] = usage_counts.get(wf, 0) + 1
    repeated = sorted([f"{k} x{v}" for k, v in usage_counts.items() if v > 2])
    if repeated:
        warnings.append(f"workflow files reused across many sets: {repeated}")

    status = "ok" if not errors else "error"
    return {"status": status, "errors": errors, "warnings": warnings}


def install_preset(root: Path, preset_name: str) -> dict[str, Any]:
    data = catalog(root)
    wf_sets = data.get("workflow_sets", {})
    presets = data.get("presets", {})
    if preset_name not in presets:
        raise ValueError(f"Unknown preset: {preset_name}")

    v = validate_catalog(root)
    if v["status"] != "ok":
        raise ValueError("Catalog validation failed: " + "; ".join(v["errors"]))

    preset = presets[preset_name]
    resolved_sets: dict[str, Any] = {}
    for set_name in preset.get("default_set_order", []):
        spec = wf_sets[set_name]
        resolved_sets[set_name] = {
            "goal": spec.get("goal"),
            "when_to_apply": spec.get("when_to_apply", []),
            "sequence": [_workflow_basename(p) for p in spec.get("sequence", [])],
            "sequence_paths": spec.get("sequence", []),
            "post_actions": [_workflow_basename(p) for p in spec.get("post_actions", [])],
            "post_action_paths": spec.get("post_actions", []),
            "algorithm": spec.get("algorithm", {}),
        }

    active = {
        "version": data.get("version"),
        "installed_at": utc_now_iso(),
        "preset": preset_name,
        "selection_policy": data.get("selection_policy", {}),
        "source_repositories": data.get("source_repositories", []),
        "path_mapping": preset.get("path_mapping", {}),
        "explicit_modes": preset.get("explicit_modes", {}),
        "always_run_preflight": preset.get("always_run_preflight", []),
        "always_run_post_c3_plus": preset.get("always_run_post_c3_plus", []),
        "default_set_order": preset.get("default_set_order", []),
        "sets": resolved_sets
    }

    out_path = root / ".agents/config/workflow_sets.active.json"
    dump_json(out_path, active)
    return {
        "status": "ok",
        "preset": preset_name,
        "output": str(out_path.relative_to(root)),
        "sets_installed": list(resolved_sets.keys())
    }


def list_presets(root: Path) -> dict[str, Any]:
    data = catalog(root)
    return {
        "status": "ok",
        "presets": data.get("presets", {}),
        "workflow_sets": list((data.get("workflow_sets") or {}).keys())
    }


def show_active(root: Path) -> dict[str, Any]:
    path = root / ".agents/config/workflow_sets.active.json"
    if not path.exists():
        return {"status": "error", "error": "No active workflow sets installed"}
    return {"status": "ok", "active": load_json(path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage global workflow set presets for Antigravity Agent OS")
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="Validate workflow sets catalog")
    sub.add_parser("list", help="List available workflow sets and presets")
    ins = sub.add_parser("install", help="Install a workflow set preset into .agents/config")
    ins.add_argument("--preset", required=True, help="Preset name (e.g. speed_free_max)")
    sub.add_parser("show-active", help="Show installed active workflow set config")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    try:
        if args.cmd == "validate":
            result = validate_catalog(root)
            code = 0 if result["status"] == "ok" else 1
        elif args.cmd == "list":
            result = list_presets(root)
            code = 0
        elif args.cmd == "install":
            result = install_preset(root, args.preset)
            code = 0
        elif args.cmd == "show-active":
            result = show_active(root)
            code = 0 if result["status"] == "ok" else 1
        else:
            raise ValueError(f"Unknown command: {args.cmd}")

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        return code
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print(f"error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

