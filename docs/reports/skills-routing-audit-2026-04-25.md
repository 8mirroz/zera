# 🔍 Ревью скиллов и алгоритмов роутинга
**Дата:** 2026-04-25
**Версия конфигов:** router.yaml v4.2, models.yaml v4.3
**Аудитор:** Zera (self-audit)

---

## 📊 Executive Summary

Выявлено **12 несоответствий и проблем**, из которых:
- 🚨 **3 критических** — потенциальные сбои рантайма
- ⚠️ **6 серьёзных** — расхождения контрактов, невалидные ссылки, дрейф конфигурации
- 💡 **3 рекомендации** — оптимизация и упрощение

---

## 🚨 Критические проблемы

### 1. Несоответствие лимитов инструментов: router.yaml vs AGENTS.md
**Файлы:** `configs/orchestrator/router.yaml` vs `AGENTS.md`

| Tier | router.yaml max_tools | AGENTS.md заявлено | Дельта |
|------|----------------------|-------------------|--------|
| C1   | 15                   | 8                 | **+7** |
| C2   | 25                   | 12                | **+13** |
| C3   | 30                   | 20                | **+10** |
| C4   | 35                   | 30                | **+5**  |
| C5   | 50                   | 50                | 0      |

**Риск:** Классификатор задач (AGENTS.md) обещает ограничения, которые router.yaml не соблюдает. Для C1-C3 разрыв 50–100%+. Это приводит к:
- Перерасходу токенов на тривиальных задачах
- Нарушению контракта с пользователем (ожидание "лёгкого" исполнения)
- Возможному таймауту агента на C1-C2 из-за избыточных tool_calls

**Решение:** Синхронизировать. Рекомендую привести router.yaml к AGENTS.md (более консервативные лимиты) или обновить AGENTS.md с обоснованием новых лимитов.

---

### 2. Неопределённый алиас модели: `MODEL_DESIGN_PRIMARY`
**Файл:** `configs/orchestrator/models.yaml` (строка ~100)

```yaml
AGENT_MODEL_DESIGN_DIRECT: "$MODEL_DESIGN_PRIMARY"  # ← НЕ СУЩЕСТВУЕТ
```

В файле определён только `MODEL_DESIGN_POWER: "antigravity/gemini-3.1-pro-high"`.

**Риск:** При отключении OmniRoute (omniroute.enabled: false) все Design-задачи падают с ошибкой разрешения алиаса. Design Lead роль становится неработоспособной.

**Решение:** Переименовать `$MODEL_DESIGN_PRIMARY` → `$MODEL_DESIGN_POWER` или добавить отдельный алиас `MODEL_DESIGN_PRIMARY`.

---

### 3. Артефакт предыдущей сессии в role_contract
**Файл:** `configs/orchestrator/role_contracts/orchestrator.yaml`

В конце файла обнаружен посторонний текст:
```yaml
execution_truth:
  ...
  forbidden_patterns:
    - "created without evidence"
    - "done without artifact list"
    - "checking without findings"
    - "continuing without state"


				# TODO LIST UPDATE REQUIRED - You MUST include the task_progress parameter in your NEXT tool call.
				**Current Progress: 6/7 items completed (86%)**
				...
```

**Риск:** YAML-парсер может упасть или проигнорировать валидную часть файла. Повреждение контракта оркестратора = полная остановка рантайма.

**Решение:** Немедленно очистить файл от артефактов.

---

## ⚠️ Серьёзные проблемы

### 4. Motion Awareness: конфиг ссылается на несуществующие ассеты
**Файл:** `configs/orchestrator/router.yaml` (раздел `motion_awareness`)

```yaml
motion_awareness:
  capability_spec: "configs/capabilities/gsap_motion.yaml"  # ← ДИРЕКТОРИИ НЕТ
  skills_path: ".agent/skills/"
  # Required skills:
  # - "gsap-animation.md"          ← НЕТ в .agent/skills/
  # - "gsap-performance-guardrails.md" ← НЕТ
  # - "gsap-scrolltrigger.md"      ← НЕТ
  # - "gsap-vs-framer-motion.md"   ← НЕТ
  # - "framer-motion-patterns.md"  ← НЕТ
```

**Риск:** При срабатывании motion-триггеров роутер попытается активировать несуществующие capability и skills. В лучшем случае — silent fail и откат к стандартному роутингу. В худшем — ошибка в рантайме.

