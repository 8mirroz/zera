# Qwen Code Orchestration Workflow
## For Antigravity Core Multi-Agent System

### Overview

This workflow defines how Zera and her "svita" (138 domain expert agents) 
integrate with Qwen Code CLI for enhanced capabilities.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ZERA (Central Queen)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Router    │  │  Strategy   │  │      Memory         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  OLLAMA  │  │  QWEN    │  │ 0xFurai  │
    │  Local   │  │  OAuth   │  │  Expert  │
    │  Models  │  │  (Cloud) │  │  Agents  │
    └──────────┘  └──────────┘  └──────────┘
```

---

## Decision Matrix: When to Use Qwen

| Task Type | Primary Model | Fallback |
|-----------|---------------|----------|
| Complex reasoning | Qwen3-Max | Ollama deepseek-r1 |
| Code generation | Qwen3-Max | Ollama qwen3 |
| Simple tasks | Qwen3-Coder | Ollama gemma3 |
| Research/web | Qwen3-Max | Tavily MCP |
| File operations | Local agent | Qwen if complex |

---

## Usage Patterns

### 1. Direct Delegation (Zera → Qwen)

```python
# Zera delegates complex coding to Qwen
def zera_delegate_to_qwen(task: str) -> str:
    cmd = f'qwen "{task}" --auth-type qwen-oauth -m openrouter/qwen/qwen3-235b-a22b -y'
    result = terminal(cmd, timeout=180)
    return result["output"]
```

### 2. Parallel Sub-Agent Spawning

```python
# Zera spawns multiple Qwen instances for parallel work
def zera_parallel_qwen(tasks: List[str]) -> List[str]:
    results = []
    for task in tasks:
        # Each runs in background
        terminal(f'qwen "{task}" -y 2>&1 &')
    
    # Wait and collect results
    # ...
```

### 3. Hierarchical Processing

```
User Request
    │
    ▼
Zera (Router)
    │
    ├── Simple? → Answer directly
    │
    ├── Medium? → Qwen Code (single)
    │
    └── Complex? → Qwen + 0xFurai agents (parallel)
```

---

## Qwen-Specific Capabilities

### Code Generation Pipeline

```
Request: "Build REST API for user management"
    │
    ▼
Qwen3-Max
    │
    ├── Generates: routes.py, models.py, schemas.py
    │
    ├── Type hints: Complete
    │
    ├── Tests: Unit + Integration
    │
    └── Documentation: docstrings + README
    │
    ▼
Zera Review
    │
    ├── Quality check
    │
    ├── Integration with existing code
    │
    └── Commit or request changes
```

### Research Pipeline

```
Request: "Analyze competitor X for features"
    │
    ▼
Qwen3-Max (with web search)
    │
    ├── Web search for X
    │
    ├── Extract features
    │
    ├── Compare with current product
    │
    └── Generate report
    │
    ▼
Zera Synthesis
    │
    └── Create actionable recommendations
```

---

## Configuration

### Environment Variables

```bash
# Qwen OAuth (set during auth flow)
export QWEN_AUTH_TYPE="qwen-oauth"

# Default model
export QWEN_DEFAULT_MODEL="openrouter/qwen/qwen3-235b-a22b"

# Auto-approve tools
export QWEN_AUTO_YOLO="false"  # true for fully autonomous
```

### Skill Loading

```markdown
When Zera needs Qwen capabilities:
1. Load skill: qwen-integration
2. Read config: configs/qwen/default.yaml
3. Check auth: qwen auth status
4. Execute with appropriate flags
```

---

## Integration with 0xFurai Pack

### Scenario: Complex Feature Implementation

```
Zera receives: "Build real-time chat with WebSockets"

1. Zera analyzes → Complex task
2. Zera delegates:
   ├── Qwen3-Max → Design architecture + core implementation
   ├── 0xFurai/expert-api → API design review
   └── 0xFurai/expert-websocket → Security review

3. Parallel execution with timeouts
4. Zera synthesizes results
5. Final integration + testing
```

### Communication Protocol

```python
# Each agent returns structured result
{
    "agent": "qwen-max",
    "status": "success",
    "output": "...",
    "files_modified": ["chat.py"],
    "confidence": 0.95,
}
```

---

## Rate Limiting & Quotas

### Qwen OAuth Free Tier

- **Limit:** 1000 requests/day
- **Warning:** At 800 requests
- **Strategy:** Use Ollama for heavy batch processing

### Load Balancing

```python
# Zera's request distribution
def select_model(task_complexity: str, remaining_quota: int) -> str:
    if remaining_quota < 200:
        return "ollama:qwen3-main:8b"  # Save Qwen quota
    
    if task_complexity == "high":
        return "qwen:qwen3-max"
    elif task_complexity == "medium":
        return "qwen:openrouter/qwen/qwen3-235b-a22b"
    else:
        return "ollama:qwen3-coder"
```

---

## Testing & Validation

### Before Production

```bash
# Test Qwen integration
qwen "Hello, respond with 'OK'" --auth-type qwen-oauth

# Check quota
qwen auth status

# Run integration tests
python tests/qwen_integration_test.py
```

### Monitoring

```python
# Track Qwen usage
metrics = {
    "qwen_requests_today": track_daily_requests("qwen"),
    "ollama_requests_today": track_daily_requests("ollama"),
    "average_response_time": calculate_avg_time("qwen"),
}
```

---

## Rollback Plan

If Qwen OAuth becomes unavailable:

1. Switch all requests to Ollama (local models)
2. Update router config to prefer Ollama
3. Notify Artem of status change
4. Continue with degraded capability

---

## File Structure

```
configs/qwen/
├── default.yaml          # Default settings
├── routing.yaml          # Routing decisions
└── models.yaml           # Model-specific configs

.agent/skills/
└── qwen-integration/
    ├── SKILL.md          # Main skill file
    └── qwen-helper.py    # Python utilities

.agent/workflows/
└── qwen-orchestration.md  # This workflow

scripts/
└── qwen-usage-monitor.sh  # Usage tracking
```

---

## Next Steps

1. [ ] Test integration with complex multi-file generation
2. [ ] Benchmark Qwen vs Ollama performance
3. [ ] Implement request quota tracking
4. [ ] Add to cron monitoring
5. [ ] Document 0xFurai + Qwen collaboration patterns
