from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.zera_command_os import ZeraCommandOS


class TestZeraBranchMergeAndGovernor(unittest.TestCase):
    def test_branch_merge_requires_candidate_classification(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        manifest = runtime.create_branch_manifest(
            command_id="zera:evolve-capability",
            client_id="repo_native",
            branch_type="research_branch",
            objective="Test merge",
            run_id="run-merge-1",
        )
        with self.assertRaisesRegex(ValueError, "candidate classification"):
            runtime.create_branch_merge_record(
                manifest=manifest,
                candidate_classification="",
                summary="missing classification",
            )

    def test_branch_merge_blocks_stable_memory_and_personality_promotion(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        manifest = runtime.create_branch_manifest(
            command_id="zera:evolve-personality",
            client_id="repo_native",
            branch_type="persona_sensitivity_branch",
            objective="Test persona merge",
            run_id="run-merge-2",
        )
        with self.assertRaisesRegex(ValueError, "stable memory"):
            runtime.create_branch_merge_record(
                manifest=manifest,
                candidate_classification="personality",
                summary="attempt write",
                stable_memory_write_requested=True,
            )
        with self.assertRaisesRegex(ValueError, "personality promotion"):
            runtime.create_branch_merge_record(
                manifest=manifest,
                candidate_classification="personality",
                summary="attempt promote",
                personality_promotion_requested=True,
            )

    def test_governor_blocks_multi_axis_and_router_rewrite(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        multi_axis = runtime.evaluate_governor(
            axis_deltas={"warmth": 1, "firmness": 1},
            cycle_significant_deltas=0,
            consecutive_regressions=0,
            router_rewrite=False,
            review_approved=False,
        )
        self.assertTrue(multi_axis["blocked"])
        self.assertIn("one significant personality axis", " ".join(multi_axis["reasons"]))

        router_conflict = runtime.evaluate_governor(
            axis_deltas={"warmth": 1},
            cycle_significant_deltas=0,
            consecutive_regressions=0,
            router_rewrite=True,
            review_approved=False,
        )
        self.assertTrue(router_conflict["blocked"])
        self.assertTrue(router_conflict["freeze"])

    def test_governor_requires_review_for_emotional_closeness(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        review = runtime.evaluate_governor(
            axis_deltas={"emotional_closeness": 1},
            cycle_significant_deltas=0,
            consecutive_regressions=0,
            router_rewrite=False,
            review_approved=False,
        )
        self.assertTrue(review["blocked"])
        self.assertTrue(review["requires_review"])

    def test_import_activation_blocks_concept_only_and_unknown_artifacts(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        concept = runtime.validate_import_activation(
            artifact_id="open-claude-code-workflow-oracle",
            imported_files=["vendor/reference/open-claude-code.txt"],
        )
        self.assertTrue(concept["blocked"])
        self.assertEqual(concept["import_lane"], "concept_reference_quarantine")

        with self.assertRaisesRegex(ValueError, "Unknown import artifact"):
            runtime.validate_import_activation(
                artifact_id="unknown-artifact",
                imported_files=["foo.py"],
            )


class TestZeraCommandRuntimeTelemetry(unittest.TestCase):
    def test_resolve_emits_command_event(self) -> None:
        trace_file = None
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            env = dict(os.environ)
            env["AGENT_OS_TRACE_FILE"] = str(trace_file)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/zera_command_runtime.py"),
                    "resolve",
                    "--client",
                    "gemini",
                    "--command",
                    "zera:evolve-capability",
                    "--objective",
                    "Test degrade",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=ROOT,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rows = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            event_types = {row["event_type"] for row in rows}
            self.assertIn("zera_command_resolved", event_types)
            resolved = next(row for row in rows if row["event_type"] == "zera_command_resolved")
            self.assertEqual(resolved["command_id"], "zera:research")
            self.assertEqual(resolved["client_id"], "gemini")
            self.assertEqual(resolved["decision"], "degraded")
            self.assertEqual(resolved["rollback_path"], "downgrade to analysis-only review with no external source promotion")

    def test_branch_merge_cli_rejects_missing_classification(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/zera_command_runtime.py"),
                "branch-merge",
                "--manifest-json",
                json.dumps(
                    {
                        "branch_id": "research_branch-run-1",
                        "branch_type": "research_branch",
                        "parent_run_id": "run-1",
                        "source_command": "zera:evolve-capability",
                        "origin_prompt": "Test",
                        "allowed_tools": ["swarm"],
                        "max_turns": 10,
                        "ttl_minutes": 90,
                        "merge_policy": "source_card_then_candidate_cards",
                        "candidate_emission_allowed": True,
                        "stable_memory_write_allowed": False,
                        "personality_promotion_allowed": False,
                    }
                ),
                "--classification",
                "",
                "--summary",
                "bad",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
