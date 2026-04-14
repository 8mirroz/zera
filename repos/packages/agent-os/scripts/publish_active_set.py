#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.active_set_lib import publish_active_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish ACTIVE_SKILLS.md into .agent/skills/")
    parser.add_argument("--repo-root", default=None, help="Path to repo root (defaults to auto-detect)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[4]
    active_md = repo_root / "configs/skills/ACTIVE_SKILLS.md"
    dest_dir = repo_root / ".agent/skills"

    publish_active_set(repo_root=repo_root, active_md=active_md, dest_dir=dest_dir)
    print(f"Published active skills to: {dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
