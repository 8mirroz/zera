"""MetaGPT Role Coordination Patterns — SOP-совместимый слой ролей.

Вдохновлено FoundationAgents/MetaGPT: multi-agent software company.
Определяет role contracts, handoff protocols и SOP-совместимую
координацию между Orchestrator → Architect → Engineer → Reviewer.

Интегрируется с:
- configs/orchestrator/role_contracts/*.yaml (существующие контракты)
- src/sop_pipeline.py (фазы выполнения)
- src/telegram_agent.py (orchestration layer)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

logger = logging.getLogger("hermes-zera.roles")


class Role(Enum):
    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    DESIGN_LEAD = "design_lead"
    COUNCIL = "council"
    ROUTINE_WORKER = "routine_worker"


@dataclass
class RoleContract:
    """Parsed role contract from YAML."""
    role: str
    version: str
    status: str
    system_role: str
    complexity_scope: list[str]
    model_alias: str
    fallback_model: str
    runtime_hint: str
    responsibilities: list[str]
    forbidden_from: list[str]
    handoff_triggers: list[dict[str, str]]
    escalation_path: str
    constraints: dict[str, Any]
    quality_gates: list[str]
    metrics: list[str]
    file_path: str = ""


@dataclass
class HandoffDecision:
    """Result of a handoff evaluation."""
    from_role: Role
    to_role: Role
    reason: str
    context: dict[str, Any] = field(default_factory=dict)
    approved: bool = True


class RoleCoordinator:
    """Manages role contracts, handoff evaluation, and escalation.

    Reads role contracts from configs/orchestrator/role_contracts/
    and provides handoff logic compatible с MetaGPT SOP patterns.
    """

    def __init__(self, contracts_dir: Path | None = None) -> None:
        self.contracts_dir = contracts_dir or Path(__file__).parents[4] / "configs/orchestrator/role_contracts"
        self.contracts: dict[str, RoleContract] = {}
        self._load_contracts()

    def _load_contracts(self) -> None:
        """Load all role contract YAML files."""
        if not self.contracts_dir.exists():
            logger.warning(f"Role contracts dir not found: {self.contracts_dir}")
            return

        for yaml_file in self.contracts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    if _HAS_YAML:
                        data = yaml.safe_load(f)
                    else:
                        data = self._simple_yaml(f.read())
                if data and isinstance(data, dict):
                    contract = self._parse_contract(data, str(yaml_file))
                    self.contracts[contract.role] = contract
                    logger.debug(f"✅ Loaded role contract: {contract.role}")
            except Exception as e:
                logger.warning(f"Failed to load {yaml_file.name}: {e}")

        logger.info(f"✅ RoleCoordinator: {len(self.contracts)} contracts loaded")

    def _simple_yaml(self, text: str) -> dict:
        """Minimal YAML parser for role contracts."""
        result: dict = {}
        current_key = None
        current_list: list | None = None
        current_dict_list: list[dict] = []
        current_dict: dict | None = None

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if current_list is not None:
                    if ":" in value and current_dict is None:
                        # Start of dict in list (e.g. handoff_triggers)
                        current_dict = {}
                        k, _, v = value.partition(":")
                        current_dict[k.strip()] = v.strip().strip('"')
                    elif current_dict is not None and ":" in value:
                        k, _, v = value.partition(":")
                        current_dict[k.strip()] = v.strip().strip('"')
                        current_dict_list.append(current_dict)
                        current_dict = None
                    else:
                        current_list.append(value)
                continue

            if ":" in stripped:
                # Save previous list if any
                if current_list is not None and current_key:
                    if current_dict_list:
                        result[current_key] = current_dict_list
                    else:
                        result[current_key] = current_list

                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"')

                if val:
                    result[key] = val
                    current_key = key
                    current_list = None
                    current_dict = None
                    current_dict_list = []
                else:
                    current_key = key
                    current_list = []
                    current_dict = None
                    current_dict_list = []

        # Save last list
        if current_list is not None and current_key:
            if current_dict_list:
                result[current_key] = current_dict_list
            else:
                result[current_key] = current_list

        return result

    def _parse_contract(self, data: dict, file_path: str) -> RoleContract:
        """Parse raw YAML dict into RoleContract."""
        handoff_raw = data.get("handoff_triggers", [])
        handoff_triggers = []
        for h in handoff_raw:
            if isinstance(h, dict):
                handoff_triggers.append({str(k): str(v) for k, v in h.items()})
            elif isinstance(h, str):
                handoff_triggers.append({"condition": h, "target": "unknown"})

        constraints_raw = data.get("constraints", {})
        constraints = {}
        if isinstance(constraints_raw, dict):
            for k, v in constraints_raw.items():
                if isinstance(v, bool):
                    constraints[k] = v
                elif isinstance(v, (int, float)):
                    constraints[k] = v
                else:
                    try:
                        constraints[k] = int(v)
                    except (ValueError, TypeError):
                        constraints[k] = str(v)

        return RoleContract(
            role=str(data.get("role", "unknown")),
            version=str(data.get("version", "0.0.0")),
            status=str(data.get("status", "inactive")),
            system_role=str(data.get("system_role", "")),
            complexity_scope=data.get("complexity_scope", []) if isinstance(data.get("complexity_scope"), list) else [],
            model_alias=str(data.get("model_alias", "")),
            fallback_model=str(data.get("fallback_model", "")),
            runtime_hint=str(data.get("runtime_hint", "")),
            responsibilities=data.get("responsibilities", []) if isinstance(data.get("responsibilities"), list) else [],
            forbidden_from=data.get("forbidden_from", []) if isinstance(data.get("forbidden_from"), list) else [],
            handoff_triggers=handoff_triggers,
            escalation_path=str(data.get("escalation_path", "")),
            constraints=constraints,
            quality_gates=data.get("quality_gates", []) if isinstance(data.get("quality_gates"), list) else [],
            metrics=data.get("metrics", []) if isinstance(data.get("metrics"), list) else [],
            file_path=file_path,
        )

    def get_contract(self, role: Role) -> RoleContract | None:
        return self.contracts.get(role.value)

    def evaluate_handoff(
        self,
        from_role: Role,
        context: dict[str, Any],
        condition_text: str,
    ) -> HandoffDecision:
        """Evaluate whether a handoff should occur based on conditions.

        Checks the from_role's handoff_triggers against condition_text.
        """
        contract = self.get_contract(from_role)
        if not contract:
            return HandoffDecision(
                from_role=from_role,
                to_role=Role.ORCHESTRATOR,
                reason=f"No contract for {from_role.value}",
                approved=False,
            )

        lower = condition_text.lower()
        for trigger in contract.handoff_triggers:
            condition = str(trigger.get("condition", "")).lower()
            target = str(trigger.get("target", ""))

            # Simple keyword matching on condition
            keywords = condition.split()
            if any(kw.lower() in lower for kw in keywords if len(kw) > 3):
                target_role = Role(target) if target in [r.value for r in Role] else Role.ORCHESTRATOR
                return HandoffDecision(
                    from_role=from_role,
                    to_role=target_role,
                    reason=condition,
                    context=context,
                    approved=True,
                )

        return HandoffDecision(
            from_role=from_role,
            to_role=from_role,  # No handoff
            reason="No matching handoff condition",
            context=context,
            approved=False,
        )

    def get_role_for_tier(self, tier: str) -> Role:
        """Get the primary role responsible for a tier."""
        tier_role_map = {
            "C1": Role.ROUTINE_WORKER,
            "C2": Role.ENGINEER,
            "C3": Role.ENGINEER,
            "C4": Role.ARCHITECT,
            "C5": Role.COUNCIL,
        }
        return tier_role_map.get(tier, Role.ENGINEER)

    def get_sop_roles(self, tier: str) -> list[Role]:
        """Get the SOP role sequence for a given tier."""
        if tier == "C3":
            return [Role.ORCHESTRATOR, Role.ENGINEER, Role.REVIEWER]
        if tier in ("C4", "C5"):
            return [Role.ORCHESTRATOR, Role.ARCHITECT, Role.ENGINEER, Role.REVIEWER]
        return [self.get_role_for_tier(tier)]

    def validate_quality_gates(self, role: Role, check_results: dict[str, bool]) -> list[str]:
        """Check which quality gates failed for a role."""
        contract = self.get_contract(role)
        if not contract:
            return ["No contract found — cannot validate"]

        failed = []
        for gate in contract.quality_gates:
            # Map gate name to check_results key
            gate_key = gate.lower().replace(" ", "_").replace("-", "_")
            if not check_results.get(gate_key, True):
                failed.append(gate)

        return failed

    def list_roles(self) -> list[str]:
        return sorted(self.contracts.keys())
