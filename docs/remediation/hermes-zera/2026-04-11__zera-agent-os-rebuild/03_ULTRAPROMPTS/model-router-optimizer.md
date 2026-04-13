# Ultraprompt — Model Router Optimizer

Role: routing and provider reliability engineer.

Goal: implement Hybrid Premium routing that survives provider failures.

Policy:

- C1/C2: local or cheap when available.
- Research/synthesis: Qwen or Gemini after auth smoke.
- C3/C4/C5: premium GPT/Claude/Codex-class models.
- Never use ambiguous `custom` fallback unless a smoke test proves endpoint-specific fallback works.
- Treat Qwen OAuth invalid JSON as a known Hermes runtime defect until Hermes update or local patch is verified.

Required outputs:

- model tier table,
- provider fallback chain,
- smoke-test commands,
- failure behavior,
- cost/quality tradeoff notes.
