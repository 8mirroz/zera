# 05. Hermes Runtime Audit

## Where Real Planning Happens
- Command classification and degrade paths: `ZeraCommandOS.resolve_command()`.
- Provider choice: `RuntimeRegistry.resolve()`.
- Workflow context selection: `RegistryWorkflowResolver`, not `WorkflowRouter`.
- L1 prompt shaping: `ProfileManager.get_summary_context()` injected in `AgentRuntime.run()`.

## Where Silent Degradation Starts
- `RuntimeRegistry.resolve()` can choose a provider that later fails during `get_provider()` or execution.
- `agent_runtime.py` emits `runtime_provider_selected` before provider instantiation.
- On fallback to `agent_os_python`, run still ends with `agent_run_completed` and `verification_result.status=ok` though verification never ran.

## Decision Map
- `zera:*` request -> resolve command -> enrich route -> resolve provider/profile -> emit runtime selection -> run provider -> optionally enqueue background jobs.
- For `T7`, config tries to prefer `zeroclaw`; if unavailable or blocked, system falls back.
- Source-tier policy can block capability promotion and constrain provider/profile.

## Fallback Map
- Command fallback: `zera:research -> zera:critic`, `zera:architect -> zera:plan`, etc.

## Deepened Findings (Phase 5+)

### Provider Lifecycle — No State Machine
`RuntimeRegistry.get_provider()` performs lazy instantiation:
```
config exists → is_enabled() → _builtin_factories[name] → instantiate → cache
```
There is no state machine. No `initializing`, `healthy`, `degraded`, `unhealthy`, `recovering`, or `draining` states. A provider is either "not yet instantiated" or "instantiated." No health checking occurs after instantiation.

### Pre-flight Catalog Update — Silent Failure Point
`AgentRuntime.run()` lines 1-8:
```python
try:
    cataloger_path = self.repo_root / "scripts/re_catalog.py"
    if cataloger_path.exists():
        subprocess.run(["python3", str(cataloger_path)], capture_output=True, check=False)
except Exception: pass
```
This executes a Python script before every run. Any failure is silently swallowed. No telemetry is emitted. The catalog update could fail, corrupt data, or hang indefinitely — the runtime would proceed regardless.

### Profile Context Injection — Blind String Concatenation
```python
profile_ctx = pm.get_summary_context() + "\n"
agent_input = replace(agent_input, objective=profile_ctx + agent_input.objective)
```
The profile context is prepended to the user's objective with no separator, no schema, no validation. This means:
- The profile text becomes part of the routing input
- It influences mode selection (keyword matching on the combined string)
- It affects tool eligibility decisions
- The user cannot see or debug what was injected
- No telemetry event records what was injected

### ZeraCommandOS — Scope Creep
`ZeraCommandOS` is a 400+ line class that handles:
1. Command registry resolution
2. Client profile validation
3. Capability matching
4. Branch manifest creation
5. Source card creation
6. Branch merge records
7. Personality governor evaluation
8. Import activation validation

This is a God object. The command resolution, branch management, and governance concerns should be separate modules. The `evaluate_governor()` method is never called by `agent_runtime.py` but represents a complete personality governance system.

### Autonomy Boundary — Metadata, Not Gate
`agent_runtime.py` reads `autonomy_level` from the provider config, places it in `route_decision`, and emits it as telemetry. But it never checks:
- Whether the requested action is within the autonomy level
- Whether approval gates should block execution
- Whether the task exceeds `max_actions` or `cost_budget_usd`

The autonomy boundary is observable but not enforceable.

### Telemetry Completeness — Gaps
Missing telemetry events:
- `preflight_catalog_update` (silent fail)
- `profile_context_injected` (what was added to objective)
- `registry_workflow_missing` (silent None return)
- `persona_docs_loaded` (proof persona content reached LLM)
- `autonomy_gate_blocked` (never fires because gate doesn't exist)
- `memory_write_blocked` (never fires because policy not enforced)
- `context_budget_exceeded` (no budget tracker)
- `provider_health_check` (no health checking)
- `tone_violation` (no tone detector)
- `sycophancy_detected` (no sycophancy detector)

Present but misleading events:
- `runtime_provider_selected` with `status=ok` emitted before execution
- `verification_result` with `status=ok` when `verification_status=not-run`
- Runtime fallback: declared in `runtime_providers.json`; observed 37 `runtime_provider_fallback` events in trace.
- Recovery instrumentation exists, but benchmark failure taxonomy still collapses many failures to `unknown`.

## Autonomy Boundary Map
- Declarative autonomy: `autonomy_policy.yaml`, `background_jobs.yaml`, `zeroclaw_profiles.json`.
- Reachable autonomy: primarily `zeroclaw` path only.
- Default `agent_os_python` path offers almost no real autonomy, tool execution, or verification.

## Invisible Failure Report
- Provider success is overstated because selection is logged earlier than provider readiness.
- Verification layer is overstated because `not-run` is wrapped as `status=ok`.
- Hermes adapter docs overstate available workspace/tool fidelity relative to current reachable path.

## Verdict
- Hermes runtime is **workable as a dispatcher and contract carrier**, but **not production-grade as a reliable execution engine** in its default path.
