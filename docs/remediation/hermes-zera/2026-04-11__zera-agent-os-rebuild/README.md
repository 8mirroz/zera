# Zera Agent OS Rebuild Program

Эта папка — контрольный пакет ребилда Zera в управляемый Agent OS, а не очередную хрупкую chat-wrapper конфигурацию.

## Состав

- `00_RESEARCH_REPORT.md` — официальные источники, GitHub-сигналы и community-сигналы.
- `01_LOCAL_FORENSIC_AUDIT.md` — локальная forensic-диагностика и root cause.
- `02_TARGET_ARCHITECTURE.md` — целевая архитектура Agent OS.
- `03_ULTRAPROMPTS/` — role prompts для выполнения ребилда.
- `04_IMPLEMENTATION_RUNBOOK.md` — упорядоченные команды внедрения.
- `05_VALIDATION_MATRIX.md` — gates и acceptance criteria.
- `06_ROLLBACK_PLAN.md` — rollback и emergency stop.
- `07_ROLLOUT_PLAN.md` — staged rollout от ручного режима к контролируемой автономии.
- `08_IMPLEMENTATION_REPORT.md` — фактический отчет после внедрения и проверки.

## Текущий статус внедрения

- Добавлен контроллер `zera-evolutionctl`.
- Создан backup внешнего Zera profile.
- Опасный unmanaged self-evolution cron job отключен.
- Legacy state schema нормализована.
- Исправлен repo-root calculation в `self_evolution_loop.py`.
- Добавлен безопасный default no-promote mode; promotion требует явного `--allow-promote --force`.
- Hardening, MCP, wiki-core, workflow registry, trace registry, `swarmctl doctor`, Qwen CLI и Hermes CLI smoke теперь проходят.
- Агрессивная автономия пока запрещена: gateway adapters, live LLM scoring, optional MCP servers и promotion pipeline еще не подтверждены.

## Первая команда оператора

```bash
zera-evolutionctl status
```
