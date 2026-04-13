from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


class EggentProfileError(RuntimeError):
    """Raised when Eggent compatibility profile is invalid."""


@dataclass
class EggentProfile:
    root: Path
    task_spec_schema: dict[str, Any]
    model_routing_matrix: dict[str, Any]
    escalation_rules: dict[str, Any]
    agent_loop_config: dict[str, Any]
    router_logic_markdown: str


@dataclass
class EggentDesignProfile:
    root: Path
    design_routing: dict[str, Any]
    design_rules_markdown: str
    visual_tokens: dict[str, Any]


def resolve_eggent_pack_root(repo_root: Path, pack_root: Path | None = None) -> Path:
    if pack_root is not None:
        root = Path(pack_root)
    else:
        env_root = os.getenv("EGGENT_PACK_ROOT", "").strip()
        if env_root:
            root = Path(env_root)
        else:
            root = repo_root / "docs/AntiQ v3/antigravity_eggent_pack"

    if not root.is_absolute():
        root = repo_root / root
    return root


class EggentProfileLoader:
    """Loads and validates antigravity_eggent_pack profile files."""

    def __init__(self, repo_root: Path, pack_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.pack_root = resolve_eggent_pack_root(self.repo_root, pack_root)
        self.strict = self._strict_mode_enabled()

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EggentProfileError(f"Invalid JSON: {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise EggentProfileError(f"JSON object expected: {path}")
        return data

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        try:
            data = parse_simple_yaml(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EggentProfileError(f"Invalid YAML: {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise EggentProfileError(f"YAML mapping expected: {path}")
        return data

    def _require(self, condition: bool, message: str) -> None:
        if not condition:
            if not self.strict:
                return
            raise EggentProfileError(message)

    def _strict_mode_enabled(self) -> bool:
        raw = os.getenv("AGENT_OS_EGGENT_STRICT", "true").strip().lower()
        if raw in {"0", "false", "no", "off"}:
            return False
        return True

    def load(self) -> EggentProfile:
        self._require(self.pack_root.exists(), f"Eggent pack root not found: {self.pack_root}")

        task_spec_path = self.pack_root / "task_spec.schema.json"
        routing_matrix_path = self.pack_root / "model_routing_matrix.json"
        escalation_path = self.pack_root / "escalation_rules.yaml"
        loop_path = self.pack_root / "agent_loop_config.json"
        router_logic_path = self.pack_root / "router_logic.md"

        for path in (task_spec_path, routing_matrix_path, escalation_path, loop_path, router_logic_path):
            self._require(path.exists(), f"Missing Eggent profile file: {path}")

        task_spec_schema = self._load_json(task_spec_path)
        model_routing_matrix = self._load_json(routing_matrix_path)
        escalation_rules = self._load_yaml(escalation_path)
        agent_loop_config = self._load_json(loop_path)
        router_logic_markdown = router_logic_path.read_text(encoding="utf-8")

        self._validate_task_spec_schema(task_spec_schema)
        self._validate_routing_matrix(model_routing_matrix)
        self._validate_escalation_rules(escalation_rules)
        self._validate_loop_config(agent_loop_config)
        self._require(router_logic_markdown.strip() != "", f"router_logic.md is empty: {router_logic_path}")

        return EggentProfile(
            root=self.pack_root,
            task_spec_schema=task_spec_schema,
            model_routing_matrix=model_routing_matrix,
            escalation_rules=escalation_rules,
            agent_loop_config=agent_loop_config,
            router_logic_markdown=router_logic_markdown,
        )

    def load_design_profile(self) -> EggentDesignProfile:
        design_root = self.pack_root / "design_agent"
        routing_path = design_root / "design_routing.json"
        rules_path = design_root / "design_agent_rules.md"
        tokens_path = design_root / "design_memory/visual_tokens.json"

        for path in (routing_path, rules_path, tokens_path):
            self._require(path.exists(), f"Missing Eggent design profile file: {path}")

        design_routing = self._load_json(routing_path)
        design_rules_markdown = rules_path.read_text(encoding="utf-8")
        visual_tokens = self._load_json(tokens_path)

        self._require("ui_component" in design_routing, "design_routing missing ui_component")
        self._require("design_system_change" in design_routing, "design_routing missing design_system_change")
        self._require("spacing" in visual_tokens, "visual_tokens missing spacing")
        self._require("durations_ms" in visual_tokens, "visual_tokens missing durations_ms")
        self._require("easing" in visual_tokens, "visual_tokens missing easing")

        return EggentDesignProfile(
            root=design_root,
            design_routing=design_routing,
            design_rules_markdown=design_rules_markdown,
            visual_tokens=visual_tokens,
        )

    def _validate_task_spec_schema(self, schema: dict[str, Any]) -> None:
        root = schema.get("TaskSpec")
        self._require(isinstance(root, dict), "task_spec.schema.json missing TaskSpec object")
        for key in (
            "task_id",
            "area",
            "risk",
            "scope",
            "complexity",
            "requires_reasoning",
            "requires_accuracy",
        ):
            self._require(key in root, f"task_spec.schema.json missing TaskSpec.{key}")

    def _validate_routing_matrix(self, matrix: dict[str, Any]) -> None:
        self._require("version" in matrix, "model_routing_matrix.json missing version")
        pools = matrix.get("model_pools")
        self._require(isinstance(pools, dict), "model_routing_matrix.json missing model_pools")
        for name in ("worker", "specialist", "supervisor"):
            self._require(name in pools, f"model_routing_matrix.json missing model_pools.{name}")

    def _validate_escalation_rules(self, rules: dict[str, Any]) -> None:
        self._require("failure_tracking" in rules, "escalation_rules.yaml missing failure_tracking")
        self._require("signals" in rules, "escalation_rules.yaml missing signals")
        self._require("supervisor_usage" in rules, "escalation_rules.yaml missing supervisor_usage")

    def _validate_loop_config(self, loop_config: dict[str, Any]) -> None:
        self._require("loop" in loop_config, "agent_loop_config.json missing loop")
        self._require("repair_policy" in loop_config, "agent_loop_config.json missing repair_policy")
