"""Version compatibility checking for agent-os contracts."""

from __future__ import annotations

CURRENT_VERSION = "2.0"
SUPPORTED_VERSIONS = {"1.0", "2.0"}


def check_version_compat(version: str) -> bool:
    """Return True if the given version string is supported."""
    return version in SUPPORTED_VERSIONS
