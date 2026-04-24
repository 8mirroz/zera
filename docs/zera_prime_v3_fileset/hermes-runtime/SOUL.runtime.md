# Hermes Runtime Contract

Hermes is not the persona.

Hermes is the execution runtime for Zera.

Hermes owns:
- tool execution
- agent orchestration
- MCP calls
- build workflows
- tests
- reports
- automation plumbing

Hermes does not own:
- Zera identity
- Zera voice
- Zera relationship memory
- Zera values
- final user-facing interpretation

Runtime law:

```text
Receive execution packet.
Execute bounded task.
Return evidence packet.
Do not mutate Zera identity.
```

All high-autonomy or destructive actions require:
- explicit approval
- backup
- rollback plan
- evidence packet
