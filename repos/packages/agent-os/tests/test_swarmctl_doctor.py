from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import swarmctl


class TestSwarmctlDoctor(unittest.TestCase):
    def _write(self, path: Path, data: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def _build_min_repo(self, root: Path) -> None:
        # Minimal files required by cmd_doctor.
        self._write(
            root / "configs/skills/ACTIVE_SKILLS.md",
            "\n".join(
                [
                    "# Active Skills Set",
                    "- `configs/skills/superpowers/systematic-debugging`",
                ]
            ),
        )
        self._write(root / "configs/skills/superpowers/systematic-debugging/SKILL.md", "# skill\n")

        self._write(
            root / "configs/orchestrator/router.yaml",
            "\n".join(
                [
                    "routing:",
                    "  tiers:",
                    "    C1:",
                    "      name: Simple",
                    "    C2:",
                    "      name: Simple",
                    "    C3:",
                    "      name: Standard",
                    "    C4:",
                    "      name: Advanced",
                    "    C5:",
                    "      name: Advanced",
                ]
            ),
        )
        self._write(
            root / "configs/orchestrator/models.yaml",
            "\n".join(
                [
                    "models:",
                    "  AGENT_MODEL_C1_LIGHT:",
                    "    provider_model: google/gemini-2.0-flash-exp:free",
                ]
            ),
        )
        self._write(
            root / "configs/tooling/mcp_profiles.json",
            json.dumps(
                {
                    "default_profile": "core",
                    "profiles": {"core": {}},
                    "routing": [{"task_type": ["T6"], "complexity": ["C3"], "profile": "core"}],
                }
            ),
        )
        self._write(
            root / "configs/tooling/model_providers.json",
            json.dumps({"provider_topology": "hybrid"}),
        )
        self._write(
            root / "configs/tooling/model_routing.json",
            json.dumps({"routing": []}),
        )

        skill_dir = root / ".agent/skills/systematic-debugging"
        self._write(skill_dir / "SKILL.md", "# published skill\n")
        manifest = {
            "skills": [
                {
                    "name": "systematic-debugging",
                    "sha256_tree": swarmctl.sha256_tree(skill_dir),
                }
            ]
        }
        self._write(root / ".agent/skills/.active_set_manifest.json", json.dumps(manifest))

    def test_doctor_warn_only_returns_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "ok"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 0)
            self.assertIn("OK: doctor passed", stdout.getvalue())
            # OPENROUTER_API_KEY is intentionally absent in test env; this should be a warning, not a failure.
            self.assertIn("WARN: Missing env var: OPENROUTER_API_KEY", stderr.getvalue())
            self.assertNotIn("REMEDIATION:", stderr.getvalue())

    def test_doctor_hash_drift_is_warning_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)
            self._write(repo / ".agent/skills/systematic-debugging/EXTRA.md", "local overlay\n")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "warn"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), patch.dict(os.environ, {"AGENT_OS_STRICT_SKILL_HASH": "0"}, clear=False), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 0)
            self.assertIn("OK: doctor passed", stdout.getvalue())
            self.assertIn("WARN: Hash mismatch for systematic-debugging", stderr.getvalue())

    def test_doctor_hash_drift_can_be_strict_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)
            self._write(repo / ".agent/skills/systematic-debugging/EXTRA.md", "local overlay\n")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "warn"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), patch.dict(os.environ, {"AGENT_OS_STRICT_SKILL_HASH": "1"}, clear=False), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 2)
            self.assertIn("FAIL: Hash mismatch for systematic-debugging", stderr.getvalue())

    def test_doctor_validator_error_emits_remediation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "warn"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "error"}
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 2)
            err = stderr.getvalue()
            self.assertIn("FAIL: Workflow/skill model alias validator: error", err)
            self.assertIn("REMEDIATION: Run `python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json`", err)
            self.assertIn("REMEDIATION: Run `python3 repos/packages/agent-os/scripts/skill_drift_validator.py --json`", err)

    def test_doctor_warns_when_wiki_core_qmd_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)
            self._write(
                repo / "configs/tooling/wiki_core.yaml",
                "\n".join(
                    [
                        "paths:",
                        "  root: repos/data/knowledge/wiki-core",
                        "  raw: repos/data/knowledge/wiki-core/raw",
                        "  wiki: repos/data/knowledge/wiki-core/wiki",
                        "  manifests: repos/data/knowledge/wiki-core/manifests",
                        "  skills: repos/data/knowledge/wiki-core/.skills",
                        "  local_skill_target: .agent/skills",
                        "search:",
                        "  primary_backend: qmd",
                        "  fallback_backend: tfidf",
                        "  qmd:",
                        "    command: qmd",
                    ]
                ),
            )
            for rel in [
                "repos/data/knowledge/wiki-core/raw",
                "repos/data/knowledge/wiki-core/wiki",
                "repos/data/knowledge/wiki-core/manifests",
                "repos/data/knowledge/wiki-core/.skills",
            ]:
                (repo / rel).mkdir(parents=True, exist_ok=True)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "ok"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), patch.object(
                swarmctl.shutil, "which", side_effect=lambda name: "/usr/bin/qwen" if name == "qwen" else None
            ), patch.object(
                swarmctl.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 0)
            self.assertIn("WARN: Wiki-core qmd unavailable", stderr.getvalue())

    def test_doctor_fails_when_registry_workflow_references_missing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)
            self._write(
                repo / "configs/orchestrator/router.yaml",
                "\n".join(
                    [
                        "version: \"4.2\"",
                        "routing:",
                        "  tiers:",
                        "    C1:",
                        "      name: Simple",
                        "    C2:",
                        "      name: Simple",
                        "    C3:",
                        "      name: Standard",
                        "    C4:",
                        "      name: Advanced",
                        "      workflow: \"configs/registry/workflows/path-swarm.yaml\"",
                        "      ralph_loop:",
                        "        enabled: true",
                        "        iterations: 5",
                        "    C5:",
                        "      name: Advanced",
                        "  handoff_safeguards:",
                        "    require_contract: true",
                    ]
                ),
            )
            self._write(
                repo / "configs/registry/workflows/path-swarm.yaml",
                "\n".join(
                    [
                        "id: swarm-path-to-completion",
                        "name: Swarm Path (C4-C5)",
                        "handoff_skill: dynamic-handoff",
                        "iteration_skill: ralph-loop-execute",
                        "stages:",
                        "  - id: plan",
                        "    agent: architecture-systems-architect",
                    ]
                ),
            )
            (repo / "configs/registry/skills").mkdir(parents=True, exist_ok=True)
            self._write(
                repo / "configs/registry/skills/ralph-loop-execute.yaml",
                "id: ralph-loop-execute\noutputs: [best_solution]\n",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "ok"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 2)
            self.assertIn("FAIL: Registry workflow binding invalid for C4", stderr.getvalue())

    def test_doctor_fails_when_handoff_contract_fields_do_not_match_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._build_min_repo(repo)
            self._write(
                repo / "configs/orchestrator/router.yaml",
                "\n".join(
                    [
                        "version: \"4.2\"",
                        "routing:",
                        "  tiers:",
                        "    C1:",
                        "      name: Simple",
                        "    C2:",
                        "      name: Simple",
                        "    C3:",
                        "      name: Standard",
                        "    C4:",
                        "      name: Advanced",
                        "      workflow: \"configs/registry/workflows/path-swarm.yaml\"",
                        "    C5:",
                        "      name: Advanced",
                        "  handoff_safeguards:",
                        "    require_contract: true",
                        "    contract_schema: \"configs/registry/schemas/task.schema.yaml\"",
                    ]
                ),
            )
            self._write(
                repo / "configs/registry/workflows/path-swarm.yaml",
                "\n".join(
                    [
                        "id: swarm-path-to-completion",
                        "name: Swarm Path (C4-C5)",
                        "handoff_skill: dynamic-handoff",
                        "iteration_skill: ralph-loop-execute",
                        "stages:",
                        "  - id: plan",
                        "    agent: architecture-systems-architect",
                    ]
                ),
            )
            self._write(
                repo / "configs/registry/schemas/task.schema.yaml",
                "\n".join(
                    [
                        "type: object",
                        "required: [objective, evidence, next_owner]",
                    ]
                ),
            )
            (repo / "configs/registry/skills").mkdir(parents=True, exist_ok=True)
            self._write(
                repo / "configs/registry/skills/dynamic-handoff.yaml",
                "id: dynamic-handoff\ncontract_fields: [objective]\n",
            )
            self._write(
                repo / "configs/registry/skills/ralph-loop-execute.yaml",
                "id: ralph-loop-execute\noutputs: [best_solution]\n",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl,
                "resolve_route_context",
                return_value={"route": {"primary_model": "google/gemini-2.0-flash-exp:free"}},
            ), patch.object(swarmctl, "build_skill_drift_report", return_value={"severity": "ok"}), patch.object(
                swarmctl, "build_workflow_model_alias_report", return_value={"severity": "ok"}
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                rc = swarmctl.cmd_doctor(SimpleNamespace())

            self.assertEqual(rc, 2)
            self.assertIn("missing required schema fields", stderr.getvalue())
            self.assertIn("evidence", stderr.getvalue())
            self.assertIn("next_owner", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
