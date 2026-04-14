---
name: claude-code-patterns
description: >
  Адаптированные паттерны из awesome-claude-code для локальной (offline-first)
  интеграции в Antigravity: CLAUDE.md, slash-commands, hooks и review workflows.
source: https://github.com/hesreallyhim/awesome-claude-code
adapted_for: antigravity-core-v5 (router v4.1, Agent OS v2)
---

# Claude Code Patterns — Antigravity Integration

## Цель

Использовать лучшие практики Claude Code без обязательной авторизации Claude API:
- используем upstream как reference index, а не источник для verbatim copy;
- поддерживаем локально написанные Antigravity-шаблоны команд/settings;
- применяем через `.claude/commands` и `.claude/settings.json`;
- привязываем к нашим правилам (`configs/rules/*`, `configs/orchestrator/*`).

## Источники в репо

- Vendor snapshot: `repos/skills/awesome-claude-code/`
- Curated index: `repos/skills/awesome-claude-code/THE_RESOURCES_TABLE.csv`
- Local templates: `templates/claude-code/`
- Installer: `scripts/install_claude_templates.sh`
- License guard: `awesome-claude-code` is CC BY-NC-ND 4.0; do not redistribute modified upstream list content.

## Быстрый запуск

```bash
# Установить адаптированные команды и settings в текущий проект
bash scripts/install_claude_templates.sh --target .

# Если нужно перезаписать существующие .claude файлы
bash scripts/install_claude_templates.sh --target . --force
```

## Что ставится

1. `.claude/commands/context-prime.md`
2. `.claude/commands/pr-review.md`
3. `.claude/commands/fix-github-issue.md`
4. `.claude/commands/update-docs.md`
5. `.claude/commands/design-review.md`
6. `.claude/settings.json` (если отсутствует, либо overwrite при `--force`)

## Operational Patterns

### 1) Context Prime перед реализацией
Используй `/context-prime`, чтобы собрать минимально достаточный контекст и зафиксировать assumptions.

### 2) Review как gate, а не формальность
Используй `/pr-review` для отчёта с severity и file references.

### 3) Доки синхронно с кодом
Используй `/update-docs` после существенных изменений поведения или архитектуры.

### 4) Hooks в quick-mode
`PostToolUse` запускает `bash scripts/run_quality_checks.sh --quick`.
Этот режим оптимизирован для частого запуска на каждом write/edit.

## Mapping на Antigravity

- Review standards: `configs/rules/ENGINEERING_STANDARDS.md`
- Completion gates: `configs/orchestrator/completion_gates.yaml`
- Routing: `configs/rules/TASK_ROUTING.md`
- Workspace constraints: `configs/rules/WORKSPACE_STANDARD.md`

## Guardrails

- Не копировать внешние команды «как есть» в production workflow.
- Любой шаблон адаптировать к локальным правилам и путям.
- Не добавлять destructive hooks/permissions без явного запроса.
- Не считать команду валидной без локальной проверки выполнения.
- Не использовать leak/decompiled/source-map based repos как активный source.
