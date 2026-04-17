"""Tests for AutoUpdateEngine."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.auto_update_engine import AutoUpdateEngine, AutoUpdateReport


def _trace(outcome: str = "success", qgf: int = 0, path: str = "Quality Path",
           complexity: str = "C3", token_cost: float = 1.0, confidence: float = 0.0) -> dict:
    return {
        "event_type": "task_run_summary",
        "quality_gate_failures": qgf,
        "token_cost": token_cost,
        "data": {
            "outcome": outcome,
            "orchestration_path": path,
            "complexity": complexity,
            "confidence": confidence,
        },
    }


def _make_repo(tmp_path: Path, traces: list[dict], memory_entries: list[dict] | None = None) -> Path:
    (tmp_path / "configs/tooling").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)
    (tmp_path / ".agents/memory").mkdir(parents=True)

    # kill-switches config
    (tmp_path / "configs/tooling/kill-switches.yaml").write_text(
        "version: '2026-03-11'\nkill_switches:\n"
        "  - name: low_win_rate\n    trigger:\n      replay_win_rate: \"< 0.48\"\n"
        "    action:\n      - disable_policy\n"
    )

    # traces
    (tmp_path / "logs/agent_traces.jsonl").write_text(
        "\n".join(json.dumps(t) for t in traces)
    )

    # memory
    if memory_entries is not None:
        (tmp_path / ".agents/memory/memory.jsonl").write_text(
            "\n".join(json.dumps(e) for e in memory_entries)
        )

    return tmp_path


class TestAutoUpdateEngineBasic:
    def test_run_returns_report(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 10)
        engine = AutoUpdateEngine(repo)
        report = engine.run()
        assert isinstance(report, AutoUpdateReport)
        assert report.run_id
        assert report.ts

    def test_report_written_to_jsonl(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 5)
        engine = AutoUpdateEngine(repo)
        engine.run()
        report_path = repo / "logs/auto_update_report.jsonl"
        assert report_path.exists()
        lines = [l for l in report_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        data = json.loads(lines[0])
        assert "run_id" in data
        assert "actions_taken" in data

    def test_empty_traces_no_crash(self, tmp_path):
        repo = _make_repo(tmp_path, [])
        engine = AutoUpdateEngine(repo)
        report = engine.run()
        assert report is not None
        assert report.drift_signals == []

    def test_report_to_dict_structure(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 5)
        engine = AutoUpdateEngine(repo)
        report = engine.run()
        d = report.to_dict()
        for key in ["run_id", "ts", "kill_switches_fired", "drift_signals_fired",
                    "actions_taken", "blocked_by_kill_switch"]:
            assert key in d


class TestDriftDetection:
    def test_no_drift_on_healthy_traces(self, tmp_path):
        traces = [_trace("success")] * 20
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        traces_loaded = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces_loaded)
        signals = engine._run_drift_detection(metrics)
        fired = [s for s in signals if s.fired]
        assert fired == []

    def test_strategy_success_rate_drop_fires(self, tmp_path):
        traces = [_trace("failed")] * 20
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        traces_loaded = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces_loaded)
        signals = engine._run_drift_detection(metrics)
        names = [s.name for s in signals if s.fired]
        assert "strategy_success_rate_drop" in names

    def test_swarm_drift_fires(self, tmp_path):
        traces = [_trace(path="swarm", complexity="C2")] * 15 + [_trace()] * 5
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        traces_loaded = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces_loaded)
        signals = engine._run_drift_detection(metrics)
        names = [s.name for s in signals if s.fired]
        assert "premature_swarm_increase" in names

    def test_drift_response_populated(self, tmp_path):
        traces = [_trace("failed")] * 20
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        traces_loaded = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces_loaded)
        signals = engine._run_drift_detection(metrics)
        for s in signals:
            if s.fired:
                assert len(s.response) > 0


class TestRitualPruning:
    def test_returns_verdicts(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 10)
        engine = AutoUpdateEngine(repo)
        traces = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces)
        verdicts = engine._run_ritual_pruning(metrics)
        assert len(verdicts) >= 1

    def test_verdict_values_valid(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 10)
        engine = AutoUpdateEngine(repo)
        traces = engine._load_traces()
        metrics = engine._ks_monitor._compute_metrics(traces)
        verdicts = engine._run_ritual_pruning(metrics)
        valid = {"keep", "make_conditional", "disable_for_low_risk_tasks"}
        for v in verdicts:
            assert v.verdict in valid

    def test_ritual_verdict_logic(self):
        # High activation, low decision change, low quality gain → disable
        assert AutoUpdateEngine._ritual_verdict(0.8, 0.05, 0.01) == "disable_for_low_risk_tasks"
        # Medium activation, medium decision change → conditional
        assert AutoUpdateEngine._ritual_verdict(0.4, 0.15, 0.04) == "make_conditional"
        # Low activation → keep
        assert AutoUpdateEngine._ritual_verdict(0.2, 0.5, 0.1) == "keep"


class TestMemoryEval:
    def test_no_memory_file_returns_none(self, tmp_path):
        repo = _make_repo(tmp_path, [_trace()] * 5, memory_entries=None)
        engine = AutoUpdateEngine(repo)
        result = engine._run_memory_eval([])
        assert result is None

    def test_empty_memory_returns_ok(self, tmp_path):
        repo = _make_repo(tmp_path, [], memory_entries=[])
        engine = AutoUpdateEngine(repo)
        result = engine._run_memory_eval([])
        assert result is not None
        assert result.total_entries == 0
        assert result.action == "ok"

    def test_fresh_entries_ok(self, tmp_path):
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc).isoformat()
        entries = [{"content": f"entry {i}", "created_at": now} for i in range(10)]
        repo = _make_repo(tmp_path, [], memory_entries=entries)
        engine = AutoUpdateEngine(repo)
        result = engine._run_memory_eval([])
        assert result is not None
        assert result.stale_count == 0
        assert result.action == "ok"

    def test_duplicate_detection(self, tmp_path):
        entries = [{"content": "same content here", "id": str(i)} for i in range(5)]
        repo = _make_repo(tmp_path, [], memory_entries=entries)
        engine = AutoUpdateEngine(repo)
        result = engine._run_memory_eval([])
        assert result is not None
        assert result.duplicate_count >= 4  # 5 entries, 4 are duplicates


class TestConfidenceCalibration:
    def test_no_traces_returns_none(self, tmp_path):
        repo = _make_repo(tmp_path, [])
        engine = AutoUpdateEngine(repo)
        result = engine._run_confidence_calibration([])
        assert result is None

    def test_well_calibrated_is_ok(self, tmp_path):
        # confidence matches outcome
        traces = [
            _trace("success", confidence=0.9),
            _trace("success", confidence=0.85),
            _trace("failed", confidence=0.1),
            _trace("failed", confidence=0.15),
        ]
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        result = engine._run_confidence_calibration(traces)
        assert result is not None
        assert result.status in {"ok", "warn"}

    def test_ece_bounded(self, tmp_path):
        traces = [_trace("success", confidence=0.5)] * 10
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        result = engine._run_confidence_calibration(traces)
        assert result is not None
        assert 0.0 <= result.ece <= 1.0


class TestKillSwitchIntegration:
    def test_kill_switch_fires_in_full_run(self, tmp_path):
        traces = [_trace("failed")] * 20
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        report = engine.run()
        assert "low_win_rate" in report.to_dict()["kill_switches_fired"]

    def test_actions_include_kill_switch_response(self, tmp_path):
        traces = [_trace("failed")] * 20
        repo = _make_repo(tmp_path, traces)
        engine = AutoUpdateEngine(repo)
        report = engine.run()
        # drift actions should be present (strategy_success_rate_drop fires too)
        assert len(report.actions_taken) > 0
