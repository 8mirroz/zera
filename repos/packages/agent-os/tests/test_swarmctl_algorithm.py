from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import swarmctl


class TestSwarmctlAlgorithm(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_cmd_algorithm_doctor_validates_default_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), redirect_stdout(out):
                rc = swarmctl.cmd_algorithm_doctor(SimpleNamespace(matrix=None))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["summary"]["promoted_default"]["variant"], "autonomy_ladder")
            self.assertTrue(any(row["id"] == "baseline" for row in payload["summary"]["variants"]))

    def test_cmd_algorithm_inspect_returns_preflight_for_variant(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            route_ctx = {
                "mcp_profile": "core",
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "approval_policy": None,
                    "telemetry": {"v4_path": "Quality Path"},
                },
            }
            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "resolve_route_context", return_value=route_ctx
            ), redirect_stdout(out):
                rc = swarmctl.cmd_algorithm_inspect(
                    SimpleNamespace(
                        objective="Implement endpoint with tests",
                        task_type="T3",
                        complexity="C3",
                        variant="self_verify_gate",
                        matrix=None,
                        execution_channel="auto",
                    )
                )
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["variant"]["id"], "self_verify_gate")
            self.assertFalse(payload["preflight_checks"]["self_verify_gate"])
            self.assertEqual(payload["execution_channel_effective"], "cli_qwen")

    def test_cmd_algorithm_recommend_prefers_contract_variant_for_verified_build(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            route_ctx = {
                "mcp_profile": "core",
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "approval_policy": None,
                },
            }
            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "resolve_route_context", return_value=route_ctx
            ), redirect_stdout(out):
                rc = swarmctl.cmd_algorithm_recommend(
                    SimpleNamespace(
                        objective="Implement endpoint with tests and verify behavior",
                        task_type="T3",
                        complexity="C3",
                        matrix=None,
                        execution_channel="auto",
                    )
                )
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["recommendation"]["recommended_variant"], "spec_to_contract_gate")
            self.assertTrue(payload["recommendation"]["contract"]["requires_verification"])
            self.assertEqual(payload["recommendation"]["suggested_execution_channel"], "cli_qwen")


if __name__ == "__main__":
    unittest.main()
