from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..contracts import AgentInput, AgentOutput


class RuntimeProvider(ABC):
    """Base interface for pluggable runtime providers."""

    name: str

    @abstractmethod
    def run(
        self,
        agent_input: AgentInput,
        *,
        repo_root: Path,
        runtime_profile: str | None = None,
    ) -> AgentOutput:
        """Execute one agent run under provider-specific runtime semantics."""
        raise NotImplementedError

