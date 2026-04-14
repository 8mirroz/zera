from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .contracts import ModelRouteInput, ModelRouteOutput
from .exceptions import ModelRouterError, BudgetExceededError
from .yaml_compat import parse_simple_yaml

try:
    import yaml as _yaml_mod
except ImportError:
    _yaml_mod = None

# ---------------------------------------------------------------------------
# Lazy-initialized structured trace emitter
# ---------------------------------------------------------------------------

_emitter: Any = None

def _get_emitter() -> Any:
    global _emitter
    # In test mode (AGENT_OS_TRACE_FILE set), always create fresh emitter
    if os.getenv("AGENT_OS_TRACE_FILE"):
        from .trace_context import TraceSink, StructuredTraceEmitter
        return StructuredTraceEmitter(TraceSink())
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter


def _safe_yaml_load(text: str) -> dict[str, Any]:
    """Use real YAML parser when available, fall back to simple parser."""
    if _yaml_mod is not None:
        try:
            result = _yaml_mod.safe_load(text)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return parse_simple_yaml(text)

_ALLOWED_ENV_PREFIXES = ["AGENT_MODEL_", "OPENROUTER_", "GEMINI_"]

@dataclass
class ModelAlias:
    alias: str
    provider: str
    model_name: str
    capabilities: list[str] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0


