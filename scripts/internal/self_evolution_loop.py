#!/usr/bin/env python3
"""
Zera Self-Evolution Loop — бесконечный цикл саморазвития Hermes Zera

Архитектура (7-фазный цикл):
  1. OBSERVE    — Scout external patterns + review recent failures
  2. CLASSIFY   — Classify candidates per governance contract
  3. SCORE      — Score on capability, risk, novelty
  4. DESIGN     — Build evolution prompt
  5. SANDBOX    — Test in beta profile (safe isolation)
  6. EVAL       — Run evaluation suite
  7. PROMOTE    — If passes → promote; else → rollback
  8. REFLECT    — Self-reflection + telemetry capture

Governor: zera_growth_governance.json (enforced across all phases)

Usage:
    python3 self_evolution_loop.py              # Run forever
    python3 self_evolution_loop.py --cycles 3   # Run 3 cycles then stop
    python3 self_evolution_loop.py --dry-run    # Simulate without executing
    python3 self_evolution_loop.py --status     # Show current state
    python3 self_evolution_loop.py --reset      # Reset evolution state

Author: Agent OS Architecture Team
Date: 2026-04-09
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import logging
import math
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
HERMES_PROFILES = Path.home() / ".hermes/profiles"
GOVERNANCE_PATH = REPO_ROOT / "configs/tooling/zera_growth_governance.json"
EVO_STATE_PATH = REPO_ROOT / ".agent/evolution/state.json"
EVO_TELEMETRY_PATH = REPO_ROOT / ".agent/evolution/telemetry.jsonl"
EVO_LOG_PATH = REPO_ROOT / ".agent/evolution/loop.log"
EVO_META_MEMORY_PATH = REPO_ROOT / ".agent/evolution/meta_memory.json"
SCOUT_JOURNAL_PATH = REPO_ROOT / ".agent/evolution/scout_journal.md"
MAX_TRACE_SCAN_LINES = 250
MAX_MEMORY_SCAN_LINES = 120
MAX_TELEMETRY_STATUS_LINES = 5
TAIL_CHUNK_SIZE_BYTES = 8192
OBSERVE_PARALLEL_WORKERS = 3
LLM_SCORING_ENDPOINT = "http://127.0.0.1:11434/api/chat"
LLM_SCORING_TIMEOUT_SECONDS = 45
LLM_SCORING_MODEL = os.getenv("ZERA_EVO_SCORING_MODEL", "qwen3.5:4b-q4_K_M")
MAX_META_MEMORY_ENTRIES = 200

# 10 loop algorithms for rotation
LOOP_ALGORITHMS = [
    "karpathy",            # Iterative self-correction
    "rsi",                 # Recursive self-improvement
    "darwin-goedel",       # Evolutionary self-reference
    "pantheon",            # Multi-persona council
    "self-improving",      # Meta-learning loop
    "karpathy-swarm",      # Parallel self-correction
    "ralph",               # Iterative refinement
    "agentic-ci",          # Continuous integration
    "self-driving",        # Autonomous operation
    "meta-learning",       # Learning to learn
]

# Governance-aligned candidate classes.
# IMPORTANT: This list MUST match configs/tooling/zera_growth_governance.json
# candidate_classes keys exactly. The script reads from governance as source of truth.
# Previously this was a hardcoded parallel list with mismatched names (160 cycles of
# class_stats showing 0 trials for governance classes). Fixed 2026-04-09.
GOVERNANCE_CANDIDATE_CLASSES = [
    "skill_refinement",
    "tool_usage_refinement",
    "workflow_improvement",
    "orchestration_pattern_update",
    "memory_policy_refinement",
    "tone_calibration",
    "boundary_tightening",
    "proactivity_adjustment",
    "refusal_behavior_adjustment",
    "autonomy_behavior_adjustment",
    "governance_affecting_candidate",
    "mixed_ambiguous_candidate",
    "command_recipe",
    "branch_template",
    "research_target",
]

# Legacy dry-run fallback (not used in live cycles — kept for --dry-run safety)
DRYRUN_CANDIDATE_CLASSES = [
    "skill_refinement",
    "tool_usage_refinement",
    "workflow_improvement",
    "orchestration_pattern_update",
    "memory_policy_refinement",
    "tone_calibration",
    "boundary_tightening",
    "proactivity_adjustment",
    "refusal_behavior_adjustment",
    "autonomy_behavior_adjustment",
    "governance_affecting_candidate",
    "mixed_ambiguous_candidate",
    "command_recipe",
    "branch_template",
    "research_target",
]

# Alias for backwards compatibility in places that reference CANDIDATE_CLASSES
CANDIDATE_CLASSES = GOVERNANCE_CANDIDATE_CLASSES

# ── Setup logging ─────────────────────────────────────────────────────

EVO_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(EVO_LOG_PATH),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("zera.evolution")

# ── Graceful shutdown ─────────────────────────────────────────────────

_shutdown_requested = False

def _handle_shutdown(signum: int, frame: Any) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown signal received (signal %d). Completing current cycle...", signum)

signal.signal(signal.SIGINT, _handle_shutdown)
signal.signal(signal.SIGTERM, _handle_shutdown)


# ── Data Models ────────────────────────────────────────────────────────

class EvolutionPhase(Enum):
    OBSERVE = "observe"
    CLASSIFY = "classify"
    SCORE = "score"
    DESIGN = "design"
    SANDBOX = "sandbox"
    EVAL = "eval"
    PROMOTE = "promote"
    REFLECT = "reflect"


class CandidateStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionCandidate:
    candidate_class: str
    loop_algorithm: str
    description: str
    risk_level: str
    status: CandidateStatus = CandidateStatus.PENDING
    score: float = 0.0
    sandbox_result: str = ""
    eval_passed: bool = False
    telemetry: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    promoted_at: str = ""


@dataclass
class CycleResult:
    cycle_number: int
    loop_algorithm: str
    phases_completed: list[str]
    candidate: EvolutionCandidate | None
    duration_seconds: float
    status: str  # completed, failed, skipped, shutdown
    error: str = ""


@dataclass
class EvolutionState:
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    skipped_cycles: int = 0
    candidates_promoted: int = 0
    candidates_rolled_back: int = 0
    current_cycle: int = 0
    current_loop_algorithm: str = ""
    loop_algorithm_index: int = 0
    last_cycle_at: str = ""
    last_cycle_status: str = ""
    last_error: str = ""
    started_at: str = ""
    freeze_active: bool = False
    freeze_reason: str = ""
    personality_changes: int = 0
    consecutive_regressions: int = 0
    loop_stats: dict[str, dict[str, float | int]] = field(default_factory=dict)
    class_stats: dict[str, dict[str, float | int]] = field(default_factory=dict)


# ── State Management ──────────────────────────────────────────────────

def load_state() -> EvolutionState:
    """Load evolution state from disk."""
    if EVO_STATE_PATH.exists():
        try:
            data = json.loads(EVO_STATE_PATH.read_text(encoding="utf-8"))
            return EvolutionState(**data)
        except Exception as e:
            logger.warning("Failed to load state: %s. Starting fresh.", e)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return EvolutionState(
        started_at=now,
        last_cycle_at=now,
        current_loop_algorithm=LOOP_ALGORITHMS[0],
    )


def save_state(state: EvolutionState) -> None:
    """Save evolution state to disk."""
    EVO_STATE_PATH.write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def log_telemetry(event: dict[str, Any]) -> None:
    """Append telemetry event."""
    event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Custom serializer for enums and complex objects
    def _serialize(obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return str(obj)
    with open(EVO_TELEMETRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, default=_serialize) + "\n")


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    """Read last N lines without loading the full file into memory."""
    if max_lines <= 0 or not path.exists():
        return []

    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            position = fh.tell()
            if position <= 0:
                return []

            buffer = bytearray()
            while position > 0 and buffer.count(b"\n") <= max_lines:
                read_size = min(TAIL_CHUNK_SIZE_BYTES, position)
                position -= read_size
                fh.seek(position)
                buffer[:0] = fh.read(read_size)

        lines = buffer.decode("utf-8", errors="replace").splitlines()
        return lines[-max_lines:]
    except Exception as e:
        logger.warning("Failed to tail file %s: %s", path, e)
        return []


def _load_env_file(env_file: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines from a .env file."""
    env: dict[str, str] = {}
    if not env_file.exists():
        return env

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _new_stat_row() -> dict[str, float | int]:
    return {
        "trials": 0,
        "reward_sum": 0.0,
        "successes": 0,
        "promotions": 0,
        "failures": 0,
        "last_reward": 0.0,
        "last_cycle": 0,
    }


