# Quick Wins — Zera Fractal Multi-Agent Blueprint

**Audit Wave:** 7 — Final Recommendation + Migration Package
**Date:** 2026-04-13
**Scope:** Items that can be completed in < 1 day each
**Sorted by:** Impact (highest first)

---

## QW-1: Eliminate `.agents/.agents` Path Mismatch

**Impact:** Critical — causes intermittent failures, confusing for all developers
**Effort:** 2–4 hours

**What:** The codebase has two directory names (`.agent` and `.agents`) referenced interchangeably. Pick one canonical name and update all references.

**Why:** Path mismatches cause `FileNotFoundError` at runtime, make onboarding confusing, and break any tool that relies on predictable paths.

**How:**
1. Audit all references: `grep -r "\.agent" --include="*.py" --include="*.yaml" --include="*.json" --include="*.md"`
2. Choose canonical path (recommend `.agent` — matches existing conventions)
3. Update all references to use canonical path
4. Create compat symlink: `ln -s .agent .agents` (temporary, until all external references updated)
5. Run full test suite to verify

**Risk if not done:** Every new developer will hit this. Intermittent failures will be blamed on "environment issues" rather than the real cause.

---

## QW-2: Remove Duplicate Scripts

**Impact:** High — wastes maintenance effort, causes confusion about which script to run
**Effort:** 3–6 hours

**What:** Audit `scripts/` directory for duplicates (same content or same purpose). Consolidate or remove.

**Why:** Duplicate scripts create ambiguity ("which one do I run?"), double maintenance effort, and can produce conflicting results.

**How:**
1. Generate content hashes: `find scripts/ -type f -name "*.py" -exec sha256sum {} \; | sort | uniq -D -w 64`
2. For identical content: keep one, remove others, update references
3. For similar purpose: merge into single script with subcommands, remove originals
4. Update any documentation referencing removed scripts
5. Verify no broken imports

**Risk if not done:** Ongoing confusion, duplicated bug fixes (fix one script, forget the other), wasted CI time running redundant scripts.

---

## QW-3: Create Missing Directories

**Impact:** High — causes runtime errors that only appear in production
**Effort:** 1–2 hours

**What:** Identify all directories referenced by code but not present on disk. Create them with `.gitkeep` files.

**Why:** Missing directories cause `FileNotFoundError` at runtime, often only in production where the directory structure differs from development.

**How:**
1. Search for `os.makedirs` and `Path.mkdir` calls with `exist_ok=False` (or no flag)
2. Search for hardcoded paths in configs that reference directories
3. Create all missing directories: `mkdir -p <path> && touch <path>/.gitkeep`
4. Commit to ensure directories exist in fresh clones

**Risk if not done:** Runtime failures in production, delayed startup, confusing error messages for operators.

---

## QW-4: Replace Silent Fallbacks with Explicit Errors

**Impact:** High — makes debugging impossible, hides real problems
**Effort:** 4–8 hours

**What:** Find all `except: pass` or bare `try/except` blocks that silently swallow errors. Replace with explicit error + trace emission.

**Why:** Silent fallbacks make it impossible to diagnose why something failed. The system appears to work but is silently degrading.

**How:**
1. Search for patterns: `except: pass`, `except Exception: pass`, bare `except:`
2. For each match:
   - Determine what the fallback was trying to handle
   - Add explicit error log with component, action, reason
   - Emit trace event (once P0-1 trace emitter exists)
   - Decide: should this be a hard failure or a documented fallback?
3. Verify no silent fallbacks remain: `grep -r "except.*pass" --include="*.py" repos/`

**Risk if not done:** Failures accumulate silently. System degrades gradually without anyone noticing. Debugging requires guesswork.

---

## QW-5: Add Config Validation at Startup

**Impact:** Medium — prevents hard-to-diagnose issues from bad configs
**Effort:** 3–5 hours

**What:** Validate all YAML configs at startup using JSON Schema. Invalid config → process exits with clear message.

**Why:** Bad configs cause subtle behavior changes that are hard to trace. Fail-fast at startup is much cheaper than debugging later.

**How:**
1. Create JSON Schema for each config file type (router.yaml, models.yaml, etc.)
2. Add validation at startup: load config → validate → exit if invalid
3. Error message format: `[config] validation failed: <file>:<line>: <what's wrong>. Suggested fix: <hint>`
4. Add `--skip-config-validation` flag for emergency overrides (logged as warning)

**Risk if not done:** Typos in configs cause silent behavior changes. Missing keys use defaults that may not be appropriate for production.

---

## QW-6: Standardize Error Message Format

**Impact:** Medium — improves debuggability, reduces time-to-resolution
**Effort:** 4–6 hours

**What:** Update all error messages to follow format: `[component] action failed: reason. Suggested fix: hint`.

