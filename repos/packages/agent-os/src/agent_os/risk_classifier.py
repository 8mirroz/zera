from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class RiskAssessment:
    action_type: str
    risk_class: str
    requires_gate: bool
    reason: str

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "action_type": self.action_type,
            "risk_class": self.risk_class,
            "requires_gate": self.requires_gate,
            "reason": self.reason,
        }


class RiskClassifier:
    """Keyword-based risk classifier with optional connectors_registry integration."""

    _KEYWORDS = {
        "financial": ("finance", "payment", "invest", "trade", "wallet", "defi", "buy", "sell"),
        "destructive": ("delete", "destroy", "remove", "drop", "wipe", "format"),
        "privacy_sensitive": ("contact", "private", "secret", "token", "credential", "pii", "export"),
        "irreversible": ("publish", "send", "transfer", "commit", "deploy", "merge"),
        "external": ("email", "message", "call", "contact", "post", "outreach", "notify"),
    }

    _REGISTRY_PATH = "configs/global/connectors_registry.yaml"

    def __init__(self, repo_root: Path | None = None) -> None:
        self._connector_risk: dict[str, str] = {}
        if repo_root:
            self._load_connector_registry(Path(repo_root))

    def _load_connector_registry(self, repo_root: Path) -> None:
        path = repo_root / self._REGISTRY_PATH
        if not path.exists():
            return
        try:
            data = parse_simple_yaml(path.read_text(encoding="utf-8")) or {}
            connectors = data.get("connectors", {})
            if isinstance(connectors, dict):
                for name, cfg in connectors.items():
                    if isinstance(cfg, dict):
                        self._connector_risk[str(name)] = str(cfg.get("risk_level", "low"))
        except Exception:
            pass

    def _connector_risk_class(self, action_type: str) -> str | None:
        """Return risk_level from connectors_registry if action_type names a connector."""
        normalized = action_type.lower().replace("-", "_").replace(" ", "_")
        for connector_name, risk in self._connector_risk.items():
            if connector_name in normalized or normalized in connector_name:
                return risk
        return None

    def classify(self, action_type: str, *, approval_gates: list[str] | None = None) -> RiskAssessment:
        normalized = str(action_type or "unknown").strip().lower()
        matched_classes: list[str] = []
        for risk_class, tokens in self._KEYWORDS.items():
            if any(token in normalized for token in tokens):
                matched_classes.append(risk_class)

        # Connector registry override
        connector_risk = self._connector_risk_class(normalized)
        if connector_risk == "high" and "irreversible" not in matched_classes:
            matched_classes.insert(0, "irreversible")
        elif connector_risk == "medium" and not matched_classes:
            matched_classes.append("external")

        matched = matched_classes[0] if matched_classes else "low_risk"
        gate_names = {str(item).strip().lower() for item in (approval_gates or []) if str(item).strip()}
        requires_gate = bool(gate_names & (set(matched_classes) | {normalized}))
        reason = f"Action '{normalized}' classified as '{matched}'"
        if len(matched_classes) > 1:
            reason += f" (also: {', '.join(matched_classes[1:])})"
        if connector_risk:
            reason += f" [connector risk: {connector_risk}]"
        if requires_gate:
            reason += " and intersects provider approval gates"
        return RiskAssessment(
            action_type=normalized,
            risk_class=matched,
            requires_gate=requires_gate,
            reason=reason,
        )
