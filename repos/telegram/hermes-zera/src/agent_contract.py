"""Agent Contract Parser — SOUL.md v2 structured config.

Parses the YAML blocks inside SOUL.md and provides typed access
to delegation rules, triggers, tools, behavior policy, etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _simple_yaml_load(text: str) -> dict[str, Any]:
    """Minimal YAML-like parser for simple key-value structures."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    current_dict: dict[str, Any] | None = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if current_list is not None:
                current_list.append(value)
            continue

        # Key: value
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val:
                # Simple value
                if current_key and current_dict is not None:
                    current_dict[key] = val
                else:
                    result[key] = val
                    current_key = key
                    current_list = None
                    current_dict = None
            else:
                # Start of nested structure
                current_key = key
                result[key] = {}
                current_dict = result[key]
                current_list = None

    return result


@dataclass
class AgentContract:
    """Parsed SOUL.md v2 contract."""
    name: str = "Unknown"
    role: str = "unknown"
    platform: str = "unknown"
    capabilities: list[str] = field(default_factory=list)

    # Personality
    style: list[str] = field(default_factory=list)
    language_policy: dict[str, str] = field(default_factory=dict)
    principles: list[str] = field(default_factory=list)

    # Boundaries
    allowed: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)

    # Delegation
    delegation: dict[str, Any] = field(default_factory=dict)
    roles: dict[str, str] = field(default_factory=dict)

    # Triggers
    triggers: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    # Tools
    tools: dict[str, Any] = field(default_factory=dict)

    # Behavior
    response_policy: dict[str, Any] = field(default_factory=dict)

    # Safety
    rate_limits: dict[str, Any] = field(default_factory=dict)
    error_handling: dict[str, str] = field(default_factory=dict)

    # Memory
    memory: dict[str, Any] = field(default_factory=dict)


class ContractParser:
    """Parse SOUL.md v2 into AgentContract."""

    _BLOCK_RE = re.compile(r"##\s+(\w[\w\s]*?)\s*\n\n```(?:yaml)?\n(.*?)```", re.DOTALL)

    def __init__(self, soul_path: Path | str | None = None) -> None:
        self.soul_path = Path(soul_path) if soul_path else Path(__file__).parent.parent / "SOUL.md"
        self._raw = ""
        self._blocks: dict[str, str] = {}

    def load(self) -> AgentContract:
        """Load and parse SOUL.md."""
        if not self.soul_path.exists():
            raise FileNotFoundError(f"SOUL.md not found at {self.soul_path}")

        self._raw = self.soul_path.read_text(encoding="utf-8")
        self._extract_blocks()

        contract = AgentContract()
        self._parse_identity(contract)
        self._parse_personality(contract)
        self._parse_boundaries(contract)
        self._parse_delegation(contract)
        self._parse_triggers(contract)
        self._parse_tools(contract)
        self._parse_behavior(contract)
        self._parse_safety(contract)
        self._parse_memory(contract)

        return contract

    def _extract_blocks(self) -> None:
        """Extract all YAML code blocks from SOUL.md."""
        for match in self._BLOCK_RE.finditer(self._raw):
            section_name = match.group(1).strip().lower()
            yaml_content = match.group(2).strip()
            self._blocks[section_name] = yaml_content

    def _parse_yaml_block(self, block_name: str) -> dict[str, Any]:
        """Parse a YAML block with fallback to simple parser."""
        raw = self._blocks.get(block_name, "")
        if not raw:
            return {}
        if _HAS_YAML:
            try:
                return yaml.safe_load(raw) or {}
            except Exception:
                pass
        return _simple_yaml_load(raw)

    def _parse_identity(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("identity")
        contract.name = str(data.get("name", "Unknown"))
        contract.role = str(data.get("role", "unknown"))
        contract.platform = str(data.get("platform", "unknown"))
        caps = data.get("capabilities", [])
        contract.capabilities = [str(c) for c in caps] if isinstance(caps, list) else []

    def _parse_personality(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("personality")
        style = data.get("style", [])
        contract.style = [str(s) for s in style] if isinstance(style, list) else []
        lang = data.get("language", {})
        if isinstance(lang, dict):
            contract.language_policy = {str(k): str(v) for k, v in lang.items()}
        principles = data.get("principles", [])
        contract.principles = [str(p) for p in principles] if isinstance(principles, list) else []

    def _parse_boundaries(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("boundaries")
        allowed = data.get("allowed", [])
        contract.allowed = [str(a) for a in allowed] if isinstance(allowed, list) else []
        forbidden = data.get("forbidden", [])
        contract.forbidden = [str(f) for f in forbidden] if isinstance(forbidden, list) else []

    def _parse_delegation(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("delegation")
        contract.delegation = data
        roles = data.get("roles", {})
        if isinstance(roles, dict):
            contract.roles = {str(k): str(v) for k, v in roles.items()}

    def _parse_triggers(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("triggers")
        contract.triggers = data

    def _parse_tools(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("tools")
        contract.tools = data

    def _parse_behavior(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("behavior")
        contract.response_policy = data.get("response_policy", {}) if isinstance(data, dict) else {}

    def _parse_safety(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("safety")
        if isinstance(data, dict):
            limits = data.get("rate_limits", {})
            contract.rate_limits = limits if isinstance(limits, dict) else {}
            errors = data.get("error_handling", {})
            contract.error_handling = errors if isinstance(errors, dict) else {}

    def _parse_memory(self, contract: AgentContract) -> None:
        data = self._parse_yaml_block("memory")
        contract.memory = data

    def get_delegation_for_tier(self, tier: str) -> dict[str, Any]:
        """Get delegation rules for a specific tier."""
        return self.delegation.get(tier, {})

    def get_response_policy_for_tier(self, tier: str) -> dict[str, Any]:
        """Get response policy for a specific tier."""
        return self.response_policy.get(tier, {})

    def match_triggers(self, text: str) -> dict[str, list[str]]:
        """Find which triggers match the given text.

        Returns dict of {trigger_category: [matched_sub_types]}.
        """
        lower = text.lower()
        matched: dict[str, list[str]] = {}

        # Parse the triggers YAML block
        triggers = self._blocks.get("triggers", "")
        if triggers:
            parsed = yaml.safe_load(triggers) if _HAS_YAML else _simple_yaml_load(triggers)
        else:
            parsed = {}

        # The top-level key is "triggers", drill down
        triggers_root = parsed.get("triggers", parsed) if isinstance(parsed, dict) else {}
        if not isinstance(triggers_root, dict):
            return matched

        for category, value in triggers_root.items():
            if isinstance(value, list):
                # Flat keyword list — match any keyword
                for kw in value:
                    if str(kw).lower() in lower:
                        if category not in matched:
                            matched[category] = []
                        matched[category].append(str(kw))
            elif isinstance(value, dict):
                # Nested dict (e.g. skill_activation → {systematic_debugging: [...]})
                for sub_type, patterns in value.items():
                    if not isinstance(patterns, list):
                        continue
                    for pattern in patterns:
                        if str(pattern).lower() in lower:
                            if category not in matched:
                                matched[category] = []
                            entry = f"{sub_type}"
                            if entry not in matched[category]:
                                matched[category].append(entry)
                            break  # One match per sub_type is enough

        return matched
