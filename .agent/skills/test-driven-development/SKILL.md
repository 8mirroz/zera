---
name: test-driven-development
description: Use when writing logic that needs to be robust, or when fixing bugs (reproduction test first).
---

# Test Driven Development

## The Cycle (Red-Green-Refactor)

### 1. RED (Write a failing test)
- Write the smallest possible test case that describes the desired behavior.
- Run the test.
- **Verify it fails** for the right reason.

### 2. GREEN (Make it pass)
- Write the minimum code necessary to make the test pass.
- Do not optimize. Do not over-engineer.
- **Verify it passes**.

### 3. REFACTOR (Clean up)
- Remove duplication.
- Improve naming.
- Extract methods.
- **Verify it still passes**.

## When to use
- **Bugs:** Always write a reproduction test first.
- **Complex Logic:** Parsers, state machines, algorithmic code.
- **API Endpoints:** Request/Response validation.

## Tools
- Python: `pytest`
- JS/TS: `vitest` or `jest`

## Anti-Patterns (See testing-anti-patterns.md)
- mocking too much (implementation details)
- testing library code
- slow tests
