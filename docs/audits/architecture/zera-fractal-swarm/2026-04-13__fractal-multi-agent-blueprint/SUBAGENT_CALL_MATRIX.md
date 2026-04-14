# Subagent Call Matrix — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** Where delegation (spawn/wait/send) exists or is simulated in the current codebase  

---

## 1. Finding: No True Subagent Spawning

**Critical finding:** The current codebase does **not** implement true subagent spawning with independent execution contexts.

What is called "swarm" or "multi-agent" is actually:
- **Sequential workflow stages** with different role prompts
- **Iterative refinement loops** (RALPH) that re-run the same model with feedback
- **Role contracts** that define responsibilities but don't create separate execution contexts

There is **no** `spawn_agent()`, `wait_for_subagent()`, or `send_to_subagent()` in the codebase.

---

## 2. Delegation Patterns Found

### 2.1 RALPH Loop — Iterative Refinement (Simulated Multi-Agent)

| Aspect | Detail |
|--------|--------|
| **Location** | `agent_os/ralph_loop.py` |
| **Pattern** | Iteration → Score → Iterate (up to N times) |
| **Delegation** | Same model, different prompts (each iteration includes previous best + feedback) |
| **Parallel?** | No — sequential iterations |
| **Independent?** | No — each iteration depends on previous output |
| **Config** | `router.yaml → ralph_loop: {enabled, iterations, scoring_threshold}` |
| **Events** | `ralph_iteration_started`, `ralph_iteration_scored`, `ralph_stop_decision`, `ralph_best_selected` |

**Assessment:** This is **single-agent self-refinement**, not multi-agent delegation.

### 2.2 Workflow Paths — Sequential Role Handoff

| Workflow | Path | Stages |
|----------|------|--------|
| path-fast | `configs/registry/workflows/path-fast.yaml` | Single agent, fast path |
| path-quality | `configs/registry/workflows/path-quality.yaml` | Agent → Reviewer → (RALPH) |
| path-swarm | `configs/registry/workflows/path-swarm.yaml` | Architect → Engineer → Reviewer (sequential) |

**Assessment:** "Swarm" workflow is **sequential role handoff**, not parallel agent execution. Each role is a different prompt/configuration applied to the same execution context.

### 2.3 Zera Command OS — Command Resolution

| Aspect | Detail |
|--------|--------|
| **Location** | `agent_os/zera_command_os.py` |
| **Pattern** | Command catalog → resolve → render → execute |
| **Delegation** | Commands map to different modes/workflows, but all execute through the same pipeline |
| **Parallel?** | No |

### 2.4 Persona Mode Router — Mode Switching

| Aspect | Detail |
|--------|--------|
| **Location** | `agent_os/persona_mode_router.py` |
| **Pattern** | Task context → mode binding (research/execute/review/etc.) |
| **Delegation** | Mode changes the prompt/context, not the execution agent |
| **Parallel?** | No |

### 2.5 Background Scheduler — Job Queue

| Aspect | Detail |
|--------|--------|
| **Location** | `agent_os/background_scheduler.py`, `agent_os/background_jobs.py` |
| **Pattern** | Job queue → sequential execution |
| **Delegation** | Jobs are executed one at a time by the scheduler |
| **Parallel?** | `runtimes.yaml` declares `max_parallel_tasks: 2-3`, but scheduler is sequential |
| **State** | `.agent/runtime/background-jobs.json` |

### 2.6 Evolution Loop — Self-Improvement Pipeline

| Aspect | Detail |
|--------|--------|
| **Location** | `scripts/internal/self_evolution_loop.py` |
| **Pattern** | 10-phase sequential pipeline: observe → classify → score → promote → evolve → evaluate → reflect → ... |
| **Delegation** | All phases run in the same process; no agent spawning |
| **Parallel?** | No — phases are sequential |

### 2.7 Eggent System — Algorithm Selection

| Aspect | Detail |
|--------|--------|
| **Location** | `agent_os/eggent_*.py` (8 modules) |
| **Pattern** | Task type → algorithm selection → gate evaluation → promotion |
| **Delegation** | Algorithm selection determines scoring method, not agent spawning |
| **Modules** | algorithm, contracts, design_guard, escalation, profile_loader, router_adapter |

