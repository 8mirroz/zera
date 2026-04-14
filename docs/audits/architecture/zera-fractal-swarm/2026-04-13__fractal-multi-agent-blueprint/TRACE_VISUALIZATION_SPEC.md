# Trace Visualization Specification — Wave 5

> **Wave:** 5 — Trace + Dashboard + Visualization Architecture
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–4
> **Aligned with:** `trace_schema.json` v2.1, Entity Schema v2, Execution State Machine

---

## 1. Scope

This document specifies how append-only JSONL trace data (events.jsonl, spans.jsonl, and legacy logs/agent_traces.jsonl) is parsed, indexed, and rendered in the dashboard. It covers color coding, filtering, search, correlation, and performance requirements.

---

## 2. Trace Data Format

### 2.1 Canonical Format (v2)

Each line in `events.jsonl` or `spans.jsonl` is a single JSON object:

```json
{"event_id":"evt_001","event_type":"task.state_transition","timestamp":"2026-04-13T10:00:03.000Z","entity_id":"task_001","entity_type":"task","run_id":"run_2026041310000001","correlation_id":"corr_run001_wave001_wf001_task001","severity":"info","payload":{"from_state":"ready","to_state":"running","transition":"acquire","worker_id":"worker_1"},"source":"scheduler","tags":["state_transition"]}
```

### 2.2 Legacy Format (v1 / mixed)

Legacy traces may contain:

```json
{"schema_version": "v1", "entry": {"ts": 1713000000, "event_type": "agent_start", "payload": {...}}}
```

or:

```json
{"ts": 1713000000, "event_type": "route_decision", "payload": {"task_type": "T3", "complexity": "C3"}}
```

### 2.3 Normalization Layer

All trace data passes through a normalization layer before rendering:

```python
def normalize_event(raw: dict) -> Event:
    """Normalize v1 or v2.1 event to canonical v2 Event."""
    if raw.get("schema_version") == "v1" and "entry" in raw:
        raw = raw["entry"]
    elif "schema_version" not in raw and isinstance(raw.get("ts"), (int, float)):
        # v1 legacy envelope: ts as unix epoch
        raw["timestamp"] = datetime.fromtimestamp(raw["ts"], tz=UTC).isoformat()
        del raw["ts"]

    return Event(
        event_id=raw.get("event_id", generate_id()),
        event_type=raw.get("event_type", "unknown"),
        timestamp=raw.get("timestamp") or raw.get("ts", ""),
        entity_id=raw.get("entity_id", raw.get("run_id", "")),
        entity_type=raw.get("entity_type", infer_entity_type(raw)),
        run_id=raw.get("run_id", ""),
        correlation_id=raw.get("correlation_id", ""),
        severity=raw.get("level", raw.get("severity", "info")),
        payload=raw.get("data", raw.get("payload", {})),
        source=raw.get("source", raw.get("component", "unknown")),
        tags=raw.get("tags", []),
        is_legacy=raw.get("schema_version") != "v2",
    )
```

**Migration note:** Legacy events are flagged with `is_legacy: true` in the UI. The migration tool (Phase 2) will convert v1 traces to v2 format.

---

## 3. Color Coding Scheme

### 3.1 Severity Colors

| Severity | Color (hex) | Background | Icon | Use |
|----------|-------------|------------|------|-----|
| `debug` | `#6B7280` | Transparent | `·` | Trace-level detail, hidden by default |
| `info` | `#3B82F6` | Transparent | `i` | Normal operation events |
| `warn` | `#F59E0B` | `rgba(245, 158, 11, 0.1)` | `!` | Recoverable issues, degraded mode |
| `error` | `#EF4444` | `rgba(239, 68, 68, 0.15)` | `✗` | Failures, non-recoverable errors |
| `critical` | `#DC2626` | `rgba(220, 38, 38, 0.2)` | `⚠` | System-level emergencies, safe-mode |

### 3.2 Entity Type Colors

| Entity Type | Accent Color | Usage |
|-------------|-------------|-------|
| `run` | `#8B5CF6` (violet) | Run-level events, lifecycle |
| `wave` | `#6366F1` (indigo) | Wave boundaries |
| `workflow` | `#3B82F6` (blue) | Workflow execution |
| `task` | `#06B6D4` (cyan) | Task lifecycle events |
| `subtask` | `#14B8A6` (teal) | Subtask decomposition |
| `action` | `#10B981` (emerald) | Atomic operations |
| `tool_call` | `#84CC16` (lime) | Tool invocations |

### 3.3 State Colors (Kanban + Node Graph)

