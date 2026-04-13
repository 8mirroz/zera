"""WorkflowRouter — workflow-first routing layer поверх UnifiedRouter.

Читает configs/global/workflow_graphs.yaml и configs/global/platform_mode.yaml.
Если задача матчится на workflow — возвращает workflow-enriched route.
Иначе делегирует в UnifiedRouter (fallback).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .model_router import UnifiedRouter
from .routing_vector import RoutingVectorClassifier, RoutingVector
from .yaml_compat import parse_simple_yaml
from .config_loader import ModularConfigLoader, ConfigNode


class WorkflowRouter:
    """Workflow-first router: workflow_graphs → UnifiedRouter fallback."""

    _WORKFLOW_GRAPHS_PATH = "configs/global/workflow_graphs.yaml"
    _PLATFORM_MODE_PATH = "configs/global/platform_mode.yaml"
    _REGION_PROFILES_PATH = "configs/global/region_profiles.yaml"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.loader = ModularConfigLoader(str(self.repo_root))
        self._unified = UnifiedRouter(repo_root)
        self._classifier = RoutingVectorClassifier(repo_root)
        self._wf_cache: dict[str, Any] | None = None
        self._mode_cache: dict[str, Any] | None = None
        self._region_cache: dict[str, Any] | None = None

    def _load_yaml(self, rel_path: str) -> dict[str, Any]:
        path = self.repo_root / rel_path
        if not path.exists():
            return {}
        try:
            return parse_simple_yaml(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    @property
    def _workflows(self) -> dict[str, Any]:
        if self._wf_cache is None:
            raw = self.loader.load_suite(self._WORKFLOW_GRAPHS_PATH)
            self._wf_cache = raw.get("workflows", {}) or {}
        return self._wf_cache

    @property
    def _platform_modes(self) -> dict[str, Any]:
        if self._mode_cache is None:
            raw = self.loader.load_suite(self._PLATFORM_MODE_PATH)
            
            # Follow components to modes_catalog
            catalog = ModularConfigLoader.get_component(raw, "modes_catalog")
            if catalog:
                self._mode_cache = catalog.get("modes", {}).to_dict()
            else:
                self._mode_cache = raw.get("modes", {}) or {}
        return self._mode_cache

    @property
    def _region_profiles(self) -> dict[str, Any]:
        if self._region_cache is None:
            raw = self._load_yaml(self._REGION_PROFILES_PATH)
            self._region_cache = raw.get("profiles", {}) or {}
        return self._region_cache

    def _match_workflow(self, intent: str) -> tuple[str, dict[str, Any]] | tuple[None, None]:
        """Match intent string to a workflow definition. Returns (name, workflow_def)."""
        intent_lower = intent.lower().replace("-", "_").replace(" ", "_")
        # Direct name match
        for name, wf in self._workflows.items():
            if not isinstance(wf, dict):
                continue
            if name == intent_lower:
                return name, wf
        # Intent class match
        for name, wf in self._workflows.items():
            if not isinstance(wf, dict):
                continue
            if str(wf.get("intent_class", "")).lower() in intent_lower:
                return name, wf
        return None, None

    def _resolve_region_profile(self, context: dict[str, Any]) -> dict[str, Any]:
        profile_name = str(context.get("region_profile") or "global_west")
        return self._region_profiles.get(profile_name, {}) or {}

    def _apply_region_constraints(
        self, base_route: dict[str, Any], region: dict[str, Any], ctx: dict[str, Any]
    ) -> dict[str, Any]:
        if not region:
            return base_route
        preferred = region.get("preferred_providers", [])
        restricted = region.get("restricted_providers", [])
        if not preferred and not restricted:
            return base_route

        route = dict(base_route)
        primary = route.get("primary_model", "")
        fallback = list(route.get("fallback_chain", []))

        def _provider_of(model_id: str) -> str:
            # openrouter/anthropic/... → anthropic
            parts = str(model_id).split("/")
            return parts[1] if len(parts) >= 2 else parts[0]

        def _is_restricted(model_id: str) -> bool:
            p = _provider_of(model_id)
            return any(r in p for r in restricted)

        if _is_restricted(primary) and fallback:
            route["primary_model"] = fallback[0]
            route["fallback_chain"] = fallback[1:]
            route["region_fallback_applied"] = True

        route["region_profile"] = ctx.get("region_profile", "global_west")
        return route

    def route(
        self,
        intent: str,
        complexity: str = "C2",
        *,
        context: dict[str, Any] | None = None,
        routing_vector: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route by workflow-first logic, then fall back to UnifiedRouter.

        Args:
            intent: workflow name (e.g. 'deep_research') or task type (T1-T7)
            complexity: C1-C5 (overridden if routing_vector is provided)
            context: optional dict with region_profile, platform_mode, etc.
            routing_vector: optional 9-dim dict; if provided, complexity is
                            computed via RoutingVectorClassifier instead of
                            using the complexity string directly.

        Returns:
            Enriched routing dict with workflow_name, steps, quality_gates fields.
        """
        ctx = dict(context or {})

        # Auto-classify complexity from routing vector if provided
        if routing_vector:
            classification = self._classifier.classify_dict(routing_vector)
            complexity = classification.complexity
            ctx["routing_vector_score"] = classification.score
            ctx["routing_vector_lane"] = classification.lane
            ctx["routing_vector_reasons"] = classification.reasons

        # Base route from UnifiedRouter
        base = self._unified.route(intent, complexity, context=ctx)

        # Workflow match
        wf_name, wf_def = self._match_workflow(intent)
        if wf_def:
            base["workflow_name"] = wf_name
            base["workflow_steps"] = wf_def.get("steps", [])
            base["quality_gates"] = wf_def.get("quality_gates", [])
            base["memory_scope"] = wf_def.get("memory_scope", "project")
            base["workflow_tools"] = wf_def.get("tools", [])
            base["output_schema"] = wf_def.get("output_schema", "")
            base["routing_profile"] = wf_def.get("routing_profile", "") # Pass the profile for arbitration
            base["routing_source"] = "workflow_first"

            # Enforce complexity floor from workflow definition
            floor_map = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
            floor_str = str(wf_def.get("complexity_floor", "C1"))
            current_int = floor_map.get(complexity, 2)
            floor_int = floor_map.get(floor_str, 1)
            if current_int < floor_int:
                base["complexity"] = floor_str
                base["complexity_floor_applied"] = True
        else:
            base["workflow_name"] = None
            base["routing_source"] = "unified_fallback"

        # Region profile constraints
        region = self._resolve_region_profile(ctx)
        base = self._apply_region_constraints(base, region, ctx)

        return base

    def list_workflows(self) -> list[str]:
        return list(self._workflows.keys())

    def get_workflow(self, name: str) -> dict[str, Any] | None:
        return self._workflows.get(name)
