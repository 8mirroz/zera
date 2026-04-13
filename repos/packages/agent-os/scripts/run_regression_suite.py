#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASKS_PATH = ROOT / "repos/packages/agent-os/tests/regression_tasks.json"
SWARMCTL = ROOT / "repos/packages/agent-os/scripts/swarmctl.py"


def main() -> int:
    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    results: list[dict] = []

    for task in tasks:
        cmd = [
            sys.executable,
            str(SWARMCTL),
            "route",
            task["text"],
            "--task-type",
            task["task_type"],
            "--complexity",
            task["complexity"],
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
        ok = proc.returncode == 0
        observed_tier = None
        if ok:
            try:
                payload = json.loads(proc.stdout)
                observed_tier = payload.get("model_tier")
            except Exception:
                ok = False
        tier_ok = observed_tier == task["expected_tier"]
        results.append(
            {
                "id": task["id"],
                "ok": ok and tier_ok,
                "expected_tier": task["expected_tier"],
                "observed_tier": observed_tier,
            }
        )

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    report = {
        "passed": passed,
        "total": total,
        "pass_rate": round((passed / total) * 100, 2) if total else 0.0,
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
