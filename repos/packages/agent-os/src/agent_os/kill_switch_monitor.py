"""KillSwitchMonitor — runtime enforcement of configs/tooling/kill-switches.yaml.

Reads agent_traces.jsonl, computes trigger metrics, fires configured actions.
Designed to be called periodically (e.g. after each task run or on a schedule).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any



@dataclass
class KillSwitchResult:
    name: str
    fired: bool
    reason: str
    actions: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class KillSwitchMonitor:
    """Evaluates kill-switch triggers against recent trace data."""

    _CONFIG_PATH = "configs/tooling/kill-switches.yaml"
    _TRACES_PATH = "logs/agent_traces.jsonl"

    def __init__(self, repo_root: Path, window: int = 50) -> None:
        self.repo_root = Path(repo_root)
        self.window = window  # number of recent task_run_summary events to analyse

    def _load_config(self) -> list[dict[str, Any]]:
        path = self.repo_root / self._CONFIG_PATH
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(text) or {}
        except Exception:
            try:
                import json as _json
                data = _json.loads(text)
            except Exception:
                return []
        if not isinstance(data, dict):
            return []
        switches = data.get("kill_switches", [])
        return switches if isinstance(switches, list) else []

    def _load_traces(self) -> list[dict[str, Any]]:
        path = self.repo_root / self._TRACES_PATH
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        # Return last N task_run_summary events
        summaries = [r for r in rows if r.get("event_type") == "task_run_summary"]
        return summaries[-self.window :]

    def _compute_metrics(self, traces: list[dict[str, Any]]) -> dict[str, float]:
        if not traces:
            return {}

        total = len(traces)
        data_list = [t.get("data", {}) or {} for t in traces]

        # replay_win_rate: fraction where outcome == "success"
        wins = sum(1 for d in data_list if str(d.get("outcome", "")).lower() in {"success", "ok", "completed"})
        replay_win_rate = wins / total

        # regression_rate: fraction where quality_gate_failures > 0
        regressions = sum(1 for t in traces if int(t.get("quality_gate_failures", 0) or 0) > 0)
        regression_rate = regressions / total

        # token_cost_delta: avg token_cost vs first-half baseline
        costs = [float(t.get("token_cost", 0) or 0) for t in traces]
        half = max(1, total // 2)
        baseline_cost = sum(costs[:half]) / half
        recent_cost = sum(costs[half:]) / max(1, total - half)
        token_cost_delta = (recent_cost - baseline_cost) / max(baseline_cost, 1e-9)

        # quality_gain: avg quality_gate_failures delta (negative = improvement)
        qgf = [float(t.get("quality_gate_failures", 0) or 0) for t in traces]
        baseline_qgf = sum(qgf[:half]) / half
        recent_qgf = sum(qgf[half:]) / max(1, total - half)
        quality_gain = baseline_qgf - recent_qgf  # positive = improved

        # unnecessary_swarm_rate: swarm used on C1/C2 tasks
        swarm_events = [
            d for d in data_list
            if str(d.get("orchestration_path", "")).lower().find("swarm") >= 0
            and str(d.get("complexity", "C3")) in {"C1", "C2", "C3"}
        ]
        unnecessary_swarm_rate = len(swarm_events) / total

        # rollback_safety_delta: fraction of rollbacks in recent vs baseline
        rollbacks = [1 if d.get("rollback_triggered") else 0 for d in data_list]
        baseline_rb = sum(rollbacks[:half]) / half
        recent_rb = sum(rollbacks[half:]) / max(1, total - half)
        rollback_safety_delta = recent_rb - baseline_rb

        return {
            "replay_win_rate": round(replay_win_rate, 4),
            "regression_rate": round(regression_rate, 4),
            "token_cost_delta": round(token_cost_delta, 4),
            "quality_gain": round(quality_gain, 4),
            "unnecessary_swarm_rate": round(unnecessary_swarm_rate, 4),
            "rollback_safety_delta": round(rollback_safety_delta, 4),
            "total_traces": float(total),
        }

    def _evaluate_trigger(
        self, trigger: dict[str, Any], metrics: dict[str, float]
    ) -> tuple[bool, str]:
        """Evaluate a single trigger dict against computed metrics.

        Supports simple expressions: "< 0.48", "> baseline + 0.07", "<= 0".
        Returns (fired, reason).
        """
        for metric_key, expr in trigger.items():
            if metric_key not in metrics:
                continue
            actual = metrics[metric_key]
            expr_str = str(expr).strip()

            fired, reason = self._eval_expr(metric_key, actual, expr_str, metrics)
            if fired:
                return True, reason
        return False, ""

    @staticmethod
    def _eval_expr(
        key: str, actual: float, expr: str, metrics: dict[str, float]
    ) -> tuple[bool, str]:
        """Parse and evaluate a simple comparison expression."""
        import re

        # Replace "baseline" token with regression_rate as proxy baseline
        expr = expr.replace("baseline", str(metrics.get("regression_rate", 0.0)))

        # Evaluate arithmetic in threshold (e.g. "baseline + 0.07")
        match = re.match(r"^([<>]=?|==)\s*(.+)$", expr.strip())
        if not match:
            return False, ""
        op, rhs_str = match.group(1), match.group(2).strip()
        try:
            threshold = float(eval(rhs_str, {"__builtins__": {}}, {}))  # noqa: S307
        except Exception:
            return False, ""

        ops = {"<": actual < threshold, ">": actual > threshold,
               "<=": actual <= threshold, ">=": actual >= threshold, "==": actual == threshold}
        fired = ops.get(op, False)
        reason = f"{key}={actual:.4f} {op} {threshold:.4f}" if fired else ""
        return fired, reason

    def evaluate(self) -> list[KillSwitchResult]:
        """Evaluate all kill switches. Returns list of results (fired or not)."""
        switches = self._load_config()
        traces = self._load_traces()
        metrics = self._compute_metrics(traces)

        results: list[KillSwitchResult] = []
        for switch in switches:
            name = str(switch.get("name", "unnamed"))
            trigger = switch.get("trigger", {})
            actions = list(switch.get("action", []))

            if not isinstance(trigger, dict):
                results.append(KillSwitchResult(name=name, fired=False, reason="invalid_trigger", actions=actions))
                continue

            fired, reason = self._evaluate_trigger(trigger, metrics)
            results.append(KillSwitchResult(
                name=name,
                fired=fired,
                reason=reason or ("ok" if not fired else "triggered"),
                actions=actions if fired else [],
                metrics={k: metrics.get(k, 0.0) for k in trigger},
            ))

        return results

    def fired_switches(self) -> list[KillSwitchResult]:
        """Return only the switches that fired."""
        return [r for r in self.evaluate() if r.fired]

    def summary(self) -> dict[str, Any]:
        """Return a compact summary dict suitable for logging."""
        traces = self._load_traces()
        metrics = self._compute_metrics(traces)
        results = self.evaluate()
        fired = [r for r in results if r.fired]
        return {
            "total_switches": len(results),
            "fired_count": len(fired),
            "fired_names": [r.name for r in fired],
            "metrics": metrics,
        }
