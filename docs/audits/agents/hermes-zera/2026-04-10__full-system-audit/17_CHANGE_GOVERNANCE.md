# 17. Change Governance

## Policy
- Runtime code, config, and operator-side profile changes are one governance surface and must be reviewed together.
- Narrative docs never become authoritative without a live consumer or an explicit validator.
- “Strict parity” claims require automated diff evidence, not labels in config.

## Required Gates
- Config-consumer parity gate.
- Provider-registration gate.
- Workflow-asset existence gate.
- Benchmark validity gate.
- Persona/memory executable-eval gate.
- Adapter/home-profile parity gate.

## Human Review Triggers
- Any change touching persona boundaries, safety, memory retention, approval policy, or external cron behavior.
- Any benchmark analyzer change that can affect score or gate outcomes.
- Any new provider, tool surface, or MCP admission.

## Artifact Rules
- One canonical audit directory per full-system audit.
- One canonical trace sink per active runtime.
- One canonical benchmark ledger with explicit provenance classes.