---

## 3. Subagent Simulation Matrix

| "Agent" Role | Actual Implementation | Execution Context | Independence |
|--------------|----------------------|-------------------|--------------|
| Architect | Model alias `$MODEL_ARCHITECT_PRIMARY` (deepseek-r1) | Same LLM call, different prompt | ❌ Prompt-level only |
| Engineer | Model alias `$MODEL_ENGINEER_PRIMARY` (deepseek-v3) | Same LLM call, different prompt | ❌ Prompt-level only |
| Reviewer | Model alias `$MODEL_REVIEWER_PRIMARY` | Same LLM call, different prompt | ❌ Prompt-level only |
| Council | `$MODEL_ARCHITECT_PRIMARY` with council prompt | Same LLM call, council prompt | ❌ Prompt-level only |
| RALPH iterations | Same model, N iterations | Sequential iterations | ❌ Dependent on previous |
| Background jobs | Sequential job queue | Single scheduler process | ❌ Sequential |

---

## 4. Skills That Imply Multi-Agent (But Don't Implement It)

| Skill | File | Implies | Actually Does |
|-------|------|---------|---------------|
| `dispatching-parallel-agents` | `.agent/skills/dispatching-parallel-agents/SKILL.md` | Parallel agent dispatch | Provides procedural knowledge for manual dispatch — not automated |
| `subagent-driven-development` | `.agent/skills/subagent-driven-development/SKILL.md` | Subagent spawning | Provides prompt templates for subagent simulation via LLM — not code-level spawning |
| `brainstorming` | `.agent/skills/brainstorming/SKILL.md` | Multiple perspectives | Single-agent exploration pattern |

---

## 5. Parallel Execution Infrastructure — Status

| Component | Exists? | Functional? | Notes |
|-----------|---------|-------------|-------|
| `agent_os/swarm/branch_lock.py` | ✅ Yes | ⚠️ Partial | Detects collisions, but no enforcement mechanism |
| `agent_os/swarm/lane_events.py` | ✅ Yes | ⚠️ Partial | Lane-scoped events, but no lane isolation |
| `runtime_providers` max_parallel_tasks | ✅ Yes (config) | ⚠️ Partial | Configured but not enforced by scheduler |
| True parallel subprocess execution | ❌ No | N/A | No `spawn_agent()` or equivalent |
| Distributed task queue | ❌ No | N/A | No Celery/RQ/Redis queue |
| Lease-based task claiming | ❌ No | N/A | No lease mechanism |
| Heartbeat monitoring | ❌ No | N/A | No agent liveness checks |

---

## 6. Agents Registry vs Real Parallelism

| Aspect | Registry Definition | Reality |
|--------|--------------------|---------|
| Agent roles | 7 roles defined in `configs/orchestrator/role_contracts/` (referenced, directory missing) | Roles are prompt-level bindings, not execution contexts |
| Swarm workflow | `path-swarm.yaml` defines multi-role workflow | Sequential role handoff, not parallel |
| RALPH loop | Iterative refinement with scoring | Sequential single-agent self-refinement |
| Background jobs | Job queue with max_parallel_tasks | Sequential execution |
| Evolution loop | Multi-phase self-improvement | Sequential pipeline |

**Conclusion:** The agents registry defines **roles and responsibilities**, but the runtime executes them **sequentially** in a single process. True parallel multi-agent execution requires:
1. Independent execution contexts (processes/threads)
2. Task claiming with leases
3. Inter-agent communication channels
4. Merge/convergence logic

None of these are currently implemented.

---

## 7. Recommendations for True Multi-Agent

| Capability | Current State | Required Implementation |
|------------|--------------|------------------------|
| Parallel execution | ❌ Not implemented | Process pool / async task queue |
| Task claiming | ❌ Not implemented | Lease + heartbeat mechanism |
| Inter-agent communication | ❌ Not implemented | Message queue / event bus |
| Result merging | ❌ Not implemented | Merge function with conflict resolution |
| Independent agent state | ❌ Not implemented | Per-agent memory/trace isolation |
| Fault tolerance | ❌ Not implemented | Agent timeout, retry, fallback |
| Agent registry at runtime | ⚠️ YAML definitions | Runtime agent instance management |
