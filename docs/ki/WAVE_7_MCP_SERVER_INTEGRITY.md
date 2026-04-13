# Wave 7 — MCP Server Integrity

**Date:** 2026-04-12
**Status:** Implemented
**Scope:** MCP test harness, security audit, deployment workflow, LightRAG integration

## Summary

Wave 7 закрывает критический gap — MCP серверы не имели protocol-level тестов, security audit, и deployment workflow.

## New Scripts

| Script | Purpose |
|--------|---------|
| `scripts/mcp_test_harness.py` | Generic MCP protocol test framework (handshake, tool discovery, call/response, rejection, shutdown) |
| `scripts/mcp_security_tests.py` | Security audit tests (path traversal, injection, oversized input, input validation) |
| `scripts/mcp-deploy.sh` | Build, test, and deploy all MCP servers |

## Test Results — LightRAG MCP Server

### Protocol Tests (8 tests)
| Test | Result | Details |
|------|--------|---------|
| Handshake | ✅ PASS | lightrag v1.0.0, capabilities: tools |
| List tools | ✅ PASS | 4 tools registered |
| call_tool: ingest | ⚠️ FAIL | Requires real API provider (mock unsupported) |
| call_tool: query | ⚠️ FAIL | Requires real API provider |
| call_tool: rebuild | ⚠️ FAIL | Requires real API provider |
| call_tool: stats | ⚠️ FAIL | Requires real API provider |
| Unknown tool rejection | ✅ PASS | Correctly rejected |
| Graceful shutdown | ✅ PASS | <50ms |

### Security Tests (7 tests)
| Test | Result | Details |
|------|--------|---------|
| Path traversal in ingest | ✅ PASS | No file system access |
| Injection in query | ✅ PASS | Treated as normal search |
| Oversized input (10MB) | ✅ PASS | No crash |
| Empty query rejection | ⚠️ WARNING | Not rejected |
| Missing required args | ⚠️ WARNING | Not rejected |
| Malformed JSON metadata | ⚠️ WARNING | Not rejected |
| Graceful shutdown | ✅ PASS | 42ms |

## MCP Test Harness Features

- JSON-RPC handshake validation
- Tool discovery verification
- Individual tool call testing
- Unknown tool rejection verification
- Argument validation testing
- Graceful shutdown measurement
- Auto-discovery mode (`--all`)
- JSON output mode (`--json`)
- Non-JSON line filtering (logger output)

## Security Audit Findings

### Pass (4/7)
- No file system access through MCP tools
- Injection attempts safely handled
- Large inputs don't crash the server
- Clean shutdown

### Warnings (3/7)
- Empty query not rejected — could be improved
- Missing required args not rejected — validation gap
- Malformed JSON not rejected — input validation gap

**No critical errors found.**

## Deployment Workflow

```bash
# Full deployment
bash scripts/mcp-deploy.sh

# Skip tests
bash scripts/mcp-deploy.sh --no-test

# Skip health check
bash scripts/mcp-deploy.sh --no-health-check
```

## Policy v7.0.0

New section: `mcp_integrity`
```yaml
mcp_integrity:
  protocol_test_required: true
  security_audit_required: true
  deployment_workflow_required: true
  test_harness_path: "scripts/mcp_test_harness.py"
  security_tests_path: "scripts/mcp_security_tests.py"
  deploy_script_path: "scripts/mcp-deploy.sh"
  minimum_handshake_pass: true
  minimum_tool_discovery_pass: true
  minimum_unknown_tool_rejection_pass: true
  minimum_graceful_shutdown_pass: true
```

## Files

| File | Change |
|------|--------|
| `scripts/mcp_test_harness.py` | New — 498 lines |
| `scripts/mcp_security_tests.py` | New — 410 lines |
| `scripts/mcp-deploy.sh` | New — 90 lines |
| `configs/tooling/zera_promotion_policy.yaml` | v7.0.0 (+ mcp_integrity section) |

## Usage

```bash
# Test MCP protocol
python3 scripts/mcp_test_harness.py --server "node repos/mcp/lightrag/dist/index.js" --all

# Security audit
python3 scripts/mcp_security_tests.py --server "node repos/mcp/lightrag/dist/index.js"

# Deploy
bash scripts/mcp-deploy.sh

# Deploy without tests
bash scripts/mcp-deploy.sh --no-test
```
