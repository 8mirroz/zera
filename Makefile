.PHONY: install test test-all test-unit test-contract test-integration test-smoke \
        test-governance test-benchmark test-regression quality doctor debug-test \
        reliability-report reliability-inventory update drift kill-switch-check \
        self-improve benchmark-report benchmark-gate clean

AGENT_OS := repos/packages/agent-os
UV       := cd $(AGENT_OS) && uv run
RELIABILITY := cd $(AGENT_OS) && uv run python ../../../scripts/reliability_orchestrator.py
TEST ?=

# ── Setup ──────────────────────────────────────────────────────────────────
install:
	@echo "→ Installing Node.js dependencies..."
	cd repos/packages/mcp-profile-manager && npm install
	cd repos/packages/mcp_context && npm install
	@echo "→ Installing Python dependencies (uv)..."
	cd $(AGENT_OS) && uv sync
	cd repos/packages/design-system && (uv sync || pip install -r requirements.txt)

# ── Reliability Platform ───────────────────────────────────────────────────
test:
	@$(MAKE) test-smoke

test-all:
	@$(RELIABILITY) run --profile all_non_benchmark

test-unit:
	@$(RELIABILITY) run --suite unit

test-contract:
	@$(RELIABILITY) run --suite contract

test-integration:
	@$(RELIABILITY) run --suite integration

test-smoke:
	@$(RELIABILITY) run --suite smoke

test-governance:
	@$(RELIABILITY) run --suite governance

test-benchmark:
	@$(RELIABILITY) run --suite benchmark

test-regression:
	@$(RELIABILITY) run --suite regression

quality:
	@bash scripts/run_quality_checks.sh

doctor:
	@$(RELIABILITY) run --suite doctor

debug-test:
	@if [ -z "$(TEST)" ]; then echo "Usage: make debug-test TEST=<node>"; exit 2; fi
	@$(RELIABILITY) debug-test --test "$(TEST)"

reliability-report:
	@$(RELIABILITY) report

reliability-inventory:
	@$(RELIABILITY) inventory

# ── Auto-update cycle ──────────────────────────────────────────────────────
update:
	@echo "→ Running AutoUpdateEngine (drift + kill-switch + memory eval)..."
	$(UV) python3 ../../../scripts/auto_update.py

drift:
	@echo "→ Drift detection only..."
	$(UV) python3 ../../../scripts/drift_check.py || true

kill-switch-check:
	@echo "→ Kill-switch check..."
	$(UV) python3 ../../../scripts/kill_switch_check.py || true

self-improve:
	@echo "→ Self-improvement loop (update + test-smoke)..."
	$(MAKE) update
	$(MAKE) test-smoke

# ── Benchmarks ─────────────────────────────────────────────────────────────
benchmark-report:
	@$(RELIABILITY) run --suite benchmark --continue-on-fail

benchmark-gate:
	@$(RELIABILITY) run --suite benchmark

# ── Cleanup ────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── LightRAG ───────────────────────────────────────────────────────────────
LIGHTRAG := repos/mcp/lightrag

lightrag-install:
	@echo "→ Installing LightRAG dependencies..."
	cd $(LIGHTRAG) && npm install

lightrag-build:
	@echo "→ Building LightRAG..."
	cd $(LIGHTRAG) && npm run build

lightrag-test:
	@echo "→ Running LightRAG tests..."
	cd $(LIGHTRAG) && npm test

lightrag-eval:
	@echo "→ Running LightRAG evaluation suite..."
	cd $(LIGHTRAG) && node dist/tests/evaluation.js

lightrag-bench:
	@echo "→ Running LightRAG benchmarks..."
	cd $(LIGHTRAG) && node dist/tests/benchmarks.js

lightrag-ingest:
	@if [ -z "$(FILE)" ] && [ -z "$(TEXT)" ]; then echo "Usage: make lightrag-ingest FILE=path/to/file.md or TEXT=\"content\""; exit 2; fi
	cd $(LIGHTRAG) && npm run ingest -- $(if $(FILE),--file $(FILE)) $(if $(TEXT),--text "$(TEXT)")

lightrag-query:
	@if [ -z "$(Q)" ]; then echo "Usage: make lightrag-query Q=\"your question\""; exit 2; fi
	cd $(LIGHTRAG) && npm run query -- --query "$(Q)" $(if $(DEBUG),--debug)

lightrag-stats:
	@echo "LightRAG stats command requires manual MCP server query or programmatic API"
	@echo "Use: npm run query in repos/mcp/lightrag/ or call pipeline.stats() directly"

lightrag-rebuild:
	@echo "LightRAG index rebuild requires MCP server or programmatic API"
	@echo "Use: pipeline.reBuildIndex() in code or lightrag_rebuild_index via MCP"

lightrag: lightrag-build lightrag-test
