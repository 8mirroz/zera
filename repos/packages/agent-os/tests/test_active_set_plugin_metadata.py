from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from active_set_lib import publish_active_set


class TestActiveSetPluginMetadata(unittest.TestCase):
    def _write_skill(self, root: Path, name: str, *, plugin: dict | None = None) -> None:
        skill_dir = root / "configs/skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("---\nname: test\n---\n# Test\n", encoding="utf-8")
        if plugin is not None:
            (skill_dir / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")

    def test_publish_legacy_skill_without_plugin_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_skill(repo, "legacy")
            active = repo / "configs/skills/ACTIVE_SKILLS.md"
            active.write_text("- `configs/skills/legacy`\n", encoding="utf-8")

            manifest = publish_active_set(repo_root=repo, active_md=active, dest_dir=repo / ".agents/skills")

            self.assertEqual(manifest["skills"][0]["name"], "legacy")
            self.assertNotIn("plugin", manifest["skills"][0])

    def test_publish_skill_with_supported_plugin_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_skill(
                repo,
                "with-plugin",
                plugin={
                    "name": "with-plugin",
                    "version": "0.1.0",
                    "hooks": {"PreToolUse": [], "PostToolUse": []},
                    "lifecycle": {"Init": [], "Shutdown": []},
                },
            )
            active = repo / "configs/skills/ACTIVE_SKILLS.md"
            active.write_text("- `configs/skills/with-plugin`\n", encoding="utf-8")

            manifest = publish_active_set(repo_root=repo, active_md=active, dest_dir=repo / ".agents/skills")

            plugin = manifest["skills"][0]["plugin"]
            self.assertEqual(plugin["path"], ".agents/skills/with-plugin/plugin.json")
            self.assertEqual(plugin["hooks"], ["PostToolUse", "PreToolUse"])
            self.assertEqual(plugin["lifecycle"], ["Init", "Shutdown"])

    def test_publish_rejects_unsupported_plugin_hook(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_skill(
                repo,
                "bad-plugin",
                plugin={"name": "bad-plugin", "version": "0.1.0", "hooks": {"DangerousHook": []}},
            )
            active = repo / "configs/skills/ACTIVE_SKILLS.md"
            active.write_text("- `configs/skills/bad-plugin`\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported plugin hook"):
                publish_active_set(repo_root=repo, active_md=active, dest_dir=repo / ".agents/skills")


if __name__ == "__main__":
    unittest.main()
