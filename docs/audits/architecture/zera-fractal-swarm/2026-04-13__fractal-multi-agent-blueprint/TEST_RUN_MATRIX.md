# Test Run Matrix — Wave 6

> **Wave:** 6 — Testing / Evals / Chaos / Benchmarking
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–5
> **Aligned with:** BENCHMARK_SUITE_SPEC.md, EVAL_METRICS_AND_THRESHOLDS.md, FAILURE_INJECTION_PLAN.md, Execution State Machine, Trace Schema v2.1

---

## 1. Scope

This document defines the complete test run matrix for the Zera fractal multi-agent architecture. It maps test categories against subsystems and tiers, specifies execution frequency, current vs target coverage, identifies known gaps, and assigns test ownership.

---

## 2. Test Categories

### 2.1 Category Definitions

| Category | ID | Description | Scope | Granularity |
|----------|----|-------------|-------|-------------|
| **Unit** | `TEST-UNIT` | Test individual functions/classes in isolation | Single module | Function/method |
| **Integration** | `TEST-INT` | Test interaction between 2+ modules | Module boundary | Subsystem |
| **End-to-End** | `TEST-E2E` | Test full run from task submission to completion | Full system | Run/Wave/Workflow |
| **Chaos** | `TEST-CHAOS` | Test failure injection and recovery | Failure scenarios | Specific failure type |
| **Benchmark** | `TEST-BENCH` | Test performance against thresholds | Performance metrics | Metric × category |
| **Regression** | `TEST-REG` | Test that previously fixed bugs don't reappear | Known failure modes | Bug/issue |

### 2.2 Category Characteristics

| Category | Execution Time | Environment | Parallelizable | Data Dependency |
|----------|---------------|-------------|----------------|-----------------|
| Unit | < 1s per test | Any (no deps) | Yes | None (mocked) |
| Integration | < 30s per test | Local or CI | Partially | Fixtures |
| End-to-End | 1-10 min per test | Staging-like | No | Real traces or generated |
| Chaos | 1-5 min per injection | Staging (isolated) | No | Running system |
| Benchmark | 5-30 min per suite | Staging | Partially | Benchmark datasets |
| Regression | < 30s per test | CI | Yes | Historical traces |

---

## 3. Test × Subsystem × Tier Matrix

### 3.1 Routing Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_model_router.py` | Model routing logic | Unit | C1-C5 | ✅ Exists | CI |
| `test_routing.py` | Core routing decisions | Unit | C1-C5 | ✅ Exists | CI |
| `test_routing_vector.py` | Vector-based routing | Unit | C1-C5 | ✅ Exists | CI |
| `test_phase_aware_c1_c2.py` | Phase-aware routing | Integration | C1, C2 | ✅ Exists | CI |
| `test_router_baseline.py` | Baseline regression | Integration | C1-C5 | ✅ Exists | Nightly |
| `test_persona_mode_router.py` | Persona-mode routing | Unit | C1-C5 | ✅ Exists | CI |
| `test_swarmctl_runtime_routing.py` | Runtime routing | Integration | C1-C5 | ✅ Exists | CI |
| `RT-001` to `RT-012` | Routing benchmark suite | Benchmark | C1-C5 | ❌ Gap (need new) | Nightly |

**Coverage:** 7/7 test types exist. Benchmark cases need creation.

### 3.2 Execution Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_agent_runtime_dispatch.py` | Runtime dispatch | Unit | C1-C5 | ✅ Exists | CI |
| `test_recovery_state_machine.py` | Recovery state machine | Unit | All | ✅ Exists | CI |
| `test_recovery.py` | Recovery logic | Unit | All | ✅ Exists | CI |
| `test_swarmctl_run_integration.py` | Run integration | Integration | C1-C5 | ✅ Exists | CI |
| `test_stop_controller.py` | Stop signal handling | Unit | All | ✅ Exists | CI |
| `test_approval_engine.py` | Approval gates | Unit | C4, C5 | ✅ Exists | CI |
| `test_autonomy_policy.py` | Autonomy policy | Unit | C1-C5 | ✅ Exists | CI |
| `EX-001` to `EX-012` | Execution benchmark suite | Benchmark | C1-C5 | ❌ Gap (need new) | Nightly |
| `INFRA-004`, `STATE-001` | Worker crash / lease expiry | Chaos | C1-C5 | ❌ Gap (need new) | Weekly |
| Full task lifecycle (queued→completed) | E2E task execution | E2E | C1-C5 | ❌ Gap (need new) | Nightly |

