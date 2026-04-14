# Kanban, Graph, and Timeline View Model — Wave 5

> **Wave:** 5 — Trace + Dashboard + Visualization Architecture
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–4
> **Aligned with:** Execution State Machine, Entity Schema v2, Parallelization Policy

---

## 1. Overview

This document defines the three primary dashboard views — Kanban (state machine visualization), Node Graph (invocation/dependency graph), and Timeline Playback (event sequence with branch visualization) — along with their data models, interaction patterns, and real-time update strategies.

---

## 2. Kanban View — State Machine Visualization

### 2.1 Column Definition

Kanban columns map directly to the **state taxonomy** defined in the Execution State Machine document:

| Column | State Category | Entities Shown | Sort Order |
|--------|---------------|----------------|------------|
| **Queued** | Pre-execution | All entities with state=`queued` | Priority DESC, created_at ASC |
| **Ready** | Pre-execution | All entities with state=`ready` | Priority DESC, ready_time ASC |
| **Running** | In-execution | All entities with state=`running` | Started_at ASC (oldest first) |
| **Waiting** | In-execution | All entities with state=`waiting` | Wait_start ASC |
| **Blocked** | In-execution | All entities with state=`blocked` | Block_start ASC |
| **Validating** | In-execution | All entities with state=`validating` | Validation_start ASC |
| **Completed** | Post-execution | All entities with state=`completed` | Completed_at DESC |
| **Failed** | Post-execution | All entities with state=`failed` | Failed_at DESC |
| **Escalated** | Post-execution | All entities with state=`escalated` | Escalated_at DESC |
| **Replayed** | Recovery | All entities with state=`replayed` | Replay_start ASC |
| **Compensated** | Post-execution | All entities with state=`compensated` | Compensated_at DESC |

**Column visibility rules:**
- Empty columns are hidden by default (toggle via column settings)
- `Queued` and `Ready` are collapsed by default (not actionable for Operator)
- `Running`, `Waiting`, `Blocked`, `Failed`, `Escalated` are always visible
- `Completed` shows count badge only; expand to see list

### 2.2 Card Content per Entity Type

Each entity type renders a card with different information density:

#### Task Card (primary Kanban entity)

```
┌─────────────────────────────────────────────┐
│ ◉ task_003                            [C3]  │
│ analyze-current-theming                     │
│ ─────────────────────────────────────────── │
│ Worker: worker_1  │  Lease: 3m 12s          │
│ Tools: 3/12 used  │  Cost: $0.45            │
│ Subtasks: 2/4 completed                     │
│ ─────────────────────────────────────────── │
│ [Timeline] [Artifacts] [Stop]               │
└─────────────────────────────────────────────┘
```

#### Subtask Card

```
┌───────────────────────────────────────┐
│ ● subtask_001                   [C3]  │
│ analyze-css-variables                 │
│ ───────────────────────────────────── │
│ Parent: task_003  │  Duration: 2m 11s │
│ Actions: 3/3 completed                │
│ ───────────────────────────────────── │
│ [Timeline] [Artifacts]                │
└───────────────────────────────────────┘
```

#### Tool Call Card (collapsed, inline in task card)

```
  ✓ tc_001  mcp:filesystem:read_file    45ms   $0.01
  ✓ tc_002  mcp:context7:query          230ms  $0.08
  ✗ tc_003  shell:pytest                12s    $0.15  (timeout)
```

#### Action Card (minimal)

```
  ● action_001  search-css-files  2.1s
```

### 2.3 Card Visual States

| Entity State | Card Treatment |
|--------------|---------------|
| `queued` | Dimmed (opacity 0.6), gray border |
| `ready` | Normal, blue left border, subtle glow |
| `running` | Normal, cyan left border, **pulsing glow** |
| `waiting` | Normal, amber left border, **clock icon** |
| `blocked` | Normal, orange left border, **stop icon** |
| `validating` | Normal, violet left border, **spinner icon** |
| `completed` | Dimmed (opacity 0.8), green left border |
| `failed` | Normal, red left border, **X icon** |
| `escalated` | Normal, rose left border, **pulsing alert icon** |
| `replayed` | Normal, purple left border, **replay icon** |
| `compensated` | Dimmed, dark red left border, **strikethrough** |

### 2.4 Kanban Interaction Model

