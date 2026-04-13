"""Tests for AssetRegistry, LaneEvents, and RecoveryRecipes."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_os.registry import AssetRegistry
from agent_os.swarm.lane_events import (
    LaneEvent, write_lane_event, read_lane_events, ALLOWED_LANE_EVENT_TYPES
)
from agent_os.recovery.recipes import (
    classify_failure, plan_recovery, FailureType, RecoveryResult
)


# ---------------------------------------------------------------------------
# AssetRegistry
# ---------------------------------------------------------------------------

class TestAssetRegistry:
    def test_empty_catalog_on_missing_file(self, tmp_path):
        reg = AssetRegistry(tmp_path / "nonexistent.json")
        assert reg.catalog == {"skills": [], "rules": [], "workflows": [], "configs": []}

    def test_load_catalog_from_file(self, tmp_path):
        catalog = {"skills": [{"name": "routing-skill"}], "rules": [], "workflows": [], "configs": []}
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)
        assert len(reg.catalog["skills"]) == 1

    def test_find_rule_by_name(self, tmp_path):
        catalog = {"rules": [{"name": "WORKSPACE_STANDARD"}, {"name": "SECURITY_RULES"}], "skills": [], "workflows": [], "configs": []}
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)
        results = reg.find_rule("workspace")
        assert len(results) == 1
        assert results[0]["name"] == "WORKSPACE_STANDARD"

    def test_find_workflow_by_description(self, tmp_path):
        catalog = {
            "workflows": [
                {"name": "swarm-plan", "description": "multi-agent swarm planning"},
                {"name": "triage", "description": "issue triage workflow"},
            ],
            "skills": [], "rules": [], "configs": []
        }
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)
        results = reg.find_workflow("swarm")
        assert len(results) == 1
        assert results[0]["name"] == "swarm-plan"

    def test_find_skill_by_trigger(self, tmp_path):
        catalog = {
            "skills": [
                {"name": "routing-skill", "triggers": ["route", "dispatch"]},
                {"name": "memory-skill", "triggers": ["remember", "recall"]},
            ],
            "rules": [], "workflows": [], "configs": []
        }
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)
        results = reg.find_skill("recall")
        assert len(results) == 1
        assert results[0]["name"] == "memory-skill"

    def test_get_asset_by_name_cross_category(self, tmp_path):
        catalog = {
            "skills": [{"name": "brainstorming"}],
            "rules": [{"name": "ANTI_CHAOS"}],
            "workflows": [], "configs": []
        }
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)
        assert reg.get_asset_by_name("ANTI_CHAOS") is not None
        assert reg.get_asset_by_name("nonexistent") is None

    def test_register_asset_and_list(self, tmp_path):
        reg = AssetRegistry(tmp_path / "catalog.json")
        reg.register_asset("skills", {"name": "openclaude", "lane": "local"})
        reg.register_asset("skills", {"name": "memfree", "lane": "cloud"})
        skills = reg.list_by_category("skills")
        assert len(skills) == 2
        assert skills[0]["name"] == "openclaude"

    def test_save_and_reload_catalog(self, tmp_path):
        path = tmp_path / "catalog.json"
        reg1 = AssetRegistry(path)
        reg1.register_asset("rules", {"name": "NEW_RULE"})
        reg1.save_catalog()

        reg2 = AssetRegistry(path)
        assert len(reg2.list_by_category("rules")) == 1
        assert reg2.list_by_category("rules")[0]["name"] == "NEW_RULE"

    def test_corrupted_catalog_returns_empty(self, tmp_path):
        path = tmp_path / "catalog.json"
        path.write_text("not valid json {{{{")
        reg = AssetRegistry(path)
        assert reg.catalog == {"skills": [], "rules": [], "workflows": [], "configs": []}

    def test_context_pack_includes_doc_refs(self, tmp_path):
        catalog = {
            "skills": [],
            "rules": [],
            "workflows": [],
            "configs": [],
            "docs": [
                {
                    "name": "AGENT_HARNESS_MAP",
                    "title": "Agent Harness Map",
                    "path": "docs/ki/AGENT_HARNESS_MAP.md",
                    "status": "canonical",
                    "description": "Progressive disclosure map for routing validation observability and docs.",
                }
            ],
        }
        path = tmp_path / "catalog.json"
        path.write_text(json.dumps(catalog))
        reg = AssetRegistry(path)

        pack = reg.generate_context_pack("harness validation observability")

        assert "doc_refs" in pack
        assert pack["doc_refs"][0]["name"] == "AGENT_HARNESS_MAP"
        assert pack["doc_refs"][0]["status"] == "canonical"


# ---------------------------------------------------------------------------
# LaneEvents
# ---------------------------------------------------------------------------

class TestLaneEvents:
    def test_create_valid_event(self):
        event = LaneEvent(task_id="t1", lane_id="lane-0", event_type="Started")
        assert event.task_id == "t1"
        assert event.event_type == "Started"
        assert event.ts  # auto-generated

    def test_invalid_event_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            LaneEvent(task_id="t1", lane_id="lane-0", event_type="InvalidType")

    def test_all_allowed_types_valid(self):
        for event_type in ALLOWED_LANE_EVENT_TYPES:
            e = LaneEvent(task_id="t", lane_id="l", event_type=event_type)
            assert e.event_type == event_type

    def test_write_and_read_events(self, tmp_path):
        path = tmp_path / "events.jsonl"
        e1 = LaneEvent(task_id="t1", lane_id="lane-0", event_type="Started", payload={"model": "qwen"})
        e2 = LaneEvent(task_id="t1", lane_id="lane-0", event_type="Finished", payload={"tokens": 100})
        write_lane_event(path, e1)
        write_lane_event(path, e2)

        events = read_lane_events(path)
        assert len(events) == 2
        assert events[0].event_type == "Started"
        assert events[1].event_type == "Finished"
        assert events[0].payload["model"] == "qwen"

    def test_read_empty_file_returns_empty(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        assert read_lane_events(path) == []

    def test_to_dict_structure(self):
        e = LaneEvent(task_id="t1", lane_id="l1", event_type="Blocked", payload={"reason": "lock"})
        d = e.to_dict()
        assert set(d.keys()) == {"task_id", "lane_id", "event_type", "payload", "ts"}

    def test_write_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "events.jsonl"
        e = LaneEvent(task_id="t1", lane_id="l1", event_type="Started")
        write_lane_event(path, e)
        assert path.exists()


# ---------------------------------------------------------------------------
# RecoveryRecipes
# ---------------------------------------------------------------------------

class TestClassifyFailure:
    def test_stdio_json(self):
        assert classify_failure("non-json response from stdio") == FailureType.STDIO_JSON_FAILURE

    def test_mcp_handshake(self):
        assert classify_failure("MCP handshake failed") == FailureType.MCP_HANDSHAKE

    def test_stale_branch(self):
        assert classify_failure("stale branch behind main") == FailureType.STALE_BRANCH

    def test_compile_failure(self):
        assert classify_failure("typecheck failed: 3 errors") == FailureType.COMPILE_FAILURE

    def test_test_failure(self):
        assert classify_failure("pytest: 5 tests failed") == FailureType.TEST_FAILURE

    def test_plugin_startup(self):
        assert classify_failure("plugin startup error") == FailureType.PLUGIN_STARTUP

    def test_provider_startup(self):
        assert classify_failure("binary not found: ollama") == FailureType.PROVIDER_STARTUP

    def test_unknown(self):
        assert classify_failure("something completely unexpected") == FailureType.UNKNOWN

    def test_empty_message(self):
        assert classify_failure("") == FailureType.UNKNOWN


class TestPlanRecovery:
    def test_returns_recovery_result(self):
        result = plan_recovery(
            FailureType.TEST_FAILURE,
            run_id="run-123",
            runtime_provider="zeroclaw",
            message="5 tests failed",
        )
        assert isinstance(result, RecoveryResult)
        assert result.failure_type == FailureType.TEST_FAILURE
        assert result.attempted is True
        assert result.recovered is False
        assert result.degraded_mode is False
        assert result.next_action

    def test_event_payload_structure(self):
        result = plan_recovery(
            FailureType.COMPILE_FAILURE,
            run_id="run-456",
            runtime_provider="agent-os",
            message="typecheck error",
        )
        p = result.event_payload
        assert p["run_id"] == "run-456"
        assert p["component"] == "recovery"
        assert p["data"]["failure_type"] == "compile_failure"
        assert p["data"]["degraded_mode"] is False

    def test_string_failure_type_accepted(self):
        result = plan_recovery(
            "test_failure",
            run_id="r1",
            runtime_provider="p1",
            message="tests red",
        )
        assert result.failure_type == FailureType.TEST_FAILURE
        assert result.degraded_mode is False

    def test_unknown_string_falls_back(self):
        result = plan_recovery(
            "totally_unknown_type",
            run_id="r1",
            runtime_provider="p1",
            message="???",
        )
        assert result.failure_type == FailureType.UNKNOWN

    def test_all_failure_types_have_next_action(self):
        for ft in FailureType:
            result = plan_recovery(ft, run_id="r", runtime_provider="p", message="err")
            assert result.next_action

    def test_degraded_mode_failure_types(self):
        for ft in (FailureType.STDIO_JSON_FAILURE, FailureType.MCP_HANDSHAKE, FailureType.PLUGIN_STARTUP):
            result = plan_recovery(ft, run_id="r", runtime_provider="p", message="err")
            assert result.degraded_mode is True
