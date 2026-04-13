# Antigravity Design System

Unified design system engine for Antigravity Core.

## What is included
- Offline UI/UX knowledge base (styles, palettes, typography, UX rules, stacks)
- BM25 search engine for design recommendations
- Design system generator (`MASTER + page overrides`)
- Adaptive design aggregator (Stitch/21st/MagicUI/Pinterest abstraction)
- Lightweight debug audit for consistency checks

## Quick start
```bash
cd repos/packages/design-system
python3 -m antigravity_design_system --query "fintech dashboard" --design-system -p "FinFlow"
```

## Commands
```bash
# Search in one domain
python3 -m antigravity_design_system --query "glassmorphism" --domain style

# Generate design system
python3 -m antigravity_design_system --query "ecommerce luxury" --design-system -p "Maison Store"

# Persist MASTER + page override
python3 -m antigravity_design_system --query "saas analytics" --design-system --persist -p "Pulse" --page "dashboard"

# Lightweight quality audit
python3 -m antigravity_design_system.debug_audit
```

## Data sources
- `data/styles.csv`
- `data/colors.csv`
- `data/typography.csv`
- `data/ux-guidelines.csv`
- `data/stacks/*.csv`

## Environment variables
- `AGDS_DATA_DIR` optional override for data path
- `PERPLEXITY_API_KEY` optional, only for Pinterest scanner
- `STITCH_API_KEY` optional, only for adaptive source priority
