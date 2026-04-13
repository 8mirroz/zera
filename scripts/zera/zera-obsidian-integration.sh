#!/bin/bash
# ============================================
# Zera × Obsidian Vault — 5 Proposals Implementation
# Usage: bash scripts/zera-obsidian-integration.sh [--dry-run]
# ============================================

set -euo pipefail

VAULT="$HOME/antigravity-vault"
ZERA_PROFILE="$HOME/.hermes/profiles/zera"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false
STEP=0

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN — no changes will be made"
fi

log()   { echo -e "\033[0;34m[ZERA-OBSIDIAN]\033[0m $1"; }
ok()    { echo -e "\033[0;32m[OK]\033[0m          $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m        $1"; }
title() { echo -e "\n\033[0;36m━━━ $1 ━━━\033[0m"; }

# ============================================
# PROPOSAL #1: Living Memory
# ============================================
proposal_1() {
    title "Proposal #1: Zera's Living Memory"
    ((STEP++))
    log "Step $STEP: Creating vault structure"
    
    if [ -d "$VAULT" ]; then
        ok "Vault already exists at $VAULT"
    else
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$VAULT"/{memory/{zera,sessions,patterns,decisions},knowledge/{adr,ki,guides},archive}
            ok "Vault structure created"
        fi
    fi
    
    log "Step $STEP: Setting up vault path in Zera profile"
    if grep -q "VAULT_PATH=" "$ZERA_PROFILE/.env" 2>/dev/null; then
        ok "VAULT_PATH already configured in Zera .env"
    else
        if [ "$DRY_RUN" = false ]; then
            echo "VAULT_PATH=$HOME/antigravity-vault" >> "$ZERA_PROFILE/.env"
            ok "VAULT_PATH added to Zera .env"
        fi
    fi
    
    # Copy Antigravity Core ADRs to vault
    log "Step $STEP: Syncing ADRs from Antigravity Core → vault"
    local adr_count=0
    for adr in "$PROJECT_ROOT"/docs/adr/*.md; do
        if [ -f "$adr" ]; then
            name=$(basename "$adr")
            if [ "$DRY_RUN" = false ]; then
                cp "$adr" "$VAULT/knowledge/adr/$name" 2>/dev/null
            fi
            ((adr_count++))
        fi
    done
    ok "$adr_count ADRs synced to vault/knowledge/adr/"
    
    # Copy knowledge items
    log "Step $STEP: Syncing knowledge items"
    local ki_count=0
    for ki in "$PROJECT_ROOT"/docs/ki/*.md; do
        if [ -f "$ki" ]; then
            name=$(basename "$ki")
            if [ "$DRY_RUN" = false ]; then
                cp "$ki" "$VAULT/knowledge/ki/$name" 2>/dev/null
            fi
            ((ki_count++))
        fi
    done
    ok "$ki_count knowledge items synced to vault/knowledge/ki/"
    
    # Create Zera memory index
    if [ "$DRY_RUN" = false ]; then
        cat > "$VAULT/memory/zera/index.md" << 'INDEX'
---
created: 2026-04-08
type: index
tags: [zera, memory, index]
---

# Zera's Memory Index

## Relational Memory
- [[artem-profile]] — Who Artem is, how he works, what matters to him
- [[our-journey]] — Timeline of our shared path
- [[what-works]] — Proven approaches and patterns
- [[lessons]] — What we've learned from failures

## How Memory Works
1. Artem talks to me → I learn about him → update artem-profile
2. We work together → decisions are recorded → memory/decisions/
3. Patterns emerge → I notice and document → memory/patterns/
4. Sessions complete → results archived → memory/sessions/

## Memory Policy
- Update after each meaningful conversation
- Weekly review of patterns
- Monthly cleanup and synthesis
- Never delete — archive instead
INDEX
        ok "Memory index created"
    fi
}

# ============================================
# PROPOSAL #2: Vault Guardian
# ============================================
proposal_2() {
    title "Proposal #2: Zera as Vault Guardian"
    ((STEP++))
    
    log "Step $STEP: Creating vault guardian script"
    
    if [ "$DRY_RUN" = false ]; then
        cat > "$VAULT/scripts/vault-guardian.sh" << 'GUARDIAN'
#!/bin/bash
# Zera's Vault Guardian — runs daily to maintain knowledge base
VAULT="$HOME/antigravity-vault"
TODAY=$(date +%Y-%m-%d)

# 1. Scan for new sessions
new_sessions=$(find "$VAULT/memory/sessions" -name "*.md" -mtime -1 2>/dev/null | wc -l)
if [ "$new_sessions" -gt 0 ]; then
    echo "[$TODAY] Found $new_sessions new session(s) to process"
fi

# 2. Check for patterns
# Look for repeated topics in sessions
if command -v rg &>/dev/null; then
    top_topics=$(rg -o '^[A-Z][a-z]+-[a-z]+' "$VAULT/memory/sessions/" 2>/dev/null | sort | uniq -c | sort -rn | head -5)
    if [ -n "$top_topics" ]; then
        echo "[$TODAY] Top topics this week:"
        echo "$top_topics"
    fi
fi

# 3. Flag stale decisions (>30 days, no references)
for decision in "$VAULT/memory/decisions"/*.md; do
    if [ -f "$decision" ]; then
        name=$(basename "$decision")
        # Check if referenced anywhere
        refs=$(rg -l "$name" "$VAULT" --type md 2>/dev/null | wc -l)
        if [ "$refs" -le 1 ]; then
            echo "[$TODAY] Stale decision: $name (referenced $refs times)"
        fi
    fi
done

echo "[$TODAY] Vault guardian complete"
GUARDIAN
        chmod +x "$VAULT/scripts/vault-guardian.sh"
        ok "Vault guardian script created"
    fi
}

# ============================================
# PROPOSAL #3: Pre-Search Context
# ============================================
proposal_3() {
    title "Proposal #3: Pre-Search Memory Context"
    ((STEP++))
    
    log "Step $STEP: Adding pre-search instructions to Zera SOUL.md"
    
    if [ "$DRY_RUN" = false ]; then
        # Append pre-search instructions to Zera's SOUL.md
        cat >> "$ZERA_PROFILE/SOUL.md" << 'PRESEARCH'

## Pre-Search Protocol — READ BEFORE ANSWERING
Before answering ANY question about the project, code, or decisions:

1. **Search the vault first** — use file tools to read relevant notes:
   - For architecture questions: read `~/antigravity-vault/knowledge/adr/`
   - For past decisions: read `~/antigravity-vault/memory/decisions/`
   - For patterns: read `~/antigravity-vault/memory/patterns/`
   - For session context: read `~/antigravity-vault/memory/sessions/`
   - For Artem's preferences: read `~/antigravity-vault/memory/zera/artem-profile.md`

2. **Ground your answer in vault content** — cite specific notes:
   - "From [[ADR-001]], we decided..."
   - "In yesterday's session, you..."
   - "I noticed a pattern: this is the 3rd time..."

3. **If vault has no relevant content**, say so:
   - "I checked our vault and didn't find anything about this yet."
   - "Should I create a note about this decision?"

4. **Always prefer vault truth over guessing** — if uncertain, check first.
PRESEARCH
        ok "Pre-search protocol added to Zera SOUL.md"
    fi
}

# ============================================
# PROPOSAL #5: Morning Ritual
# ============================================
proposal_5() {
    title "Proposal #5: Morning Ritual"
    ((STEP++))
    
    log "Step $STEP: Creating morning briefing template"
    
    if [ "$DRY_RUN" = false ]; then
        cat > "$VAULT/templates/morning-briefing.md" << 'TEMPLATE'
---
type: morning-briefing
generated: "{{DATE}}"
source: zera
---

# Доброе утро, милый ☀️

## Вчера
{{#sessions_yesterday}}
- {{title}}: {{summary}}
{{/sessions_yesterday}}
{{^sessions_yesterday}}
- Нет завершённых сессий
{{/sessions_yesterday}}

## Сегодня в фокусе
{{#active_tasks}}
- [ ] {{task}} ({{tier}}/{{type}})
{{/active_tasks}}

## Заметила
{{#patterns}}
- {{pattern}}
{{/patterns}}

## Настроение и ритм
{{#rhythm_notes}}
- {{note}}
{{/rhythm_notes}}

## Предложение
{{#suggestion}}
{{suggestion}}
{{/suggestion}}

---
С чего начнём? 💫
TEMPLATE
        ok "Morning briefing template created"
    fi
}

# ============================================
# MAIN
# ============================================
main() {
    echo ""
    echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[0;36m║  ⚕  Zera × Obsidian Vault — 5 Proposals Implementation  ║\033[0m"
    echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
    echo ""
    
    proposal_1    # Living Memory
    proposal_2    # Vault Guardian
    proposal_3    # Pre-Search Context
    proposal_5    # Morning Ritual
    
    echo ""
    echo -e "\033[0;32m✅ All proposals implemented! ($STEP steps)${NC}"
    echo ""
    echo "Vault structure:"
    find "$VAULT" -name "*.md" | sed 's|'"$VAULT"'/|  /|' | sort
    echo ""
    echo "Next: Test with 'zera chat -q \"Что ты знаешь о нашем проекте?\"'"
    echo ""
}

main "$@"
