from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..contracts import AgentInput, AgentOutput
from ..role_contract_loader import RoleContractLoader
from .swarm_state import SwarmState
from .handoff_engine import HandoffEngine

if TYPE_CHECKING:
    from ..agent_runtime import AgentRuntime

logger = logging.getLogger(__name__)

class SwarmOrchestrator:
    """Orchestrates multi-agent execution flows (Swarms).
    
    Loads role contracts, maintains swarm state, and executes handoffs
    between specialized agents.
    """

    def __init__(self, repo_root: Path, runtime: AgentRuntime) -> None:
        self.repo_root = repo_root
        self.runtime = runtime
        self.contract_loader = RoleContractLoader(
            contracts_dir=repo_root / "configs/orchestrator/role_contracts"
        )
        self.handoff_engine = HandoffEngine(self.contract_loader)
        
        # Load all contracts at init
        self.contract_loader.load_all()

    def coordinate(self, agent_input: AgentInput) -> AgentOutput:
        """Main swarm execution loop."""
        logger.info("Starting swarm coordination for run_id: %s", agent_input.run_id)
        
        # 1. Initialize Swarm State
        state = SwarmState(
            run_id=agent_input.run_id,
            objective=agent_input.objective,
            initial_input=agent_input
        )
        
        # 2. Determine Initial Role
        # If not specified, default to 'architect'
        current_role = agent_input.route_decision.get("role") or "architect"
        
        iteration = 0
        max_iterations = agent_input.route_decision.get("max_swarm_iterations", 5)
        
        final_output: Optional[AgentOutput] = None
        
        while iteration < max_iterations:
            iteration += 1
            logger.info("Swarm Iteration %d: Role=%s", iteration, current_role)
            
            # Prepare input for specific agent
            current_input = state.prepare_agent_input(current_role)
            
            # 3. Execute Agent via recursive Runtime call
            # We bypass lane arbitration for sub-agents to avoid infinite swarm loops
            agent_output = self.runtime.run(current_input)
            state.record_step(current_role, agent_output)
            
            # 4. Check for Handoff
            next_role = self.handoff_engine.resolve_next_role(current_role, agent_output)
            
            if not next_role or next_role == "terminal":
                logger.info("Swarm reached terminal state or no handoff triggered.")
                final_output = agent_output
                break
                
            current_role = next_role
            
        if not final_output:
            # Reached max iterations
            return AgentOutput(
                status="failed",
                diff_summary="Swarm reached maximum iterations without terminal state.",
                test_report={"status": "error", "error": f"max_iterations_reached: {max_iterations}"},
                artifacts=state.get_all_artifacts(),
                next_action="Increase max_swarm_iterations or refine handoff logic."
            )
            
        # Enrich final output with swarm history
        if isinstance(final_output.meta, dict):
            final_output.meta["swarm_history"] = state.get_history_summary()
            final_output.meta["total_swarm_iterations"] = iteration
            
        return final_output
