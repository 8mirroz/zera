from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import memory_query_adapter as memory_adapter


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class TestMemoryQueryAdapter(unittest.TestCase):
    def _seed_fresh_indexes(self, root: Path) -> None:
        ts = datetime.now(tz=timezone.utc).isoformat()
        for rel in (
            ".agents/memory/build-library/indexes/global_index.json",
            ".agents/memory/build-library/indexes/projects_index.json",
            ".agents/memory/build-library/indexes/best_library_snapshot.json",
            ".agents/memory/build-library/indexes/validation_report.json",
            ".agents/memory/repos-catalog/indexes/repos_index.json",
            ".agents/memory/repos-catalog/indexes/aliases_index.json",
            ".agents/memory/repos-catalog/indexes/navigation_shortcuts.json",
            ".agents/memory/repos-catalog/indexes/validation_report.json",
        ):
            _write_json(root / rel, {"generated_at": ts})

    def test_query_memory_layers_uses_deterministic_fallback_order(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_fresh_indexes(root)

            with patch.object(memory_adapter.build_memory_library, "query_entries", return_value={"results": []}) as build_q:
                with patch.object(
                    memory_adapter.repo_memory_catalog,
                    "query",
                    return_value={"results": [{"repo": "repos/packages/design-system", "score": 93}]},
                ) as repo_q:
                    out = memory_adapter.query_memory_layers(
                        root,
                        scope="auto",
                        task_type="T6",
                        complexity="C3",
                        text="token drift",
                        tags=[],
                        project_slug="design-system",
                        limit=5,
                        min_score=None,
                        freshness_max_age_hours=72,
                    )

            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["source"], "repo_catalog")
            self.assertTrue(out["fallback_used"])
            self.assertEqual(
                out["sources_checked"][:3],
                ["build_library_project", "build_library_global", "repo_catalog"],
            )
            self.assertEqual(build_q.call_count, 2)
            repo_q.assert_called_once()
            self.assertEqual(out["entries"][0]["type"], "repo_catalog")

    def test_compact_runtime_memory_applies_ttl_for_managed_sources_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            memory_file = root / ".agents/memory/memory.jsonl"
            memory_file.parent.mkdir(parents=True, exist_ok=True)

            now = datetime.now(tz=timezone.utc)
            recent = now.isoformat()
            old = (now - timedelta(days=90)).isoformat()
            rows = [
                {
                    "id": "1",
                    "key": "dup:key",
                    "created_at": old,
                    "payload": {"source": "build_memory_library", "value": "old-dup"},
                },
                {
                    "id": "2",
                    "key": "dup:key",
                    "created_at": recent,
                    "payload": {"source": "build_memory_library", "value": "new-dup"},
                },
                {
                    "id": "3",
                    "key": "stale:derived",
                    "created_at": old,
                    "payload": {"source": "repo_memory_catalog", "value": "drop-me"},
                },
                {
                    "id": "4",
                    "key": "stale:manual",
                    "created_at": old,
                    "payload": {"source": "manual_note", "value": "keep-me"},
                },
            ]
            memory_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

            out = memory_adapter.compact_runtime_memory(
                root,
                ttl_days=30,
                max_rows=5000,
                apply=False,
                all_sources=False,
            )

            self.assertEqual(out["status"], "ok")
            self.assertTrue(out["changed"])
            self.assertEqual(out["before_count"], 4)
            self.assertEqual(out["after_count"], 2)
            self.assertEqual(out["ttl_dropped"], 2)
            self.assertEqual(out["dedupe_dropped"], 0)
            self.assertFalse(out["applied"])

            # apply=False should not mutate file
            persisted = [json.loads(line) for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(persisted), 4)


if __name__ == "__main__":
    unittest.main()
