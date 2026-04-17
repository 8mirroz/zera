"""Hermes Zera — Telegram agent with Agent OS integration.

Bridges Telegram messaging to the Antigravity Core routing system:
1. Parses SOUL.md v2 contract → capabilities, delegation, triggers
2. Classifies user message → C1–C5 tier
3. Matches triggers → skill activation, SOP activation
4. Routes through UnifiedRouter → picks model + fallback chain
5. Executes via agent_executor (direct) or SOP pipeline (C3+)
6. Maintains per-chat conversation memory
"""
from __future__ import annotations

import sys
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any
from collections import defaultdict

# Add parent dirs so we can import agent_os
REPO_ROOT = Path(__file__).resolve().parents[3]  # zera/
AGENT_OS_SRC = REPO_ROOT / "repos/packages/agent-os/src"
sys.path.insert(0, str(AGENT_OS_SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from task_classifier import classify, ClassificationResult
from agent_contract import ContractParser, AgentContract
from agent_executor import execute, ExecutionResult
from skill_registry import SkillRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hermes-zera")


@dataclass
class ChatSession:
    """Per-chat conversation state."""
    chat_id: int
    history: list[dict[str, str]] = field(default_factory=list)
    total_messages: int = 0
    last_tier: str = "C1"
    total_latency_ms: float = 0.0
    model_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    sop_active: bool = False

    def add_user_message(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        self.total_messages += 1
        # Keep last 20 messages
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def add_assistant_message(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})

    def get_history(self) -> list[dict[str, str]]:
        return list(self.history)


@dataclass
class RoutingLog:
    """Audit trail for each message."""
    chat_id: int
    user_text: str
    classification: dict[str, Any]
    triggers_matched: dict[str, list[str]]
    active_skills: list[str]
    sop_activated: bool
    route_decision: dict[str, Any]
    execution: dict[str, Any]
    timestamp: float


class HermesZeraAgent:
    """Main agent — routes Telegram messages through Agent OS."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or REPO_ROOT
        self.sessions: dict[int, ChatSession] = {}
        self.routing_logs: list[RoutingLog] = []

        # Load SOUL.md v2 contract
        soul_path = Path(__file__).parent.parent / "SOUL.md"
        self._load_contract(soul_path)

        # Load Skill Registry
        skills_dir = self.repo_root / ".agents/skills"
        self.skill_registry = SkillRegistry(skills_dir)
        logger.info(f"✅ SkillRegistry: {len(self.skill_registry.skills)} skills loaded")

        # Load Agent OS components
        try:
            from agent_os.model_router import UnifiedRouter
            self.router = UnifiedRouter(self.repo_root)
            logger.info("✅ UnifiedRouter loaded")
        except Exception as e:
            logger.warning(f"⚠️  UnifiedRouter not available: {e}")
            self.router = None

        logger.info(f"🌌 Hermes Zera initialized (repo: {self.repo_root})")

    def _load_contract(self, soul_path: Path) -> None:
        """Load and parse SOUL.md v2 contract."""
        try:
            parser = ContractParser(soul_path)
            self.contract = parser.load()
            self.soul_md = soul_path.read_text(encoding="utf-8")
            logger.info(f"✅ SOUL.md v2 loaded: {self.contract.name} ({self.contract.role})")
            logger.info(f"   Capabilities: {self.contract.capabilities}")
            logger.info(f"   Triggers: {list(self.contract.triggers.keys())}")
        except FileNotFoundError:
            logger.warning("SOUL.md not found, using default")
            self.contract = AgentContract()
            self.soul_md = "You are Hermes Zera, a helpful AI assistant."
        except Exception as e:
            logger.warning(f"Failed to parse SOUL.md: {e}")
            self.contract = AgentContract()
            self.soul_md = "You are Hermes Zera, a helpful AI assistant."

    def _get_session(self, chat_id: int) -> ChatSession:
        if chat_id not in self.sessions:
            self.sessions[chat_id] = ChatSession(chat_id=chat_id)
        return self.sessions[chat_id]

    def _classify_tier(self, text: str) -> ClassificationResult:
        """Classify user message into C1–C5 tier."""
        return classify(text)

    def _match_triggers(self, text: str) -> dict[str, list[str]]:
        """Match triggers from SOUL.md contract."""
        return self.contract.match_triggers(text)

    def _should_activate_sop(self, tier: str, triggers: dict[str, list[str]]) -> bool:
        """Check if SOP pipeline should be activated."""
        if tier not in ("C3", "C4", "C5"):
            return False
        sop_triggers = triggers.get("sop_activation", [])
        if sop_triggers:
            return True
        # C4/C5 always activate SOP
        return tier in ("C4", "C5")

    def _route_task(
        self,
        text: str,
        tier: str,
        session: ChatSession,
    ) -> dict[str, Any]:
        """Route through UnifiedRouter or fallback."""
        if self.router:
            try:
                return self.router.route(
                    routing_topic=text[:100],
                    complexity_or_context=tier,
                    context={
                        "mode": "telegram",
                        "execution_channel": "telegram",
                    },
                )
            except Exception as e:
                logger.warning(f"Router failed: {e}")

        # Fallback routing
        model_map = {
            "C1": "google/gemini-2.0-flash-exp:free",
            "C2": "qwen/qwen3-coder",
            "C3": "qwen/qwen3-coder",
            "C4": "deepseek/deepseek-r1-0528:free",
            "C5": "anthropic/claude-3.5-opus",
        }
        fallback_map = {
            "C1": ["qwen/qwen3.6-plus"],
            "C2": ["google/gemini-2.0-flash-exp:free"],
            "C3": ["anthropic/claude-3-5-sonnet-20241022"],
            "C4": ["openai/gpt-4o"],
            "C5": ["openai/gpt-4o"],
        }
        return {
            "primary_model": model_map.get(tier, "qwen/qwen3-coder"),
            "fallback_chain": fallback_map.get(tier, []),
            "complexity": tier,
            "route_reason": "Fallback routing (no UnifiedRouter)",
            "routing_source": "hermes-fallback",
        }

    def _execute_direct(
        self,
        route: dict[str, Any],
        session: ChatSession,
    ) -> ExecutionResult:
        """Execute directly with the selected model."""
        model = route.get("primary_model", "qwen/qwen3-coder")
        fallback_chain = route.get("fallback_chain", [])
        history = session.get_history()

        result = execute(
            model=model,
            system=self.soul_md,
            messages=history,
            max_tokens=route.get("max_output_tokens", 4096),
            fallback_chain=fallback_chain,
        )
        return result

    def _execute_sop(
        self,
        tier: str,
        session: ChatSession,
    ) -> tuple[str, dict[str, Any]]:
        """Execute through SOP pipeline."""
        try:
            from sop_pipeline import SOPPipeline, SOPResult
        except ImportError as e:
            logger.warning(f"SOP pipeline not available: {e}")
            return ("SOP pipeline unavailable, falling back to direct execution", {})

        route = self._route_task("", tier, session)
        history = session.get_history()

        pipeline = SOPPipeline(
            system_prompt=self.soul_md,
            conversation_history=history,
            tier=tier,
            max_output_tokens=route.get("max_output_tokens", 4096),
            fallback_chains={
                "qwen/qwen3-coder": ["google/gemini-2.0-flash-exp:free"],
            },
        )

        sop_result = pipeline.run()
        session.sop_active = True

        execution_info = {
            "sop": True,
            "phases": sop_result.phases_executed,
            "total_latency_ms": sop_result.total_latency_ms,
        }

        return sop_result.final_response, execution_info

    def process_message(self, chat_id: int, text: str) -> tuple[str, dict[str, Any]]:
        """Process a user message and return the response.

        Returns:
            (response_text, routing_info_dict)
        """
        session = self._get_session(chat_id)
        session.add_user_message(text)

        # Step 1: Classify
        classification = self._classify_tier(text)
        tier = classification.tier
        session.last_tier = tier
        logger.info(f"📊 [{chat_id}] Classified as {tier} (conf={classification.confidence:.2f})")

        # Step 2: Match triggers
        triggers = self._match_triggers(text)
        logger.info(f"🎯 [{chat_id}] Triggers: {triggers}")

        # Step 2.5: Match skills from registry
        active_skills = self.skill_registry.get_active_skills(text, tier)
        if active_skills:
            skill_names = [s["name"] for s in active_skills]
            logger.info(f"🧩 [{chat_id}] Skills activated: {skill_names}")
        else:
            skill_names = []

        # Step 3: Check SOP activation
        sop_active = self._should_activate_sop(tier, triggers)
        logger.info(f"🔄 [{chat_id}] SOP: {'active' if sop_active else 'inactive'}")

        # Step 4: Route (always, for logging/metrics)
        route = self._route_task(text, tier, session)
        primary_model = route.get("primary_model", "unknown")
        logger.info(f"🔀 [{chat_id}] Routed to {primary_model} ({route.get('routing_source', 'unknown')})")

        # Step 5: Execute
        if sop_active and tier in ("C3", "C4", "C5"):
            response, execution_info = self._execute_sop(tier, session)
        else:
            result = self._execute_direct(route, session)
            if result.error:
                logger.error(f"❌ [{chat_id}] Execution failed: {result.error}")
                response = "Извини, что-то пошло не так. Попробуй ещё раз."
                session.add_assistant_message(response)
            else:
                response = result.response
                session.add_assistant_message(response)
                session.total_latency_ms += result.latency_ms
                session.model_usage[result.model] += 1
                logger.info(f"✅ [{chat_id}] Responded via {result.model} ({result.latency_ms:.0f}ms)")
            execution_info = {
                "sop": False,
                "model": result.model if not result.error else "error",
                "latency_ms": result.latency_ms if not result.error else 0,
                "fallback_used": result.fallback_used,
                "error": result.error,
            }

        # Step 6: Log
        log_entry = RoutingLog(
            chat_id=chat_id,
            user_text=text,
            classification={
                "tier": classification.tier,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            },
            triggers_matched=triggers,
            active_skills=skill_names,
            sop_activated=sop_active,
            route_decision={
                "primary_model": primary_model,
                "fallback_chain": route.get("fallback_chain", []),
                "routing_source": route.get("routing_source", "unknown"),
                "complexity": route.get("complexity", tier),
            },
            execution=execution_info,
            timestamp=time.time(),
        )
        self.routing_logs.append(log_entry)

        routing_info = {
            "tier": tier,
            "sop": sop_active,
            "triggers": triggers,
            "skills": skill_names,
            "model": primary_model,
        }
        if execution_info.get("sop"):
            routing_info["phases"] = execution_info.get("phases", [])
            routing_info["latency_ms"] = execution_info.get("total_latency_ms", 0)
        else:
            routing_info["latency_ms"] = execution_info.get("latency_ms", 0)
            routing_info["fallback_used"] = execution_info.get("fallback_used", False)

        return response, routing_info

    def get_session_stats(self, chat_id: int) -> dict[str, Any]:
        """Get stats for a chat session."""
        session = self._get_session(chat_id)
        return {
            "chat_id": chat_id,
            "total_messages": session.total_messages,
            "history_length": len(session.history),
            "last_tier": session.last_tier,
            "sop_active": session.sop_active,
            "avg_latency_ms": (
                session.total_latency_ms / max(1, session.total_messages)
            ),
            "model_usage": dict(session.model_usage),
        }

    def get_last_logs(self, n: int = 5) -> list[dict[str, Any]]:
        """Get the last N routing logs."""
        logs = self.routing_logs[-n:]
        return [asdict(log) for log in logs]
