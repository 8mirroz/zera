#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_iso8601_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    raw = value
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        datetime.fromisoformat(raw)
    except Exception:
        return False
    return True


def _validate_v2_event(row: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    required_common = list(schema.get("required_common_fields", []))
    for key in required_common:
        if key not in row:
            errors.append(f"missing required field: {key}")

    if "ts" in row and not _is_iso8601_utc(row.get("ts")):
        errors.append("ts must be ISO-8601 string")

    if "event_type" in row and not isinstance(row.get("event_type"), str):
        errors.append("event_type must be string")
    if "run_id" in row and not isinstance(row.get("run_id"), str):
        errors.append("run_id must be string")
    if "level" in row and row.get("level") not in {"debug", "info", "warn", "error"}:
        errors.append("level must be one of debug|info|warn|error")
    if "data" in row and not isinstance(row.get("data"), dict):
        errors.append("data must be object")

    event_type = row.get("event_type")
    event_specs = schema.get("event_types", {})
    if isinstance(event_type, str) and event_type in event_specs:
        spec = event_specs[event_type] or {}
        for key in spec.get("required", []):
            if key not in row:
                errors.append(f"event {event_type}: missing required field {key}")

    return errors


def _validate_legacy_entry(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "schema_version" not in row:
        errors.append("legacy row missing schema_version")
        return errors
    entry = row.get("entry")
    if not isinstance(entry, dict):
        errors.append("legacy row missing object entry")
        return errors
    for key in ("timestamp", "run_id"):
        if key not in entry:
            errors.append(f"legacy row missing entry.{key}")
    if "timestamp" in entry and not _is_iso8601_utc(entry.get("timestamp")):
        errors.append("legacy entry.timestamp must be ISO-8601 string")
    return errors


def validate_trace_file(
    trace_file: Path,
    *,
    schema_path: Path,
    allow_legacy: bool,
) -> dict[str, Any]:
    schema = load_json(schema_path)
    if not trace_file.exists():
        return {
            "status": "error",
            "error": f"Trace file not found: {trace_file}",
        }

    lines = [line for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors: list[dict[str, Any]] = []
    v2_count = 0
    legacy_count = 0

    for idx, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except Exception as e:
            errors.append({"line": idx, "error": f"invalid json: {e}"})
            continue
        if not isinstance(row, dict):
            errors.append({"line": idx, "error": "row must be JSON object"})
            continue

        if "schema_version" in row and "entry" in row:
            if not allow_legacy:
                errors.append({"line": idx, "error": "legacy trace envelope not allowed"})
            else:
                legacy_errs = _validate_legacy_entry(row)
                if legacy_errs:
                    errors.append({"line": idx, "error": "; ".join(legacy_errs), "format": "legacy"})
                else:
                    legacy_count += 1
            continue

        row_errors = _validate_v2_event(row, schema)
        if row_errors:
            errors.append({"line": idx, "error": "; ".join(row_errors), "format": "v2"})
        else:
            v2_count += 1

    return {
        "status": "ok" if not errors else "error",
        "trace_file": str(trace_file),
        "schema_file": str(schema_path),
        "lines_total": len(lines),
        "v2_valid_count": v2_count,
        "legacy_valid_count": legacy_count,
        "errors_count": len(errors),
        "allow_legacy": allow_legacy,
        "errors": errors[:100],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Agent OS trace JSONL rows against Trace Event v2 (with optional legacy support)")
    p.add_argument("--file", dest="trace_file", help="Path to trace jsonl file (defaults to AGENT_OS_TRACE_FILE or logs/agent_traces.jsonl)")
    p.add_argument("--schema", dest="schema_file", help="Path to trace schema JSON (defaults to configs/tooling/trace_schema.json)")
    p.add_argument("--allow-legacy", action="store_true", help="Accept legacy {schema_version, entry} rows for migration")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    trace_file = Path(args.trace_file) if args.trace_file else Path(os.getenv("AGENT_OS_TRACE_FILE", str(root / "logs/agent_traces.jsonl")))
    if not trace_file.is_absolute():
        trace_file = root / trace_file
    schema_file = Path(args.schema_file) if args.schema_file else (root / "configs/tooling/trace_schema.json")
    if not schema_file.is_absolute():
        schema_file = root / schema_file

    try:
        result = validate_trace_file(trace_file, schema_path=schema_file, allow_legacy=bool(args.allow_legacy))
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for k, v in result.items():
            print(f"{k}: {v}")
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