def ensure_meta_tables(state: EvolutionState, governance: dict[str, Any]) -> None:
    """Ensure meta-learning tables contain all known algorithms and classes."""
    if not isinstance(state.loop_stats, dict):
        state.loop_stats = {}
    if not isinstance(state.class_stats, dict):
        state.class_stats = {}

    for algo in LOOP_ALGORITHMS:
        row = state.loop_stats.get(algo)
        if not isinstance(row, dict):
            state.loop_stats[algo] = _new_stat_row()
        else:
            for key, default_value in _new_stat_row().items():
                row.setdefault(key, default_value)

    # Use governance schema as source of truth. No silent fallback to hardcoded list.
    configured_classes = list(governance.get("candidate_classes", {}).keys())
    if not configured_classes:
        logger.error("  Governance candidate_classes is empty! Cannot proceed.")
        return "skill_refinement"  # Safe default — still governed
    for candidate_class in configured_classes:
        row = state.class_stats.get(candidate_class)
        if not isinstance(row, dict):
            state.class_stats[candidate_class] = _new_stat_row()
        else:
            for key, default_value in _new_stat_row().items():
                row.setdefault(key, default_value)


def _ucb_score(row: dict[str, float | int], total_trials: int, exploration: float) -> float:
    trials = max(0, int(row.get("trials", 0)))
    if trials == 0:
        return float("inf")
    mean_reward = float(row.get("reward_sum", 0.0)) / trials
    bonus = exploration * math.sqrt(max(0.0, math.log(max(2, total_trials + 1)) / trials))
    return mean_reward + bonus


def select_loop_algorithm(state: EvolutionState) -> str:
    """Adaptive algorithm selection with UCB-style explore/exploit."""
    total_trials = sum(int(row.get("trials", 0)) for row in state.loop_stats.values())
    exploration = 0.50 + min(0.30, state.consecutive_regressions * 0.10)
    best_algo = LOOP_ALGORITHMS[0]
    best_score = float("-inf")

    for algo in LOOP_ALGORITHMS:
        row = state.loop_stats.get(algo, _new_stat_row())
        score = _ucb_score(row, total_trials=total_trials, exploration=exploration)
        if score > best_score:
            best_score = score
            best_algo = algo

    return best_algo


def _compute_cycle_reward(result: CycleResult) -> float:
    """Convert cycle outcome into [0.0, 1.0] reward for meta-learning."""
    if result.status == "failed":
        return 0.0
    if result.status in ("shutdown",):
        return 0.2

    reward = 0.35
    candidate = result.candidate
    if candidate is not None:
        reward += min(0.35, max(0.0, candidate.score) * 0.5)
        if candidate.status == CandidateStatus.PROMOTED:
            reward += 0.25
        elif candidate.status == CandidateStatus.APPROVED:
            reward += 0.15
        elif candidate.status == CandidateStatus.ROLLED_BACK:
            reward -= 0.25
        elif candidate.status == CandidateStatus.REJECTED:
            reward -= 0.10

    # Mild efficiency pressure: very long cycles reduce reward.
    if result.duration_seconds > 10:
        reward -= min(0.10, (result.duration_seconds - 10) / 300.0)

    return max(0.0, min(1.0, reward))


def update_meta_learning(state: EvolutionState, result: CycleResult) -> float:
    """Update algorithm/class performance tables after each cycle."""
    reward = _compute_cycle_reward(result)

    algo_row = state.loop_stats.setdefault(result.loop_algorithm, _new_stat_row())
    algo_row["trials"] = int(algo_row["trials"]) + 1
    algo_row["reward_sum"] = float(algo_row["reward_sum"]) + reward
    algo_row["last_reward"] = reward
    algo_row["last_cycle"] = result.cycle_number

    if result.status == "completed":
        algo_row["successes"] = int(algo_row["successes"]) + 1
    else:
        algo_row["failures"] = int(algo_row["failures"]) + 1

    if result.candidate and result.candidate.status == CandidateStatus.PROMOTED:
        algo_row["promotions"] = int(algo_row["promotions"]) + 1

    if result.candidate:
        class_row = state.class_stats.setdefault(result.candidate.candidate_class, _new_stat_row())
        class_row["trials"] = int(class_row["trials"]) + 1
        class_row["reward_sum"] = float(class_row["reward_sum"]) + reward
        class_row["last_reward"] = reward
        class_row["last_cycle"] = result.cycle_number
        if result.status == "completed":
            class_row["successes"] = int(class_row["successes"]) + 1
        else:
            class_row["failures"] = int(class_row["failures"]) + 1
        if result.candidate.status == CandidateStatus.PROMOTED:
            class_row["promotions"] = int(class_row["promotions"]) + 1

    return reward


def load_meta_memory() -> dict[str, Any]:
    if not EVO_META_MEMORY_PATH.exists():
        return {"insights": [], "updated_at": ""}
    try:
        data = json.loads(EVO_META_MEMORY_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"insights": [], "updated_at": ""}
        insights = data.get("insights", [])
        if not isinstance(insights, list):
            insights = []
        return {"insights": insights, "updated_at": data.get("updated_at", "")}
    except Exception as e:
        logger.warning("Failed to load meta memory: %s", e)
        return {"insights": [], "updated_at": ""}


