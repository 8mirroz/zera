# Миграция ZeroClaw → Agent OS Python

**Дата:** 21 марта 2026  
**Статус:** ✅ ЗАВЕРШЕНО  
**Автор:** Agent OS Architecture Team

---

## Резюме миграции

ZeroClaw runtime provider удалён. Telegram бот перемещён из `sandbox/` в production директорию `repos/apps/zera-telegram/`. Интеграция с реальным LLM (OpenRouter) добавлена.

---

## Что было сделано

### 1. Создан production Telegram бот

**Новая структура:** `repos/apps/zera-telegram/`

```
repos/apps/zera-telegram/
├── README.md                    # Документация
├── .env.example                 # Шаблон конфигурации
├── requirements.txt             # Зависимости
├── docker-compose.yaml          # Docker deployment
├── bot/
│   ├── __init__.py
│   ├── __main__.py              # Entry point (async main)
│   ├── main.py                  # Backwards compat (python bot/main.py)
│   ├── config.py                # Config management (TelegramConfig, LLMConfig)
│   └── runtime_bridge.py        # LLM integration + governance commands
└── tests/
    └── test_bot.py              # 15 тестов (100% pass)
```

### 2. Добавлена LLM интеграция

**Ключевое изменение:** `runtime_bridge.py` теперь вызывает реальный LLM API:

```python
async def call_llm(message: str, system_prompt: str | None = None) -> str:
    """Call OpenRouter API and return response text."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages}
        )
        return response.json()["choices"][0]["message"]["content"]
```

**Fallback:** Если LLM не настроен, используется `swarmctl run` через agent_os_python runtime.

### 3. Удалённые файлы

| Файл/Директория | Причина |
|-----------------|---------|
| `ops/zeroclaw/` | Весь каталог (9 файлов) |
| `configs/tooling/zeroclaw_profiles.json` | Не используется |
| `repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py` | Заглушка |
| `repos/packages/agent-os/src/agent_os/runtime_providers/zeroclaw.py` | Удалён provider |
| `repos/packages/agent-os/tests/test_zeroclaw_exec_adapter.py` | Тесты удалены |
| `sandbox/template-telegram/` | Перемещён в repos/apps/ |

### 4. Обновлённые файлы

| Файл | Изменение |
|------|-----------|
| `runtime_registry.py` | Удалён ZeroClaw provider, обновлён fallback chain |
| `runtime_providers/__init__.py` | Удалён импорт ZeroClawRuntimeProvider |

---

## Сравнение: до и после

### До (ZeroClaw)

```
User → Telegram Bot → runtime_bridge → swarmctl run → zeroclaw_exec_adapter → STUB RESPONSE
                                                                           "Zera runtime handled..."
```

**Проблемы:**
- ❌ Нет реального LLM вызова
- ❌ Бот в sandbox/ (не production)
- ❌ 1500+ строк мёртвого кода
- ❌ Хардкод пути macOS в systemd unit

### После (Agent OS Python + LLM)

```
User → Telegram Bot → runtime_bridge → OpenRouter API → REAL RESPONSE
                                  ↓ (fallback)
                              swarmctl run → agent_os_python
```

**Преимущества:**
- ✅ Реальные LLM ответы через OpenRouter
- ✅ Production-ready структура
- ✅ 15 тестов (100% pass)
- ✅ Docker + systemd deployment
- ✅ Конфигурация через env vars
- ✅ Health checks
- ✅ Fallback на swarmctl если LLM недоступен

---

## Конфигурация

### Required env vars

```bash
# Telegram
TG_BOT_TOKEN=your_bot_token
TG_ALLOWED_CHAT_IDS=12345,67890

# LLM (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=deepseek/deepseek-v3:free  # default
```

### Optional env vars

```bash
TG_BOT_MODE=polling              # polling | webhook
TG_RATE_LIMIT_SECONDS=3
TG_ADMIN_CHAT_IDS=
TG_WEBHOOK_URL=
TG_WEBHOOK_SECRET=
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7
TG_RUNTIME_TIMEOUT_SECONDS=60
```

