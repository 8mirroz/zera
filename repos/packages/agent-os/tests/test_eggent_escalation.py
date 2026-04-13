from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.eggent_escalation import EggentEscalationEngine
from agent_os.eggent_algorithm import evaluate_algorithm_gates
from agent_os.contracts import MemoryStoreInput
from agent_os.memory_store import MemoryStore


class _FakeHTTPResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


_ENV_KEYS = [
    "MEMORY_FILE_PATH",
    "MEMORY_BACKEND",
    "MEMU_API_KEY",
    "MEMU_BASE_URL",
    "MEMU_USER_ID",
    "MEMU_AGENT_ID",
    "MEMU_HTTP_TIMEOUT_SECONDS",
    "MEMU_FAIL_OPEN",
]


class TestEggentEscalation(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EggentEscalationEngine(ROOT)
        self.spec = {
            "task_id": "esc-1",
            "area": "backend",
            "risk": "medium",
            "scope": "multi_file",
            "complexity": "normal",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        self._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values: str) -> None:
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in values.items():
            os.environ[key] = value

    def test_worker_limit_escalates_to_specialist(self) -> None:
        out = self.engine.decide(self.spec, signals=[], attempts_worker=3, attempts_specialist=0)
        self.assertEqual(out.next_role, "specialist")

    def test_specialist_limit_escalates_to_supervisor(self) -> None:
        out = self.engine.decide(self.spec, signals=[], attempts_worker=0, attempts_specialist=2)
        self.assertEqual(out.next_role, "supervisor")

    def test_architecture_violation_escalates_to_supervisor(self) -> None:
        out = self.engine.decide(
            self.spec,
            signals=["architecture_violation"],
            attempts_worker=0,
            attempts_specialist=0,
        )
        self.assertEqual(out.next_role, "supervisor")
        self.assertIn("architecture_violation", out.matched_signals)

    def test_unknown_signal_fail_safe_supervisor(self) -> None:
        out = self.engine.decide(self.spec, signals=["unknown_signal"], attempts_worker=0, attempts_specialist=0)
        self.assertEqual(out.next_role, "supervisor")

    def test_autonomy_ladder_requires_approval_for_destructive_complex_task(self) -> None:
        checks, metadata = evaluate_algorithm_gates(
            {"id": "autonomy_ladder", "gates": ["autonomy_ladder"]},
            objective="Delete stale production records",
            task_type="T4",
            complexity="C4",
            route_payload={},
            run_payload={"agent": {"status": "completed"}},
            summary_data={"verification_status": "passed"},
            base_checks={"agent_completed": True},
        )

        self.assertFalse(checks["autonomy_ladder"])
        self.assertTrue(metadata["contract"]["requires_approval"])

        checks, _ = evaluate_algorithm_gates(
            {"id": "autonomy_ladder", "gates": ["autonomy_ladder"]},
            objective="Delete stale production records",
            task_type="T4",
            complexity="C4",
            route_payload={"approval_policy": "human_required"},
            run_payload={"agent": {"status": "completed"}},
            summary_data={"verification_status": "passed"},
            base_checks={"agent_completed": True},
        )
        self.assertTrue(checks["autonomy_ladder"])

    def test_self_verify_is_evidence_aware_for_low_risk_tasks(self) -> None:
        checks, metadata = evaluate_algorithm_gates(
            {"id": "self_verify_gate", "gates": ["self_verify"]},
            objective="Add a new env variable to .env.example",
            task_type="T1",
            complexity="C1",
            route_payload={"primary_model": "qwen/qwen3.6-plus:free"},
            run_payload={"agent": {"status": "completed"}},
            summary_data={"verification_status": "not-run"},
            base_checks={"agent_completed": True, "duration_within_limit": True},
        )

        self.assertTrue(checks["self_verify_gate"])
        self.assertEqual(metadata["verification_state"], "missing")
        self.assertFalse(metadata["contract"]["requires_verification"])

    def test_spec_contract_keeps_explicit_test_tasks_strict(self) -> None:
        checks, metadata = evaluate_algorithm_gates(
            {"id": "spec_to_contract_gate", "gates": ["spec_contract"]},
            objective="Implement a REST API endpoint with validation and tests",
            task_type="T3",
            complexity="C3",
            route_payload={"primary_model": "qwen/qwen3.6-plus:free"},
            run_payload={"agent": {"status": "completed"}},
            summary_data={"verification_status": "not-run"},
            base_checks={"agent_completed": True, "duration_within_limit": True},
        )

        self.assertFalse(checks["spec_to_contract_gate"])
        self.assertTrue(metadata["contract"]["requires_verification"])
        self.assertEqual(metadata["verification_state"], "missing")

    def test_memory_namespace_helpers_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._set_env(MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"), MEMORY_BACKEND="jsonl")
            mem = MemoryStore(ROOT)
            write = mem.record_eggent_snapshot("escalation", "task-55", {"next_role": "specialist"})
            self.assertTrue(str(write.result.get("key", "")).startswith("eggent:escalation:task-55"))
            read = mem.operate(MemoryStoreInput(op="read", key=write.result["key"], payload={}))
            self.assertGreaterEqual(len(read.result.get("items", [])), 1)

    def test_memory_namespace_helpers_memu_cloud(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="true",
            )

            with mock.patch("agent_os.memory_store.urllib_request.urlopen", return_value=_FakeHTTPResponse({"task_id": "m1"})):
                mem = MemoryStore(ROOT)
                write = mem.record_eggent_snapshot("runs", "task-77", {"status": "ok"}, suffix="route")

            self.assertTrue(str(write.result.get("key", "")).startswith("eggent:runs:task-77:route"))
            self.assertEqual(write.result.get("_backend"), "memu_cloud_hybrid")


class TestEggentEscalationCli(unittest.TestCase):
    def test_cli_escalates_after_3_worker_failures(self) -> None:
        spec = {
            "task_id": "esc-cli-1",
            "area": "backend",
            "risk": "medium",
            "scope": "multi_file",
            "complexity": "normal",
            "requires_reasoning": False,
            "requires_accuracy": True,
        }
        cmd = [
            sys.executable,
            str(ROOT / "repos/packages/agent-os/scripts/swarmctl.py"),
            "eggent-escalate",
            "--task-spec",
            json.dumps(spec, ensure_ascii=False),
            "--attempts-worker",
            "3",
            "--attempts-specialist",
            "0",
            "--signals",
            "",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get("next_role"), "specialist")
        self.assertIn("memory_snapshot", payload)


if __name__ == "__main__":
    unittest.main()
