"""
Ralph Loop Engine — Isolated Module for Iterative Solution Optimization.

This module provides a runtime-agnostic implementation of Ralph's Loop:
- Accepts candidate solutions with scores
- Implements stop conditions (max_iterations, min_iterations, thresholds, plateau detection)
- Selects best-of-N candidates
- Emits Trace Event v2-compatible events (without writing to trace file)

Usage:
    config = RalphLoopConfig()
    engine = RalphLoopEngine(config)
    
    for iteration in range(1, config.max_iterations + 1):
        candidate = generate_candidate(iteration)  # External generation
        score = score_candidate(candidate)         # External scoring
        
        events = engine.record_iteration(iteration, candidate, score)
        emit_events(events)  # External emission
        
        if engine.should_stop():
            break
    
    decision = engine.finalize()
    apply_solution(decision.best_candidate)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class RalphLoopConfig:
    """Configuration for Ralph Loop engine."""
    
    max_iterations: int = 7
    """Maximum number of iterations before forced stop."""
    
    min_iterations: int = 3
    """Minimum iterations required before early stop is allowed."""
    
    min_acceptable_score: float = 0.70
    """Threshold score for early stop (if min_iterations met)."""
    
    min_score_delta: float = 0.05
    """Minimum improvement delta; below this triggers plateau stop."""
    
    score_weights: dict[str, float] = field(default_factory=lambda: {
        "correctness": 0.35,
        "speed": 0.20,
        "code_quality": 0.20,
        "token_efficiency": 0.15,
        "tool_success_rate": 0.10,
    })
    """Weights for weighted score calculation."""
    
    run_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique run identifier for trace correlation."""
    
    task_type: str = "T3"
    """Task type for trace events."""
    
    complexity: str = "C3"
    """Complexity level for trace events."""


@dataclass
class RalphLoopState:
    """Runtime state for Ralph Loop engine."""
    
    iteration: int = 0
    """Current iteration number (1-based)."""
    
    candidates: list[dict[str, Any]] = field(default_factory=list)
    """List of candidate solutions with metadata."""
    
    scores: list[float] = field(default_factory=list)
    """List of weighted total scores."""
    
    best_index: int = -1
    """Index of best candidate (by weighted_total score)."""
    
    best_score: float = 0.0
    """Best score seen so far."""
    
    prev_best_score: float = 0.0
    """Best score from previous iteration (for plateau detection)."""
    
    stopped: bool = False
    """Whether stop condition has been triggered."""
    
    stop_reason: str | None = None
    """Reason for stopping (if stopped)."""


@dataclass
class RalphLoopDecision:
    """Final decision from Ralph Loop engine."""
    
    selected: bool
    """Whether a candidate was selected."""
    
    best_candidate: dict[str, Any] | None
    """The selected best candidate solution."""
    
    best_score: float
    """Score of the selected candidate."""
    
    total_iterations: int
    """Total iterations performed."""
    
    stop_reason: str | None
    """Reason for stopping."""
    
    all_scores: list[float]
    """All scores for analysis."""
    
    improvement_history: list[float]
    """Score improvement history."""


@dataclass
class RalphEvent:
    """Trace Event v2-compatible event structure."""
    
    ts: str
    """ISO 8601 timestamp."""
    
    run_id: str
    """Run identifier."""
    
    event_type: str
    """Event type (ralph_*)."""
    
    level: str = "info"
    """Event level."""
    
    component: str = "ralph"
    """Component name."""
    
    task_type: str | None = None
    """Task type."""
    
    complexity: str | None = None
    """Complexity level."""
    
    status: str = "ok"
    """Event status."""
    
    message: str = ""
    """Human-readable message."""
    
    data: dict[str, Any] = field(default_factory=dict)
    """Additional event data."""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "ts": self.ts,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "level": self.level,
            "component": self.component,
        }
        if self.task_type is not None:
            result["task_type"] = self.task_type
        if self.complexity is not None:
            result["complexity"] = self.complexity
        result["status"] = self.status
        result["message"] = self.message
        result["data"] = self.data
        return result