| State | Color | Visual Treatment |
|-------|-------|-----------------|
| `queued` | `#6B7280` (gray) | Dimmed, dashed border |
| `ready` | `#3B82F6` (blue) | Solid border, subtle glow |
| `running` | `#06B6D4` (cyan) | Solid fill, pulsing glow animation |
| `waiting` | `#F59E0B` (amber) | Amber border, clock icon |
| `blocked` | `#F97316` (orange) | Orange fill, stop icon |
| `validating` | `#8B5CF6` (violet) | Violet border, spinner icon |
| `completed` | `#10B981` (green) | Green fill, checkmark icon |
| `failed` | `#EF4444` (red) | Red fill, X icon |
| `compensated` | `#DC2626` (dark red) | Red fill with strikethrough |
| `escalated` | `#BE185D` (rose) | Rose fill, alert icon, pulsing |
| `replayed` | `#A855F7` (purple) | Purple fill, replay icon |

### 3.4 Component Colors (trace_schema.json `component` field)

| Component | Color | Icon |
|-----------|-------|------|
| `triage` | `#EC4899` (pink) | `T` |
| `router` | `#6366F1` (indigo) | `R` |
| `agent` | `#06B6D4` (cyan) | `A` |
| `tool` | `#84CC16` (lime) | `⚙` |
| `verifier` | `#8B5CF6` (violet) | `V` |
| `ralph` | `#F59E0B` (amber) | `Σ` |
| `retro` | `#14B8A6` (teal) | `⟲` |
| `policy` | `#EF4444` (red) | `P` |
| `memory` | `#3B82F6` (blue) | `M` |
| `eval` | `#A855F7` (purple) | `E` |
| `harness` | `#F97316` (orange) | `H` |
| `ml` | `#EC4899` (pink) | `ML` |

### 3.5 Accessibility — High Contrast Mode

When `reduce_motion` or `high_contrast` is enabled:

| Adjustment | Detail |
|------------|--------|
| High contrast | All colors shift to WCAG AAA compliant contrasts. Background tints removed, replaced with solid fills and border-only treatment. |
| Colorblind safe | Entity types distinguished by shape + color (not color alone). State states distinguished by icon + color. |
| No color dependency | Every color-coded element has a text label or icon fallback. |

---

## 4. Filtering and Search

### 4.1 Filter Dimensions

| Dimension | Type | Options |
|-----------|------|---------|
| `event_type` | Multi-select | All 40+ types from trace_schema.json v2.1 |
| `severity` | Multi-select | debug, info, warn, error, critical |
| `entity_type` | Multi-select | run, wave, workflow, task, subtask, action, tool_call |
| `entity_id` | Text match | Exact or prefix match |
| `run_id` | Text match | Exact match |
| `component` | Multi-select | triage, router, agent, tool, verifier, etc. |
| `source` | Multi-select | scheduler, worker_1, worker_2, etc. |
| `time_range` | Range picker | Absolute (ISO-8601) or relative (last 5m, 1h, 1d) |
| `tags` | Multi-select | State transition, tool_call, lifecycle, etc. |
| `correlation_id` | Text match | Prefix or full match |
| `search` | Full-text | Search across event payload fields |

### 4.2 Filter Composition

Filters combine with **AND** logic between dimensions, **OR** logic within multi-select dimensions.

```
(event_type IN [selected_types])
AND (severity IN [selected_severities])
AND (entity_type IN [selected_entity_types])
AND (time_range BETWEEN start AND end)
AND (search MATCHES payload_text)
```

### 4.3 Saved Filter Presets

| Preset Name | Filter | Use Case |
|-------------|--------|----------|
| **Errors only** | severity: error, critical | Quick failure scan |
| **State transitions** | event_type: *.state_transition | Lifecycle tracking |
| **Tool calls** | event_type: tool_call.* | Performance analysis |
| **Policy events** | component: policy | Governance audit |
| **Retry & recovery** | event_type: retry.*, escalation.* | Reliability review |
| **Operator view** | severity: warn,error,critical + state: blocked,escalated,failed | Mission control |
| **Full trace** | No filters | Complete audit trail |

### 4.4 Search Implementation

Full-text search uses BM25 ranking over event payload fields:

```python
from rank_bm25 import BM25Okapi

class EventSearch:
    def __init__(self, events: list[Event]):
        # Tokenize payload text for indexing
        self.corpus = [tokenize(e.payload_text) for e in events]
        self.bm25 = BM25Okapi(self.corpus)
        self.events = events

    def search(self, query: str, top_k: int = 50) -> list[Event]:
        tokens = tokenize(query)
        scores = self.bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.events[i] for i in top_indices if scores[i] > 0]
```

**Performance:** BM25 index builds in O(N) time. Search is O(N * query_tokens). For 10K events, search completes in <100ms.

