from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    PROVIDER_STARTUP = "provider_startup"
    STDIO_JSON_FAILURE = "stdio_json_failure"
    MCP_HANDSHAKE = "mcp_handshake"
    STALE_BRANCH = "stale_branch"
    COMPILE_FAILURE = "compile_failure"
    TEST_FAILURE = "test_failure"
    PLUGIN_STARTUP = "plugin_startup"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RecoveryResult:
    failure_type: FailureType
    attempted: bool
    recovered: bool
    degraded_mode: bool
    next_action: str
    event_payload: dict[str, Any]


def classify_failure(message: str) -> FailureType:
    low = str(message or "").lower()
    if "stdio" in low or "json" in low or "non-json" in low:
        return FailureType.STDIO_JSON_FAILURE
    if "mcp" in low and ("handshake" in low or "initialize" in low or "initialise" in low):
        return FailureType.MCP_HANDSHAKE
    if "stale" in low and ("branch" in low or "main" in low):
        return FailureType.STALE_BRANCH
    if "compile" in low or "typecheck" in low or "type check" in low:
        return FailureType.COMPILE_FAILURE
    if "pytest" in low or "test failed" in low or "tests failed" in low:
        return FailureType.TEST_FAILURE
    if "plugin" in low and ("startup" in low or "start" in low or "init" in low):
        return FailureType.PLUGIN_STARTUP
    if "provider" in low or "startup" in low or "binary not found" in low or "health probe" in low:
        return FailureType.PROVIDER_STARTUP
    return FailureType.UNKNOWN


def plan_recovery(
    failure_type: FailureType | str,
    *,
    run_id: str,
    runtime_provider: str,
    message: str,
) -> RecoveryResult:
    try:
        normalized = failure_type if isinstance(failure_type, FailureType) else FailureType(str(failure_type))
    except ValueError:
        normalized = FailureType.UNKNOWN
    next_actions = {
        FailureType.PROVIDER_STARTUP: "Run provider health checks, then fallback to the configured runtime provider.",
        FailureType.STDIO_JSON_FAILURE: "Treat the provider response as degraded, record the bad stdio JSON payload, then fallback.",
        FailureType.MCP_HANDSHAKE: "Enter degraded MCP mode for the failed server and continue with healthy servers when available.",
        FailureType.STALE_BRANCH: "Check branch freshness against main before broad verification and rebase only under policy.",
        FailureType.COMPILE_FAILURE: "Classify compile diagnostics, run the smallest targeted fix loop, then recompile.",
        FailureType.TEST_FAILURE: "Classify failing tests, rerun the smallest targeted test set, then escalate if still red.",
        FailureType.PLUGIN_STARTUP: "Disable the failing plugin hook for this run, report degraded plugin startup, then continue.",
        FailureType.UNKNOWN: "Record the failure class as unknown and use the configured fallback or escalation path.",
    }
    degraded_mode = normalized in {
        FailureType.STDIO_JSON_FAILURE,
        FailureType.MCP_HANDSHAKE,
        FailureType.PLUGIN_STARTUP,
    }

    event_payload = {
        "run_id": run_id,
        "component": "recovery",
        "status": "warn",
        "runtime_provider": runtime_provider,
        "message": f"Recovery planned for {normalized.value}",
        "data": {
            "failure_type": normalized.value,
            "attempted": True,
            "recovered": False,
            "degraded_mode": degraded_mode,
            "next_action": next_actions[normalized],
            "source_error": str(message),
        },
    }
    return RecoveryResult(
        failure_type=normalized,
        attempted=True,
        recovered=False,
        degraded_mode=degraded_mode,
        next_action=next_actions[normalized],
        event_payload=event_payload,
    )
