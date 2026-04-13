# Hermes Zera Model Routing Fix — 2026-04-11

## Контекст

Проверялась работа профиля Hermes `zera` после сбоев с моделями. Точка запуска без аргументов:

```bash
scripts/zera/zera-command.sh
```

Она запускает:

```bash
/Users/user/.local/bin/hermes -p zera chat
```

Фактический runtime-конфиг профиля:

```bash
/Users/user/.hermes/profiles/zera/config.yaml
```

## Найденная причина

Primary model был настроен на `opencode-zen/minimax-m2.5-free`. В логах Hermes это нормализовалось в `minimax-m2-5-free`, после чего credential pool помечал provider как недоступный. Дальше включался fallback-каскад на OpenRouter free-модели и OpenCode Zen, но текущие endpoint/model IDs не проходили:

- `opencode-zen/minimax-m2.5-free` — прямой API test вернул `403`.
- `openrouter/google/gemini-2.0-flash-exp:free` — `404`, endpoint отсутствует.
- `openrouter/deepseek/deepseek-v3:free` — `400`, invalid model ID.
- `openrouter/qwen/qwen3.6-plus-preview:free` — `404`, endpoint отсутствует.
- `openrouter/qwen/qwen3.6-plus:free` — `404`, free model deprecated.
- `openrouter/google/gemini-2.0-flash-001` — `402`, insufficient credits.

Дополнительно в profile config были inline secrets в `model.api_key` и `custom_providers[].api_key`, хотя `secret_policy.env_ref_only` и `inline_secret_forbidden` уже включены.

## Исправление

Изменен `/Users/user/.hermes/profiles/zera/config.yaml`:

- primary provider: `gemini`;
- primary model: `gemini-2.5-flash`;
- `fallback_providers`: очищен, чтобы Hermes не уходил в заведомо битый каскад;
- `custom_providers`: очищен, чтобы убрать inline secret и не создавать 401/credential exhaustion для локального custom provider;
- compression summary provider/model переведены на `gemini/gemini-2.5-flash`;
- smart routing cheap model переведен на `gemini/gemini-2.5-flash`;
- quick command `/routing` обновлен под текущий default;
- skin `zera.yaml` скопирован в profile-local `skins/`, чтобы убрать `Skin 'zera' not found`.

Перед изменением создан backup:

```bash
/Users/user/.hermes/profiles/zera/config.yaml.bak-<timestamp>
```

## Валидация

Команды:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
p = Path('/Users/user/.hermes/profiles/zera/config.yaml')
obj = yaml.safe_load(p.read_text())
print(obj['model']['provider'], obj['model']['default'])
print(len(obj.get('fallback_providers') or []))
print(len(obj.get('custom_providers') or []))
PY
```

Результат:

```text
gemini gemini-2.5-flash
0
0
```

Hermes status:

```bash
/Users/user/.local/bin/hermes -p zera status
```

Ключевые строки:

```text
Model:        gemini-2.5-flash
Provider:     Google AI Studio
```

Runtime smoke test:

```bash
/Users/user/.local/bin/hermes -p zera chat -Q --max-turns 1 -q 'Ответь одним словом: ok'
```

Результат:

```text
❤️ ZeRa
ok
```

Interactive entrypoint smoke test:

```bash
printf "/exit\n" | zera
```

Результат:

```text
ZeRa banner rendered
Привет! Я ZeRa ❤️. Твой персональный AI-ассистент в Antigravity.
До встречи! ❤️
exit code 0
```

Hermes doctor:

```bash
/Users/user/.local/bin/hermes -p zera doctor
```

Ключевой результат:

```text
Profiles
✓ zera: gemini-2.5-flash
```

## Остаточные предупреждения

Не исправлялись в рамках model-routing fix:

- `Config version outdated (v13 → v14)` — требуется отдельный `hermes doctor --fix` или ручная миграция.
- `Anthropic API (invalid API key)` — ключ в env недействителен.
- Optional dependencies: `docker`, `agent-browser`, `image_gen`, `messaging`.
- MCP server пишет служебную строку в stdout, из-за чего Hermes логирует `Failed to parse JSONRPC message`; это отдельный MCP hygiene issue, не блокирует текущий Zera chat.

## Итог

Сбой модели воспроизведен, причина подтверждена прямыми provider tests и логами fallback. Профиль `zera` переведен на рабочий `gemini-2.5-flash`, сломанный fallback-каскад отключен, inline secrets из runtime config убраны. Smoke test Zera chat проходит.

## Follow-up fix: banner crash

После model-routing fix интерактивный запуск `zera` падал до prompt:

```text
NameError: name 'sys' is not defined
```

Причина: `/Users/user/.local/share/hermes-agent/hermes_cli/banner.py` использовал `sys.stdout.write(...)` в `build_welcome_banner`, но не импортировал `sys`.

Исправление:

```python
import sys
```

добавлен рядом с остальными imports в `/Users/user/.local/share/hermes-agent/hermes_cli/banner.py`.

Проверки:

```bash
python3 -m py_compile /Users/user/.local/share/hermes-agent/hermes_cli/banner.py
/Users/user/.local/bin/hermes -p zera chat --max-turns 1 -q 'Ответь одним словом: ok'
printf "/exit\n" | zera
```

Результат: `NameError` исчез, banner строится, `zera` стартует и корректно выходит по `/exit`.