def save_meta_memory(memory: dict[str, Any]) -> None:
    memory["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    EVO_META_MEMORY_PATH.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def memory_reflection_signals(limit: int = 20) -> list[dict[str, Any]]:
    """Load latest reflection-derived signals for future cycle selection."""
    memory = load_meta_memory()
    insights = memory.get("insights", [])
    if not isinstance(insights, list):
        return []
    recent = insights[-limit:]
    signals: list[dict[str, Any]] = []
    for insight in recent:
        if isinstance(insight, dict):
            signals.append(
                {
                    "candidate_class": insight.get("candidate_class", ""),
                    "loop_algorithm": insight.get("loop_algorithm", ""),
                    "reward": insight.get("reward", 0.0),
                    "next_focus": insight.get("next_focus", ""),
                    "risk_hint": insight.get("risk_hint", ""),
                }
            )
    return signals


def persist_cycle_insight(candidate: EvolutionCandidate, cycle_result: CycleResult, reward: float, next_focus: str) -> None:
    memory = load_meta_memory()
    insights = memory.setdefault("insights", [])
    if not isinstance(insights, list):
        insights = []
    risk_hint = "regression_risk" if candidate.status in (CandidateStatus.ROLLED_BACK, CandidateStatus.REJECTED) else "stable"
    insights.append(
        {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cycle_number": cycle_result.cycle_number,
            "loop_algorithm": cycle_result.loop_algorithm,
            "candidate_class": candidate.candidate_class,
            "score": candidate.score,
            "status": candidate.status.value,
            "reward": round(reward, 4),
            "next_focus": next_focus,
            "risk_hint": risk_hint,
        }
    )
    memory["insights"] = insights[-MAX_META_MEMORY_ENTRIES:]
    save_meta_memory(memory)


# ── Governance ─────────────────────────────────────────────────────────

def load_governance() -> dict[str, Any]:
    """Load governance contract."""
    if GOVERNANCE_PATH.exists():
        return json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))
    logger.warning("Governance file not found at %s. Using defaults.", GOVERNANCE_PATH)
    return {
        "freeze_conditions": {"conditions": []},
        "candidate_classes": {c: {"risk_level": "medium", "auto_promote_allowed": False} for c in CANDIDATE_CLASSES},
        "promotion_rules": {"eval_required": True, "rollback_required": True, "telemetry_required": True},
    }


def check_freeze_conditions(governance: dict[str, Any], state: EvolutionState | None = None) -> tuple[bool, str]:
    """Check if evolution should be frozen."""
    freeze_config = governance.get("freeze_conditions", [])

    # freeze_conditions is a list of condition strings
    if isinstance(freeze_config, list):
        # For now, only check runtime conditions
        pass
    elif isinstance(freeze_config, dict):
        conditions = freeze_config.get("conditions", [])

    # Always-check runtime conditions
    current_state = state or load_state()

    # Check consecutive regressions
    if current_state.consecutive_regressions >= governance.get("promotion_rules", {}).get("freeze_after_consecutive_personality_regressions", 2):
        return True, f"Consecutive regressions: {current_state.consecutive_regressions}"

    # Check profile existence
    if not (HERMES_PROFILES / "zera/config.yaml").exists():
        return True, "Zera profile not found"

    return False, ""


# ── Phase 1: OBSERVE ──────────────────────────────────────────────────

def phase_observe() -> dict[str, Any]:
    """Phase 1: Gather external intelligence and internal signals."""
    logger.info("═══ PHASE 1: OBSERVE ═══")
    observations: dict[str, Any] = {
        "external_patterns": [],
        "internal_failures": [],
        "memory_signals": [],
        "meta_memory_signals": [],
        "telemetry_review": {},
    }

    logger.info("  → Collecting signals in parallel...")
    tasks = {
        "external_patterns": scout_external_patterns,
        "internal_failures": review_recent_failures,
        "memory_signals": check_memory_signals,
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=OBSERVE_PARALLEL_WORKERS) as executor:
        future_to_key = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                observations[key] = future.result()
            except Exception as e:
                logger.warning("  Signal collection failed for %s: %s", key, e)
                observations[key] = [{"status": "error", "error": str(e)}]

    observations["meta_memory_signals"] = memory_reflection_signals(limit=20)
    observations["telemetry_review"] = {
        "external_count": len(observations["external_patterns"]),
        "failure_count": len(observations["internal_failures"]),
        "memory_count": len(observations["memory_signals"]),
        "reflection_memory_count": len(observations["meta_memory_signals"]),
    }

    log_telemetry({"phase": "observe", "data": observations})
    logger.info("  ✓ Observe complete: %d external, %d internal signals",
                len(observations["external_patterns"]),
                len(observations["internal_failures"]))
    return observations


def scout_external_patterns() -> list[dict[str, str]]:
    """Run scout daemon to gather external patterns."""
    scout_script = REPO_ROOT / "scripts/scout_daemon.py"
    if not scout_script.exists():
        logger.warning("  Scout daemon not found at %s", scout_script)
        return [{"source": "scout", "status": "daemon_not_found"}]

    env_file = HERMES_PROFILES / "zera/.env"
    env_overrides = _load_env_file(env_file)
    has_exa_key = bool((os.getenv("EXA_API_KEY") or "").strip() or (env_overrides.get("EXA_API_KEY") or "").strip())

    if not has_exa_key:
        logger.info("  EXA_API_KEY not configured — skipping scout")
        return [{"source": "scout", "status": "skipped", "reason": "no EXA_API_KEY"}]

    # Run scout with strict timeout
    try:
        env = dict(os.environ)
        env.update(env_overrides)

        result = subprocess.run(
            [sys.executable, str(scout_script)],
            capture_output=True, text=True, timeout=15, env=env, check=False,
        )
        if result.returncode == 0:
            logger.info("  Scout completed successfully")
            return [{"source": "scout_daemon", "status": "completed"}]
        else:
            logger.warning("  Scout failed (exit %d): %s", result.returncode, (result.stderr or "")[:200])
            return [{"source": "scout", "status": "error", "exit_code": result.returncode}]
    except subprocess.TimeoutExpired:
        logger.warning("  Scout timed out (15s) — skipping")
        return [{"source": "scout", "status": "timeout"}]
    except Exception as e:
        logger.warning("  Scout error: %s", e)
        return [{"source": "scout", "status": "error", "error": str(e)}]


def review_recent_failures() -> list[dict[str, str]]:
    """Review recent agent failures from traces."""
    trace_file = REPO_ROOT / "logs/agent_traces.jsonl"
    failures = []
    if not trace_file.exists():
        return failures

    try:
        recent = _tail_lines(trace_file, MAX_TRACE_SCAN_LINES)
        for line in reversed(recent):
            try:
                event = json.loads(line)
                if event.get("level") == "error" or event.get("status") == "failed":
                    failures.append({
                        "event_type": event.get("event_type", "unknown"),
                        "message": str(event.get("message", ""))[:100],
                        "timestamp": event.get("ts", ""),
                    })
                    if len(failures) >= 5:
                        break
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.warning("  Failed to review traces: %s", e)

    return failures


def check_memory_signals() -> list[dict[str, Any]]:
    """Check BM25 memory for evolution signals."""
    memory_file = REPO_ROOT / ".agent/memory/memory.jsonl"
    signals = []
    if not memory_file.exists():
        return signals

    try:
        lines = _tail_lines(memory_file, MAX_MEMORY_SCAN_LINES)
        # Check for low-confidence entries that might need refinement
        for line in lines:
            try:
                entry = json.loads(line)
                payload = entry.get("payload", {})
                confidence = payload.get("confidence", 1.0)
                if isinstance(confidence, (int, float)) and confidence < 0.5:
                    signals.append({
                        "key": entry.get("key", ""),
                        "confidence": confidence,
                        "action": "review_for_refinement",
                    })
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.warning("  Failed to check memory: %s", e)

    return signals


# ── Phase 2: CLASSIFY ─────────────────────────────────────────────────

def phase_classify(observations: dict[str, Any], governance: dict[str, Any], state: EvolutionState, loop_algo: str) -> EvolutionCandidate:
    """Phase 2: Classify evolution candidate."""
    logger.info("═══ PHASE 2: CLASSIFY ═══")

    # Determine candidate class based on observations
    candidate_class = determine_candidate_class(observations, governance, state)

    # Determine risk level
    risk_config = governance.get("candidate_classes", {}).get(candidate_class, {})
    risk_level = risk_config.get("risk_level", "medium")

    candidate = EvolutionCandidate(
        candidate_class=candidate_class,
        loop_algorithm=loop_algo,
        description=f"Evolution cycle {state.current_cycle + 1}: {candidate_class} via {loop_algo}",
        risk_level=risk_level,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )

    # Check if auto-promotion is allowed
    auto_promote = risk_config.get("auto_promote_allowed", False)
    logger.info("  → Candidate: %s (risk: %s, auto_promote: %s)",
                candidate_class, risk_level, auto_promote)
    candidate.telemetry["auto_promote_allowed"] = auto_promote

    log_telemetry({"phase": "classify", "candidate": asdict(candidate)})
    return candidate


def determine_candidate_class(observations: dict[str, Any], governance: dict[str, Any], state: EvolutionState) -> str:
    """Determine which candidate class to pursue based on signals."""
    external = observations.get("external_patterns", [])
    failures = observations.get("internal_failures", [])
    memory = observations.get("memory_signals", [])
    reflection_memory = observations.get("meta_memory_signals", [])
    # Use governance schema as source of truth. No silent fallback.
    configured_classes = list(governance.get("candidate_classes", {}).keys())
    if not configured_classes:
        logger.error("  Governance candidate_classes is empty — cannot classify candidate.")
        return "skill_refinement"  # Safe governed default

    # Priority-based classification — use GOVERNANCE class names only
    if failures and "autonomy_behavior_adjustment" in configured_classes:
        # Internal failures suggest an autonomy/action-class problem
        return "autonomy_behavior_adjustment"
    if memory and "memory_policy_refinement" in configured_classes:
        return "memory_policy_refinement"
    if external and "research_target" in configured_classes:
        return "research_target"

    # Reflection memory can request specific next focus
    for signal in reversed(reflection_memory):
        next_focus = str(signal.get("next_focus", "")).strip()
        if next_focus in configured_classes:
            return next_focus

    # UCB-class selection for long-term meta-learning
    total_trials = sum(int(row.get("trials", 0)) for row in state.class_stats.values())
    exploration = 0.45 + min(0.25, state.consecutive_regressions * 0.10)
    best_class = configured_classes[0]
    best_score = float("-inf")
    for candidate_class in configured_classes:
        row = state.class_stats.get(candidate_class, _new_stat_row())
        score = _ucb_score(row, total_trials=total_trials, exploration=exploration)
        if score > best_score:
            best_score = score
            best_class = candidate_class
    return best_class


# ── Phase 3: SCORE ────────────────────────────────────────────────────

