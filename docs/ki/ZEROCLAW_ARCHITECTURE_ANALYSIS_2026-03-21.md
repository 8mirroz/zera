# Анализ архитектуры ZeroClaw

**Дата:** 21 марта 2026  
**Статус:** ⚠️ Требует решения  
**Автор:** Agent OS Architecture Team

---

## 1. Что такое ZeroClaw?

**ZeroClaw** — это runtime-провайдер для Agent OS, обеспечивающий выполнение задач через stdio-адаптер. Он работает как мост между маршрутизатором задач и фактическим исполнителем (LLM-агентом).

### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZeroClaw Runtime Stack                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Input (Telegram/CLI)                                      │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────┐                                        │
│  │  Telegram Bot       │  aiogram 3.x                           │
│  │  (sandbox/...)      │  polling/webhook mode                  │
│  └────────┬────────────┘                                        │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────┐                                        │
│  │  Runtime Bridge     │  runtime_bridge.py                     │
│  │  (sandbox/...)      │  rate limit, chat ACL, admin cmds      │
│  └────────┬────────────┘                                        │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────┐                                        │
│  │  ZeroClaw Provider  │  zeroclaw.py                           │
│  │  (agent_os/)        │  profiles, autonomy, approval          │
│  └────────┬────────────┘                                        │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────┐                                        │
│  │  Exec Adapter       │  zeroclaw_exec_adapter.py              │
│  │  (scripts/)         │  stdio JSON contract                   │
│  └────────┬────────────┘                                        │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────┐                                        │
│  │  ZeroClaw CLI (opt) │  native binary (NOT INSTALLED)         │
│  │  (ops/zeroclaw/)    │  ZEROCLAW_USE_NATIVE_BIN=false         │
│  └─────────────────────┘                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Как это работает

### 2.1 Поток выполнения задачи

1. **Пользователь** отправляет сообщение в Telegram бот
2. **Telegram Bot** (`sandbox/template-telegram/bot/main.py`) принимает сообщение
3. **Runtime Bridge** (`runtime_bridge.py`) проверяет:
   - ACL чата (`TG_ALLOWED_CHAT_IDS`)
   - Rate limiting (`TG_RATE_LIMIT_SECONDS`)
   - Админские команды (`TG_ADMIN_CHAT_IDS`)
4. **ZeroClaw Provider** (`zeroclaw.py`) загружает профиль из `zeroclaw_profiles.json`:
   - `autonomy_mode` — режим автономности
   - `approval_policy` — политика одобрения
   - `background_profile` — фоновые задачи
   - `execution_mode` — режим выполнения (stdio_json / health_probe)
5. **Exec Adapter** (`zeroclaw_exec_adapter.py`) выполняет задачу:
   - Читает stdin JSON payload
   - Генерирует proposals (инициативы)
   - Возвращает structured runtime contract
6. **Результат** возвращается через Telegram бот

### 2.2 Режимы выполнения

| Режим | Описание | Статус |
|-------|----------|--------|
| `stdio_json` | Python адаптер читает JSON из stdin | ✅ Активен |
| `zeroclaw_native` | Нативный бинарник ZeroClaw | ❌ Не установлен |
| `health_probe` | Проверка здоровья без выполнения | ✅ По умолчанию |

### 2.3 Профили выполнения

| Профиль | Канал | Автономность | Бюджет | Timeout |
|---------|-------|--------------|--------|---------|
| `zera-telegram-prod` | Telegram | bounded_initiative | $0.02 | 20с |
| `zera-edge-local` | Edge (local dev) | bounded_initiative | $0.02 | 15с |
| `generic-c1-c2-worker` | CLI | approval_only | $0.01 | 10с |

---

## 3. Найденные проблемы

### 🔴 Критические

#### 3.1 ZeroClaw CLI бинарник НЕ УСТАНОВЛЕН

```
ZEROCLAW_USE_NATIVE_BIN=false
```

**Что это значит:**
- Все профили имеют `native_command` с `__ZEROCLAW_BIN__` placeholder
- Этот placeholder никогда не резолвится в реальный бинарник
- Вместо native ZeroClaw используется **Python адаптер** (`zeroclaw_exec_adapter.py`)
- Адаптер — это **mock**, который возвращает заглушку:

```python
response_text = (
    f"Zera runtime handled the request in {mode} mode. "
    "I may be wrong on details, so let's verify external assumptions..."
)
```

**Вывод:** ZeroClaw **не выполняет реальную работу** — это заглушка с красивой обёрткой.

#### 3.2 Telegram бот в sandbox/

```
ops/zeroclaw/docker-compose.yaml:
  command: python sandbox/template-telegram/bot/main.py
```

