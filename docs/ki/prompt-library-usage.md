---
title: Prompt Library Usage
description: Guide for agents on how to utilize the centralized prompt library in configs/prompts/
type: knowledge_item
status: validated
created_at: 2026-04-14
---

# 🎭 Prompt Library Usage

В системе Antigravity внедрена централизованная библиотека промтов для обеспечения высокого качества и детерминизма работы агентов.

## 📍 Локация
[configs/prompts/](file:///Users/user/zera/configs/prompts/)

## 🛠️ Как это работает
Каждый агент перед запуском сабагента или выполнением сложной задачи (Tier C3+) обязан проверить наличие подходящего промта в [manifest.yaml](file:///Users/user/zera/configs/prompts/manifest.yaml).

### Алгоритм выбора:
1.  **Поиск по тегам**: Ищите промт по `role` (напр., `architect`) или `task_type` (напр., `research`).
2.  **Проверка тира**: Убедитесь, что промт подходит под текущий Tier сложности (C1-C5).
3.  **Загрузка шаблона**: Считайте контент из указанного в манифесте пути.
4.  **Context Injection**: Замените плейсхолдеры (напр., `{{goal}}`, `{{files}}`) актуальными данными из текущей сессии.

## 🌟 Рекомендованные промты
-   `system.architect.v1` — для задач проектирования и управления техдолгом.
-   `tasks.research.v1` — для задач глубокого исследования.

## ➕ Добавление новых промтов
При создании нового "ультра-промта":
1.  Разместите его в соответствующей подпапке (system/tasks/templates).
2.  Зарегистрируйте в `manifest.yaml` с подробным описанием.
3.  Обновите это KI, если промт является критически важным.

---
*Связано с: AGENTS.md, router.yaml*
