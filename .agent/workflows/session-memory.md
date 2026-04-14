---
description: Управление памятью сессии — запись контекста при старте и сохранение summary перед сжатием. Предотвращает деградацию точности при "Session compressed N times".
---

# /session-memory

## Когда использовать

- **При старте** любой сессии с задачей C2+ или длиннее 10 сообщений
- **При сжатии** — когда видишь "Session compressed N times" (N ≥ 2)
- **Перед /new** — всегда сохраняй summary перед сменой сессии
- **По завершении этапа** — после крупного milestone

---

## Step 1: Старт сессии — запись контекста

Вызови в начале сессии:

```bash
python3 repos/packages/agent-os/scripts/session_context_writer.py \
  --agent <agent_id> \
  --objective "<главная цель сессии>" \
  --task-type <T1-T7> \
  --complexity <C1-C5> \
  --facts "<факт 1>" "<факт 2>" "<факт 3>"
```

**Что писать в `--facts`**: технические решения, ограничения, договорённости с пользователем, текущий стек, критические зависимости.

Сохрани `session_id` из вывода — он нужен для Step 2.

---

## Step 2: Восстановление контекста (новая сессия после /new)

Если начинаешь новую сессию после сжатия — сначала найди предыдущий summary:

```bash
python3 repos/packages/agent-os/scripts/session_summary_saver.py \
  --query \
  --agent <agent_id> \
  --limit 3
```

Прочитай `pending_items` и `key_decisions` из последнего summary — это твой восстановленный контекст.

---

## Step 3: Сохранение summary (перед сжатием или /new)

```bash
python3 repos/packages/agent-os/scripts/session_summary_saver.py \
  --agent <agent_id> \
  --session-id <session_id из Step 1> \
  --summary "<что сделано, что осталось, текущий статус>" \
  --decisions "<решение 1>" "<решение 2>" \
  --completed "<выполненный пункт 1>" "<выполненный пункт 2>" \
  --pending "<следующий шаг 1>" "<следующий шаг 2>" \
  --compression-count <N> \
  --current-file "<текущий файл>" \
  --current-line <номер строки>
```

**Что писать в `--summary`**: одно-два предложения о прогрессе. Достаточно чтобы восстановить контекст без истории чата.

**Для быстрого восстановления позиции**: используй `--current-file` и `--current-line` — это сохраняет точное место в коде.

---

## Правила для агентов

| Триггер | Действие |
|---------|----------|
| Начало сессии (C2+) | Step 1: записать контекст |
| "Session compressed 2 times" | Step 3: сохранить summary |
| "Session compressed 4 times" | Step 3 + предупредить пользователя о /new |
| Перед /new | Step 3 обязательно |
| После /new | Step 2: восстановить контекст |

---

## System Prompt для агентов (добавить в промпт)

```
### Правило сессионной памяти
При старте сессии (C2+):
  → вызови session-start с objective, task_type, complexity, facts

При "Session compressed 2 times":
  → вызови session-summary --save с decisions/completed/pending

При "Session compressed 4 times":
  → session-summary --save + предупреди пользователя о /new

Перед /new:
  → обязательно session-summary --save

После /new (новая сессия):
  → сначала session-summary --query для восстановления контекста
```

---

## Ключи в memory.jsonl

- `session:<agent>:<session_id>:start` — контекст старта (memory_class: working_memory)
- `session:<agent>:<session_id>:summary` — summary перед сжатием (memory_class: working_memory)

Поиск через BM25: `session <agent_id> pending` найдёт незавершённые задачи.
