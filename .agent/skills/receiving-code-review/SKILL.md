---
name: receiving-code-review
description: How to process and apply feedback from code reviews (human or agent).
---

# Receiving Code Review

## The Protocol

1. **Read Everything First**: Don't start fixing until you read all comments.
2. **Prioritize**:
   - **Blockers**: Bugs, security issues, spec violations.
   - **Improvements**: Refactoring, naming, style.
   - **Nits**: Typos, minor formatting.

3. **Respond**:
   - If you disagree, ask clarifying questions.
   - If you agree, implement the fix.
   - Mark comments as resolved when done.

4. **Verify Fixes**:
   - Run tests again after applying review fixes.
   - Don't break existing functionality while fixing nits.
