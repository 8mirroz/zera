# Fractal Decomposition Model — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Status:** Target design (not current implementation)  
> **Principle:** Deterministic decomposition via rule-set + schema validation  

---

## 1. Decomposition Levels

The fractal model defines **6 levels** of task decomposition, each with explicit entry/exit criteria:

```
Level 0: MISSION
       ↓  (mission → program decomposition rules)
Level 1: PROGRAM
       ↓  (program → workflow decomposition rules)
Level 2: WORKFLOW
       ↓  (workflow → task decomposition rules)
Level 3: TASK
       ↓  (task → subtask decomposition rules)
Level 4: SUBTASK
       ↓  (subtask → atomic action rules)
Level 5: ATOMIC ACTION
       ↓  (executed against tool/runtime)
```

---

## 2. Level Definitions

### Level 0: MISSION

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Top-level goal — the "why" behind all work |
| **Input** | Natural language goal from user |
| **Output** | 1+ Programs with success criteria |
| **Duration** | Days to weeks |
| **Example** | "Build a multi-agent autonomous development platform" |
| **Decomposition rule** | Mission → Programs by functional domain |

**Mission → Program decomposition rules:**
1. If mission spans multiple functional domains → create one Program per domain
2. If mission has temporal phases (setup → build → operate) → create one Program per phase
3. If mission is single-domain → 1 Program = Mission

### Level 1: PROGRAM

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Functional domain or phase within a Mission |
| **Input** | Mission definition |
| **Output** | 1+ Workflows with dependencies |
| **Duration** | Hours to days |
| **Example** | "Implement routing system v4.2" (Program under Mission "Build platform") |
| **Decomposition rule** | Program → Workflows by execution phase |

**Program → Workflow decomposition rules:**
1. If program requires sequential phases → create ordered Workflow chain
2. If program has parallel workstreams → create parallel Workflows with merge point
3. If program is single-workflow → 1 Workflow = Program

### Level 2: WORKFLOW

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Executable pipeline within a Program |
| **Input** | Program definition |
| **Output** | 1+ Tasks with dependencies and handoff contracts |
| **Duration** | Minutes to hours |
| **Example** | "path-swarm" workflow (Architect → Engineer → Reviewer) |
| **Decomposition rule** | Workflow → Tasks by role/stage |

**Workflow → Task decomposition rules:**
1. Each workflow stage → 1 Task
2. If stage requires iteration (e.g., RALPH) → 1 Task with loop metadata
3. If stage requires approval → 1 Task with approval gate

### Level 3: TASK

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Unit of work assignable to an agent |
| **Input** | Workflow stage definition |
| **Output** | 1+ Subtasks or a single Atomic Action |
| **Duration** | Seconds to minutes |
| **Example** | "Implement model selection logic" (Task within routing workflow) |
| **Decomposition rule** | Task → Subtasks if complexity > threshold |

**Task → Subtask decomposition rules:**
1. If task requires >3 distinct operations → decompose into Subtasks
2. If task touches >2 code modules → decompose into Subtasks
3. If task has dependencies on other tasks → create Subtasks per dependency
4. If task is simple → 1 Atomic Action = Task

### Level 4: SUBTASK

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Granular unit of work within a Task |
| **Input** | Task definition |
| **Output** | 1+ Atomic Actions |
| **Duration** | Seconds |
| **Example** | "Write test for model selection" (Subtask of "Implement model selection") |
| **Decomposition rule** | Subtask → Atomic Actions by operation type |

**Subtask → Atomic Action decomposition rules:**
1. Each distinct operation (read/write/call/validate) → 1 Atomic Action
2. Each tool invocation → 1 Atomic Action
3. Each file modification → 1 Atomic Action (read → modify → write = 3 actions)

### Level 5: ATOMIC ACTION

| Aspect | Definition |
|--------|-----------|
| **Purpose** | Smallest executable unit |
| **Input** | Subtask definition |
| **Output** | Result (success/failure with evidence) |
| **Duration** | Milliseconds to seconds |
| **Example** | "Read file configs/orchestrator/router.yaml" |
| **Decomposition rule** | NONE — atomic actions are leaf nodes |

---

## 3. Decomposition Algorithm (Deterministic)

```
function decompose(entity: Mission|Program|Workflow|Task|Subtask) -> [Children]:
    1. Load decomposition rules for entity.level
    2. For each applicable rule:
       a. Evaluate rule condition against entity properties
       b. If condition matches → create child entity
       c. Set child.parent_id = entity.id
       d. Set child.dependencies from rule
    3. Validate all children against TaskContractSchema
    4. If validation fails → escalate to parent level (stop decomposition)
    5. Return [children]
```

**Determinism guarantees:**
- Same entity properties → same decomposition
- Rule evaluation order is fixed (priority-based)
- Schema validation is deterministic
- No LLM involvement in decomposition — pure rule-based

---

## 4. Stop / Merge / Escalate Rules

### Stop Rules

| Condition | Action | Level |
|-----------|--------|-------|
| Decomposition produces 1 child | Stop — child = entity (no further decomposition needed) | Any |
| Schema validation fails | Stop — escalate to parent for manual review | Any |
| Resource budget exceeded | Stop — emit `budget_exceeded` event | Any |
| Max depth reached (level 5) | Stop — atomic action must execute | Level 5 |
| Stop signal detected | Stop — emit `stop_signal_received` event | Any |
| Parent task failed | Stop — child tasks marked `blocked` | Any |

### Merge Rules

| Condition | Merge Strategy | Responsible |
|-----------|---------------|-------------|
| All parallel subtasks completed | Merge outputs by dependency order | Task owner |
| Subtask failed, retry exhausted | Merge with error marker; escalate | Task owner |
| Conflicting outputs | Conflict resolution via owner authority | Task owner (highest authority) |
| Partial completion | Merge completed; mark incomplete | Task owner |

### Escalate Rules

| Condition | Escalate To | Trigger |
|-----------|------------|---------|
| Schema validation fails | Parent level (human or supervisor) | Immediate |
| Resource budget exceeded | Program owner | Immediate |
| Stop signal detected | Mission owner | Immediate |
| Repeated failures (N > 3) | Next level up | After N retries |
| Conflict unresolvable | Council review (C5 only) | After conflict detection |

---

## 5. Fractal Property: Self-Similarity

Each level has the **same contract shape**:

```
Entity {
    id: string
    parent_id: string | null
    level: 0|1|2|3|4|5
    objective: string
    inputs: [ArtifactRef]
    constraints: [Constraint]
    dependencies: [EntityId]
    expected_outputs: [ArtifactRef]
    validation: ValidationRule
    state: StateMachineValue
    evidence: [EvidenceRecord]
    artifact_refs: [ArtifactRef]
}
```

This means:
- A Mission can be treated as a Task at a higher level
- An Atomic Action can be promoted to a Task if complexity grows
- The same state machine applies at all levels

---

## 6. Current vs Target Decomposition

| Level | Current State | Target State |
|-------|--------------|--------------|
| Mission | ❌ Not modeled | ✅ Mission entity with program decomposition |
| Program | ❌ Not modeled | ✅ Program entity with workflow decomposition |
| Workflow | ⚠️ YAML definitions only | ✅ Workflow entity with task decomposition |
| Task | ⚠️ Implicit in prompts | ✅ Task entity with subtask decomposition |
| Subtask | ❌ Not modeled | ✅ Subtask entity with atomic action decomposition |
| Atomic Action | ⚠️ Tool calls in traces | ✅ Atomic Action entity with result evidence |
