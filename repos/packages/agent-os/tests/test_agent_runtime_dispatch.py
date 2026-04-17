from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.agent_runtime import AgentRuntime
from agent_os.approval_engine import ApprovalEngine
from agent_os.contracts import AgentInput
from agent_os.runtime_providers.agent_os_python import AgentOsPythonRuntimeProvider
from agent_os.runtime_providers.base import RuntimeProvider


class TestAgentRuntimeDispatch(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_fallback_to_python_runtime_when_zeroclaw_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {"enabled": False, "env_flag": "ENABLE_ZEROCLAW_ADAPTER", "fallback_chain": ["agent_os_python"]},
                    },
                    "routing_overrides": [],
                },
            )

            runtime = AgentRuntime(repo_root=repo)
            output = runtime.run(
                AgentInput(
                    run_id="run-fallback",
                    objective="test",
                    plan_steps=["execute"],
                    route_decision={
                        "task_type": "T7",
                        "complexity": "C2",
                        "runtime_provider": "zeroclaw",
                    },
                )
            )
            self.assertEqual(output.status, "completed")
            self.assertIn("No repository mutations", output.diff_summary)

    def test_runtime_enriches_route_with_registry_workflow_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {"agent_os_python": {"enabled": True, "fallback_chain": []}},
                    "routing_overrides": [],
                },
            )
            (repo / "configs/orchestrator").mkdir(parents=True, exist_ok=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C4:
      name: "Complex"
      workflow: "configs/registry/workflows/path-swarm.yaml"
      ralph_loop:
        enabled: true
        iterations: 5
  handoff_safeguards:
    max_chain_depth: 2
    forbid_cycles: true
    require_contract: true
    contract_schema: "configs/registry/schemas/task.schema.yaml"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/workflows").mkdir(parents=True, exist_ok=True)
            (repo / "configs/registry/skills").mkdir(parents=True, exist_ok=True)
            (repo / "configs/registry/workflows/path-swarm.yaml").write_text(
                """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
stages:
  - id: plan
    agent: architecture-systems-architect
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/skills/dynamic-handoff.yaml").write_text(
                "id: dynamic-handoff\noutputs: [handoff_contract]\ncontract_fields: [objective]\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/skills/ralph-loop-execute.yaml").write_text(
                "id: ralph-loop-execute\noutputs: [best_solution]\nverification_required: true\n",
                encoding="utf-8",
            )

            captured: dict[str, object] = {}

            class CapturingProvider(AgentOsPythonRuntimeProvider):
                def run(self, agent_input, *, repo_root, runtime_profile=None):
                    captured["route_decision"] = agent_input.route_decision
                    return super().run(agent_input, repo_root=repo_root, runtime_profile=runtime_profile)

            runtime = AgentRuntime(repo_root=repo)
            with patch.object(
                runtime,
                "runtime_registry",
                SimpleNamespace(
                    default_provider="agent_os_python",
                    resolve=lambda **_: {"runtime_provider": "agent_os_python", "runtime_fallback_chain": []},
                    get_provider=lambda _: CapturingProvider(),
                ),
            ):
                output = runtime.run(
                    AgentInput(
                        run_id="run-registry",
                        objective="complex task",
                        plan_steps=["execute"],
                        route_decision={"task_type": "T2", "complexity": "C4"},
                    )
                )

            self.assertEqual(output.status, "completed")
            route = captured["route_decision"]
            self.assertEqual(route["orchestration_path"], "Swarm Path")
            self.assertEqual(route["registry_workflow_context"]["workflow_id"], "swarm-path-to-completion")

    def test_runtime_enriches_zera_route_with_command_resolution(self) -> None:
        runtime = AgentRuntime(repo_root=ROOT)
        captured: dict[str, object] = {}

        class CapturingProvider(AgentOsPythonRuntimeProvider):
            def run(self, agent_input, *, repo_root, runtime_profile=None):
                captured["route_decision"] = agent_input.route_decision
                return super().run(agent_input, repo_root=repo_root, runtime_profile=runtime_profile)

        with patch.object(
            runtime,
            "runtime_registry",
            SimpleNamespace(
                default_provider="agent_os_python",
                resolve=lambda **_: {"runtime_provider": "agent_os_python", "runtime_fallback_chain": []},
                get_provider=lambda _: CapturingProvider(),
            ),
        ):
            output = runtime.run(
                AgentInput(
                    run_id="run-zera-command",
                    objective="Собери план развития",
                    plan_steps=["execute"],
                    route_decision={
                        "persona_id": "zera-v1",
                        "client_id": "repo_native",
                        "command_id": "zera:plan",
                        "task_type": "T3",
                        "complexity": "C2",
                    },
                )
            )

        self.assertEqual(output.status, "completed")
        route = captured["route_decision"]
        self.assertEqual(route["command_id"], "zera:plan")
        self.assertEqual(route["command_decision_reason"], "explicit_command")
        self.assertEqual(route["mode"], "plan")
        self.assertEqual(route["loop"], "capability")
        self.assertEqual(route["approval_route"], "allow_low_risk_after_eval")
        self.assertEqual(route["client_id"], "repo_native")

    def test_runtime_enriches_zera_route_with_gemini_degradation(self) -> None:
        runtime = AgentRuntime(repo_root=ROOT)
        captured: dict[str, object] = {}

        class CapturingProvider(AgentOsPythonRuntimeProvider):
            def run(self, agent_input, *, repo_root, runtime_profile=None):
                captured["route_decision"] = agent_input.route_decision
                return super().run(agent_input, repo_root=repo_root, runtime_profile=runtime_profile)

        with patch.object(
            runtime,
            "runtime_registry",
            SimpleNamespace(
                default_provider="agent_os_python",
                resolve=lambda **_: {"runtime_provider": "agent_os_python", "runtime_fallback_chain": []},
                get_provider=lambda _: CapturingProvider(),
            ),
        ):
            output = runtime.run(
                AgentInput(
                    run_id="run-zera-gemini",
                    objective="Запусти bounded capability evolution",
                    plan_steps=["execute"],
                    route_decision={
                        "persona_id": "zera-v1",
                        "client_id": "gemini",
                        "command_id": "zera:evolve-capability",
                        "task_type": "T3",
                        "complexity": "C2",
                    },
                )
            )

        self.assertEqual(output.status, "completed")
        route = captured["route_decision"]
        self.assertEqual(route["requested_command_id"], "zera:evolve-capability")
        self.assertEqual(route["command_id"], "zera:research")
        self.assertTrue(route["command_degraded"])
        self.assertIn("degrades to research-only mode", route["command_degradation_reason"])

    def test_zeroclaw_runtime_executes_health_probe_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {"enabled": False, "env_flag": "ENABLE_ZEROCLAW_ADAPTER", "fallback_chain": ["agent_os_python"]},
                    },
                    "routing_overrides": [],
                },
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            os.environ["ZEROCLAW_BIN"] = "echo"
            try:
                runtime = AgentRuntime(repo_root=repo)
                output = runtime.run(
                    AgentInput(
                        run_id="run-zeroclaw",
                        objective="test",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C3",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("ZEROCLAW_BIN", None)

            self.assertEqual(output.status, "completed")
            self.assertIn("ZeroClaw runtime provider executed health probe", output.diff_summary)

    def test_zeroclaw_runtime_executes_stdio_profile_and_writes_goal_stack(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {
                            "enabled": False,
                            "env_flag": "ENABLE_ZEROCLAW_ADAPTER",
                            "fallback_chain": ["agent_os_python"],
                            "capabilities": ["local_execution", "background_jobs"],
                            "autonomy_level": "bounded_initiative",
                            "background_jobs_supported": True,
                            "approval_gates": ["external_message_send"],
                            "resource_limits": {"timeout_seconds": 15},
                        },
                    },
                    "routing_overrides": [],
                },
            )
            self._write_json(
                repo / "configs/tooling/zeroclaw_profiles.json",
                {
                    "profiles": {
                        "zera-edge-local": {
                            "channel": "edge",
                            "persona_id": "zera-v1",
                            "persona_version": "zera-v1",
                            "memory_policy": "companion-curated-v1",
                            "autonomy_mode": "bounded_initiative",
                            "approval_policy": "zera-standard",
                            "background_profile": "zera-companion",
                            "scheduler_profile": "local-dev",
                            "budget_profile": "zera-standard",
                            "network_policy": "local-dev-restricted",
                            "workspace_scope": "workspace_only",
                            "tool_allowlist": ["memory_read", "memory_write", "background_queue", "goal_stack"],
                            "execution_mode": "stdio_json",
                            "timeout_seconds": 10,
                            "command": [
                                "python3",
                                str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                                "--profile",
                                "zera-edge-local",
                            ],
                        }
                    }
                },
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/autonomy_policy.yaml").write_text(
                "\n".join(
                    [
                        "policy_name: \"test-policy\"",
                        "default_action_class: always_allowed",
                        "action_classes:",
                        "  always_allowed:",
                        "    blocked: false",
                        "    requires_approval: false",
                        "action_type_map:",
                        "  task_follow_up: always_allowed",
                        "  goal_review: always_allowed",
                        "  research_refresh: always_allowed",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/background_jobs.yaml").write_text(
                "\n".join(
                    [
                        "scheduler_profiles:",
                        "  local-dev:",
                        "    cadence_policy: debug",
                        "jobs:",
                        "  goal_review:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: done",
                        "    escalation_rule: none",
                        "    user_suppressible: true",
                        "    daily_cap: 2",
                        "    staleness_minutes: 1440",
                        "    budget_profile: \"zera-standard\"",
                        "  memory_consolidation:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: done",
                        "    escalation_rule: none",
                        "    user_suppressible: false",
                        "    daily_cap: 2",
                        "    staleness_minutes: 1440",
                        "    budget_profile: \"zera-standard\"",
                        "  self_reflection:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: done",
                        "    escalation_rule: none",
                        "    user_suppressible: false",
                        "    daily_cap: 2",
                        "    staleness_minutes: 1440",
                        "    budget_profile: \"zera-standard\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/tool_execution_policy.yaml").write_text(
                "\n".join(
                    [
                        "allowed_tools:",
                        "  memory_read: read_only",
                        "  memory_write: workspace_only",
                        "  background_queue: workspace_only",
                        "  goal_stack: workspace_only",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/network_policy.yaml").write_text(
                "\n".join(
                    [
                        "policies:",
                        "  local-dev-restricted:",
                        "    mode: allowlist",
                        "    allow_hosts:",
                        "      - localhost",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/budget_policy.yaml").write_text(
                "\n".join(
                    [
                        "profiles:",
                        "  zera-standard:",
                        "    max_recursive_depth: \"4\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self._write_json(
                repo / "configs/tooling/persona_eval_suite.json",
                {"thresholds": {"overall_min": 0.7}},
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                runtime = AgentRuntime(repo_root=repo)
                output = runtime.run(
                    AgentInput(
                        run_id="run-zeroclaw-stdio",
                        objective="please help me plan next week carefully",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)

            self.assertEqual(output.status, "completed")
            self.assertIn("stdio adapter executed profile", output.diff_summary)
            goal_stack_path = repo / ".agents/memory/goal-stack.json"
            self.assertTrue(goal_stack_path.exists())
            payload = json.loads(goal_stack_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(payload.get("goals", [])), 1)

    def test_runtime_dispatch_enqueues_background_jobs_for_non_zeroclaw_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/background_jobs.yaml").write_text(
                "\n".join(
                    [
                        "scheduler_profiles:",
                        "  local-dev:",
                        "    cadence_policy: debug",
                        "jobs:",
                        "  harness_gardening:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: manual_stop",
                        "    escalation_rule: queue_review",
                        "    user_suppressible: false",
                        "    daily_cap: 1",
                        "    staleness_minutes: 1440",
                        "    budget_profile: \"operator-standard\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            class FakeBgProvider(RuntimeProvider):
                name = "fake_bg"

                def run(self, agent_input, *, repo_root, runtime_profile=None):
                    return type("Out", (), {
                        "status": "completed",
                        "diff_summary": "fake provider completed",
                        "test_report": {"status": "not-run"},
                        "artifacts": [],
                        "next_action": "none",
                        "response_text": None,
                        "meta": {"selected_mode": "analysis", "background_jobs": ["harness_gardening"]},
                    })()

            runtime = AgentRuntime(repo_root=repo)
            with patch.object(
                runtime,
                "runtime_registry",
                SimpleNamespace(
                    default_provider="fake_bg",
                    resolve=lambda **_: {
                        "runtime_provider": "fake_bg",
                        "runtime_provider_requested": "fake_bg",
                        "runtime_reason": "forced",
                        "runtime_fallback_chain": [],
                        "runtime_profile_data": {},
                        "capabilities": ["background_jobs"],
                        "autonomy_level": "bounded_initiative",
                        "background_jobs_supported": True,
                        "approval_gates": [],
                        "resource_limits": {},
                        "network_policy": None,
                        "max_chain_length": 2,
                        "max_cost_usd_per_run": 0.02,
                        "stop_conditions": [],
                        "autonomy_mode": "bounded_initiative",
                        "approval_policy": "operator-standard",
                        "background_profile": "worker-maintenance",
                        "scheduler_profile": "local-dev",
                        "persona_version": "agent-os-v1",
                        "operator_visibility": "summary",
                        "cost_budget_usd": 0.02,
                        "max_actions": 2,
                        "stop_token": None,
                        "proof_required": True,
                        "source_tier_policy": {},
                    },
                    get_provider=lambda _: FakeBgProvider(),
                ),
            ):
                output = runtime.run(
                    AgentInput(
                        run_id="run-fake-bg",
                        objective="refresh harness",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T4",
                            "complexity": "C4",
                            "runtime_provider": "fake_bg",
                            "persona_id": "agent-os",
                        },
                    )
                )

            self.assertEqual(output.status, "completed")
            queue_path = repo / ".agents/runtime/background-jobs.json"
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("queued", [])), 1)
            self.assertEqual(payload["queued"][0]["job_type"], "harness_gardening")

    def test_zeroclaw_runtime_creates_approval_ticket_for_external_contact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {
                            "enabled": False,
                            "env_flag": "ENABLE_ZEROCLAW_ADAPTER",
                            "fallback_chain": ["agent_os_python"],
                            "capabilities": ["local_execution", "background_jobs"],
                            "autonomy_level": "bounded_initiative",
                            "background_jobs_supported": True,
                            "approval_gates": ["external"],
                            "resource_limits": {"timeout_seconds": 15},
                            "network_policy": "profile_defined",
                            "max_chain_length": 4,
                            "max_cost_usd_per_run": 0.02,
                            "stop_conditions": ["user_stop", "loop_stop"],
                        },
                    },
                    "routing_overrides": [],
                },
            )
            self._write_json(
                repo / "configs/tooling/zeroclaw_profiles.json",
                {
                    "profiles": {
                        "zera-edge-local": {
                            "channel": "edge",
                            "persona_id": "zera-v1",
                            "persona_version": "zera-v1",
                            "memory_policy": "companion-curated-v1",
                            "autonomy_mode": "bounded_initiative",
                            "approval_policy": "zera-standard",
                            "background_profile": "zera-companion",
                            "scheduler_profile": "local-dev",
                            "budget_profile": "zera-standard",
                            "network_policy": "local-dev-restricted",
                            "workspace_scope": "workspace_only",
                            "tool_allowlist": ["memory_read", "memory_write", "background_queue", "goal_stack"],
                            "execution_mode": "stdio_json",
                            "timeout_seconds": 10,
                            "command": [
                                "python3",
                                str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                                "--profile",
                                "zera-edge-local",
                            ],
                        }
                    }
                },
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/autonomy_policy.yaml").write_text(
                "\n".join(
                    [
                        "policy_name: \"test-policy\"",
                        "default_action_class: always_allowed",
                        "action_classes:",
                        "  always_allowed:",
                        "    blocked: false",
                        "    requires_approval: false",
                        "  execute_gated:",
                        "    blocked: false",
                        "    requires_approval: true",
                        "action_type_map:",
                        "  external_contact: execute_gated",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/background_jobs.yaml").write_text("scheduler_profiles:\n  local-dev:\n    cadence_policy: debug\njobs:\n", encoding="utf-8")
            (repo / "configs/tooling/tool_execution_policy.yaml").write_text("allowed_tools:\n  memory_read: read_only\n  memory_write: workspace_only\n  background_queue: workspace_only\n  goal_stack: workspace_only\n", encoding="utf-8")
            (repo / "configs/tooling/network_policy.yaml").write_text("policies:\n  local-dev-restricted:\n    mode: allowlist\n    allow_hosts:\n      - localhost\n", encoding="utf-8")
            (repo / "configs/tooling/budget_policy.yaml").write_text("profiles:\n  zera-standard:\n    max_recursive_depth: \"4\"\n", encoding="utf-8")
            self._write_json(repo / "configs/tooling/persona_eval_suite.json", {"thresholds": {"overall_min": 0.7}})

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                runtime = AgentRuntime(repo_root=repo)
                output = runtime.run(
                    AgentInput(
                        run_id="run-approval-ticket",
                        objective="Please message the vendor and contact them about pricing",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)

            self.assertEqual(output.status, "completed")
            tickets = ApprovalEngine(repo).list_tickets(status="pending")
            self.assertEqual(len(tickets), 1)
            self.assertEqual(tickets[0].action_type, "external_contact")

    def test_source_tier_block_emits_policy_violation_and_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_path = repo / "logs/agent_traces.jsonl"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_path)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {"enabled": False, "env_flag": "ENABLE_ZEROCLAW_ADAPTER", "fallback_chain": ["agent_os_python"]},
                    },
                    "routing_overrides": [],
                },
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/source_trust_policy.yaml").write_text(
                "\n".join(
                    [
                        "default_tier: \"Tier C\"",
                        "tiers:",
                        "  Tier A:",
                        "    allowed_for_capability_promotion: true",
                        "  Tier B:",
                        "    allowed_for_capability_promotion: true",
                        "  Tier C:",
                        "    allowed_for_capability_promotion: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                runtime = AgentRuntime(repo_root=repo)
                output = runtime.run(
                    AgentInput(
                        run_id="run-source-tier-blocked",
                        objective="test",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "source_tier": "Tier C",
                            "requests_capability_promotion": True,
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(output.status, "completed")
            self.assertIn("No repository mutations", output.diff_summary)
            rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            policy_rows = [row for row in rows if row.get("event_type") == "policy_violation_detected"]
            self.assertEqual(len(policy_rows), 1)
            self.assertIn("does not allow capability promotion", str(policy_rows[0].get("message") or ""))


if __name__ == "__main__":
    unittest.main()
