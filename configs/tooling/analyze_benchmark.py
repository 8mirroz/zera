#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


def analyze_benchmark(report_path: str | Path) -> dict:
    path = Path(report_path)
    if not path.exists():
        return {
            "status": "failed",
            "reason": "benchmark_report_missing",
            "path": str(path),
        }

    payload = json.loads(path.read_text())
    return {
        "status": "ok",
        "summary": payload.get("summary", {}),
        "metrics": payload.get("metrics", {}),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "failed",
            "reason": "missing_report_path"
        }))
        return 2

    print(json.dumps(analyze_benchmark(sys.argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
