# Ralph Loop Bug Fix Report

**Date:** 2026-04-14  
**Severity:** HIGH — Agent premature termination  
**Status:** ✅ FIXED & TESTED  

---

## Problem Summary

The agent was exhibiting "short execution" behavior — responding with 1 message and appearing to hang. Root cause analysis revealed **two critical bugs** in the Ralph Loop optimization engine:

### Bug #1: False Plateau Detection (CRITICAL)
**Location:** `repos/packages/agent-os/src/agent_os/ralph_loop.py`

**Symptom:** Loop stopped after 3 iterations with `plateau_detected`, despite consistent improvements (0.689 → 0.718 → 0.747).

**Root Cause:** 
```python
# OLD CODE (buggy)
delta = self.state.best_score - self.state.prev_best_score
if delta < self.config.min_score_delta:  # 0.05
    return True, "plateau_detected"
```

The plateau detection triggered on **any improvement smaller than 0.05**, even if improvements were consistent and ongoing. This caused premature termination at ~75% quality instead of continuing to ~87%.

**Impact:** Agent stopped optimizing after 3 iterations instead of continuing to 6-7 iterations.

### Bug #2: Aggressive Confidence Degradation (MEDIUM)
**Location:** `configs/orchestrator/router.yaml` → `ralph_loop.confidence`

**Symptom:** Confidence dropped to minimum (0.30) after just 3 retries, triggering task escalation.

**Current Settings:**
- `penalty_per_retry: 0.15` — too aggressive
- `min_floor: 0.3`
- Escalation triggers at retry 3 out of 7 max iterations

**Impact:** Tasks escalated prematurely while agent was still improving.

---

## Fixes Applied

### Fix #1: Improved Plateau Detection Logic

**Changes to `ralph_loop.py`:**

1. **Added tracking fields to `RalphLoopState`:**
   - `improvement_streak: int` — consecutive iterations with improvement
   - `last_improvement_delta: float` — delta of last score improvement

2. **Rewrote plateau detection:**
```python
# NEW CODE (fixed)
delta = self.state.last_improvement_delta

# Plateau only if:
# 1. No improvement this iteration (delta == 0), OR
# 2. Improvement is below min_score_delta AND we have no streak
if delta <= 0:
    return True, "plateau_detected"

# If there's consistent small improvement, continue
if delta < self.config.min_score_delta and self.state.improvement_streak < 2:
    return False, None  # Give it more iterations
```

**Result:** Agent now completes 6-7 iterations with consistent improvements instead of stopping at 3.

### Fix #2: Test Suite Created

**New test files:**
- `repos/packages/agent-os/tests/test_ralph_loop.py` — Unit tests (6 tests)
- `repos/packages/agent-os/tests/test_integration_ralph.py` — Integration tests

**Coverage:**
- ✅ Basic iteration
- ✅ Early stop threshold
- ✅ Plateau detection regression (false positive)
- ✅ True plateau detection (correct behavior)
- ✅ Max iterations enforcement
- ✅ Finalize selects best candidate
- ✅ Production scenario simulation
- ✅ Confidence degradation analysis

---

## Before vs After Comparison

### Before Fix
```
Iteration 1: score=0.689
Iteration 2: score=0.718  
Iteration 3: score=0.747
>>> STOP: plateau_detected  ← BUG

Final: best_score=0.747, iterations=3
```

### After Fix
```
Iteration 1: score=0.695, streak=1
Iteration 2: score=0.729, streak=2
Iteration 3: score=0.763, streak=3
Iteration 4: score=0.798, streak=4
Iteration 5: score=0.833, streak=5
Iteration 6: score=0.867, streak=6
>>> STOP: threshold_met  ← CORRECT

Final: best_score=0.867, iterations=6
Improvement: +16% quality (0.747 → 0.867)
```

---

## Remaining Issues

### Confidence Degradation Still Aggressive

**Current:** penalty=0.15 → escalation at retry 3  
**Recommended:** penalty=0.08-0.10 → escalation at retry 5-6

**To fix:** Update `configs/orchestrator/router.yaml`:
```yaml
ralph_loop:
  confidence:
    penalty_per_retry: 0.08  # Changed from 0.15
    min_floor: 0.3
    escalate_on_degradation: true
```

**Decision:** Left as-is for now to preserve existing behavior. Fix can be applied after validating plateau fix in production.

---

## Testing

All tests pass:
```bash
cd repos/packages/agent-os
uv run python tests/test_ralph_loop.py
uv run python tests/test_integration_ralph.py
```

**Test Results:**
- ✅ 6/6 unit tests passed
- ✅ 2/2 integration tests passed
- ✅ Production scenario: 6 iterations, score 0.867, threshold_met

---

## Files Modified

| File | Change |
|------|--------|
| `repos/packages/agent-os/src/agent_os/ralph_loop.py` | Fixed plateau detection + added streak tracking |
| `repos/packages/agent-os/tests/test_ralph_loop.py` | Created unit test suite |
| `repos/packages/agent-os/tests/test_integration_ralph.py` | Created integration tests |

---

## Recommendations

1. **Deploy fix to production** — plateau detection bug is critical
2. **Monitor iteration counts** — should see 5-7 iterations per C3+ task instead of 3
3. **Consider confidence penalty adjustment** — reduce from 0.15 to 0.08
4. **Add metrics** — track avg iterations, stop reasons, and final scores in production

---

**Fixed by:** Qwen Code Agent  
**Reviewed:** Automated tests  
**Status:** Ready for production deployment
