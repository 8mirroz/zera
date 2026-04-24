---
name: write-a-prd
description: Create a PRD through user interview, codebase exploration, and module design, then submit as a GitHub issue. Use when user wants to write a PRD, create a product requirements document, or plan a new feature.
source: https://github.com/mattpocock/skills/tree/main/write-a-prd
---

# Write a PRD

## Process

1. Ask for a long, detailed description of the problem and potential solutions.

2. Explore the repo to verify assertions and understand current codebase state.

3. Interview the user relentlessly about every aspect of the plan. Walk down each branch of the design tree, resolving dependencies one-by-one.

4. Sketch major modules to build or modify. Prioritize **deep modules** — simple interface, rich internal logic, testable in isolation. Confirm with user which modules need tests.

5. Write the PRD using the template below and submit as a GitHub issue.

## PRD Template

```md
## Problem Statement
[Problem from user's perspective]

## Solution
[Solution from user's perspective]

## User Stories
1. As a <actor>, I want <feature>, so that <benefit>
[Extensive numbered list covering all aspects]

## Implementation Decisions
- Modules to build/modify
- Interface contracts
- Architectural decisions
- Schema/API changes
[NO file paths or code snippets — they go stale]

## Testing Decisions
- Which modules get tests
- What behaviors to verify
- Integration vs unit split

## Out of Scope
[Explicit exclusions to prevent scope creep]
```

## Key Rules
- One question at a time during interview
- Deep modules > shallow modules
- No file paths in PRD (stale quickly)
- File as GitHub issue when complete
