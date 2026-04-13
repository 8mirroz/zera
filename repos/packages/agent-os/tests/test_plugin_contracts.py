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

from agent_os.plugin_contracts import PluginManifest, validate_plugin_manifest_file, validate_plugin_manifest_payload


class TestPluginContracts(unittest.TestCase):
    def test_validates_supported_plugin_manifest(self) -> None:
        summary = validate_plugin_manifest_payload(
            {
                "name": "quality-gate",
                "version": "0.1.0",
                "description": "Runs quality gates for a skill.",
                "permissions": ["read_workspace"],
                "hooks": {"PreToolUse": [], "PostToolUse": []},
                "lifecycle": {"Init": [], "Shutdown": []},
                "tools": {},
                "commands": {},
            },
            source="inline",
        )

        self.assertIsInstance(summary, PluginManifest)
        self.assertEqual(summary.name, "quality-gate")
        self.assertEqual(summary.version, "0.1.0")
        self.assertEqual(summary.hooks, ["PostToolUse", "PreToolUse"])
        self.assertEqual(summary.lifecycle, ["Init", "Shutdown"])

    def test_rejects_missing_name_or_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires string `name`"):
            validate_plugin_manifest_payload({"version": "0.1.0"}, source="inline")
        with self.assertRaisesRegex(ValueError, "requires string `version`"):
            validate_plugin_manifest_payload({"name": "quality-gate"}, source="inline")

    def test_rejects_unsupported_hook_and_non_list_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported plugin hook"):
            validate_plugin_manifest_payload(
                {"name": "bad", "version": "0.1.0", "hooks": {"BeforeAnything": []}},
                source="inline",
            )
        with self.assertRaisesRegex(ValueError, "hook `PreToolUse` must be a list"):
            validate_plugin_manifest_payload(
                {"name": "bad", "version": "0.1.0", "hooks": {"PreToolUse": "node hook.js"}},
                source="inline",
            )

    def test_validates_manifest_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "plugin.json"
            path.write_text(
                json.dumps({"name": "file-plugin", "version": "0.1.0", "hooks": {"PostToolUseFailure": []}}),
                encoding="utf-8",
            )

            summary = validate_plugin_manifest_file(path)

            self.assertEqual(summary.name, "file-plugin")
            self.assertEqual(summary.hooks, ["PostToolUseFailure"])


if __name__ == "__main__":
    unittest.main()
