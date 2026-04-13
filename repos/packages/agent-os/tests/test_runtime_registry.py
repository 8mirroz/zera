from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.runtime_registry import RuntimeRegistry


class TestRuntimeRegistry(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_t7_route_prefers_zeroclaw_when_enabled(self) -> None:
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
                    "routing_overrides": [
                        {
                            "task_type": ["T7"],
                            "complexity": ["C1", "C2", "C3", "C4", "C5"],
                            "provider": "zeroclaw",
                            "profile": "zera-telegram-prod",
                        }
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

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                registry = RuntimeRegistry(repo)
                decision = registry.resolve(task_type="T7", complexity="C3")
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)

            self.assertEqual(decision["runtime_provider_requested"], "zeroclaw")
            self.assertEqual(decision["runtime_provider"], "zeroclaw")
            self.assertEqual(decision["runtime_profile"], "zera-telegram-prod")
            self.assertEqual(decision["runtime_profile_data"]["channel"], "telegram")
            self.assertEqual(decision["autonomy_mode"], "bounded_initiative")
            self.assertEqual(decision["approval_policy"], "zera-standard")
            self.assertEqual(decision["background_profile"], "zera-companion")
            self.assertEqual(decision["scheduler_profile"], "telegram-edge")
            self.assertEqual(decision["persona_version"], "zera-v1")
            self.assertEqual(decision["capabilities"], ["local_execution", "background_jobs"])
            self.assertEqual(decision["network_policy"], "profile_defined")
            self.assertEqual(decision["max_chain_length"], 4)
            self.assertEqual(decision["max_cost_usd_per_run"], 0.02)
            self.assertEqual(decision["stop_conditions"], ["user_stop", "loop_stop"])
            self.assertEqual(decision["operator_visibility"], "approval_summary")
            self.assertEqual(decision["cost_budget_usd"], 0.02)
            self.assertEqual(decision["max_actions"], 4)
            self.assertTrue(decision["proof_required"])

    def test_provider_parity_report_detects_enabled_unregistered_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "hermes": {"enabled": True, "fallback_chain": ["agent_os_python"]},
                    },
                    "routing_overrides": [],
                },
            )
            registry = RuntimeRegistry(repo)
            report = registry.provider_parity_report()
            self.assertFalse(report["parity_ok"])
            self.assertIn("hermes", report["enabled_but_unregistered"])

    def test_enabled_unregistered_provider_falls_back_to_registered_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "hermes": {"enabled": True, "fallback_chain": ["agent_os_python"]},
                    },
                    "routing_overrides": [
                        {"task_type": ["T4"], "complexity": ["C4"], "provider": "hermes"}
                    ],
                },
            )
            registry = RuntimeRegistry(repo)
            decision = registry.resolve(task_type="T4", complexity="C4")
            self.assertEqual(decision["runtime_provider_requested"], "hermes")
            self.assertEqual(decision["runtime_provider"], "agent_os_python")
            self.assertIn("unregistered", decision["runtime_reason"])

    def test_t7_route_falls_back_when_zeroclaw_disabled(self) -> None:
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
                        },
                    },
                    "routing_overrides": [
                        {
                            "task_type": ["T7"],
                            "complexity": ["C1", "C2", "C3", "C4", "C5"],
                            "provider": "zeroclaw",
                            "profile": "zera-telegram-prod",
                        }
                    ],
                },
            )

            registry = RuntimeRegistry(repo)
            decision = registry.resolve(task_type="T7", complexity="C2")

            self.assertEqual(decision["runtime_provider_requested"], "zeroclaw")
            self.assertEqual(decision["runtime_provider"], "agent_os_python")
            self.assertIn("fallback", decision["runtime_reason"])

    def test_source_tier_blocks_capability_promotion_and_constrains_runtime(self) -> None:
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
                        },
                    },
                    "routing_overrides": [
                        {
                            "task_type": ["T7"],
                            "complexity": ["C1", "C2", "C3", "C4", "C5"],
                            "provider": "zeroclaw",
                            "profile": "zera-telegram-prod",
                        }
                    ],
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
                registry = RuntimeRegistry(repo)
                decision = registry.resolve(
                    task_type="T7",
                    complexity="C2",
                    source_tier="Tier C",
                    requests_capability_promotion=True,
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
            self.assertEqual(decision["runtime_provider_requested"], "zeroclaw")
            self.assertEqual(decision["runtime_provider"], "agent_os_python")
            self.assertIsNone(decision["runtime_profile"])
            self.assertTrue(decision["source_tier_policy"]["blocked"])
            self.assertIn("does not allow capability promotion", decision["runtime_reason"])

    def test_claw_code_route_prefers_provider_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "claw_code": {
                            "enabled": False,
                            "env_flag": "ENABLE_CLAW_CODE",
                            "fallback_chain": ["agent_os_python"],
                            "capabilities": ["local_execution", "tool_execution", "recovery"],
                            "autonomy_level": "bounded_initiative",
                            "background_jobs_supported": False,
                            "approval_gates": ["destructive", "external"],
                            "resource_limits": {"timeout_seconds": 15},
                            "network_policy": "profile_defined",
                            "max_chain_length": 3,
                            "max_cost_usd_per_run": 0.03,
                            "stop_conditions": ["user_stop", "safety_stop"],
                            "profiles": {
                                "claw-local": {
                                    "execution_mode": "stdio_json",
                                    "network_policy": "local-dev-restricted",
                                }
                            },
                        },
                    },
                    "routing_overrides": [
                        {
                            "task_type": ["T3"],
                            "complexity": ["C3"],
                            "provider": "claw_code",
                            "profile": "claw-local",
                        }
                    ],
                },
            )

            os.environ["ENABLE_CLAW_CODE"] = "true"
            try:
                decision = RuntimeRegistry(repo).resolve(task_type="T3", complexity="C3")
            finally:
                os.environ.pop("ENABLE_CLAW_CODE", None)

            self.assertEqual(decision["runtime_provider_requested"], "claw_code")
            self.assertEqual(decision["runtime_provider"], "claw_code")
            self.assertEqual(decision["runtime_profile"], "claw-local")
            self.assertEqual(decision["runtime_profile_data"]["execution_mode"], "stdio_json")
            self.assertEqual(decision["capabilities"], ["local_execution", "tool_execution", "recovery"])
            self.assertEqual(decision["network_policy"], "local-dev-restricted")

    def test_claw_code_route_falls_back_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "claw_code": {
                            "enabled": False,
                            "env_flag": "ENABLE_CLAW_CODE",
                            "fallback_chain": ["agent_os_python"],
                        },
                    },
                    "routing_overrides": [
                        {
                            "task_type": ["T3"],
                            "complexity": ["C3"],
                            "provider": "claw_code",
                            "profile": "claw-local",
                        }
                    ],
                },
            )

            decision = RuntimeRegistry(repo).resolve(task_type="T3", complexity="C3")

            self.assertEqual(decision["runtime_provider_requested"], "claw_code")
            self.assertEqual(decision["runtime_provider"], "agent_os_python")
            self.assertIn("fallback", decision["runtime_reason"])

    def test_source_tier_blocks_claw_code_capability_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "claw_code": {
                            "enabled": False,
                            "env_flag": "ENABLE_CLAW_CODE",
                            "fallback_chain": ["agent_os_python"],
                        },
                    },
                    "routing_overrides": [
                        {
                            "task_type": ["T3"],
                            "complexity": ["C3"],
                            "provider": "claw_code",
                            "profile": "claw-local",
                        }
                    ],
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
                        "  Tier C:",
                        "    allowed_for_capability_promotion: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            os.environ["ENABLE_CLAW_CODE"] = "true"
            try:
                decision = RuntimeRegistry(repo).resolve(
                    task_type="T3",
                    complexity="C3",
                    source_tier="Tier C",
                    requests_capability_promotion=True,
                )
            finally:
                os.environ.pop("ENABLE_CLAW_CODE", None)

            self.assertEqual(decision["runtime_provider_requested"], "claw_code")
            self.assertEqual(decision["runtime_provider"], "agent_os_python")
            self.assertIsNone(decision["runtime_profile"])
            self.assertTrue(decision["source_tier_policy"]["blocked"])


if __name__ == "__main__":
    unittest.main()
