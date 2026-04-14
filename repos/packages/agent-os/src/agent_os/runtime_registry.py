from __future__ import annotations

import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .exceptions import RuntimeProviderUnavailableError
from .runtime_providers import (
    AgentOsPythonRuntimeProvider,
    ClawCodeRuntimeProvider,
    MlxLmRuntimeProvider,
    RuntimeProvider,
    ZeroClawRuntimeProvider,
)
from .source_trust import evaluate_source_tier_policy, load_source_trust_policy


# Lazy-initialized trace emitter
_emitter: Any = None


def _get_emitter() -> Any:
    global _emitter
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter


class ProviderState(str, Enum):
    """Provider lifecycle states with defined transitions.

    State transitions:
      unknown → initializing → healthy
      healthy → degraded (on errors)
      degraded → healthy (on recovery) or unhealthy (on continued failures)
      unhealthy → initializing (on retry) or draining (on decommission)
      draining → decommissioned (final state)
    """
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    DECOMMISSIONED = "decommissioned"


VALID_TRANSITIONS: dict[ProviderState, list[ProviderState]] = {
    ProviderState.UNKNOWN: [ProviderState.INITIALIZING],
    ProviderState.INITIALIZING: [ProviderState.HEALTHY, ProviderState.UNHEALTHY],
    ProviderState.HEALTHY: [ProviderState.HEALTHY, ProviderState.DEGRADED, ProviderState.DRAINING],
    ProviderState.DEGRADED: [ProviderState.HEALTHY, ProviderState.UNHEALTHY, ProviderState.DRAINING],
    ProviderState.UNHEALTHY: [ProviderState.INITIALIZING, ProviderState.DRAINING],
    ProviderState.DRAINING: [ProviderState.DECOMMISSIONED],
    ProviderState.DECOMMISSIONED: [],  # terminal state
}

_DEFAULT_RUNTIME_CONFIG: dict[str, Any] = {
    "default_provider": "agent_os_python",
    "providers": {
        "agent_os_python": {
            "enabled": True,
            "type": "builtin",
            "fallback_chain": [],
            "capabilities": ["local_execution"],
            "autonomy_level": "approval_only",
            "background_jobs_supported": False,
            "approval_gates": ["destructive", "external", "privacy_sensitive"],
            "resource_limits": {"timeout_seconds": 60, "max_memory_mb": 512},
            "network_policy": "workspace_only",
            "max_chain_length": 2,
            "max_cost_usd_per_run": 0.05,
            "stop_conditions": ["user_stop", "admin_stop", "safety_stop"],
        },
        "zeroclaw": {
            "enabled": False,
            "type": "builtin",
            "env_flag": "ENABLE_ZEROCLAW_ADAPTER",
            "fallback_chain": ["agent_os_python"],
            "capabilities": ["local_execution", "background_jobs", "memory_sync", "tool_execution"],
            "autonomy_level": "bounded_initiative",
            "background_jobs_supported": True,
            "approval_gates": ["financial", "destructive", "privacy_sensitive", "irreversible", "external"],
            "resource_limits": {"timeout_seconds": 45, "max_memory_mb": 80},
            "network_policy": "profile_defined",
            "max_chain_length": 4,
            "max_cost_usd_per_run": 0.02,
            "stop_conditions": ["user_stop", "admin_stop", "safety_stop", "budget_stop", "loop_stop"],
        },
        "claw_code": {
            "enabled": False,
            "type": "builtin",
            "env_flag": "ENABLE_CLAW_CODE",
            "fallback_chain": ["zeroclaw", "agent_os_python"],
            "capabilities": ["local_execution", "tool_execution", "recovery"],
            "autonomy_level": "bounded_initiative",
            "background_jobs_supported": False,
            "approval_gates": ["financial", "destructive", "privacy_sensitive", "irreversible", "external"],
            "resource_limits": {"timeout_seconds": 45, "max_memory_mb": 128},
            "network_policy": "profile_defined",
            "max_chain_length": 3,
            "max_cost_usd_per_run": 0.03,
            "stop_conditions": ["user_stop", "admin_stop", "safety_stop", "budget_stop", "loop_stop"],
        },
    },
    "routing_overrides": [],
}

_DEFAULT_ZEROCLAW_PROFILES: dict[str, Any] = {
    "profiles": {},
}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    raw = value.strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


