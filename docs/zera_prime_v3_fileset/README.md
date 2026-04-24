# ZERA PRIME v3 — Sovereign Persona + Hermes Runtime Fileset

Purpose: make Zera the sovereign identity, memory, governance, growth and decision layer, while Hermes becomes the runtime execution grid for tools, agents, builds, MCP and automation.

Core rule:

```text
Zera decides. Hermes executes.
Zera owns identity. Hermes owns runtime.
Zera owns memory approval. Hermes returns evidence.
```

This package is designed to be copied into:

```text
/Users/user/zera-core/
/Users/user/.hermes/runtime/
```

Recommended install order:

1. Backup `/Users/user/zera` and `/Users/user/.hermes`.
2. Create `/Users/user/zera-core`.
3. Copy `zera-core/*` into `/Users/user/zera-core/`.
4. Copy `hermes-runtime/*` into `/Users/user/.hermes/runtime/`.
5. Replace `.hermes/SOUL.md` with `hermes-runtime/SOUL.runtime.md`.
6. Run `scripts/check_zera_hermes_drift.py`.
7. Only then remove duplicate profiles/skills/vault copies.