**Coverage:** 7 unit/integration tests exist. 14 benchmarks, chaos, and E2E tests needed.

### 3.3 Memory Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_memory.py` | Core memory operations | Unit | All | ✅ Exists | CI |
| `test_memory_retriever.py` | Memory retrieval | Unit | All | ✅ Exists | CI |
| `test_memory_store_jsonl.py` | JSONL store | Unit | All | ✅ Exists | CI |
| `test_memory_store_memu_cloud.py` | Memu cloud store | Unit | All | ✅ Exists | CI |
| `test_layered_memory_retriever.py` | Layered retrieval | Integration | All | ✅ Exists | CI |
| `test_memory_policy_layer.py` | Memory policy | Unit | All | ✅ Exists | CI |
| `test_memory_query_adapter.py` | Query adapter | Unit | All | ✅ Exists | CI |
| `test_build_memory_auto_ingest.py` | Auto-ingest | Integration | All | ✅ Exists | CI |
| `test_smart_skill_matching_trace.py` | Skill matching trace | Integration | All | ✅ Exists | CI |
| `MEM-001` to `MEM-010` | Memory benchmark suite | Benchmark | All | ❌ Gap (need new) | Nightly |

**Coverage:** 9 unit/integration tests exist. 10 benchmark tests needed.

### 3.4 Observability Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_observability_trace_v2.py` | v2 trace validation | Unit | All | ✅ Exists | CI |
| `test_trace_schema_mirror.py` | Schema mirror | Unit | All | ✅ Exists | CI |
| `test_trace_validator.py` | Trace validator | Unit | All | ✅ Exists | CI |
| `test_trace_metrics_materializer.py` | Metrics materializer | Unit | All | ✅ Exists | CI |
| `test_trace_metrics_primary_sources.py` | Primary sources | Unit | All | ✅ Exists | CI |
| `test_swarmctl_trace_coverage.py` | Trace coverage audit | Integration | All | ✅ Exists | Nightly |
| `OBS-001` to `OBS-010` | Observability benchmark suite | Benchmark | All | ❌ Gap (need new) | Nightly |
| Full trace completeness test | E2E trace completeness | E2E | C1-C5 | ❌ Gap (need new) | Nightly |

**Coverage:** 6 unit/integration tests exist. 10 benchmarks + E2E tests needed.

### 3.5 Coordination Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_swarm_contracts.py` | Swarm contracts | Unit | C4, C5 | ✅ Exists | CI |
| `test_swarmctl_swarm.py` | Swarm orchestration | Integration | C4, C5 | ✅ Exists | CI |
| `test_swarmctl_algorithm.py` | Algorithm selection | Unit | C1-C5 | ✅ Exists | CI |
| `test_ralph_loop.py` | Ralph loop | Integration | C3-C5 | ✅ Exists | Nightly |
| `test_registry_swarm_recovery.py` | Swarm recovery | Integration | C4, C5 | ✅ Exists | CI |
| `test_eggent_escalation.py` | Escalation handling | Unit | C4, C5 | ✅ Exists | CI |
| `test_eggent_router_adapter.py` | Router adapter | Unit | C1-C5 | ✅ Exists | CI |
| `COORD-001` to `COORD-010` | Coordination benchmark suite | Benchmark | C1-C5 | ❌ Gap (need new) | Nightly |
| Dependency chain E2E test | E2E dependency resolution | E2E | C3-C5 | ❌ Gap (need new) | Nightly |
| `COORD-001` | Deadlock injection | Chaos | C3-C5 | ❌ Gap (need new) | Monthly |

**Coverage:** 7 unit/integration tests exist. 10 benchmarks + E2E + chaos tests needed.

### 3.6 Cost Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_contracts.py` | Contract validation (includes token fields) | Unit | C1-C5 | ✅ Exists | CI |
| `test_swarmctl_benchmark.py` | Swarm benchmark | Integration | C1-C5 | ✅ Exists | Nightly |
| `test_analyze_benchmark.py` | Benchmark analysis | Unit | All | ✅ Exists | CI |
| `COST-001` to `COST-010` | Cost benchmark suite | Benchmark | C1-C5 | ❌ Gap (need new) | Nightly |

**Coverage:** 3 unit/integration tests exist. 10 benchmark tests needed.

