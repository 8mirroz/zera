# Execution Truth Contract

**Version:** 1.0.0  
**Status:** ACTIVE — Enforced by Runtime Guards  
**Applies to:** All agents (Hermes profiles, Zera, CLI tools, workflow executors)  
**Enforcement:** `guards.forbid_unverified_completion_claims: true`

---

## Zero Law: No Narrative Without Evidence

```
claim ≠ completion
narration ≠ execution
intention ≠ action
```

An agent must **never** claim that an action has been completed unless:
1. A tool/action was **actually executed**,
2. The result was **observed and captured**,
3. The state change was **verified** (existence, content, or side-effect).

---

## Prohibited Patterns

These patterns are **hard violations**. Any agent producing these without immediate evidence has failed the task.

| Pattern | Example | Why It's Wrong |
|---------|---------|----------------|
| Declarative creation | "Created `src/config/`" | No tool output confirming existence |
| Action narration | "Now I'll create the files..." | Narration ≠ execution |
| Fake progress | "Step 3 of 7 complete" | No verified state change |
| Premature done | "Done! All files created." | No artifact list, no verification |
| Silent tool call | Tool called, result not shown | User cannot verify outcome |
| Hidden failures | "Something went wrong" | No error details, no recovery plan |

---

## Required Format: Evidence Block

After **any** action claim, the agent MUST include an evidence block:

````markdown
### Step: Create project directories

**Action:** Executed `mkdir -p` for 6 directories

**Evidence:**
```bash
$ find /path/to/project -maxdepth 2 -type d | sort
/path/to/project/
├── src/
├── configs/
├── data/
├── tests/
├── tools/
└── docs/
```

**Verification:** All 6 directories exist and are empty (expected state).

**Artifacts:** 6 directories created at `/path/to/project/`
````

### Minimum Evidence Requirements by Action Type

| Action | Required Evidence |
|--------|------------------|
| File/directory created | Path exists (`test -f` / `ls` / `find`) |
| File modified | Diff or content excerpt |
| Code executed | stdout/stderr output |
| Test run | Pass/fail count + summary |
| API call | Response status + key fields |
| Config changed | Before/after comparison |
| Search/query | Result count + top results |

---

## Response Template (All Tasks)

Every agent response during task execution MUST follow this structure:

```yaml
task:
  objective: "What is being done"
  progress: "Step X of Y"

executed:
  action: "Concrete action taken"
  tool: "Tool/command used"
  result: "Output from tool"

verified:
  check: "What was verified"
  evidence: "Concrete evidence"
  status: "pass | fail | partial"

artifacts:
  created: ["list", "of", "paths"]
  modified: ["list", "of", "paths"]
  failed: ["list", "of", "paths"]

next:
  step: "Next action" | "blocked: reason"
```

---

## No-Tool Responses

If no tool has been executed yet, the agent MUST NOT claim progress. Instead:

```yaml
status: "planning"
intended_action: "What will be done next"
blocking_condition: "None | description"
current_state: "Known state before starting"
```

---

## Enforcement Rules

These are enforced by the runtime (see `configs/tooling/tool_permissions.yaml`):

```yaml
guards:
  forbid_unverified_completion_claims: true
  require_evidence_for_filesystem_claims: true
  auto_continue_safe_multistep_tasks: true
  stall_timeout_seconds: 20
  require_artifact_summary_on_completion: true
  evidence_required_for:
    - filesystem_operations
    - code_execution
    - test_results
    - api_responses
    - configuration_changes
```

### Violation Consequences

| Violation | Action |
|-----------|--------|
| Single claim without evidence | Warning + request for evidence |
| Repeated claims without evidence | Task paused, human notification |
| Fabricated evidence | Task failed, incident logged |
| Missing artifact summary | Response rejected, regenerate |

---

## Examples

### ❌ Bad Response
```
I'm creating the project structure now. I'll set up src/, configs/, and tests/.
Continuing with the next steps...
```

**Violations:**
- No tool executed
- No evidence provided
- No artifact list
- Vague progress statement

### ✅ Good Response
```yaml
task:
  objective: "Create AgentSessionLearningSystem project skeleton"
  progress: "Step 2 of 7"

executed:
  action: "Created 6 top-level directories"
  tool: "mkdir -p"
  result: "exit 0"

verified:
  check: "All directories exist"
  evidence: |
    $ ls -d /path/to/AgentSessionLearningSystem/*/
    configs/  data/  docs/  src/  tests/  tools/
  status: "pass"

artifacts:
  created:
    - /path/to/AgentSessionLearningSystem/src
    - /path/to/AgentSessionLearningSystem/configs
    - /path/to/AgentSessionLearningSystem/data
    - /path/to/AgentSessionLearningSystem/tests
    - /path/to/AgentSessionLearningSystem/tools
    - /path/to/AgentSessionLearningSystem/docs

next:
  step: "Create src/ subdirectories (models/, services/, adapters/)"
```

---

## Relationship to Other Contracts

| Contract | Relationship |
|----------|-------------|
| `AGENTS.md` | Zero Law extension |
| `RULES.md` | Layer 2 — enforced rule |
| `configs/orchestrator/router.yaml` | Gates applied at all tiers C2+ |
| `configs/tooling/tool_permissions.yaml` | Runtime enforcement hooks |
| `docs/adr/ADR-005` | Path validation prerequisite |

---

*Contract version: 1.0.0 | Created: 2026-04-14 | Status: ACTIVE*
*Enforcement: Runtime guards + completion gates*
