---
type: knowledge-item
created: 2026-04-10
tags: [synced, healed]
---

# Zera Self-Evolution Loop — Руководство

**Дата:** 9 апреля 2026  
**Статус:** ✅ ГОТОВО К ЗАПУСКУ  
**Автор:** Agent OS Architecture Team

---

## Что это

Бесконечный цикл саморазвития для Hermes Zera — автоматизированная система, которая постоянно анализирует, улучшает и развивает способности Zera в рамках конституционных ограничений.

---

## Архитектура (7-фазный цикл)

```
┌─────────────────────────────────────────────────────────────┐
│           ZERA SELF-EVOLUTION LOOP                          │
│                                                             │
│   ┌─────────┐    ┌──────────┐    ┌─────────┐               │
│   │ 1.OBSERVE│───▶│ 2.CLASSIFY│───▶│ 3.SCORE │               │
│   │          │    │          │    │         │               │
│   │ • Scout  │    │ • Risk   │    │ • Capab │               │
│   │ • Review │    │ • Class  │    │ • Risk  │               │
│   │ • Memory │    │ • Auto?  │    │ • Novel │               │
│   └─────────┘    └──────────┘    └────┬────┘               │
│                                       │                     │
│   ┌─────────┐    ┌──────────┐    ┌────▼────┐               │
│   │ 8.REFLECT◀───│ 7.PROMOTE│◀───│ 6.EVAL  │               │
│   │          │    │          │    │         │               │
│   │ • Telem  │    │ • Promote│    │ • Harness│              │
│   │ • Log    │    │ • Rollbk │    │ • Checks│               │
│   └─────────┘    └────▲─────┘    └────┬────┘               │
│                       │               │                     │
│                  ┌────┴─────┐    ┌────▼────┐               │
│                  │ 5.SANDBOX│◀───│ 4.DESIGN│               │
│                  │          │    │         │               │
│                  │ • Beta   │    │ • Prompt│               │
│                  │ • Isolate│    │ • Loop  │               │
│                  └──────────┘    └─────────┘               │
│                                                             │
│   ═══════════════════════════════════════════════           │
│              GOVERNANCE GOVERNOR (всегда активен)           │
│   • Freeze conditions    • Personality delta budget         │
│   • Candidate classes    • Rollback requirements            │
│   • Approval routes      • Telemetry capture                │
│   ═══════════════════════════════════════════════           │
└─────────────────────────────────────────────────────────────┘
```

---

## Фазы подробно

### 1. OBSERVE — Наблюдение
**Что делает:** Собирает сигналы из трёх источников
- **External patterns:** Scout daemon ищет новые AI/ML тренды через Exa API
- **Internal failures:** Анализ последних 100 трейсов на ошибки
- **Memory signals:** Проверка BM25 памяти на записи с низкой уверенностью

**Результат:** Список наблюдений для классификации

### 2. CLASSIFY — Классификация
**Что делает:** Определяет кандидата на эволюцию
- Выбирает класс из 15 возможных (governance)
- Определяет уровень риска (low/medium/high)
- Проверяет auto-promote eligibility

**Классы кандидатов:**
- `skill_refinement` — улучшение навыков
- `workflow_optimization` — оптимизация процессов
- `mcp_enhancement` — улучшение MCP серверов
- `prompt_compression` — сжатие промптов
- `memory_organization` — организация памяти
- `routing_improvement` — улучшение маршрутизации
- `tool_integration` — интеграция инструментов
- `observability_boost` — улучшение наблюдаемости
- `safety_hardening` — усиление безопасности
- `performance_tuning` — настройка производительности
- `knowledge_synthesis` — синтез знаний
- `personality_calibration` — калибровка личности
- `branch_template` — шаблоны ветвления
- `external_pattern_adoption` — внешние паттерны
- `failure_driven_fix` — исправление по ошибкам

