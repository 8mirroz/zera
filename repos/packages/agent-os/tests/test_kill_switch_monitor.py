"""Tests for KillSwitchMonitor."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.kill_switch_monitor import KillSwitchMonitor, KillSwitchResult


def _make_repo(tmp_path: Path, switches: list[dict], traces: list[dict]) -> Path:
    """Scaffold a minimal repo with kill-switches config and traces."""
    (tmp_path / "configs/tooling").mkdir(parents=True)
    (tmp_path / "logs").mkdir(parents=True)

    ks_yaml = "version: '2026-03-11'\nkill_switches:\n"
    for sw in switches:
        ks_yaml += f"  - name: {sw['name']}\n"
        ks_yaml += "    trigger:\n"
        for k, v in sw["trigger"].items():
            ks_yaml += f"      {k}: \"{v}\"\n"
        ks_yaml += "    action:\n"
        for a in sw.get("action", []):
            ks_yaml += f"      - {a}\n"

    (tmp_path / "configs/tooling/kill-switches.yaml").write_text(ks_yaml)

    trace_lines = "\n".join(json.dumps(t) for t in traces)
    (tmp_path / "logs/agent_traces.jsonl").write_text(trace_lines)

    return tmp_path


def _summary_trace(outcome: str = "success", qgf: int = 0, path: str = "Quality Path",
                   complexity: str = "C3", token_cost: float = 1.0) -> dict:
    return {
        "event_type": "task_run_summary",
        "quality_gate_failures": qgf,
        "token_cost": token_cost,
        "data": {
            "outcome": outcome,
            "orchestration_path": path,
            "complexity": complexity,
        },
    }


class TestKillSwitchMonitorMetrics:
    def test_empty_traces_returns_empty_metrics(self, tmp_path):
        repo = _make_repo(tmp_path, [], [])
        mon = KillSwitchMonitor(repo)
        traces = mon._load_traces()
        metrics = mon._compute_metrics(traces)
        assert metrics == {}

    def test_replay_win_rate_all_success(self, tmp_path):
        traces = [_summary_trace("success")] * 10
        repo = _make_repo(tmp_path, [], traces)
        mon = KillSwitchMonitor(repo)
        metrics = mon._compute_metrics(mon._load_traces())
        assert metrics["replay_win_rate"] == 1.0

    def test_replay_win_rate_all_failure(self, tmp_path):
        traces = [_summary_trace("failed")] * 10
        repo = _make_repo(tmp_path, [], traces)
        mon = KillSwitchMonitor(repo)
        metrics = mon._compute_metrics(mon._load_traces())
        assert metrics["replay_win_rate"] == 0.0

    def test_unnecessary_swarm_rate(self, tmp_path):
        traces = [_summary_trace(path="swarm", complexity="C2")] * 4 + \
                 [_summary_trace(path="Quality Path", complexity="C3")] * 6
        repo = _make_repo(tmp_path, [], traces)
        mon = KillSwitchMonitor(repo)
        metrics = mon._compute_metrics(mon._load_traces())
        assert metrics["unnecessary_swarm_rate"] == pytest.approx(0.4, abs=0.01)

    def test_regression_rate(self, tmp_path):
        traces = [_summary_trace(qgf=1)] * 3 + [_summary_trace(qgf=0)] * 7
        repo = _make_repo(tmp_path, [], traces)
        mon = KillSwitchMonitor(repo)
        metrics = mon._compute_metrics(mon._load_traces())
        assert metrics["regression_rate"] == pytest.approx(0.3, abs=0.01)


class TestKillSwitchTriggers:
    def test_switch_fires_on_low_win_rate(self, tmp_path):
        switches = [{"name": "low_win_rate", "trigger": {"replay_win_rate": "< 0.48"}, "action": ["disable_policy"]}]
        traces = [_summary_trace("failed")] * 10
        repo = _make_repo(tmp_path, switches, traces)
        mon = KillSwitchMonitor(repo)
        fired = mon.fired_switches()
        assert len(fired) == 1
        assert fired[0].name == "low_win_rate"
        assert "disable_policy" in fired[0].actions

    def test_switch_does_not_fire_on_high_win_rate(self, tmp_path):
        switches = [{"name": "low_win_rate", "trigger": {"replay_win_rate": "< 0.48"}, "action": ["disable_policy"]}]
        traces = [_summary_trace("success")] * 10
        repo = _make_repo(tmp_path, switches, traces)
        mon = KillSwitchMonitor(repo)
        fired = mon.fired_switches()
        assert fired == []

    def test_swarm_switch_fires(self, tmp_path):
        switches = [{"name": "swarm_overuse", "trigger": {"unnecessary_swarm_rate": "> 0.20"}, "action": ["revert_to_single_agent_default"]}]
        traces = [_summary_trace(path="swarm", complexity="C2")] * 8 + [_summary_trace()] * 2
        repo = _make_repo(tmp_path, switches, traces)
        mon = KillSwitchMonitor(repo)
        fired = mon.fired_switches()
        assert len(fired) == 1
        assert fired[0].name == "swarm_overuse"

    def test_no_config_returns_empty(self, tmp_path):
        (tmp_path / "configs/tooling").mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        mon = KillSwitchMonitor(tmp_path)
        assert mon.evaluate() == []

    def test_summary_structure(self, tmp_path):
        switches = [{"name": "test_sw", "trigger": {"replay_win_rate": "< 0.5"}, "action": ["mark_for_review"]}]
        traces = [_summary_trace("failed")] * 5
        repo = _make_repo(tmp_path, switches, traces)
        mon = KillSwitchMonitor(repo)
        s = mon.summary()
        assert "fired_count" in s
        assert "metrics" in s
        assert "fired_names" in s

    def test_multiple_switches_partial_fire(self, tmp_path):
        switches = [
            {"name": "win_rate_check", "trigger": {"replay_win_rate": "< 0.48"}, "action": ["disable_policy"]},
            {"name": "swarm_check", "trigger": {"unnecessary_swarm_rate": ">= 0.20"}, "action": ["revert_to_single_agent_default"]},
        ]
        # win rate ok (1.0), swarm rate exactly at threshold (0.20)
        traces = [_summary_trace("success")] * 8 + \
                 [_summary_trace(path="swarm", complexity="C2", outcome="success")] * 2
        repo = _make_repo(tmp_path, switches, traces)
        mon = KillSwitchMonitor(repo)
        results = mon.evaluate()
        fired = [r for r in results if r.fired]
        not_fired = [r for r in results if not r.fired]
        assert len(fired) == 1
        assert fired[0].name == "swarm_check"
        assert len(not_fired) == 1
        assert not_fired[0].name == "win_rate_check"
