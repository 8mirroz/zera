#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


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
        lib / "indexes/project_indexes",
        lib / "templates",
        lib / "schemas",
        lib / "audit/dedupe_reports",
        lib / "audit/stale_reports",
        lib / "audit/validation_reports",
        lib / "snapshots/gold",
        lib / "snapshots/validated",
        lib / "snapshots/planner_packs",
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
    lib = build_lib_root(root)
    schema_path = lib / "schemas/entry.schema.json"
    if not schema_path.exists():
        return ["missing entry.schema.json in build-library/schemas/"]

    errors: list[str] = []
    try:
        schema = load_json(schema_path)
        if HAS_JSONSCHEMA:
            from jsonschema import validate, ValidationError
            try:
                validate(instance=entry, schema=schema)
            except ValidationError as ve:
                errors.append(f"schema violation: {ve.message}")
        else:
            # Fallback simple validation
            required = schema.get("required", [])
            for field in required:
                if field not in entry:
                    errors.append(f"missing required field: {field}")
    except Exception as e:
        errors.append(f"validation system error: {str(e)}")

    if entry.get("scope") == "project" and not entry.get("project_slug"):
        errors.append("project scope requires project_slug")
    if entry.get("scope") == "global" and entry.get("project_slug") not in (None, "", "null"):
        errors.append("global scope must not define project_slug")

    return errors


def normalize_entry(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    out.setdefault("id", f"bml-candidate-{str(uuid4())[:8]}")
    out.setdefault("version", 1)
    out.setdefault("scope", "global")
    out.setdefault("status", "candidate")
    out.setdefault("entry_type", "build_combination")
    out.setdefault("title", "Untitled Entry")
    out.setdefault("summary", "")
    out.setdefault("problem_class", [])
    out.setdefault("components", [])
    out.setdefault("configuration", {})
    out.setdefault("algorithm", {"inputs": [], "steps": [], "fallbacks": []})
    out.setdefault("evidence", {"trace_refs": [], "ki_refs": [], "metrics": {}})
    out.setdefault("scoring", {
        "overall_score": 0.0,
        "confidence": 0.0,
        "evidence_strength": 0.0,
        "reusability": 0.0,
        "determinism": 0.0
    })
    out.setdefault("constraints", [])
    out.setdefault("failure_modes", [])
    out.setdefault("when_to_use", [])
    out.setdefault("when_not_to_use", [])
    out.setdefault("tags", [])
    out.setdefault("owner_agent", "unknown-harvester")
    out.setdefault("created_at", utc_now_iso())
    out.setdefault("updated_at", utc_now_iso())

    # Auto-calc overall_score if dimensions present
    s = out["scoring"]
    if s.get("overall_score") in (None, 0.0):
        # Default Weights V2.0
        s["overall_score"] = round(
            0.20 * s.get("confidence", 0) +
            0.18 * s.get("evidence_strength", 0) +
            0.16 * s.get("determinism", 0) +
            0.14 * s.get("reusability", 0),
            4
        )

    search_chunks: list[str] = [
        str(out.get("title")),
        str(out.get("summary")),
        " ".join(out.get("tags", [])),
        " ".join(out.get("problem_class", []))
    ]
    out["_search_text"] = " ".join(search_chunks).lower()

    return out


def entry_output_path(root: Path, entry: dict[str, Any]) -> Path:
    lib = build_lib_root(root)
    scope = entry["scope"]
    if scope == "global":
        return lib / "global/entries" / f"{entry['id']}.json"
    project_slug = str(entry.get("project_slug", "unknown"))
    return lib / "projects" / project_slug / "entries" / f"{entry['id']}.json"


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
        "id": entry.get("id"),
        "scope": entry.get("scope"),
        "project_slug": entry.get("project_slug"),
        "entry_type": entry.get("entry_type"),
        "status": entry.get("status"),
        "title": entry.get("title"),
        "tags": entry.get("tags", []),
        "problem_class": entry.get("problem_class", []),
        "score": (entry.get("scoring") or {}).get("overall_score"),
        "updated_at": entry.get("updated_at"),
        "path": entry.get("_path"),
    }