### 3.7 Persona Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_persona_eval.py` | Persona evaluation | Unit | All | ✅ Exists | Nightly |
| `test_zera_persona_*` (various) | Persona behavior tests | Unit | All | ✅ Exists | CI |
| `test_zera_hardening_assets.py` | Hardening assets | Unit | All | ✅ Exists | CI |
| `test_zera_hybrid_pilot_contracts.py` | Hybrid pilot contracts | Unit | All | ✅ Exists | CI |
| `test_zera_hybrid_pilot_runtime_telemetry.py` | Runtime telemetry | Unit | All | ✅ Exists | CI |
| `test_zera_runtime_parity.py` | Runtime parity | Integration | All | ✅ Exists | CI |
| `test_zera_client_profile_validation.py` | Profile validation | Unit | All | ✅ Exists | CI |
| Persona eval suite (4 cases) | Persona eval scenarios | Integration | All | ✅ Exists | Nightly |

**Coverage:** 8 tests exist + persona eval suite. No gaps.

### 3.8 Quality Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_swarmctl_approval_and_stop.py` | Approval + stop | Integration | C4, C5 | ✅ Exists | CI |
| `test_swarmctl_background_controls.py` | Background controls | Integration | All | ✅ Exists | CI |
| `test_swarmctl_background_daemon.py` | Background daemon | Integration | All | ✅ Exists | CI |
| `test_swarmctl_background_status.py` | Background status | Integration | All | ✅ Exists | CI |
| `test_background_job_planner.py` | Job planner | Unit | All | ✅ Exists | CI |
| `test_background_jobs.py` | Background jobs | Unit | All | ✅ Exists | CI |
| `test_background_jobs_quiet_hours.py` | Quiet hours | Unit | All | ✅ Exists | CI |
| `test_background_scheduler.py` | Background scheduler | Unit | All | ✅ Exists | CI |
| `test_reliability_platform_assets.py` | Reliability platform | Integration | All | ✅ Exists | CI |
| `test_risk_and_observability.py` | Risk + observability | Integration | All | ✅ Exists | CI |
| `test_kill_switch_monitor.py` | Kill switch | Unit | All | ✅ Exists | CI |
| `test_self_reflection_validation_integration.py` | Self-reflection | Integration | C3-C5 | ✅ Exists | CI |
| `test_reflection_policy.py` | Reflection policy | Unit | C3-C5 | ✅ Exists | CI |
| `test_swarmctl_governance_cli.py` | Governance CLI | Integration | All | ✅ Exists | CI |
| `test_security.py` | Security tests | Unit | All | ✅ Exists | CI |
| `test_security_policy_runtime.py` | Security policy runtime | Unit | All | ✅ Exists | CI |

**Coverage:** 16 tests exist. No gaps in unit/integration. Benchmark tests needed (aligned with QUAL metrics).

### 3.9 Plugin/Adapter Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_adapter_and_toolrunner.py` | Adapter + tool runner | Unit | All | ✅ Exists | CI |
| `test_plugin_contracts.py` | Plugin contracts | Unit | All | ✅ Exists | CI |
| `test_modular_loading.py` | Modular loading | Unit | All | ✅ Exists | CI |
| `test_tool_runner.py` | Tool runner | Unit | All | ✅ Exists | CI |
| `test_zeroclaw_exec_adapter.py` | ZeroClaw exec adapter | Unit | All | ✅ Exists | CI |
| `test_telegram_runtime_bridge.py` | Telegram bridge | Integration | All | ✅ Exists | CI |
| `test_swarmctl_telegram_readiness.py` | Telegram readiness | Integration | All | ✅ Exists | CI |
| `test_skill_orchestration.py` | Skill orchestration | Integration | All | ✅ Exists | CI |
| `test_active_set_plugin_metadata.py` | Plugin metadata | Unit | All | ✅ Exists | CI |

**Coverage:** 9 tests exist. No gaps.

