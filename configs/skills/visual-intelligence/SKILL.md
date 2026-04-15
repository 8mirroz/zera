---
name: visual-intelligence
description: Extract design DNA, trends, and aesthetic parameters from visual sources (Pinterest) using Perplexity Sonar Pro.
---

# Visual Intelligence Skill

## When to use
- You need to analyze a competitor's visual style.
- You need to extract a color palette or typography from a mood board.
- You want to find the "vibe" of a specific niche (e.g., "cyberpunk fintech").

## Capabilities
1. **Pinterest Scanning**: Extracts 4-point DNA (Color, Typography, Visual Language, Vibe).
2. **Trend Analysis**: Identifies current design trends in a specific domain.

## Commands

### 1. Scan Pinterest Profile
Extracts visual DNA from a Pinterest board or profile.

```bash
python3 configs/skills/visual-intelligence/scripts/scan_pinterest.py --url "https://ru.pinterest.com/deushareAI/"
```

**Output:**
- JSON with Visual DNA
- Ready-to-use prompt context for `design-system-architect`

### 2. Generate Prompt Context
Get a string representation of the visual DNA to feed into other agents.

```bash
python3 configs/skills/visual-intelligence/scripts/scan_pinterest.py --url "..." --format prompt
```

## Integration
Used by:
- `design-system-architect` (to seed the generator)
- `ui-premium` (for inspiration)