| Interaction | Effect |
|-------------|--------|
| Click card | Opens entity detail panel (right sidebar) |
| Drag card | Disabled (state transitions are engine-managed, not user-draggable) |
| Hover card | Tooltip with full entity summary |
| Double-click | Opens full timeline view for entity |
| Right-click | Context menu: [Copy ID] [View Trace] [Export Artifact] [Stop] |
| Column header click | Toggle column collapse/expand |
| Column header count click | Filter to show only this state |

### 2.5 Kanban Aggregation Modes

| Mode | Display | Use Case |
|------|---------|----------|
| **Detail** (default) | Individual cards | Operator monitoring |
| **Count only** | Column header with count badge | High-level overview |
| **Grouped by workflow** | Cards grouped under workflow headers | Architect analysis |
| **Grouped by worker** | Cards grouped under worker headers | Load balancing review |

---

## 3. Node Graph — Invocation and Dependency Graph

### 3.1 Graph Structure

The node graph visualizes the **entity hierarchy** and **dependency edges**:

```
                    ┌──────────────┐
                    │  run_001     │
                    │  C3 • 45%    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  wave_001    │
                    │  3 workflows │
                    └──┬───┬───┬──┘
                       │   │   │
               ┌───────┘   │   └───────┐
               ▼           ▼           ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │ wf_001   │ │ wf_002   │ │ wf_003   │
         │ 3 tasks  │ │ 2 tasks  │ │ 4 tasks  │
         └────┬─────┘ └────┬─────┘ └────┬─────┘
              │             │             │
         ┌────▼─────┐  ┌────▼─────┐      │
         │ task_001 │  │ task_004 │      │
         │ ● done   │  │ ◉ run    │      │
         └────┬─────┘  └────┬─────┘      │
              │        ┌────┼─────┐      │
              │        ▼    ▼     ▼      │
              │    st_001 st_002 st_003  │
              │    ●     ◉      ○        │
              │             │             │
              │        ┌────┼─────┐      │
              │        ▼    ▼     ▼      │
              │    tc_001 tc_002 tc_003  │
              │    ✓    ◉     ○          │
```

### 3.2 Node Properties

| Property | Display | Source |
|----------|---------|--------|
| **Node ID** | Entity ID (shortened if long) | Entity schema |
| **State** | Color + icon | State machine |
| **Entity type** | Shape + color accent | Entity hierarchy |
| **Duration** | Below node | Span end_time - start_time |
| **Cost** | Tooltip | Sum of tool_call costs |
| **Progress** | Progress ring (for in-progress nodes) | Subtask completion ratio |

### 3.3 Node Shapes by Entity Type

| Entity Type | Shape | Color | Size |
|-------------|-------|-------|------|
| `run` | Rounded rectangle | Violet | 120x40 |
| `wave` | Hexagon | Indigo | 100x40 |
| `workflow` | Diamond | Blue | 90x40 |
| `task` | Circle | Cyan | 60x60 |
| `subtask` | Rounded rect | Teal | 80x30 |
| `action` | Small circle | Emerald | 40x40 |
| `tool_call` | Dot | Lime | 20x20 |

### 3.4 Edge Types

| Edge Type | Visual | Meaning |
|-----------|--------|---------|
| **Parent-child** | Solid line, downward | Hierarchical containment |
| **Dependency** | Dashed line, arrow | "A must complete before B starts" |
| **Parallel** | Dotted line, no arrow | "A and B can run in parallel" |
| **Merge point** | Converging arrows | Fan-in point (multiple inputs → single output) |
| **Error propagation** | Red dashed line | Failure cascading to dependents |
| **Compensation** | Red strikethrough line | Rollback propagation |

### 3.5 Graph Layout Algorithm

```
Top-down hierarchical layout (Dagre / Elk.js):

1. Layer 0: Run
2. Layer 1: Wave(s) — sequential
3. Layer 2: Workflow(s) — parallel within wave
4. Layer 3: Task(s) — parallel where no dependency
5. Layer 4: Subtask(s) — parallel where no dependency
6. Layer 5: Action(s) — sequential within subtask
7. Layer 6: ToolCall(s) — parallel within action

Constraints:
- Dependency edges enforce ordering
- Parallel siblings arrange horizontally
- Minimize edge crossings
- Preserve left-to-right reading order
```

