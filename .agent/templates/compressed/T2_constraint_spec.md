# T2: Constraint Specification (Compressed Format)

**Savings:** 70% vs explanatory format

## Format

```
<constraint:REQUIRED_PARAM param_name>
  error: "User-facing error message"
  lookup: "file_to_check.md"
  action: "halt_if_missing"
</constraint>
```

## Rules
- Type: REQUIRED_PARAM, FORBIDDEN, RANGE, ENUM
- error: concise user-facing message with example usage
- lookup: reference file for valid values (optional)
- action: halt_if_missing | warn | default(value)
