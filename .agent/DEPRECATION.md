# DEPRECATED — `.agent/` directory

> **Status:** Deprecated. Migrate to `.agents/` (plural).
> **Date:** 2026-04-14
> **Action:** Do NOT add new files here. Use `.agents/` instead.

## Why

The canonical agent runtime directory is `.agents/` (plural). This `.agent/` directory
is a legacy path that persists for backward compatibility with older tooling references.

## Migration

All content from `.agent/memory/` should be merged into `.agents/memory/`:

| Legacy Path | Canonical Path |
|-------------|----------------|
| `.agent/memory/memory.jsonl` | `.agents/memory/memory.jsonl` |
| `.agent/memory/build-library/` | `.agents/memory/build-library/` |
| `.agent/memory/repos-catalog/` | `.agents/memory/repos-catalog/` |
| `.agent/config/` | `.agents/config/` |
| `.agent/evolution/` | `.agents/evolution/` |
| `.agent/skills/` | `.agents/skills/` |
| `.agent/workflows/` | `.agents/workflows/` |

## References

- `router.yaml` references `.agent/skills/` and `.agent/memory/` — these need updating.
- `AGENT_ROLE_CONTRACTS.md` references `.agent/` paths — needs updating.
- After migration, this directory should become a symlink: `ln -s .agents .agent`

## Do NOT

- Delete this directory without verifying content has been migrated
- Add new files here
- Create new tooling references to this path