---

## Deployment

### Docker

```bash
cd repos/apps/zera-telegram
cp .env.example .env
# Edit .env
docker compose up -d
```

### systemd

```bash
# Create /etc/systemd/system/zera-telegram.service
[Unit]
Description=Zera Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/antigravity/repos/apps/zera-telegram
EnvironmentFile=/opt/antigravity/repos/apps/zera-telegram/.env
ExecStart=/usr/bin/python3 bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable --now zera-telegram.service
```

### Polling (development)

```bash
cd repos/apps/zera-telegram
pip install -r requirements.txt
export TG_BOT_TOKEN=your_token
export TG_ALLOWED_CHAT_IDS=your_chat_id
export OPENROUTER_API_KEY=your_key
python bot/main.py
```

---

## Тестирование

```bash
cd repos/apps/zera-telegram
python3 -m pytest tests/test_bot.py -v
```

**Результат:**
```
15 passed in 0.11s

Test Categories:
- TelegramConfig (5 tests)
- LLMConfig (3 tests)
- Chat ACL (2 tests)
- Rate Limiting (2 tests)
- Response Chunks (3 tests)
```

---

## System Health

```bash
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
```

**Результат:**
```
OK: doctor passed
```

ZeroClaw references полностью удалены из кодовой базы.

---

## Миграция для существующих деплоев

Если у вас работает `ops/zeroclaw/`:

1. **Остановите старые сервисы:**
   ```bash
   sudo systemctl stop zeroclaw-zera.service
   sudo systemctl stop zera-telegram-bot.service
   sudo systemctl disable zeroclaw-zera.service
   sudo systemctl disable zera-telegram-bot.service
   ```

2. **Удалите старые файлы:**
   ```bash
   sudo rm /etc/systemd/system/zeroclaw-zera.service
   sudo rm /etc/systemd/system/zera-telegram-bot.service
   sudo rm -rf /path/to/ops/zeroclaw/
   ```

3. **Разверните новый бот:**
   ```bash
   cd repos/apps/zera-telegram
   cp .env.example .env
   # Настройте .env
   docker compose up -d
   # ИЛИ
   sudo systemctl enable --now zera-telegram.service
   ```

---

## Удалённые функции

Следующие функции были в ZeroClaw, но **не были функциональны**:

| Функция | Статус в ZeroClaw | Новый статус |
|---------|-------------------|--------------|
| Native binary execution | ❌ Placeholder `__ZEROCLAW_BIN__` | ✅ LLM API calls |
| Stdio JSON contract | ❌ Stub responses | ✅ Real responses |
| Health probe | ✅ Работал | ✅ Health endpoint `/healthz` |
| Background daemon | ✅ Работал | ✅ Через swarmctl |

---

## Будущие улучшения

1. **Streaming responses:** Поддержка streaming от OpenRouter для длинных ответов
2. **Multi-model routing:** Выбор модели на основе сложности задачи
3. **Memory integration:** Прямая интеграция с BM25 memory для контекста
4. **MCP tools:** Добавление MCP tool calls в Telegram бот
5. **Mini App:** Telegram Mini App для управления задачами

---

## Changelog

### 2026-03-21

- ✅ Создан `repos/apps/zera-telegram/` (production)
- ✅ Добавлена LLM интеграция (OpenRouter)
- ✅ 15 тестов (100% pass)
- ✅ Удалён `ops/zeroclaw/` (9 файлов)
- ✅ Удалён `zeroclaw.py` runtime provider
- ✅ Удалён `zeroclaw_exec_adapter.py` (stub)
- ✅ Удалён `zeroclaw_profiles.json`
- ✅ Удалён `sandbox/template-telegram/`
- ✅ Обновлён `runtime_registry.py`
- ✅ Swarmctl doctor: OK

---

**Статус миграции:** ✅ ЗАВЕРШЕНА  
**Время выполнения:** ~2 часа  
**Влияние на систему:** Положительное (упрощение + реальная функциональность)
