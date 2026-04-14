#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.build_memory_library import repo_root, utc_now_iso, register_entry, rebuild_indexes, sync_memory_store, dump_json, load_entries
from agent_os.trace_metrics_materializer import _normalize_trace_rows, SUCCESS_STATUSES

def _fingerprint(run_id: str, task_type: str, complexity: str, model: str | None) -> str:
    base = "|".join([run_id, task_type, complexity, model or ""])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def _existing_fingerprints(root: Path) -> set[str]:
    entries, _ = load_entries(root)
    existing: set[str] = set()
    for e in entries:
        prov = e.get("provenance") or {}
        fp = prov.get("fingerprint")
        if isinstance(fp, str) and fp:
            existing.add(fp)
    return existing

def extract_candidates(trace_file: Path, allow_legacy: bool, require_retro: bool = False, target_run_id: str | None = None) -> list[dict[str, Any]]:
    events, norm = _normalize_trace_rows(trace_file, allow_legacy=allow_legacy)
    
    runs: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        rid = ev.get("run_id")
        if not rid:
            continue
        if target_run_id and rid != target_run_id:
            continue
        if rid not in runs:
            runs[rid] = []
        runs[rid].append(ev)
        
    candidates = []
    
    for rid, run_events in runs.items():
        task_summary = next((e for e in run_events if e.get("event_type") == "task_run_summary"), None)
        if not task_summary:
            continue
        
        status = str(task_summary.get("status") or "").lower()
        if status not in SUCCESS_STATUSES:
            continue
            
        route_decision = next((e for e in run_events if e.get("event_type") == "route_decision"), None)
        if not route_decision:
            continue
            
        if require_retro:
            retro = next((e for e in run_events if e.get("event_type") == "retro_written"), None)
            if not retro:
                continue
                
        task_type = task_summary.get("task_type") or "unknown_task"
        complexity = task_summary.get("complexity") or "C1"
        data = task_summary.get("data") or {}
        
        route_data = route_decision.get("data") or {}
        model = route_data.get("model") or route_decision.get("model")
        
        title = f"Auto-ingested memory for run {rid[:8]}"
        summary = f"Task type: {task_type}, Complexity: {complexity}. Generated automatically from trace."
        fingerprint = _fingerprint(rid, str(task_type), str(complexity), str(model) if model else None)
        
        entry = {
            "entry_id": f"auto-{rid}",
            "scope": "global",
            "kind": "build",
            "title": title,
            "summary": summary,
            "status": "candidate",
            "tags": ["auto-ingested", task_type],
            "problem_types": [task_type],
            "models": [model] if model else [],
            "settings": {},
            "algorithm": {},
            "evidence": {
                "run_id": rid,
                "complexity": complexity,
                "duration_seconds": data.get("duration_seconds")
            },
            "scores": {
                "weighted_total": 0.5,
                "confidence": 0.5
            },
            "provenance": {
                "source": "auto_ingest",
                "captured_at": utc_now_iso(),
                "fingerprint": fingerprint,
            },
            "trace_refs": [rid]
        }
        
        candidates.append(entry)
        
    return candidates


def main(args_list: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-ingest build memory candidates from traces")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    p_preview = sub.add_parser("preview", help="Preview generated JSON")
    p_preview.add_argument("--run-id", required=True, help="Target run ID")
    
    p_export = sub.add_parser("export-entry", help="Export matching entry to JSON file")
    p_export.add_argument("--run-id", required=True, help="Target run ID")
    p_export.add_argument("--out", required=True, help="Output JSON path")
    
    p_reg = sub.add_parser("register", help="Register entry directly via build_memory_library")
    p_reg.add_argument("--run-id", required=True, help="Target run ID")
    p_reg.add_argument("--rebuild-index", action="store_true", help="Rebuild indexes after register")
    p_reg.add_argument("--sync-memory", action="store_true", help="Sync memory store after register")
    p_reg.add_argument("--allow-duplicate", action="store_true", help="Allow duplicate auto-ingest entries")
    
    for p in [p_preview, p_export, p_reg]:
        p.add_argument("--file", "--trace-file", dest="trace_file", help="Path to trace file")
        p.add_argument("--repo-root", help="Override repo root (for temp fixtures)")
        p.add_argument("--allow-legacy", action="store_true", help="Allow legacy traces")
        p.add_argument("--require-retro", action="store_true", help="Require retro_written event")
        
    args = parser.parse_args(args_list)
    root = Path(args.repo_root) if args.repo_root else repo_root()
    trace_file = Path(args.trace_file) if args.trace_file else Path(os.getenv("AGENT_OS_TRACE_FILE", str(root / "logs/agent_traces.jsonl")))
    
    if not trace_file.is_absolute():
        trace_file = root / trace_file
        
    if not trace_file.exists():
        print(f"Error: Trace file not found at {trace_file}")
        return 1
        
    candidates = extract_candidates(trace_file, args.allow_legacy, args.require_retro, args.run_id)
    
    if not candidates:
        print(f"No eligible candidates found for run_id {args.run_id}")
        return 1
        
    candidate = candidates[0]
    
    if args.cmd == "preview":
        print(json.dumps(candidate, ensure_ascii=False, indent=2))
        return 0
        
    elif args.cmd == "export-entry":
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Exported to {out_path}")
        return 0
        
    elif args.cmd == "register":
        if not args.allow_duplicate:
            existing_fps = _existing_fingerprints(root)
            cand_fp = (candidate.get("provenance") or {}).get("fingerprint")
            if isinstance(cand_fp, str) and cand_fp in existing_fps:
                print(f"Duplicate candidate detected for run_id {args.run_id}; skipping register")
                return 0
            existing_path = root / ".agent/memory/build-library/global/entries" / f"{candidate['entry_id']}.json"
            if existing_path.exists():
                print(f"Entry already exists at {existing_path}; skipping register")
                return 0
        out_path = root / f".tmp_auto_ingest_{args.run_id}.json"
        dump_json(out_path, candidate)
        
        try:
            res = register_entry(root, out_path)
            print(f"Registered entry: {res.get('entry_id')} at {res.get('path')}")
            
            if args.rebuild_index:
                idx_res = rebuild_indexes(root)
                print(f"Rebuilt index. Status: {idx_res.get('status')}")
                
            if args.sync_memory:
                sync_res = sync_memory_store(root)
                print(f"Synced memory store. Written: {sync_res.get('written')}")
                
        except Exception as e:
            print(f"Error registering entry: {e}")
            return 1
        finally:
            if out_path.exists():
                out_path.unlink()
                
        return 0

if __name__ == "__main__":
    sys.exit(main())
