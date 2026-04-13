# T3: Workflow Step (Compressed Format)

**Savings:** 50-60% vs narrative format

## Format

```
<step:N STEP_NAME>
Goal: One-line goal

<check:CHECK_NAME>
  - file_or_condition_1
  - file_or_condition_2
  on_missing: "action" + halt|warn
</check>

<load>
  N.1: Source (focus: [field1, field2])
  N.2: Source (focus: [field1, field2])
</load>

<output>Description (memory|file path)</output>
</step>
```

## Rules
- Step number + ALL_CAPS name
- Goal: single line
- check: preconditions with on_missing action
- load: numbered sub-steps with focus filters
- output: what this step produces