**Решение:** Либо создать недостающие скиллы и capability-спек, либо отключить motion_awareness до их появления.

---

### 5. OmniRoute отключён, но комбо-конфиг актуален
**Файлы:** `configs/orchestrator/models.yaml` + `configs/orchestrator/omniroute_combos.yaml`

```yaml
# models.yaml
omniroute:
  enabled: false
```

При этом `omniroute_combos.yaml` содержит 187 проверенных моделей и 10 комбо. Все алиасы в `models.yaml` используют **прямые** ссылки (`kc/openrouter/auto`, `lmstudio/...`) вместо OmniRoute combo-имён.

**Риск:**
- Дублирование логики fallback в двух местах (models.yaml и combos.yaml)
- combos.yaml становится "зомби-конфигом" — поддерживается, но не используется
- Любое изменение в combos.yaml не влияет на реальный роутинг

**Решение:** Либо включить OmniRoute и перевести алиасы на combo-ссылки (`omniroute://combo/engineer`), либо удалить combos.yaml и консолидировать fallback-логику в models.yaml.

---

### 6. Несуществующие скиллы в AGENTS.md
**Файл:** `AGENTS.md` (раздел "Skill Categories")

В AGENTS.md перечислены скиллы, которых нет в `configs/skills/` и нет в `.agent/skills/`:

| Скилл в AGENTS.md | Есть в configs/skills/ | Есть в .agent/skills/ |
|-------------------|----------------------|---------------------|
| `21st-agents-sdk` | ❌ Нет | ❌ Нет |
| `21st-magic-mcp`  | ❌ Нет | ❌ Нет |
| `lm-studio-subagent-delegation` | ❌ Нет | ❌ Нет |
| `kanban`          | ❌ Нет | ❌ Нет |

При этом в `.agent/skills/` (runtime) есть скилл `ai-designer`, которого нет в `ACTIVE_SKILLS.md`.

**Риск:** Документация врёт о доступных возможностях. Агент может попытаться активировать несуществующий скилл.

**Решение:** Синхронизировать AGENTS.md с ACTIVE_SKILLS.md и реальным `.agent/skills/`. Удалить или добавить недостающие.

---

### 7. Зомби-конфиг skill_factory.yaml
**Файл:** `configs/autonomy/skill_factory.yaml`

```yaml
cataloging:
  registry_path: ".agent/skills/registry.json"  # ← НЕТ
```

В `.agent/skills/` есть только `.active_set_manifest.json`, но нет `registry.json`.

**Риск:** Skill Acquisition Engine (если он работает) пишет/читает в несуществующий файл. Потенциальная потеря данных о новых скиллах.

**Решение:** Либо обновить путь на `.active_set_manifest.json`, либо создать отдельный registry.json с нужной схемой.

---

### 8. Невалидная модель в fallback C4
**Файл:** `configs/orchestrator/router.yaml`

```yaml
C4:
  fallback_chain: ["cx/gpt-5.4", "$MODEL_ARCHITECT_STABILITY", "$MODEL_LOCAL_MEDIUM"]
```

`cx/gpt-5.4` — это значение `MODEL_ENGINEER_POWER`, но в C4 fallback используется как прямая строка, не через алиас. В models.yaml нет алиаса `MODEL_C4_FALLBACK_1`.

**Риск:** Неочевидная зависимость от конкретной строки. При изменении `MODEL_ENGINEER_POWER` fallback C4 не обновится.

**Решение:** Использовать алиас, например `$MODEL_ENGINEER_POWER`.

---

### 9. C5 Ralph Loop не сконфигурирован
**Файл:** `configs/orchestrator/router.yaml`

Для C3 и C4 явно задан `ralph_loop: { enabled: true, iterations: 4/5 }`. Для C5 — нет, хотя:
- `ralph_loop.min_complexity: "C3"` включает C5
- `human_audit_required: true` и `council_required: true` намекают на максимальную верификацию

**Риск:** C5 использует global defaults, но не получает усиленной итерации ralph_loop (которая логична для critical tier).

**Решение:** Явно задать `ralph_loop.iterations: 6` или `7` для C5.

---

### 10. Реестр скиллов (configs/registry/skills/) — семантическая путаница
**Файл:** `configs/registry/skills/*.yaml`

