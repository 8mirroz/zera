from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


class TestTraceSchemaMirror(unittest.TestCase):
    def test_agent_os_trace_schema_mirrors_canonical(self) -> None:
        canonical_path = ROOT / "configs/tooling/trace_schema.json"
        mirror_path = ROOT / "configs/tooling/agent_os_trace_schema.json"

        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        mirror = json.loads(mirror_path.read_text(encoding="utf-8"))

        self.assertEqual(mirror.get("schema_id"), canonical.get("schema_id"))
        self.assertEqual(mirror.get("required_common_fields"), canonical.get("required_common_fields"))
        self.assertEqual(mirror.get("field_types"), canonical.get("field_types"))
        self.assertEqual(mirror.get("event_types"), canonical.get("event_types"))


if __name__ == "__main__":
    unittest.main()
