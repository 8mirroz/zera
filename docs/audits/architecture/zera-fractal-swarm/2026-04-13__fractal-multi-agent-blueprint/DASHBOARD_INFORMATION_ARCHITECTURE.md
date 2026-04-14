# Dashboard Information Architecture — Wave 5

> **Wave:** 5 — Trace + Dashboard + Visualization Architecture
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–4 (Audit through Target Blueprint)
> **Aligned with:** `trace_schema.json` v2.1, Entity Schema, Execution State Machine, Parallelization Policy

---

## 1. Design Goals

The dashboard exists to answer three questions in under 5 seconds:

1. **What is running right now?** (operational awareness)
2. **Is anything broken or blocked?** (exception detection)
3. **Where should I look next?** (guided drill-down)

It is **not** a data dump. It is a cognitive interface that surfaces signal and suppresses noise.

---

## 2. User Personas

### 2.1 Persona Matrix

| Persona | Role | Primary Question | Session Length | Tolerance for Noise |
|---------|------|------------------|----------------|---------------------|
| **Operator** | Runs missions, monitors execution, resolves escalations | "Is my mission progressing? Do I need to intervene?" | 2–15 min (frequent check-ins) | Low — wants immediate signal |
| **Architect** | Designs workflows, analyzes performance, tunes policies | "Where are the bottlenecks? Are the patterns correct?" | 15–60 min (deep analysis) | Medium — wants aggregate + drill |
| **Auditor** | Reviews completed runs for compliance, cost, correctness | "Did this run follow policy? What was the cost? Were gates honored?" | 30–120 min (post-hoc review) | Very low — wants complete audit trail |

### 2.2 Persona → View Mapping

| View | Operator | Architect | Auditor |
|------|:--------:|:---------:|:-------:|
| Mission Overview | Primary | Secondary | Tertiary |
| Live Kanban | Primary | Secondary | — |
| Timeline Playback | Secondary | Primary | Secondary |
| Node Graph | — | Primary | Secondary |
| Metrics Dashboard | Secondary | Primary | Primary |
| Waterfall Tool Calls | — | Secondary | Primary |
| Artifact Explorer | Secondary | Secondary | Primary |

---

## 3. Information Hierarchy

### 3.1 Priority Levels

| Level | Name | Content | Refresh | Visual Weight |
|-------|------|---------|---------|---------------|
| **P0** | Alert Zone | Active escalations, safe-mode triggers, failed missions | Real-time (push) | Red banner, pulsing |
| **P1** | Mission Status | Active runs, progress %, ETA, cost accumulator | 5s poll | Prominent cards |
| **P2** | Entity Detail | Kanban, timeline, node graph for selected entity | 5s poll / on-select | Content area |
| **P3** | Metrics & Trends | p50/p95 latency, success rate, intervention rate, cost trend | 30s poll | Sidebar / bottom panel |
| **P4** | Historical Archive | Completed runs, audit trails, pattern analysis | On-demand (no auto-refresh) | Explorer / search |

### 3.2 Information Density by Persona

```
Operator:     P0 ▓▓▓▓▓  P1 ▓▓▓▓  P2 ▓▓  P3 ▓  P4 —
Architect:    P0 ▓▓▓▓   P1 ▓▓▓   P2 ▓▓▓▓  P3 ▓▓▓▓  P4 ▓▓
Auditor:      P0 ▓▓     P1 ▓▓    P2 ▓▓▓  P3 ▓▓▓  P4 ▓▓▓▓▓
```

---

## 4. Dashboard Layouts per Persona

### 4.1 Operator Layout — "Mission Control"