class RuntimeRegistry:
    """Config-backed runtime provider registry and routing resolver."""

    def __init__(
        self,
        repo_root: Path,
        runtime_config_path: Path | None = None,
        zeroclaw_profiles_path: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.runtime_config_path = runtime_config_path or (self.repo_root / "configs/tooling/runtime_providers.json")
        self.zeroclaw_profiles_path = zeroclaw_profiles_path or (self.repo_root / "configs/tooling/zeroclaw_profiles.json")
        self.runtime_config = self._load_json(self.runtime_config_path, fallback=_DEFAULT_RUNTIME_CONFIG)
        self.zeroclaw_profiles = self._load_json(self.zeroclaw_profiles_path, fallback=_DEFAULT_ZEROCLAW_PROFILES)
        self.source_trust_policy = load_source_trust_policy(self.repo_root)

        self.default_provider = str(self.runtime_config.get("default_provider") or "agent_os_python")
        self._providers_map = self.runtime_config.get("providers", {})
        self._routing_overrides = self.runtime_config.get("routing_overrides", [])
        self._builtin_factories: dict[str, type[RuntimeProvider]] = {
            "agent_os_python": AgentOsPythonRuntimeProvider,
            "claw_code": ClawCodeRuntimeProvider,
            "mlx_lm": MlxLmRuntimeProvider,
            "zeroclaw": ZeroClawRuntimeProvider,
        }
        self._instances: dict[str, RuntimeProvider] = {}
        self._provider_health: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _load_json(path: Path, *, fallback: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return dict(fallback)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return dict(fallback)
        if not isinstance(loaded, dict):
            return dict(fallback)
        return loaded

    @staticmethod
    def _normalize_string_list(raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out

    @staticmethod
    def _normalize_dict(raw: Any) -> dict[str, Any]:
        return dict(raw) if isinstance(raw, dict) else {}

    def _provider_row(self, name: str) -> dict[str, Any]:
        row = self._providers_map.get(name, {})
        if isinstance(row, dict):
            return row
        return {}

    def _fallback_chain(self, name: str) -> list[str]:
        row = self._provider_row(name)
        raw = row.get("fallback_chain", [])
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for candidate in raw:
            text = str(candidate).strip()
            if text and text not in out:
                out.append(text)
        return out

    def is_enabled(self, name: str) -> bool:
        row = self._provider_row(name)
        enabled = bool(row.get("enabled", False))
        env_flag = str(row.get("env_flag") or "").strip()
        if enabled:
            return True
        if env_flag:
            return _parse_bool(os.getenv(env_flag), default=False)
        return False

    def is_registered(self, name: str) -> bool:
        return name in self._builtin_factories

    def is_available(self, name: str) -> bool:
        return self.is_enabled(name) and self.is_registered(name)

    def provider_parity_report(self) -> dict[str, Any]:
        declared = sorted(str(name) for name in self._providers_map.keys())
        registered = sorted(self._builtin_factories.keys())
        enabled = sorted(name for name in declared if self.is_enabled(name))
        enabled_and_registered = sorted(name for name in enabled if self.is_registered(name))
        enabled_but_unregistered = sorted(name for name in enabled if not self.is_registered(name))
        disabled_but_registered = sorted(
            name for name in registered
            if name in self._providers_map and not self.is_enabled(name)
        )
        return {
            "declared_providers": declared,
            "registered_providers": registered,
            "enabled_providers": enabled,
            "enabled_and_registered": enabled_and_registered,
            "enabled_but_unregistered": enabled_but_unregistered,
            "disabled_but_registered": disabled_but_registered,
            "parity_ok": not enabled_but_unregistered,
        }

    def _determine_provider_state(self, health: dict[str, Any]) -> ProviderState:
        """Determine provider state based on health metrics."""
        consecutive_failures = health.get("consecutive_failures", 0)
        total_runs = health.get("total_runs", 0)
        successful_runs = health.get("successful_runs", 0)
        state_str = health.get("state", ProviderState.UNKNOWN.value)

        # No runs yet
        if total_runs == 0:
            return ProviderState.UNKNOWN

        # Successful run — transition to healthy
        if health.get("last_success") and not health.get("last_failure"):
            return ProviderState.HEALTHY

        # Check for consecutive failures
        if consecutive_failures >= 5:
            return ProviderState.UNHEALTHY
        elif consecutive_failures >= 2:
            return ProviderState.DEGRADED

        # Mixed success/failure
        success_rate = successful_runs / total_runs if total_runs > 0 else 0
        if success_rate >= 0.8:
            return ProviderState.HEALTHY
        elif success_rate >= 0.5:
            return ProviderState.DEGRADED
        else:
            return ProviderState.UNHEALTHY

    def record_provider_health(self, name: str, status: str, error: str | None = None) -> dict[str, Any]:
        """Record provider health after a run and transition state machine.

        Returns the new health state for telemetry emission.
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        if name not in self._provider_health:
            self._provider_health[name] = {
                "state": ProviderState.UNKNOWN.value,
                "last_check": None,
                "last_success": None,
                "last_failure": None,
                "consecutive_failures": 0,
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "state_transitions": [],
            }
        health = self._provider_health[name]
        health["last_check"] = now
        health["total_runs"] += 1

        old_state = ProviderState(health.get("state", ProviderState.UNKNOWN.value))

        if status in ("ok", "completed", "executed", "completed_unverified"):
            health["last_success"] = now
            health["successful_runs"] += 1
            health["consecutive_failures"] = 0
        else:
            health["last_failure"] = now
            health["failed_runs"] += 1
            health["consecutive_failures"] += 1
            if error:
                health["last_error"] = error

        # Determine new state
        new_state = self._determine_provider_state(health)

        # Validate transition
        allowed = VALID_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            # Force transition to closest valid state
            if old_state in (ProviderState.DEGRADED, ProviderState.UNHEALTHY):
                if new_state == ProviderState.HEALTHY:
                    pass  # Allow recovery even if not in transition table for degraded→healthy
                else:
                    new_state = ProviderState.INITIALIZING
            elif old_state == ProviderState.HEALTHY:
                if new_state in (ProviderState.DEGRADED, ProviderState.UNHEALTHY):
                    pass  # Allow degradation
            # else keep new_state as determined

        health["state"] = new_state.value
        if old_state != new_state:
            health["state_transitions"].append({
                "from": old_state.value,
                "to": new_state.value,
                "at": now,
                "reason": f"status={status}, consecutive_failures={health['consecutive_failures']}",
            })

        return dict(health)

    def get_provider_health(self, name: str | None = None) -> dict[str, Any]:
        """Get provider health status."""
        if name:
            return self._provider_health.get(name, {"status": "unknown"})
        # Return all provider health
        all_health = {}
        for provider in self._providers_map:
            all_health[provider] = self._provider_health.get(
                provider, {"status": "unknown", "total_runs": 0}
            )
        return all_health

    def _override_match(self, row: dict[str, Any], *, task_type: str, complexity: str) -> bool:
        task_types = row.get("task_type", [])
        complexities = row.get("complexity", [])
        if not isinstance(task_types, list) or not isinstance(complexities, list):
            return False
        return task_type in task_types and complexity in complexities

    def resolve(
        self,
        *,
        task_type: str,
        complexity: str,
        requested_provider: str | None = None,
        requested_profile: str | None = None,
        source_tier: str | None = None,
        requests_capability_promotion: bool = False,
    ) -> dict[str, Any]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"runtime_resolve:{task_type}", tier="C2", component="runtime_registry")
        t0 = time.perf_counter()
        emitter.task_start(ctx, task_type=task_type, complexity=complexity,
                           requested_provider=requested_provider, requested_profile=requested_profile)

        try:
            source = "default"
            runtime_provider_requested = str(requested_provider).strip() if requested_provider else self.default_provider
            runtime_profile = str(requested_profile).strip() if requested_profile else None

            if requested_provider:
                source = "forced"
            else:
                for row in self._routing_overrides:
                    if not isinstance(row, dict):
                        continue
                    if not self._override_match(row, task_type=task_type, complexity=complexity):
                        continue
                    forced_provider = str(row.get("provider") or "").strip()
                    if forced_provider:
                        runtime_provider_requested = forced_provider
                    if runtime_profile is None:
                        profile_from_row = str(row.get("profile") or "").strip()
                        runtime_profile = profile_from_row or None
                    source = "routing_override"
                    break

            fallback_chain = self._fallback_chain(runtime_provider_requested)
            candidates = [runtime_provider_requested, *fallback_chain]

            selected_provider = None
            for candidate in candidates:
                if self.is_available(candidate):
                    selected_provider = candidate
                    break

            if selected_provider is None:
                default_chain = [self.default_provider, *self._fallback_chain(self.default_provider), "agent_os_python"]
                for candidate in default_chain:
                    if self.is_available(candidate):
                        selected_provider = candidate
                        break

            if selected_provider is None:
                selected_provider = "agent_os_python"

            source_policy_eval = evaluate_source_tier_policy(
                self.source_trust_policy,
                source_tier=source_tier,
                requests_capability_promotion=bool(requests_capability_promotion),
            )
            if source_policy_eval["blocked"]:
                runtime_profile = None
                if selected_provider != self.default_provider and self.is_available(self.default_provider):
                    selected_provider = self.default_provider
                reason = f"{source_policy_eval['reason']}; runtime constrained to {selected_provider}"
            elif selected_provider != runtime_provider_requested:
                reason = f"{runtime_provider_requested} disabled/unavailable/unregistered; fallback to {selected_provider}"
            else:
                reason = f"{selected_provider} selected via {source}"

            profile_data: dict[str, Any] = {}
            if runtime_profile:
                all_profiles = self.zeroclaw_profiles.get("profiles", {})
                if isinstance(all_profiles, dict):
                    row = all_profiles.get(runtime_profile, {})
                    if isinstance(row, dict):
                        profile_data = row
            provider_row = self._provider_row(selected_provider)
            if not profile_data and runtime_profile:
                inline_profiles = provider_row.get("profiles", {})
                if isinstance(inline_profiles, dict):
                    inline_profile = inline_profiles.get(runtime_profile, {})
                    if isinstance(inline_profile, dict):
                        profile_data = inline_profile
            stop_conditions = self._normalize_string_list(provider_row.get("stop_conditions", []))
            max_chain_length = provider_row.get("max_chain_length")
            max_cost_usd_per_run = profile_data.get("cost_budget_usd", provider_row.get("max_cost_usd_per_run"))

            result = {
                "runtime_provider_requested": runtime_provider_requested,
                "runtime_provider": selected_provider,
                "runtime_profile": runtime_profile,
                "runtime_fallback_chain": fallback_chain,
                "runtime_source": source,
                "runtime_reason": reason,
                "runtime_profile_data": profile_data,
                "capabilities": self._normalize_string_list(provider_row.get("capabilities", [])),
                "autonomy_level": str(provider_row.get("autonomy_level") or "approval_only"),
                "background_jobs_supported": bool(provider_row.get("background_jobs_supported", False)),
                "approval_gates": self._normalize_string_list(provider_row.get("approval_gates", [])),
                "resource_limits": self._normalize_dict(provider_row.get("resource_limits", {})),
                "network_policy": str(profile_data.get("network_policy") or provider_row.get("network_policy") or "") or None,
                "max_chain_length": int(max_chain_length) if max_chain_length not in (None, "") else None,
                "max_cost_usd_per_run": float(max_cost_usd_per_run) if max_cost_usd_per_run not in (None, "") else None,
                "stop_conditions": stop_conditions,
                "autonomy_mode": str(profile_data.get("autonomy_mode") or provider_row.get("autonomy_level") or "approval_only"),
                "approval_policy": str(profile_data.get("approval_policy") or "standard"),
                "background_profile": str(profile_data.get("background_profile") or "") or None,
                "scheduler_profile": str(profile_data.get("scheduler_profile") or "") or None,
                "persona_version": str(profile_data.get("persona_version") or profile_data.get("persona_id") or "") or None,
                "operator_visibility": str(profile_data.get("operator_visibility") or "summary"),
                "cost_budget_usd": float(profile_data.get("cost_budget_usd")) if profile_data.get("cost_budget_usd") not in (None, "") else (float(provider_row.get("max_cost_usd_per_run")) if provider_row.get("max_cost_usd_per_run") not in (None, "") else None),
                "max_actions": int(profile_data.get("max_actions")) if profile_data.get("max_actions") not in (None, "") else (int(max_chain_length) if max_chain_length not in (None, "") else None),
                "stop_token": str(profile_data.get("stop_token") or "") or None,
                "proof_required": bool(profile_data.get("proof_required", False)),
                "source_tier": source_policy_eval.get("source_tier"),
                "requests_capability_promotion": source_policy_eval.get("requests_capability_promotion"),
                "source_tier_policy": source_policy_eval,
            }

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             provider_id=selected_provider, capabilities=result["capabilities"],
                             fallback_chain=fallback_chain)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def get_provider(self, name: str) -> RuntimeProvider:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"get_provider:{name}", tier="C2", component="runtime_registry")
        t0 = time.perf_counter()
        emitter.task_start(ctx, provider_id=name, operation="get_provider")

        try:
            if not self.is_enabled(name):
                raise RuntimeProviderUnavailableError(f"Runtime provider '{name}' is disabled")
            if name in self._instances:
                duration_ms = (time.perf_counter() - t0) * 1000
                emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                                 provider_id=name, provider_state="cached")
                return self._instances[name]
            factory = self._builtin_factories.get(name)
            if factory is None:
                raise RuntimeProviderUnavailableError(f"Runtime provider '{name}' is not registered")
            instance = factory()
            self._instances[name] = instance
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             provider_id=name, provider_state="initialized")
            return instance
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise
