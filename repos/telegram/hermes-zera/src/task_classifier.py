"""Task classifier — maps user messages to C1–C5 complexity tiers.

Uses keyword heuristics + token-length estimation.
Future: replace with LLM-based classifier.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    tier: str
    confidence: float
    reasoning: str


# Keywords that signal higher complexity
_C4_KEYWORDS = [
    "архитектур", "architecture", "микросервис", "microservice",
    "cross-domain", "cross domain", "api design", "api design",
    "рефакторинг всей", "full refactor", "redesign system",
    "pipeline", "orchestrat", "swarm", "multi-agent",
    "инфраструктур", "infrastructure", "deploy", "ci/cd",
    "баз данных", "database design", "schema migration",
]

_C5_KEYWORDS = [
    "безопасност", "security", "vulnerability", "уязвимост",
    "платеж", "payment", "production infra", "prod deployment",
    "критическ", "critical", "high risk", "compliance",
    "council", "совет", "аудит безопасности",
]

_C3_KEYWORDS = [
    "тест", "test", "integration", "модуль", "module",
    "feature", "функцион", "functional", "end-to-end",
    "e2e", "сервис", "service", "роутер", "router",
    "workflow", "маршрутизац", "routing",
]


def _token_estimate(text: str) -> int:
    """Rough token count (split on whitespace + punctuation)."""
    return len(re.findall(r'\S+', text))


def classify(text: str) -> ClassificationResult:
    """Classify a user message into a complexity tier.

    Heuristics:
    - C5: security, payments, critical infra keywords
    - C4: architecture, multi-component, infrastructure keywords
    - C3: tests, modules, services, integration
    - C2: multi-file, specific feature request, medium length
    - C1: short, trivial, single-purpose questions
    """
    lower = text.lower()
    text_len = len(text)
    tokens = _token_estimate(text)

    # Count keyword matches per tier
    c5_hits = sum(1 for kw in _C5_KEYWORDS if kw in lower)
    c4_hits = sum(1 for kw in _C4_KEYWORDS if kw in lower)
    c3_hits = sum(1 for kw in _C3_KEYWORDS if kw in lower)

    # Rule-based classification
    if c5_hits >= 1:
        confidence = min(0.7 + c5_hits * 0.1, 0.95)
        return ClassificationResult(
            tier="C5",
            confidence=confidence,
            reasoning=f"Critical keywords matched ({c5_hits}), security/production risk"
        )

    if c4_hits >= 2 or (c4_hits >= 1 and tokens > 50):
        confidence = min(0.6 + c4_hits * 0.1, 0.9)
        return ClassificationResult(
            tier="C4",
            confidence=confidence,
            reasoning=f"Architecture/infrastructure keywords ({c4_hits}), complex scope"
        )

    if c3_hits >= 1 or tokens > 30:
        confidence = min(0.5 + c3_hits * 0.1, 0.85)
        return ClassificationResult(
            tier="C3",
            confidence=confidence,
            reasoning=f"Integration/module keywords ({c3_hits}), medium complexity"
        )

    # Length-based heuristic for simple queries
    if tokens <= 10 and text_len < 100:
        return ClassificationResult(
            tier="C1",
            confidence=0.7,
            reasoning="Short trivial query, single-purpose"
        )

    return ClassificationResult(
        tier="C2",
        confidence=0.6,
        reasoning="Simple task, local scope, no complex keywords"
    )
