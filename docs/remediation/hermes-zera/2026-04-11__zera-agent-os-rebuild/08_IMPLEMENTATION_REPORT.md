# 08 Implementation Report

Дата: 2026-04-11 22:11 MSK

## Статус

Частичная реализация завершена. Контролируемый lifecycle для Zera evolution включен, опасный внешний cron остановлен, базовый no-promote smoke test проходит, основные repo gates теперь зеленые.

Полная готовность Agent OS пока не достигнута: Hermes CLI smoke проходит, но gateway adapters, premium routing secrets, optional MCP servers, scout daemon, beta manager и live LLM scoring еще не подтверждены.

## Что реализовано

1. Создана программа ребилда:
   - `README.md`
   - `00_RESEARCH_REPORT.md`
   - `01_LOCAL_FORENSIC_AUDIT.md`
   - `02_TARGET_ARCHITECTURE.md`
   - `03_ULTRAPROMPTS/*`
   - `04_IMPLEMENTATION_RUNBOOK.md`
   - `05_VALIDATION_MATRIX.md`
   - `06_ROLLBACK_PLAN.md`
   - `07_ROLLOUT_PLAN.md`

2. Добавлен управляемый evolution controller:
   - `scripts/zera/zera-evolutionctl.py`
   - `scripts/zera/zera-evolutionctl`
   - `scripts/zera-evolutionctl`
   - installed symlink: `/Users/user/.local/bin/zera-evolutionctl`

3. Контроллер поддерживает:
   - `backup`
   - `install`
   - `sanitize-cron`
   - `dry-run`
   - `start`
   - `status`
   - `stop`
   - `tail`

4. Добавлены safety-механизмы:
   - single PID file
   - state file
   - kill-switch check
   - отказ от unbounded start без `--forever`
   - отказ от forever mode с interval ниже 300 секунд без `--force`
   - stale PID cleanup
   - zombie detection
   - default no-promote mode
   - promotion-enabled start requires explicit `--allow-promote --force`
   - heuristic scoring by default, чтобы не зависать на локальном LLM scoring endpoint

5. Исправлен core loop:
   - corrected repo root discovery in `scripts/internal/self_evolution_loop.py`
   - added `--no-promote`
   - added promotion bypass when gates pass but promotion is disabled
   - added `ZERA_EVO_DISABLE_LLM_SCORING=1` fallback path

6. Исправлена YAML-совместимость:
   - `repos/packages/agent-os/src/agent_os/yaml_compat.py` now delegates real YAML to `yaml.safe_load` before using the lightweight parser.
   - Это сняло ошибку `router.yaml` в `swarmctl doctor`.

7. Нормализовано legacy evolution state:
   - `vault/loops/.evolve-state.json`
   - schema file: `configs/tooling/zera_evolution_state.schema.json`

8. Исправлена hardening validation surface:
   - root symlink `scripts/zera-agent-intelligence.sh` now points to `scripts/zera/zera-agent-intelligence.sh`.

9. Внешний cron обезврежен:
   - backup: `/Users/user/.hermes/profiles/zera/backups/zera-agent-os-rebuild-20260411_220301`
   - disabled job: `Zera Self-Evolution Cycle`

10. MCP profile truth repaired:
   - missing servers removed from active profile server lists until they are actually installed;
   - `T5/C4` route fixed to `data-scraping`;
   - `scripts/test_mcp_profiles.py` now passes.

11. Workflow registry repaired:
   - added 18 missing operational workflow files to the linked workflow bundle;
   - `workflow_model_alias_validator.py --json` now passes with 26 workflow files scanned and 0 missing.

12. Wiki-core paths repaired:
   - created required empty directories with `.gitkeep`;
   - `swarmctl.py wiki doctor --config configs/tooling/wiki_core.yaml` now passes.

13. Trace registry repaired by quarantine, not guesswork:
   - backup: `/Users/user/antigravity-core/logs/agent_traces.backup-20260411_222037.jsonl`
   - quarantined invalid rows: `/Users/user/antigravity-core/logs/agent_traces.invalid-20260411_222037.jsonl`
   - repair report: `/Users/user/antigravity-core/logs/agent_traces.repair-20260411_222037.json`
   - `trace_validator.py --json --allow-legacy` now passes with 21361 valid rows and 0 errors.

## Validation Results