### 3.6 Graph Interaction Model

| Interaction | Effect |
|-------------|--------|
| Scroll / pinch | Zoom in/out (0.1x – 5x) |
| Drag background | Pan the graph |
| Click node | Select node, show details in side panel |
| Double-click node | Expand/collapse children |
| Hover node | Tooltip with summary |
| Hover edge | Highlight edge, show relationship type |
| Right-click node | Context menu: [Copy ID] [View Trace] [Timeline] [Artifacts] |
| Click legend item | Filter graph to show only this entity type |
| Search | Highlight matching nodes, dim others |

### 3.7 Graph Detail Panel (on node select)

```
┌───────────────────────────────────────────────┐
│ task_003 — analyze-current-theming            │
│ ◉ Running  │  C3  │  Worker: worker_1         │
├───────────────────────────────────────────────┤
│ Started: 10:00:03  │  Elapsed: 3m 12s         │
│ Progress: ████░░░░ 50% (2/4 subtasks)          │
│ Cost: $0.45  │  Tools: 3/12 used               │
├───────────────────────────────────────────────┤
│ Subtasks:                                     │
│  ● subtask_001  analyze-css-variables   2m 11s │
│  ● subtask_002  analyze-component-tree 1m 45s │
│  ◉ subtask_003  generate-migration-plan       │
│  ○ subtask_004  write-tests                    │
├───────────────────────────────────────────────┤
│ [Timeline] [Waterfall] [Artifacts] [Trace]     │
└───────────────────────────────────────────────┘
```

---

## 4. Timeline Playback — Event Sequence Visualization

### 4.1 Timeline Mechanics

The timeline displays events chronologically with playback controls:

```
┌─────────────────────────────────────────────────────────────────────┐
│ ◄◄  ◄  [▶]  ►  ►►   1x  [2x] [4x] [0.5x]    10:00:00 ──▶ 10:05:00 │
│ ─────────────────────────────────────────────────────────────────── │
│ │  ◀─────────── scrubber (draggable) ─────────────────▶│            │
│ │                                                      │            │
│ 10:00:00  task_001  ready → running                     │            │
│ 10:00:01  tc_001    mcp:filesystem:read_file  [45ms]    │            │
│ 10:00:01  tc_002    mcp:context7:query  [230ms]         │            │
│ 10:00:02  task_001  running → validating                │            │
│ 10:00:02  verifier  check passed                        │            │
│ 10:00:02  task_001  validating → completed              │            │
│ 10:00:03  task_003  ready → running                     │            │
│ 10:00:03  tc_003    mcp:filesystem:read_file  [45ms]    │            │
│ 10:00:04  tc_004    mcp:filesystem:edit  [1200ms]       │            │
│ 10:00:05  ! tc_004  ERROR: timeout after 1200ms         │            │
│ 10:00:05  task_003  running → failed                    │            │
│ 10:00:05  task_003  retry initiated (1/3)               │            │
│ ...                                                       │            │
│                                                             │            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Playback Controls

| Control | Function | Shortcut |
|---------|----------|----------|
| `⏮` (jump to start) | Move scrubber to first event | `Home` |
| `⏪` (step back) | Jump to previous event | `Left` / `P` |
| `▶` (play/pause) | Toggle auto-advance through events | `Space` |
| `⏩` (step forward) | Jump to next event | `Right` / `N` |
| `⏭` (jump to end) | Move scrubber to last event | `End` |
| Speed selector | 0.25x, 0.5x, 1x, 2x, 4x, 8x | `1`-`6` keys |
| Time range | Last 30s, 1m, 5m, all | Dropdown |
| Scrubber | Drag to any point in time | Mouse drag |

### 4.3 Event Rendering in Timeline

Each event renders as a row with:

```
┌──────┬──────┬──────────┬───────────────────────────────────────┐
│ Time │ Icon │ Entity   │ Summary                               │
├──────┼──────┼──────────┼───────────────────────────────────────┤
│00:03 │  ◉   │task_003  │ ready → running (acquire, worker_1)   │
│      │      │          │  wf_001 • C3 • $0.00 so far           │
├──────┼──────┼──────────┼───────────────────────────────────────┤
│00:04 │  ⚙   │tc_001    │ mcp:filesystem:read_file [45ms] ✓     │
│      │      │          │  → 4521 bytes read                    │
├──────┼──────┼──────────┼───────────────────────────────────────┤
│00:05 │  ✗   │tc_004    │ mcp:filesystem:edit TIMEOUT [1200ms]  │
│      │  !   │          │  Error: operation exceeded timeout    │
│      │      │          │  Retry initiated (1/3)                │
└──────┴──────┴──────────┴───────────────────────────────────────┘
```

**Color coding:** Left border uses entity type accent color. Background uses severity tint. Icon uses state color.

### 4.4 Branch Visualization — Converge and Diverge

When tasks fan-out to parallel subtasks and fan-in at merge points:

```
Time ─────────────────────────────────────────────────────▶

