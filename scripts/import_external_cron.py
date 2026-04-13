#!/usr/bin/env python3
"""
External Cron Import Script

Imports Zera cron jobs from ~/.hermes/profiles/zera/cron/ into
configs/tooling/background_jobs.yaml where they are governed by the repo.

Usage:
  python3 scripts/import_external_cron.py [--dry-run]

Exit codes:
  0 — Import successful (or dry-run complete)
  1 — Import failed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def _cron_dir() -> Path:
    return Path.home() / ".hermes" / "profiles" / "zera" / "cron"


def _read_cron_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  {YELLOW}⚠️  Failed to parse {path.name}: {e}{NC}")
        return None


def _normalize_cron_job(data: dict[str, Any], source_file: str) -> dict[str, Any] | None:
    """Normalize a cron job into repo-governed background job format."""
    # Handle jobs.json format (array of jobs)
    if "jobs" in data and isinstance(data["jobs"], list):
        jobs = []
        for job in data["jobs"]:
            normalized = _normalize_single_job(job, source_file)
            if normalized:
                jobs.append(normalized)
        return jobs if jobs else None

    # Handle individual cron file format
    return _normalize_single_job(data, source_file)


def _normalize_single_job(data: dict[str, Any], source_file: str) -> dict[str, Any] | None:
    """Normalize a single cron job."""
    name = data.get("name")
    if not name:
        return None

    # Extract schedule
    schedule = data.get("schedule", "")
    if isinstance(schedule, dict):
        if schedule.get("kind") == "interval":
            minutes = schedule.get("minutes", 60)
            schedule = f"*/{minutes} * * * *"
        else:
            schedule = schedule.get("display", "")
    elif isinstance(schedule, str):
        pass  # Already a cron expression

    # Extract command/prompt
    prompt = ""
    if "prompt" in data:
        prompt = data["prompt"]
    elif "args" in data and isinstance(data["args"], list):
        # Find the -q argument
        for i, arg in enumerate(data["args"]):
            if arg == "-q" and i + 1 < len(data["args"]):
                prompt = data["args"][i + 1]
                break

    # Extract model/provider
    model = data.get("model", "")
    provider = data.get("provider", "")

    # Determine job type
    job_type = "zera_task"
    if "self-evolution" in name or "self_evolution" in name:
        job_type = "zera_self_evolution"
    elif "memory" in name:
        job_type = "zera_memory"
    elif "briefing" in name or "digest" in name:
        job_type = "zera_briefing"
    elif "guardian" in name:
        job_type = "zera_guardian"
    elif "reflection" in name:
        job_type = "zera_reflection"
    elif "goal" in name:
        job_type = "zera_goal_review"
    elif "research" in name:
        job_type = "zera_research"

    return {
        "job_id": f"imported_{name}",
        "name": name,
        "type": job_type,
        "schedule": schedule,
        "enabled": bool(data.get("enabled", True)),
        "source": f"external_cron:{source_file}",
        "description": data.get("description", ""),
        "model": model,
        "provider": provider,
        "prompt": prompt,
        "max_turns": data.get("max_turns", 200),
        "imported_at": "2026-04-10",
        "import_status": "pending_review",
    }


def main() -> int:
    cron_dir = _cron_dir()
    if not cron_dir.exists():
        print(f"{RED}❌ Cron directory not found: {cron_dir}{NC}")
        return 1

    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}External Cron Import{NC}")
    print(f"{YELLOW}{'='*60}{NC}\n")

    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print(f"{YELLOW}🔍 DRY RUN — no changes will be made{NC}\n")

    all_jobs = []
    files_processed = 0

    # Process all JSON files in cron directory
    for cron_file in sorted(cron_dir.glob("*.json")):
        if cron_file.name == "jobs.json":
            # Special handling for jobs.json
            data = _read_cron_file(cron_file)
            if data is None:
                continue
            files_processed += 1
            result = _normalize_cron_job(data, cron_file.name)
            if result:
                if isinstance(result, list):
                    all_jobs.extend(result)
                else:
                    all_jobs.append(result)
        else:
            # Individual cron file
            data = _read_cron_file(cron_file)
            if data is None:
                continue
            files_processed += 1
            job = _normalize_single_job(data, cron_file.name)
            if job:
                all_jobs.append(job)

    print(f"Files processed: {files_processed}")
    print(f"Jobs found: {len(all_jobs)}\n")

    for job in all_jobs:
        status_icon = GREEN + "✅" + NC if job.get("enabled") else YELLOW + "⏸️" + NC
        print(f"  {status_icon} {job['name']}")
        print(f"      Schedule: {job['schedule']}")
        print(f"      Type: {job['type']}")
        print(f"      Model: {job.get('model', 'default')}")
        print(f"      Source: {job['source']}")
        print(f"      Status: {job['import_status']}")
        print()

    if not dry_run and all_jobs:
        # Write imported jobs to repo-governed background jobs config
        import os
        repo_root = Path(__file__).resolve().parents[1]
        bg_jobs_path = repo_root / "configs" / "tooling" / "imported_background_jobs.json"
        
        # Read existing imported jobs
        existing_jobs = []
        if bg_jobs_path.exists():
            try:
                existing_jobs = json.loads(bg_jobs_path.read_text(encoding="utf-8"))
                if not isinstance(existing_jobs, list):
                    existing_jobs = []
            except Exception:
                existing_jobs = []

        # Merge: update existing, add new
        existing_by_id = {j.get("job_id"): j for j in existing_jobs}
        for job in all_jobs:
            existing_by_id[job["job_id"]] = job
        
        merged = list(existing_by_id.values())
        
        if not dry_run:
            bg_jobs_path.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"{GREEN}✅ Imported {len(all_jobs)} jobs to {bg_jobs_path}{NC}")
            print(f"   Total governed jobs: {len(merged)}")

    print(f"\n{'='*60}")
    if all_jobs:
        print(f"{GREEN}✅ Cron import complete — {len(all_jobs)} jobs now under repo governance{NC}")
    else:
        print(f"{YELLOW}⚠️  No cron jobs found to import{NC}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
