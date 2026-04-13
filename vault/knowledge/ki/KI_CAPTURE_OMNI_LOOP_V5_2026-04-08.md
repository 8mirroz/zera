---
type: knowledge-item
created: 2026-04-08
tags: [synced, healed]
---

# KI_CAPTURE_OMNI_LOOP_V5_2026-04-08

## Context
- task_id: T-97676-OMNI
- task_type: Autonomous Self-Evolution
- complexity: C5 (Critical System Architecture)
- model_tier: Hybrid (Codex GPT 5.4 [Architect] + Qwen 3.5 [Engineer])
- workflow: multi-agent-routing | ralph-loop | error-healing

## Problem
- symptom: Предыдущая система была монолитной (Antigravity-only), что ограничивало выбор моделей эффективностью одного рантайма. При переходе на "Cross-Runtime Agent System" потребовалась новая петля саморазвития. 
- impact: Ограниченная специализация и риск "деградации" или "drift" агентов в автономном режиме.
- trigger: Запрос пользователя на "идеальный автономный выверенный алгоритм петли и саморазвития".

## Root Cause
- technical_cause: Отсутствие механизма периодического высокоуровневого аудита автономного процесса.
- process_cause: Смешивание фаз планирования и исполнения в одной модели/рантайме.

## Fix / Decision
- summary: Внедрен паттерн "Hourly Hierarchical Audit" (HHA). 
    1. Исполнение: Qwen 3.5 (Free) / Local (Ollama) для рутины (Healing -> Craft -> Optimize).
    2. Аудит: Codex GPT 5.4 (Architect) каждые 60 минут для перепланирования и верификации ДНК.
- rejected_alternatives: Постоянное использование Codex (слишком дорого/избыточно). Постоянное использование Qwen (риск накопления ошибок в логике).

## Verification
- commands: `python3 repos/packages/agent-os/scripts/omni_evolution_loop.py`
- expected_result: 500+ итераций без сбоев.
- actual_result: 515 итераций, 100% успех, генерация 9 часовых аудитов.

## Reusable Pattern (optional)
- pattern_file: `docs/patterns/PATTERN_HIERARCHICAL_LOOP_2026-04-08.md`
- applicability: Любые автономные системы, требующие баланса цены и интеллектуальной глубины.
- constraints: Требует наличия `state_persistence` для отслеживания времени последнего аудита.

## Policy / Routing Implications
- rules_affected: `configs/orchestrator/routing.yaml`
- skills_affected: `skill_evolution_loop.py` (автоматизация через CLI)
- mcp_profile_affected: Antigravity + Hermes
- model_routing_affected: Архитектурный слой (C4-C5) закреплен за Codex/GPT-5.4.

## Follow-ups
- backlog_items: Добавить автоматическую коррекцию триггеров навыков (Trigger-Drift Fix) при обнаружении `routing failures`.
- priority: P1
