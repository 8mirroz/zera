---
name: memfree-engine
description: Hybrid AI Search Engine (Internet + Project Context + Docs)
---

# MemFree Engine Skill (No-Key Adaptive Mode)

## Scope
Используйте этот навык для выполнения глубокого "Гибридного поиска", который объединяет данные из интернета (DuckDuckGo/SearXNG) и локальных проиндексированных файлов (Local Vector Store). 

## Core principles
1. **Local-First Architecture**: В текущей конфигурации система работает в режиме **No-Key**. Поиск в вебе выполняется через бесплатные прокси, а LLM — через локальные эндпоинты (Ollama/AG-Proxy).
2. **Hybrid Retrieval**: Сначала проверяется локальный контекст (проекта/документации), затем выполняется поиск в вебе.
2. **Context Enrichment**: Все найденные данные автоматически форматируются под стандарты Antigravity (markdown, таблицы, цитаты).
3. **Task-Aware**: Поиск адаптируется под текущий шаг воркфлоу (например, поиск ошибок, архитектурный анализ или поиск библиотек).

## Engine Integration
Primary path:
- `repos/memfree`

Основные компоненты:
- **Frontend/API**: `repos/memfree/frontend` (Next.js)
- **Vector Service**: `repos/memfree/vector` (Headless Vector DB)

## Run commands
Инстанс MemFree должен быть запущен (Docker или локально):

```bash
# Запуск бэкенда вектора
cd repos/memfree/vector
bun run install
bun run dev

# Запуск фронтенда (API портал)
cd repos/memfree/frontend
pnpm install
pnpm dev
```

## Search API (Internal usage)
Агенты могут обращаться к эндпоинтам:
- `POST /api/search` — гибридный поиск.
- `POST /api/index` — индексация новых документов/URL.

## Creative Automation (Antigravity Exclusive)
1. **Auto-KI Sync**: Результаты поиска через MemFree могут быть напрямую сохранены в `docs/ki/` с помощью воркфлоу `/memfree`.
2. **Project Indexing**: Вы можете проиндексировать этот репозиторий в MemFree для ответов на сложные вопросы по структуре v5:
   ```bash
   # Пример команды индексации (через MemFree CLI/API)
   curl -X POST http://localhost:3000/api/index -d '{"path": "./docs"}'
   ```

## Quality gate
При использовании MemFree для исследований:
- Проверять актуальность источников (не старше 1 года для библиотек).
- Сопоставлять найденные в вебе решения с существующими `configs/rules/`.
- Выделять "trap" и "risk" в результатах поиска.
