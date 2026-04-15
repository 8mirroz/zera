---
name: design-system-architect
description: Generate and maintain design systems with token governance, page overrides, and adaptive source routing.
---

# Design System Architect

## When to use
- You need a full design system for a new product.
- You need page-specific overrides on top of master design rules.
- You need consistency checks across style, color, typography, and UX constraints.

## Commands
```bash
cd repos/packages/design-system
export PYTHONPATH="$PWD/src"

# Full design system
python3 -m antigravity_design_system --query "fintech dashboard" --design-system -p "FinFlow"

# Persist MASTER + page override
python3 -m antigravity_design_system --query "fintech dashboard" --design-system --persist -p "FinFlow" --page "dashboard"

# Domain search
python3 -m antigravity_design_system --query "glassmorphism" --domain style

# Lightweight audit
python3 -m antigravity_design_system.debug_audit
```

## Output contract
- `design-system/<project>/MASTER.md` is global source of truth.
- `design-system/<project>/pages/<page>.md` overrides MASTER only for that page.
- If page override file does not exist, use MASTER only.
