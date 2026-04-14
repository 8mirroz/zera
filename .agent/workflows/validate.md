# Validator Workflow
# Phase 3 - Automated testing and validation
# Version: 1.0

## Overview

Validator workflow runs automated tests and quality checks.
Activates automatically for C2+ tasks (based on completion_gates) or manually.

## Workflow Steps

### Step 1: Detect Test Framework

```bash
# Detect what test framework to use
if [ -f "pytest.ini" ] || [ -d "tests" ]; then
  FRAMEWORK="pytest"
elif [ -f "jest.config.js" ]; then
  FRAMEWORK="jest"
elif [ -f "Makefile" ]; then
  FRAMEWORK="make"
fi
```

### Step 2: Run Validation Suite

Execute in order:
1. Syntax checks
2. Lint checks
3. Unit tests (if available)
4. Integration tests (if available)
5. Smoke tests (if available)

### Step 3: Collect Results

```json
{
  "syntax": { "passed": true },
  "lint": { "passed": true, "warnings": 0 },
  "tests": { "passed": 42, "failed": 0 },
  "coverage": 87.5
}
```

### Step 4: Check Thresholds

Compare against tier-based thresholds from `validator.yaml`

### Step 5: Generate Report

Output to `.agent/reviews/validation_{task_id}_{timestamp}.json`

## Usage

```bash
# Run all validations
validate

# Run specific check
validate --lint
validate --tests
validate --smoke

# Skip certain checks
validate --no-coverage
```

## Integration Points

- Triggered by: `execution_loop.yaml` Step 7
- Completion gates: `completion_gates.yaml` C2+
- Thresholds from: `validator.yaml` quality_thresholds
