"""
Role Contract Loader — Antigravity Core v4.2

Loads, validates, and indexes role contracts from YAML files.
Validates schema structure, resolves model aliases, and validates handoff targets.

Source of truth: configs/orchestrator/role_contracts/*.yaml
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .exceptions import AgentOSError
from .yaml_compat import parse_simple_yaml

try:
    import yaml as _yaml_mod
except ImportError:
    _yaml_mod = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

REQUIRED_KEYS: Set[str] = {
    "role",
    "version",
    "status",
    "system_role",
    "complexity_scope",
    "model_alias",
    "fallback_model",
    "runtime_hint",
    "responsibilities",
    "interfaces",
    "dependencies",
    "forbidden_from",
    "handoff_triggers",
    "escalation_path",
    "constraints",
    "quality_gates",
    "metrics",
    "memory_policy",
    "fail_safe",
}

VALID_COMPLEXITY_TIERS: Set[str] = {"C1", "C2", "C3", "C4", "C5"}

VALID_STATUSES: Set[str] = {"active", "deprecated", "draft", "archived"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RoleContractError(AgentOSError):
    """Base error for role contract operations."""


class RoleContractNotFoundError(RoleContractError):
    def __init__(self, role_name: str):
        super().__init__(f"Role contract not found: {role_name}")
        self.role_name = role_name


class RoleContractValidationError(RoleContractError):
    def __init__(self, role_name: str, reason: str):
        super().__init__(f"Role contract validation failed for '{role_name}': {reason}")
        self.role_name = role_name
        self.reason = reason


class RoleContractAliasResolutionError(RoleContractError):
    def __init__(self, role_name: str, alias: str):
        super().__init__(f"Model alias '{alias}' could not be resolved for role '{role_name}'")
        self.role_name = role_name
        self.alias = alias


class RoleContractHandoffError(RoleContractError):
    def __init__(self, role_name: str, target: str, known_roles: Set[str]):
        super().__init__(
            f"Invalid handoff target '{target}' in role '{role_name}'. "
            f"Known roles: {sorted(known_roles)}"
        )
        self.role_name = role_name
        self.target = target


# ---------------------------------------------------------------------------
# YAML loader with fallback
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Model alias resolver
# ---------------------------------------------------------------------------

class AliasResolver:
    """Resolves $ALIAS references against models.yaml."""

    def __init__(self, models_path: Path):
        self.models_path = models_path
        self._alias_map: Optional[Dict[str, str]] = None

    def load(self) -> Dict[str, str]:
        """Load and flatten models.yaml into alias -> value map."""
        if self._alias_map is not None:
            return self._alias_map

        if not self.models_path.exists():
            logger.warning("models.yaml not found at %s, alias resolution disabled", self.models_path)
            self._alias_map = {}
            return self._alias_map

        data = _safe_yaml_load(self.models_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            self._alias_map = {}
            return self._alias_map

        models_section = data.get("models", {})
        if not isinstance(models_section, dict):
            models_section = {}

        # Resolve $REFERENCES iteratively (max 5 depth)
        resolved: Dict[str, str] = {}
        for _ in range(5):
            changed = False
            for key, value in models_section.items():
                if isinstance(value, str):
                    if value.startswith("$") and value[1:] in resolved:
                        new_value = resolved[value[1:]]
                        if resolved.get(key) != new_value:
                            resolved[key] = new_value
                            changed = True
                    else:
                        if key not in resolved:
                            resolved[key] = value
                            changed = True
            if not changed:
                break

        self._alias_map = resolved
        return resolved

    def resolve(self, alias: str) -> Optional[str]:
        """Resolve a single alias. Returns raw value if not an alias.

        Supports:
        - $ALIAS references → resolved against models.yaml
        - omniroute://combo/name → resolved via OmniRoute combo config
        """
        if not alias:
            return None

        raw = alias.strip()
        if not raw.startswith("$"):
            return raw

        # Handle omniroute:// URI references
        if raw.startswith("$MODEL_OMNIRROUTE_"):
            key = raw[1:]
            aliases = self.load()
            value = aliases.get(key)
            if value and value.startswith("omniroute://"):
                # Return the combo URI as-is — runtime will handle OmniRoute routing
                return value
            # Fallback: if omniroute alias not set, resolve underlying model
            if value:
                return self._resolve_chain(value)
            return raw

        key = raw[1:] if raw.startswith("$") else raw
        return self._resolve_chain(key)

    def _resolve_chain(self, key: str) -> Optional[str]:
        """Resolve an alias, following $REFERENCES up to 5 levels deep."""
        aliases = self.load()
        value = aliases.get(key)
        if not value:
            return key  # Return as-is if not found

        for _ in range(5):
            if isinstance(value, str) and value.startswith("$"):
                next_key = value[1:]
                value = aliases.get(next_key, value)
            else:
                break

        return value


# ---------------------------------------------------------------------------
# Contract loader and validator
# ---------------------------------------------------------------------------

class RoleContractLoader:
    """Discovers, loads, validates, and indexes role contracts."""

    def __init__(self, contracts_dir: Path, models_path: Optional[Path] = None):
        self.contracts_dir = contracts_dir
        self.models_path = models_path or contracts_dir.parent / "models.yaml"
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.alias_resolver = AliasResolver(self.models_path)
        self._validation_errors: List[str] = []

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> List[Path]:
        """Find all YAML files in contracts directory."""
        if not self.contracts_dir.exists():
            logger.warning("Contracts directory not found: %s", self.contracts_dir)
            return []
        return sorted(self.contracts_dir.glob("*.yaml"))

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Load all role contracts from the contracts directory."""
        self.contracts = {}
        self._validation_errors = []

        yaml_files = self.discover()
        for path in yaml_files:
            try:
                contract = self._load_single(path)
                role_name = contract.get("role", path.stem)
                self.contracts[role_name] = contract
            except Exception as exc:
                self._validation_errors.append(f"Failed to load {path.name}: {exc}")
                logger.error("Failed to load %s: %s", path.name, exc)

        return self.contracts

    def _load_single(self, path: Path) -> Dict[str, Any]:
        """Load and parse a single YAML contract."""
        text = path.read_text(encoding="utf-8")
        data = _safe_yaml_load(text)
        if not isinstance(data, dict):
            raise RoleContractValidationError(
                path.stem, f"Expected dict, got {type(data).__name__}"
            )
        data["_source_path"] = str(path)
        return data

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_all(self) -> List[str]:
        """Run full validation suite on all loaded contracts.

        Returns list of error messages (empty = all passed).
        """
        self._validation_errors = []
        known_roles = set(self.contracts.keys())

        for role_name, contract in self.contracts.items():
            self._validate_schema(role_name, contract)
            self._validate_complexity_scope(role_name, contract)
            self._validate_status(role_name, contract)
            self._validate_handoff_targets(role_name, contract, known_roles)
            self._validate_constraints(role_name, contract)

        # Cross-contract validation: model alias resolution
        self._validate_model_aliases(known_roles)

        return self._validation_errors

    def _validate_schema(self, role_name: str, contract: Dict[str, Any]) -> None:
        """Check all required keys are present."""
        missing = REQUIRED_KEYS - set(contract.keys())
        if missing:
            self._validation_errors.append(
                f"Role '{role_name}': missing required keys: {sorted(missing)}"
            )

    def _validate_status(self, role_name: str, contract: Dict[str, Any]) -> None:
        """Validate status field."""
        status = contract.get("status")
        if status and status not in VALID_STATUSES:
            self._validation_errors.append(
                f"Role '{role_name}': invalid status '{status}', must be one of {sorted(VALID_STATUSES)}"
            )

    def _validate_complexity_scope(self, role_name: str, contract: Dict[str, Any]) -> None:
        """Validate complexity_scope contains only valid tiers."""
        scope = contract.get("complexity_scope", [])
        if not isinstance(scope, list):
            self._validation_errors.append(
                f"Role '{role_name}': complexity_scope must be a list"
            )
            return
        invalid = set(scope) - VALID_COMPLEXITY_TIERS
        if invalid:
            self._validation_errors.append(
                f"Role '{role_name}': invalid complexity tiers {sorted(invalid)}"
            )

    def _validate_handoff_targets(
        self, role_name: str, contract: Dict[str, Any], known_roles: Set[str]
    ) -> None:
        """Validate all handoff targets reference known roles or 'terminal'."""
        triggers = contract.get("handoff_triggers", [])
        if not isinstance(triggers, list):
            self._validation_errors.append(
                f"Role '{role_name}': handoff_triggers must be a list"
            )
            return

        valid_targets = known_roles | {"terminal"}
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            target = trigger.get("target")
            if target and target not in valid_targets:
                self._validation_errors.append(
                    f"Role '{role_name}': handoff target '{target}' not in known roles"
                )

    def _validate_constraints(self, role_name: str, contract: Dict[str, Any]) -> None:
        """Validate constraints have sensible values."""
        constraints = contract.get("constraints", {})
        if not isinstance(constraints, dict):
            self._validation_errors.append(
                f"Role '{role_name}': constraints must be a dict"
            )
            return

        numeric_fields = ["token_budget", "max_tool_calls", "max_files_modified"]
        for field in numeric_fields:
            value = constraints.get(field)
            if value is not None:
                try:
                    numeric = int(value)
                    if numeric < 0 and field != "max_files_modified":
                        # max_files_modified can be 0 (review-only roles)
                        self._validation_errors.append(
                            f"Role '{role_name}': {field} must be non-negative, got {numeric}"
                        )
                except (ValueError, TypeError):
                    self._validation_errors.append(
                        f"Role '{role_name}': {field} must be numeric, got {value!r}"
                    )

    def _validate_model_aliases(self, known_roles: Set[str]) -> None:
        """Validate that all model_alias and fallback_model resolve."""
        aliases = self.alias_resolver.load()
        if not aliases:
            logger.warning("Alias resolver empty, skipping alias validation")
            return

        for role_name, contract in self.contracts.items():
            for alias_key in ("model_alias", "fallback_model"):
                raw = contract.get(alias_key)
                if not raw:
                    continue
                if not isinstance(raw, str):
                    self._validation_errors.append(
                        f"Role '{role_name}': {alias_key} must be a string"
                    )
                    continue

                # Check if it's a $ALIAS reference
                if raw.startswith("$"):
                    key = raw[1:]
                    if key not in aliases:
                        self._validation_errors.append(
                            f"Role '{role_name}': {alias_key} '{raw}' does not resolve in models.yaml"
                        )

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def get_contract(self, role_name: str) -> Dict[str, Any]:
        """Get a specific role contract by name."""
        if role_name not in self.contracts:
            raise RoleContractNotFoundError(role_name)
        return self.contracts[role_name]

    def list_roles(self) -> List[str]:
        """List all loaded role names."""
        return sorted(self.contracts.keys())

    def get_roles_for_complexity(self, complexity: str) -> List[str]:
        """Get roles that handle a given complexity tier."""
        return [
            name for name, contract in self.contracts.items()
            if complexity in contract.get("complexity_scope", [])
        ]

    def is_valid(self) -> bool:
        """Check if all validation passed (no errors)."""
        return len(self._validation_errors) == 0

    def validation_report(self) -> str:
        """Return human-readable validation report."""
        if not self._validation_errors:
            return f"✓ All {len(self.contracts)} role contracts valid"
        lines = [f"✗ {len(self._validation_errors)} validation error(s):"]
        for err in self._validation_errors:
            lines.append(f"  - {err}")
        return "\n".join(lines)