task_003 running
  │
  ├─ fan-out ──┐
  │            │
  │     ┌──────┴──────┐
  │     ▼             ▼
  │  subtask_003   subtask_004
  │  ◉ generating   ○ waiting
  │  migration plan
  │     │
  │     ├─ tc_005 ✓  tc_006 ✓
  │     │
  │     ▼
  │  subtask_003 completed
  │            │
  ├─ fan-in ◄──┘
  │  (waiting for subtask_004)
  │
  ▼
task_003 continues...
```

**Visual encoding:**
- **Fan-out (diverge):** Arrow splits into multiple lines, each going to a parallel branch
- **Fan-in (converge):** Multiple lines merge into a single arrow at a merge point symbol (`⬟`)
- **Blocked branch:** Red X on the branch line
- **Completed branch:** Green check on the branch line
- **In-progress branch:** Pulsing cyan line

### 4.5 Timeline Grouping Modes

| Mode | Grouping | Use Case |
|------|----------|----------|
| **Flat** (default) | All events in single chronological list | Full trace review |
| **By entity** | Events grouped under entity headers | Entity lifecycle tracking |
| **By component** | Events grouped by source component | Component behavior analysis |
| **By event type** | Events grouped by event_type | Pattern recognition |
| **By worker** | Events grouped by worker_id | Agent performance review |

### 4.6 Timeline Correlation Highlighting

When an event is selected:
1. All events with the same `correlation_id` prefix are highlighted
2. Events with different correlation IDs dim to 40% opacity
3. A correlation breadcrumb shows the full entity path

```
Selected: tc_004 (tool_call)
Correlation: run_001 > wave_001 > wf_001 > task_003 > subtask_003 > action_002 > tc_004
Highlighted: 47 events  |  Dimmed: 123 events
```

---

## 5. Real-Time Update Strategy

### 5.1 Update Channels

| Channel | Protocol | Data | Latency |
|---------|----------|------|---------|
| **State updates** | SSE (Server-Sent Events) | Entity state changes, new events | < 100ms |
| **Metrics** | HTTP GET poll | Aggregated metrics | 30s interval |
| **Initial load** | HTTP GET (full snapshot) | All current state | On page load |

### 5.2 SSE Event Schema

```typescript
interface DashboardEvent {
  type: 'entity_state_change' | 'new_event' | 'new_span' | 'new_artifact'
      | 'metrics_update' | 'alert' | 'heartbeat';
  timestamp: string;  // ISO-8601
  data: EntityStateChange | NewEvent | NewSpan | NewArtifact | Metrics | Alert;
}

interface EntityStateChange {
  entity_id: string;
  entity_type: string;
  run_id: string;
  from_state: string;
  to_state: string;
  transition: string;
  timestamp: string;
}

interface NewEvent {
  event: Event;  // Full event object
}

interface Alert {
  level: 'warn' | 'error' | 'critical';
  message: string;
  entity_id?: string;
  run_id?: string;
}
```

### 5.3 UI Update Strategy — Incremental Diff

The dashboard does NOT re-render the entire view on each update. Instead:

```
Incoming SSE event
  │
  ▼
Parse and classify:
  ├── entity_state_change → Update Kanban card position (move to new column)
  ├── new_event → Append to timeline (if in current view)
  ├── new_span → Append to waterfall (if entity is visible)
  ├── new_artifact → Add badge to entity card
  ├── metrics_update → Update metrics panel
  ├── alert → Show in P0 alert zone
  └── heartbeat → Update lease timer (no visible change unless expiring)
