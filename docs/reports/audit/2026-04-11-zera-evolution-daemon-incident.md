# Отчет: инцидент фонового Zera evolution loop

Дата: 2026-04-11  
Рабочая директория: `/Users/user/antigravity-core`  
Запрошенное действие: остановить фоновый процесс, оценить эффективность, найти ошибки и слабые места.

## Краткий вывод

Фоновый "бесконечный цикл саморазвития" не был полноценным агентом и не выполнял заявленные 10 алгоритмов. Это был набор inline `python3 -c` процессов, запущенных из `bash`, без supervisor-контракта, PID-файла, lock-файла, корректного shutdown и без реального вызова алгоритмов.

Главный заявленный PID `11920` остановлен. Дополнительно обнаружены и остановлены связанные evolution-процессы `11649`, `11701`, `11938`. После остановки активных процессов по сигнатурам `Zera Evolution Daemon`, `vault/loops`, `current_algorithm`, `next_algorithm`, `zera-evolve`, `zera-self-evolution` не осталось.

## Что было найдено

### Процессы

- `11920` был `/bin/bash -lic ... python3 -c ...`.
- После `SIGTERM` процесс не завершился корректно.
- После `SIGKILL` стал `defunct`, то есть полезная работа остановлена, но родительский процесс `hermes -p zera chat` с PID `8205` не сразу забрал exit status.
- Были найдены дополнительные циклы:
  - `11649` — shell-обертка старого inline loop.
  - `11701` — дочерний Python-процесс.
  - `11938` — orphan Python-процесс с PPID `1`.

Это означает, что запуск был не единичным управляемым daemon, а несколькими независимыми процессами.

### State-файл

Файл `/Users/user/antigravity-core/vault/loops/.evolve-state.json` на момент проверки:

```json
{
  "current_cycle": 0,
  "last_run": null,
  "algorithm_order": [
    "karpathy",
    "rsi",
    "darwin-goedel",
    "pantheon",
    "self-improving",
    "swarm",
    "ralph",
    "agentic-ci",
    "self-driving",
    "meta-learning"
  ],
  "next_algorithm": "karpathy"
}
```

Критичный факт: `last_run` остался `null`, а `current_cycle` остался `0`. Значит процесс не фиксировал успешные циклы.

### Несовместимость state schema

Inline loop обращался к ключу:

```python
state["current_algorithm"]
```

Но в актуальном `.evolve-state.json` такого ключа нет. Есть `next_algorithm`.

Итог: процесс должен был бесконечно ловить `KeyError: 'current_algorithm'`, печатать ошибку и спать 1 секунду. Полезного evolution-цикла не происходило.

### Реальная логика алгоритмов отсутствовала

В inline loop были только комментарии:

```python
# Логика выполнения текущего алгоритма
# Здесь будет выполнение конкретного алгоритма
```

Ни один из 10 алгоритмов фактически не вызывался. Не было вызова `scripts/zera/zera-evolve.sh`, `scripts/internal/self_evolution_loop.py`, валидаторов, тестов, sandbox, promotion gate или rollback.

## Почему агент не отвечал

Вероятные причины по убыванию важности:

1. Родительский процесс `hermes -p zera chat` держал несколько фоновых процессов и zombie-child, что создает грязное состояние сессии.
2. Inline loop был ошибочным и мог постоянно писать ошибки в stdout/stderr с частотой 1 раз в секунду.
3. Qwen/IDE показал ошибку `Qwen OAuth refresh returned invalid JSON`, то есть refresh-запрос OAuth получил не JSON. Русское пояснение: Qwen ожидал JSON-ответ от OAuth endpoint, но получил пустой/HTML/ошибочный ответ.
4. Локальный `qwen -p 'ping'` после проверки ответил `Pong!`, а `/Users/user/.qwen/oauth_creds.json` является валидным JSON. Значит OAuth-проблема не выглядит как поврежденный локальный creds-файл; вероятнее, это временный сбой refresh endpoint, сетевой/прокси-сбой или баг версии VS Code companion/Qwen extension.

## Оценка эффективности

Эффективность текущего фонового цикла: близка к 0%.

Основания:

- `last_run` не обновлялся.
- `current_cycle` не увеличивался.
- алгоритмы не вызывались.
- state schema не совпадала с кодом.
- процесс не имел измеримой цели, метрик результата и stop condition.
- не было лог-файла, кроме stdout/stderr сессии.
- не было single-instance lock, поэтому запустилось несколько процессов.
- не было healthcheck/status команды.

Исторический `.agent/evolution/loop.log` показывает, что более ранний настоящий `scripts/internal/self_evolution_loop.py` был существенно ближе к рабочей системе: он проходил фазы OBSERVE/CLASSIFY/SCORE/DESIGN/SANDBOX/EVAL/PROMOTE/REFLECT. Но там тоже были серьезные проблемы:

