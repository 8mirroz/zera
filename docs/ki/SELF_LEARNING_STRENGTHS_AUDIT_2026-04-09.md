# Анализ силы скриптов самообучения Zera

**Дата:** 9 апреля 2026  
**Статус:** 🔍 Честный аудит  
**Автор:** Architecture Review

---

## Вердикт: 3/10 — Каркас есть, интеллекта нет

Цикл саморазвития **технически работает** (5/5 циклов прошли), но **интеллектуальная глубина крайне мала**. Это красивый оркестратор с пустым двигателем.

---

## Построчный анализ каждого компонента

### 1. self_evolution_loop.py (1016 строк)

#### ✅ Что работает реально

| Компонент | Статус | Качество |
|-----------|--------|----------|
| Цикл управления | ✅ Работает | Хорошо — state, telemetry, graceful shutdown |
| Phase OBSERVE — review_recent_failures | ✅ Работает | Читает agent_traces.jsonl, находит ошибки |
| Phase OBSERVE — check_memory_signals | ✅ Работает | Проверяет confidence < 0.5 |
| Phase CLASSIFY | ✅ Работает | Логика приоритетов корректна |
| Phase SANDBOX — beta_manager | ✅ Работает | Создаёт/удаляет beta профиль |
| Phase EVAL — hardening validator | ✅ Работает | 26 eval cases, governance checks |
| Phase PROMOTE — promote/rollback | ✅ Работает | Через beta_manager |
| Phase REFLECT — telemetry capture | ✅ Работает | JSONL с 21 полем |
| Freeze conditions | ✅ Работает | 2 consecutive regressions = stop |
| JSON serialization fix | ✅ Работает | Enum handler added |
| Scout timeout fix | ✅ Работает | 15s timeout, graceful skip |

#### ❌ Что stub/mock/placeholder

| Компонент | Проблема | Серьёзность |
|-----------|----------|-------------|
| **phase_score()** | `random.uniform(0.5, 0.9)` — рандом вместо LLM оценки | 🔴 КРИТИЧНО |
| **phase_design()** | Генерирует строку-заглушку вместо реального промпта | 🔴 КРИТИЧНО |
| **scout_external_patterns()** | Если нет EXA_API_KEY — всегда `skipped` | 🟡 СРЕДНЕ |
| **Нет реального LLM вызова** | Цикл не вызывает LLM для анализа, дизайна, оценки | 🔴 КРИТИЧНО |
| **Нет реального изменения кода** | SANDBOX + EVAL проверяют конфиги, но не меняют код | 🔴 КРИТИЧНО |
| **Нет feedback loop** | Результат одного цикла не влияет на следующий | 🟡 СРЕДНЕ |
| **Нет diff/patch generation** | Нет механизма создания изменений в репозитории | 🔴 КРИТИЧНО |

---

### 2. scout_daemon.py (94 строки)

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| Exa API запрос | ✅ Работает | Нужен API ключ ($$) |
| Сохранение в journal | ✅ Работает | Markdown append |
| Без ключа | ❌ Пропускает | Нет fallback источников |

**Оценка:** 5/10 — работает если есть ключ, иначе бесполезен

---

### 3. beta_manager.py (~100 строк)

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| setup_beta | ✅ Работает | Копирует zera → zera_beta |
| promote_beta | ✅ Работает | Копирует обратно с backup |
| rollback_beta | ✅ Работает | Удаляет beta |

**Оценка:** 7/10 — работает, но примитивно (просто copy/paste файлов)

---

### 4. check_zera_hardening.py (680 строк)

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| Governance validation | ✅ Работает | 15 candidate classes, 14 freeze conditions |
| Eval cases validation | ✅ Работает | 26 test cases |
| Secret hygiene | ✅ Работает | Regex detection API keys |
| Hermes adapter contract | ✅ Работает | Reference validation |
| Secret detection | ⚠️ Базовый | Только 4 паттерна (openai, supabase, google, slack) |
| Script validation | ⚠️ Базовый | Проверяет наличие строк, не семантику |

**Оценка:** 6/10 — хорош для проверки конфигов, но не проверяет реальное поведение

---

### 5. zera-evolve.sh (~200 строк)