---

## 5. Correlation Across Runs

### 5.1 Correlation Mechanisms

| Mechanism | Field | Purpose |
|-----------|-------|---------|
| **Correlation ID** | `correlation_id` | Links all events from run → wave → workflow → task → subtask → action → tool_call |
| **Run ID prefix** | `run_id` starts with `run_YYYYMMDD` | Groups runs by date |
| **Mission ID** | `mission.id` in run entity | Groups runs by originating mission |
| **Workflow name** | `workflow.name` | Same workflow across different runs |
| **Task name** | `task.name` | Same task pattern across runs |

### 5.2 Cross-Run Views

| View | Correlation Key | Display |
|------|----------------|---------|
| **Mission timeline** | `mission.id` | All runs for a mission, ordered by time |
| **Workflow comparison** | `workflow.name` | Side-by-side: same workflow, different runs (latency, cost, success rate) |
| **Task pattern analysis** | `task.name` | Aggregated stats for a task pattern across all runs |
| **Agent performance** | `lease.worker_id` | Per-agent metrics across all runs |

### 5.3 Correlation Query Examples

```
# All events for a specific task
correlation_id STARTS_WITH "corr_run001_wave001_wf001_task003"

# All runs for mission "dark-mode-implementation"
mission.id = "dark-mode-implementation"

# Compare wf_001 performance across runs
workflow.name = "implement-dark-mode" GROUP BY run_id

# Agent worker_1 performance
lease.worker_id = "worker_1" GROUP BY run_id
```

---

## 6. Performance Requirements

### 6.1 Rendering Budgets

| Scenario | Event Count | Target Render Time | Technique |
|----------|-------------|-------------------|-----------|
| Small run | < 1K events | < 200ms | Full DOM render |
| Medium run | 1K–10K events | < 500ms | Virtual scrolling + windowing |
| Large run | 10K–100K events | < 1s | Virtual scrolling + aggregation buckets |
| Very large | 100K+ events | < 2s | Server-side aggregation + progressive loading |

### 6.2 Virtual Scrolling Strategy

For timeline and waterfall views, use virtual scrolling:

```
Viewport height: 800px
Row height: 32px (event row)
Visible rows: 25
Buffer rows: 10 above + 10 below
Total rendered rows: 45 (regardless of total event count)

Scroll position → calculate visible range → render only those rows
```

Implementation: React `react-window` or equivalent. Each row is a lightweight component.

### 6.3 Aggregation Buckets (Large Runs)

For runs with >10K events, aggregate into time buckets for the overview:

```python
def aggregate_events(events: list[Event], bucket_duration_ms: int = 5000) -> list[Bucket]:
    """Aggregate events into time buckets for overview rendering."""
    buckets = {}
    for event in events:
        bucket_key = int(event.timestamp_ms // bucket_duration_ms)
        if bucket_key not in buckets:
            buckets[bucket_key] = Bucket(
                start_ms=bucket_key * bucket_duration_ms,
                event_count=0,
                error_count=0,
                event_types=set(),
                entities=set(),
            )
        bucket = buckets[bucket_key]
        bucket.event_count += 1
        if event.severity in ("error", "critical"):
            bucket.error_count += 1
        bucket.event_types.add(event.event_type)
        bucket.entities.add(event.entity_id)
    return sorted(buckets.values(), key=lambda b: b.start_ms)
```

**Click to expand:** Clicking a bucket zooms into that time range, showing individual events. Progressive zoom: bucket → smaller buckets → individual events.

### 6.4 Index Build Performance

| Events | Index Build Time | Memory |
|--------|-----------------|--------|
| 1K | < 50ms | ~200 KB |
| 10K | < 500ms | ~2 MB |
| 100K | < 3s | ~20 MB |
| 1M | < 30s | ~200 MB |

Index builds happen on startup. During operation, new events are appended to the index incrementally (O(1) per event).

### 6.5 Parsing Performance

JSONL parsing target: **10K lines/second** minimum.

```python
import orjson  # Faster than json.loads

def parse_jsonl(filepath: str) -> Generator[dict, None, None]:
    """Parse JSONL file line by line with orjson for speed."""
    with open(filepath, "rb") as f:
        for line in f:
            line = line.strip()
            if line:
                yield orjson.loads(line)
```

Benchmark: `orjson` parses ~500K lines/second on Apple Silicon. Well above the 10K target.

---

## 7. Event Rendering Rules

### 7.1 Timeline Event Row Format

