# Implementation Plan - ZeroClaw + Zera Integration

Execution log for approved platform-investment plan.

## Completed in Batch 1

### Runtime Abstraction (`agent-os`)
- [x] Add runtime provider base interface and provider package.
- [x] Add `agent_os_python` runtime provider (legacy-compatible behavior).
- [x] Add `zeroclaw` runtime provider (health-probe integration mode).
- [x] Add runtime registry with config-driven provider resolution and fallback.
- [x] Refactor `AgentRuntime` to dispatch via runtime registry.
- [x] Extend route contract with runtime fields.
- [x] Extend `swarmctl route/run` with runtime provider/profile overrides.
- [x] Add runtime decision fields to route context and outputs.

### Config and Contracts
- [x] Add `configs/tooling/runtime_providers.json`.
- [x] Add `configs/tooling/zeroclaw_profiles.json`.
- [x] Extend `configs/tooling/integration_contracts.json` with `RuntimeProvider` contract.
- [x] Register `zeroclaw` in `configs/tooling/optional_adapters.json`.

### Zera Persona and Skills
- [x] Normalize persona into `configs/personas/zera/*`.
- [x] Add mode router config `configs/tooling/zera_mode_router.json`.
- [x] Add Zera skill pack `configs/skills/zera-*`.
- [x] Add dedicated active-set file `configs/skills/ZERA_ACTIVE_SKILLS.md`.

### Verification
- [x] Add tests:
  - `test_runtime_registry.py`
  - `test_agent_runtime_dispatch.py`
  - `test_persona_mode_router.py`
  - `test_swarmctl_runtime_routing.py`
- [x] Run targeted test suite successfully.
- [x] Validate JSON configs.
- [x] Validate `swarmctl route/run` runtime output paths manually.

## Pending from Full Plan

### Runtime/Execution
- [ ] Wire ZeroClaw provider from health-probe mode to real execution command profile.
- [ ] Add profile-level tool/memory bridge wiring for end-to-end ZeroClaw execution.
- [ ] Add provider-level telemetry metrics (fallback rate, provider latency percentiles).

### Telegram + Edge
- [ ] Add production-grade edge deployment assets (systemd/Docker templates).
- [ ] Add Telegram channel end-to-end integration tests with runtime assertions.

### Persona Governance
- [ ] Add automated eval harness for `configs/personas/zera/eval_cases.json`.
- [ ] Add persona release workflow (`zera-v1.x` gating and rollback).

### Rollout
- [ ] Add staged rollout checklist and rollback toggles to release checklist docs.
- [ ] Add KPI dashboard slices for runtime provider distribution and safety eval pass rates.
