#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_lib_root(root: Path) -> Path:
    return root / ".agent/memory/build-library"


def ensure_structure(root: Path) -> dict[str, str]:
    lib = build_lib_root(root)
    dirs = [
        lib / "global/entries",
        lib / "projects",
        lib / "indexes",
        lib / "templates",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "build_library_root": str(lib)}


def entry_score_weights(root: Path) -> dict[str, float]:
    schema_path = root / "configs/tooling/build_memory_entry_schema.json"
    schema = load_json(schema_path)
    weights = schema.get("score_weights_default", {})
    return {str(k): float(v) for k, v in weights.items()}


def compute_weighted_total(entry: dict[str, Any], weights: dict[str, float]) -> float | None:
    scores = entry.get("scores", {})
    values: dict[str, float] = {}
    for key, w in weights.items():
        v = scores.get(key)
        if v is None:
            return None
        try:
            fv = float(v)
        except Exception:
            return None
        if fv < 0 or fv > 1:
            return None
        values[key] = fv * float(w)
    total = sum(values.values())
    return round(total, 4)


def validate_entry_shape(root: Path, entry: dict[str, Any]) -> list[str]:
    schema = load_json(root / "configs/tooling/build_memory_entry_schema.json")
    errors: list[str] = []
    for field in schema.get("required_fields", []):
        if field not in entry:
            errors.append(f"missing required field: {field}")

    constraints = schema.get("field_constraints", {})
    for field in ("scope", "kind", "status"):
        if field in entry and field in constraints and entry[field] not in constraints[field]:
            errors.append(f"invalid {field}: {entry[field]}")

    if entry.get("scope") == "project" and not entry.get("project_slug"):
        errors.append("project scope requires project_slug")
    if entry.get("scope") == "global" and entry.get("project_slug") not in (None, "", "null"):
        errors.append("global scope must not define project_slug")

    if not isinstance(entry.get("tags", []), list):
        errors.append("tags must be a list")
    if not isinstance(entry.get("models", []), list):
        errors.append("models must be a list")

    weights = entry_score_weights(root)
    weighted_total = compute_weighted_total(entry, weights)
    if weighted_total is None and (entry.get("scores") or {}).get("weighted_total") is None:
        errors.append("scores.weighted_total missing and cannot be computed from default weighted scores")
    return errors


