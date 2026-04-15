# Hermes Zera — Telegram AI Agent v2

AI-агент платформы Antigravity Core с интеллектуальной маршрутизацией и SOP-orchestration.

## Возможности

- **SOUL.md v2 Contract** — structured agent contract (delegation, triggers, tools, boundaries)
- **Классификация задач** — автоматическое определение сложности (C1–C5)
- **Trigger matching** — авто-активация skills и SOP по ключевым словам из SOUL.md
- **Мульти-модельный роутинг** — выбор оптимальной модели через UnifiedRouter
- **SOP Pipeline** — MetaGPT-style phased execution (Orchestrator→Architect→Engineer→Reviewer)
- **Fallback chains** — автоматический переход к резервной модели при ошибке
- **История разговоров** — контекст на каждый чат (последние 20 сообщений)

## Архитектура

```
Telegram User
    │
    ▼
┌──────────────────────────────────────────────────┐
│  bot.py (python-telegram-bot)                    │
│  /start, /stats, /debug                          │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  src/telegram_agent.py — HermesZeraAgent          │
│  ┌────────────────────────────────────────────┐  │
│  │ 1. SOUL.md v2 Contract Parser              │  │ ← identity, delegation, triggers
│  │ 2. task_classifier.py                      │  │ → C1-C5 tier
│  │ 3. trigger matching                        │  │ → SOP/skill/human escalation
│  │ 4. UnifiedRouter (Agent OS)                │  │ → model + fallback chain
│  │ 5. Execute:                                │  │
│  │    - C1-C2: direct model call              │  │
│  │    - C3+: SOP pipeline (if triggered)      │  │
│  │ 6. ChatSession memory                      │  │
│  └────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  src/sop_pipeline.py — SOPPipeline               │
│  Phase 1: Orchestrator → decomposition + plan    │
│  Phase 2: Architect → design + tradeoffs         │
│  Phase 3: Engineer → implementation + tests      │
│  Phase 4: Reviewer → critique + recommendation   │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│  src/agent_executor.py — API calls               │
│  OpenRouter (100+ models) + Anthropic (Claude)   │
│  Automatic fallback chain                        │
└──────────────────────────────────────────────────┘
```

## Быстрый старт

1. Скопируй `.env.example` → `.env`:
   ```bash
   cp .env.example .env
   ```

2. Установи зависимости:
   ```bash
   uv sync
   # или: pip install -r requirements.txt
   ```

3. Заполни токены в `.env`:
   - `TELEGRAM_BOT_TOKEN` — от @BotFather
   - `OPENROUTER_API_KEY` — или `ANTHROPIC_API_KEY`

4. Запусти:
   ```bash
   uv run python bot.py        # Production
   python bot.py --debug       # С routing info
   ```

## SOUL.md v2 — Agent Contract

SOUL.md теперь — не просто текст, а **structured YAML-embedded contract**:

```yaml
## Identity — имя, роль, capabilities
## Personality — стиль, язык, принципы
## Boundaries — allowed / forbidden
## Delegation — когда делегировать суб-агентам (по tier)
## Triggers — keywords для SOP, skills, human escalation
## Tools — доступные модули и их маппинг
## Behavior — response policy per tier (model, tokens, format)
## Safety — rate limits, error handling, content policy
## Memory — per-chat context, routing logs
```

**Delegation rules:**
| Tier | Execute | Review | Escalate |
|------|---------|--------|----------|
| C1 | self | none | — |
| C2 | self | self | — |
| C3 | self | reviewer | design_tradeoff → architect |
| C4 | sop_pipeline | reviewer | strategic_conflict → council |
| C5 | sop_pipeline | reviewer + council | security_risk → human |

**Trigger types:**
- `sop_activation` — запускает SOP pipeline (архитектура, микросервисы, multi-agent)
- `skill_activation` — активирует skills (debugging, TDD, planning, verification)
- `human_escalation` — требует человеческого аудита (security, payments, critical)

## SOP Pipeline — Phased Execution

Для C3+ задач с SOP-триггерами запускается **MetaGPT-style pipeline**:

```
User: "Спроектируй архитектуру микросервисов"
         │
         ▼
    [C4 + SOP triggers matched]
         │
         ▼
  ┌── Orchestrator ──┐
  │ Декомпозиция      │
  │ Роли, план, риски │
  └────────┬─────────┘
           ▼
  ┌── Architect ────┐
  │ Дизайн системы   │
  │ Trade-offs       │
  │ Зависимости      │
  └────────┬─────────┘
           ▼
  ┌── Engineer ─────┐
  │ Реализация       │
  │ Компоненты       │
  │ Тесты            │
  └────────┬─────────┘
           ▼
  ┌── Reviewer ─────┐
  │ Критика          │
  │ Качество         │
  │ Рекомендация     │
  └────────┬─────────┘
           ▼
    Synthesized Response
```

## Конфигурация

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `OPENROUTER_API_KEY` | API-ключ OpenRouter (100+ моделей) |
| `ANTHROPIC_API_KEY` | API-ключ Anthropic (Claude) |
| `AGENT_NAME` | Отображаемое имя бота |
| `LOG_LEVEL` | Уровень логирования (INFO, DEBUG) |

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/stats` | Статистика сессии |
| `/debug` | Toggle debug режим |

## Тесты

```bash
# Classifier
python3 -c "import sys; sys.path.insert(0,'src'); from task_classifier import classify; print(classify('Напиши тест'))"

# Contract Parser
python3 -c "import sys; sys.path.insert(0,'src'); from agent_contract import ContractParser; from pathlib import Path; c = ContractParser(Path('SOUL.md')).load(); print(c.name, c.role)"

# Trigger Matching
python3 -c "import sys; sys.path.insert(0,'src'); from agent_contract import ContractParser; from pathlib import Path; p = ContractParser(Path('SOUL.md')); p.load(); print(p.match_triggers('У меня баг'))"
```

## Интеграция в Antigravity Core

Размещение: `repos/telegram/hermes-zera/`
Стандарт: [`WORKSPACE_STANDARD`](../../../configs/rules/WORKSPACE_STANDARD.md) §Placement Matrix

Agent OS: `repos/packages/agent-os/src/agent_os/`
UnifiedRouter: `configs/orchestrator/router.yaml`
Role Contracts: `configs/orchestrator/role_contracts/`
