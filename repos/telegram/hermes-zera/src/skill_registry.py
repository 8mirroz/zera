"""Skill Registry — metadata layer over .agent/skills/.

Reads all skill.md frontmatter, extracts capability metadata,
and provides skill matching by keyword/trigger/intent.

Compatible with: Antigravity Core v4.2, VoltAgent skills format, Claude Skills format.
"""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes-zera.skills")


@dataclass
class SkillMetadata:
    """Structured metadata for a single skill."""
    name: str
    description: str
    category: str  # domain | superpower | zera
    tier_affinity: list[str]  # C1, C2, C3, C4, C5
    triggers: list[str]  # keywords that activate this skill
    source: str  # antigravity | mattpocock | community
    structural_pattern: str  # algorithm | process | method
    when_to_use: str  # short description
    file_path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Pre-built skill metadata for known skills (bootstrapped from inventory)
_KNOWN_SKILLS: dict[str, dict[str, Any]] = {
    # === DOMAIN SKILLS ===
    "design-system-architect": {
        "category": "domain",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["design system", "tokens", "component library", "theme", "CSS variables"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Creating or evolving UI component systems",
    },
    "ui-premium": {
        "category": "domain",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["premium interface", "UI", "frontend", "dark mode", "glassmorphism", "premium design"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Building any user-facing interface",
    },
    "visual-intelligence": {
        "category": "domain",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["design critique", "visual consistency", "Pinterest", "design DNA", "aesthetic"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Design critique, visual consistency checks",
    },
    "telegram-bot": {
        "category": "domain",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["telegram bot", "aiogram", "бот телеграм", "telegram integration"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Develop Telegram Bots using aiogram 3.x patterns",
    },
    "telegram-miniapp": {
        "category": "domain",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["telegram mini app", "web app", "telegram web", "miniapp"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Develop Telegram Mini Apps using React and native SDKs",
    },
    "telegram-payments": {
        "category": "domain",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["telegram stars", "TON Connect", "payment", "платеж", "crypto payment"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Integration patterns for Telegram Stars and TON Connect",
    },
    "e-commerce": {
        "category": "domain",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["product catalog", "cart", "checkout", "shop", "магазин", "ecommerce"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Shopping, cart, checkout systems",
    },

    # === SUPERPOWER SKILLS ===
    "systematic-debugging": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3", "C4"],
        "triggers": ["баг", "bug", "ошибка", "error", "не работает", "broken", "fail", "debug", "отладка"],
        "source": "mattpocock",
        "structural_pattern": "algorithm",
        "when_to_use": "Investigating a reproducible bug, failing test, or runtime error",
    },
    "test-driven-development": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["тест", "test", "TDD", "покрытие", "unit test", "red green refactor"],
        "source": "antigravity",
        "structural_pattern": "algorithm",
        "when_to_use": "Writing tests before or alongside code",
    },
    "writing-plans": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["план", "plan", "roadmap", "этапы", "steps", "реализовать"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Creating a plan for implementation",
    },
    "executing-plans": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3", "C4"],
        "triggers": ["выполни план", "execute plan", "реализуй план", "implement the plan"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Executing a written implementation plan",
    },
    "verification-before-completion": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3", "C4", "C5"],
        "triggers": ["проверь", "verify", "проверка", "validate", "готово?", "done?", "completion"],
        "source": "antigravity",
        "structural_pattern": "algorithm",
        "when_to_use": "Before declaring a task done — run targeted checks",
    },
    "brainstorming": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3", "C4"],
        "triggers": ["brainstorm", "идеи", "brainstorming", "creative", "придумай", "explore options"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Before any creative work — features, components, behavior",
    },
    "dispatching-parallel-agents": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4", "C5"],
        "triggers": ["parallel", "concurrent", "одновременно", "multiple tasks", "несколько задач"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Multiple independent tasks to speed up execution",
    },
    "subagent-driven-development": {
        "category": "superpower",
        "tier_affinity": ["C4", "C5"],
        "triggers": ["subagent", "delegate", "high quality", "C5", "critical task"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Complex C5 tasks requiring high quality — orchestrates sub-agents",
    },
    "requesting-code-review": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["review", "ревью", "code review", "проверь код", "second opinion"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Second opinion on code before human review",
    },
    "receiving-code-review": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["apply review", "примени ревью", "review feedback"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Processing and applying code review feedback",
    },
    "finishing-a-development-branch": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["merge", "заверши ветку", "finish branch", "PR", "pull request"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Development complete — merge worktree back to main",
    },
    "git-guardrails": {
        "category": "superpower",
        "tier_affinity": ["C1", "C2"],
        "triggers": ["git hook", "guardrails", "force push", "git safety", "block dangerous"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Set up git hooks to block dangerous commands",
    },
    "using-git-worktrees": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["worktree", "parallel branch", "isolated work", "complex task"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Isolate changes from main working directory",
    },
    "react-doctor-analyzer": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["react", "next.js", "performance", "heal", "doctor", "React warnings"],
        "source": "antigravity",
        "structural_pattern": "algorithm",
        "when_to_use": "Debugging React component issues",
    },
    "prd-to-plan": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["PRD", "product requirements", "требования", "turn PRD into plan"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Converting product requirements to technical plans",
    },
    "triage-issue": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["triage", "investigate bug", "root cause", "file issue", "GitHub issue"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Investigate bug, identify root cause, file GitHub issue",
    },
    "ubiquitous-language": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["DDD", "domain model", "ubiquitous language", "glossary", "terminology"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Extract DDD glossary, flag ambiguities, propose canonical terms",
    },
    "grill-me": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["grill me", "stress test", "design review", "interview plan"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Stress-test a plan or design through relentless questioning",
    },
    "design-an-interface": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["design interface", "API design", "design twice", "interface options"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Generate multiple interface designs using parallel sub-agents",
    },
    "claude-code-patterns": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["CLAUDE.md", "slash command", "hooks", "review workflow"],
        "source": "community",
        "structural_pattern": "process",
        "when_to_use": "Adapt patterns from awesome-claude-code for Antigravity",
    },
    "memfree-engine": {
        "category": "superpower",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["search", "AI search", "hybrid search", "internet + project context"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Hybrid AI search (Internet + Project Context + Docs)",
    },
    "design-system-architect": {
        "category": "domain",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["design system", "tokens", "component library", "theme"],
        "source": "antigravity",
        "structural_pattern": "process",
        "when_to_use": "Design system governance and page overrides",
    },

    # === ZERA PERSONA SKILLS ===
    "zera-core": {
        "category": "zera",
        "tier_affinity": ["C1", "C2", "C3", "C4", "C5"],
        "triggers": ["zera", "truthfulness", "anti-sycophancy", "persona"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Core Zera operating behavior",
    },
    "zera-muse": {
        "category": "zera",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["creative", "ideation", "muse", "творчество", "inspiration"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Creative support mode for ideation",
    },
    "zera-researcher": {
        "category": "zera",
        "tier_affinity": ["C2", "C3", "C4"],
        "triggers": ["research", "исследование", "source", "synthesis", "confidence"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Source-aware research for reliable synthesis",
    },
    "zera-rhythm-coach": {
        "category": "zera",
        "tier_affinity": ["C1", "C2"],
        "triggers": ["rhythm", "sleep", "focus block", "recovery", "устал", "burnout"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Sustainable rhythm: sleep, focus blocks, recovery",
    },
    "zera-strategist": {
        "category": "zera",
        "tier_affinity": ["C3", "C4", "C5"],
        "triggers": ["strategy", "стратегия", "prioritize", "goals", "execution path"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Strategic planning — goals to prioritized execution",
    },
    "zera-style-curator": {
        "category": "zera",
        "tier_affinity": ["C2", "C3"],
        "triggers": ["aesthetic", "стиль", "lifestyle", "context guidance", "appearance"],
        "source": "antigravity",
        "structural_pattern": "method",
        "when_to_use": "Refined aesthetic and lifestyle guidance",
    },
    "write-a-prd": {
        "category": "superpower",
        "tier_affinity": ["C3", "C4"],
        "triggers": ["write PRD", "product doc", "requirements document", "новый фича"],
        "source": "mattpocock",
        "structural_pattern": "process",
        "when_to_use": "Create PRD through user interview + codebase exploration",
    },
}


class SkillRegistry:
    """Registry of all available skills with metadata and matching."""

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or Path(__file__).parents[4] / ".agent/skills"
        self.skills: dict[str, SkillMetadata] = {}
        self._load_known()

    def _load_known(self) -> None:
        """Bootstrap from known skills metadata."""
        for name, meta in _KNOWN_SKILLS.items():
            skill_path = self.skills_dir / name
            file_path = str(skill_path) if skill_path.exists() else f"unknown:{name}"
            self.skills[name] = SkillMetadata(
                name=name,
                description="",  # filled from SOUL.md triggers or defaults
                file_path=file_path,
                **{k: v for k, v in meta.items() if k != "name"},
            )
        logger.info(f"✅ SkillRegistry bootstrapped with {len(self.skills)} skills")

    def get_skill(self, name: str) -> SkillMetadata | None:
        return self.skills.get(name)

    def list_skills(self, category: str | None = None) -> list[SkillMetadata]:
        skills = list(self.skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return sorted(skills, key=lambda s: s.name)

    def match_by_tier(self, tier: str) -> list[SkillMetadata]:
        """Find skills appropriate for a given tier."""
        return [s for s in self.skills.values() if tier in s.tier_affinity]

    def match_by_keywords(self, text: str) -> list[tuple[SkillMetadata, int, list[str]]]:
        """Match skills by keyword presence in text.

        Returns list of (skill, score, matched_keywords) sorted by score desc.
        """
        lower = text.lower()
        results: list[tuple[SkillMetadata, int, list[str]]] = []

        for skill in self.skills.values():
            matched: list[str] = []
            for trigger in skill.triggers:
                if trigger.lower() in lower:
                    matched.append(trigger)
            if matched:
                # Score: more matched triggers = higher score
                # Weight by category: domain > superpower > zera
                category_weight = {"domain": 3, "superpower": 2, "zera": 1}.get(skill.category, 1)
                score = len(matched) * category_weight
                results.append((skill, score, matched))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_active_skills(self, text: str, tier: str) -> list[dict[str, Any]]:
        """Get skills active for a given text and tier.

        Returns list of skill dicts with metadata + matched keywords.
        """
        matched = self.match_by_keywords(text)
        # Filter by tier affinity
        active = []
        for skill, score, keywords in matched:
            if tier in skill.tier_affinity:
                active.append({
                    "name": skill.name,
                    "category": skill.category,
                    "score": score,
                    "matched_keywords": keywords,
                    "when_to_use": skill.when_to_use,
                    "source": skill.source,
                })
        return active

    def to_json(self) -> str:
        """Export full registry as JSON."""
        return json.dumps(
            {name: skill.to_dict() for name, skill in self.skills.items()},
            ensure_ascii=False,
            indent=2,
        )