| Gate | Result | Notes |
|---|---:|---|
| `python3 -m py_compile ...` | PASS | Controller, core loop, YAML compat compile cleanly. |
| `scripts/zera-evolutionctl dry-run --cycles 1` | PASS | Dry-run completed with no promotion. |
| `scripts/zera-evolutionctl start --cycles 1 --no-promote` | PASS | One bounded cycle completed. |
| `scripts/zera-evolutionctl start --cycles 1` | PASS | Default start injects `--no-promote`. |
| `scripts/zera-evolutionctl start --cycles 1 --allow-promote` | PASS | Refused without `--force`, as intended. |
| `scripts/zera-evolutionctl status` | PASS | Reports `exited`, `alive: false`, no stale PID. |
| `scripts/zera-evolutionctl tail --lines 30` | PASS | Shows observe/classify/score/design/sandbox/eval/promote/reflect phases. |
| `scripts/zera-evolutionctl stop` | PASS | No running loop; does not overwrite completed `exited` state. |
| Orphan/zombie evolution process check | PASS | No active `self_evolution_loop`, `.evolve-state`, `zera-evolutionctl`, or inline `python3 -c` daemon remains. |
| `qwen -p 'ping'` | PASS | Returned `pong`. |
| `hermes chat -Q -q 'ping'` | PASS | Returned `pong`; session id `20260411_222349_2d9438`. |
| `python3 scripts/validation/check_zera_hardening.py` | PASS | Zera hardening validation OK. |
| `python3 scripts/validation/check_external_cron.py` | PASS with warnings | External cron surfaces still exist outside repo governance, but dangerous self-evolution job is disabled. |
| `python3 scripts/test_mcp_profiles.py` | PASS | Available: 11; routing tests: 8/8. |
| `python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json` | PASS | 26 workflow files scanned, 0 missing, 0 unknown aliases, 0 hardcoded model refs. |
| `python3 repos/packages/agent-os/scripts/trace_validator.py --json --allow-legacy` | PASS | 21361 valid v2 rows, 0 errors after quarantine of 163 invalid rows. |
| `python3 repos/packages/agent-os/scripts/swarmctl.py wiki doctor --config configs/tooling/wiki_core.yaml` | PASS | Required wiki-core paths exist. |
| `python3 repos/packages/agent-os/scripts/swarmctl.py doctor` | PASS with warnings | Warnings: missing `OPENROUTER_API_KEY`, legacy compat files absent until full migration. |

## Критическая оценка

Zera перестал быть неконтролируемым фоновым `python3 -c` процессом. Это важный сдвиг, но это еще не полноценный автономный Agent OS.

Оставшиеся слабые места:

1. Evolution loop пока ближе к управляемому harness, чем к самостоятельному инженеру:
   - `scout_daemon.py` не найден.
   - beta manager не найден.
   - sandbox phase фактически пропускается.
   - promotion корректно заблокирован, но реальный promotion pipeline не доказан.

2. LLM scoring пришлось отключить по умолчанию:
   - первый live smoke завис на локальном scoring endpoint.
   - текущий режим использует heuristic scoring.
   - перед включением `--llm-score` нужны timeout, circuit breaker и проверенный provider.

3. MCP слой теперь валидируется, но capability surface временно урезан:
   - отсутствующие optional servers удалены из активных профилей, чтобы не было ложной готовности.
   - Exa, Obsidian semantic/disk/memory, browser, google-llm, openclaude-executor, lsp-bridge и agent-pool нужно ставить отдельно и возвращать в профили только после smoke tests.
   - Это честнее, но снижает доступный tool surface до следующей фазы.

4. Governance registry больше не красный, но предупреждения остаются:
   - `OPENROUTER_API_KEY` не задан.
   - legacy compat files отсутствуют до полной миграции.
   - агрессивная автономия всё равно должна оставаться в observation/no-promote режиме до проверки Hermes/gateway/model routing.

5. Trace registry очищен через quarantine:
   - 163 невалидные строки сохранены отдельно, а не потеряны.
   - основной trace теперь проходит schema validation.
   - нужно найти writer, который генерировал неполные v2 события.

6. Gateway не считается подтвержденным:
   - Telegram/Slack extras ранее отсутствовали.
   - gateway нужно либо доустановить, либо явно отключить эти adapters до следующего smoke test.
   - `hermes chat -Q -q 'ping'` проходит, но это не доказывает gateway readiness.

## Следующий порядок remediation

1. Harden live LLM scoring:
   - add provider timeout;
   - add circuit breaker;
   - add explicit fallback scoring telemetry;
   - only then allow `zera-evolutionctl start --llm-score`.

2. Shadow-profile Hermes upgrade:
   - update or patch Hermes in a shadow profile first;
   - verify Qwen OAuth refresh path after the User-Agent fix, not just one short chat ping;
   - promote to `zera` only after smoke tests.

3. Restore optional MCP servers one by one:
   - install/smoke each server;
   - return it to active profile only after validation;
   - rerun `python3 scripts/test_mcp_profiles.py`.

4. Find and fix the trace writer:
   - identify which process emitted incomplete v2 events;
   - add schema validation before writes;
   - prevent recurrence.

5. Gateway hardening:
   - install Telegram/Slack extras or explicitly disable adapters;
   - run gateway smoke after Hermes provider path is stable.

6. Keep autonomy bounded:
   - cron may observe frequently;
   - mutation and promotion remain forbidden until all required gates pass and rollback artifacts exist.
