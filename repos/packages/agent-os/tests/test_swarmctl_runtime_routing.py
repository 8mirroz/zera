from __future__ import annotations

import json
import io
import os
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


class TestSwarmctlRuntimeRouting(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_resolve_route_context_sets_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/model_providers.json",
                {
                    "provider_topology": "hybrid",
                    "budgets": {
                        "per_complexity": {
                            "C1": {"max_total_tokens": 2000, "max_cost_usd": 0.05, "max_input_tokens": 1024, "max_output_tokens": 512},
                            "C2": {"max_total_tokens": 4000, "max_cost_usd": 0.1, "max_input_tokens": 2048, "max_output_tokens": 1024},
                            "C3": {"max_total_tokens": 8000, "max_cost_usd": 0.2, "max_input_tokens": 4096, "max_output_tokens": 2048},
                            "C4": {"max_total_tokens": 12000, "max_cost_usd": 0.4, "max_input_tokens": 6144, "max_output_tokens": 3072},
                            "C5": {"max_total_tokens": 16000, "max_cost_usd": 0.8, "max_input_tokens": 8192, "max_output_tokens": 4096}
                        }
                    },
                    "tiers": {
                        "free": {"gateway_models": ["google/gemini-2.0-flash-exp:free"], "direct_models": [], "aliases": {}},
                        "quality": {"gateway_models": ["openrouter/openai/gpt-4o-mini"], "direct_models": [], "aliases": {}},
                        "reasoning": {"gateway_models": ["openrouter/anthropic/claude-3.7-sonnet"], "direct_models": [], "aliases": {}},
                        "light": {"gateway_models": ["google/gemini-2.0-flash-exp:free"], "direct_models": [], "aliases": {}}
                    }
                },
            )
            self._write_json(
                repo / "configs/tooling/mcp_profiles.json",
                {"default_profile": "core", "profiles": {"core": {}}, "routing": []},
            )
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
                            "capabilities": ["background_jobs"],
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
                    "routing_overrides": [
                        {"task_type": ["T7"], "complexity": ["C1", "C2", "C3", "C4", "C5"], "provider": "zeroclaw", "profile": "zera-telegram-prod"}
                    ],
                },
            )
            self._write_json(
                repo / "configs/tooling/zeroclaw_profiles.json",
                {
                    "profiles": {
                        "zera-telegram-prod": {
                            "channel": "telegram",
                            "persona_id": "zera-v1",
                            "memory_policy": "companion-curated-v1",
                            "autonomy_mode": "bounded_initiative",
                            "approval_policy": "zera-standard",
                            "background_profile": "zera-companion",
                            "scheduler_profile": "telegram-edge",
                            "persona_version": "zera-v1",
                            "operator_visibility": "approval_summary",
                            "cost_budget_usd": 0.02,
                            "max_actions": 4,
                            "proof_required": True,
                        }
                    }
                },
            )

            ctx = swarmctl.resolve_route_context(
                repo,
                task_type="T7",
                complexity="C2",
                token_budget=2000,
                cost_budget=0.05,
                source_tier="Tier B",
                requests_capability_promotion=False,
            )

            route = ctx["route"]
            self.assertEqual(route["runtime_provider"], "agent_os_python")
            self.assertEqual(route["runtime_profile"], "zera-telegram-prod")
            self.assertEqual(route["channel"], "telegram")
            self.assertEqual(route["persona_id"], "zera-v1")
            self.assertEqual(route["autonomy_mode"], "bounded_initiative")
            self.assertEqual(route["approval_policy"], "zera-standard")
            self.assertEqual(route["background_profile"], "zera-companion")
            self.assertEqual(route["scheduler_profile"], "telegram-edge")
            self.assertEqual(route["persona_version"], "zera-v1")
            self.assertEqual(route["operator_visibility"], "approval_summary")
            self.assertEqual(route["cost_budget_usd"], 0.02)
            self.assertEqual(route["max_actions"], 4)
            self.assertTrue(route["proof_required"])
            self.assertEqual(route["source_tier"], "Tier B")
            self.assertFalse(route["requests_capability_promotion"])
            self.assertFalse(route["source_tier_policy"]["blocked"])

    def test_resolve_route_context_degrades_cli_qwen_when_binary_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/model_providers.json",
                {
                    "provider_topology": "hybrid",
                    "transport_routing": {
                        "default": "gateway-first",
                        "channel_overrides": {
                            "cli_qwen": "direct-only",
                            "api_router": "gateway-first",
                        },
                    },
                    "budgets": {"per_complexity": {"C1": {"max_total_tokens": 1000, "max_cost_usd": 0.05}}},
                    "tiers": {"free": {"gateway_models": ["openrouter/qwen/qwen3.6-plus:free"], "direct_models": ["qwen/qwen3.6-plus:free"]}},
                },
            )
            self._write_json(
                repo / "configs/tooling/mcp_profiles.json",
                {"default_profile": "core", "profiles": {"core": {}}, "routing": []},
            )
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True}}},
            )
            (repo / "configs/orchestrator").mkdir(parents=True, exist_ok=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                "\n".join(
                    [
                        "routing:",
                        "  tiers:",
                        "    C1:",
                        "      name: Trivial",
                        "      path: Fast Path",
                    ]
                ),
                encoding="utf-8",
            )
            (repo / "configs/orchestrator/models.yaml").write_text("models: {}\n", encoding="utf-8")

            with patch.object(swarmctl.shutil, "which", return_value=None):
                ctx = swarmctl.resolve_route_context(
                    repo,
                    task_type="T1",
                    complexity="C1",
                    token_budget=1000,
                    cost_budget=0.05,
                    execution_channel="cli_qwen",
                )

            route = ctx["route"]
            self.assertEqual(route.get("execution_channel_effective"), "api_router")
            self.assertEqual(route.get("execution_channel_requested"), "cli_qwen")
            self.assertEqual(route.get("execution_channel_degraded_reason"), "qwen_cli_unavailable")

    def test_resolve_route_context_respects_mcp_profile_feature_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/model_providers.json",
                {
                    "provider_topology": "hybrid",
                    "budgets": {"per_complexity": {"C3": {"max_total_tokens": 8000, "max_cost_usd": 0.2}}},
                    "tiers": {"quality": {"gateway_models": ["openrouter/openai/gpt-4o-mini"], "direct_models": [], "aliases": {}}},
                },
            )
            self._write_json(
                repo / "configs/tooling/mcp_profiles.json",
                {
                    "default_profile": "core",
                    "profiles": {
                        "core": {},
                        "lsp-code": {"feature_flag": "ENABLE_LSP_BRIDGE"},
                    },
                    "routing": [{"task_type": ["T2"], "complexity": ["C4"], "profile": "lsp-code"}],
                },
            )
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True}}},
            )
            (repo / "configs/orchestrator").mkdir(parents=True, exist_ok=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                "routing:\n  tiers:\n    C4:\n      name: Deep\n      path: Swarm Path\n",
                encoding="utf-8",
            )
            (repo / "configs/orchestrator/models.yaml").write_text("models: {}\n", encoding="utf-8")

            try:
                os.environ.pop("ENABLE_LSP_BRIDGE", None)
                ctx_disabled = swarmctl.resolve_route_context(repo, task_type="T2", complexity="C4", token_budget=8000, cost_budget=0.2)
                self.assertEqual(ctx_disabled["mcp_profile"], "core")

                os.environ["ENABLE_LSP_BRIDGE"] = "true"
                ctx_enabled = swarmctl.resolve_route_context(repo, task_type="T2", complexity="C4", token_budget=8000, cost_budget=0.2)
                self.assertEqual(ctx_enabled["mcp_profile"], "lsp-code")
            finally:
                os.environ.pop("ENABLE_LSP_BRIDGE", None)

    def test_resolve_route_context_respects_swarm_feature_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/model_providers.json",
                {
                    "provider_topology": "hybrid",
                    "budgets": {"per_complexity": {"C5": {"max_total_tokens": 16000, "max_cost_usd": 0.8}}},
                    "tiers": {"quality": {"gateway_models": ["openrouter/openai/gpt-4o-mini"], "direct_models": [], "aliases": {}}},
                },
            )
            self._write_json(
                repo / "configs/tooling/mcp_profiles.json",
                {
                    "default_profile": "core",
                    "profiles": {
                        "core": {},
                        "swarm": {"feature_flag": "ENABLE_SWARM_V2"},
                    },
                    "routing": [{"task_type": ["T4"], "complexity": ["C5"], "profile": "swarm"}],
                },
            )
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True}}},
            )
            (repo / "configs/orchestrator").mkdir(parents=True, exist_ok=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                "routing:\n  tiers:\n    C5:\n      name: Deep\n      path: Swarm Path\n",
                encoding="utf-8",
            )
            (repo / "configs/orchestrator/models.yaml").write_text("models: {}\n", encoding="utf-8")

            try:
                os.environ.pop("ENABLE_SWARM_V2", None)
                ctx_disabled = swarmctl.resolve_route_context(repo, task_type="T4", complexity="C5", token_budget=16000, cost_budget=0.8)
                self.assertEqual(ctx_disabled["mcp_profile"], "core")

                os.environ["ENABLE_SWARM_V2"] = "true"
                ctx_enabled = swarmctl.resolve_route_context(repo, task_type="T4", complexity="C5", token_budget=16000, cost_budget=0.8)
                self.assertEqual(ctx_enabled["mcp_profile"], "swarm")
            finally:
                os.environ.pop("ENABLE_SWARM_V2", None)

    def test_route_command_attaches_registry_workflow_context_for_swarm_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/model_providers.json",
                {
                    "provider_topology": "hybrid",
                    "budgets": {"per_complexity": {"C4": {"max_total_tokens": 12000, "max_cost_usd": 0.4}}},
                    "tiers": {"quality": {"gateway_models": ["openrouter/openai/gpt-4o-mini"], "direct_models": [], "aliases": {}}},
                },
            )
            self._write_json(
                repo / "configs/tooling/mcp_profiles.json",
                {"default_profile": "core", "profiles": {"core": {}}, "routing": []},
            )
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True}}},
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/wiki_core.yaml").write_text(
                """
version: "1.0"
paths:
  root: "repos/data/knowledge/wiki-core"
  raw: "repos/data/knowledge/wiki-core/raw"
  wiki: "repos/data/knowledge/wiki-core/wiki"
  manifests: "repos/data/knowledge/wiki-core/manifests"
  skills: "repos/data/knowledge/wiki-core/.skills"
  local_skill_target: ".agent/skills"
search:
  primary_backend: "qmd"
  fallback_backend: "tfidf"
  qmd:
    command: "definitely-not-qmd"
writeback:
  default_target: "wiki/_briefs"
  allowed_page_types: [brief]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/swarm.md"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text("# Swarm Context\n\nretrieval for swarm route", encoding="utf-8")
            (repo / "configs/registry/workflows").mkdir(parents=True, exist_ok=True)
            (repo / "configs/registry/skills").mkdir(parents=True, exist_ok=True)
            (repo / "configs/registry/workflows/path-swarm.yaml").write_text(
                """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
