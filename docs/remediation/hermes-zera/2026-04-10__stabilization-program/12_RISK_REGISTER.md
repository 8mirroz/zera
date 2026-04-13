# 12 Risk Register

## Open Risks (Current)

| ID | Risk | Severity | Status |
|---|---|---|---|
| R-001 | Benchmark strict gate fails quality/provenance checks | High | Open |
| R-002 | MCP profile surface has missing servers and routing mismatch | High | Open |
| R-003 | Workflow catalog references 18 missing files | High | Open |
| R-004 | Runtime trace field-level compliance failures | High | Open |
| R-005 | Zera runtime enforcement incomplete | Medium | Open |
| R-006 | Memory layering remains declarative | Medium | Open |

## Mitigated Risks

| ID | Risk | Mitigation | Status |
|---|---|---|---|
| M-001 | Validator false-green | non-zero fail-fast semantics | Mitigated |
| M-002 | Enabled provider/runtime registration drift | parity APIs + checks | Mitigated |
| M-003 | Trace schema mirror drift | parity test + synchronized mirror | Mitigated |
| M-004 | Runtime health tracking regression | compatibility wrapper + updated tests | Mitigated |

## Summary

- Open: 6
- Mitigated: 4
- Closed: 0 (for full-program acceptance)