```
┌─────────────────────────────────────────────────────────────────┐
│  P0: ALERT ZONE (hidden when no alerts)                         │
│  [!] 2 escalations pending  |  [!] wave_003 blocked on MCP     │
├─────────────────────────────────────────────────────────────────┤
│  P1: ACTIVE MISSIONS (card grid, 1–3 cards)                     │
│  ┌─────────────────────┐ ┌─────────────────────┐               │
│  │ run_2026041310000001 │ │ run_2026041310050002 │               │
│  │ Dark Mode Impl       │ │ Router Refactor      │               │
│  │ ████░░░░ 45%         │ │ ████████░░ 82%       │               │
│  │ Wave 2/5 • ETA 4m    │ │ Wave 4/5 • ETA 1m    │               │
│  │ $1.23 / $10 budget   │ │ $4.56 / $10 budget   │               │
│  │ [View] [Stop]        │ │ [View] [Stop]        │               │
│  └─────────────────────┘ └─────────────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│  P2: LIVE KANBAN (for selected mission)                         │
│  queued(2) │ ready(1) │ running(3) │ waiting(1) │ done(12)     │
│  [task]    │ [task]   │ [task]     │ [task]     │ [task]       │
│            │          │ [task]     │            │ [task]       │
│            │          │ [subtask]  │            │ [task]       │
├─────────────────────────────────────────────────────────────────┤
│  P3: METRICS STRIP (compact, bottom)                            │
│  p50: 2.3s  p95: 8.1s  |  Success: 97%  |  Interventions: 2    │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Auto-refreshes P1/P2 every 5 seconds via Server-Sent Events (SSE)
- P0 alerts push immediately via SSE
- Click any mission card to expand full Kanban + Timeline for that run
- Click any entity card in Kanban to open detail panel

### 4.2 Architect Layout — "System Observatory"

```
┌─────────────────────────────────────────────────────────────────┐
│  P0: ALERT ZONE                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Tab bar: [Node Graph] [Timeline] [Waterfall] [Metrics]         │
├─────────────────────────────────────────────────────────────────┤
│  P2: NODE GRAPH (default view)                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ◉ Mission                                                  ││
│  │    └── ◉ Program                                            ││
│  │         ├── ◉ Wave 1 ──▶ ◉ Wave 2 ──▶ ◉ Wave 3             ││
│  │         │        │                                            ││
│  │         │        ├── ◉ wf_001                                ││
│  │         │        │     ├── ● task_001 (completed)            ││
│  │         │        │     ├── ● task_002 (completed)            ││
│  │         │        │     └── ◉ task_003 (running) ──▶ tc_001  ││
│  │         │        │                          └──▶ tc_002     ││
│  │         │        └── ◉ wf_002                                ││
│  │         │              └── ◯ task_004 (waiting)              ││
│  │         └── ◉ Wave 2                                        ││
│  │                                                              ││
│  │  Legend: ● completed  ◉ running  ◯ waiting  ○ queued  ✗ failed ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  P3: METRICS PANEL (right sidebar, collapsible)                 │
│  Latency Distribution    │  Tool Call Breakdown                 │
│  ▓▓▓▓▓░░░░░ p50: 2.3s   │  mcp:filesystem  ▓▓▓▓▓▓ 45%         │
│  ▓▓▓▓▓▓▓▓▓░ p95: 8.1s   │  shell:pytest    ▓▓▓░░░ 28%         │
│  ▓▓▓▓▓▓▓▓▓▓ p99: 12.4s  │  mcp:context7    ▓▓░░░░ 18%         │
│  Success Rate Trend      │  Cost Accumulator                    │
│  100% ────┐              │  $5.79 total                         │
│   95% ────┤──────        │  by task: task_003 $2.10             │
│   90% ────┘              │  by tool: mcp:filesystem $1.80       │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- All views share the same entity selector (run/wave/workflow/task)
- Node graph supports zoom, pan, click-to-expand
- Timeline supports playback controls (play/pause/scrub/speed)
- Waterfall shows tool call latency/token/cost per entity
- Metrics panel updates every 30 seconds

### 4.3 Auditor Layout — "Evidence Room"

