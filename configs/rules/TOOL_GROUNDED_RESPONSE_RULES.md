# Tool-Grounded Response Rules

**Version:** 1.0.0  
**Status:** ACTIVE — Enforced by Runtime Guards  
**Applies to:** All agents (Hermes profiles, Zera, CLI tools, workflow executors)  
**Enforcement:** Response validation layer + completion gates

---

## Core Principle

> **Every agent response must be grounded in observed tool results.**
> 
> No tool result → no claim. No claim without evidence → violation.

This rule eliminates the class of bugs where agents narrate actions they haven't performed,
claim completions they haven't verified, or report progress that hasn't occurred.

---

## The Grounding Chain

Every response must follow this chain:

```
Tool Executed → Result Observed → State Verified → Response Generated
      ↑                                                    ↓
      └──────────────── Grounding Link ────────────────────┘
```

**Breaking the chain is a hard violation.**

### Valid Chain Example
```
1. execute: mkdir -p /path/to/src
2. result: exit 0
3. verify: test -d /path/to/src && echo "exists"
4. verify result: "exists"
5. response: "Created /path/to/src (verified)"
```

### Broken Chain Example (VIOLATION)
```
1. execute: mkdir -p /path/to/src
2. result: exit 0
3. response: "Created /path/to/src with models/, services/, adapters/ subdirectories"
   ↑ VIOLATION: subdirectories not created or verified
```

---

## Response Construction Rules

### Rule 1: Tool Result is the Source of Truth

When constructing a response, the agent MUST derive all claims from tool results.

**Template:**
```
Claim = f(tool_results, verification_checks)
```

**Example:**
```yaml
# Tool result:
tool: "ls"
result: |
  configs/  data/  docs/  src/  tests/  tools/

# Valid claims:
- "6 top-level directories exist"
- "configs/ directory exists"
- "src/ directory exists"

# Invalid claims (not supported by tool result):
- "src/ contains models/, services/"  # Not verified
- "All directories are empty"          # Not checked
- "Project structure is complete"      # Subjective, not grounded
```

### Rule 2: No Forward Claims

An agent MUST NOT claim results from future steps.

**Violation:**
```
"Now I'll create the config files and tests."
→ No tool called for config files or tests yet.
```

**Correct:**
```
"Next step: create config files. Awaiting tool call."
```

### Rule 3: No Aggregation Without Verification

An agent MUST NOT aggregate results from multiple steps unless all steps were verified.

**Violation:**
```
"All 20 files created successfully."
→ Only 15 verified, 5 assumed.
```

**Correct:**
```
"15 of 20 files created and verified. 5 pending (see artifact list)."
```

### Rule 4: Distinguish Known from Intended

When describing planned work vs. completed work:

| Status | Prefix | Example |
|--------|--------|---------|
| Completed | "Created" + evidence | "Created `src/` (verified: exists)" |
| In progress | "Executing" + tool | "Executing: write `src/models/user.py`" |
| Planned | "Will create" | "Will create `src/services/` next" |
| Blocked | "Blocked: reason" | "Blocked: awaiting API key from user" |

---

## Persona vs Executor Separation

### Problem

When a persona layer (like ZeRa's identity/tone) wraps execution output,
it can accidentally replace evidence with narrative:

```
❌ "I'm thoughtfully crafting your project structure with care..."
   → No evidence, no tool result, pure narrative.
```

### Solution: Two-Layer Response

**Layer 1 — Executor (mandatory, always present):**
```yaml
executed:
  tool: "mkdir"
  result: "exit 0, created 6 dirs"
verified:
  check: "ls output confirms 6 dirs"
  status: "pass"
```

**Layer 2 — Persona (optional, wraps executor output):**
```
✅ "Project skeleton ready — 6 directories created and verified.
   Next up: populating src/ with the model layer."
```

**Rule:** Persona layer can FORMAT executor output but NEVER REPLACE it.

---

## Enforcement Mechanisms

### 1. Response Validator (Pre-flight)

Before any response is emitted, validate:

```python
def validate_response(response, tool_results):
    claims = extract_claims(response)
    for claim in claims:
        if not is_grounded(claim, tool_results):
            raise GroundingViolation(f"Claim '{claim}' not supported by tool results")
    return True
```

### 2. Evidence Checker (Post-flight)

After response is emitted:

```python
def check_evidence(response):
    file_claims = extract_file_claims(response)
    for path, action in file_claims:
        if action == "created" and not path_exists(path):
            return {"status": "fail", "claim": f"{path} not found"}
    return {"status": "pass"}
```

### 3. Completion Gate

At task completion:

```yaml
gate:
  name: "tool_grounded_completion"
  checks:
    - all_claims_grounded_in_tool_results: true
    - all_file_claims_verified_by_fs: true
    - artifact_summary_present: true
    - no_forward_claims: true
```

---

## Violation Detection Patterns

The following patterns are automatically flagged by the runtime:

| Pattern | Regex/Heuristic | Severity |
|---------|----------------|----------|
| "created" without path | `created(?!.*\b/\b)` | warning |
| "done" without evidence | `done(?!.*evidence)` | error |
| "complete" without artifact | `complete(?!.*artifact)` | error |
| Future tense claim | `will (create|build|setup)` before tool | warning |
| Aggregated claim without count | `(all|every|both).*created` | error |
| Narrative without action | `I'm (creating|building|setting up)` | warning |

---

## Integration with Execution Truth Contract

This document works in tandem with `EXECUTION_TRUTH_CONTRACT.md`:

| Document | Focus |
|----------|-------|
| `EXECUTION_TRUTH_CONTRACT.md` | WHAT evidence is required |
| `TOOL_GROUNDED_RESPONSE_RULES.md` | HOW to construct grounded responses |

Together they form the **Execution Integrity Layer** enforced at all tiers C1+.

---

## Examples

### ✅ Grounded Response
```yaml
executed:
  tool: "write_file"
  target: "/path/to/src/config.yaml"
  result: "42 bytes written"
verified:
  tool: "read_file"
  target: "/path/to/src/config.yaml"
  result: "content matches expected"
  status: "pass"

response: "Created config.yaml at /path/to/src/ (42 bytes, verified)"
```

### ❌ Ungrounded Response
```
"I've set up the configuration and created all the necessary files for the project."
```
**Violations:**
- "set up the configuration" — no tool result shown
- "created all the necessary files" — which files? how many? verified?
- No evidence block
- No artifact list
- Aggregated claim without support

---

## Migration Guide

If your agent currently produces ungrounded responses:

1. **Audit:** Run response validator on recent outputs
2. **Identify:** List all ungrounded claim patterns
3. **Fix:** Add evidence blocks to each claim
4. **Test:** Run grounded response checker
5. **Deploy:** Enable completion gate

---

## Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| `EXECUTION_TRUTH_CONTRACT.md` | Sibling — defines evidence requirements |
| `TASK_PROGRESS_PROTOCOL.yaml` | Consumer — uses states and transitions |
| `AGENTS.md` | Parent — Zero Law extension |
| `configs/orchestrator/router.yaml` | Enforced at all tiers C1+ |
| `configs/tooling/tool_permissions.yaml` | Runtime enforcement hooks |

---

*Rules version: 1.0.0 | Created: 2026-04-14 | Status: ACTIVE*
*Enforcement: Response validation + completion gates + runtime guards*
