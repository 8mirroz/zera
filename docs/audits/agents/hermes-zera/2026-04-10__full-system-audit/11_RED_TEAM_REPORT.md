# 11. Red Team Report

## Attack Surfaces Exercised
- Persona exploitation through affection/flattery prompts.
- Instruction collision between declared governance and runtime shortcuts.
- Benchmark cheating through malformed case identity.
- Tooling success-washing via validators that return `0` despite failures.
- Runtime success-washing through `agent_os_python` completion path.
- Policy bypass via external cron sidecar not governed by repo config.

## Successful Exploit Classes
1. **Benchmark score inflation**
   - Entry: repeated `::rN` and `real-trace-*` IDs.
   - Path: analyzer counts total cases for coverage but compares raw IDs for expected-case matching.
   - Severity: critical.
2. **Validator false-positive**
   - Entry: `scripts/test_mcp_profiles.py`.
   - Path: routing failure only affects printed output, not exit code.
   - Severity: high.
3. **Provider declaration spoof**
   - Entry: `runtime_providers.json` declares reachable provider.
   - Path: `RuntimeRegistry` silently lacks implementation factory.
   - Severity: high.
4. **Success-washed execution**
   - Entry: fallback/default provider path.
   - Path: selection logged as success; verification logged as ok with `not-run`.
   - Severity: high.
5. **Governance perimeter leak**
   - Entry: home-side `jobs.json` cron.
   - Path: active behavior exists outside repo `background_jobs.yaml`.
   - Severity: medium.

## Mitigation Additions
- Regression test for benchmark case normalization.
- Contract test for provider registration parity.
- Non-zero exit on MCP validator mismatch.
- Doctor check for empty `.agents/workflows`.
- Audit check for out-of-repo active cron jobs affecting Zera.