- старые циклы падали на `TypeError: Object of type CandidateStatus is not JSON serializable`;
- часть циклов считалась успешной даже при rollback после failed eval;
- promotion мог проходить по слишком слабой семантике: "external_pattern_adoption" без явной доказательной привязки к изменению;
- были зафиксированы regressions/freeze-состояния;
- документация указывает запуск `scripts/self_evolution_loop.py`, но фактический файл находится в `scripts/internal/self_evolution_loop.py`.

## Ошибки и слабые места

1. Нет одного canonical runner.
   Документация, shell-скрипты и фактический Python runtime расходятся.

2. Нет single-instance protection.
   Можно запустить несколько evolution loops одновременно, что уже произошло.

3. Нет PID-файла и lifecycle-команд.
   Нельзя надежно выполнить `start/status/stop/restart`.

4. Нет строгой state schema.
   Один процесс ожидает `current_algorithm`, state содержит `next_algorithm`, legacy state хранит только индекс в `.evolve-state`.

5. Ошибки скрываются бесконечным циклом.
   `except Exception as e: print(...); sleep(1)` превращает системную ошибку в бесконечный шум.

6. Нет backoff.
   Ошибка повторяется каждую секунду, что увеличивает нагрузку и засоряет вывод.

7. Нет полезной работы в inline daemon.
   Код только читает/пишет state и содержит placeholder-комментарии.

8. Shutdown некорректный.
   `SIGTERM` не дал чистого завершения для PID `11920`; пришлось применять `SIGKILL`.

9. Состояние и отчеты пишутся в `vault/`, хотя workspace standard допускает верхний уровень только `configs/`, `docs/`, `repos/`, `sandbox/`, `templates/`.
   Это уже существующая структура, но она конфликтует с текущим `WORKSPACE_STANDARD.md` и требует отдельного архитектурного решения.

10. Qwen OAuth failure не изолирован от agent runtime.
    Ошибка внешнего auth refresh может блокировать агентский UX, но runner не имеет fallback на другой backend или понятного degraded mode.

## Что улучшить перед следующим запуском

1. Запретить inline `python3 -c` для evolution.
   Запускать только canonical script: `python3 scripts/internal/self_evolution_loop.py`.

2. Добавить supervisor wrapper:
   - `scripts/zera/evolutionctl.sh start|status|stop|tail`;
   - PID-файл в `runtime/locks/` или согласованном control dir;
   - lock через `flock` или atomic file lock;
   - отказ старта, если loop уже активен.

3. Нормализовать state:
   - один JSON schema;
   - поля `current_cycle`, `current_algorithm`, `next_algorithm`, `last_run`, `last_error`, `consecutive_errors`, `status`;
   - миграция legacy `.evolve-state`.

4. Сделать fail-fast для schema mismatch.
   Если state некорректен, процесс должен остановиться с понятным отчетом, а не крутиться бесконечно.

5. Ввести bounded defaults.
   По умолчанию только `--cycles 1` или `--cycles 3`; бесконечный режим только с явным `--forever --interval >= 300`.

6. Пересмотреть success semantics.
   Цикл не должен считаться успешным, если eval failed и был rollback.

7. Ввести минимальные acceptance gates:
   - state updated;
   - telemetry event written;
   - eval result captured;
   - report generated;
   - no unhandled exception;
   - no promotion without evidence.

8. Починить документацию.
   Заменить `scripts/self_evolution_loop.py` на `scripts/internal/self_evolution_loop.py` или вернуть тонкий wrapper по старому пути.

9. Изолировать Qwen OAuth.
   Для Zera runtime нужен явный provider healthcheck и fallback, чтобы ошибка `Qwen OAuth refresh returned invalid JSON` не превращалась в молчание агента.

10. Добавить smoke-test:
    - старт dry-run на 1 цикл;
    - проверка state;
    - проверка telemetry;
    - проверка stop;
    - проверка отсутствия orphan/zombie процессов.

## Текущий статус

- Evolution loop процессы остановлены.
- PID `11920` больше не выполняет полезную работу.
- Дополнительные активные evolution-процессы остановлены.
- Qwen CLI локально отвечает на `qwen -p 'ping'`.
- Qwen creds-файл валиден как JSON, секреты не выводились.
- Рабочее дерево уже было сильно изменено до расследования; в рамках этого отчета изменен только файл отчета.

## Рекомендуемое следующее действие

Не перезапускать бесконечный loop в текущем виде.

Сначала реализовать `evolutionctl` с single-instance lock, schema validation, bounded mode и smoke-test. После этого запускать только один dry-run цикл, затем один live цикл без promotion, и только после отчета оператора включать долгий режим.