knowledge_policy:
  pre_search: true
  writeback: true
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
            (repo / "configs/registry/schemas").mkdir(parents=True, exist_ok=True)
            (repo / "configs/registry/schemas/task.schema.yaml").write_text(
                "type: object\nrequired: [objective, evidence]\n",
                encoding="utf-8",
            )
            (repo / "configs/orchestrator").mkdir(parents=True, exist_ok=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C4:
      name: "Complex"
      path: "Swarm Path"
      workflow: "configs/registry/workflows/path-swarm.yaml"
      max_tools: 35
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
            (repo / "configs/orchestrator/models.yaml").write_text("models: {}\n", encoding="utf-8")

            with patch.object(swarmctl, "_repo_root", return_value=repo):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_route(
                        SimpleNamespace(
                            text="complex architecture change",
                            task_type="T2",
                            complexity="C4",
                            token_budget=None,
                            cost_budget=None,
                            preferred_model=[],
                            mode=None,
                            unavailable_model=[],
                            runtime_provider=None,
                            runtime_profile=None,
                            source_tier=None,
                            request_capability_promotion=False,
                            execution_channel=None,
                        )
                    )
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["orchestration_path"], "Swarm Path")
            self.assertEqual(payload["registry_workflow_context"]["workflow_id"], "swarm-path-to-completion")
            self.assertEqual(payload["wiki_core_context"]["backend"], "tfidf")
            self.assertEqual(payload["handoff_contract_template"]["schema"], "configs/registry/schemas/task.schema.yaml")
            self.assertEqual(payload["handoff_contract_template"]["required_fields"], ["objective", "evidence"])
            self.assertEqual(payload["handoff_contract_template"]["template"]["objective"], "")
            self.assertEqual(payload["handoff_contract_template"]["template"]["evidence"], [])

    def test_validate_handoff_contract_output_marks_missing_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            validation = swarmctl._validate_handoff_contract_output(
                repo,
                registry_workflow_context={
                    "workflow_id": "swarm-path-to-completion",
                    "handoff": {
                        "required": True,
                        "schema": None,
                        "contract_fields": ["objective", "evidence"],
                    },
                },
                agent_meta={},
            )
            self.assertTrue(validation["required"])
            self.assertEqual(validation["status"], "missing")
            self.assertEqual(validation["missing_fields"], ["objective", "evidence"])

    def test_validate_handoff_contract_output_marks_valid_when_fields_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            validation = swarmctl._validate_handoff_contract_output(
                repo,
                registry_workflow_context={
                    "workflow_id": "swarm-path-to-completion",
                    "handoff": {
                        "required": True,
                        "schema": None,
                        "contract_fields": ["objective", "evidence"],
                    },
                },
                agent_meta={
                    "handoff_contract": {
                        "objective": "Ship feature safely",
                        "evidence": [{"type": "test", "value": "pytest green"}],
                    }
                },
            )
            self.assertEqual(validation["status"], "valid")
            self.assertEqual(validation["missing_fields"], [])
            self.assertEqual(validation["empty_required_fields"], [])


if __name__ == "__main__":
    unittest.main()
