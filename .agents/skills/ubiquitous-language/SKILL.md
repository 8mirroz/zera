---
name: ubiquitous-language
description: Extract a DDD-style ubiquitous language glossary from the current conversation, flagging ambiguities and proposing canonical terms. Use when user wants to define domain terms, build a glossary, harden terminology, or mentions "domain model", "DDD", "ubiquitous language".
source: https://github.com/mattpocock/skills/tree/main/ubiquitous-language
---

# Ubiquitous Language

Extract and formalize domain terminology into a consistent glossary. Saves to `UBIQUITOUS_LANGUAGE.md`.

## Process

1. **Scan** the conversation for domain-relevant nouns, verbs, concepts.

2. **Identify problems**:
   - Same word → different concepts (ambiguity)
   - Different words → same concept (synonyms)
   - Vague or overloaded terms

3. **Propose canonical glossary** with opinionated term choices.

4. **Write** to `UBIQUITOUS_LANGUAGE.md` in working directory.

5. **Output summary** inline in conversation.

## Output Format

```md
# Ubiquitous Language

## <Domain Group>

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Order** | Customer's request to purchase items | Purchase, transaction |

## Relationships
- An **Invoice** belongs to exactly one **Customer**

## Example dialogue
> **Dev:** "When a **Customer** places an **Order**..."
> **Domain expert:** "..."

## Flagged ambiguities
- "account" used for both **Customer** and **User** — distinct concepts
```

## Key Rules
- Opinionated: pick ONE canonical term, list aliases to avoid
- Group terms by domain area (not alphabetically)
- Include example dialogue showing terms in context
- Flag every ambiguity explicitly
- Pairs with `write-a-prd` — run before writing PRD to align terminology
- Pairs with `grill-me` — use to resolve terminology conflicts during grilling