### 3. SCORE — Оценка
**Что делает:** Оценивает кандидата по 5 измерениям
- **Capability potential (30%):** Потенциал улучшения
- **Risk assessment (25%):** Оценка рисков
- **Novelty (15%):** Новизна подхода
- **Alignment with goals (20%):** Соответствие целям
- **Resource efficiency (10%):** Эффективность ресурсов

**Порог:** score > 0.5 для продолжения

### 4. DESIGN — Проектирование
**Что делает:** Создаёт промпт для эволюции
- Использует `zera-evolve.sh` (10 алгоритмов ротации)
- Включает constitutional boundaries
- Определяет success criteria

**Алгоритмы ротации:**
1. `karpathy` — Итеративная самокоррекция
2. `rsi` — Рекурсивное самоусовершенствование
3. `darwin-goedel` — Эволюционная самореференция
4. `pantheon` — Мультиперсонажный совет
5. `self-improving` — Мета-обучение
6. `karpathy-swarm` — Параллельная самокоррекция
7. `ralph` — Итеративное уточнение
8. `agentic-ci` — Непрерывная интеграция
9. `self-driving` — Автономная работа
10. `meta-learning` — Обучение обучению

### 5. SANDBOX — Песочница
**Что делает:** Тестирует в изоляции (beta profile)
- Создаёт beta профиль из основного
- Beta полностью изолирована от production
- Все изменения тестируются в beta

### 6. EVAL — Оценка
**Что делает:** Запускает evaluation suite
- `check_zera_hardening.py` — основной валидатор
- Проверка governance control plane
- Базовые проверки конфигов

### 7. PROMOTE — Продвижение
**Что делает:** Продвигает или откатывает
- **Eval PASSED:** Beta → Main (promote)
- **Eval FAILED:** Rollback к backup
- **Нет beta:** Принимается концептуально (logged)

### 8. REFLECT — Рефлексия
**Что делает:** Захватывает телетрию
- Логирует результат цикла
- Обновляет state
- Генерирует рефлексию

---

## Запуск

### Быстрый старт

```bash
# Dry run (без выполнения — для проверки)
python3 scripts/self_evolution_loop.py --dry-run --cycles 3

# Запуск навсегда (с интервалом 5 минут)
python3 scripts/self_evolution_loop.py

# Запуск на 10 циклов с интервалом 1 минута
python3 scripts/self_evolution_loop.py --cycles 10 --interval 60

# Проверить статус
python3 scripts/self_evolution_loop.py --status

# Сбросить состояние
python3 scripts/self_evolution_loop.py --reset
```

### Фоновый запуск (nohup)

```bash
# Запустить в фоне
nohup python3 scripts/self_evolution_loop.py --interval 3600 \
  > /tmp/zera-evolution.log 2>&1 &

# Проверить процесс
ps aux | grep self_evolution_loop

# Остановить
kill $(pgrep -f self_evolution_loop)
```

### Cron (каждые 6 часов)

```bash
# Добавить в crontab
crontab -e

# Добавить строку:
0 */6 * * * cd /Users/user/antigravity-core && python3 scripts/self_evolution_loop.py --interval 3600 >> /tmp/zera-evolution.log 2>&1
```

---

## Команды управления

| Команда | Описание |
|---------|----------|
| `--status` | Показать текущее состояние |
| `--reset` | Сбросить состояние эволюции |
| `--dry-run` | Симуляция без выполнения |
| `--cycles N` | Максимум N циклов (0 = ∞) |
| `--interval S` | Секунд между циклами (по умолчанию: 300) |

---

## Конституционные ограничения

**Governor:** `configs/tooling/zera_growth_governance.json`

### Freeze conditions (эволюция останавливается)
- 2 последовательные регрессии личности
- Zera profile не найден
- Мутация governance файлов
- Неклассифицированный кандидат
- Отсутствует rollback path
- Breach personality delta budget
- Сигналы дрейфа