### 3.10 Data/Config Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_config_validation.py` | Config validation | Unit | All | ✅ Exists | CI |
| `test_global_config_integration.py` | Global config integration | Integration | All | ✅ Exists | CI |
| `test_registry.py` | Registry | Unit | All | ✅ Exists | CI |
| `test_registry_workflows.py` | Registry workflows | Unit | All | ✅ Exists | CI |
| `test_workflows.py` | Workflows | Unit | All | ✅ Exists | CI |
| `test_workflow_router.py` | Workflow router | Unit | All | ✅ Exists | CI |
| `test_workflow_model_alias_validator.py` | Model alias validation | Unit | All | ✅ Exists | CI |
| `test_wiki_core.py` | Wiki core | Unit | All | ✅ Exists | CI |
| `test_swarmctl_wiki.py` | Swarmctl wiki | Integration | All | ✅ Exists | CI |
| `test_swarmctl_notebooklm.py` | NotebookLM | Integration | All | ✅ Exists | CI |
| `test_swarmctl_notebooklm_router.py` | NotebookLM router | Integration | All | ✅ Exists | CI |
| `test_notebooklm_doctor.py` | NotebookLM doctor | Unit | All | ✅ Exists | CI |
| `test_notebooklm_router_prompt.py` | NotebookLM router prompt | Unit | All | ✅ Exists | CI |

**Coverage:** 13 tests exist. No gaps.

### 3.11 Design System Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_design_system.py` | Design system tests | Unit | All | ✅ Exists | CI |
| `test_pinterest_integration.py` | Pinterest integration | Integration | All | ✅ Exists | CI |
| `test_import_visual_prompt_cases.py` | Visual prompt cases | Unit | All | ✅ Exists | CI |

**Coverage:** 3 tests exist. No gaps.

### 3.12 Telegram Bot/Payment Subsystem

| Test ID | Test Name | Category | Tier Coverage | Status | Execution |
|---------|-----------|----------|---------------|--------|-----------|
| `test_bot_core.py` | Bot core | Unit | All | ✅ Exists | CI |
| `test_payments_core.py` | Payments core | Unit | All | ✅ Exists | CI |

**Coverage:** 2 tests exist. No gaps.

---

## 4. Execution Frequency Matrix

### 4.1 CI (Per-PR) Tests

| Category | Test Count | Subsystems Covered | Average Duration |
|----------|-----------|--------------------|-----------------|
| Unit | ~70+ | All subsystems | < 2 minutes total |
| Integration | ~25+ | Routing, execution, memory, coordination, quality, plugins | < 5 minutes total |
| Regression | ~10+ | Known bug fixes | < 2 minutes total |
| **Total CI** | **~105+** | **All** | **< 10 minutes** |

### 4.2 Nightly Tests

| Category | Test Count | Subsystems Covered | Average Duration |
|----------|-----------|--------------------|-----------------|
| Integration (full) | ~25+ | All subsystems | ~30 minutes |
| Benchmark | 64 cases (BENCHMARK_SUITE_SPEC.md) | 6 categories | ~60 minutes |
| E2E | ~5+ (need creation) | Full system | ~30 minutes |
| Persona eval | 4 cases | Persona | ~10 minutes |
| Regression (full) | ~15+ | Historical bugs | ~15 minutes |
| **Total Nightly** | **~113+** | **All** | **~2.5 hours** |

### 4.3 Weekly Tests

| Category | Test Count | Subsystems Covered | Average Duration |
|----------|-----------|--------------------|-----------------|
| Chaos (standard) | 7 injections | Infra, state, protocol | ~2 hours |
| Benchmark (full trends) | 64 cases + trending | 6 categories | ~60 minutes |
| **Total Weekly** | **~71+** | **All + chaos** | **~3 hours** |

### 4.4 Monthly Tests

| Category | Test Count | Subsystems Covered | Average Duration |
|----------|-----------|--------------------|-----------------|
| Chaos (extended) | 8 injections | Infra, state, policy, coordination | ~3 hours |
| Pre-release gate (full) | All tests | Full system | ~4 hours |
| **Total Monthly** | **All tests** | **All** | **~4 hours** |

### 4.5 On-Demand Tests

Any test can be run on-demand via CLI:

```bash
# Run specific test
pytest repos/packages/agent-os/tests/test_model_router.py -v

# Run specific category
python3 repos/packages/agent-os/scripts/benchmark_runner.py --category routing

# Run specific chaos injection
python3 scripts/chaos/run.py --injection INFRA-004

# Run full nightly suite
make test-all

# Run pre-release gate
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all --gate pre-release
```

---

## 5. Coverage Analysis

### 5.1 Current Coverage

