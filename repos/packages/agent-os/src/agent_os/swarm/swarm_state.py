from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ..contracts import AgentInput, AgentOutput

@dataclass
class SwarmStep:
    role: str
    status: str
    timestamp: str
    output_summary: str
    artifacts: List[str]

class SwarmState:
    """Maintains state across multiple agent invocations in a swarm."""

    def __init__(self, run_id: str, objective: str, initial_input: AgentInput) -> None:
        self.run_id = run_id
        self.objective = objective
        self.initial_input = initial_input
        self.history: List[SwarmStep] = []
        self.shared_context: Dict[str, Any] = {}
        self.all_artifacts: List[str] = []

    def record_step(self, role: str, output: AgentOutput) -> None:
        step = SwarmStep(
            role=role,
            status=output.status,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            output_summary=output.diff_summary[:500],
            artifacts=output.artifacts
        )
        self.history.append(step)
        self.all_artifacts.extend(output.artifacts)
        
        # Merge metadata into shared context if needed
        if isinstance(output.meta, dict):
            self.shared_context.update(output.meta.get("provide_to_next", {}))

    def prepare_agent_input(self, role: str) -> AgentInput:
        """Create an AgentInput tailored for a specific role/sub-agent."""
        # Clone original route decision but update the persona/role
        new_route = dict(self.initial_input.route_decision)
        new_route["role"] = role
        new_route["swarm_mode"] = True
        
        # Append swarm context to objective for the agent
        swarm_context_str = f"\n\n[SWARM CONTEXT]\nIteration: {len(self.history) + 1}\nPrior Steps: {len(self.history)}"
        if self.history:
            last_step = self.history[-1]
            swarm_context_str += f"\nLast Role: {last_step.role} (Status: {last_step.status})"

        return AgentInput(
            run_id=f"{self.run_id}_{role}_{len(self.history)}",
            objective=self.initial_input.objective + swarm_context_str,
            plan_steps=self.initial_input.plan_steps,
            route_decision=new_route
        )

    def get_history_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "role": s.role,
                "status": s.status,
                "timestamp": s.timestamp,
                "artifacts": s.artifacts
            } for s in self.history
        ]

    def get_all_artifacts(self) -> List[str]:
        return sorted(list(set(self.all_artifacts)))