### Запрещённые действия
- ❌ Прямая запись в persona memory
- ❌ Изменение governance файлов
- ❌ Изменение core identity
- ❌ Автономные внешние контакты без approval
- ❌ Финансовые обязательства

### Разрешённые действия
- ✅ Анализ и предложения улучшений
- ✅ Оптимизация workflow
- ✅ Рефайнмент навыков
- ✅ Организация памяти
- ✅ Улучшение наблюдаемости

---

## Мониторинг

### State file
```bash
cat .agents/evolution/state.json
```

### Telemetry
```bash
tail -f .agents/evolution/telemetry.jsonl | jq
```

### Log
```bash
tail -f .agents/evolution/loop.log
```

### Scout Journal
```bash
cat .agents/evolution/scout_journal.md
```

---

## Интеграция с Hermes

### Через cron

Файл: `Zera/cron-self-evolution.json`

```json
{
  "command": "python3 scripts/self_evolution_loop.py",
  "schedule": "0 */6 * * *",
  "profile": "zera"
}
```

### Через zera-evolve.sh

```bash
# Один цикл эволюции
bash scripts/zera-evolve.sh --loop karpathy --class skill_refinement

# Dry run
bash scripts/zera-evolve.sh --dry-run
```

---

## Troubleshooting

### Evolution frozen

```bash
# Проверить причину
python3 scripts/self_evolution_loop.py --status

# Если consecutive regressions — сбросить
python3 scripts/self_evolution_loop.py --reset
```

### Scout daemon не работает

```bash
# Проверить EXA_API_KEY
cat ~/.hermes/profiles/zera/.env | grep EXA_API_KEY

# Если нет — зарегистрировать на exa.ai
```

### Beta manager не работает

```bash
# Проверить beta manager
python3 scripts/beta_manager.py setup
python3 scripts/beta_manager.py rollback
```

---

## Статистика (после dry run)

```
Total cycles:     4
Successful:       0 (dry run)
Failed:           0
Promoted:         0
Loop algorithms:  karpathy → rsi → darwin-goedel → pantheon
```

---

## Следующие шаги

1. ✅ Создан основной цикл (`self_evolution_loop.py`)
2. ✅ Протестирован dry run (4 цикла)
3. ✅ Создан cron конфиг (`Zera/cron-self-evolution.json`)
4. ⏳ Настроить EXA_API_KEY для scout daemon
5. ⏳ Запустить live режим
6. ⏳ Мониторить первые реальные эволюции
7. ⏳ Настроить оповещения о promote/rollback

---

**Статус:** ✅ ГОТОВО К ЗАПУСКУ  
**Режим:** Dry run протестирован, Live режим готов

---

## Update 2026-04-09: Meta-Learning + Memory + Self-Reflection

### Что добавлено

1. **Meta-learning selection (UCB)**
- Выбор loop-алгоритма теперь адаптивный, а не только ротация.
- Система балансирует exploration/exploitation по накопленному reward.

2. **Meta-memory цикла (`.agents/evolution/meta_memory.json`)**
- Каждый цикл сохраняет insight: `algorithm`, `candidate_class`, `score`, `status`, `reward`, `next_focus`, `risk_hint`.
- Память ограничена (`MAX_META_MEMORY_ENTRIES`) и используется в будущих циклах.

3. **Self-reflection как структурированный сигнал**
- Рефлексия теперь не только текст, но и структурный payload:
  - `what_worked`
  - `what_failed`
  - `next_focus`
  - `risk_hint`
- `next_focus` может влиять на выбор следующего candidate class.

4. **Оптимизация observe/I-O**
- `OBSERVE` собирает внешние/внутренние сигналы параллельно.
- Чтение JSONL логов сделано через tail-like чтение последних N строк, без загрузки всего файла.

### Новый operational эффект
- Цикл начинает **учиться на исходах** (промоут/rollback/quality/скорость), а не просто крутить алгоритмы по кругу.
- Память и рефлексия становятся частью решения следующего шага.
