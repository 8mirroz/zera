# Hermes Zera — Telegram AI Agent

AI-агент платформы Antigravity Core, работающий в Telegram.Powered by Anthropic Claude.

## Быстрый старт

1. Скопируй `.env.example` → `.env` и настрой токены:
   ```bash
   cp .env.example .env
   ```

2. Установи зависимости:
   ```bash
   npm install
   ```

3. Отредактируй `SOUL.md` — определи личность, навыки и правила агента.

4. Запусти:
   ```bash
   npm start
   ```

   Или через Docker:
   ```bash
   docker compose up -d
   ```

## Конфигурация

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `ANTHROPIC_API_KEY` | API-ключ Anthropic для Claude |
| `OPENAI_API_KEY` | (опционально) API-ключ OpenAI |
| `AGENT_NAME` | Отображаемое имя бота |
| `MODEL` | Модель Claude (по умолчанию: `claude-sonnet-4-20250514`) |

## Возможности

- История разговоров на каждый чат (последние 20 сообщений)
- SOUL.md — система личности агента
- Hot-reload: `npm run dev`
- Docker-поддержка

## Интеграция в Antigravity Core

Размещение: `repos/telegram/hermes-zera/`
Стандарт: [`WORKSPACE_STANDARD`](../../../configs/rules/WORKSPACE_STANDARD.md) §Placement Matrix
