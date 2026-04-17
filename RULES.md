# Точка входа в правила Antigravity

`RULES.md` — человекочитаемый индекс.  
Машинный источник истины для порядка, статусов и потребителей правил:
`configs/rules/rules.registry.yaml`.

Читать в таком порядке:
1. `configs/rules/WORKSPACE_STANDARD.md`
2. `configs/rules/AGENT_ONLY.md`
3. `configs/rules/ENGINEERING_STANDARDS.md`
4. `configs/rules/BUILD_PROFILE.md`
5. `configs/rules/GLOBAL_RULE_RU.md` (только workspace-дополнения)
6. `configs/rules/TASK_ROUTING.md`
7. `configs/rules/SECURITY_RULES.md`
8. `configs/rules/META_PROMPT.md`
9. `configs/rules/QWEN.md`
10. `configs/rules/LEGACY_CODE_PROTECTION.md`
11. `configs/rules/ANTI_CHAOS.md`

## Как запускать Agent OS v2

1) Active Skills публикуются в `.agents/skills/` из `configs/skills/ACTIVE_SKILLS.md`:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills
```

2) Swarm управляется workflow’ами из `.agents/workflows/*.md`.

3) Быстрая проверка целостности:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
```

## Языковая политика

- Отчеты, планы и коммуникация для владельца системы: на русском.
- Технические термины/команды могут быть на английском, если это требуется инструментами.
- Любое английское системное сообщение в отчете должно сопровождаться русским пояснением.
