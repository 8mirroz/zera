---
name: design-an-interface
description: Generate multiple radically different interface designs for a module using parallel sub-agents. Use when user wants to design an API, explore interface options, compare module shapes, or mentions "design it twice".
source: https://github.com/mattpocock/skills/tree/main/design-an-interface
---

# Design an Interface

Based on "Design It Twice" from *A Philosophy of Software Design*: your first idea is unlikely to be the best. Generate multiple radically different designs, then compare.

## Process

### 1. Gather Requirements
- What problem does this module solve?
- Who are the callers? (other modules, external users, tests)
- What are the key operations?
- Constraints? (performance, compatibility, existing patterns)
- What should be hidden vs exposed?

### 2. Generate Designs (Parallel Sub-Agents)

Spawn 3 sub-agents simultaneously. Each gets a different constraint:

| Agent | Constraint |
|-------|-----------|
| A | Minimize method count (1–3 methods max) |
| B | Maximize flexibility (support many use cases) |
| C | Optimize for the most common case |

Each agent outputs:
1. Interface signature (types/methods)
2. Usage example (how caller uses it)
3. What this design hides internally
4. Trade-offs

### 3. Present & Compare

Show each design sequentially. Then compare on:
- **Simplicity**: How easy to use correctly?
- **Depth**: How much complexity is hidden?
- **Testability**: How easy to test in isolation?
- **Evolvability**: How easy to change internals without breaking callers?

### 4. Recommend

Pick the best design with explicit reasoning. Offer to combine strengths if warranted.

## Key Rules
- Deep modules > shallow modules (simple interface, rich internals)
- Caller perspective first — design for the user of the interface
- Pairs with `grill-me` to stress-test the chosen design
- Pairs with `write-a-prd` for full feature planning flow