```
┌─────────────────────────────────────────────────────────────────┐
│  Search & Filter Bar                                            │
│  [Run ID] [Date Range ▼] [Status ▼] [Tier ▼] [Agent ▼] [Search] │
├─────────────────────────────────────────────────────────────────┤
│  Results: 23 runs found  |  Sort: [Date ▼]  [Cost ▼]  [Duration]│
├─────────────────────────────────────────────────────────────────┤
│  Run Table (paginated, sortable columns)                        │
│  ┌──────┬────────────┬──────────┬────────┬──────┬───────┬─────┐│
│  │Run ID│Mission     │Duration  │Waves   │Cost  │Status │Tier ││
│  ├──────┼────────────┼──────────┼────────┼──────┼───────┼─────┤│
│  │run_01│Dark Mode   │12m 34s   │5/5     │$5.79 │Done   │C3   ││
│  │run_02│Router Fix  │8m 12s    │3/3     │$3.21 │Done   │C2   ││
│  │run_03│Auth Refactor│—        │1/5     │$1.45 │Failed │C4   ││
│  └──────┴────────────┴──────────┴────────┴──────┴───────┴─────┘│
├─────────────────────────────────────────────────────────────────┤
│  Detail Panel (click any row)                                   │
│  [Timeline] [Waterfall] [Artifacts] [Policy Gates] [Full Trace] │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Timeline: Full event sequence with state transitions         ││
│  │ Waterfall: Tool call latency/token/cost breakdown            ││
│  │ Artifacts: All produced files with checksums and lineage     ││
│  │ Policy Gates: All gate decisions with timestamps             ││
│  │ Full Trace: Raw JSONL download / inline viewer               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- All data is historical (no auto-refresh)
- Search supports full-text across event payloads
- Export: JSONL, CSV, PDF report
- Lineage view shows artifact dependency graph
- Policy gate audit: every gate decision with rationale

---

## 5. Data Sources and Refresh Rates

### 5.1 Source Map

| Data Source | Format | Location | Consumers |
|-------------|--------|----------|-----------|
| **events.jsonl** | Append-only JSONL | `.agents/store/runs/{run_id}/.../events.jsonl` | Timeline, Kanban, Metrics |
| **spans.jsonl** | Append-only JSONL | `.agents/store/runs/{run_id}/.../spans.jsonl` | Waterfall, Timeline |
| **state.json** | Atomic JSON | `.agents/store/runs/{run_id}/.../state.json` | Kanban, Mission Status |
| **artifacts/** | Files + metadata JSON | `.agents/store/runs/{run_id}/.../artifacts/` | Artifact Explorer |
| **checkpoints/** | JSON snapshots | `.agents/store/runs/{run_id}/.../checkpoints/` | Recovery, Timeline |
| **logs/agent_traces.jsonl** | Legacy JSONL (v1+v2.1 mixed) | Project root | Migration layer, backward compat |

### 5.2 Refresh Strategy

| Component | Strategy | Interval | Rationale |
|-----------|----------|----------|-----------|
| P0 Alert Zone | **Push** (SSE event) | Immediate | Critical path — no polling delay |
| P1 Mission Cards | **SSE + heartbeat** | 5s or on state change | Balances freshness with I/O |
| P2 Entity Views | **SSE + diff** | On state change | Only re-render changed entities |
| P3 Metrics | **Poll** | 30s | Aggregate computation, acceptable lag |
| P4 Archive | **On-demand** | N/A | Historical, no freshness requirement |

### 5.3 Data Flow Pipeline

```
Workers ──(append)──▶ events.jsonl / spans.jsonl
                       │
                       ▼
               Trace Aggregator (in-process, asyncio)
                       │
                       ├──▶ In-memory index (by run_id, entity_id, event_type, timestamp)
                       │
                       ├──▶ Metrics aggregator (sliding window: 1m, 5m, 30m)
                       │
                       └──▶ SSE broadcaster (to connected dashboard clients)
                               │
                               ▼
                       Dashboard UI (browser / terminal)
```

### 5.4 Index Structure (In-Memory)

```python
@dataclass
class TraceIndex:
    """In-memory index for fast dashboard queries."""
    by_run: dict[str, list[Event]]              # All events for a run
    by_entity: dict[str, list[Event]]            # Events per entity
    by_type: dict[str, list[Event]]              # Events per event_type
    by_state: dict[str, list[EntityState]]       # Current entities per state
    timeline: SortedList[tuple[str, Event]]      # (timestamp, event) ordered
    metrics: SlidingWindowMetrics                # p50, p95, success_rate, etc.
    artifacts: dict[str, ArtifactMetadata]        # artifact_id → metadata
