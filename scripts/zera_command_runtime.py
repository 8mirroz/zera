#!/usr/bin/env python3
from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    current_root = _repo_root()
    target_root = Path(os.getenv("ZERA_REPO_ROOT", "/Users/user/zera")).expanduser().resolve()
    local_impl = current_root / "scripts" / "zera" / "zera_command_runtime.py"
    target_impl = target_root / "scripts" / "zera" / "zera_command_runtime.py"

    if target_root != current_root and target_impl.exists():
        env = dict(os.environ)
        env.setdefault("ZERA_REPO_ROOT", str(target_root))
        env.setdefault("AGENT_OS_REPO_ROOT", str(target_root))
        proc = subprocess.run([sys.executable, str(target_impl), *sys.argv[1:]], env=env, check=False)
        return int(proc.returncode)

    if not local_impl.exists():
        print(f"Missing runtime bridge: {local_impl}", file=sys.stderr)
        return 2

    sys.argv = [str(local_impl), *sys.argv[1:]]
    runpy.run_path(str(local_impl), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
