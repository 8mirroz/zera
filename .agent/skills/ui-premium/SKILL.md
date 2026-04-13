---
name: ui-premium
description: Create premium interfaces using the unified Antigravity design-system package.
---

# UI Premium Skill

## Scope
Use this skill when building high-quality UI with strict token consistency and predictable overrides.

## Core principles
1. Theme sync via CSS variables (`var(--tg-theme-...)` for Telegram, `--ag-*` for web).
2. Mobile-first layout and safe area support.
3. Meaningful motion only (150-300ms, respect `prefers-reduced-motion`).
4. Accessibility baseline: contrast >= 4.5:1 and visible focus states.

## Design system engine
Primary engine path:
- `repos/packages/design-system`

Run commands:
```bash
cd repos/packages/design-system
export PYTHONPATH="$PWD/src"

# Generate full design system
python3 -m antigravity_design_system --query "saas analytics" --design-system -p "Pulse"

# Persist MASTER + page override
python3 -m antigravity_design_system --query "saas analytics" --design-system --persist -p "Pulse" --page "dashboard"

# Domain search (style/color/typography/ux/...)
python3 -m antigravity_design_system --query "glassmorphism" --domain style
```

## Source priority for adaptive mode
1. Stitch (tokens)
2. 21st.dev (components)
3. MagicUI (motion blocks)
4. Pinterest (visual DNA)

MCP example config:
- `configs/tooling/mcp_design_sources.example.json`

## UI Library Registry
- `docs/ki/UI_LIBRARIES_REGISTRY_RU.md`

## Starter templates
- `templates/design/base-theme.css`
- `templates/design/tailwind.theme.preset.ts`

## Quality gate
Before handoff, run:
```bash
cd repos/packages/design-system
./scripts/run_quality_checks.sh
```
