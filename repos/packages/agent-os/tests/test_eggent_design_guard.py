from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.eggent_design_guard import EggentDesignGuard
from agent_os.eggent_profile_loader import EggentProfileError
from agent_os.eggent_router_adapter import EggentRouterAdapter


class TestEggentDesignGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = EggentDesignGuard(ROOT)
        self.adapter = EggentRouterAdapter(ROOT)

    def test_design_guard_allows_ui_and_is_stable(self) -> None:
        spec = {
            "task_id": "design-1",
            "area": "ui",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        route = self.adapter.route_task(spec)
        first = self.guard.evaluate(spec, route)
        second = self.guard.evaluate(spec, route)

        self.assertTrue(first.design_contour)
        self.assertEqual(first.design_role, "design_worker")
        self.assertEqual(first.token_policy_hash, second.token_policy_hash)
        self.assertEqual(first.violations, [])

    def test_outside_t6_reports_violation(self) -> None:
        spec = {
            "task_id": "design-2",
            "area": "backend",
            "risk": "low",
            "scope": "single_file",
            "complexity": "normal",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        route = self.adapter.route_task(spec)
        out = self.guard.evaluate(spec, route)
        self.assertFalse(out.design_contour)
        self.assertIn("Task is outside T6 design contour", out.violations)

    def test_backend_assigned_role_violation(self) -> None:
        spec = {
            "task_id": "design-3",
            "area": "ui",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        route = self.adapter.route_task(spec)
        # EggentRouteDecisionV1 stores execution_role
        route.execution_role = "specialist"
        out = self.guard.evaluate(spec, route)
        self.assertIn("Backend execution role cannot be used inside design contour", out.violations)

    def test_missing_tokens_raises(self) -> None:
        src = ROOT / "docs/AntiQ v3/antigravity_eggent_pack"
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pack"
            shutil.copytree(src, dst)
            (dst / "design_agent/design_memory/visual_tokens.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(EggentProfileError):
                EggentDesignGuard(ROOT, pack_root=dst)


class TestEggentDesignRouteCli(unittest.TestCase):
    def _run_cli(self, spec: dict[str, object]) -> dict[str, object]:
        cmd = [
            sys.executable,
            str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
            "eggent-design-route",
            "--task-spec",
            json.dumps(spec, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_design_route_kinds(self) -> None:
        cases = [
            (
                {
                    "task_id": "dr-ui",
                    "area": "ui",
                    "risk": "low",
                    "scope": "single_file",
                    "complexity": "trivial",
                    "requires_reasoning": False,
                    "requires_accuracy": True,
                },
                "ui_component",
                "design_worker",
            ),
            (
                {
                    "task_id": "dr-anim",
                    "area": "animation",
                    "risk": "medium",
                    "scope": "multi_file",
                    "complexity": "normal",
                    "requires_reasoning": False,
                    "requires_accuracy": True,
                },
                "animation",
                "design_worker",
            ),
            (
                {
                    "task_id": "dr-system",
                    "area": "ui",
                    "risk": "high",
                    "scope": "system_wide",
                    "complexity": "hard",
                    "requires_reasoning": True,
                    "requires_accuracy": True,
                },
                "design_system_change",
                "design_supervisor",
            ),
        ]

        for spec, expected_kind, expected_role in cases:
            with self.subTest(task_id=spec["task_id"]):
                out = self._run_cli(spec)
                self.assertEqual(out["design_task_kind"], expected_kind)
                self.assertEqual(out["design_role"], expected_role)
                self.assertTrue(out["design_contour"])
                self.assertIn("token_policy_hash", out)


if __name__ == "__main__":
    unittest.main()
