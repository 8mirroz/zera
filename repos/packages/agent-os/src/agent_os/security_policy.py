from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class SecurityPolicyDecision:
    allowed: bool
    issues: list[str]
    workspace_scope: str | None
    tool_allowlist: list[str]
    network_policy: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "issues": list(self.issues),
            "workspace_scope": self.workspace_scope,
            "tool_allowlist": list(self.tool_allowlist),
            "network_policy": self.network_policy,
        }


class SecurityPolicy:
    """Validate runtime profiles before enabling autonomous execution."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.tool_policy = self._load_yaml("configs/tooling/tool_execution_policy.yaml")
        self.network_policy = self._load_yaml("configs/tooling/network_policy.yaml")

    def _load_yaml(self, relative_path: str) -> dict[str, Any]:
        path = self.repo_root / relative_path
        if not path.exists():
            return {}
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _as_list(raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out

    def validate_runtime_profile(
        self,
        profile_name: str | None,
        profile_data: dict[str, Any],
        *,
        provider_name: str,
    ) -> SecurityPolicyDecision:
        issues: list[str] = []
        workspace_scope = str(profile_data.get("workspace_scope") or "").strip() or None
        tool_allowlist = self._as_list(profile_data.get("tool_allowlist"))
        network_policy_name = str(profile_data.get("network_policy") or "").strip() or None
        channel = str(profile_data.get("channel") or "").strip().lower()
        execution_mode = str(profile_data.get("execution_mode") or "health_probe").strip().lower()

        guarded_execution_modes = {"stdio_json", "zeroclaw_native", "claw_native"}
        if provider_name in {"zeroclaw", "claw_code"} and execution_mode in guarded_execution_modes:
            if workspace_scope != "workspace_only":
                issues.append(f"runtime profile '{profile_name or 'default'}' must use workspace_only scope")
            if not tool_allowlist:
                issues.append(f"runtime profile '{profile_name or 'default'}' requires a tool_allowlist")
            if not network_policy_name:
                issues.append(f"runtime profile '{profile_name or 'default'}' requires a network_policy")

        if channel in {"telegram", "edge"} and not profile_data.get("budget_profile"):
            issues.append(f"runtime profile '{profile_name or 'default'}' requires a budget_profile for {channel}")

        allowed_tools = self.tool_policy.get("allowed_tools", {})
        if isinstance(allowed_tools, dict):
            for tool_name in tool_allowlist:
                if tool_name not in allowed_tools:
                    issues.append(f"tool '{tool_name}' is not present in tool_execution_policy")

        policies = self.network_policy.get("policies", {})
        if network_policy_name and isinstance(policies, dict) and network_policy_name not in policies:
            issues.append(f"network policy '{network_policy_name}' is not defined")

        return SecurityPolicyDecision(
            allowed=not issues,
            issues=issues,
            workspace_scope=workspace_scope,
            tool_allowlist=tool_allowlist,
            network_policy=network_policy_name,
        )