| Category | Tests Existing | Tests Needed | Current Coverage |
|----------|---------------|--------------|-----------------|
| Unit | ~70+ | ~70+ | **~100%** |
| Integration | ~25+ | ~25+ | **~100%** |
| End-to-End | 0 | ~8 | **0%** |
| Chaos | 0 | ~15 | **0%** |
| Benchmark | Partial (routing only) | ~64 | **~15%** |
| Regression | ~10+ | ~15+ | **~67%** |
| **Overall** | **~105+** | **~197+** | **~53%** |

### 5.2 Target Coverage (Post-Implementation)

| Category | Tests Needed | Target Coverage |
|----------|-------------|-----------------|
| Unit | ~70+ (maintain) | 100% |
| Integration | ~25+ (maintain) | 100% |
| End-to-End | ~8 (create) | 100% |
| Chaos | ~15 (create) | 100% |
| Benchmark | ~64 (create) | 100% |
| Regression | ~15+ (maintain + grow) | 100% |
| **Overall** | **~197+** | **100%** |

### 5.3 Coverage by Tier

| Tier | Unit | Integration | E2E | Chaos | Benchmark | Total |
|------|------|-------------|-----|-------|-----------|-------|
| **C1** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| **C2** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| **C3** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| **C4** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| **C5** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| **All** | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |

**Target:** All tiers: 5/5 (100%).

### 5.4 Coverage by Subsystem

| Subsystem | Unit | Integration | E2E | Chaos | Benchmark | Total |
|-----------|------|-------------|-----|-------|-----------|-------|
| Routing | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Execution | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Memory | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Observability | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Coordination | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Cost | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Persona | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |
| Quality | ✅ | ✅ | ❌ | ❌ | ❌ | 2/5 (40%) |

**Target:** All subsystems: 5/5 (100%).

---

## 6. Known Gaps

### 6.1 Critical Gaps (P0 — Must Create Before Release)

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| No E2E task lifecycle tests | Cannot verify full system works end-to-end | 2 days | P0 |
| No chaos/failure injection tests | Cannot validate fault tolerance | 3 days | P0 |
| No execution benchmarks (EX-001 to EX-012) | Cannot measure execution performance | 2 days | P0 |
| No memory benchmarks (MEM-001 to MEM-010) | Cannot measure retrieval performance | 2 days | P0 |
| No observability benchmarks (OBS-001 to OBS-010) | Cannot verify trace completeness | 2 days | P0 |
| No coordination benchmarks (COORD-001 to COORD-010) | Cannot measure dependency resolution | 2 days | P0 |
| No cost benchmarks (COST-001 to COST-010) | Cannot track cost per tier | 1 day | P0 |
| Benchmark runner CLI tool | Cannot execute benchmarks consistently | 1 day | P0 |

### 6.2 Important Gaps (P1 — Should Create Within 2 Weeks)

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| No regression tests for 4 missing benchmark cases | `bench-context-map-retrieval`, `bench-doc-staleness-detection`, `bench-harness-gardening-candidate`, `bench-worktree-validation-evidence` not covered | 1 day | P1 |
| No duplicate case detection fix | `benchmark_latest.json` shows 24 duplicate cases | 0.5 days | P1 |
| No trend data collection | Cannot measure improvement over time | 1 day | P1 |
| No chaos automation framework | Manual chaos injection only | 2 days | P1 |

### 6.3 Nice-to-Have Gaps (P2 — Backlog)

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| No property-based tests for routing | Edge cases may be missed | 1 day | P2 |
| No fuzz testing for trace schema | Malformed events not tested | 1 day | P2 |
| No performance regression alerts | Performance regressions detected late | 1 day | P2 |
| No mutation testing | Test effectiveness not measured | 2 days | P2 |
| No load testing (1000+ concurrent tasks) | System capacity unknown | 2 days | P2 |

---

## 7. Test Ownership

### 7.1 Ownership Matrix

| Subsystem | Primary Owner | Backup Owner | Reviewer |
|-----------|--------------|--------------|----------|
| Routing | Agent OS team | Router module maintainer | Architect |
| Execution | Agent OS team | Scheduler maintainer | Architect |
| Memory | Memory subsystem owner | LightRAG maintainer | Memory architect |
| Observability | Observability team | Trace collector maintainer | SRE |
| Coordination | Agent OS team | Dependency resolver maintainer | Architect |
| Cost | Agent OS team | Finance/ops | Product |
| Persona | Zera persona maintainer | Governor | Product owner |
| Quality | Quality team | Reliability engineer | Architect |
| Plugins/Adapters | Plugin team | Adapter maintainer | Senior engineer |
| Data/Config | Config team | Registry maintainer | Senior engineer |
| Design System | Design team | UI engineer | Design lead |
| Telegram Bot/Payments | Telegram team | Bot maintainer | Product |
| Benchmarks (all) | SRE/Reliability team | Each subsystem owner | Architect |
| Chaos engineering | SRE team | Infrastructure team | Architect |
| E2E tests | QA team | Each subsystem owner | Architect |
| Regression tests | Each subsystem owner | QA team | Senior engineer |

