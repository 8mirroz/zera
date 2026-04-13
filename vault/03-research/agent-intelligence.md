---
created: 2026-04-08
updated: 2026-04-08
source: zera-self-evolution
type: intelligence-memory
tags: [intelligence, agents, knowledge, swarm]

---
# Zera Agent Intelligence

## Known Agent Systems
| System | Type | Location | Status |
|--------|------|----------|--------|
| NanoClaw | Claude Agent SDK | ~/NanoClaw/nanoclaw/ | ✅ Indexed |
| Antigravity Core | Multi-agent platform | ~/antigravity-core-v5-refactor/ | ✅ Active |
| Hermes Agent | CLI agent | ~/.hermes/ | ✅ Active (Zera) |
| Qwen CLI | Coding agent | ~/.qwen/ | ✅ Configured |
| OpenClaw | Agent harness | Research | ✅ Known |
| Claude-Swarm | Swarm agent | Research | ✅ Known |
| Auto-Claude | Auto agent | Research | ✅ Known |
| SuperClaude Framework | Framework | Research | ✅ Known |

## Agent Configs in Projects
| Project | Config Type | Files |
|---------|------------|-------|
| RIVO INTRO | .agent + CLAUDE.md | AGENTS.md, CLAUDE.md |
| CF1 | .agent | Configs |
| creativfree | .agent | Configs |
| AXEL Dashboard | .claude + .agent | CLAUDE.md, QWEN.md |
| electromax | .claude + .agent | CLAUDE.md, QWEN.md |
| RIVO CONF | .agent | CLAUDE.md, QWEN.md |

## Swarm Patterns I Know
1. **Model Tier Routing** — Use cheap for routing, expensive for quality
2. **Container Isolation** — Each agent in isolated VM
3. **Channel Self-Registration** — Auto-discover capabilities
4. **Free-First + Local Fallback** — Ollama when cloud unavailable
5. **Group-Based Memory** — Isolated memory per context
6. **Scheduled Tasks** — Cron-based execution

## What I Can Learn
- NanoClaw's free model tier routing → optimize Antigravity Core routing
- NanoClaw's channel self-registration → adapt for Hermes skills
- NanoClaw's group memory → isolate per-project memory in vault
- Research repos → new patterns, configs, skills to try
- Project configs → proven patterns for different domains

## Integration Priorities
1. Free model tier routing from NanoClaw → Antigravity Core
2. Channel self-registration → Hermes skill system
3. Group-based memory → Per-project vault sections
4. Ollama local fallback → Hermes when API unavailable