#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from . import build_memory_library
from . import repo_memory_catalog


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso_to_dt(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _freshness_check(root: Path, max_age_hours: int = 72) -> dict[str, Any]:
    now = utc_now()
    checks = [
        root / ".agent/memory/build-library/indexes/global_index.json",
        root / ".agent/memory/build-library/indexes/projects_index.json",
        root / ".agent/memory/build-library/indexes/best_library_snapshot.json",
        root / ".agent/memory/build-library/indexes/validation_report.json",
        root / ".agent/memory/repos-catalog/indexes/repos_index.json",
        root / ".agent/memory/repos-catalog/indexes/aliases_index.json",
        root / ".agent/memory/repos-catalog/indexes/navigation_shortcuts.json",
        root / ".agent/memory/repos-catalog/indexes/validation_report.json",
    ]

    findings: list[dict[str, Any]] = []
    indexes_used: list[str] = []
    severity = "ok"

    for path in checks:
        rel = str(path.relative_to(root))
        if not path.exists():
            findings.append({"severity": "warn", "code": "INDEX_MISSING", "path": rel})
            severity = "warn" if severity == "ok" else severity
            continue
        indexes_used.append(rel)
        try:
            data = _load_json(path)
        except Exception as e:
            findings.append({"severity": "error", "code": "INDEX_INVALID_JSON", "path": rel, "error": str(e)})
            severity = "error"
            continue
        generated_at = _iso_to_dt(data.get("generated_at"))
        if not generated_at:
            findings.append({"severity": "warn", "code": "INDEX_MISSING_GENERATED_AT", "path": rel})
            severity = "warn" if severity == "ok" else severity
            continue
        age_hours = round((now - generated_at).total_seconds() / 3600, 2)
        if age_hours > max_age_hours:
            findings.append(
                {
                    "severity": "warn",
                    "code": "INDEX_STALE",
                    "path": rel,
                    "age_hours": age_hours,
                    "max_age_hours": max_age_hours,
                }
            )
            severity = "warn" if severity == "ok" else severity

    return {
        "severity": severity,
        "checked": len(checks),
        "indexes_used": indexes_used,
        "findings": findings,
        "checked_at": now.isoformat(),
        "max_age_hours": max_age_hours,
    }


def _docs_fallback_query(root: Path, text: str, limit: int) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    needle = text.lower().strip()
    candidates: list[Path] = []
    for base in (root / "docs/patterns", root / "docs/ki"):
        if base.exists():
            candidates.extend(sorted(base.glob("*.md")))

    results: list[dict[str, Any]] = []
    for path in candidates:
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        low = body.lower()
        idx = low.find(needle)
        if idx < 0:
            continue
        start = max(0, idx - 80)
        end = min(len(body), idx + len(needle) + 160)
        snippet = body[start:end].replace("\n", " ").strip()
        results.append(
            {
                "type": "docs_fallback",
                "path": str(path.relative_to(root)),
                "snippet": snippet,
            }
        )
        if len(results) >= limit:
            break
    return results


def query_memory_layers(
    root: Path,
    *,
    scope: str,
    task_type: str | None,
    complexity: str | None,
    text: str | None,
    tags: list[str],
    project_slug: str | None,
    limit: int,
    min_score: float | None,
    freshness_max_age_hours: int,
) -> dict[str, Any]:
    freshness = _freshness_check(root, max_age_hours=freshness_max_age_hours)
    indexes_used = list(freshness.get("indexes_used", []))

    search_text = (text or "").strip()
    problem_type = task_type
    if complexity and search_text:
        search_text = f"{search_text} {complexity}"

    checks_order: list[dict[str, Any]] = []

    if scope in {"auto", "project"} and project_slug:
        checks_order.append({"source": "build_library_project", "scope": "project", "project_slug": project_slug})
    if scope in {"auto", "global", "project"}:
        checks_order.append({"source": "build_library_global", "scope": "global", "project_slug": None})
    if scope == "auto":
        checks_order.append({"source": "repo_catalog", "scope": None, "project_slug": None})
        checks_order.append({"source": "docs_patterns", "scope": None, "project_slug": None})

    chosen_source = "none"
    entries: list[dict[str, Any]] = []
    fallback_used = False
    sources_checked: list[str] = []

    for idx, item in enumerate(checks_order):
        source = item["source"]
        sources_checked.append(source)
        if source.startswith("build_library"):
            q = build_memory_library.query_entries(
                root,
                text=search_text or None,
                tag=tags,
                problem_type=problem_type,
                scope=item["scope"],
                project_slug=item["project_slug"],
                min_score=min_score,
                status=None,
                limit=limit,
            )
            raw_results = list(q.get("results", []))
            entries = [
                {
                    "type": "build_memory",
                    "source": source,
                    **row,
                }
                for row in raw_results
            ]
        elif source == "repo_catalog":
            q = repo_memory_catalog.query(
                root,
                text=search_text or (task_type or ""),
                domain=None,
                tag=tags[0] if tags else None,
                min_score=None if min_score is None else int(min_score * 100),
                limit=limit,
            )
            raw_results = list(q.get("results", []))
            entries = [
                {
                    "type": "repo_catalog",
                    "source": source,
                    **row,
                }
                for row in raw_results
            ]
        elif source == "docs_patterns":
            entries = _docs_fallback_query(root, search_text or (task_type or ""), limit)
        else:
            entries = []

        if entries:
            chosen_source = source
            fallback_used = idx > 0
            break

    return {
        "status": "ok",
        "request": {
            "scope": scope,
            "task_type": task_type,
            "complexity": complexity,
            "text": text,
            "tags": tags,
            "project_slug": project_slug,
            "limit": limit,
            "min_score": min_score,
        },
        "entries": entries[:limit],
        "source": chosen_source,
        "sources_checked": sources_checked,
        "fallback_used": fallback_used,
        "freshness": freshness,
        "indexes_used": indexes_used,
    }


def _guess_row_timestamp(row: dict[str, Any]) -> datetime | None:
    candidates: list[str | None] = [row.get("created_at")]
    payload = row.get("payload")
    if isinstance(payload, dict):
        for key in ("synced_at", "updated_at", "captured_at"):
            candidates.append(payload.get(key))
        prov = payload.get("provenance")
        if isinstance(prov, dict):
            candidates.append(prov.get("captured_at"))
    for raw in candidates:
        dt = _iso_to_dt(raw if isinstance(raw, str) else None)
        if dt:
            return dt
    return None


def compact_runtime_memory(
    root: Path,
    *,
    ttl_days: int,
    max_rows: int | None,
    apply: bool,
    all_sources: bool,
) -> dict[str, Any]:
    memory_file = root / ".agent/memory/memory.jsonl"
    if not memory_file.exists():
        return {"status": "ok", "memory_file": str(memory_file.relative_to(root)), "changed": False, "reason": "missing_file"}

    now = utc_now()
    ttl_cutoff = now - timedelta(days=max(0, ttl_days))
    managed_sources = {"repo_memory_catalog", "build_memory_library"}

    parsed_rows: list[dict[str, Any]] = []
    invalid_lines = 0
    for idx, line in enumerate(memory_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            invalid_lines += 1
            continue
        if not isinstance(row, dict):
            invalid_lines += 1
            continue
        row["_line_index"] = idx
        row["_ts"] = _guess_row_timestamp(row)
        payload = row.get("payload")
        row["_source"] = payload.get("source") if isinstance(payload, dict) else None
        parsed_rows.append(row)

    before_count = len(parsed_rows)
    ttl_dropped = 0

    filtered: list[dict[str, Any]] = []
    for row in parsed_rows:
        source = row.get("_source")
        ts = row.get("_ts")
        ttl_applies = all_sources or (isinstance(source, str) and source in managed_sources)
        if ttl_applies and isinstance(ts, datetime) and ts < ttl_cutoff:
            ttl_dropped += 1
            continue
        filtered.append(row)

    # Dedupe by key, keep most recent/last occurrence.
    by_key: dict[str, dict[str, Any]] = {}
    non_keyed: list[dict[str, Any]] = []
    dedupe_dropped = 0
    for row in filtered:
        key = row.get("key")
        if not isinstance(key, str) or not key:
            non_keyed.append(row)
            continue
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = row
            continue
        prev_ts = prev.get("_ts")
        cur_ts = row.get("_ts")
        prev_idx = int(prev.get("_line_index", 0))
        cur_idx = int(row.get("_line_index", 0))
        take_new = False
        if isinstance(cur_ts, datetime) and isinstance(prev_ts, datetime):
            take_new = cur_ts >= prev_ts
        elif isinstance(cur_ts, datetime) and prev_ts is None:
            take_new = True
        elif cur_ts is None and prev_ts is None:
            take_new = cur_idx >= prev_idx
        else:
            take_new = cur_idx >= prev_idx
        if take_new:
            dedupe_dropped += 1
            by_key[key] = row
        else:
            dedupe_dropped += 1

    compacted = list(by_key.values()) + non_keyed

    max_rows_dropped = 0
    if max_rows is not None and max_rows > 0 and len(compacted) > max_rows:
        ranked = sorted(
            compacted,
            key=lambda r: (
                r.get("_ts") or datetime.min.replace(tzinfo=timezone.utc),
                int(r.get("_line_index", 0)),
            ),
            reverse=True,
        )
        keep = ranked[:max_rows]
        max_rows_dropped = len(compacted) - len(keep)
        compacted = sorted(keep, key=lambda r: int(r.get("_line_index", 0)))

    after_count = len(compacted)
    changed = (after_count != before_count) or invalid_lines > 0

    result = {
        "status": "ok",
        "memory_file": str(memory_file.relative_to(root)),
        "changed": changed,
        "applied": bool(apply),
        "before_count": before_count,
        "after_count": after_count,
        "invalid_lines_skipped": invalid_lines,
        "ttl_days": ttl_days,
        "ttl_dropped": ttl_dropped,
        "dedupe_dropped": dedupe_dropped,
        "max_rows": max_rows,
        "max_rows_dropped": max_rows_dropped,
        "all_sources": all_sources,
    }

    if apply and changed:
        lines: list[str] = []
        for row in compacted:
            row_out = {k: v for k, v in row.items() if not k.startswith("_")}
            if "id" not in row_out:
                row_out["id"] = str(uuid4())
            lines.append(json.dumps(row_out, ensure_ascii=False))
        memory_file.write_text(("\n".join(lines) + ("\n" if lines else "")), encoding="utf-8")

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified memory query adapter + freshness validator for Antigravity")
    p.add_argument("--json", action="store_true", help="JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="Query memory layers with deterministic fallback")
    q.add_argument("--scope", choices=["auto", "project", "global"], default="auto")
    q.add_argument("--task-type", dest="task_type")
    q.add_argument("--complexity")
    q.add_argument("--text")
    q.add_argument("--tag", action="append", default=[])
    q.add_argument("--project-slug")
    q.add_argument("--limit", type=int, default=10)
    q.add_argument("--min-score", type=float)
    q.add_argument("--freshness-max-age-hours", type=int, default=72)

    f = sub.add_parser("freshness-check", help="Validate memory index freshness/consistency")
    f.add_argument("--max-age-hours", type=int, default=72)

    c = sub.add_parser("compact-runtime", help="Compact .agent/memory/memory.jsonl with TTL/dedupe")
    c.add_argument("--ttl-days", type=int, default=30)
    c.add_argument("--max-rows", type=int, default=5000)
    c.add_argument("--all-sources", action="store_true", help="Apply TTL to all sources, not only managed derived sources")
    c.add_argument("--apply", action="store_true", help="Write changes back to memory.jsonl (default is dry-run)")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()

    try:
        if args.cmd == "query":
            result = query_memory_layers(
                root,
                scope=args.scope,
                task_type=args.task_type,
                complexity=args.complexity,
                text=args.text,
                tags=list(args.tag or []),
                project_slug=args.project_slug,
                limit=max(1, int(args.limit)),
                min_score=args.min_score,
                freshness_max_age_hours=max(1, int(args.freshness_max_age_hours)),
            )
        elif args.cmd == "freshness-check":
            result = _freshness_check(root, max_age_hours=max(1, int(args.max_age_hours)))
        elif args.cmd == "compact-runtime":
            result = compact_runtime_memory(
                root,
                ttl_days=max(0, int(args.ttl_days)),
                max_rows=None if args.max_rows is None else max(1, int(args.max_rows)),
                apply=bool(args.apply),
                all_sources=bool(args.all_sources),
            )
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