class ModelRouter:
    """Core routing logic for selecting models based on task requirements."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = self.repo_root / "configs/orchestrator/router.yaml"
        # self._load_config() # Keep it light in v4-alpha

    @staticmethod
    def _expand_env_vars(s: str) -> str:
        import os, re
        def repl(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2)
            if any(var_name.startswith(p) for p in _ALLOWED_ENV_PREFIXES):
                return os.environ.get(var_name, match.group(0))
            return match.group(0)
        return re.sub(r'\$\{([\w_]+)\}|\$([\w_]+)', repl, s)

    def _load_config(self) -> None:
        if not self.config_path.exists():
            raise ModelRouterError(f"Config not found: {self.config_path}")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            raise ModelRouterError(f"Failed to load config: {e}")

    def route(self, routing_topic: str, complexity: str | dict = "C2", **kwargs) -> dict:
        """Route a task to the best available model. Handles both v3 and v4 signatures."""
        if isinstance(complexity, dict):
            context = complexity
            complexity_str = "C2"
        else:
            context = kwargs.get("context", {})
            complexity_str = complexity

        # Baseline implementation for v3 compatibility
        # Real logic moved to UnifiedRouter in v4
        out = ModelRouteOutput(
            task_type=routing_topic,
            complexity=complexity_str,
            model_tier="worker",
            primary_model="google/gemini-2.0-flash-exp:free",
            fallback_chain=["google/gemini-2.0-pro-exp-02-05:free"],
            max_input_tokens=32000,
            max_output_tokens=8000,
            route_reason="Default v3 fallback",
            provider_topology="direct",
            routing_source="legacy_v3",
            telemetry={"v3_compat": True}
        )
        return asdict(out)

    def _v4_complexity_row(self, complexity: str) -> dict | None:
        # Helper for v4 lookup
        return None

    @staticmethod
    def to_json(route_output: ModelRouteOutput) -> str:
        return json.dumps(asdict(route_output), ensure_ascii=False, indent=2)


# =============================================================================
# UnifiedRouter - Consolidated routing class (Phase 8 Optimization)
# =============================================================================
# Replaces: ModelRouter + EggentRouterAdapter + EggentEscalationEngine
# Target: <200 lines, single source of truth from router.yaml


class UnifiedRouter(ModelRouter):
    """Unified router consolidating ModelRouter + adapters.

    Reads from configs/orchestrator/router.yaml (sole source of truth).
    Provides simplified escalation and task mapping.
    """

    _V4_COMPLEXITIES = {"C1", "C2", "C3", "C4", "C5"}

    @staticmethod
    def _read_yaml_mapping(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = _safe_yaml_load(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _read_json_mapping(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _workflow_ref_to_path_name(workflow_ref: str | None) -> str | None:
        raw = str(workflow_ref or "").strip()
        if not raw:
            return None
        stem = Path(raw).stem
        if stem.startswith("path-"):
            suffix = stem[len("path-") :]
            words = [part for part in suffix.split("-") if part]
            if words:
                return f"{' '.join(word.capitalize() for word in words)} Path"
        return None

    @staticmethod
    def _normalize_complexity(raw: Any) -> str:
        text = str(raw or "C2").strip().upper()
        return text if text in UnifiedRouter._V4_COMPLEXITIES else "C2"

    @staticmethod
    def _path_to_model_tier(orchestration_path: str, complexity: str) -> str:
        low = orchestration_path.lower()
        if "fast" in low:
            return "worker"
        if "quality" in low or "swarm" in low:
            return "specialist"
        return "worker" if complexity in {"C1", "C2"} else "specialist"

    @staticmethod
    def _path_to_provider_tier(orchestration_path: str, complexity: str) -> str:
        low = orchestration_path.lower()
        if "fast" in low:
            return "free"
        if "quality" in low:
            return "quality"
        if "swarm" in low:
            return "reasoning"
        return "free" if complexity in {"C1", "C2"} else ("quality" if complexity == "C3" else "reasoning")

    @staticmethod
    def _parse_alias_key(raw: Any) -> str | None:
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if not text or text == "self-verify":
            return None
        if text.startswith("${") and text.endswith("}"):
            return text[2:-1]
        if text.startswith("$"):
            return text[1:]
        return None

    @staticmethod
    def _uniq(items: list[str]) -> list[str]:
        out: list[str] = []
        for item in items:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out

    @staticmethod
    def _is_gateway_model(model_id: str) -> bool:
        return str(model_id).startswith("openrouter/")

    def _resolve_transport_preference(self, *, complexity: str, context: dict[str, Any], providers_json: dict[str, Any]) -> str:
        transport_cfg = (providers_json.get("transport_routing") if isinstance(providers_json, dict) else {}) or {}
        if not isinstance(transport_cfg, dict):
            return "gateway-first"

        preference = str(transport_cfg.get("default") or "gateway-first")
        per_complexity = transport_cfg.get("per_complexity", {})
        if isinstance(per_complexity, dict):
            pref = per_complexity.get(complexity)
            if isinstance(pref, str) and pref.strip():
                preference = pref.strip()

        mode_overrides = transport_cfg.get("mode_overrides", {})
        mode = str(context.get("mode") or "").strip()
        if mode and isinstance(mode_overrides, dict):
            pref = mode_overrides.get(mode)
            if isinstance(pref, str) and pref.strip():
                preference = pref.strip()

        channel_overrides = transport_cfg.get("channel_overrides", {})
        channel = str(context.get("execution_channel") or "").strip()
        if channel and isinstance(channel_overrides, dict):
            pref = channel_overrides.get(channel)
            if isinstance(pref, str) and pref.strip():
                preference = pref.strip()

        return preference

    def _load_v4_sources(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        router_yaml = self._read_yaml_mapping(self.repo_root / "configs/orchestrator/router.yaml")
        models_yaml = self._read_yaml_mapping(self.repo_root / "configs/orchestrator/models.yaml")
        providers_json = self._read_json_mapping(self.repo_root / "configs/tooling/model_providers.json")
        return router_yaml, models_yaml, providers_json

    def _v4_complexity_row(self, complexity: str) -> dict | None:
        _, _, providers_json = self._load_v4_sources()
        budgets = (((providers_json.get("budgets") or {}).get("per_complexity")) or {})
        if not isinstance(budgets, dict):
            return None
        c_key = self._normalize_complexity(complexity)
        row = budgets.get(c_key, {})
        return row if isinstance(row, dict) else None

    def route(self, routing_topic: str, complexity_or_context: str | dict = None, **kwargs) -> dict:
        """Route a task to the appropriate model based on v4 logic.

        Args:
            routing_topic: T1-T7 or specific topic string
            complexity_or_context: Backward compatible complexity string or context dict

        Returns:
            dict with routing decision
        """
        if isinstance(complexity_or_context, dict):
            context = complexity_or_context
            complexity = "C2"
        elif isinstance(complexity_or_context, str):
            context = kwargs.get("context", kwargs)
            complexity = complexity_or_context
        else:
            context = kwargs.get("context", kwargs)
            complexity = "C2"

        # --- trace: route decision start ---
        t_start = time.perf_counter()
        task_id = context.get("task_id", routing_topic)
        norm_complexity = self._normalize_complexity(complexity)
        if isinstance(context.get("complexity"), str):
            norm_complexity = self._normalize_complexity(context.get("complexity"))
        from .trace_context import TraceContext
        ctx = TraceContext.root(
            task_id=str(task_id),
            tier=norm_complexity,
            component="router",
        )
        _get_emitter().task_start(ctx, model_selection=True, task_type=routing_topic, complexity=norm_complexity)
        # --- end trace ---

        context = context or {}
        complexity = self._normalize_complexity(complexity)
        if isinstance(context.get("complexity"), str):
            complexity = self._normalize_complexity(context.get("complexity"))

        router_yaml, models_yaml, providers_json = self._load_v4_sources()
        routing_cfg = (router_yaml.get("routing") if isinstance(router_yaml, dict) else {}) or {}
        tiers_cfg = (routing_cfg.get("tiers") if isinstance(routing_cfg, dict) else {}) or {}
        tier_row = (tiers_cfg.get(complexity) if isinstance(tiers_cfg, dict) else {}) or {}
        if not isinstance(tier_row, dict):
            tier_row = {}

        orchestration_path = str(
            tier_row.get("path")
            or self._workflow_ref_to_path_name(tier_row.get("workflow"))
            or "Quality Path"
        )
        max_tools = int(tier_row.get("max_tools", 12))
        ui_fast_path_cfg = (routing_cfg.get("exceptions") or {}).get("ui_fast_path", {}) if isinstance(routing_cfg, dict) else {}
        if isinstance(ui_fast_path_cfg, dict):
            ui_fast_enabled = bool(ui_fast_path_cfg.get("enabled", False))
            ui_fast_task = str(ui_fast_path_cfg.get("task_type") or "")
            ui_fast_forbidden_by_logic = bool(context.get("business_logic_changed", False))
            ui_fast_eligible = bool(context.get("ui_fast_path_eligible", False))
            if ui_fast_enabled and ui_fast_eligible and routing_topic == ui_fast_task and not ui_fast_forbidden_by_logic:
                orchestration_path = str(ui_fast_path_cfg.get("force_path") or orchestration_path)
                if ui_fast_path_cfg.get("max_tools_override") not in (None, ""):
                    max_tools = int(ui_fast_path_cfg.get("max_tools_override"))

        provider_tier = self._path_to_provider_tier(orchestration_path, complexity)
        model_tier = self._path_to_model_tier(orchestration_path, complexity)

        budgets_cfg = (((providers_json.get("budgets") or {}).get("per_complexity")) or {})
        budget_row = {}
        if isinstance(budgets_cfg, dict):
            raw_row = budgets_cfg.get(complexity) or budgets_cfg.get(provider_tier) or {}
            budget_row = raw_row if isinstance(raw_row, dict) else {}
        max_total_tokens = int(budget_row.get("max_total_tokens", budget_row.get("token_budget", 20000)))
        max_input_tokens = int(budget_row.get("max_input_tokens", max_total_tokens))
        max_output_tokens = int(budget_row.get("max_output_tokens", max(1, int(max_total_tokens * 0.25))))
        max_cost_usd = float(budget_row.get("max_cost_usd", budget_row.get("cost_budget", 0.3)))

        # Check requested budget from context (v4) or fallback to defaults.
        req_tokens = context.get("token_budget")
        req_cost = context.get("cost_budget")

        # Keep compatibility with tests expecting small-budget rejection.
        if (req_tokens is not None and 0 < req_tokens < 100) or (req_cost is not None and 0 < req_cost < 0.01):
            raise BudgetExceededError(f"Budget too small: tokens={req_tokens}, cost={req_cost}")

        models_map = (models_yaml.get("models") if isinstance(models_yaml, dict) else {}) or {}
        if not isinstance(models_map, dict):
            models_map = {}

        role_alias_values = [
            tier_row.get("primary_model"),
            tier_row.get("model_alias"),
            tier_row.get("reviewer_model"),
            tier_row.get("orchestrator_model"),
        ]
        role_models: list[str] = []
        for raw_alias in role_alias_values:
            alias_key = self._parse_alias_key(raw_alias)
            if alias_key and isinstance(models_map.get(alias_key), str):
                role_models.append(str(models_map[alias_key]).strip())

        tiers_cfg_json = providers_json.get("tiers", {}) if isinstance(providers_json, dict) else {}
        provider_row = (tiers_cfg_json.get(provider_tier) if isinstance(tiers_cfg_json, dict) else {}) or {}
        if not isinstance(provider_row, dict):
            provider_row = {}
        direct_models = provider_row.get("direct_models", [])
        gateway_models = provider_row.get("gateway_models", [])
        direct_list = [str(m).strip() for m in direct_models] if isinstance(direct_models, list) else []
        gateway_list = [str(m).strip() for m in gateway_models] if isinstance(gateway_models, list) else []

        preferred_models = context.get("preferred_models", [])
        preferred_list = [str(m).strip() for m in preferred_models] if isinstance(preferred_models, list) else []

        role_direct = [m for m in role_models if m and not self._is_gateway_model(m)]
        role_gateway = [m for m in role_models if m and self._is_gateway_model(m)]

        transport_preference = self._resolve_transport_preference(
            complexity=complexity,
            context=context,
            providers_json=providers_json,
        )
        if transport_preference == "direct-only":
            ordered_pool = role_direct + direct_list
        elif transport_preference == "gateway-only":
            ordered_pool = role_gateway + gateway_list
        elif transport_preference == "direct-first":
            ordered_pool = role_direct + direct_list + role_gateway + gateway_list
        elif transport_preference == "balanced":
            ordered_pool = role_gateway + role_direct + direct_list + gateway_list
        else:
            # Default: gateway-first
            ordered_pool = role_gateway + gateway_list + role_direct + direct_list

        candidate_models = self._uniq(preferred_list + ordered_pool)
        unavailable_models = {str(m).strip() for m in context.get("unavailable_models", [])} if isinstance(context.get("unavailable_models", []), list) else set()

        selected = next((m for m in candidate_models if m and m not in unavailable_models), "")
        primary_model = selected or "google/gemini-2.0-flash-exp:free"
        fallback_chain = [m for m in candidate_models if m and m != primary_model and m not in unavailable_models]

        tier_name = str(tier_row.get("name") or complexity)
        route_reason = f"Unified v4 config route for {routing_topic}/{complexity} via {orchestration_path}"
        provider_topology = str(providers_json.get("provider_topology") or "hybrid")
        role_models_payload = {
            "model_alias": tier_row.get("model_alias"),
            "reviewer_model": tier_row.get("reviewer_model"),
            "orchestrator_model": tier_row.get("orchestrator_model"),
        }

        # --- trace: model selection + route decision end ---
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        _get_emitter().task_end(
            ctx,
            duration_ms=elapsed_ms,
            status="completed",
            selected_model=primary_model,
            model_tier=model_tier,
            reason=route_reason,
            fallback_chain=fallback_chain,
            orchestration_path=orchestration_path,
        )
        # --- end trace ---

        return {
            "task_type": routing_topic,
            "complexity": complexity,
            "model_tier": model_tier,
            "primary_model": primary_model,
            "fallback_chain": fallback_chain,
            "max_input_tokens": max_input_tokens,
            "max_output_tokens": max_output_tokens,
            "route_reason": route_reason,
            "provider_topology": provider_topology,
            "routing_source": "v4",
            "orchestration_path": orchestration_path,
            "max_tools": max_tools,
            "telemetry": {
                "router_mode": str(providers_json.get("router_mode_default") or "hybrid"),
                "fallback_depth": 0,
                "token_budget": max_total_tokens,
                "cost_budget": max_cost_usd,
                "max_total_tokens": max_total_tokens,
                "max_input_tokens": max_input_tokens,
                "max_output_tokens": max_output_tokens,
                "max_cost_usd": max_cost_usd,
                "routing_source": "v4",
                "v4_path": orchestration_path,
                "v4_agents": int(tier_row.get("agents", 1)),
                "v4_max_tools": max_tools,
                "v4_human_audit_required": bool(tier_row.get("human_audit_required", False)),
                "v4_tier_name": tier_name,
                "v4_priority_models": [primary_model] + fallback_chain[:2],
                "v4_role_models": role_models_payload,
                "transport_preference": transport_preference,
                "execution_channel": str(context.get("execution_channel") or "") or None,
            },
            "escalation": {
                "escalated_tier": complexity,
                "reason": "Initial v4 route"
            },
            "escalated_tier": complexity,  # Flattened for some CLI tests
        }

    def escalate(self, current_tier: str, reason: str) -> dict:
        """Escalate to next tier after failure. Max 2 escalation steps.

        Args:
            current_tier: Current complexity tier (C1-C5)
            reason: Reason for escalation

        Returns:
            dict with next complexity tier and model
        """
        # --- trace: fallback event ---
        task_id = f"escalate-{current_tier}"
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=task_id, tier=current_tier, component="router")
        _get_emitter().task_start(ctx, escalation=True, from_tier=current_tier, escalation_reason=reason)
        # --- end trace ---

        tiers = ["C1", "C2", "C3", "C4", "C5"]
        try:
            idx = tiers.index(current_tier)
            next_tier = tiers[min(idx + 1, len(tiers) - 1)]
        except ValueError:
            next_tier = "C3"

        # --- trace: fallback event end ---
        _get_emitter().fallback(
            ctx,
            from_model=current_tier,
            to_model=next_tier,
            reason=f"Escalated from {current_tier}: {reason}",
            level="warning",
        )
        # --- end trace ---

        return {
            "escalated_tier": next_tier,
            "reason": f"Escalated from {current_tier}: {reason}",
            "escalation_reason": reason,
            "original_tier": current_tier,
            "can_escalate": next_tier != current_tier and next_tier != "C5",
        }
