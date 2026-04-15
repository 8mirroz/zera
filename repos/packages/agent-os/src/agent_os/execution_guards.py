"""
Execution Guards — Runtime Enforcement of Execution Truth Contract.

This module provides:
- Pre-flight response validation (claims must be grounded in tool results)
- Post-flight grounding check (response must match actual tool results)
- Stall detection with timeout and likely cause classification
- Heartbeat emission during executing state
- Violation tracking with escalation

Enforcement points:
1. pre_response_validation — before response is emitted
2. post_response_validation — after response is emitted
3. tool_result_processing — after tool result received
4. completion_gate — at task completion

Usage:
    guards = ExecutionGuards.from_config(repo_root)
    
    # Pre-flight
    violations = guards.preflight_validate(response_text, tool_results)
    if violations:
        handle_violations(violations)
    
    # Post-flight
    grounding = guards.postflight_check(response_text, tool_results, filesystem_root)
    if not grounding.passed:
        handle_grounding_failure(grounding)
    
    # Stall detection
    stall_detector = StallDetector(timeout_seconds=20)
    stall_detector.signal_progress("tool_call_executed")
    if stall_detector.is_stalled():
        handle_stall(stall_detector.get_stall_event())
    
    # Heartbeat
    heartbeat = HeartbeatEmitter(interval_seconds=15)
    if heartbeat.should_emit():
        emit(heartbeat.create_payload(state, step, last_tool))
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class ViolationLevel(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    UNVERIFIED_COMPLETION_CLAIM = "unverified_completion_claim"
    MISSING_FILESYSTEM_EVIDENCE = "missing_filesystem_evidence"
    FABRICATED_EVIDENCE = "fabricated_evidence"
    NARRATE_WITHOUT_TOOL = "narrate_without_tool"
    MISSING_ARTIFACT_SUMMARY = "missing_artifact_summary"
    STALL_DETECTED = "stall_detected"
    STALL_PERSISTENT = "stall_persistent"
    HEARTBEAT_MISS = "heartbeat_miss"
    FORWARD_CLAIM = "forward_claim"


class ProgressSignal(str, Enum):
    TOOL_CALL_EXECUTED = "tool_call_executed"
    TOOL_RESULT_RECEIVED = "tool_result_received"
    FILESYSTEM_DIFF_DETECTED = "filesystem_diff_detected"
    ARTIFACT_CREATED = "artifact_created"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    STATE_TRANSITION = "state_transition"


class StallCause(str, Enum):
    WAITING_FOR_TOOL = "waiting_for_tool"
    NO_DIFF = "no_diff"
    REASONING_LOOP_STUCK = "reasoning_loop_stuck"
    TOOL_TIMEOUT = "tool_timeout"
    ORCHESTRATION_ERROR = "orchestration_error"


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class Violation:
    """A single guard violation."""
    
    violation_type: ViolationType
    level: ViolationLevel
    message: str
    claim_text: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: _utc_now_iso())


@dataclass
class ValidationResult:
    """Result of pre-flight or post-flight validation."""
    
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    retry_message: str = ""
    
    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.level == ViolationLevel.ERROR)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.level == ViolationLevel.CRITICAL)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.level == ViolationLevel.WARNING)


@dataclass
class GroundingResult:
    """Result of tool-grounded response check."""
    
    passed: bool
    grounded_claims: int = 0
    ungrounded_claims: int = 0
    ungrounded_details: list[dict[str, str]] = field(default_factory=list)
    filesystem_verified: bool = True
    filesystem_failures: list[dict[str, str]] = field(default_factory=list)


@dataclass
class StallEvent:
    """Emitted when stall is detected."""
    
    run_id: str
    stalled_at: str
    last_progress_signal: str
    last_known_state: str
    last_tool_call: str | None
    last_tool_result: str | None
    stall_duration_seconds: float
    likely_cause: StallCause
    recovery_attempted: bool = False


@dataclass
class HeartbeatPayload:
    """Heartbeat emitted during executing state."""
    
    run_id: str
    state: str
    current_step: int
    total_steps: int
    last_tool: str
    last_tool_status: str
    artifacts_created: int
    last_verified_change: str | None
    stall_seconds: float


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ============================================================================
# VIOLATION DETECTION PATTERNS
# ============================================================================

# Patterns that indicate ungrounded claims
UNVERIFIED_COMPLETION_PATTERNS = [
    r'(?i)created(?!.*(?:\/|path|directory|file|exists|evidence|verified))',
    r'(?i)(done|complete|finished)(?!.*(?:evidence|artifact|verified|summary))',
    r'(?i)all\s+(?:files?|directories?|configs?)\s+(?:created|done|ready)',
    r'(?i)(?:successfully|successfully)\s+(?:created|modified|deleted)(?!.*evidence)',
]

FORWARD_CLAIM_PATTERNS = [
    r'(?i)(?:will|going to|about to|next i\'ll)\s+(?:create|build|setup|configure|write)',
    r'(?i)(?:planning to|will now|next step)\s+(?:create|write|modify)',
]

NARRATIVE_WITHOUT_TOOL_PATTERNS = [
    r'(?i)(?:I\'m|I am)\s+(?:creating|building|setting up|configuring|writing|checking)',
    r'(?i)(?:now|currently)\s+(?:creating|building|setting up)',
    r'(?i)(?:continuing|proceeding|moving on)\s+(?:with|to)',
]

AGGREGATION_WITHOUT_COUNT_PATTERNS = [
    r'(?i)(?:all|every|both)\s+.*(?:created|done|complete|ready)(?!.*\d+)',
]

# Keywords that indicate filesystem claims
FILESYSTEM_CLAIM_KEYWORDS = [
    "created", "modified", "deleted", "directory", "directories",
    "file", "files", "folder", "path", "wrote", "written",
    "removed", "moved", "copied", "renamed",
]

# Evidence keywords
EVIDENCE_KEYWORDS = [
    "evidence", "verified", "confirmed", "exists", "output",
    "result", "found", "ls", "find", "cat", "diff", "test",
    "```", "bash", "$", "verified:", "evidence:",
]


# ============================================================================
# PRE-FLIGHT RESPONSE VALIDATOR
# ============================================================================


class PreflightValidator:
    """Validates response before it is emitted.
    
    Checks that all claims in the response are grounded in tool results.
    """
    
    def __init__(
        self,
        forbid_unverified: bool = True,
        require_filesystem_evidence: bool = True,
        check_forward_claims: bool = True,
        check_aggregation: bool = True,
        evidence_required_for: list[str] | None = None,
    ) -> None:
        self.forbid_unverified = forbid_unverified
        self.require_filesystem_evidence = require_filesystem_evidence
        self.check_forward_claims = check_forward_claims
        self.check_aggregation = check_aggregation
        self.evidence_required_for = evidence_required_for or [
            "filesystem_operations",
            "code_execution",
            "test_results",
            "api_responses",
            "configuration_changes",
        ]
    
    def validate(
        self,
        response_text: str,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> ValidationResult:
        """Validate response text against tool results.
        
        Args:
            response_text: The agent's response text.
            tool_results: List of tool results from current session.
        
        Returns:
            ValidationResult with any violations found.
        """
        violations: list[Violation] = []
        tool_results = tool_results or []
        has_evidence_block = self._has_evidence_block(response_text)
        
        # Check 1: Unverified completion claims
        if self.forbid_unverified:
            violations.extend(
                self._check_unverified_claims(response_text, has_evidence_block)
            )
        
        # Check 2: Filesystem evidence required
        if self.require_filesystem_evidence:
            violations.extend(
                self._check_filesystem_evidence(response_text, tool_results, has_evidence_block)
            )
        
        # Check 3: Forward claims (claiming future results)
        if self.check_forward_claims:
            violations.extend(
                self._check_forward_claims(response_text, tool_results)
            )
        
        # Check 4: Aggregation without count
        if self.check_aggregation:
            violations.extend(
                self._check_aggregation(response_text, tool_results)
            )
        
        # Check 5: Narrative without tool
        violations.extend(
            self._check_narrative_without_tool(response_text, tool_results)
        )
        
        passed = not any(
            v.level in (ViolationLevel.ERROR, ViolationLevel.CRITICAL)
            for v in violations
        )
        
        retry_message = ""
        if not passed:
            retry_message = self._build_retry_message(violations)
        
        return ValidationResult(
            passed=passed,
            violations=violations,
            retry_message=retry_message,
        )
    
    def _has_evidence_block(self, text: str) -> bool:
        """Check if response contains an evidence block (code fence with command/output)."""
        return bool(re.search(r'```(?:bash|shell|text)?\s*\$|```(?:bash|shell|text)?\s*\w+', text))
    
    def _check_unverified_claims(
        self, text: str, has_evidence: bool
    ) -> list[Violation]:
        """Check for completion claims without evidence."""
        violations = []
        if has_evidence:
            return violations
        
        for pattern in UNVERIFIED_COMPLETION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(Violation(
                    violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
                    level=ViolationLevel.ERROR,
                    message="Completion claim without evidence block",
                    claim_text=match.group(0),
                ))
        
        return violations
    
    def _check_filesystem_evidence(
        self, text: str, tool_results: list[dict], has_evidence: bool
    ) -> list[Violation]:
        """Check for filesystem claims without evidence."""
        violations = []
        has_fs_claim = any(
            kw.lower() in text.lower() for kw in FILESYSTEM_CLAIM_KEYWORDS
        )
        
        if not has_fs_claim:
            return violations
        
        # If evidence block present, check if it contains filesystem verification
        if has_evidence:
            has_fs_evidence = any(
                kw.lower() in text.lower() for kw in EVIDENCE_KEYWORDS
            )
            if not has_fs_evidence:
                violations.append(Violation(
                    violation_type=ViolationType.MISSING_FILESYSTEM_EVIDENCE,
                    level=ViolationLevel.ERROR,
                    message="Filesystem claim without path verification",
                ))
        else:
            # No evidence block at all
            violations.append(Violation(
                violation_type=ViolationType.MISSING_FILESYSTEM_EVIDENCE,
                level=ViolationLevel.ERROR,
                message="Filesystem claim without any evidence",
            ))
        
        return violations
    
    def _check_forward_claims(
        self, text: str, tool_results: list[dict]
    ) -> list[Violation]:
        """Check for claims about future steps not yet executed."""
        violations = []
        for pattern in FORWARD_CLAIM_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # Forward claims are warnings unless tool results are empty
                # (meaning nothing has been done yet)
                if not tool_results:
                    violations.append(Violation(
                        violation_type=ViolationType.FORWARD_CLAIM,
                        level=ViolationLevel.WARNING,
                        message="Planning future work — OK if no tools executed yet",
                        claim_text=match.group(0),
                    ))
        
        return violations
    
    def _check_aggregation(
        self, text: str, tool_results: list[dict]
    ) -> list[Violation]:
        """Check for aggregated claims without specific count."""
        violations = []
        for pattern in AGGREGATION_WITHOUT_COUNT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(Violation(
                    violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
                    level=ViolationLevel.ERROR,
                    message="Aggregated claim without verification count",
                    claim_text=match.group(0),
                ))
        
        return violations
    
    def _check_narrative_without_tool(
        self, text: str, tool_results: list[dict]
    ) -> list[Violation]:
        """Check for narrative action without tool execution."""
        violations = []
        for pattern in NARRATIVE_WITHOUT_TOOL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(Violation(
                    violation_type=ViolationType.NARRATE_WITHOUT_TOOL,
                    level=ViolationLevel.WARNING,
                    message="Narrative action without tool execution",
                    claim_text=match.group(0),
                ))
        
        return violations
    
    def _build_retry_message(self, violations: list[Violation]) -> str:
        """Build retry message from violations."""
        errors = [v for v in violations if v.level == ViolationLevel.ERROR]
        if errors:
            types = set(v.violation_type.value for v in errors)
            if ViolationType.UNVERIFIED_COMPLETION_CLAIM.value in types:
                return "Response rejected: completion claim not supported by tool results. Add evidence block."
            if ViolationType.MISSING_FILESYSTEM_EVIDENCE.value in types:
                return "Response rejected: filesystem claim without evidence. Include path verification (ls/find/test)."
            if ViolationType.FORWARD_CLAIM.value in types:
                return "Warning: claiming results from future steps. Only report what has been verified."
        return "Response rejected: validation failed. See violations for details."


# ============================================================================
# POST-FLIGHT GROUNDING CHECKER
# ============================================================================


class PostflightGroundingChecker:
    """Validates response after it is emitted.
    
    Checks that file claims match actual filesystem state.
    """
    
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path.cwd()
    
    def check(
        self,
        response_text: str,
        tool_results: list[dict[str, Any]] | None = None,
        filesystem_root: Path | None = None,
    ) -> GroundingResult:
        """Check response grounding.
        
        Args:
            response_text: The agent's response.
            tool_results: Tool results from current session.
            filesystem_root: Root path for filesystem verification.
        
        Returns:
            GroundingResult with verification status.
        """
        tool_results = tool_results or []
        fs_root = filesystem_root or self.repo_root
        
        grounded_claims = 0
        ungrounded_claims = 0
        ungrounded_details: list[dict[str, str]] = []
        
        # Extract path claims from response
        claimed_paths = self._extract_path_claims(response_text)
        
        for path_str in claimed_paths:
            path = Path(path_str) if Path(path_str).is_absolute() else fs_root / path_str
            
            # Check if path exists in tool results
            tool_confirmed = self._path_in_tool_results(path_str, tool_results)
            fs_verified = path.exists()
            
            if tool_confirmed or fs_verified:
                grounded_claims += 1
            else:
                ungrounded_claims += 1
                ungrounded_details.append({
                    "path": str(path),
                    "claim": "created/modified",
                    "tool_confirmed": str(tool_confirmed),
                    "fs_verified": str(fs_verified),
                })
        
        # Check filesystem claims against actual filesystem
        fs_verified = True
        fs_failures: list[dict[str, str]] = []
        fs_claims = self._extract_filesystem_claims(response_text)
        
        for claim in fs_claims:
            path_str = claim.get("path", "")
            if not path_str:
                continue
            
            path = Path(path_str) if Path(path_str).is_absolute() else fs_root / path_str
            action = claim.get("action", "created")
            
            if action in ("created", "modified"):
                if not path.exists():
                    fs_verified = False
                    fs_failures.append({
                        "path": str(path),
                        "action": action,
                        "status": "not_found",
                    })
        
        passed = ungrounded_claims == 0 and fs_verified
        
        return GroundingResult(
            passed=passed,
            grounded_claims=grounded_claims,
            ungrounded_claims=ungrounded_claims,
            ungrounded_details=ungrounded_details,
            filesystem_verified=fs_verified,
            filesystem_failures=fs_failures,
        )
    
    def _extract_path_claims(self, text: str) -> list[str]:
        """Extract path claims from response text."""
        paths = []
        # Match absolute paths
        paths.extend(re.findall(r'(?:/[\w./_-]+(?:/\w+)*)', text))
        # Match paths in code blocks
        for match in re.finditer(r'```.*?\n(.*?)```', text, re.DOTALL):
            paths.extend(re.findall(r'(?:/[\w./_-]+(?:/\w+)*)', match.group(1)))
        return list(set(paths))
    
    def _path_in_tool_results(
        self, path_str: str, tool_results: list[dict]
    ) -> bool:
        """Check if path is confirmed in tool results."""
        for result in tool_results:
            output = str(result.get("output", "")) + str(result.get("result", ""))
            if path_str in output:
                return True
        return False
    
    def _extract_filesystem_claims(self, text: str) -> list[dict[str, str]]:
        """Extract filesystem claims from response text."""
        claims = []
        for line in text.split('\n'):
            line_lower = line.lower()
            if any(kw in line_lower for kw in FILESYSTEM_CLAIM_KEYWORDS):
                paths = re.findall(r'(?:/[\w./_-]+(?:/\w+)*)', line)
                for path in paths:
                    action = "unknown"
                    if "creat" in line_lower:
                        action = "created"
                    elif "modif" in line_lower or "edit" in line_lower:
                        action = "modified"
                    elif "delet" in line_lower or "remov" in line_lower:
                        action = "deleted"
                    claims.append({"path": path, "action": action})
        return claims


# ============================================================================
# STALL DETECTOR
# ============================================================================


class StallDetector:
    """Detects stalls in agent execution.
    
    Monitors progress signals and triggers stall events when no progress
    is detected within the timeout window.
    """
    
    def __init__(
        self,
        timeout_seconds: float = 20.0,
        max_duration_seconds: float = 60.0,
        run_id: str = "unknown",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_duration_seconds = max_duration_seconds
        self.run_id = run_id
        
        self._last_progress_time = time.monotonic()
        self._last_progress_signal: ProgressSignal | None = None
        self._stall_start_time: float | None = None
        self._last_known_state = "planning"
        self._last_tool_call: str | None = None
        self._last_tool_result: str | None = None
    
    def signal_progress(self, signal: ProgressSignal, **context: Any) -> None:
        """Reset stall timer — progress detected."""
        self._last_progress_time = time.monotonic()
        self._last_progress_signal = signal
        self._stall_start_time = None
        
        # Update context from signal
        if "state" in context:
            self._last_known_state = context["state"]
        if "tool_call" in context:
            self._last_tool_call = context["tool_call"]
        if "tool_result" in context:
            self._last_tool_result = context["tool_result"]
    
    def set_state(self, state: str) -> None:
        """Update last known state."""
        self._last_known_state = state
    
    def set_tool_call(self, tool_call: str) -> None:
        """Record last tool call."""
        self._last_tool_call = tool_call
    
    def set_tool_result(self, tool_result: str) -> None:
        """Record last tool result."""
        self._last_tool_result = tool_result
    
    def is_stalled(self) -> bool:
        """Check if currently stalled."""
        if self._stall_start_time is None:
            elapsed = time.monotonic() - self._last_progress_time
            if elapsed >= self.timeout_seconds:
                self._stall_start_time = time.monotonic() - self.timeout_seconds
                return True
            return False
        return True
    
    def stall_duration(self) -> float:
        """Get current stall duration in seconds (total time since last progress)."""
        elapsed = time.monotonic() - self._last_progress_time
        if elapsed < self.timeout_seconds:
            return 0.0
        return elapsed
    
    def is_persistent(self) -> bool:
        """Check if stall has persisted beyond max duration."""
        return self.stall_duration() >= self.max_duration_seconds
    
    def get_stall_event(self) -> StallEvent | None:
        """Get stall event if stalled."""
        if not self.is_stalled():
            return None
        
        likely_cause = self._classify_stall_cause()
        
        return StallEvent(
            run_id=self.run_id,
            stalled_at=_utc_now_iso(),
            last_progress_signal=self._last_progress_signal.value if self._last_progress_signal else "none",
            last_known_state=self._last_known_state,
            last_tool_call=self._last_tool_call,
            last_tool_result=self._last_tool_result,
            stall_duration_seconds=self.stall_duration(),
            likely_cause=likely_cause,
        )
    
    def recover(self) -> None:
        """Reset stall state after recovery."""
        self._stall_start_time = None
        self._last_progress_time = time.monotonic()
    
    def _classify_stall_cause(self) -> StallCause:
        """Classify likely cause of stall."""
        state = self._last_known_state
        
        if state in ("executing", "verifying"):
            if self._last_tool_call and not self._last_tool_result:
                return StallCause.WAITING_FOR_TOOL
            if self._last_tool_result:
                return StallCause.NO_DIFF
            return StallCause.REASONING_LOOP_STUCK
        
        if state in ("planning", "reporting"):
            return StallCause.REASONING_LOOP_STUCK
        
        return StallCause.ORCHESTRATION_ERROR


# ============================================================================
# HEARTBEAT EMITTER
# ============================================================================


class HeartbeatEmitter:
    """Emits heartbeats during executing state.
    
    Tracks time since last heartbeat and emits when interval elapsed.
    """
    
    def __init__(
        self,
        interval_seconds: float = 15.0,
        run_id: str = "unknown",
    ) -> None:
        self.interval_seconds = interval_seconds
        self.run_id = run_id
        
        self._last_heartbeat = time.monotonic()
        self._miss_count = 0
    
    def should_emit(self) -> bool:
        """Check if heartbeat should be emitted now."""
        return (time.monotonic() - self._last_heartbeat) >= self.interval_seconds
    
    def emit(self) -> HeartbeatPayload | None:
        """Create heartbeat payload if interval elapsed."""
        if not self.should_emit():
            return None
        
        self._last_heartbeat = time.monotonic()
        self._miss_count = 0
        
        # Payload must be populated by caller
        return HeartbeatPayload(
            run_id=self.run_id,
            state="executing",
            current_step=0,
            total_steps=0,
            last_tool="",
            last_tool_status="unknown",
            artifacts_created=0,
            last_verified_change=None,
            stall_seconds=0.0,
        )
    
    def record_miss(self) -> int:
        """Record a missed heartbeat. Returns miss count."""
        self._miss_count += 1
        return self._miss_count
    
    def reset(self) -> None:
        """Reset heartbeat timer."""
        self._last_heartbeat = time.monotonic()
        self._miss_count = 0
    
    @property
    def miss_count(self) -> int:
        return self._miss_count


# ============================================================================
# CONTINUOUS HEARTBEAT MONITOR (Background Thread)
# ============================================================================


class HeartbeatMonitor:
    """Continuous background heartbeat monitor.
    
    Runs as a daemon thread, emitting heartbeats at the configured interval
    during the entire execution lifecycle. Unlike HeartbeatEmitter (one-shot),
    this provides continuous observability.
    
    Usage:
        monitor = HeartbeatMonitor(interval_seconds=15, run_id="run-001")
        monitor.start()  # Starts background thread
        
        # Later, when execution completes:
        monitor.stop()
        stats = monitor.get_stats()
    """
    
    def __init__(
        self,
        interval_seconds: float = 15.0,
        run_id: str = "unknown",
        stall_detector: StallDetector | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.run_id = run_id
        self.stall_detector = stall_detector
        
        self._thread: Any = None
        self._running = False
        self._emit_count = 0
        self._miss_count = 0
        self._last_heartbeat = time.monotonic()
        self._callback: Any = None
    
    def set_callback(self, callback) -> None:
        """Set a callback to invoke on each heartbeat.
        
        Callback signature: callback(HeartbeatPayload)
        """
        self._callback = callback
    
    def start(self) -> None:
        """Start the background heartbeat thread."""
        if self._running:
            return
        
        self._running = True
        self._last_heartbeat = time.monotonic()
        self._emit_count = 0
        self._miss_count = 0
        
        import threading
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"heartbeat-{self.run_id}",
            daemon=True,  # Dies with main thread
        )
        self._thread.start()
    
    def stop(self) -> dict[str, Any]:
        """Stop the background heartbeat thread and return stats."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        return self.get_stats()
    
    def get_stats(self) -> dict[str, Any]:
        """Get heartbeat statistics."""
        return {
            "run_id": self.run_id,
            "running": self._running,
            "emit_count": self._emit_count,
            "miss_count": self._miss_count,
            "interval_seconds": self.interval_seconds,
        }
    
    def _run_loop(self) -> None:
        """Background thread loop."""
        while self._running:
            now = time.monotonic()
            elapsed = now - self._last_heartbeat
            
            if elapsed >= self.interval_seconds:
                self._emit_heartbeat()
            
            # Sleep in small increments for responsive shutdown
            time.sleep(min(1.0, self.interval_seconds / 4))
    
    def _emit_heartbeat(self) -> None:
        """Emit a single heartbeat."""
        self._last_heartbeat = time.monotonic()
        self._emit_count += 1
        
        stall_seconds = 0.0
        stall_detected = False
        if self.stall_detector:
            stall_seconds = self.stall_detector.stall_duration()
            stall_detected = self.stall_detector.is_stalled()
        
        payload = HeartbeatPayload(
            run_id=self.run_id,
            state="executing",
            current_step=0,
            total_steps=0,
            last_tool="",
            last_tool_status="unknown",
            artifacts_created=0,
            last_verified_change=None,
            stall_seconds=stall_seconds,
        )
        
        if self._callback:
            try:
                self._callback(payload)
            except Exception:
                self._miss_count += 1
        
        # If stall detected, increment miss count
        if stall_detected:
            self._miss_count += 1


# ============================================================================
# VIOLATION TRACKER
# ============================================================================


class ViolationTracker:
    """Tracks violations and handles escalation."""
    
    def __init__(
        self,
        escalation_after: int = 3,
        run_id: str = "unknown",
    ) -> None:
        self.escalation_after = escalation_after
        self.run_id = run_id
        
        self._violations: list[Violation] = []
        self._counts: dict[ViolationType, int] = {}
    
    def record(self, violation: Violation) -> None:
        """Record a violation."""
        self._violations.append(violation)
        vtype = violation.violation_type
        self._counts[vtype] = self._counts.get(vtype, 0) + 1
    
    def should_escalate(self, violation_type: ViolationType) -> bool:
        """Check if violation count exceeds escalation threshold."""
        return self._counts.get(violation_type, 0) >= self.escalation_after
    
    def get_violations(self) -> list[Violation]:
        """Get all violations."""
        return self._violations.copy()
    
    def get_counts(self) -> dict[ViolationType, int]:
        """Get violation counts by type."""
        return self._counts.copy()
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of violations."""
        return {
            "total": len(self._violations),
            "by_type": {k.value: v for k, v in self._counts.items()},
            "by_level": {
                "warning": sum(1 for v in self._violations if v.level == ViolationLevel.WARNING),
                "error": sum(1 for v in self._violations if v.level == ViolationLevel.ERROR),
                "critical": sum(1 for v in self._violations if v.level == ViolationLevel.CRITICAL),
            },
            "escalation_pending": any(
                self.should_escalate(v.violation_type)
                for v in self._violations
            ),
        }


# ============================================================================
# ARTIFACT SUMMARY VALIDATOR
# ============================================================================


class ArtifactSummaryValidator:
    """Validates artifact summary on task completion."""
    
    REQUIRED_FIELDS = [
        "created",
        "modified",
        "failed",
        "verification",
    ]
    
    def validate(self, response_text: str) -> ValidationResult:
        """Check response contains artifact summary."""
        violations: list[Violation] = []
        
        # Check for artifact section
        has_artifacts = bool(re.search(r'(?i)(?:artifacts|summary|created:|modified:|failed:)', response_text))
        
        if not has_artifacts:
            violations.append(Violation(
                violation_type=ViolationType.MISSING_ARTIFACT_SUMMARY,
                level=ViolationLevel.ERROR,
                message="Response missing artifact summary",
            ))
        
        # Check for verification section
        has_verification = bool(re.search(r'(?i)(?:verification|verified|checks)', response_text))
        
        if not has_verification:
            violations.append(Violation(
                violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
                level=ViolationLevel.ERROR,
                message="Response missing verification summary",
            ))
        
        passed = not violations
        
        return ValidationResult(
            passed=passed,
            violations=violations,
            retry_message="Response rejected: missing artifact summary. Include created/modified/failed lists and verification results." if not passed else "",
        )


# ============================================================================
# MAIN EXECUTION GUARDS FACADE
# ============================================================================


class ExecutionGuards:
    """Main facade for all execution guards.
    
    Provides unified interface for pre-flight, post-flight, stall,
    heartbeat, and violation tracking.
    """
    
    def __init__(
        self,
        preflight: PreflightValidator | None = None,
        grounding: PostflightGroundingChecker | None = None,
        stall_detector: StallDetector | None = None,
        heartbeat: HeartbeatEmitter | None = None,
        violations: ViolationTracker | None = None,
        artifact_validator: ArtifactSummaryValidator | None = None,
    ) -> None:
        self.preflight = preflight or PreflightValidator()
        self.grounding = grounding or PostflightGroundingChecker()
        self.stall_detector = stall_detector or StallDetector()
        self.heartbeat = heartbeat or HeartbeatEmitter()
        self.violations = violations or ViolationTracker()
        self.artifact_validator = artifact_validator or ArtifactSummaryValidator()
    
    @classmethod
    def from_config(cls, repo_root: Path) -> "ExecutionGuards":
        """Create ExecutionGuards from configuration file.
        
        Args:
            repo_root: Repository root path.
        
        Returns:
            ExecutionGuards instance with config-loaded settings.
        """
        config_path = repo_root / "configs/tooling/execution_guards.yaml"
        
        defaults = {
            "forbid_unverified": True,
            "require_filesystem_evidence": True,
            "stall_timeout": 20.0,
            "stall_max_duration": 60.0,
            "heartbeat_interval": 15.0,
            "escalation_after": 3,
        }
        
        if config_path.exists():
            try:
                config_text = config_path.read_text(encoding="utf-8")
                config = parse_simple_yaml(config_text)
                guards = config.get("guards", {})
                defaults["forbid_unverified"] = guards.get("forbid_unverified_completion_claims", True)
                defaults["require_filesystem_evidence"] = guards.get("require_evidence_for_filesystem_claims", True)
                defaults["stall_timeout"] = guards.get("stall_timeout_seconds", 20.0)
                defaults["escalation_after"] = guards.get("escalation_after", 3)
                
                heartbeat_cfg = guards.get("require_heartbeat", {})
                defaults["heartbeat_interval"] = heartbeat_cfg.get("interval_seconds", 15.0)
            except Exception:
                pass
        
        return cls(
            preflight=PreflightValidator(
                forbid_unverified=defaults["forbid_unverified"],
                require_filesystem_evidence=defaults["require_filesystem_evidence"],
            ),
            grounding=PostflightGroundingChecker(repo_root),
            stall_detector=StallDetector(
                timeout_seconds=defaults["stall_timeout"],
                max_duration_seconds=defaults["stall_max_duration"],
            ),
            heartbeat=HeartbeatEmitter(
                interval_seconds=defaults["heartbeat_interval"],
            ),
            violations=ViolationTracker(
                escalation_after=defaults["escalation_after"],
            ),
        )
    
    def preflight_validate(
        self,
        response_text: str,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> ValidationResult:
        """Validate response before emission."""
        result = self.preflight.validate(response_text, tool_results)
        for violation in result.violations:
            self.violations.record(violation)
        return result
    
    def postflight_check(
        self,
        response_text: str,
        tool_results: list[dict[str, Any]] | None = None,
        filesystem_root: Path | None = None,
    ) -> GroundingResult:
        """Validate response after emission."""
        return self.grounding.check(response_text, tool_results, filesystem_root)
    
    def validate_completion_artifacts(self, response_text: str) -> ValidationResult:
        """Validate artifact summary at task completion."""
        result = self.artifact_validator.validate(response_text)
        for violation in result.violations:
            self.violations.record(violation)
        return result
    
    def signal_progress(self, signal: ProgressSignal, **context: Any) -> None:
        """Signal progress — resets stall timer."""
        self.stall_detector.signal_progress(signal, **context)
    
    def get_stall_event(self) -> StallEvent | None:
        """Get stall event if stalled."""
        return self.stall_detector.get_stall_event()
    
    def recover_from_stall(self) -> None:
        """Reset stall state."""
        self.stall_detector.recover()
    
    def get_violation_summary(self) -> dict[str, Any]:
        """Get summary of all violations."""
        return self.violations.get_summary()
    
    def should_escalate(self) -> bool:
        """Check if any violation requires escalation."""
        return self.violations.get_summary().get("escalation_pending", False)
