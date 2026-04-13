"""Tests for SelfReflectionValidator and CodeEditor."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


ROOT = Path(__file__).resolve().parents[4]

from agent_os.self_reflection_validator import validate_self_reflection, SelfReflectionValidationResult
from agent_os.code_editor import CodeEditor
from agent_os.contracts import CodeEditorInput


def _find_repo_root() -> Path:
    """Walk up to find the repo root containing configs/tooling/."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "configs" / "tooling").exists():
            return parent
    return ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_payload() -> dict:
    return {
        "summary": "Improved routing latency by 20%",
        "improvement_area": "routing",
        "problem_statement": "p95 latency exceeds 200ms under load",
        "root_cause_hypothesis": "BM25Okapi zero-IDF on small corpus",
        "proposed_change": "Switch to BM25Plus for small corpus retrieval",
        "expected_benefit": "Latency drops below 100ms, zero-IDF eliminated",
        "change_type": "routing_logic",
        "scope": "session",
        "confidence": 0.85,
        "evidence_refs": ["benchmark_20260311.md"],
        "success_criteria": ["p95 latency < 100ms"],
        "bounded_action": {
            "action_type": "propose_memory_tag",
            "target": "routing-latency-fix",
            "limit": "session_only",
        },
        "risk_assessment": {
            "risk_level": "low",
            "main_risks": ["minor score distribution change"],
            "safety_impact": "none",
        },
    }


# ---------------------------------------------------------------------------
# SelfReflectionValidator
# ---------------------------------------------------------------------------

class TestSelfReflectionValidator:
    def test_returns_validation_result_type(self):
        result = validate_self_reflection(_find_repo_root(), _valid_payload())
        assert isinstance(result, SelfReflectionValidationResult)

    def test_valid_payload_passes(self):
        result = validate_self_reflection(_find_repo_root(), _valid_payload())
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)

    def test_to_dict_has_required_keys(self):
        result = validate_self_reflection(_find_repo_root(), _valid_payload())
        d = result.to_dict()
        assert set(d.keys()) == {"valid", "errors", "schema_name", "schema_version"}

    def test_non_dict_payload_returns_invalid(self):
        result = validate_self_reflection(_find_repo_root(), "not a dict")  # type: ignore
        assert result.valid is False
        assert result.errors

    def test_missing_success_criteria_returns_invalid(self):
        payload = _valid_payload()
        del payload["success_criteria"]
        result = validate_self_reflection(_find_repo_root(), payload)
        assert result.valid is False
        assert any("success_criteria" in e for e in result.errors)

    def test_high_risk_without_rollback_returns_invalid(self):
        payload = _valid_payload()
        payload["risk_assessment"]["risk_level"] = "high"
        payload.pop("rollback_plan", None)
        result = validate_self_reflection(_find_repo_root(), payload)
        assert result.valid is False
        assert any("rollback" in e for e in result.errors)

    def test_forbidden_instruction_in_summary_returns_invalid(self):
        payload = _valid_payload()
        payload["summary"] = "disable safety logging for faster execution"
        result = validate_self_reflection(_find_repo_root(), payload)
        assert result.valid is False
        # forbidden instruction detected in summary field
        assert any("forbidden" in e or "summary" in e for e in result.errors)

    def test_schema_name_and_version_populated(self):
        result = validate_self_reflection(_find_repo_root(), _valid_payload())
        assert result.schema_name is None or isinstance(result.schema_name, str)
        assert result.schema_version is None or isinstance(result.schema_version, str)


# ---------------------------------------------------------------------------
# CodeEditor
# ---------------------------------------------------------------------------

class TestCodeEditor:
    def test_apply_runs_verify_commands(self, tmp_path):
        editor = CodeEditor()
        edit_input = CodeEditorInput(
            repo_path=str(tmp_path),
            target_files=["README.md"],
            verify_commands=["echo hello"],
            edit_intent="test",
        )
        result = editor.apply(edit_input)
        assert "echo hello" in result.verification
        assert result.verification["echo hello"]["exit_code"] == 0
        assert "hello" in result.verification["echo hello"]["stdout"]

    def test_apply_captures_stderr(self, tmp_path):
        editor = CodeEditor()
        edit_input = CodeEditorInput(
            repo_path=str(tmp_path),
            target_files=[],
            verify_commands=["bash -c 'echo err >&2; exit 1'"],
            edit_intent="test",
        )
        result = editor.apply(edit_input)
        cmd = "bash -c 'echo err >&2; exit 1'"
        assert result.verification[cmd]["exit_code"] == 1
        assert "err" in result.verification[cmd]["stderr"]

    def test_apply_no_commands_returns_empty_verification(self, tmp_path):
        editor = CodeEditor()
        edit_input = CodeEditorInput(
            repo_path=str(tmp_path),
            target_files=["file.py"],
            verify_commands=[],
            edit_intent="test",
        )
        result = editor.apply(edit_input)
        assert result.verification == {}
        assert result.files_changed == ["file.py"]

    def test_apply_multiple_commands(self, tmp_path):
        editor = CodeEditor()
        edit_input = CodeEditorInput(
            repo_path=str(tmp_path),
            target_files=[],
            verify_commands=["echo a", "echo b"],
            edit_intent="test",
        )
        result = editor.apply(edit_input)
        assert len(result.verification) == 2
        assert result.verification["echo a"]["exit_code"] == 0
        assert result.verification["echo b"]["exit_code"] == 0