**Проблема:**
- Бот запускается из `sandbox/` — экспериментальной директории
- По правилам `WORKSPACE_STANDARD.md`, код из `sandbox/` не должен попадать в production
- Это нарушение архитектурных правил проекта

#### 3.3 systemd unit с абсолютными путями

```ini
EnvironmentFile=/Users/user/antigravity-core/ops/zeroclaw/.env
ExecStart=/usr/bin/env python3 /Users/user/antigravity-core/sandbox/template-telegram/bot/main.py
```

**Проблемы:**
- Пути захардкожены для macOS (`/Users/user/...`)
- На Linux сервере эти пути не существуют
- Unit файлы не будут работать на продакшен сервере

#### 3.4 Нет реального LLM вызова

**Exec Adapter не вызывает LLM:**
```python
def build_response(payload, profile):
    # ... генерирует статический ответ без вызова API
    return {
        "status": "completed",
        "response_text": "Zera runtime handled the request...",
        "meta": { ... }
    }
```

**Это означает:**
- Нет real-time генерации ответов
- Нет связи с OpenRouter/Google/Anthropic
- Все ответы — заглушки

### ⚠️ Предупреждения

#### 3.5 Docker Compose монтирует весь репозиторий

```yaml
volumes:
  - ../..:/workspace
```

**Риск:** Контейнер имеет доступ ко всему репозиторию, включая `.env` файлы и секреты.

#### 3.6 Нет проверки здоровья MCP серверов

ZeroClaw Provider имеет `_health_probe()` метод, но:
- Он проверяет только наличие бинарника
- Не проверяет доступность MCP серверов
- Не проверяет connectivity к LLM провайдерам

#### 3.7 Нет retry логики для внешних вызовов

```python
proc = subprocess.run(
    args,
    timeout=max(1, timeout_seconds),
    check=False,  # Не выбрасывает exception при error exit code
)
```

Нет retry, exponential backoff, circuit breaker для subprocess вызовов.

#### 3.8 Memory updates — заглушка

```python
"memory_updates": [
    {
        "key": f"run:{payload.get('run_id')}",
        "payload": {"objective": objective, "mode": mode, "profile": profile},
        "options": {"memory_class": "working_memory", "ttl_seconds": 86400, "confidence": 0.82},
    }
]
```

`confidence: 0.82` — магическое число, не основанное на реальной оценке.

---

## 4. Анализ кодовой базы

### Файлы ZeroClaw

| Файл | Строк | Назначение | Качество |
|------|-------|------------|----------|
| `zeroclaw.py` | 613 | Runtime provider | ⭐⭐⭐⭐ Хороший |
| `zeroclaw_exec_adapter.py` | 247 | Stdio адаптер | ⭐⭐ Заглушка |
| `zeroclaw_profiles.json` | 131 | Профили | ⭐⭐⭐ Хороший |
| `runtime_bridge.py` | 243 | Telegram bridge | ⭐⭐⭐ Хороший |
| `main.py` (bot) | 279 | Telegram bot | ⭐⭐⭐ Хороший |
| `docker-compose.yaml` | 26 | Deploy | ⭐⭐ Sandbox |
| `*.service` | 2x | systemd | ⭐⭐ Хардкод |
| `Caddyfile` | 4 | Proxy | ⭐⭐ Шаблон |
| `nginx.conf` | — | Proxy | ⭐⭐ Шаблон |

### Тестовое покрытие

| Тест | Строк | Покрытие |
|------|-------|----------|
| `test_zeroclaw_exec_adapter.py` | 58 | 2 теста |
| `test_agent_runtime_dispatch.py` | 3 теста | Integration |

**Итого:** 5 тестов — недостаточно для production runtime.

---

## 5. Рекомендации

### Вариант A: Удалить ZeroClaw 🗑️

**Аргументы ЗА:**
1. Не приносит реальной ценности — заглушки вместо LLM
2. Усложняет архитектуру — 9 файлов, 1500+ строк
3. Нарушает правила проекта — sandbox в production
4. Не используется активно — traces показывают только тестовые запуски
5. Нет real LLM integration — главный функционал отсутствует

**Что удалить:**
```
ops/zeroclaw/              # Весь каталог
configs/tooling/zeroclaw_profiles.json
repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py
repos/packages/agent-os/src/agent_os/runtime_providers/zeroclaw.py
sandbox/template-telegram/ # Перенести в repos/ или удалить
tests/test_zeroclaw_exec_adapter.py
```

**Что сохранить:**
- Концепцию профилей автономности → перенести в `agent_os/orchestration/`
- Runtime Bridge ACL → перенести в `agent_os/security/`
- Stop controller, Approval engine → уже в `agent_os/`

---

### Вариант B: Доработать до production 🛠️

**Если ZeroClaw нужен:**

