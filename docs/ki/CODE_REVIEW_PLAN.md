# Global Code Review Plan (Pre-Commit)

## Purpose

This document defines the **mandatory code review process** that must be completed **before every commit** in the Antigravity Core workspace.

The goal is to catch bugs, enforce standards, and ensure all changes meet the project's quality gates **before they become permanent history**.

---

## Scope

This plan applies to **all commits** regardless of complexity tier (C1–C5), with gate requirements scaling according to tier.

## Reliability Platform Contract

Review and pre-commit execution now use the config-driven reliability platform as the source of truth:

- `configs/tooling/test_reliability_program.yaml`
- `configs/tooling/test_suite_matrix.yaml`
- `configs/tooling/debug_surface_map.yaml`

Runtime entrypoints must route through these contracts, not through ad hoc `pytest` or shell wrappers. The operator-facing commands are:

- `make test-contract`
- `make test-governance`
- `make test-smoke`
- `make test-unit`
- `make doctor`
- `make reliability-report`

---

## Review Phases

### Phase 0: Pre-Review Preparation

**Trigger:** Work on a task is complete, changes are ready to commit.

| Step | Action | Tool/Command |
|------|--------|--------------|
| 0.1 | Identify task tier | Check task classification (C1–C5) |
| 0.2 | Determine required gates | Read `configs/orchestrator/completion_gates.yaml` |
| 0.3 | Gather all changes | `git status && git diff HEAD` |
| 0.4 | Review recent commit style | `git log -n 3 --oneline` |

**Output:** Review checklist scoped to the correct tier.

---

### Phase 1: Self-Review (All Tiers C1–C5)

**Performed by:** The author (human or agent) who made the changes.

#### 1.1 Correctness Review

- [ ] **Logic:** Does the code do what it's supposed to do?
- [ ] **Edge cases:** Are boundary conditions handled?
- [ ] **Error handling:** No silent failures — explicit error messages
- [ ] **No regressions:** Existing functionality not broken

#### 1.2 Standards Compliance

- [ ] **Type hints** present (Python) / **TypeScript strict mode** (TS)
- [ ] **Naming:** Explicit, not clever
- [ ] **Structure:** Modular, composable
- [ ] **No prohibited patterns:** See "Absolute Prohibitions" in `WORKSPACE_STANDARD.md`

#### 1.3 Security Review

- [ ] **No secrets/keys** in code (check `.env.example` pattern)
- [ ] **Input validation:** Zod (TS) or explicit validation (Python)
- [ ] **Path validation:** Within allowed directories (per ADR-005)
- [ ] **Rate limiting:** Present on external-facing code
- [ ] **Audit logging:** Present on sensitive operations

#### 1.4 Definition of Done Check

- [ ] `README.md` exists with purpose, install, run instructions
- [ ] `.env.example` exists (if env vars used)
- [ ] Code passes lint/format
- [ ] Errors handled with meaningful messages
- [ ] Minimal happy-path test or script exists
- [ ] Relevant docs updated (`docs/ki/` or `docs/adr/`)

**Output:** Self-review completed, changes deemed ready for next phase.

---

### Phase 2: Automated Quality Gates (All Tiers C1–C5)

**Trigger:** After self-review passes.

| Step | Action | Command |
|------|--------|---------|
| 2.1 | Run contract gates | `make test-contract` |
| 2.2 | Run governance gates | `make test-governance` |
| 2.3 | Run smoke suite | `make test-smoke` |
| 2.4 | Run unit suite when code/runtime paths changed | `make test-unit` |
| 2.5 | Run pre-commit wrapper | `bash scripts/run_quality_checks.sh` |
| 2.6 | Run doctor triage when env/tooling/docs changed | `make doctor` |
| 2.7 | Inspect reliability event summary | `make reliability-report` |
| 2.8 | Skill publish check | `cd repos/packages/agent-os && uv run python scripts/swarmctl.py publish-skills` |

**Blocking:** Any failure in this phase **blocks the commit** until resolved.

**Output:** All gates passed, evidence collected.

Notes:

