# 00 Research Report — Hermes/Zera Agent OS Rebuild

Date: 2026-04-11  
Target: Zera on Hermes Agent v0.8.0, rebuilt as a controlled Agent OS.

## Executive Read

The external evidence points to the same pattern as the local failure: modern Hermes can be a strong agent runtime, but only when provider auth, MCP schemas, cron context, memory boundaries, and config source-of-truth are actively governed. Zera currently has many capabilities installed, but they are not under one lifecycle contract.

## Official Hermes Sources

- Providers: https://hermes-agent.nousresearch.com/docs/integrations/providers/
- MCP: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- Cron: https://hermes-agent.nousresearch.com/docs/user-guide/features/cron
- Memory: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Context files: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files
- Security: https://hermes-agent.nousresearch.com/docs/user-guide/security

Operational implications:

- Provider configs need explicit fallback behavior. Zera had `fallback_providers: []`, so a provider auth failure can become silence instead of graceful degradation.
- MCP needs a deliberately small default surface and validated server schemas. Large unmanaged tool surfaces amplify context bloat and runtime schema errors.
- Cron is not a substitute for an agent supervisor. Scheduled jobs need bounded context, read-only memory where possible, and explicit write/promotion gates.
- Skills improve behavior only when loaded through a stable selection policy. A large skill pile without routing discipline becomes prompt weight, not capability.
- Context files should be treated as high-value, curated inputs, not an unbounded dump of every rule and memory.
- Security needs fail-closed defaults for destructive actions and clear secret redaction. Zera currently has broad secrets in profile env, so reporting must stay redacted.

## GitHub Signals

Repository: https://github.com/NousResearch/hermes-agent

Observed live repo metadata on 2026-04-11:

- Latest release installed locally: `v2026.4.8`.
- Upstream main continued moving after release; local Hermes reported `103 commits behind`.
- Open issue count is high, so Zera must assume fast-moving runtime drift.

Relevant issues and PRs:

- Qwen OAuth bug: https://github.com/NousResearch/hermes-agent/issues/7746
- Qwen OAuth User-Agent fix: https://github.com/NousResearch/hermes-agent/pull/7751
- Fallback provider issue: https://github.com/NousResearch/hermes-agent/issues/5392
- Custom fallback endpoint issue: https://github.com/NousResearch/hermes-agent/issues/3124
- Cron read-only memory PR: https://github.com/NousResearch/hermes-agent/pull/5648
- Cron context optimization PR: https://github.com/NousResearch/hermes-agent/pull/5672
- MCP schema normalization PR: https://github.com/NousResearch/hermes-agent/pull/4651
- MCP include-filter PR: https://github.com/NousResearch/hermes-agent/pull/7822

Critical interpretation:

- The `Qwen OAuth refresh returned invalid JSON` symptom is a known Hermes-side provider refresh failure. The PR says the refresh request missed a `User-Agent`, causing Qwen to return a non-JSON response. Zera must not treat this as bad local credentials by default.
- Fallback path bugs around custom providers mean Zera should prefer verified first-class provider chains and avoid ambiguous `provider: custom` fallbacks until a smoke test proves the path.
- Cron roadmap PRs confirm that cron context/memory is still evolving. Zera should not run high-frequency mutation jobs through raw Hermes cron prompts.
- MCP filter/schema PRs confirm that large MCP surfaces and schema drift are real failure modes, especially across providers.

## Reddit / Community Signals

- Hermes cron/gateway troubleshooting: https://www.reddit.com/r/hermesagent/comments/1shlbub/cronjobs_does_not_launch_in_docker_gateway_not/
- Local autonomous agent discussion: https://www.reddit.com/r/LocalLLaMA/comments/1sedb37/trying_to_get_a_chatgptcodexstyle_autonomous/

Critical interpretation:

- Community expectations often confuse "chat agent" with "background daemon." Hermes chat will not reliably behave like a living autonomous system unless gateway, cron, and process lifecycle are configured and observable.
- Small/local models can be useful for cheap triage, but tool-heavy autonomous operation needs routing discipline, stronger models for planning/tool calls, and explicit fallback.
- Background automation must be built as a supervised job system, not as a prompt asking the agent to remember to update state.

## Best-Case Build Pattern For Zera

1. Repo-owned semantics: commands, routing, skills, model tiers, governance, and validation live in repo.
2. Hermes profile as generated runtime config: profile is an execution target, not the source of truth.
3. Hybrid Premium routing: cheap/local models for low-risk tasks; premium models for planning, code surgery, tool orchestration, and audits.
4. Bounded aggressive autonomy: frequent observe/report loops are allowed; mutation requires locks, gates, rollback, and telemetry.
5. Thin lifecycle controller: all evolution starts through `zera-evolutionctl`; raw inline background loops are prohibited.
6. Tool surface economy: default MCP profile is small; expanded profiles are selected by task type and validated.
7. Evidence-first self-improvement: every improvement candidate must point to a signal, a test, a rollback path, and an acceptance gate.
