from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SUPPORTED_PLUGIN_HOOKS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
SUPPORTED_PLUGIN_LIFECYCLE = {"Init", "Shutdown"}


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    hooks: list[str]
    lifecycle: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_string(payload: dict[str, Any], key: str, source: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid plugin manifest: {source}: requires string `{key}`")
    return value.strip()


def _validate_named_list_map(
    raw: Any,
    *,
    allowed: set[str],
    label: str,
    source: str,
) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid plugin manifest: {source}: {label} must be an object")
    unsupported = sorted(str(key) for key in raw if str(key) not in allowed)
    if unsupported:
        noun = "hook" if label == "hooks" else "lifecycle hook"
        raise ValueError(f"Unsupported plugin {noun} in {source}: {', '.join(unsupported)}")
    for key, value in raw.items():
        if not isinstance(value, list):
            singular = "hook" if label == "hooks" else "lifecycle hook"
            raise ValueError(f"Invalid plugin manifest: {source}: {singular} `{key}` must be a list")
    return sorted(str(key) for key in raw)


def validate_plugin_manifest_payload(payload: Any, *, source: str = "plugin.json") -> PluginManifest:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid plugin manifest: {source}: root must be an object")

    name = _require_string(payload, "name", source)
    version = _require_string(payload, "version", source)
    hooks = _validate_named_list_map(
        payload.get("hooks", {}),
        allowed=SUPPORTED_PLUGIN_HOOKS,
        label="hooks",
        source=source,
    )
    lifecycle = _validate_named_list_map(
        payload.get("lifecycle", {}),
        allowed=SUPPORTED_PLUGIN_LIFECYCLE,
        label="lifecycle",
        source=source,
    )
    return PluginManifest(name=name, version=version, hooks=hooks, lifecycle=lifecycle)


def validate_plugin_manifest_file(plugin_path: Path) -> PluginManifest:
    try:
        payload = json.loads(plugin_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid plugin manifest JSON: {plugin_path}: {e}") from e
    return validate_plugin_manifest_payload(payload, source=str(plugin_path))
