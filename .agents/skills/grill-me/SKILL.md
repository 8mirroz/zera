---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
source: https://github.com/mattpocock/skills/tree/main/grill-me
---

# Grill Me

Stress-test a plan or design through relentless interviewing. Every branch of the decision tree must be resolved.

## Process

1. Ask user to describe the plan or design to stress-test.

2. For each aspect of the plan:
   - Ask ONE question at a time
   - If the answer can be found by exploring the codebase — explore instead of asking
   - Provide your recommended answer with each question
   - Walk down every branch before moving to the next

3. Track unresolved decisions. Don't move on until each is resolved.

4. When all branches are resolved, summarize:
   - Key decisions made
   - Assumptions validated
   - Risks identified
   - Open questions (if any remain)

## Question Categories

- **Scope**: What's in? What's explicitly out?
- **Dependencies**: What does this touch? What breaks if it changes?
- **Edge cases**: What happens when X fails? What if Y is null?
- **Rollback**: How do we undo this if it goes wrong?
- **Testing**: How do we know it works?
- **Performance**: What's the load? Any bottlenecks?

## Key Rules
- One question per message
- Always provide your recommended answer
- Explore codebase before asking about existing behavior
- Don't stop until every branch is resolved
- Pairs well with `brainstorming` (use after initial idea exploration)