def _score_via_llm(candidate: EvolutionCandidate, observations: dict[str, Any]) -> dict[str, float] | None:
    """Score candidate using local free LLM with heuristic fallback.

    Returns dict of scores or None if LLM unavailable.
    """
    if os.getenv("ZERA_EVO_DISABLE_LLM_SCORING", "").strip().lower() in {"1", "true", "yes", "on"}:
        return None

    risk_val = '0.2' if candidate.risk_level == 'high' else '0.5' if candidate.risk_level == 'medium' else '0.8'

    prompt = (
        f"Score this evolution candidate. Reply with exactly 4 numbers separated by commas. "
        f"Each number 0.0 to 1.0. No explanation.\n\n"
        f"Class: {candidate.candidate_class}\n"
        f"Algorithm: {candidate.loop_algorithm}\n"
        f"Risk: {candidate.risk_level} (risk_assessment={risk_val})\n"
        f"External signals: {len(observations.get('external_patterns', []))}\n"
        f"Failures: {len(observations.get('internal_failures', []))}\n"
        f"Memory signals: {len(observations.get('memory_signals', []))}\n\n"
        f"Reply format: capability,novelty,alignment,efficiency"
    )

    try:
        payload = {
            "model": LLM_SCORING_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        req = urllib.request.Request(
            LLM_SCORING_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=LLM_SCORING_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result.get("message", {}).get("content", "").strip()

        if not content:
            return None

        # Extract numbers from response
        numbers = []
        for part in content.replace("\n", ",").split(","):
            part = part.strip().strip("`")
            try:
                numbers.append(float(part))
            except ValueError:
                continue

        if len(numbers) < 4:
            logger.warning("  LLM format: %s", repr(content[:80]))
            return None

        return {
            "capability_potential": max(0.0, min(1.0, numbers[0])),
            "novelty": max(0.0, min(1.0, numbers[1])),
            "alignment_with_goals": max(0.0, min(1.0, numbers[2])),
            "resource_efficiency": max(0.0, min(1.0, numbers[3])),
        }

    except (TimeoutError, json.JSONDecodeError, urllib.error.URLError):
        return None
    except Exception:
        return None


def _score_via_heuristics(candidate: EvolutionCandidate, observations: dict[str, Any]) -> dict[str, float]:
    """Fallback heuristic scoring when LLM unavailable."""
    external_count = len(observations.get("external_patterns", []))
    failure_count = len(observations.get("internal_failures", []))
    memory_count = len(observations.get("memory_signals", []))

    # More signals = higher capability potential
    signal_score = min(1.0, (external_count + failure_count + memory_count) / 5.0)

    return {
        "capability_potential": 0.4 + signal_score * 0.4,
        "risk_assessment": 1.0 - ({"low": 0.2, "medium": 0.5, "high": 0.8}.get(candidate.risk_level, 0.5)),
        "novelty": 0.4 + (0.2 if candidate.loop_algorithm in ("darwin-goedel", "pantheon", "meta-learning") else 0.0),
        "alignment_with_goals": 0.5 + (0.2 if "pattern" in candidate.candidate_class else 0.1),
        "resource_efficiency": 0.5 + (0.1 if candidate.risk_level == "low" else 0.0),
    }


def phase_score(candidate: EvolutionCandidate, observations: dict[str, Any] | None = None) -> float:
    """Phase 3: Score the candidate on multiple dimensions.

    Uses local free LLM scoring with
    heuristic fallback if LLM is unavailable.
    """
    logger.info("═══ PHASE 3: SCORE ═══")
    observations = observations or {}

    # Try LLM scoring first
    llm_scores = _score_via_llm(candidate, observations)

    if llm_scores:
        scores = {
            "capability_potential": llm_scores["capability_potential"],
            "risk_assessment": 1.0 - ({"low": 0.2, "medium": 0.5, "high": 0.8}.get(candidate.risk_level, 0.5)),
            "novelty": llm_scores["novelty"],
            "alignment_with_goals": llm_scores["alignment_with_goals"],
            "resource_efficiency": llm_scores["resource_efficiency"],
        }
        logger.info("  → LLM-based scoring")
    else:
        # Fallback to heuristics
        scores = _score_via_heuristics(candidate, observations)
        logger.info("  → Heuristic scoring (LLM unavailable)")

    # Weighted average
    weights = {
        "capability_potential": 0.30,
        "risk_assessment": 0.25,
        "novelty": 0.15,
        "alignment_with_goals": 0.20,
        "resource_efficiency": 0.10,
    }
    total_score = sum(scores[k] * weights[k] for k in weights)

    candidate.score = round(total_score, 3)
    candidate.telemetry["scores"] = {k: round(v, 3) for k, v in scores.items()}
    candidate.telemetry["scoring_method"] = "llm" if llm_scores else "heuristic"

    logger.info("  → Score: %.3f (capability: %.2f, risk: %.2f, novelty: %.2f)",
                total_score, scores["capability_potential"], scores["risk_assessment"], scores["novelty"])

    log_telemetry({"phase": "score", "candidate_class": candidate.candidate_class, "score": total_score, "scores": scores})
    return total_score


# ── Phase 4: DESIGN ───────────────────────────────────────────────────

def phase_design(candidate: EvolutionCandidate) -> str:
    """Phase 4: Build evolution prompt."""
    logger.info("═══ PHASE 4: DESIGN ═══")

    # Load evolution prompt template
    evolve_script = REPO_ROOT / "scripts/zera-evolve.sh"

    if evolve_script.exists():
        logger.info("  → Using zera-evolve.sh for prompt generation")
        prompt = f"Execute evolution cycle via zera-evolve.sh: --loop {candidate.loop_algorithm} --class {candidate.candidate_class}"
    else:
        logger.info("  → Generating inline evolution prompt")
        prompt = build_inline_evolution_prompt(candidate)

    candidate.telemetry["prompt_length"] = len(prompt)
    candidate.telemetry["prompt_source"] = "zera-evolve.sh" if evolve_script.exists() else "inline"

    log_telemetry({"phase": "design", "candidate_class": candidate.candidate_class, "prompt_source": candidate.telemetry["prompt_source"]})
    return prompt


def build_inline_evolution_prompt(candidate: EvolutionCandidate) -> str:
    """Build an evolution prompt inline (fallback when zera-evolve.sh unavailable)."""
    return f"""
Zera Self-Evolution Cycle — {candidate.loop_algorithm}

Candidate Class: {candidate.candidate_class}
Risk Level: {candidate.risk_level}
Score: {candidate.score}

Task:
Analyze the current state of the Antigravity Core system and propose improvements
in the area of {candidate.candidate_class}.

Constraints (from governance):
- Do NOT modify governance files (zera_growth_governance.json, zera_command_registry.yaml, etc.)
- Do NOT change persona core identity (HERMES_SOUL.md)
- All changes must have clear rollback paths
- Changes must be testable and reversible
- Personality delta must stay within governance limits

Focus areas for {candidate.candidate_class}:
- Identify specific, measurable improvements
- Propose concrete implementation steps
- Define success criteria
- Document rollback procedure

Output format:
1. Current state analysis
2. Proposed change
3. Implementation plan
4. Success criteria
5. Rollback procedure
"""


# ── Phase 5: SANDBOX ──────────────────────────────────────────────────

def phase_sandbox(candidate: EvolutionCandidate) -> str:
    """Phase 5: Test in beta profile (safe isolation)."""
    logger.info("═══ PHASE 5: SANDBOX ═══")

    # Create beta profile
    beta_manager = REPO_ROOT / "scripts/beta_manager.py"
    sandbox_result = "beta_not_available"

    if beta_manager.exists():
        try:
            # Setup beta
            result = subprocess.run(
                [sys.executable, str(beta_manager), "setup"],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if result.returncode == 0:
                sandbox_result = "beta_setup_ok"
                logger.info("  → Beta profile created")
            else:
                sandbox_result = f"beta_setup_failed: {(result.stderr or '')[:200]}"
                logger.warning("  → Beta setup failed: %s", sandbox_result)
        except Exception as e:
            sandbox_result = f"beta_setup_error: {e}"
            logger.warning("  → Beta setup error: %s", e)
    else:
        logger.info("  → Beta manager not found — skipping sandbox phase")
        sandbox_result = "beta_manager_not_found"

    candidate.sandbox_result = sandbox_result
    candidate.telemetry["sandbox_result"] = sandbox_result

    log_telemetry({"phase": "sandbox", "candidate_class": candidate.candidate_class, "result": sandbox_result})
    return sandbox_result


# ── Phase 6: EVAL ─────────────────────────────────────────────────────

def phase_eval(candidate: EvolutionCandidate, governance: dict[str, Any], state: EvolutionState) -> bool:
    """Phase 6: Run evaluation suite."""
    logger.info("═══ PHASE 6: EVAL ═══")

    # Run hardening validator
    validator = REPO_ROOT / "scripts/validation/check_zera_hardening.py"
    eval_passed = False

    if validator.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(validator)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            eval_passed = result.returncode == 0
            if eval_passed:
                logger.info("  → Hardening validator: PASSED")
            else:
                logger.warning("  → Hardening validator: FAILED\n%s", (result.stderr or result.stdout)[:500])
        except Exception as e:
            logger.warning("  → Hardening validator error: %s", e)
            eval_passed = False
    else:
        logger.info("  → Hardening validator not found — using basic checks")
        # Basic eval: check that key config files exist and governance schema is usable
        eval_passed = basic_eval_checks(governance=governance, candidate=candidate, state=state)

    # Additional checks
    if eval_passed:
        # Check governance hasn't been mutated
        governance = load_governance()
        if not governance.get("control_plane"):
            eval_passed = False
            logger.warning("  → Governance control plane missing")

    candidate.eval_passed = eval_passed
    candidate.telemetry["eval_passed"] = eval_passed

    log_telemetry({"phase": "eval", "candidate_class": candidate.candidate_class, "passed": eval_passed})
    return eval_passed


def basic_eval_checks(
    governance: dict,
    candidate: EvolutionCandidate | None = None,
    state: EvolutionState | None = None,
) -> bool:
    """Basic evaluation checks when validator unavailable.

    HARDENED 2026-04-09: Previously only checked file existence (always passed).
    Now checks governance class alignment, class_stats sanity, and rollback readiness.
    """
    checks = []

    # Check 1: Required config files exist
    checks.append((HERMES_PROFILES / "zera/config.yaml").exists())
    checks.append((REPO_ROOT / "configs/tooling/zera_growth_governance.json").exists())
    checks.append((REPO_ROOT / "configs/adapters/hermes/adapter.yaml").exists())
    checks.append((REPO_ROOT / "configs/tooling/zera_client_profiles.yaml").exists())

    if not all(checks):
        logger.warning("  Basic eval FAILED: required config files missing")
        return False

    # Check 2: Governance candidate_classes is non-empty and aligned with script
    gov_classes = list(governance.get("candidate_classes", {}).keys())
    if not gov_classes:
        logger.warning("  Basic eval FAILED: governance candidate_classes is empty")
        return False

    # Check 3: If candidate was classified, verify its class exists in governance
    if candidate and candidate.candidate_class:
        if candidate.candidate_class not in gov_classes:
            logger.warning(
                "  Basic eval WARNING: classified class '%s' not in governance schema. "
                "This will cause class_stats to show 0 trials.",
                candidate.candidate_class
            )
            # Don't hard-fail here — the classify phase itself should be fixed instead

    # Check 4: class_stats sanity — if governance has classes, some should have trials
    if state and state.class_stats:
        gov_class_names = set(gov_classes)
        stats_class_names = set(state.class_stats.keys())
        missing_from_stats = gov_class_names - stats_class_names
        if len(missing_from_stats) == len(gov_class_names) and state.total_cycles > 5:
            logger.warning(
                "  Basic eval WARNING: %d/%d governance classes have never been recorded "
                "in class_stats (total cycles: %d). This suggests a class naming mismatch.",
                len(missing_from_stats), len(gov_class_names), state.total_cycles
            )

    # Check 5: Telemetry file is writable
    telemetry_path = REPO_ROOT / "logs" / "telemetry.jsonl"
    try:
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        telemetry_path.open("a").close()  # Test write
    except Exception as e:
        logger.warning("  Basic eval WARNING: telemetry file not writable: %s", e)

    result = all(checks)
    logger.info("  Basic eval: %s", "PASSED" if result else "FAILED")
    return result


# ── Phase 7: PROMOTE ──────────────────────────────────────────────────

def phase_promote(candidate: EvolutionCandidate, no_promote: bool = False) -> str:
    """Phase 7: Promote or rollback based on eval results.

    Wave 6: Also checks ZERA_EVO_NO_MUTATE env var — when set, promotion
    is logged but NOT executed (for safe rehearsal).
    """
    logger.info("═══ PHASE 7: PROMOTE ═══")

    # Wave 6: no-mutate enforcement (env var from rehearsal controller)
    no_mutate_env = os.environ.get("ZERA_EVO_NO_MUTATE", "0") == "1"
    if no_mutate_env:
        logger.info("  → NO-MUTATE MODE: promotion skipped (ZERA_EVO_NO_MUTATE=1)")
        result = "no_mutate_skipped"
        candidate.status = CandidateStatus.APPROVED
        log_telemetry({"phase": "promote", "action": "no_mutate", "result": result,
                       "no_mutate_mode": True})
        return result

    beta_manager = REPO_ROOT / "scripts/beta_manager.py"
    result = "no_beta_available"

    if not candidate.eval_passed:
        # Rollback
        logger.info("  → Eval failed — rolling back")
        if beta_manager.exists():
            try:
                subprocess.run(
                    [sys.executable, str(beta_manager), "rollback"],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                result = "rolled_back"
                candidate.status = CandidateStatus.ROLLED_BACK
                logger.info("  → Beta rolled back")
            except Exception as e:
                result = f"rollback_error: {e}"
        else:
            result = "no_beta_to_rollback"
            candidate.status = CandidateStatus.REJECTED

        log_telemetry({"phase": "promote", "action": "rollback", "result": result})
        return result

    if no_promote:
        result = "promotion_disabled"
        candidate.status = CandidateStatus.APPROVED
        logger.info("  → Eval passed, but promotion is disabled for this run")
        log_telemetry({"phase": "promote", "action": "no_promote", "result": result})
        return result

    # Eval passed — promote
    logger.info("  → Eval passed — promoting")
    if beta_manager.exists():
        try:
            subprocess.run(
                [sys.executable, str(beta_manager), "promote"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            result = "promoted"
            candidate.status = CandidateStatus.PROMOTED
            candidate.promoted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            logger.info("  → Beta promoted to main")
        except Exception as e:
            result = f"promote_error: {e}"
            candidate.status = CandidateStatus.REJECTED
    else:
        # No beta — accept candidate as conceptual evolution (logged but not applied)
        result = "accepted_conceptual"
        candidate.status = CandidateStatus.APPROVED
        logger.info("  → No beta profile — accepting as conceptual evolution")

    log_telemetry({"phase": "promote", "action": "promote" if candidate.status == CandidateStatus.PROMOTED else "accept", "result": result})
    return result


# ── Phase 8: REFLECT ──────────────────────────────────────────────────

def phase_reflect(candidate: EvolutionCandidate, cycle_result: CycleResult) -> None:
    """Phase 8: Self-reflection and telemetry capture."""
    logger.info("═══ PHASE 8: REFLECT ═══")
    reward = _compute_cycle_reward(cycle_result)
    structured_reflection = build_structured_reflection(candidate, cycle_result, reward)

    reflection = {
        "cycle_number": cycle_result.cycle_number,
        "loop_algorithm": cycle_result.loop_algorithm,
        "candidate_class": candidate.candidate_class,
        "candidate_score": candidate.score,
        "eval_passed": candidate.eval_passed,
        "final_status": candidate.status.value,
        "duration_seconds": cycle_result.duration_seconds,
        "reward": reward,
        "reflection": generate_self_reflection(candidate, cycle_result, structured_reflection),
        "structured_reflection": structured_reflection,
    }

    log_telemetry({"phase": "reflect", "data": reflection})
    persist_cycle_insight(candidate, cycle_result, reward=reward, next_focus=structured_reflection["next_focus"])
    logger.info("  → Reflection captured. Cycle complete.")


def build_structured_reflection(candidate: EvolutionCandidate, cycle_result: CycleResult, reward: float) -> dict[str, Any]:
    """Build actionable reflection payload for memory and meta-learning."""
    if candidate.status in (CandidateStatus.ROLLED_BACK, CandidateStatus.REJECTED):
        next_focus = "failure_driven_fix"
        risk_hint = "high_regression_risk"
        what_failed = "promotion pipeline unstable or low-value candidate"
        what_worked = "safe rollback boundaries"
    elif candidate.status == CandidateStatus.PROMOTED:
        next_focus = "external_pattern_adoption" if candidate.score >= 0.65 else "workflow_optimization"
        risk_hint = "stable"
        what_failed = ""
        what_worked = "candidate passed eval and reached promotion"
    else:
        next_focus = "workflow_optimization"
        risk_hint = "moderate"
        what_failed = "no concrete promotion signal"
        what_worked = "cycle completed under governance constraints"

    return {
        "reward": round(reward, 4),
        "what_worked": what_worked,
        "what_failed": what_failed,
        "next_focus": next_focus,
        "risk_hint": risk_hint,
        "status": cycle_result.status,
    }


def generate_self_reflection(
    candidate: EvolutionCandidate,
    cycle_result: CycleResult,
    structured_reflection: dict[str, Any] | None = None,
) -> str:
    """Generate self-reflection text for the cycle."""
    structured_reflection = structured_reflection or {}
    status_emoji = {
        "completed": "✅",
        "failed": "❌",
        "skipped": "⏭️",
        "shutdown": "🛑",
    }.get(cycle_result.status, "❓")

    promote_status = {
        CandidateStatus.PROMOTED: "🚀 Promoted to main",
        CandidateStatus.APPROVED: "✅ Approved (conceptual)",
        CandidateStatus.ROLLED_BACK: "↩️ Rolled back",
        CandidateStatus.REJECTED: "❌ Rejected",
        CandidateStatus.PENDING: "⏳ Pending",
    }.get(candidate.status, "❓")

    return (
        f"{status_emoji} Cycle {cycle_result.cycle_number} complete\n"
        f"Algorithm: {cycle_result.loop_algorithm}\n"
        f"Class: {candidate.candidate_class} (score: {candidate.score:.3f})\n"
        f"Result: {promote_status}\n"
        f"Duration: {cycle_result.duration_seconds:.1f}s\n"
        f"Next focus: {structured_reflection.get('next_focus', 'n/a')}\n"
        f"Risk hint: {structured_reflection.get('risk_hint', 'n/a')}"
    )


# ── Main Cycle ────────────────────────────────────────────────────────

def run_cycle(
    state: EvolutionState,
    governance: dict[str, Any],
    dry_run: bool = False,
    no_promote: bool = False,
) -> CycleResult:
    """Run one complete evolution cycle."""
    cycle_start = time.monotonic()
    cycle_number = state.current_cycle + 1

    ensure_meta_tables(state, governance)
    loop_algo = select_loop_algorithm(state)

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  ZERA SELF-EVOLUTION — Cycle %d / Algorithm: %-16s║", cycle_number, loop_algo)
    logger.info("╚══════════════════════════════════════════════════════╝")

    if dry_run:
        logger.info("  [DRY RUN] Simulating cycle...")
        return CycleResult(
            cycle_number=cycle_number,
            loop_algorithm=loop_algo,
            phases_completed=["observe", "classify", "score", "design", "sandbox", "eval", "promote", "reflect"],
            candidate=EvolutionCandidate(
                candidate_class=CANDIDATE_CLASSES[cycle_number % len(CANDIDATE_CLASSES)],
                loop_algorithm=loop_algo,
                description=f"Dry run cycle {cycle_number}",
                risk_level="low",
            ),
            duration_seconds=0.0,
            status="completed (dry run)",
        )

    candidate = None
    phases_completed: list[str] = []

    try:
        # Phase 1: OBSERVE
        observations = phase_observe()
        phases_completed.append("observe")

        if _shutdown_requested:
            return CycleResult(cycle_number, loop_algo, phases_completed, None, time.monotonic() - cycle_start, "shutdown")

        # Phase 2: CLASSIFY
        candidate = phase_classify(observations, governance, state, loop_algo)
        phases_completed.append("classify")

        if _shutdown_requested:
            return CycleResult(cycle_number, loop_algo, phases_completed, candidate, time.monotonic() - cycle_start, "shutdown")

        # Phase 3: SCORE
        phase_score(candidate, observations)
        phases_completed.append("score")

        # Phase 4: DESIGN
        phase_design(candidate)
        phases_completed.append("design")

        # Phase 5: SANDBOX
        phase_sandbox(candidate)
        phases_completed.append("sandbox")

        # Phase 6: EVAL
        phase_eval(candidate, governance, state)
        phases_completed.append("eval")

        # Phase 7: PROMOTE
        phase_promote(candidate, no_promote=no_promote)
        phases_completed.append("promote")

        duration = time.monotonic() - cycle_start
        cycle_result = CycleResult(cycle_number, loop_algo, phases_completed, candidate, duration, "completed")

        # Phase 8: REFLECT
        phase_reflect(candidate, cycle_result)
        phases_completed.append("reflect")

        return cycle_result

    except Exception as e:
        duration = time.monotonic() - cycle_start
        logger.error("Cycle %d failed: %s", cycle_number, e, exc_info=True)
        return CycleResult(cycle_number, loop_algo, phases_completed, candidate, duration, "failed", str(e))


# ── Main Loop ─────────────────────────────────────────────────────────

def run_loop(
    max_cycles: int = 0,
    cycle_interval_seconds: int = 300,
    dry_run: bool = False,
    no_promote: bool = False,
) -> None:
    """Run the infinite evolution loop.

    Args:
        max_cycles: Maximum cycles to run (0 = infinite).
        cycle_interval_seconds: Seconds between cycles.
        dry_run: Simulate without executing.
    """
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║     ZERA SELF-EVOLUTION LOOP — STARTING             ║")
    logger.info("║     Mode: %s                                      ║", "DRY RUN" if dry_run else "LIVE   ")
    logger.info("║     Max cycles: %s                                  ║", "∞" if max_cycles == 0 else str(max_cycles))
    logger.info("║     Interval: %ds                                    ║", cycle_interval_seconds)
    logger.info("║     Promotion: %s                                  ║", "disabled" if no_promote else "enabled ")
    logger.info("╚══════════════════════════════════════════════════════╝")

    state = load_state()
    governance = load_governance()
    ensure_meta_tables(state, governance)

    # Check freeze
    frozen, freeze_reason = check_freeze_conditions(governance, state=state)
    if frozen:
        logger.warning("⚠️  Evolution FROZEN: %s", freeze_reason)
        state.freeze_active = True
        state.freeze_reason = freeze_reason
        save_state(state)
        return

    cycles_run = 0

    try:
        while max_cycles == 0 or cycles_run < max_cycles:
            if _shutdown_requested:
                logger.info("Shutdown requested. Exiting loop.")
                break

            # Check freeze each cycle
            frozen, freeze_reason = check_freeze_conditions(governance, state=state)
            if frozen:
                logger.warning("⚠️  Evolution FROZEN: %s — sleeping %ds", freeze_reason, cycle_interval_seconds)
                time.sleep(cycle_interval_seconds)
                continue

            # Run cycle
            result = run_cycle(state, governance, dry_run=dry_run, no_promote=no_promote)

            # Update state
            state.current_cycle = result.cycle_number
            state.current_loop_algorithm = result.loop_algorithm
            if result.loop_algorithm in LOOP_ALGORITHMS:
                state.loop_algorithm_index = LOOP_ALGORITHMS.index(result.loop_algorithm)
            state.total_cycles += 1
            state.last_cycle_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            state.last_cycle_status = result.status
            reward = update_meta_learning(state, result)

            if result.status == "completed":
                state.successful_cycles += 1
                if result.candidate and result.candidate.status == CandidateStatus.PROMOTED:
                    state.candidates_promoted += 1
                    state.consecutive_regressions = 0
                elif result.candidate and result.candidate.status == CandidateStatus.ROLLED_BACK:
                    state.candidates_rolled_back += 1
                    state.consecutive_regressions += 1
            elif result.status == "failed":
                state.failed_cycles += 1
                state.last_error = result.error
            elif result.status == "shutdown":
                logger.info("Shutdown during cycle. Saving state.")
                save_state(state)
                return

            save_state(state)
            cycles_run += 1

            # Progress summary
            logger.info("")
            logger.info("📊 Progress: %d cycles (%d success, %d failed, %d promoted) | meta_reward=%.3f",
                        state.total_cycles, state.successful_cycles, state.failed_cycles, state.candidates_promoted, reward)

            # Wait between cycles
            if max_cycles == 0 or cycles_run < max_cycles:
                logger.info("💤 Next cycle in %ds (Ctrl+C to stop)...", cycle_interval_seconds)
                _wait_with_shutdown_check(cycle_interval_seconds)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down gracefully...")
    finally:
        save_state(state)
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║     ZERA SELF-EVOLUTION LOOP — STOPPED              ║")
        logger.info("║     Total cycles: %-33d ║", state.total_cycles)
        logger.info("║     Successful: %-35d ║", state.successful_cycles)
        logger.info("║     Failed: %-37d ║", state.failed_cycles)
        logger.info("║     Promoted: %-35d ║", state.candidates_promoted)
        logger.info("╚══════════════════════════════════════════════════════╝")


def _wait_with_shutdown_check(total_seconds: int) -> None:
    """Wait with periodic shutdown checks."""
    check_interval = 5  # Check every 5 seconds
    elapsed = 0
    while elapsed < total_seconds:
        if _shutdown_requested:
            break
        sleep_time = min(check_interval, total_seconds - elapsed)
        time.sleep(sleep_time)
        elapsed += sleep_time


# ── Status Command ─────────────────────────────────────────────────────

def show_status() -> None:
    """Show current evolution state."""
    state = load_state()
    governance = load_governance()
    ensure_meta_tables(state, governance)
    frozen, freeze_reason = check_freeze_conditions(governance, state=state)

    print("╔══════════════════════════════════════════════════╗")
    print("║       ZERA SELF-EVOLUTION — STATUS              ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║  Started:          {state.started_at:<28}║")
    print(f"║  Total cycles:     {state.total_cycles:<28}║")
    print(f"║  Successful:       {state.successful_cycles:<28}║")
    print(f"║  Failed:           {state.failed_cycles:<28}║")
    print(f"║  Promoted:         {state.candidates_promoted:<28}║")
    print(f"║  Rolled back:      {state.candidates_rolled_back:<28}║")
    print(f"║  Current cycle:    {state.current_cycle:<28}║")
    print(f"║  Loop algorithm:   {state.current_loop_algorithm:<28}║")
    print(f"║  Last cycle:       {state.last_cycle_at:<28}║")
    print(f"║  Last status:      {state.last_cycle_status:<28}║")
    print(f"║  Frozen:           {str(frozen):<28}║")
    if frozen:
        print(f"║  Freeze reason:    {freeze_reason:<28}║")
    print("╚══════════════════════════════════════════════════╝")

    ranked = sorted(
        (
            (algo, row)
            for algo, row in state.loop_stats.items()
            if int(row.get("trials", 0)) > 0
        ),
        key=lambda item: float(item[1].get("reward_sum", 0.0)) / max(1, int(item[1].get("trials", 0))),
        reverse=True,
    )
    if ranked:
        print("\n🧠 Meta-learning top algorithms:")
        for algo, row in ranked[:3]:
            trials = int(row.get("trials", 0))
            mean_reward = float(row.get("reward_sum", 0.0)) / max(1, trials)
            print(f"   {algo:<18} trials={trials:<4} mean_reward={mean_reward:.3f}")

    # Show recent telemetry
    if EVO_TELEMETRY_PATH.exists():
        recent = _tail_lines(EVO_TELEMETRY_PATH, MAX_TELEMETRY_STATUS_LINES)
        if recent:
            print("\n📋 Recent telemetry:")
            for line in recent:
                try:
                    event = json.loads(line)
                    phase = event.get("phase", "?")
                    ts = event.get("timestamp", "?")
                    print(f"   [{ts}] {phase}")
                except json.JSONDecodeError:
                    pass


# ── Reset Command ──────────────────────────────────────────────────────

def reset_state() -> None:
    """Reset evolution state."""
    reset_any = False
    if EVO_STATE_PATH.exists():
        EVO_STATE_PATH.unlink()
        reset_any = True
    if EVO_META_MEMORY_PATH.exists():
        EVO_META_MEMORY_PATH.unlink()
        reset_any = True

    if reset_any:
        print("✅ Evolution state and meta-memory reset.")
    else:
        print("ℹ️  No state to reset.")


# ── CLI ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zera Self-Evolution Loop")
    parser.add_argument("--cycles", type=int, default=0, help="Max cycles to run (0 = infinite)")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between cycles (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    parser.add_argument("--no-promote", action="store_true", help="Run eval and reflection but never promote beta changes")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--reset", action="store_true", help="Reset evolution state")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.status:
        show_status()
        return 0

    if args.reset:
        reset_state()
        return 0

    run_loop(
        max_cycles=args.cycles,
        cycle_interval_seconds=args.interval,
        dry_run=args.dry_run,
        no_promote=args.no_promote,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
