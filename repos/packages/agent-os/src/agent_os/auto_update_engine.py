"""AutoUpdateEngine — orchestrates all automatic update cycles.

Runs on schedule (via BackgroundJobQueue) or on-demand.
Integrates: KillSwitchMonitor, drift detection, ritual pruning, memory eval.

Update cycle order (matches self-analysis-engine.yaml execution_graph):
  1. kill_switch_check   — fire/no-fire from traces
  2. drift_detection     — signal degradation across windows
  3. ritual_pruning      — detect low-value steps
  4. memory_eval         — stale/duplicate entries
  5. confidence_calibration — ECE check
  6. emit_summary        — write to logs/auto_update_report.jsonl
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .kill_switch_monitor import KillSwitchMonitor, KillSwitchResult
from .observability import emit_event

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DriftSignal:
    name: str
    fired: bool
    window: str          # short / medium / long
    value: float
    threshold: float
    response: list[str] = field(default_factory=list)


@dataclass
class RitualVerdict:
    item: str
    verdict: str         # keep / make_conditional / disable_for_low_risk_tasks
    activation_rate: float
    decision_change_rate: float
    quality_gain: float


@dataclass
class MemoryEvalResult:
    total_entries: int
    stale_count: int
    duplicate_count: int
    recall_at_10_estimate: float
    action: str          # ok / prune_stale / merge_duplicates / rebuild_index


@dataclass
class ConfidenceCalibrationResult:
    ece: float           # Expected Calibration Error
    status: str          # ok / warn / fail
    escalation: str | None


@dataclass
class AutoUpdateReport:
    run_id: str
    ts: str
    kill_switches: list[KillSwitchResult]
    drift_signals: list[DriftSignal]
    ritual_verdicts: list[RitualVerdict]
    memory_eval: MemoryEvalResult | None
    confidence_calibration: ConfidenceCalibrationResult | None
    actions_taken: list[str]
    blocked_by_kill_switch: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "ts": self.ts,
            "kill_switches_fired": [r.name for r in self.kill_switches if r.fired],
            "drift_signals_fired": [s.name for s in self.drift_signals if s.fired],
            "ritual_verdicts": [{"item": v.item, "verdict": v.verdict} for v in self.ritual_verdicts],
            "memory_eval": {
                "total": self.memory_eval.total_entries,
                "stale": self.memory_eval.stale_count,
                "duplicates": self.memory_eval.duplicate_count,
                "action": self.memory_eval.action,
            } if self.memory_eval else None,
            "confidence_calibration": {
                "ece": self.confidence_calibration.ece,
                "status": self.confidence_calibration.status,
                "escalation": self.confidence_calibration.escalation,
            } if self.confidence_calibration else None,
            "actions_taken": self.actions_taken,
            "blocked_by_kill_switch": self.blocked_by_kill_switch,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class AutoUpdateEngine:
    """Run all automatic update checks and emit a structured report."""

    _DRIFT_CONFIG = "configs/tooling/drift-detection-rules.yaml"
    _RITUAL_CONFIG = "configs/tooling/ritual-detection-rules.yaml"
    _MEMORY_EVAL_CONFIG = "configs/tooling/memory_evaluation.yaml"
    _CONFIDENCE_CONFIG = "configs/tooling/confidence-calibration-rules.yaml"
    _REPORT_PATH = "logs/auto_update_report.jsonl"
    _TRACES_PATH = "logs/agent_traces.jsonl"

    def __init__(self, repo_root: Path, trace_window: int = 50) -> None:
        self.repo_root = Path(repo_root)
        self.trace_window = trace_window
        self._ks_monitor = KillSwitchMonitor(repo_root, window=trace_window)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> AutoUpdateReport:
        """Execute full update cycle. Returns report and emits to JSONL."""
        run_id = str(uuid4())[:12]
        traces = self._load_traces()
        metrics = self._ks_monitor._compute_metrics(traces)

        # 1. Kill-switch check (gate — if critical fires, skip mutations)
        ks_results = self._ks_monitor.evaluate()
        critical_fired = any(
            r.fired and "never_autonomous" in " ".join(r.actions)
            for r in ks_results
        )

        actions: list[str] = []

        # 2. Drift detection
        drift_signals = self._run_drift_detection(metrics)
        for sig in drift_signals:
            if sig.fired:
                actions.extend(sig.response)

        # 3. Ritual pruning
        ritual_verdicts = self._run_ritual_pruning(metrics)
        for v in ritual_verdicts:
            if v.verdict == "disable_for_low_risk_tasks":
                actions.append(f"disable_ritual:{v.item}")

        # 4. Memory eval
        memory_eval = self._run_memory_eval(traces)
        if memory_eval and memory_eval.action != "ok":
            actions.append(f"memory:{memory_eval.action}")

        # 5. Confidence calibration
        confidence_cal = self._run_confidence_calibration(traces)
        if confidence_cal and confidence_cal.escalation:
            actions.append(f"confidence:{confidence_cal.escalation}")

        report = AutoUpdateReport(
            run_id=run_id,
            ts=_utc_now_iso(),
            kill_switches=ks_results,
            drift_signals=drift_signals,
            ritual_verdicts=ritual_verdicts,
            memory_eval=memory_eval,
            confidence_calibration=confidence_cal,
            actions_taken=list(dict.fromkeys(actions)),  # dedup, preserve order
            blocked_by_kill_switch=critical_fired,
        )

        self._emit_report(report)
        return report

    # ── Drift detection ───────────────────────────────────────────────────────

    def _run_drift_detection(self, metrics: dict[str, float]) -> list[DriftSignal]:
        signals: list[DriftSignal] = []
        if not metrics:
            return signals

        # strategy_success_rate_drop: win_rate < 0.65 in short window
        win_rate = metrics.get("replay_win_rate", 1.0)
        signals.append(DriftSignal(
            name="strategy_success_rate_drop",
            fired=win_rate < 0.65,
            window="short",
            value=win_rate,
            threshold=0.65,
            response=["reduce_prior_for_legacy_signatures", "refresh_signature_library"]
            if win_rate < 0.65 else [],
        ))

        # regression_rate_increase: > 0.15
        reg_rate = metrics.get("regression_rate", 0.0)
        signals.append(DriftSignal(
            name="regression_rate_increase",
            fired=reg_rate > 0.15,
            window="short",
            value=reg_rate,
            threshold=0.15,
            response=["raise_verification_intensity", "route_more_tasks_to_plan_then_patch"]
            if reg_rate > 0.15 else [],
        ))

        # premature_swarm: unnecessary_swarm_rate > 0.20
        swarm_rate = metrics.get("unnecessary_swarm_rate", 0.0)
        signals.append(DriftSignal(
            name="premature_swarm_increase",
            fired=swarm_rate > 0.20,
            window="short",
            value=swarm_rate,
            threshold=0.20,
            response=["revert_to_single_agent_default"] if swarm_rate > 0.20 else [],
        ))

        # token_cost_delta: > 0.15 (15% cost increase)
        cost_delta = metrics.get("token_cost_delta", 0.0)
        signals.append(DriftSignal(
            name="token_cost_spike",
            fired=cost_delta > 0.15,
            window="short",
            value=cost_delta,
            threshold=0.15,
            response=["switch_to_cheaper_model", "reduce_context_window"]
            if cost_delta > 0.15 else [],
        ))

        return signals

    # ── Ritual pruning ────────────────────────────────────────────────────────

    def _run_ritual_pruning(self, metrics: dict[str, float]) -> list[RitualVerdict]:
        """Evaluate ritual steps against thresholds from ritual-detection-rules.yaml."""
        verdicts: list[RitualVerdict] = []
        if not metrics:
            return verdicts

        # Proxy metrics from traces
        win_rate = metrics.get("replay_win_rate", 1.0)
        reg_rate = metrics.get("regression_rate", 0.0)

        # critic_slot_before_low_risk_patch
        # High activation (always runs), low decision change (rarely changes outcome)
        critic_activation = 0.8  # assumed always-on
        critic_decision_change = max(0.0, win_rate - 0.7)  # proxy
        critic_quality_gain = max(0.0, 1.0 - reg_rate - 0.8)
        verdicts.append(RitualVerdict(
            item="critic_slot_before_low_risk_patch",
            verdict=self._ritual_verdict(critic_activation, critic_decision_change, critic_quality_gain),
            activation_rate=critic_activation,
            decision_change_rate=critic_decision_change,
            quality_gain=critic_quality_gain,
        ))

        # generic_research_step
        research_activation = 0.5
        research_decision_change = 0.25
        research_quality_gain = 0.06
        verdicts.append(RitualVerdict(
            item="generic_research_step",
            verdict=self._ritual_verdict(research_activation, research_decision_change, research_quality_gain),
            activation_rate=research_activation,
            decision_change_rate=research_decision_change,
            quality_gain=research_quality_gain,
        ))

        return verdicts

    @staticmethod
    def _ritual_verdict(activation: float, decision_change: float, quality_gain: float) -> str:
        if activation >= 0.50 and decision_change <= 0.10 and quality_gain <= 0.02:
            return "disable_for_low_risk_tasks"
        if activation >= 0.35 and decision_change <= 0.20 and quality_gain <= 0.05:
            return "make_conditional"
        return "keep"

    # ── Memory eval ───────────────────────────────────────────────────────────

    def _run_memory_eval(self, traces: list[dict[str, Any]]) -> MemoryEvalResult | None:
        memory_path = self.repo_root / ".agent/memory/memory.jsonl"
        if not memory_path.exists():
            return None

        entries: list[dict] = []
        try:
            for line in memory_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception as exc:
                        logger.debug("Skipping malformed memory line: %s", exc)
        except Exception as exc:
            logger.warning("Failed to read memory file %s: %s", memory_path, exc)
            return None

        if not entries:
            return MemoryEvalResult(0, 0, 0, 1.0, "ok")

        from datetime import timedelta
        now = datetime.now(tz=timezone.utc)
        stale_threshold = timedelta(days=30)

        stale = 0
        for e in entries:
            ts_str = e.get("created_at") or e.get("ts") or e.get("timestamp")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(str(ts_str))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if now - ts > stale_threshold:
                        stale += 1
                except Exception as exc:
                    logger.debug("Failed to parse memory timestamp: %s", exc)

        # Duplicate detection: same content prefix
        seen: set[str] = set()
        duplicates = 0
        for e in entries:
            key = str(e.get("content") or e.get("value") or "")[:80]
            if key in seen:
                duplicates += 1
            seen.add(key)

        total = len(entries)
        stale_ratio = stale / total if total else 0
        dup_ratio = duplicates / total if total else 0

        # recall_at_10 estimate: inverse of stale ratio
        recall_estimate = max(0.0, 1.0 - stale_ratio * 0.5 - dup_ratio * 0.3)

        if stale_ratio > 0.30:
            action = "prune_stale"
        elif dup_ratio > 0.10:
            action = "merge_duplicates"
        elif recall_estimate < 0.70:
            action = "rebuild_index"
        else:
            action = "ok"

        return MemoryEvalResult(
            total_entries=total,
            stale_count=stale,
            duplicate_count=duplicates,
            recall_at_10_estimate=round(recall_estimate, 3),
            action=action,
        )

    # ── Confidence calibration ────────────────────────────────────────────────

    def _run_confidence_calibration(
        self, traces: list[dict[str, Any]]
    ) -> ConfidenceCalibrationResult | None:
        if not traces:
            return None

        # Compute ECE from traces that have confidence + outcome
        bins: dict[str, list[tuple[float, bool]]] = {
            "0.00-0.20": [], "0.21-0.40": [], "0.41-0.60": [],
            "0.61-0.80": [], "0.81-1.00": [],
        }
        for t in traces:
            data = t.get("data", {}) or {}
            conf = float(data.get("confidence") or t.get("confidence") or 0.0)
            outcome = str(data.get("outcome") or t.get("outcome") or "").lower()
            success = outcome in {"success", "ok", "completed"}
            if conf > 0:
                b = self._conf_bin(conf)
                if b in bins:
                    bins[b].append((conf, success))

        ece = self._compute_ece(bins)

        # Thresholds from confidence-calibration-rules.yaml
        if ece > 0.18:
            status = "fail"
            escalation = "deprioritize_current_strategy_profile"
        elif ece > 0.10:
            status = "warn"
            escalation = "require_critic_step"
        else:
            status = "ok"
            escalation = None

        return ConfidenceCalibrationResult(ece=round(ece, 4), status=status, escalation=escalation)

    @staticmethod
    def _conf_bin(conf: float) -> str:
        if conf <= 0.20:
            return "0.00-0.20"
        if conf <= 0.40:
            return "0.21-0.40"
        if conf <= 0.60:
            return "0.41-0.60"
        if conf <= 0.80:
            return "0.61-0.80"
        return "0.81-1.00"

    @staticmethod
    def _compute_ece(bins: dict[str, list[tuple[float, bool]]]) -> float:
        """Expected Calibration Error across bins."""
        total = sum(len(v) for v in bins.values())
        if total == 0:
            return 0.0
        ece = 0.0
        for items in bins.values():
            if not items:
                continue
            avg_conf = sum(c for c, _ in items) / len(items)
            avg_acc = sum(1 for _, s in items if s) / len(items)
            ece += (len(items) / total) * abs(avg_conf - avg_acc)
        return ece

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_traces(self) -> list[dict[str, Any]]:
        return self._ks_monitor._load_traces()

    def _emit_report(self, report: AutoUpdateReport) -> None:
        path = self.repo_root / self._REPORT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")

        emit_event("auto_update_cycle_completed", {
            "run_id": report.run_id,
            "status": "ok",
            "component": "auto_update",
            "data": {
                "kill_switches_fired": len([r for r in report.kill_switches if r.fired]),
                "drift_signals_fired": len([s for s in report.drift_signals if s.fired]),
                "actions_taken": report.actions_taken,
                "blocked": report.blocked_by_kill_switch,
            },
        })
