# ZeroClaw + Zera Integration Guide (2026-03-11)

## Scope

This guide covers:
- ZeroClaw runtime provider activation in Agent OS.
- Runtime routing to `zeroclaw` for Telegram (`T7`) workloads.
- Zera persona pack structure and mode routing.
- Verification commands for runtime dispatch and fallback.

## Source of Truth

- Runtime providers: `configs/tooling/runtime_providers.json`
- ZeroClaw profiles: `configs/tooling/zeroclaw_profiles.json`
- Zera persona pack: `configs/personas/zera/`
- Zera mode router: `configs/tooling/zera_mode_router.json`
- Runtime dispatch code: `repos/packages/agent-os/src/agent_os/agent_runtime.py`

## Installation

Development:
```bash
brew install zeroclaw
```

Optional binary override:
```bash
export ZEROCLAW_BIN=/absolute/path/to/zeroclaw
```

Enable adapter:
```bash
export ENABLE_ZEROCLAW_ADAPTER=true
```

## Runtime Routing Checks

Default route preview:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py route "telegram companion flow" --task-type T7 --complexity C3
```

Expected output fields:
- `runtime_provider`
- `runtime_profile`
- `channel`
- `persona_id`
- `runtime_reason`

Force provider:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py route "telegram companion flow" --task-type T7 --complexity C3 --runtime-provider zeroclaw --runtime-profile zera-telegram-prod
```

## Run Checks

Minimal run:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py run "support me and build a plan" --task-type T7 --complexity C2 --runtime-provider zeroclaw --runtime-profile zera-telegram-prod
```

Run with explicit source-tier governance:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py run "prepare external outreach proposal" \
  --task-type T7 --complexity C2 \
  --runtime-provider zeroclaw --runtime-profile zera-telegram-prod \
  --source-tier "Tier C" --request-capability-promotion
```

Expected behavior:
- runtime selection is constrained by source trust policy;
- `policy_violation_detected` event is emitted if tier policy blocks promotion;
- execution remains bounded (fallback/provider constraints apply).

## Background Daemon
Drain queued background jobs:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py background-daemon --limit 10
```

## Native Binary Mode
Enable native binary command templates from `zeroclaw_profiles.json`:
```bash
export ENABLE_ZEROCLAW_ADAPTER=true
export ZEROCLAW_USE_NATIVE_BIN=true
export ZEROCLAW_BIN=zeroclaw
python3 repos/packages/agent-os/scripts/swarmctl.py run "support me and build a plan" --task-type T7 --complexity C2 --runtime-provider zeroclaw --runtime-profile zera-edge-local
```

## Edge Deployment Assets
- [README.md](/Users/user/antigravity-core/ops/zeroclaw/README.md)
- [docker-compose.yaml](/Users/user/antigravity-core/ops/zeroclaw/docker-compose.yaml)
- [zera-telegram-bot.service](/Users/user/antigravity-core/ops/zeroclaw/zera-telegram-bot.service)
- [zeroclaw-zera.service](/Users/user/antigravity-core/ops/zeroclaw/zeroclaw-zera.service)

## Telegram Readiness
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py telegram-readiness --mode polling
python3 repos/packages/agent-os/scripts/swarmctl.py telegram-readiness --mode webhook
```

## Background Controls
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py background-status
python3 repos/packages/agent-os/scripts/swarmctl.py background-pause --minutes 60
python3 repos/packages/agent-os/scripts/swarmctl.py background-resume
python3 repos/packages/agent-os/scripts/swarmctl.py stop-signal --scope global --minutes 30
python3 repos/packages/agent-os/scripts/swarmctl.py stop-clear --scope global
python3 repos/packages/agent-os/scripts/swarmctl.py approval-list
python3 repos/packages/agent-os/scripts/swarmctl.py approval-resolve <ticket_id> approve
python3 repos/packages/agent-os/scripts/swarmctl.py goal-stack
python3 repos/packages/agent-os/scripts/swarmctl.py budget-status
python3 repos/packages/agent-os/scripts/swarmctl.py incident-report
```

Fallback behavior:
- If `zeroclaw` is disabled/unavailable, runtime falls back to `agent_os_python`.
- Fallback reason is recorded in runtime decision fields and trace events.

## Zera Personality and Skills

Persona artifacts:
- `configs/personas/zera/manifest.yaml`
- `configs/personas/zera/identity.md`
- `configs/personas/zera/constitution.md`
- `configs/personas/zera/safety.md`
- `configs/personas/zera/modes.yaml`
- `configs/personas/zera/eval_cases.json`

Skill pack (separate active set):
- `configs/skills/ZERA_ACTIVE_SKILLS.md`
- `configs/skills/zera-*`

## Verification

Targeted tests:
```bash
python3 -m unittest \
  repos/packages/agent-os/tests/test_runtime_registry.py \
  repos/packages/agent-os/tests/test_agent_runtime_dispatch.py \
  repos/packages/agent-os/tests/test_persona_mode_router.py \
  repos/packages/agent-os/tests/test_swarmctl_runtime_routing.py \
  repos/packages/agent-os/tests/test_swarmctl_run_integration.py
```

Benchmark with source-tier policy:
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py benchmark --suite configs/tooling/benchmark_suite.json
```

## Notes

- ZeroClaw provider supports `stdio_json` runtime execution with policy enforcement (security profile checks, approval tickets, loop/budget guards, stop-signal honoring, proof-of-action events).
- Benchmark runner enforces `source_tier` policy and blocks `requests_capability_promotion=true` for disallowed tiers (for example `Tier C` by default policy).
- Existing Agent OS default runtime remains unchanged for non-T7 paths.