- `make test-contract` is the blocking contract for config/schema/runtime-doc parity.
- `make test-governance` is mandatory for autonomy/persona/Zera surfaces.
- `make doctor` is not a substitute for tests; it is the standard debug surface for tooling and environment failures.
- `make reliability-report` is the canonical summary of emitted suite events and latest failure artifacts.

---

### Phase 3: Peer Review (Tiers C3, C4, C5 Only)

**Trigger:** Automated gates passed. Tier is C3 or higher.

#### 3.1 Reviewer Assignment

| Tier | Reviewer | Model |
|------|----------|-------|
| C3 | 1 peer agent | `mistralai/mistral-small-24b-instruct-2501:free` |
| C4 | 2 peer agents + human audit | Reviewer + human sign-off |
| C5 | 2 peer agents + human + council | Full council review |

#### 3.2 Review Diff

```bash
# Generate focused diff for review
git diff HEAD > /tmp/commit-review.diff
```

#### 3.3 Review Checklist (Peer)

- [ ] **Correctness:** Logic is sound, no bugs
- [ ] **Security:** No vulnerabilities introduced
- [ ] **Performance:** No obvious performance regressions
- [ ] **Maintainability:** Code is readable and testable
- [ ] **Standards:** Follows project conventions
- [ ] **Tests:** Adequate coverage for the change
- [ ] **Docs:** Behavior documented appropriately

#### 3.4 AI-Assisted Review

```bash
# Use openclaude workflow for automated review
git diff HEAD~1 > /tmp/pr.diff
openclaude \
  --model github/gpt-4o \
  --no-interactive \
  --output-format json \
  --system-prompt "You are a code reviewer. Review for bugs, security, quality, standards compliance. Be concise." \
  "Review this diff and output findings as JSON: file, line, severity, message" \
  < /tmp/pr.diff > /tmp/review.json
```

**Output:** Review findings documented, all issues resolved or explicitly accepted.

---

### Phase 4: Tier-Specific Gates

#### C1 (Trivial) — Minimal Gates
- [x] Self-review (Phase 1)
- [x] Automated gates (Phase 2)
- **Ready to commit**

#### C2 (Simple)
- [x] Self-review (Phase 1)
- [x] Automated gates (Phase 2) — **tests required**
- **Ready to commit**

#### C3 (Medium)
- [x] Self-review (Phase 1)
- [x] Automated gates (Phase 2)
- [x] Peer review (Phase 3)
- [x] Retrospective written → `docs/ki/retro_{task_id}.md`
- **Ready to commit**

#### C4 (Complex)
- [x] Self-review (Phase 1)
- [x] Automated gates (Phase 2)
- [x] Peer review (Phase 3)
- [x] Retrospective written
- [x] Pattern extracted → `docs/patterns/`
- [x] Human audit completed
- [x] Validation evidence collected
- [x] Review evidence collected
- [x] Isolated worktree used
- **Ready to commit**

#### C5 (Critical)
- [x] All C4 gates
- [x] ADR updated → `docs/adr/`
- [x] Council review passed
- [x] Audit evidence collected
- **Ready to commit**

---

### Phase 5: Commit Message Review

**Trigger:** All gates passed.

#### 5.1 Commit Message Standards

- [ ] **Clear:** Describes what changed and why
- [ ] **Concise:** Single line summary ≤ 72 chars
- [ ] **Scoped:** References task/ticket ID if applicable
- [ ] **Style-matched:** Follows recent commit style (`git log -n 3`)

#### 5.2 Commit Message Template

```
<type>(<scope>): <subject>

<body: what changed and why>

<footer: references, breaking changes>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security`

**Examples:**
```
feat(router): add C4 swarm path with 3-agent routing

Implements multi-agent routing for complex tasks (C4).
Routes to 3 agents with max 30 tool calls.
Requires human audit gate.

Refs: task-142
```

```
fix(mcp): validate file paths to prevent directory traversal

Adds path validation per ADR-005 security requirements.
All MCP server requests now validate paths are within
allowed directories.
```

**Output:** Commit message drafted and reviewed.

---

### Phase 6: Final Verification (Pre-Commit Hook)

**Trigger:** Commit message approved.

