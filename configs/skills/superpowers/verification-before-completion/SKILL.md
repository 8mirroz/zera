---
name: verification-before-completion
description: Use before declaring a task done (especially C2+): run targeted checks/tests and confirm acceptance criteria.
---

# Verification Before Completion

## The Checklist

Before saying "I'm done", verify:

1. **Requirements Met**: Did I do everything the user asked?
2. **Persistence**: Did I save the file? (Don't laugh, it happens).
3. **Builds**: Does the code compile/interpret?
4. **Cleanliness**: Did I remove debug logs (`console.log`, `print`)?
5. **Tests**: Did I run the relevant tests?
6. **Linter**: Did I run the linter?

## Evidence
- Don't just check the box.
- **Show the evidence** in the final output (e.g. "Ran tests, 5 passed").

## If Verification Fails
- Go back to **Fix** mode.
- Do not deliver broken code with a "note".