| Компонент | Статус | Проблема |
|-----------|--------|----------|
| Loop rotation | ✅ Работает | 10 алгоритмов |
| Freeze checking | ✅ Работает | Читает governance |
| Prompt building | ⚠️ Шаблонный | Статичный текст, нет адаптивности |
| Execution | ⚠️ Зависит от hermes CLI | Требует работающий hermes |

**Оценка:** 4/10 — оркестратор без интеллекта

---

## Чего НЕТ (критические пробелы)

### 1. Нет реального анализа кода
- Цикл не читает код репозитория
- Не предлагает изменения в файлах
- Не создаёт патчи/PR
- Всё работает на уровне конфигов

### 2. Нет интеллектуальной оценки
- `random.uniform()` вместо LLM-based scoring
- Нет сравнения "до/после"
- Нет метрик качества изменений

### 3. Нет feedback learning
- Результат цикла не обучает систему
- Нет pattern recognition
- Нет cumulative knowledge

### 4. Нет real LLM integration
- Цикл не вызывает LLM для:
  - Анализа candidate
  - Генерации улучшений
  - Оценки результатов
  - Self-reflection

### 5. Нет real code changes
- SANDBOX = copy config files
- EVAL = check config syntax
- PROMOTE = copy config files back
- Ни одна строка кода не меняется

---

## Что цикл реально делает (честно)

```
Cycle N:
1. OBSERVE:  scout skipped → review traces → check memory confidence
2. CLASSIFY: "external_pattern_adoption" (потому что scout=skipped)
3. SCORE:    random.uniform(0.5, 0.9) → ~0.65
4. DESIGN:   "Execute evolution cycle via zera-evolve.sh..."
5. SANDBOX:  cp zera/ → zera_beta/
6. EVAL:     check_zera_hardening.py → PASS (конфиги валидны)
7. PROMOTE:  cp zera_beta/ → zera/ (без изменений)
8. REFLECT:  log telemetry {"score": 0.65, "passed": true}

Результат: Ничего не изменилось, но цикл "прошёл" ✅
```

---

## План улучшений по приоритетам

### P0 — Критические (без этого цикл бессмыслен)

| # | Улучшение | Сложность | Эффект |
|---|-----------|-----------|--------|
| 1 | LLM-based scoring вместо random | Низкая | ✅ Реальная оценка кандидатов |
| 2 | Real code analysis — чтение и анализ файлов | Средняя | ✅ Понимание кодовой базы |
| 3 | Diff/patch generation — создание реальных изменений | Высокая | ✅ Цикл реально меняет код |
| 4 | Feedback loop — результаты влияют на следующий цикл | Средняя | ✅ Cumulative learning |

### P1 — Важные

| # | Улучшение | Сложность | Эффект |
|---|-----------|-----------|--------|
| 5 | Multi-source scout (GitHub trending, arXiv, HuggingFace) | Средняя | ✅ Без EXA_API_KEY |
| 6 | Before/after metrics — сравнение результатов | Средняя | ✅ Измеримость улучшений |
| 7 | Self-reflection с LLM — агент анализирует свой прогресс | Средняя | ✅ Мета-обучение |
| 8 | Pattern recognition — обнаружение повторяющихся проблем | Средняя | ✅ Proactive fixes |

### P2 — Желательные

| # | Улучшение | Сложность | Эффект |
|---|-----------|-----------|--------|
| 9 | A/B testing — сравнение изменений | Высокая | ✅ Доказательная эволюция |
| 10 | Human-in-the-loop — оператор одобрует изменения | Средняя | ✅ Безопасность |
| 11 | Knowledge graph — накопление знаний | Высокая | ✅ Долгосрочная память |
| 12 | Auto-generated reports — отчёты о прогрессе | Низкая | ✅ Визуализация |

---

## Резюме

**Текущее состояние:**
- 🟢 Оркестрация — работает отлично
- 🟢 Governance — robust, comprehensive
- 🟢 Telemetry — full coverage
- 🔴 Интеллект — отсутствует (random scores, no LLM calls)
- 🔴 Реальные изменения — отсутствуют (config copy only)
- 🔴 Feedback learning — отсутствует

**Метафора:** Это как если бы у тебя был космический корабль с идеальной навигацией, но без двигателя. Ты знаешь куда лететь, но не двигаешься.

**Рекомендация:** Начать с P0 #1 (LLM scoring) — это даст максимальный эффект при минимальных усилиях.