**Why:** Inconsistent error messages force developers to read source code to understand failures. Standardized messages are self-documenting.

**How:**
1. Define error message template in a shared module
2. Search for all error messages (log.error, raise Exception, print to stderr)
3. Update each to follow the format
4. Review for clarity: can someone who didn't write the code understand the fix?

**Risk if not done:** Every error requires a debugging session. Operators cannot self-serve fixes. Onboarding takes longer.

---

## QW-7: Add Trace ID to All Log Lines

**Impact:** Medium — enables correlating events across components
**Effort:** 2–3 hours

**What:** Add `trace_id` to every log line emitted by the orchestrator, router, and agent execution loop.

**Why:** Without trace IDs, you cannot correlate events that belong to the same task. Debugging requires manual pattern matching on timestamps and task names.

**How:**
1. Generate trace_id at task entry point (UUID)
2. Pass trace_id through context (thread-local, async context var, or explicit parameter)
3. Update logging formatter to include `trace_id`
4. Verify trace_id appears in all log lines for a task

**Risk if not done:** Debugging multi-component failures requires manual correlation. Impossible to trace a task's journey through the system.

---

## QW-8: Document Current Orchestration Flow

**Impact:** Medium — prevents incorrect assumptions during migration
**Effort:** 3–4 hours

**What:** Write a clear, accurate description of how the current orchestrator works (not how it should work). Include: task flow, decision points, fallback chains, known limitations.

**Why:** The migration depends on understanding the current system. Incorrect assumptions lead to breaking changes that are hard to detect.

**How:**
1. Read the orchestrator code end-to-end
2. Trace a task from entry to completion (or failure)
3. Document: entry point → classification → model selection → execution → output
4. Include all fallback chains and their triggers
5. Note known limitations and workarounds
6. Have a second person verify by following the documentation against the code

**Risk if not done:** Migration introduces regressions because the current behavior was misunderstood. Debugging takes longer because no one knows what the system actually does.

---

## QW-9: Add Health Check Endpoint

**Impact:** Low (but high signal) — enables monitoring and automated alerts
**Effort:** 1–2 hours

**What:** Add a `/health` endpoint (or CLI command `swarmctl health`) that returns system status: orchestrator running, config loaded, memory usage, active tasks.

**Why:** Currently, the only way to check system health is to run a task and see if it works. A health check enables proactive monitoring.

**How:**
1. Create health check function that checks:
   - Orchestrator process running
   - Config files loaded and valid
   - Memory usage within bounds
   - No stuck tasks (tasks in same state > expected duration)
2. Expose via CLI: `swarmctl health`
3. Return structured output: `{status: ok|degraded|error, checks: [...]}`

**Risk if not done:** System degrades without anyone noticing. Failures discovered only when users report them.

---

## QW-10: Clean Up Unused Dependencies

**Impact:** Low — reduces install time, attack surface, and confusion
**Effort:** 2–3 hours

**What:** Audit `package.json`, `requirements.txt`, `pyproject.toml` for unused dependencies. Remove them.

**Why:** Unused dependencies increase install time, add potential security vulnerabilities, and confuse developers ("do we need this?").

**How:**
1. Use dependency analysis tools: `depcheck` (Node), `pip-check-reqs` (Python)
2. For each unused dependency:
   - Verify it's truly unused (grep for imports)
   - Remove from config file
   - Run test suite to confirm nothing breaks
3. Document any dependencies kept for non-obvious reasons

**Risk if not done:** Slower installs, potential security vulnerabilities, developer confusion, larger deployment artifacts.

---

## Quick Win Summary

| ID | Description | Effort | Impact | Phase |
|----|-------------|--------|--------|-------|
| QW-1 | Path canonicalization | 2–4h | Critical | Phase 2 |
| QW-2 | Duplicate script removal | 3–6h | High | Phase 2 |
| QW-3 | Create missing directories | 1–2h | High | Phase 2 |
| QW-4 | Eliminate silent fallbacks | 4–8h | High | Phase 2 |
| QW-5 | Config validation at startup | 3–5h | Medium | Phase 2 |
| QW-6 | Error message standardization | 4–6h | Medium | Phase 2 |
| QW-7 | Trace ID in all log lines | 2–3h | Medium | Phase 1 |
| QW-8 | Document current orchestration | 3–4h | Medium | Phase 1 |
| QW-9 | Health check endpoint | 1–2h | Low | Phase 1 |
| QW-10 | Clean up unused dependencies | 2–3h | Low | Phase 2 |

**Total effort:** 25–43 hours (4–7 working days)
**Recommended order:** QW-1 → QW-3 → QW-7 → QW-8 → QW-4 → QW-2 → QW-5 → QW-6 → QW-9 → QW-10

All quick wins belong to Phase 1 or Phase 2 and can be started immediately without waiting for other phases.