| Step | Action | Command |
|------|--------|---------|
| 6.1 | Verify no secrets | `git diff --staged --check` |
| 6.2 | Verify no large files | Check no files > 10MB |
| 6.3 | Verify no forbidden patterns | Check for `TODO:`, `FIXME:`, `HACK:` |
| 6.4 | Final diff review | `git diff --staged` |
| 6.5 | Verify staging | `git status` — only intended files staged |

**Blocking:** Any issue here **un-stages** and returns to Phase 1.

**Output:** Changes verified, ready for commit.

---

## Execution Flow

```
                    ┌─────────────┐
                    │  Task Done  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Phase 0     │
                    │ Prepare     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
               Yes  │ Phase 1     │
            ┌────── │ Self-Review │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            │       │ Phase 2     │
            │       │ Auto Gates  │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            ├─────► │ Phase 3     │  (C3+ only)
            │       │ Peer Review │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            │       │ Phase 4     │
            │       │ Tier Gates  │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            │       │ Phase 5     │
            │       │ Commit Msg  │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            │       │ Phase 6     │
            │       │ Final Check │
            │       └──────┬──────┘
            │              │
            │       ┌──────▼──────┐
            │       │   COMMIT    │
            │       └─────────────┘
            │
            │ (failure → fix → return to failing phase)
            └──────┘
```

---

## Tooling Integration

### Review Skill

The `review` skill provides specialized code review capabilities:

```
/review <file-path>          # Review a specific file
/review <pr-number>          # Review a PR
/review <pr-number> --comment  # Post inline comments
```

**Use cases:**
- Security review
- Performance review
- Architecture review
- Quality review

### Review Agent Pattern

```bash
# Use the review skill for comprehensive code review
skill: "review"
```

---

## Metrics & Reporting

### Review Metrics to Track

| Metric | Description | Target |
|--------|-------------|--------|
| **Review cycle time** | Time from self-review to commit | < 15 min (C1-C2), < 30 min (C3-C5) |
| **Defect escape rate** | Bugs found post-commit | < 5% |
| **Gate failure rate** | % of commits blocked by gates | < 20% |
| **Review coverage** | % of commits with full review | 100% |

### Post-Commit Reporting

After each commit:

```bash
# Verify commit success
git status

# Log commit
git log -n 1
```

For C4/C5: Document retrospective and audit evidence.

---

## Exception Process

### When Can Gates Be Skipped?

| Scenario | Gate Skip | Approval Required |
|----------|-----------|-------------------|
| Emergency hotfix | Phase 3 (peer review) | Human sign-off post-commit |
| Documentation only | Phase 2 (automated tests) | None — but docs must build cleanly |
| Config change | Phase 2 (tests) | Config validation must still pass |

**Rule:** Exceptions are logged in commit message with `Exception: <reason>` prefix.

---

## Integration with CI/CD

### GitHub Workflow

The `.github/workflows/openclaude-review.yml` workflow provides automated review on PR:

1. Checkout PR changes
2. Generate diff
3. Run openclaude review with GPT-4o
4. Post findings as PR comment

### Local Pre-Commit Hook (Optional)

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Run quality checks before commit

echo "Running pre-commit checks..."
bash scripts/run_quality_checks.sh || {
  echo "❌ Pre-commit checks failed"
  exit 1
}

echo "✅ Pre-commit checks passed"
exit 0
```

Enable with: `chmod +x .git/hooks/pre-commit`

---

## Responsibilities Matrix

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|------|---------|---------|---------|---------|---------|---------|
| **Author** | Execute | Execute | — | — | Draft | Verify |
| **Reviewer** | — | — | Execute | — | Review | — |
| **Human** (C4/C5) | — | — | — | Audit | Approve | — |
| **Council** (C5) | — | — | — | Review | Approve | — |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `configs/orchestrator/completion_gates.yaml` | Tier gate definitions |
| `configs/rules/WORKSPACE_STANDARD.md` | Workspace standards |
| `configs/rules/AGENT_ONLY.md` | Agent-specific rules |
| `docs/adr/ADR-005_mcp_security.md` | MCP security standards |
| `.github/workflows/openclaude-review.yml` | CI review workflow |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-08 | Initial creation |
