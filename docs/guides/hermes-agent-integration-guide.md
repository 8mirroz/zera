# ZeRa Agent — Antigravity Core Integration Guide

## Что установлено и настроено

### Версия и статус
| Компонент | Версия | Статус |
|-----------|--------|--------|
| ZeRa Agent | v0.7.0 | ✅ Установлен |
| Python | 3.12.12 (uv) | ✅ |
| Модель | `openrouter/qwen/qwen3.6-plus-preview:free` | ✅ (из Antigravity Core) |
| Провайдер | OpenRouter | ✅ (ключ из .env Antigravity) |
| Профиль | `antigravity` | ✅ (изолированный) |
| Workspace | `/Users/user/antigravity-core` | ✅ |
| MCP серверы | filesystem, context7, sequential-thinking | ⏳ требуют npx |
| Навыки | 32 из Antigravity Core | ✅ синхронизированы |

---

## Доступные варианты Dashboard/UI

### Вариант 1: CLI Dashboard (готово ✅)
```bash
bash scripts/hermes-dashboard.sh
```
Интерактивное меню: статус, чат, синхронизация навыков, диагностика, логи.

### Вариант 2: Open WebUI (требует Docker)
ZeRa поддерживает подключение Open WebUI через API сервер:
```bash
# 1. Запустить ZeRa API сервер
hermes config set api_server.enabled true
hermes config set api_server_port 8000

# 2. Запустить Open WebUI (требует Docker)
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8000 \
  ghcr.io/open-webui/open-webui:main
```
**Плюсы:** Полноценный веб-интерфейс, история чатов, управление пользователями.
**Минусы:** Требует Docker (не установлен).

### Вариант 3: LobeChat / LibreChat / ChatBox
Любой OpenAI-совместимый фронтенд можно подключить к ZeRa API:
```bash
# ZeRa работает как OpenAI-compatible бэкенд
# URL: http://localhost:8000/v1
# Key: OPENROUTER_API_KEY из .env
```

### Вариант 4: Telegram/Discord Gateway (готово к настройке)
```bash
hermes gateway setup
# Требуется: BOT_TOKEN и ALLOWED_USERS в .env
hermes gateway start
```

### Вариант 5: Desktop Dashboard (community)
Проект на Reddit: полноценный десктопный дашборд с KPI, статусами агентов.
Можно клонировать и адаптировать.

---

## Быстрый старт

### 1. Проверить статус
```bash
hermes status        # общий статус
hermes doctor        # полная диагностика
hermes tools list    # доступные инструменты
```

### 2. Задать вопрос
```bash
hermes chat -q "Опиши структуру проекта antigravity-core"
```

### 3. Полная сессия
```bash
hermes                    # интерактивный чат
hermes -p antigravity     # через профиль Antigravity Core
```

### 4. С навыками Antigravity Core
```bash
hermes -s systematic-debugging -q "Почему падает тест test_routing.py?"
hermes -s verification-before-completion -q "Проверь configs/orchestrator/router.yaml"
```

---

## Синхронизация с Antigravity Core

### Автоматическая синхронизация
```bash
bash scripts/hermes-sync-config.sh       # полный sync
bash scripts/hermes-sync-config.sh --dry-run  # посмотреть что изменится
```

**Что синхронизируется:**
- API ключи из `.env` → `~/.hermes/.env`
- Навыки из `configs/skills/` → `~/.hermes/skills/antigravity/`
- MCP серверы из `mcp_profiles.json`
- Workspace директория

### Ручная синхронизация навыков
```bash
# При добавлении нового навыка в Antigravity Core:
cp configs/skills/superpowers/new-skill/SKILL.md ~/.hermes/skills/antigravity/
hermes skills list   # проверить
```

---

## Управление через Dashboard