def _utc_now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(tz=timezone.utc).isoformat()


def _compute_weighted_score(
    metrics: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Compute weighted total score from metrics."""
    total = 0.0
    for key, weight in weights.items():
        value = metrics.get(key, 0.0)
        total += value * weight
    return round(total, 4)


class RalphLoopEngine:
    """
    Ralph Loop Engine — manages iterative solution optimization.
    
    This engine is runtime-agnostic: it does not write to trace files
    or depend on external systems. It returns events for external emission.
    """
    
    def __init__(self, config: RalphLoopConfig | None = None):
        self.config = config or RalphLoopConfig()
        self.state = RalphLoopState()
        self._events: list[RalphEvent] = []
    
    def _add_event(self, event: RalphEvent) -> None:
        """Add event to internal buffer."""
        self._events.append(event)
    
    def _pop_events(self) -> list[RalphEvent]:
        """Pop and return all buffered events."""
        events = self._events
        self._events = []
        return events
    
    def record_iteration(
        self,
        candidate: dict[str, Any],
        metrics: dict[str, float] | None = None,
        weighted_total: float | None = None,
    ) -> list[RalphEvent]:
        """
        Record an iteration with candidate and score.
        
        Args:
            candidate: Candidate solution metadata (must include 'id' or 'name').
            metrics: Per-metric scores (correctness, speed, etc.).
            weighted_total: Pre-computed weighted total. If None, computed from metrics.
        
        Returns:
            List of events: ralph_iteration_started, ralph_iteration_scored
        """
        if self.state.stopped:
            raise RuntimeError("Ralph Loop has already stopped")
        
        self.state.iteration += 1
        iteration = self.state.iteration
        
        # Compute score if not provided
        if weighted_total is None:
            if metrics is None:
                metrics = {}
            weighted_total = _compute_weighted_score(metrics, self.config.score_weights)
        
        # Update state
        self.state.prev_best_score = self.state.best_score
        self.state.scores.append(weighted_total)
        
        candidate_record = {
            "iteration": iteration,
            "candidate": candidate,
            "metrics": metrics or {},
            "weighted_total": weighted_total,
        }
        self.state.candidates.append(candidate_record)
        
        # Update best - first candidate is always best initially, then compare
        if self.state.best_index == -1 or weighted_total > self.state.best_score:
            self.state.best_score = weighted_total
            self.state.best_index = len(self.state.candidates) - 1
        
        # Generate events
        events: list[RalphEvent] = []
        ts = _utc_now_iso()
        
        # ralph_iteration_started
        started_event = RalphEvent(
            ts=ts,
            run_id=self.config.run_id,
            event_type="ralph_iteration_started",
            task_type=self.config.task_type,
            complexity=self.config.complexity,
            status="ok",
            message=f"Ralph iteration {iteration} started",
            data={
                "iteration": iteration,
                "max_iterations": self.config.max_iterations,
            },
        )
        events.append(started_event)
        self._add_event(started_event)
        
        # ralph_iteration_scored
        candidate_id = candidate.get("id") or candidate.get("name") or f"candidate_{iteration}"
        scored_event = RalphEvent(
            ts=ts,
            run_id=self.config.run_id,
            event_type="ralph_iteration_scored",
            task_type=self.config.task_type,
            complexity=self.config.complexity,
            status="ok",
            message=f"Ralph iteration {iteration} scored: {weighted_total}",
            data={
                "iteration": iteration,
                "candidate_id": candidate_id,
                "weighted_total": weighted_total,
                "metrics": metrics or {},
                "is_new_best": weighted_total > self.state.prev_best_score,
                "ralph_loop": {
                    "enabled": True,
                    "iteration": iteration,
                    "total_iterations": self.config.max_iterations,
                    "score": {"weighted_total": weighted_total},
                    "selected_as_best": weighted_total == self.state.best_score,
                },
            },
        )
        events.append(scored_event)
        self._add_event(scored_event)
        
        return events
    
    def check_stop_condition(self) -> tuple[bool, str | None]:
        """
        Check if stop condition is met.
        
        Returns:
            Tuple of (should_stop, reason).
        
        Stop conditions are checked in this order:
        1. max_iterations — always stops
        2. min_iterations — must be met before early stop
        3. threshold_met — if best_score >= min_acceptable_score
        4. plateau_detected — if improvement delta < min_score_delta
        """
        iteration = self.state.iteration
        
        # Max iterations — always stop
        if iteration >= self.config.max_iterations:
            return True, "max_iterations_reached"
        
        # Must complete minimum iterations before any early stop
        if iteration < self.config.min_iterations:
            return False, None
        
        # Threshold stop — only check after min_iterations
        if self.state.best_score >= self.config.min_acceptable_score:
            return True, "threshold_met"
        
        # Plateau detection — only check after min_iterations
        # Plateau means: improvement is below delta (not necessarily negative)
        delta = self.state.best_score - self.state.prev_best_score
        if delta < self.config.min_score_delta:
            return True, "plateau_detected"
        
        return False, None
    
    def should_stop(self) -> bool:
        """Check if loop should stop and update state."""
        if self.state.stopped:
            return True
        
        should_stop, reason = self.check_stop_condition()
        if should_stop:
            self.state.stopped = True
            self.state.stop_reason = reason
            
            # Emit stop decision event
            stop_event = RalphEvent(
                ts=_utc_now_iso(),
                run_id=self.config.run_id,
                event_type="ralph_stop_decision",
                task_type=self.config.task_type,
                complexity=self.config.complexity,
                status="ok",
                message=f"Ralph Loop stopped: {reason}",
                data={
                    "stop_reason": reason,
                    "total_iterations": self.state.iteration,
                    "best_score": self.state.best_score,
                    "config": {
                        "max_iterations": self.config.max_iterations,
                        "min_iterations": self.config.min_iterations,
                        "min_acceptable_score": self.config.min_acceptable_score,
                        "min_score_delta": self.config.min_score_delta,
                    },
                },
            )
            self._add_event(stop_event)
        
        return should_stop
    
    def pop_events(self) -> list[RalphEvent]:
        """Pop all buffered events for external emission."""
        return self._pop_events()
    
    def finalize(self) -> RalphLoopDecision:
        """
        Finalize the loop and return decision.
        
        Returns:
            RalphLoopDecision with selected candidate and metadata.
        """
        if not self.state.stopped:
            # Force stop if not already stopped
            self.state.stopped = True
            self.state.stop_reason = "finalized"
        
        # Emit best selected event
        if self.state.best_index >= 0:
            best = self.state.candidates[self.state.best_index]
            candidate_id = (
                best["candidate"].get("id")
                or best["candidate"].get("name")
                or f"candidate_{best['iteration']}"
            )
            
            selected_event = RalphEvent(
                ts=_utc_now_iso(),
                run_id=self.config.run_id,
                event_type="ralph_best_selected",
                task_type=self.config.task_type,
                complexity=self.config.complexity,
                status="ok",
                message=f"Best candidate selected: {candidate_id} (score: {self.state.best_score})",
                data={
                    "best_iteration": best["iteration"],
                    "candidate_id": candidate_id,
                    "best_score": self.state.best_score,
                    "total_candidates": len(self.state.candidates),
                },
            )
            self._add_event(selected_event)
        
        # Compute improvement history
        improvement_history: list[float] = []
        running_max = 0.0
        for score in self.state.scores:
            if score > running_max:
                running_max = score
            improvement_history.append(running_max)
        
        return RalphLoopDecision(
            selected=self.state.best_index >= 0,
            best_candidate=self.state.candidates[self.state.best_index]["candidate"]
            if self.state.best_index >= 0
            else None,
            best_score=self.state.best_score,
            total_iterations=self.state.iteration,
            stop_reason=self.state.stop_reason,
            all_scores=self.state.scores,
            improvement_history=improvement_history,
        )
    
    def get_events(self) -> list[RalphEvent]:
        """Get all events without popping (for inspection)."""
        return self._events.copy()
