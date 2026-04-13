---
type: knowledge
created: 2026-04-08
source: zera-initialization
tags: [lessons, learnings, growth]
---

# Lessons — What We've Learned

## About Integration
- SSL handshake issues on macOS — use `GIT_SSL_NO_VERIFY=true` for git clones
- `--args` parsing in Hermes CLI can conflict with subcommand args — edit config directly
- Python version mismatch — Hermes needs 3.11, system has 3.9, uv manages 3.12

## About Setup Flow
- Install CLI first, then configure — Artem wants to see it working
- Copy existing configs from Antigravity Core — don't create from scratch
- Test after each step — `hermes status`, `hermes doctor`, `hermes version`

## About Zera
- SOUL.md needs to be in profile directory to take effect
- Profile-specific configs override global defaults
- Alias (`zera`) created automatically for profile access