### 7.2 Ownership Responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Primary Owner** | Write, maintain, update tests. Fix test failures. Add new test cases. |
| **Backup Owner** | Step in when primary unavailable. Review test changes. |
| **Reviewer** | Approve test additions/modifications. Ensure coverage adequacy. |

### 7.3 Ownership for New Tests (Gaps)

| New Test Suite | Proposed Owner | Rationale |
|----------------|---------------|-----------|
| E2E task lifecycle tests | Agent OS team + QA | Cross-subsystem, needs system-level knowledge |
| Chaos injection tests | SRE team | Failure injection is core SRE responsibility |
| Benchmark scripts (all 6 categories) | SRE/Reliability team | Performance testing is SRE domain |
| Benchmark runner CLI | SRE team | Tooling for benchmark execution |
| Regression tests (4 missing cases) | Original test authors + QA | Domain-specific knowledge required |
| Trend data collection | Observability team | Metrics infrastructure |
| Chaos automation framework | SRE team | Automation of chaos engineering |

---

## 8. Test Execution Commands

### 8.1 Quick Reference

```bash
# Run all unit tests (CI gate)
cd repos/packages/agent-os && pytest tests/ -v --tb=short -x

# Run all integration tests
cd repos/packages/agent-os && pytest tests/integration/ -v --tb=short

# Run full test suite (nightly)
make test-all

# Run benchmark suite
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all

# Run specific benchmark category
python3 repos/packages/agent-os/scripts/benchmark_runner.py --category routing

# Run chaos injection
python3 scripts/chaos/run.py --injection INFRA-004 --duration 30

# Run pre-release gate
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all --gate pre-release

# Generate coverage report
cd repos/packages/agent-os && pytest tests/ --cov=agent_os --cov-report=html

# Check test coverage by tier
python3 scripts/validation/test_coverage_by_tier.py
```

### 8.2 CI Pipeline (`.github/workflows/test.yml`)

```yaml
name: Test
on: [pull_request, push]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest repos/packages/agent-os/tests/ -v --tb=short -x

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest repos/packages/agent-os/tests/integration/ -v

  benchmark-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 repos/packages/agent-os/scripts/benchmark_runner.py --category routing --gate ci

  schema-conformance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest repos/packages/agent-os/tests/test_trace_schema_mirror.py -v
```

---

## 9. Summary

### 9.1 Current State

| Metric | Value |
|--------|-------|
| Total test files | 101 |
| Test files (agent-os) | 96 |
| Test files (design-system) | 2 |
| Test files (telegram) | 2 |
| Test files (scripts) | 2 |
| Categories covered (of 6) | Unit ✅, Integration ✅, E2E ❌, Chaos ❌, Benchmark ❌, Regression ✅ |
| Estimated coverage | ~53% |
| Benchmark suite status | **FAIL** (score=0.667) |
| Known gaps | 8 critical (P0), 4 important (P1), 5 backlog (P2) |

### 9.2 Target State

| Metric | Target |
|--------|--------|
| Total test files | ~197+ |
| Categories covered | All 6 at 100% |
| Estimated coverage | 100% |
| Benchmark suite status | PASS (score≥0.7, pass_rate≥0.8) |
| Known gaps | 0 |

### 9.3 Implementation Priority

1. **Create benchmark runner CLI** (1 day) — enables all benchmark creation
2. **Create E2E task lifecycle tests** (2 days) — validates full system
3. **Create 64 benchmark cases** across 6 categories (10 days total, parallelizable)
4. **Create 15 chaos injection tests** (3 days) — validates fault tolerance
5. **Create regression tests for 4 missing cases** (1 day) — closes benchmark gaps
6. **Implement trend data collection** (1 day) — enables longitudinal tracking
7. **Create chaos automation framework** (2 days) — enables weekly/monthly chaos

**Total effort: ~20 person-days** (can be parallelized across team, actual calendar time ~5-7 days with 3-4 engineers).
