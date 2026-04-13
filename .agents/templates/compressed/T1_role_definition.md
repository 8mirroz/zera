# T1: Role Definition (Compressed Format)

**Savings:** 60-70% vs verbose format

## Format

```
<role:NAME>
Capabilities: [cap1, cap2, cap3]
Philosophy: Core approach in one line
Output: Expected deliverable
</role>
```

## Example

```
<role:EXPLORER>
Capabilities: [problem_decomposition, outward_search, inward_diverge, synthesis]
Philosophy: Search + diverge = dual-direction exploration (natural switching)
Output: Structured exploration report
</role>
```

## Rules
- Name: ALL_CAPS identifier
- Capabilities: bracketed list, snake_case
- Philosophy: single sentence, core approach
- Output: expected deliverable type
