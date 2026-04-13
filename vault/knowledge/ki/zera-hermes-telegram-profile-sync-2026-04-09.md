---
type: knowledge-item
created: 2026-04-10
tags: [synced, healed]
---

# KI: Zera/Hermes/Telegram Profile Sync (2026-04-09)

## Context
- Telegram responses intermittently showed generic Hermes identity ("Hermes Agent, Nous Research") instead of Zera persona.
- Hermes local setup had multiple profiles (`antigravity`, `zera`) with conflicting defaults.
- Runtime routing for T7 failed in `swarmctl` due to missing `zeroclaw_profiles` initialization.

## Findings
1. `RuntimeRegistry` referenced `self.zeroclaw_profiles` without initialization, causing crash on T7 routing with runtime profile resolution.
2. `configs/tooling/zeroclaw_profiles.json` was missing in repo, while runtime config expected `zera-telegram-prod`.
3. `repos/apps/zera-telegram/bot/runtime_bridge.py` used a hardcoded generic system prompt, bypassing canonical persona files.
4. Local Hermes profile `zera` had internal transport pointing to `antigravity` profile.
5. Sticky Hermes default profile was `antigravity`, not `zera`.

## Changes Applied
- Fixed runtime profile loading in `RuntimeRegistry`.
- Added canonical `configs/tooling/zeroclaw_profiles.json` with `zera-telegram-prod` and `zera-edge-local`.
- Updated Telegram bot to assemble system prompt from `configs/personas/zera/*`.
- Updated Zera identity with explicit queen-companion presence.
- Switched local Hermes sticky profile to `zera`.
- Fixed local `~/.hermes/profiles/zera/config.yaml` transport profile to `zera`.

## Operational Impact
- T7 route resolution no longer crashes when runtime profile is present.
- Telegram bot now uses Zera persona constraints/tone as source-of-truth from repo.
- Local Hermes defaults align with Zera profile and avoid accidental fallback to antigravity persona context.