```
┌─── ZeRa Agent Dashboard ───┐
│                               │
│  1) Full Status               — полный статус системы
│  2) Quick Chat                — быстрый вопрос
│  3) Full Session              — полная интерактивная сессия
│  4) Sync Skills               — синхронизировать навыки
│  5) Run Diagnostics           — диагностика (doctor)
│  6) Usage Insights            — аналитика использования
│  7) Test MCP Servers          — тест MCP серверов
│  8) Edit Config               — редактировать config.yaml
│  9) View Logs                 — просмотр логов
│  0) Exit                      — выход
└───────────────────────────────┘
```

---

## Доступные инструменты ZeRa

| Инструмент | Статус | Описание |
|------------|--------|----------|
| `terminal` | ✅ | Выполнение команд в терминале |
| `file` | ✅ | Чтение/запись файлов в workspace |
| `code_execution` | ✅ | Запуск Python/Node кода |
| `web` | ⚠️ | Поиск (требует EXA/TAVILY/FIRECRAWL) |
| `browser` | ✅ | Автоматизация браузера |
| `vision` | ✅ | Анализ изображений |
| `image_gen` | ⚠️ | Генерация изображений (требует FAL_KEY) |
| `tts` | ✅ | Синтез речи |
| `skills` | ✅ | Система навыков |
| `todo` | ✅ | Планирование задач |
| `memory` | ✅ | Долговременная память |
| `session_search` | ✅ | Поиск по прошлым сессиям |
| `clarify` | ✅ | Уточняющие вопросы |
| `delegation` | ✅ | Делегирование задач |
| `cronjob` | ✅ | Планировщик задач |
| `homeassistant` | ✅ | Умный дом |

---

## Полезные команды

```bash
# Управление сессиями
hermes sessions list        # список сессий
hermes sessions browse      # интерактивный выбор
hermes sessions rename ID "новое имя"
hermes sessions export sessions.jsonl
hermes sessions prune       # удалить старые

# Управление навыками
hermes skills list          # список навыков
hermes skills search "debug"

# Логи
hermes logs                 # последние 50 строк
hermes logs -f              # в реальном времени
hermes logs errors          # только ошибки
hermes logs --since 1h      # за последний час

# Конфигурация
hermes config edit          # открыть config.yaml
hermes config set model.default "openrouter/qwen/qwen3-coder-next"
hermes config migrate       # обновить конфиг

# Профили
hermes profile list         # список профилей
hermes profile use default  # переключить профиль
hermes profile show antigravity

# MCP
hermes mcp list             # список MCP серверов
hermes mcp test filesystem  # тест конкретного сервера

# Обновление
hermes update               # обновить до последней версии
hermes version              # текущая версия
```

---

## Интеграция в рабочие процессы Antigravity Core

### Как ZeRa дополняет Antigravity Core

| Сценарий | Antigravity Core | ZeRa Agent |
|----------|-----------------|--------------|
| C1-C2 задачи | ✅ Через CLI tools | ✅ Интерактивный чат |
| C3-C4 задачи | ✅ Swarm режим | ✅ С навыками и MCP |
| Code review | ✅ Reviewer модель | ✅ vision + terminal + file |
| Исследование | ✅ Research profile | ✅ web + memory + session_search |
| Быстрые вопросы | ❌ | ✅ Интерактивный чат |
| Мониторинг | ✅ Status/Doctor | ✅ Insights + Logs |

### Рекомендуемые сценарии использования

1. **Быстрая диагностика:** `hermes chat -q "Что нового в проекте?"`
2. **Анализ кода:** `hermes -s systematic-debugging -q "Разбери error-healing.md"`
3. **Исследование:** `hermes -q "Найди все workflow связанные с swarm"`
4. **Планирование:** `hermes -s writing-plans -q "Создай план интеграции lsp-bridge"`

---

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `command not found` | `export PATH="$HOME/.local/bin:$PATH"` в `.zshrc` |
| API key не работает | Проверить `cat ~/.hermes/.env \| grep OPENROUTER` |
| MCP сервер не подключается | `hermes mcp test <name>` |
| Модель не отвечает | `hermes model` — выбрать другую |
| Нет навыков | `bash scripts/hermes-sync-config.sh` |

---

*Документ создан: 2026-04-08*
*ZeRa v0.7.0 + Antigravity Core v4.1*