def rebuild_indexes(root: Path) -> dict[str, Any]:
    ensure_structure(root)
    entries, errors = load_entries(root)

    global_entries = [e for e in entries if e.get("scope") == "global"]
    project_entries = [e for e in entries if e.get("scope") == "project"]

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_problem_class: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for e in entries:
        min_e = minimal_index_entry(e)
        by_type[str(e.get("entry_type"))].append(min_e)
        for tag in e.get("tags", []):
            by_tag[str(tag)].append(min_e)
        for pc in e.get("problem_class", []):
            by_problem_class[str(pc)].append(min_e)

    global_ranked = rank_entries(global_entries)
    project_ranked = rank_entries(project_entries)

    projects_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in project_entries:
        projects_map[str(e.get("project_slug"))].append(minimal_index_entry(e))

    lib = build_lib_root(root)
    
    # Global Index
    dump_json(lib / "indexes/global_index.json", {
        "generated_at": utc_now_iso(),
        "entries_count": len(global_entries),
        "top_ranked": [minimal_index_entry(e) for e in global_ranked[:20]],
        "entries": [minimal_index_entry(e) for e in global_entries],
    })

    # Specialty Indexes
    dump_json(lib / "indexes/tag_index.json", {"generated_at": utc_now_iso(), "tags": dict(by_tag)})
    dump_json(lib / "indexes/capability_index.json", {"generated_at": utc_now_iso(), "types": dict(by_type)})
    dump_json(lib / "indexes/problem_class_index.json", {"generated_at": utc_now_iso(), "classes": dict(by_problem_class)})

    # Project Index Suite
    for slug, proj_entries in projects_map.items():
        dump_json(lib / "indexes/project_indexes" / f"{slug}.json", {
            "project_slug": slug,
            "generated_at": utc_now_iso(),
            "entries_count": len(proj_entries),
            "entries": proj_entries
        })

    # Standard Top Snapshots
    dump_json(lib / "snapshots/gold/global_top.json", {
        "generated_at": utc_now_iso(),
        "entries": [minimal_index_entry(e) for e in global_ranked if e.get("status") == "gold"][:10]
    })

    validation_report = {
        "generated_at": utc_now_iso(),
        "ok_count": len(entries),
        "error_count": len(errors),
        "errors": errors,
    }
    dump_json(lib / "audit/validation_reports/last_run.json", validation_report)

    return {
        "status": "ok",
        "entries_total": len(entries),
        "errors_total": len(errors),
        "reports": [str((lib / "audit/validation_reports/last_run.json").relative_to(root))]
    }


def register_entry(root: Path, entry_file: Path) -> dict[str, Any]:
    ensure_structure(root)
    raw = load_json(entry_file)
    entry = normalize_entry(root, raw)
    errors = validate_entry_shape(root, entry)
    if errors:
        raise ValueError(f"Entry validation failed: {'; '.join(errors)}")

    target = entry_output_path(root, entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    dump_json(target, entry)
    return {
        "status": "ok",
        "id": entry["id"],
        "path": str(target.relative_to(root)),
        "score": entry["scoring"]["overall_score"],
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

    existing_ids: set[str] = set()
    for line in memory_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            p = row.get("payload", {})
            if p.get("source") == "build_memory_library":
                existing_ids.add(str(p.get("id")))
        except: continue

    written = 0
    with memory_file.open("a", encoding="utf-8") as f:
        for e in selected:
            if e["id"] in existing_ids:
                continue
            row = {
                "id": str(uuid4()),
                "key": f"bml:{e['scope']}:{e['id']}",
                "payload": {
                    "source": "build_memory_library",
                    "id": e["id"],
                    "title": e["title"],
                    "type": e["entry_type"],
                    "status": e["status"],
                    "score": e["scoring"]["overall_score"],
                    "path": e["_path"],
                    "synced_at": utc_now_iso(),
                },
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1

    return {"status": "ok", "synced": written, "total_selected": len(selected)}


def parse_args() -> argparse.Namespace:
    import argparse
    parser = argparse.ArgumentParser(description="Build Memory v2 Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("rebuild-index")

    reg = sub.add_parser("register")
    reg.add_argument("--entry-file", required=True)

    val = sub.add_parser("validate-entry")
    val.add_argument("--path", required=True)

    q = sub.add_parser("query")
    q.add_argument("--text")
    q.add_argument("--scope")
    q.add_argument("--limit", type=int, default=10)

    sync = sub.add_parser("sync")
    sync.add_argument("--top-n", type=int, default=20)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    try:
        if args.cmd == "init":
            result = ensure_structure(root)
        elif args.cmd == "register":
            result = register_entry(root, Path(args.entry_file))
        elif args.cmd == "validate-entry":
            raw = load_json(Path(args.path))
            entry = normalize_entry(root, raw)
            errors = validate_entry_shape(root, entry)
            result = {"status": "ok" if not errors else "error", "errors": errors}
        elif args.cmd == "rebuild-index":
            result = rebuild_indexes(root)
        elif args.cmd == "query":
            result = query_entries(root, text=args.text, scope=args.scope, limit=args.limit, tag=[], problem_type=None, project_slug=None, min_score=None, status=None)
        elif args.cmd == "sync":
            result = sync_memory_store(root, top_n=args.top_n)
        else:
            raise ValueError(f"Unknown command: {args.cmd}")

        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

