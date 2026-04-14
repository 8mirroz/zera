from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class ToolPermission:
    tool_name: str
    category: str
    risk_level: int
    approval_required: bool
    allowed_roles: list[str]
    description: str
    max_frequency_per_hour: int | None = None
    max_daily: int | None = None
    sandbox_only: bool = False
    allowed_directories: list[str] | None = None
    forbidden_directories: list[str] | None = None
    allowed_commands: list[str] | None = None
    forbidden_commands: list[str] | None = None
    allowed_domains: list[str] | None = None
    never_allow_autonomous: bool = False


class ToolPermissionEngine:
    def __init__(self, repo_root: Path, config_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = config_path or (
            self.repo_root / "configs/tooling/tool_permissions.yaml"
        )
        self.config = self._load_config()
        self._tool_cache: dict[str, ToolPermission] = {}

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"version": "1.0", "tool_registry": {}}
        return parse_simple_yaml(self.config_path.read_text(encoding="utf-8"))

    def _build_tool_cache(self) -> None:
        if self._tool_cache:
            return

        registry = self.config.get("tool_registry", {})
        for tool_name, tool_config in registry.items():
            self._tool_cache[tool_name] = ToolPermission(
                tool_name=tool_name,
                category=tool_config.get("category", "unknown"),
                risk_level=tool_config.get("risk_level", 3),
                approval_required=tool_config.get("approval_required", False),
                allowed_roles=tool_config.get("roles", []),
                description=tool_config.get("description", ""),
                max_frequency_per_hour=tool_config.get("max_frequency_per_hour"),
                max_daily=tool_config.get("max_daily"),
                sandbox_only=tool_config.get("sandbox_only", False),
                allowed_directories=tool_config.get("allowed_directories"),
                forbidden_directories=tool_config.get("forbidden_directories"),
                allowed_commands=tool_config.get("allowed_commands"),
                forbidden_commands=tool_config.get("forbidden_commands"),
                allowed_domains=tool_config.get("allowed_domains"),
                never_allow_autonomous=tool_config.get("never_allow_autonomous", False),
            )

    def get_permission(self, tool_name: str) -> ToolPermission | None:
        self._build_tool_cache()
        return self._tool_cache.get(tool_name)

    def is_allowed(
        self,
        tool_name: str,
        role: str,
        sandbox_mode: bool = False,
    ) -> tuple[bool, str]:
        permission = self.get_permission(tool_name)
        if not permission:
            return True, f"Tool '{tool_name}' not in registry, default allow"

        if permission.never_allow_autonomous:
            return False, f"Tool '{tool_name}' never allowed autonomously"

        if role not in permission.allowed_roles:
            return False, f"Role '{role}' not in allowed roles for '{tool_name}'"

        if permission.sandbox_only and not sandbox_mode:
            return False, f"Tool '{tool_name}' requires sandbox mode"

        if permission.approval_required:
            return False, f"Tool '{tool_name}' requires approval"

        return True, f"Tool '{tool_name}' allowed for role '{role}'"

    def get_tools_by_category(self, category: str) -> list[str]:
        self._build_tool_cache()
        return [
            name for name, perm in self._tool_cache.items() if perm.category == category
        ]

    def get_tools_by_role(self, role: str) -> list[str]:
        self._build_tool_cache()
        return [
            name
            for name, perm in self._tool_cache.items()
            if role in perm.allowed_roles
        ]

    def get_high_risk_tools(self, min_risk_level: int = 4) -> list[str]:
        self._build_tool_cache()
        return [
            name
            for name, perm in self._tool_cache.items()
            if perm.risk_level >= min_risk_level
        ]

    def get_tools_requiring_approval(self) -> list[str]:
        self._build_tool_cache()
        return [
            name for name, perm in self._tool_cache.items() if perm.approval_required
        ]
