---
description: Knowledge-base workflow for AI bot and RAG systems.
---

# /ai-bot-kb

## Purpose

Manage AI bot knowledge bases with provenance, retrieval quality, and update safety.

## Procedure

1. Identify source documents and trust level.
2. Normalize content with provenance and stable IDs.
3. Validate retrieval against representative questions.
4. Report coverage gaps and stale sources.

## Output

- Source inventory.
- Retrieval validation summary.
- Update or rollback recommendation.

## Gate

No knowledge update without provenance and a retrieval smoke test.
