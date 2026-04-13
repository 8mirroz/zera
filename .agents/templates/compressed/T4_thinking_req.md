# T4: Thinking Requirement (Compressed Format)

**Savings:** 55% vs verbose format

## Format

```
<think:SEQUENTIAL steps=N-M>
Focus: [topic1, topic2, topic3]
Questions:
  1. "Question about topic1?"
  2. "Question about topic2?"
  ...
</think>
```

## Rules
- Type: SEQUENTIAL, PARALLEL, DIVERGENT
- steps: range (e.g., 5-7)
- Focus: bracketed topic list
- Questions: numbered, quoted, with options where applicable (Option1|Option2|Option3)
