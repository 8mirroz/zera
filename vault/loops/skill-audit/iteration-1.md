# Skill Audit - Iteration 1

**Date:** 2026-04-22 02:50 MSK
**Trigger:** idle-system-check cron job
**Algorithm:** Skill Audit (аудит навыков)

## Findings

### Size Distribution
- Total skills: 115
- Oversized (>50KB): 2

### Issue: pytorch-fsdp (156K)
Этот навык представляет собой дамп документации PyTorch — не структурированный навык с процедурами, командами и паттернами. Формат SKILL.md:
- 156K чистой документации
- Нет trigger conditions
- Нет numbered steps
- Нет pitfalls
- Нет verification commands
- Только raw API reference

### Issue: research-paper-writing (101K)  
Аналогичная проблема — документация вместо навыка.

## Recommendations

1. **pytorch-fsdp** — либо:
   - Удалить и полагаться на web_search/WebDocs
   - Переписать как краткий quick-ref с ключевыми командами запуска FSDP
   
2. **research-paper-writing** — переписать с фокусом на:
   - конкретные шаблоны (LaTeX, ACL, NeurIPS)
   - команды (latexmk, pandoc)
   - pipeline stages

## Status
В ожидании решения Artem.