```

### 5.4 Reconciliation Rules

| Scenario | Strategy |
|----------|----------|
| Out-of-order event (late arrival) | Insert at correct timestamp position; re-render affected region |
| Duplicate event (same event_id) | Discard (idempotent) |
| State inconsistency (UI disagrees with source) | Trust source (state.json); reconcile on next heartbeat |
| SSE connection lost | Switch to poll mode (5s interval); show "reconnecting" banner |
| SSE reconnected | Request full state snapshot; diff and patch UI |

### 5.5 Connection Lifecycle

```
Page load ──▶ HTTP GET /api/snapshot  (full current state)
                │
                ▼
         Render initial view
                │
                ▼
         SSE connect /api/stream
                │
                ├── Success: Start receiving events
                │
                └── Failure: Retry with backoff (1s, 2s, 4s, 8s, max 30s)
                                │
                                ├── Reconnect success: Request snapshot, diff, patch
                                │
                                └── Max retries: Switch to poll mode (5s HTTP GET)
```

---

## 6. View State Synchronization

### 6.1 Shared State Between Views

All three views (Kanban, Node Graph, Timeline) share the same underlying entity state. Selection in one view propagates to others:

```
User clicks task_003 in Kanban
  │
  ▼
Shared state update:
  selected_entity = "task_003"
  │
  ├── Kanban: Highlight card, open detail panel
  ├── Node Graph: Center on node, expand children
  └── Timeline: Filter to task_003 events, highlight correlation
```

### 6.2 View-Specific State

| View | Local State |
|------|-------------|
| **Kanban** | Column visibility, sort order, grouping mode, collapsed columns |
| **Node Graph** | Zoom level, pan offset, expanded nodes, visible entity types |
| **Timeline** | Playback position, speed, time range, grouping mode, active filters |

### 6.3 State Persistence

View-specific state is stored in `localStorage` (per run_id):

```json
{
  "dashboard:run_2026041310000001:kanban": {
    "collapsed_columns": ["queued", "ready", "completed"],
    "grouping": "workflow",
    "visible_states": ["running", "waiting", "blocked", "failed", "escalated"]
  },
  "dashboard:run_2026041310000001:node-graph": {
    "zoom": 1.5,
    "pan": { "x": -200, "y": 100 },
    "expanded_nodes": ["task_003", "subtask_001"],
    "visible_types": ["task", "subtask", "tool_call"]
  },
  "dashboard:run_2026041310000001:timeline": {
    "position": "2026-04-13T10:02:00Z",
    "speed": 2,
    "range": "5m",
    "grouping": "by_entity",
    "playing": false
  }
}
```

---

## 7. Implementation Notes

### 7.1 Recommended Libraries

| Component | Library | Rationale |
|-----------|---------|-----------|
| Kanban | Custom (CSS Grid) | Simple, no library needed |
| Node Graph | React Flow or Elk.js + D3 | Hierarchical layout, zoom/pan, selection |
| Timeline | Custom (virtual scroll) | Playback controls need custom implementation |
| Virtual scroll | react-window | Proven, performant |
| SSE client | EventSource API | Native browser support |
| State management | Zustand or Redux Toolkit | Shared state between views |

### 7.2 Data Flow Architecture

```
                     ┌──────────────────────┐
                     │  SSE Stream          │
                     │  /api/stream         │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │  Event Dispatcher     │
                     │  (classify + route)   │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
     ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
     │  Kanban Store │ │  Graph Store  │ │ Timeline Store│
     │  (entities by │ │  (nodes +     │ │  (events +    │
     │   state)       │ │   edges)      │ │   playback)   │
     └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
             │                 │                 │
             ▼                 ▼                 ▼
     ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
     │  Kanban View  │ │  Graph View   │ │ Timeline View │
     │  (CSS Grid)   │ │  (React Flow) │ │  (Virtual     │
     │               │ │               │ │   Scroll)     │
     └───────────────┘ └───────────────┘ └───────────────┘
```

### 7.3 Performance Targets

| View | Initial Render | Update Latency | Memory (10K events) |
|------|---------------|----------------|---------------------|
| Kanban | < 200ms | < 16ms (1 frame) | < 10 MB |
| Node Graph | < 500ms | < 50ms (layout recalculation) | < 20 MB |
| Timeline | < 300ms | < 16ms per event | < 15 MB |
