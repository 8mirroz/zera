#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from agent_os.skill_drift_validator import main

if __name__ == "__main__":
    raise SystemExit(main())
