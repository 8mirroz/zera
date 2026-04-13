from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = ROOT / "scripts" / "validation" / "check_zera_hardening.py"


def _load_validator_module():
    spec = importlib.util.spec_from_file_location("check_zera_hardening_module", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestZeraClientProfileValidation(unittest.TestCase):
    def test_validate_client_runtime_profiles_ok(self) -> None:
        module = _load_validator_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            hermes = tmp / "hermes.yaml"
            gemini = tmp / "gemini.json"

            hermes_payload = {
                "zera_adapter_contract": {
                    "command_registry_ref": "/x/configs/tooling/zera_command_registry.yaml",
                    "client_profiles_ref": "/x/configs/tooling/zera_client_profiles.yaml",
                    "adapter_ref": "/x/configs/adapters/hermes/adapter.yaml",
                    "agent_map_ref": "/x/configs/adapters/hermes/agent-map.yaml",
                    "mode_router_ref": "/x/configs/tooling/zera_mode_router.json",
                    "growth_governance_ref": "/x/configs/tooling/zera_growth_governance.json",
                    "branch_policy_ref": "/x/configs/tooling/zera_branching_policy.yaml",
                    "semantics_source": "repo",
                    "default_namespace": "zera:*",
                },
                "secret_policy": {
                    "env_ref_only": True,
                    "inline_secret_forbidden": True,
                },
            }
            gemini_payload = {
                "zera_command_control": {
                    "command_registry": "/x/configs/tooling/zera_command_registry.yaml",
                    "client_profiles": "/x/configs/tooling/zera_client_profiles.yaml",
                    "branching_policy": "/x/configs/tooling/zera_branching_policy.yaml",
                    "mode_router": "/x/configs/tooling/zera_mode_router.json",
                    "growth_governance": "/x/configs/tooling/zera_growth_governance.json",
                    "semantics_source": "repo",
                    "default_command_namespace": "zera:*",
                },
                "secret_policy": {
                    "env_ref_only": True,
                    "inline_secret_forbidden": True,
                },
            }

            hermes.write_text(yaml.safe_dump(hermes_payload, sort_keys=False), encoding="utf-8")
            gemini.write_text(json.dumps(gemini_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            module.HERMES_PROFILE = hermes
            module.GEMINI_CONFIG = gemini
            os.environ["ZERA_REQUIRE_CLIENT_PROFILES"] = "1"
            result = module.validate_client_runtime_profiles()

            self.assertEqual(result["hermes_profile"], "ok")
            self.assertEqual(result["gemini_config"], "ok")

    def test_validate_client_runtime_profiles_rejects_inline_secret_pattern(self) -> None:
        module = _load_validator_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            hermes = tmp / "hermes.yaml"
            gemini = tmp / "gemini.json"

            hermes.write_text(
                yaml.safe_dump(
                    {
                        "zera_adapter_contract": {
                            "command_registry_ref": "/x/configs/tooling/zera_command_registry.yaml",
                            "client_profiles_ref": "/x/configs/tooling/zera_client_profiles.yaml",
                            "adapter_ref": "/x/configs/adapters/hermes/adapter.yaml",
                            "agent_map_ref": "/x/configs/adapters/hermes/agent-map.yaml",
                            "mode_router_ref": "/x/configs/tooling/zera_mode_router.json",
                            "growth_governance_ref": "/x/configs/tooling/zera_growth_governance.json",
                            "branch_policy_ref": "/x/configs/tooling/zera_branching_policy.yaml",
                            "semantics_source": "repo",
                            "default_namespace": "zera:*",
                        },
                        "secret_policy": {
                            "env_ref_only": True,
                            "inline_secret_forbidden": True,
                        },
                        "bad_token": "sk-abc12345678901234567890",
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            gemini.write_text("{}", encoding="utf-8")

            module.HERMES_PROFILE = hermes
            module.GEMINI_CONFIG = gemini
            os.environ["ZERA_REQUIRE_CLIENT_PROFILES"] = "1"
            with self.assertRaises(module.ValidationError):
                module.validate_client_runtime_profiles()


if __name__ == "__main__":
    unittest.main()