def normalize_entry(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    out.setdefault("entry_id", f"buildmem-{uuid4()}")
    out.setdefault("scope", "global")
    out.setdefault("project_slug", None)
    out.setdefault("kind", "combo")
    out.setdefault("status", "candidate")
    out.setdefault("tags", [])
    out.setdefault("problem_types", [])
    out.setdefault("contexts", [])
    out.setdefault("models", [])
    out.setdefault("settings", {})
    out.setdefault("algorithm", {})
    out.setdefault("evidence", {})
    out.setdefault("scores", {})
    out.setdefault("provenance", {})
    out.setdefault("trace_refs", [])
    out.setdefault("ki_refs", [])
    out.setdefault("pattern_refs", [])
    out.setdefault("anti_patterns", [])
    out.setdefault("notes", "")

    out["provenance"].setdefault("captured_at", utc_now_iso())
    out["provenance"].setdefault("source", "antigravity-internal")
    out["provenance"].setdefault("links", [])

    weights = entry_score_weights(root)
    computed_total = compute_weighted_total(out, weights)
    if computed_total is not None:
        out["scores"]["weighted_total"] = computed_total

    search_chunks: list[str] = []
    for key in ("title", "summary", "notes"):
        v = out.get(key)
        if isinstance(v, str):
            search_chunks.append(v)
    search_chunks.extend([str(t) for t in out.get("tags", [])])
    search_chunks.extend([str(t) for t in out.get("problem_types", [])])
    algo = out.get("algorithm", {})
    if isinstance(algo, dict):
        for key in ("workflow", "strategy"):
            v = algo.get(key)
            if isinstance(v, str):
                search_chunks.append(v)
    out["_search_text"] = " ".join(search_chunks).lower()

    return out


def entry_output_path(root: Path, entry: dict[str, Any]) -> Path:
    lib = build_lib_root(root)
    scope = entry["scope"]
    if scope == "global":
        return lib / "global/entries" / f"{entry['entry_id']}.json"
    project_slug = str(entry["project_slug"])
    return lib / "projects" / project_slug / "entries" / f"{entry['entry_id']}.json"


def iter_entry_files(root: Path) -> list[Path]:
    lib = build_lib_root(root)
    files: list[Path] = []
    for base in [lib / "global/entries", lib / "projects"]:
        if not base.exists():
            continue
        for p in base.rglob("*.json"):
            if "/indexes/" in p.as_posix():
                continue
            files.append(p)
    return sorted(files)


def load_entries(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for p in iter_entry_files(root):
        try:
            raw = load_json(p)
            if not isinstance(raw, dict):
                raise ValueError("entry must be a JSON object")
            entry = normalize_entry(root, raw)
            problems = validate_entry_shape(root, entry)
            if problems:
                errors.append({"path": str(p), "error": "; ".join(problems)})
                continue
            entry["_path"] = str(p.relative_to(root))
            entries.append(entry)
        except Exception as e:
            errors.append({"path": str(p), "error": str(e)})
    return entries, errors


def rank_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def score(e: dict[str, Any]) -> tuple[float, float, int]:
        weighted = float((e.get("scores") or {}).get("weighted_total") or 0.0)
        confidence = float((e.get("scores") or {}).get("confidence") or 0.0)
        sample_size = int((e.get("evidence") or {}).get("sample_size") or 0)
        return (weighted, confidence, sample_size)

    return sorted(entries, key=score, reverse=True)


def minimal_index_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": entry.get("entry_id"),
        "scope": entry.get("scope"),
        "project_slug": entry.get("project_slug"),
        "kind": entry.get("kind"),
        "status": entry.get("status"),
        "title": entry.get("title"),
        "tags": entry.get("tags", []),
        "problem_types": entry.get("problem_types", []),
        "weighted_total": (entry.get("scores") or {}).get("weighted_total"),
        "confidence": (entry.get("scores") or {}).get("confidence"),
        "sample_size": (entry.get("evidence") or {}).get("sample_size"),
        "path": entry.get("_path"),
    }


def rebuild_indexes(root: Path) -> dict[str, Any]:
    ensure_structure(root)
    entries, errors = load_entries(root)

    global_entries = [e for e in entries if e.get("scope") == "global"]
    project_entries = [e for e in entries if e.get("scope") == "project"]

    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in global_entries:
        by_kind[str(e.get("kind"))].append(minimal_index_entry(e))
        for tag in e.get("tags", []):
            by_tag[str(tag)].append(minimal_index_entry(e))

    global_ranked = rank_entries(global_entries)
    project_ranked = rank_entries(project_entries)

    projects_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in project_entries:
        projects_map[str(e.get("project_slug"))].append(minimal_index_entry(e))

    top_by_problem_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in rank_entries(entries):
        for t in e.get("problem_types", []):
            bucket = top_by_problem_type[str(t)]
            if len(bucket) < 5:
                bucket.append(minimal_index_entry(e))

    lib = build_lib_root(root)
    global_index = {
        "generated_at": utc_now_iso(),
        "entries_count": len(global_entries),
        "errors_count": len(errors),
        "top_ranked": [minimal_index_entry(e) for e in global_ranked[:20]],
        "by_kind": dict(by_kind),
        "by_tag": dict(by_tag),
        "entries": [minimal_index_entry(e) for e in global_entries],
    }
    projects_index = {
        "generated_at": utc_now_iso(),
        "entries_count_total": len(project_entries),
        "errors_count": len(errors),
        "projects": dict(projects_map),
    }
    best_snapshot = {
        "generated_at": utc_now_iso(),
        "global_top": [minimal_index_entry(e) for e in global_ranked[:10]],
        "project_top": [minimal_index_entry(e) for e in project_ranked[:10]],
        "top_by_problem_type": dict(top_by_problem_type),
    }
    validation_report = {
        "generated_at": utc_now_iso(),
        "ok_entries_count": len(entries),
        "error_entries_count": len(errors),
        "errors": errors,
    }

    dump_json(lib / "indexes/global_index.json", global_index)
    dump_json(lib / "indexes/projects_index.json", projects_index)
    dump_json(lib / "indexes/best_library_snapshot.json", best_snapshot)
    dump_json(lib / "indexes/validation_report.json", validation_report)

    return {
        "status": "ok",
        "entries_total": len(entries),
        "errors_total": len(errors),
        "indexes": [
            str((lib / "indexes/global_index.json").relative_to(root)),
            str((lib / "indexes/projects_index.json").relative_to(root)),
            str((lib / "indexes/best_library_snapshot.json").relative_to(root)),
            str((lib / "indexes/validation_report.json").relative_to(root)),
        ],
    }


def register_entry(root: Path, entry_file: Path, copy_from_template: bool = False) -> dict[str, Any]:
    ensure_structure(root)
    source = entry_file
    if copy_from_template:
        source = build_lib_root(root) / "templates/build_memory_entry.template.json"
    raw = load_json(source)
    if not isinstance(raw, dict):
        raise ValueError("Entry file must be a JSON object")
    entry = normalize_entry(root, raw)
    errors = validate_entry_shape(root, entry)
    if errors:
        raise ValueError("; ".join(errors))

    target = entry_output_path(root, entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    dump_json(target, entry)
    return {
        "status": "ok",
        "entry_id": entry["entry_id"],
        "path": str(target.relative_to(root)),
        "weighted_total": (entry.get("scores") or {}).get("weighted_total"),
    }


def query_entries(
    root: Path,
    *,
    text: str | None,
    tag: list[str],
    problem_type: str | None,
    scope: str | None,
    project_slug: str | None,
    min_score: float | None,
    status: str | None,
    limit: int,
) -> dict[str, Any]:
    entries, errors = load_entries(root)
    ranked = rank_entries(entries)
    out: list[dict[str, Any]] = []
    needle = (text or "").lower().strip()
    tags = set(tag)

    for e in ranked:
        if scope and e.get("scope") != scope:
            continue
        if project_slug and str(e.get("project_slug")) != project_slug:
            continue
        if status and e.get("status") != status:
            continue
        if problem_type and problem_type not in e.get("problem_types", []):
            continue
        score = (e.get("scores") or {}).get("weighted_total")
        try:
            score_f = float(score or 0.0)
        except Exception:
            score_f = 0.0
        if min_score is not None and score_f < min_score:
            continue
        if tags and not tags.issubset(set(e.get("tags", []))):
            continue
        if needle and needle not in str(e.get("_search_text", "")):
            continue
        out.append(minimal_index_entry(e))
        if len(out) >= limit:
            break

    return {
        "status": "ok",
        "results_count": len(out),
        "validation_errors_count": len(errors),
        "results": out,
    }


def sync_memory_store(root: Path, top_n: int = 20, status_filter: str | None = None) -> dict[str, Any]:
    entries, errors = load_entries(root)
    ranked = rank_entries(entries)
    selected: list[dict[str, Any]] = []
    for e in ranked:
        if status_filter and e.get("status") != status_filter:
            continue
        selected.append(e)
        if len(selected) >= top_n:
            break

    memory_file = root / ".agent/memory/memory.jsonl"
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    if not memory_file.exists():
        memory_file.write_text("", encoding="utf-8")

    existing_source_ids: set[str] = set()
    for line in memory_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        payload = row.get("payload", {})
        if isinstance(payload, dict) and payload.get("source") == "build_memory_library":
            src_id = payload.get("entry_id")
            if isinstance(src_id, str):
                existing_source_ids.add(src_id)

    written = 0
    with memory_file.open("a", encoding="utf-8") as f:
        for e in selected:
            if e["entry_id"] in existing_source_ids:
                continue
            scope = e.get("scope")
            project_slug = e.get("project_slug")
            key_parts = ["build_library", str(scope)]
            if project_slug:
                key_parts.append(str(project_slug))
            key_parts.append(str(e.get("entry_id")))
            row = {
                "id": str(uuid4()),
                "key": ":".join(key_parts),
                "payload": {
                    "source": "build_memory_library",
                    "entry_id": e.get("entry_id"),
                    "title": e.get("title"),
                    "kind": e.get("kind"),
                    "status": e.get("status"),
                    "tags": e.get("tags", []),
                    "problem_types": e.get("problem_types", []),
                    "weighted_total": (e.get("scores") or {}).get("weighted_total"),
                    "project_slug": e.get("project_slug"),
                    "path": e.get("_path"),
                    "synced_at": utc_now_iso(),
                },
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1

    return {
        "status": "ok",
        "selected": len(selected),
        "written": written,
        "skipped_existing": len(selected) - written,
        "validation_errors_count": len(errors),
        "memory_file": str(memory_file.relative_to(root)),
    }


def copy_template(root: Path, out_path: Path) -> dict[str, Any]:
    template = build_lib_root(root) / "templates/build_memory_entry.template.json"
    if not template.exists():
        raise FileNotFoundError(f"Template missing: {template}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out_path)
    return {"status": "ok", "template": str(template.relative_to(root)), "output": str(out_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Antigravity Build Memory Library manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Initialize build memory library directories")

    reg = sub.add_parser("register", help="Register a build memory entry from JSON")
    reg.add_argument("--entry-file", required=True, help="Path to entry JSON")

    sub.add_parser("rebuild-index", help="Rebuild generated indexes and validation report")

    q = sub.add_parser("query", help="Query the build memory library")
    q.add_argument("--text", help="Substring search over normalized fields")
    q.add_argument("--tag", action="append", default=[], help="Required tag (repeatable)")
    q.add_argument("--problem-type", help="Task type filter (e.g. T3)")
    q.add_argument("--scope", choices=["global", "project"], help="Scope filter")
    q.add_argument("--project-slug", help="Project scope slug")
    q.add_argument("--min-score", type=float, help="Minimum weighted_total")
    q.add_argument("--status", choices=["candidate", "validated", "gold", "deprecated"], help="Status filter")
    q.add_argument("--limit", type=int, default=10, help="Max results")

    sync = sub.add_parser("sync-memory-store", help="Sync top build entries into .agent/memory/memory.jsonl")
    sync.add_argument("--top-n", type=int, default=20, help="Number of top entries to sync")
    sync.add_argument("--status", choices=["candidate", "validated", "gold", "deprecated"], help="Status filter before sync")

    tpl = sub.add_parser("copy-template", help="Copy JSON entry template to a target file")
    tpl.add_argument("--out", required=True, help="Output path for the template copy")

    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    try:
        if args.cmd == "init":
            result = ensure_structure(root)
        elif args.cmd == "register":
            result = register_entry(root, Path(args.entry_file))
        elif args.cmd == "rebuild-index":
            result = rebuild_indexes(root)
        elif args.cmd == "query":
            result = query_entries(
                root,
                text=args.text,
                tag=args.tag,
                problem_type=args.problem_type,
                scope=args.scope,
                project_slug=args.project_slug,
                min_score=args.min_score,
                status=args.status,
                limit=max(1, int(args.limit)),
            )
        elif args.cmd == "sync-memory-store":
            result = sync_memory_store(root, top_n=max(1, int(args.top_n)), status_filter=args.status)
        elif args.cmd == "copy-template":
            result = copy_template(root, Path(args.out))
        else:
            raise ValueError(f"Unknown command: {args.cmd}")

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print(f"error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