```

Rebuild strategy: On startup, stream all JSONL files into the index (~10K events in <1s). During operation, append new events as they arrive.

---

## 6. Drill-Down Paths

### 6.1 Primary Drill-Down Hierarchy

```
Mission Overview
  └── Click run card
        └── Wave Overview
              └── Click wave
                    └── Workflow List (with dependency graph)
                          └── Click workflow
                                └── Task Kanban
                                      └── Click task
                                            ├── Timeline (events + spans)
                                            ├── Node Graph (subtask/action tree)
                                            ├── Waterfall (tool calls)
                                            └── Artifacts (produced files)
                                                  └── Click artifact
                                                        ├── File preview
                                                        ├── Lineage graph
                                                        └── Download
```

### 6.2 Cross-Cutting Drill-Downs

| From | To | Trigger |
|------|-----|---------|
| Metrics: high p95 latency | Waterfall view | Click metric anomaly |
| Kanban: blocked entity | Policy gate log | Click blocked card |
| Timeline: error event | Raw trace context | Click error event |
| Artifact: failed checksum | Tool call trace | Click failed artifact |
| Node graph: failed branch | Retry/escalation log | Click failed node |

### 6.3 Context Preservation Rule

Every drill-down maintains **upward context**: the parent entity breadcrumb is always visible, and the user can return to any ancestor view without losing their position.

```
Breadcrumb: Mission > run_001 > wave_002 > wf_001 > task_003
            [Mission] [run_001] [wave_002] [wf_001] [task_003]
                                                             ▲
                                                Current view (click any ancestor to navigate)
```

---

## 7. View State Management

### 7.1 URL-Encoded View State

All dashboard state is encoded in the URL for shareability and bookmarkability:

```
/dashboard?run=run_2026041310000001&wave=wave_002&view=kanban&focus=task_003
/dashboard?run=run_2026041310000001&view=timeline&speed=2x&range=60s
/dashboard?run=run_2026041310000001&view=waterfall&entity=task_003
/dashboard?view=archive&date_from=2026-04-01&status=completed&tier=C4
```

### 7.2 View State Schema

```typescript
interface DashboardState {
  run_id?: string;          // Selected run
  wave_id?: string;         // Selected wave (optional)
  workflow_id?: string;     // Selected workflow (optional)
  entity_id?: string;       // Focused entity
  view: 'kanban' | 'timeline' | 'node-graph' | 'waterfall' | 'metrics' | 'artifacts' | 'archive';
  timeline?: {
    speed: 0.25 | 0.5 | 1 | 2 | 4 | 8;
    range: 'all' | `${number}s` | `${number}m`;
    position: string;       // ISO-8601 timestamp
    playing: boolean;
  };
  filters?: {
    event_types?: string[];
    severity?: string[];
    entities?: string[];
    search?: string;
  };
}
```

---

## 8. Empty States and Error Handling

| Scenario | Display |
|----------|---------|
| No active missions | "No active missions. Submit a task to begin." + [Submit Task] button |
| Run has no events yet | "Run created. Waiting for first event..." + spinner |
| Trace file corrupted | "Trace data corrupted at line {N}. Showing {M} valid events." + [Download Raw] |
| No artifacts for entity | "No artifacts produced by this entity." |
| SSE connection lost | "Live connection lost. Showing last known state. [Reconnect]" |
| Entity not found | "Entity {id} not found. It may have been deleted or the run_id is incorrect." |

---

## 9. Implementation Notes

### 9.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React + TypeScript + D3.js / React Flow | Node graph, timeline, waterfall all supported |
| Real-time | Server-Sent Events (SSE) | Simpler than WebSocket, sufficient for dashboard |
| Backend | FastAPI (Python, in-process with execution engine) | Single process, no network overhead |
| Storage | In-memory index + JSONL files | No database needed for Phase 1 |
| Search | BM25 (in-memory, Python `rank_bm25`) | Sufficient for event search at expected scale |

### 9.2 Phase 1 Scope

- Single-process dashboard server (FastAPI + SSE)
- Browser-based UI (React SPA, served by FastAPI)
- Read-only: no dashboard-to-engine writes
- Index rebuilds from JSONL on startup
- Supports 10K events per run, up to 10 concurrent runs

### 9.3 Phase 2 Scope (Future)

- PostgreSQL for entity state (replaces in-memory index)
- WebSocket for bidirectional control (stop/pause/resume from dashboard)
- Distributed deployment (dashboard as separate service)
- Embedded trace viewer (like Jaeger UI)