Содержимое: `analyze-repository.yaml`, `compare-alternatives.yaml`, `dynamic-handoff.yaml` и т.д. — это по сути **workflow-шаги / операции**, а не skills в понимании `ACTIVE_SKILLS.md`.

**Риск:** Два реестра скиллов с разной семантикой:
- `configs/skills/` — runtime skills (brainstorming, ui-premium, etc.)
- `configs/registry/skills/` — workflow operations (analyze-repository, etc.)

Это вводит в заблуждение при разработке и отладке.

**Решение:** Переименовать `configs/registry/skills/` → `configs/registry/operations/` или `workflow_steps/`.

---

## 💡 Рекомендации

### 11. Унифицировать Local Model aliases
В `models.yaml` все `MODEL_LOCAL_*` алиасы указывают на одну и ту же модель:

```yaml
MODEL_LOCAL_CODING: "lmstudio/google/gemma-4-e2b"
MODEL_LOCAL_MULTIPURPOSE: "lmstudio/google/gemma-4-e2b"
MODEL_LOCAL_VISION: "lmstudio/google/gemma-4-e2b"
MODEL_LOCAL_COMPACT: "lmstudio/google/gemma-4-e2b"
MODEL_LOCAL_MEDIUM: "lmstudio/google/gemma-4-e2b"
MODEL_LOCAL_ROBUST: "lmstudio/google/gemma-4-e2b"
# ... и ещё 5 штук
```

**Рекомендация:** Либо настроить разные модели для разных ролей (Gemma 4 не унифицирована для coding + vision + embedding), либо оставить 2-3 алиаса и удалить остальные.

---

### 12. Добавить валидацию cross-reference
**Рекомендация:** Создать скрипт валидации, который проверяет:
- Все алиасы `$MODEL_*` разрешаются в models.yaml
- Все skills из AGENTS.md существуют в `configs/skills/` и `.agent/skills/`
- Все пути `workflow:`, `contract_schema:` существуют на диске
- Лимиты router.yaml соответствуют AGENTS.md

Запускать в CI перед `publish-skills`.

---

## 📋 Чеклист исправлений

- [ ] **Критично:** Синхронизировать max_tools в router.yaml с AGENTS.md
- [ ] **Критично:** Исправить/добавить `MODEL_DESIGN_PRIMARY` алиас
- [ ] **Критично:** Очистить `orchestrator.yaml` от артефактов предыдущей сессии
- [ ] **Серьёзно:** Создать/отключить Motion Awareness ассеты
- [ ] **Серьёзно:** Решить судьбу OmniRoute (включить или удалить combos.yaml)
- [ ] **Серьёзно:** Синхронизировать AGENTS.md skills с ACTIVE_SKILLS.md
- [ ] **Серьёзно:** Исправить путь `registry.json` в skill_factory.yaml
- [ ] **Серьёзно:** Заменить `cx/gpt-5.4` на алиас в C4 fallback
- [ ] **Серьёзно:** Добавить ralph_loop для C5
- [ ] **Серьёзно:** Переименовать `configs/registry/skills/` для ясности
- [ ] **Рекомендация:** Свернуть избыточные MODEL_LOCAL_* алиасы
- [ ] **Рекомендация:** Написать валидатор cross-reference

---

## 📎 Приложения

### A. Полная карта max_tools
```
router.yaml:
  C1: 15  →  AGENTS.md: 8   ❌
  C2: 25  →  AGENTS.md: 12  ❌
  C3: 30  →  AGENTS.md: 20  ❌
  C4: 35  →  AGENTS.md: 30  ❌
  C5: 50  →  AGENTS.md: 50  ✅
```

### B. Полная карта скиллов (ACTUAL vs DOCUMENTED)
```
ACTIVE_SKILLS.md declares: 42 skills
.agent/skills/ has:        35 directories
configs/skills/ has:       35 directories + 3 files

Missing in .agent/skills/ from ACTIVE_SKILLS.md: 0 ✅
Extra in .agent/skills/ not in ACTIVE_SKILLS.md: ai-designer, pi-cli ❌
Missing in configs/skills/ from AGENTS.md: 21st-agents-sdk, 21st-magic-mcp, lm-studio-subagent-delegation, kanban ❌
```

---

*Ревью завершено. Все выявленные проблемы документированы с указанием файлов, строк и путей исправления.*