#### 5.1 Интегрировать реальный LLM вызов

```python
# zeroclaw_exec_adapter.py
import httpx

async def call_llM(objective: str, profile: dict) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": profile["model"],
                "messages": [{"role": "user", "content": objective}],
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

#### 5.2 Переместить из sandbox/

```bash
# Правильное размещение
mv sandbox/template-telegram/ repos/apps/zera-telegram/
```

#### 5.3 Исправить systemd unit

```ini
[Service]
EnvironmentFile=/opt/antigravity/zeroclaw/.env
ExecStart=/usr/bin/python3 /opt/antigravity/repos/apps/zera-telegram/bot/main.py
```

#### 5.4 Добавить health checks

```python
def health_check() -> dict:
    return {
        "zeroclaw_bin": check_binary(),
        "mcp_servers": check_mcp_connectivity(),
        "llm_provider": check_openrouter_health(),
        "telegram_bot": check_telegram_webhook(),
    }
```

#### 5.5 Увеличить тестовое покрытие

Минимум 15 тестов:
- Unit тесты для exec adapter
- Integration тесты с моком LLM API
- E2E тесты Telegram бота
- Тесты failover и retry логики

---

### Вариант C: Заменить на Agent OS Python runtime 🔄

**Текущее состояние:**
```python
# runtime_registry.py
_DEFAULT_RUNTIME_CONFIG = {
    "default_provider": "agent_os_python",  # Уже default!
    "providers": {
        "agent_os_python": {"enabled": True},
        "zeroclaw": {"enabled": False},     # Отключён!
    }
}
```

**ZeroClaw уже отключён по умолчанию!**

**Рекомендация:**
1. Удалить ZeroClaw provider полностью
2. Усилить `agent_os_python` provider:
   - Добавить MCP интеграцию
   - Добавить Telegram ingress
   - Добавить autonomy profiles
3. Консолидировать в единый runtime

---

## 6. Сравнение вариантов

| Критерий | A: Удалить | B: Доработать | C: Заменить |
|----------|------------|---------------|-------------|
| **Сложность** | Низкая | Высокая | Средняя |
| **Время** | 2 часа | 2 недели | 1 неделя |
| **Риск** | Низкий | Средний | Средний |
| **Ценность** | Убирает мёртвый код | Реальный функционал | Консолидация |
| **Рекомендация** | ✅ **ДА** | ⚠️ Если нужен | ⭐ **Лучший** |

---

## 7. Итоговая рекомендация

### 🎯 Рекомендуемый подход: Вариант C (Заменить)

**Причины:**
1. ZeroClaw **не приносит реальной ценности** — заглушки вместо LLM
2. **Дублирует функционал** `agent_os_python` runtime
3. **Усложняет поддержку** — ещё один runtime provider
4. **Архитектурно несовместим** — sandbox в production
5. **Не используется** — traces показывают только тесты

### План действий

```
Неделя 1:
├── Перенести Telegram бот из sandbox/ в repos/apps/
├── Интегрировать бот с agent_os_python runtime
├── Добавить LLM вызов в runtime_bridge.py
└── Написать 10+ тестов

Неделя 2:
├── Удалить ZeroClaw provider
├── Удалить zeroclaw_profiles.json
├── Удалить ops/zeroclaw/
├── Обновить документацию
└── Запустить smoke tests
```

### Миграция

```bash
# 1. Перенос бота
mkdir -p repos/apps/zera-telegram
mv sandbox/template-telegram/* repos/apps/zera-telegram/

# 2. Интеграция с Agent OS
# Добавить вызов LLM в runtime_bridge.py

# 3. Удаление ZeroClaw
rm -rf ops/zeroclaw/
rm configs/tooling/zeroclaw_profiles.json
rm repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py
rm repos/packages/agent-os/src/agent_os/runtime_providers/zeroclaw.py
rm tests/test_zeroclaw_exec_adapter.py

# 4. Обновить registry
# Удалить zeroclaw из runtime_providers.json

# 5. Проверить
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
```

---

## 8. Заключение

**ZeroClaw — это мёртвый код с красивой обёрткой.**

Он имеет:
- ✅ Хорошо структурированные профили
- ✅ Продуманную систему автономности
- ✅ Интеграцию с approval engine
- ✅ Stop controller и loop guard
- ✅ Persona evaluation

Но **не имеет главного**:
- ❌ Реального вызова LLM
- ❌ Рабочего native binary
- ❌ Production-ready деплоя
- ❌ Достаточного тестового покрытия

**Рекомендация:** Удалить ZeroClaw, перенести ценные концепции в `agent_os_python`, упростить архитектуру.

---

**Статус документа:** Черновик  
**Следующий шаг:** Обсудить с командой и выбрать вариант