```
┌──────┬──────┬──────────────────┬───────────────────────┬──────────────┐
│ Time │ Type │ Entity           │ Summary               │ Duration     │
├──────┼──────┼──────────────────┼───────────────────────┼──────────────┤
│10:00:│task. │task_003          │ready → running        │ —            │
│03.0  │state │  [workflow:wf_001]│(acquire, worker_1)   │              │
│      │_tran │                  │                       │              │
│      │sition│                  │                       │              │
└──────┴──────┴──────────────────┴───────────────────────┴──────────────┘
```

### 7.2 Span Rendering (Waterfall)

```
task_003.execute ──────────────────────────────────────────────────────── 132000ms
  ├─ tc_001 mcp:filesystem:read_file ───── 45ms
  ├─ tc_002 mcp:context7:query ─────────── 230ms
  ├─ tc_003 shell:grep ─────────────────── 120ms
  ├─ tc_004 mcp:filesystem:edit ───── 1200ms
  └─ tc_005 verifier:check ─────────────── 890ms
```

Span bars use:
- **Width** = duration (log scale for large ranges)
- **Color** = entity type accent color
- **Opacity** = severity (errors are fully opaque)
- **Hover** = tooltip with full span details

### 7.3 Event Grouping in Timeline

Events are grouped by correlation_id prefix and rendered as collapsible trees:

```
▶ task_003 (23 events)
  ▶ state transitions (8)
    ready → running (acquire, worker_1)
    running → validating (submit_for_validation)
    validating → completed (validate_pass)
  ▶ tool calls (5)
    tc_001 mcp:filesystem:read_file [45ms] ✓
    tc_002 mcp:context7:query [230ms] ✓
    ...
  ▶ memory operations (4)
  ▶ verification (3)
  ▶ artifacts (3)
```

**Auto-expand rules:**
- Error events: always expanded
- Selected entity: expanded
- All other groups: collapsed by default

---

## 8. Legacy Trace Handling

### 8.1 Detection

On startup, the trace parser scans `logs/agent_traces.jsonl` and flags each line:

```python
def classify_trace_line(line: str) -> TraceVersion:
    obj = json.loads(line)
    if "schema_version" in obj and obj["schema_version"] == "v2":
        return TraceVersion.V2
    if "schema_version" in obj and obj["schema_version"] == "v1":
        return TraceVersion.V1
    if "ts" in obj and isinstance(obj["ts"], (int, float)):
        return TraceVersion.V1_LEGACY
    return TraceVersion.UNKNOWN
```

### 8.2 Rendering Legacy Events

Legacy events display with a muted badge:

```
[v1] route_decision  10:00:01  task_type=T3 complexity=C3 model_tier=quality
```

The `[v1]` badge is:
- Gray color (`#6B7280`)
- Tooltip: "Legacy trace event. Migrate to v2 format for full functionality."
- Not included in v2-only filters (unless "Include legacy" checkbox is enabled)

### 8.3 Mixed Trace Timeline

When v1 and v2 events coexist in the same timeline:

1. Normalize all events to v2 format (via normalization layer)
2. Render with full v2 color coding
3. Add `[v1]` badge to legacy-derived events
4. Offer filter: "v2 only" / "Include legacy"

---

## 9. Export and Sharing

### 9.1 Export Formats

| Format | Content | Use Case |
|--------|---------|----------|
| **JSONL (v2)** | Filtered events, normalized to v2 | Re-import, offline analysis |
| **JSON (array)** | Filtered events as JSON array | API consumption |
| **CSV** | Flattened event fields | Spreadsheet analysis |
| **PNG (screenshot)** | Current view rendering | Sharing in docs/issues |
| **PDF report** | Formatted report with timeline, metrics, artifacts | Audit submission |

### 9.2 Shareable Links

Every filtered view generates a shareable URL:

```
/dashboard?run=run_001&view=timeline&filters[event_type]=task.state_transition&filters[severity]=error&time_range=last_1h
```

The URL encodes all active filters, view state, and time range.

---

## 10. Implementation Checklist

- [ ] JSONL parser with orjson, 10K lines/sec minimum
- [ ] Event normalization layer (v1 → v2)
- [ ] In-memory index (by_run, by_entity, by_type, by_state, timeline)
- [ ] BM25 search index for full-text search
- [ ] Virtual scrolling for timeline (react-window)
- [ ] Aggregation buckets for large runs (>10K events)
- [ ] Color coding system (severity, entity type, state, component)
- [ ] Filter system (multi-select, text, range, full-text)
- [ ] Saved filter presets (7 presets)
- [ ] Correlation ID navigation
- [ ] Legacy event badge and filter
- [ ] Export (JSONL, JSON, CSV, PNG, PDF)
- [ ] Shareable URL encoding
- [ ] High contrast mode
- [ ] Colorblind-safe icons
