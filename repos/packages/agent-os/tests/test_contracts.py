"""Tests for contract version fields and version_compat module."""

import unittest

from agent_os.contracts import ModelRouteInput, ModelRouteOutput
from agent_os.version_compat import (
    CURRENT_VERSION,
    SUPPORTED_VERSIONS,
    check_version_compat,
)


class TestContractVersionFields(unittest.TestCase):
    def test_model_route_input_default_version(self):
        inp = ModelRouteInput(
            task_type="code", complexity="low", token_budget=1000, cost_budget=0.5
        )
        self.assertEqual(inp.version, "2.0")

    def test_model_route_input_custom_version(self):
        inp = ModelRouteInput(
            task_type="code",
            complexity="low",
            token_budget=1000,
            cost_budget=0.5,
            version="1.0",
        )
        self.assertEqual(inp.version, "1.0")

    def test_model_route_output_default_version(self):
        out = ModelRouteOutput(
            task_type="code",
            complexity="low",
            model_tier="standard",
            primary_model="claude-3",
            fallback_chain=[],
            max_input_tokens=4096,
            max_output_tokens=2048,
            route_reason="test",
            provider_topology="single",
        )
        self.assertEqual(out.version, "2.0")

    def test_model_route_output_custom_version(self):
        out = ModelRouteOutput(
            task_type="code",
            complexity="low",
            model_tier="standard",
            primary_model="claude-3",
            fallback_chain=[],
            max_input_tokens=4096,
            max_output_tokens=2048,
            route_reason="test",
            provider_topology="single",
            version="1.0",
        )
        self.assertEqual(out.version, "1.0")


class TestVersionCompat(unittest.TestCase):
    def test_current_version_is_supported(self):
        self.assertIn(CURRENT_VERSION, SUPPORTED_VERSIONS)

    def test_supported_versions(self):
        self.assertTrue(check_version_compat("1.0"))
        self.assertTrue(check_version_compat("2.0"))

    def test_unsupported_version(self):
        self.assertFalse(check_version_compat("0.1"))
        self.assertFalse(check_version_compat("3.0"))


if __name__ == "__main__":
    unittest.main()
