"""Shared fixtures for agent-os test suite."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Return the antigravity-core project root."""
    return Path(__file__).resolve().parents[4]


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a temporary directory with sample YAML configs for testing."""
    orchestrator = tmp_path / "configs" / "orchestrator"
    orchestrator.mkdir(parents=True)

    router_yaml = orchestrator / "router.yaml"
    router_yaml.write_text(
        "version: '4.1'\nrouting:\n  tiers:\n    C1:\n      name: Trivial\n      path: Fast Path\n"
    )

    gates_yaml = orchestrator / "completion_gates.yaml"
    gates_yaml.write_text(
        "completion_gates:\n  C1:\n    name: Trivial\n    require_tests: false\n"
    )

    return tmp_path


@pytest.fixture
def sample_memory_entries() -> list[dict]:
    """Return a list of sample memory entry dicts for reuse in tests."""
    return [
        {
            "id": "mem-001",
            "content": "User prefers dark mode",
            "tags": ["preference", "ui"],
            "relevance": 0.9,
            "ttl_days": 30,
        },
        {
            "id": "mem-002",
            "content": "Project uses Python 3.12",
            "tags": ["environment", "python"],
            "relevance": 0.8,
            "ttl_days": 90,
        },
        {
            "id": "mem-003",
            "content": "API rate limit is 100 req/min",
            "tags": ["api", "limits"],
            "relevance": 0.7,
            "ttl_days": 7,
        },
    ]
