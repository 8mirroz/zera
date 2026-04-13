"""Tests for RiskClassifier multi-match and ObservabilityEmitter."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_os.risk_classifier import RiskClassifier, RiskAssessment
from agent_os.observability import emit_event, emit_events


class TestRiskClassifierMultiMatch:
    def setup_method(self):
        self.clf = RiskClassifier()

    def test_single_class_financial(self):
        r = self.clf.classify("buy tokens")
        assert r.risk_class == "financial"
        assert not r.requires_gate

    def test_single_class_destructive(self):
        r = self.clf.classify("delete all files")
        assert r.risk_class == "destructive"

    def test_multi_match_reason_includes_secondary(self):
        # "delete" (destructive) + "publish" (irreversible)
        r = self.clf.classify("delete and publish")
        assert "also:" in r.reason

    def test_gate_check_uses_all_matched_classes(self):
        # action matches "destructive", gate is "irreversible" — no gate
        r = self.clf.classify("delete files", approval_gates=["irreversible"])
        assert not r.requires_gate

        # action matches "destructive", gate includes "destructive" — gate required
        r2 = self.clf.classify("delete files", approval_gates=["destructive"])
        assert r2.requires_gate

    def test_low_risk_action(self):
        r = self.clf.classify("read config")
        assert r.risk_class == "low_risk"
        assert not r.requires_gate

    def test_unknown_action_type(self):
        r = self.clf.classify("")
        assert r.action_type == "unknown"

    def test_to_dict_structure(self):
        r = self.clf.classify("deploy service")
        d = r.to_dict()
        assert set(d.keys()) == {"action_type", "risk_class", "requires_gate", "reason"}


class TestEmitEvents:
    def test_emit_events_preserves_event_type(self, tmp_path):
        trace_file = tmp_path / "traces.jsonl"
        os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
        try:
            emit_events([
                {"event_type": "tool_call", "tool_name": "pytest", "status": "ok"},
                {"event_type": "route_decision", "complexity": "C3"},
            ])
            lines = trace_file.read_text().strip().splitlines()
            assert len(lines) == 2
            row0 = json.loads(lines[0])
            row1 = json.loads(lines[1])
            assert row0["event_type"] == "tool_call"
            assert row1["event_type"] == "route_decision"
        finally:
            del os.environ["AGENT_OS_TRACE_FILE"]

    def test_emit_event_component_inference(self, tmp_path):
        trace_file = tmp_path / "traces.jsonl"
        os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
        try:
            emit_event("memory_write", {"content": "test"})
            row = json.loads(trace_file.read_text().strip())
            assert row["component"] == "memory"
            assert row["event_type"] == "memory_write"
        finally:
            del os.environ["AGENT_OS_TRACE_FILE"]

    def test_emit_event_run_id_generated(self, tmp_path):
        trace_file = tmp_path / "traces.jsonl"
        os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
        try:
            emit_event("agent_start", {})
            row = json.loads(trace_file.read_text().strip())
            assert row["run_id"]
            assert row["ts"]
        finally:
            del os.environ["AGENT_OS_TRACE_FILE"]
