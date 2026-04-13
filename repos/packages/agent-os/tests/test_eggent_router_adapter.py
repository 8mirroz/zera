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

from agent_os.eggent_contracts import TaskSpecValidationError, TaskSpecV1
from agent_os.eggent_algorithm import load_algorithm_matrix, resolve_algorithm_variant
from agent_os.eggent_profile_loader import EggentProfileError, EggentProfileLoader
from agent_os.eggent_router_adapter import EggentRouterAdapter
from agent_os.exceptions import BudgetExceededError


class TestEggentContractsAndLoader(unittest.TestCase):
    def test_task_spec_parses_valid_payload(self) -> None:
        payload = {
            "task_id": "task-ui-1",
            "area": "ui",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        spec = TaskSpecV1.from_dict(payload)
        self.assertEqual(spec.task_id, "task-ui-1")
        self.assertEqual(spec.area, "ui")

    def test_task_spec_rejects_invalid_enum(self) -> None:
        payload = {
            "task_id": "bad-1",
            "area": "mobile",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": False,
        }
        with self.assertRaises(TaskSpecValidationError):
            TaskSpecV1.from_dict(payload)

    def test_profile_loader_default_path(self) -> None:
        loader = EggentProfileLoader(ROOT)
        profile = loader.load()
        self.assertIn("TaskSpec", profile.task_spec_schema)
        self.assertIn("model_pools", profile.model_routing_matrix)
        self.assertIn("failure_tracking", profile.escalation_rules)

    def test_profile_loader_missing_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing_root = Path(td) / "missing"
            loader = EggentProfileLoader(ROOT, pack_root=missing_root)
            with self.assertRaises(EggentProfileError):
                loader.load()

    def test_algorithm_matrix_promotes_measured_winner_and_keeps_strict_gates_shadowed(self) -> None:
        matrix = load_algorithm_matrix(ROOT)
        variant_id, variant = resolve_algorithm_variant(matrix, "spec_to_contract_gate")

        self.assertEqual(variant_id, "spec_to_contract_gate")
        self.assertIn("spec_contract", variant["gates"])
        self.assertEqual(matrix["promoted_default"]["variant"], "autonomy_ladder")
        self.assertEqual(
            matrix["promoted_default"]["always_on_gates"],
            ["autonomy_ladder"],
        )
        self.assertIn("self_verify", matrix["promoted_default"]["shadow_gates"])


class TestEggentRouterAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = EggentRouterAdapter(ROOT)

    def test_ui_task_maps_to_t6_and_is_deterministic(self) -> None:
        spec = {
            "task_id": "ui-det-1",
            "area": "ui",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }

        first = self.adapter.route_task(spec)
        second = self.adapter.route_task(spec)

        self.assertEqual(first.task_type, "T6")
        self.assertEqual(first.complexity_tier, "C1")
        self.assertEqual(first.route_reason, second.route_reason)
        self.assertEqual(first.routing_source, "v4")

    def test_budget_guard_works_for_adapter(self) -> None:
        spec = {
            "task_id": "budget-1",
            "area": "backend",
            "risk": "medium",
            "scope": "multi_file",
            "complexity": "normal",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        # In UnifiedRouter, budget check moved to route() internal. 
        # But we'll keep the test case to ensure it still raises if budgets are exceeded.
        with self.assertRaises(BudgetExceededError):
            self.adapter.route_task(spec, token_budget=1, cost_budget=0.00001)

    def test_adapter_passes_complexity_to_unified_router(self) -> None:
        spec = {
            "task_id": "complexity-pass-1",
            "area": "backend",
            "risk": "medium",
            "scope": "multi_file",
            "complexity": "normal",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        decision = self.adapter.route_task(spec)
        self.assertEqual(decision.complexity_tier, "C3")
        router_meta = (decision.telemetry or {}).get("router_telemetry", {})
        self.assertEqual(router_meta.get("v4_tier_name"), "Medium")


class TestEggentRouteCli(unittest.TestCase):
    def _run_cli(self, spec: dict[str, object]) -> dict[str, object]:
        cmd = [
            sys.executable,
            str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
            "eggent-route",
            "--task-spec",
            json.dumps(spec, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        return json.loads(proc.stdout)

    def test_cli_route_for_ui_backend_infra(self) -> None:
        cases = [
            (
                {
                    "task_id": "cli-ui-1",
                    "area": "ui",
                    "risk": "low",
                    "scope": "single_file",
                    "complexity": "trivial",
                    "requires_reasoning": False,
                    "requires_accuracy": True,
                },
                "T6",
            ),
            (
                {
                    "task_id": "cli-be-1",
                    "area": "backend",
                    "risk": "medium",
                    "scope": "multi_file",
                    "complexity": "normal",
                    "requires_reasoning": False,
                    "requires_accuracy": True,
                },
                "T3",
            ),
            (
                {
                    "task_id": "cli-infra-1",
                    "area": "infra",
                    "risk": "high",
                    "scope": "system_wide",
                    "complexity": "hard",
                    "requires_reasoning": True,
                    "requires_accuracy": True,
                },
                "T4",
            ),
        ]

        for spec, expected_task_type in cases:
            with self.subTest(task_id=spec["task_id"]):
                payload = self._run_cli(spec)
                self.assertEqual(payload["task_type"], expected_task_type)
                self.assertIn("primary_model", payload)
                self.assertIn("routing_source", payload)
                self.assertIn("memory_snapshot", payload)

    def test_cli_eggent_validate_ok(self) -> None:
        cmd = [
            sys.executable,
            str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
            "eggent-validate",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("strict_mode", payload)
        self.assertIn("profile_checks", payload)
        self.assertIn("design_checks", payload)

    def test_cli_eggent_validate_with_pack_root(self) -> None:
        src = ROOT / "docs/AntiQ v3/antigravity_eggent_pack"
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "pack"
            shutil.copytree(src, dst)
            cmd = [
                sys.executable,
                str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
                "eggent-validate",
                "--pack-root",
                str(dst),
            ]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("status"), "ok")
            self.assertEqual(payload.get("pack_root"), str(dst))

    def test_cli_eggent_auto_flow(self) -> None:
        spec = {
            "task_id": "auto-ui-1",
            "area": "ui",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        cmd = [
            sys.executable,
            str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
            "eggent-auto",
            "--task-spec",
            json.dumps(spec, ensure_ascii=False),
            "--signals",
            "build_failed",
            "--attempts-worker",
            "1",
            "--attempts-specialist",
            "0",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("route", payload)
        self.assertIn("escalation", payload)
        self.assertIn("design", payload)
        self.assertEqual(payload["route"]["task_type"], "T6")
        # In v4, specialist attempts are handled by UnifiedRouter.escalate
        self.assertIn(payload["escalation"]["escalated_tier"], ["C3", "C4", "C5"])


if __name__ == "__main__":
    unittest.main()
