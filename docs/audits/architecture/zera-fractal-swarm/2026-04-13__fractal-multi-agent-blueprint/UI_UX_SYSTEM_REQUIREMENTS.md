# UI/UX System Requirements — Wave 5

> **Wave:** 5 — Trace + Dashboard + Visualization Architecture
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–4
> **Aligned with:** Project Design DNA (AGENTS.md), Premium UI Standards, a11y WCAG 2.1 AA

---

## 1. Design Principles

### 1.1 Core Principles

| Principle | Requirement | Anti-Pattern |
|-----------|-------------|--------------|
| **Premium by default** | No generic components, no template defaults, no placeholder visuals | Bootstrap-style cards, Material defaults without customization |
| **Dark mode primary** | All interfaces ship dark-first; light mode is optional secondary | Light mode as default |
| **Signal over noise** | Surface actionable information; suppress operational detail | Data dumps, every-event lists without aggregation |
| **Cognitive motion** | Animation communicates state, not decoration | Gratuitous motion, loading spinners without purpose |
| **Progressive disclosure** | Show summary first; expand to detail on demand | All-at-once information display |
| **Consistent DNA** | Glassmorphism, layered gradients, micro-interactions across all views | Inconsistent visual treatment between views |

### 1.2 Project DNA Alignment

From `AGENTS.md` Design DNA:

```yaml
design_principles:
  premium_first:
    - No generic UI components without customization
    - No default color schemes
    - No placeholder visuals

  modern_aesthetics:
    - Dark mode by default
    - Glassmorphism, depth, layered gradients
    - Smooth micro-interactions (hover, focus, transitions)

  typography:
    preferred: [Inter, Outfit, Roboto]
    hierarchy: Clear, deliberate, consistent
    legibility: Non-negotiable

  motion:
    - Subtle, meaningful animations
    - Purposeful state transitions
    - No gratuitous motion
```

---

## 2. Visual Design System

### 2.1 Color Tokens

#### Base Palette (Dark Mode)

```css
/* Background layers */
--bg-primary: #0D0F14;       /* App background */
--bg-secondary: #151820;     /* Panel background */
--bg-tertiary: #1C2030;      /* Card background */
--bg-elevated: #242838;      /* Tooltip, modal background */

/* Surface layers (glassmorphism) */
--surface-glass: rgba(28, 32, 48, 0.85);  /* Frosted glass panels */
--surface-blur: 12px;                     /* Backdrop blur amount */
--surface-border: rgba(255, 255, 255, 0.06);

/* Text */
--text-primary: #E8EAED;     /* Primary content */
--text-secondary: #9AA0AB;   /* Secondary content, labels */
--text-tertiary: #5F6672;    /* Disabled, placeholders */
--text-inverse: #0D0F14;     /* Text on light backgrounds */

/* Semantic colors */
--color-success: #10B981;    /* Completed, passed */
--color-success-bg: rgba(16, 185, 129, 0.12);
--color-warning: #F59E0B;    /* Waiting, degraded */
--color-warning-bg: rgba(245, 158, 11, 0.12);
--color-error: #EF4444;      /* Failed, error */
--color-error-bg: rgba(239, 68, 68, 0.15);
--color-info: #3B82F6;       /* Info, running */
--color-info-bg: rgba(59, 130, 246, 0.12);

/* Accent colors (entity types) */
--accent-run: #8B5CF6;       /* Violet */
--accent-wave: #6366F1;      /* Indigo */
--accent-workflow: #3B82F6;  /* Blue */
--accent-task: #06B6D4;      /* Cyan */
--accent-subtask: #14B8A6;   /* Teal */
--accent-action: #10B981;    /* Emerald */
--accent-toolcall: #84CC16;  /* Lime */
```

#### High Contrast Mode

```css
/* Replace low-contrast colors with WCAG AAA compliant alternatives */
--text-secondary: #B0B5C0;   /* Increased from #9AA0AB */
--text-tertiary: #7A8190;    /* Increased from #5F6672 */
--surface-border: rgba(255, 255, 255, 0.15);  /* Increased from 0.06 */
--bg-tertiary: #222638;      /* Increased contrast */
```

### 2.2 Typography

```css
/* Font families */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* Type scale */
--text-xs: 0.75rem;    /* 12px — badges, labels */
--text-sm: 0.875rem;   /* 14px — body text, card content */
--text-base: 1rem;     /* 16px — default body */
--text-lg: 1.125rem;   /* 18px — card titles */
--text-xl: 1.25rem;    /* 20px — section headers */
--text-2xl: 1.5rem;    /* 24px — page headers */

/* Line heights */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;

/* Font weights */
--font-regular: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 2.3 Spacing System

```css
/* 4px base grid */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

### 2.4 Border Radius

```css
--radius-sm: 4px;    /* Badges, small elements */
--radius-md: 8px;    /* Cards, buttons */
--radius-lg: 12px;   /* Panels, modals */
--radius-xl: 16px;   /* Large containers */
--radius-full: 9999px; /* Pills, avatars */
```

### 2.5 Shadows and Depth

```css
/* Layered depth system */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.6);
--shadow-glow: 0 0 20px var(--accent-task);  /* Entity-specific glow */
```

### 2.6 Glassmorphism Treatment

All panel surfaces use glassmorphism:

```css
.glass-panel {
  background: var(--surface-glass);
  backdrop-filter: blur(var(--surface-blur));
  -webkit-backdrop-filter: blur(var(--surface-blur));
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-lg);
}
```

---

## 3. Motion Specifications

### 3.1 Design Principle: Cognitive Signals Only

Motion is not decoration. Every animation communicates a **cognitive signal**:

| Signal | Animation | Duration | Easing | Trigger |
|--------|-----------|----------|--------|---------|
| **Progress** | Smooth fill/advance of progress indicator | 300ms | `ease-out` | Entity progressing toward completion |
| **Wait** | Gentle pulse on waiting/blocked entities | 2s cycle | `ease-in-out` | Entity in `waiting` or `blocked` state |
| **Blocked** | Sharp shake (1 iteration) on block transition | 200ms | `ease-out` | Entity transitions to `blocked` |
| **Parallel** | Simultaneous glow on sibling running entities | 400ms | `ease-out` | Fan-out event received |
| **Retry** | Rewind + replay animation on retried entity | 500ms | `ease-in-out` | Entity transitions to `replayed` |
| **Escalation** | Pulsing red border (continuous) | 1s cycle | `ease-in-out` | Entity transitions to `escalated` |
| **Convergence** | Branch lines merge into single point | 300ms | `ease-out` | Fan-in event received |
| **Error** | Sharp flash + red overlay (1 iteration) | 150ms | `ease-out` | Error event received |
| **State change** | Card slides to new column | 250ms | `ease-out` | Entity state transition |
| **Hover** | Subtle lift + increased shadow | 150ms | `ease-out` | Cursor enters element |
| **Focus** | Blue ring + slight scale | 100ms | `ease-out` | Element receives focus |

### 3.2 Motion Token System

```css
/* Duration tokens */
--motion-instant: 0ms;
--motion-fast: 100ms;
--motion-normal: 200ms;
--motion-slow: 300ms;
--motion-slower: 500ms;
--motion-deliberate: 1000ms;

/* Easing tokens */
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);     /* Exit animations */
--ease-in: cubic-bezier(0.7, 0, 0.84, 0);       /* Enter animations */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);  /* Bidirectional */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);  /* Micro-interactions */

/* Signal-specific tokens */
--motion-progress: var(--motion-slow) var(--ease-out);
--motion-wait: var(--motion-deliberate) var(--ease-in-out);
--motion-blocked: var(--motion-normal) var(--ease-out);
--motion-parallel: var(--motion-slower) var(--ease-out);
--motion-retry: var(--motion-slower) var(--ease-in-out);
--motion-escalation: var(--motion-deliberate) var(--ease-in-out);
--motion-convergence: var(--motion-slow) var(--ease-out);
--motion-error: var(--motion-fast) var(--ease-out);
--motion-state-change: var(--motion-slow) var(--ease-out);
--motion-hover: var(--motion-fast) var(--ease-out);
--motion-focus: var(--motion-fast) var(--ease-out);
```

### 3.3 Keyframe Animations

```css
/* Pulsing glow (running entities) */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 4px var(--accent-task), 0 0 8px rgba(6, 182, 212, 0.2); }
  50% { box-shadow: 0 0 8px var(--accent-task), 0 0 16px rgba(6, 182, 212, 0.3); }
}

/* Clock pulse (waiting entities) */
@keyframes clock-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Escalation alert pulse */
@keyframes escalation-pulse {
  0%, 100% { border-color: var(--color-error); box-shadow: 0 0 4px rgba(239, 68, 68, 0.3); }
  50% { border-color: #DC2626; box-shadow: 0 0 8px rgba(239, 68, 68, 0.5); }
}

/* Error flash */
@keyframes error-flash {
  0% { background: var(--color-error-bg); }
  100% { background: transparent; }
}

/* Blocked shake */
@keyframes blocked-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}
```

---

## 4. Accessibility Requirements

### 4.1 WCAG 2.1 AA Compliance

| Requirement | Target | Verification |
|-------------|--------|--------------|
| Color contrast (normal text) | 4.5:1 minimum | Automated check in CI |
| Color contrast (large text) | 3:1 minimum | Automated check in CI |
| Focus indicators | Visible, 3:1 contrast against adjacent colors | Manual review |
| Keyboard navigation | All interactive elements reachable via Tab | Manual review |
| Screen reader labels | All icons, charts, graphs have aria-labels | Manual review with VoiceOver/NVDA |
| Motion reduction | Respects `prefers-reduced-motion` | Automated + manual |
| Touch target size | Minimum 44x44px | Automated check |

### 4.2 Accessibility Toggle Panel

All users can access the accessibility panel (gear icon in header):

```
┌────────────────────────────────────────┐
│  Accessibility Settings                │
├────────────────────────────────────────┤
│  ☐ Reduce motion                       │
│     Disables all non-essential         │
│     animations                         │
│                                        │
│  ☐ High contrast                       │
│     Increases color contrast to        │
│     WCAG AAA level                     │
│                                        │
│  ☐ Large text                          │
│     Increases base font size to 18px   │
│                                        │
│  ☐ Screen reader optimized             │
│     Adds ARIA descriptions,            │
│     live regions, chart descriptions   │
│                                        │
│  ☐ Colorblind safe mode                │
│     Adds patterns/shapes to            │
│     color-coded elements               │
│                                        │
│  [Reset to defaults]  [Save]          │
└────────────────────────────────────────┘
```

### 4.3 Reduced Motion Behavior

When `prefers-reduced-motion` is enabled or user toggles "Reduce motion":

| Animation | Reduced Behavior |
|-----------|-----------------|
| Pulse glow (running) | Static border, no animation |
| Clock pulse (waiting) | Static icon, no animation |
| Escalation pulse | Solid red border, no animation |
| State change slide | Instant position change (no transition) |
| Hover lift | Color change only (no transform) |
| Error flash | Persistent red background (no animation) |
| Blocked shake | No animation |
| Retry rewind/replay | Instant state change |
| Convergence merge | Instant line appearance |
| Timeline playback | Step-by-step (no smooth scrolling) |

### 4.4 Screen Reader Support

| Component | ARIA Treatment |
|-----------|---------------|
| **Kanban columns** | `role="list"`, each card `role="listitem"`, column header `aria-label="Running tasks, 3 items"` |
| **Node graph** | `role="img"`, `aria-label="Dependency graph showing {N} entities"`, with hidden text description of graph structure |
| **Timeline** | `role="log"`, `aria-live="polite"`, each event announced as it appears during playback |
| **Metrics charts** | `role="img"`, `aria-label="{Chart title}: {Data summary}"`, with `<table>` fallback for data |
| **Waterfall** | `role="group"`, `aria-label="Tool call waterfall, {N} calls"`, with hidden list of calls and durations |
| **Alert zone** | `role="alert"`, `aria-live="assertive"` for critical alerts |
| **Progress indicators** | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| **Breadcrumbs** | `role="navigation"`, `aria-label="Breadcrumb"` |

### 4.5 Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Navigate between interactive elements |
| `Enter` / `Space` | Activate selected element |
| `Escape` | Close panel, deselect entity |
| `Arrow Left/Right` | Navigate timeline events, graph nodes |
| `Arrow Up/Down` | Navigate Kanban cards, list items |
| `Space` (timeline) | Toggle playback |
| `1-6` (timeline) | Set playback speed |
| `Home` / `End` | Jump to start/end of timeline |
| `/` | Focus search bar |
| `?` | Show keyboard shortcuts panel |

---

## 5. Responsive Design

### 5.1 Breakpoints

```css
--breakpoint-sm: 640px;    /* Mobile portrait */
--breakpoint-md: 768px;    /* Mobile landscape, tablet portrait */
--breakpoint-lg: 1024px;   /* Tablet landscape, small desktop */
--breakpoint-xl: 1280px;   /* Standard desktop */
--breakpoint-2xl: 1536px;  /* Large desktop */
```

### 5.2 Layout Behavior by Breakpoint

| Breakpoint | Layout | Visible Panels |
|------------|--------|---------------|
| **sm (<640px)** | Single column, stacked | One view at a time (tab switcher) |
| **md (768px)** | Two columns | Main view + collapsed sidebar |
| **lg (1024px)** | Three columns | Main view + metrics sidebar + detail panel |
| **xl (1280px)** | Full layout | All panels visible |
| **2xl (1536px)** | Expanded layout | Wider graph view, larger timeline |

### 5.3 Mobile-Specific Adaptations

| Feature | Desktop | Mobile |
|---------|---------|--------|
| Kanban columns | All columns visible horizontally | Horizontal scroll, snap-to-column |
| Node graph | Full interactive graph | Touch to zoom/pinch, tap to select |
| Timeline | Full playback controls | Swipe to scrub, tap to expand event |
| Metrics panel | Right sidebar | Bottom sheet (swipe up) |
| Detail panel | Right sidebar | Full-screen overlay (swipe down to dismiss) |
| Alert zone | Top banner | Full-screen overlay (dismiss to continue) |

---

## 6. Performance Budgets

### 6.1 Core Web Vitals

| Metric | Target | Measurement |
|--------|--------|-------------|
| **LCP** (Largest Contentful Paint) | < 2.5s | Page load to first meaningful content |
| **FID** (First Input Delay) | < 100ms | Click/tap to browser response |
| **CLS** (Cumulative Layout Shift) | < 0.1 | Layout stability during load |
| **TTI** (Time to Interactive) | < 5s | Page load to fully interactive |

### 6.2 Runtime Performance

| Scenario | Target | Measurement |
|----------|--------|-------------|
| **SSE event processing** | < 16ms (1 frame) | Event receipt to DOM update |
| **Kanban card move** | < 16ms | State change to repositioned card |
| **Timeline render (10K events)** | < 500ms | Initial render with virtual scroll |
| **Graph layout (100 nodes)** | < 300ms | Dagre layout computation |
| **Search (10K events)** | < 100ms | Query to results displayed |
| **Filter change** | < 50ms | Filter apply to re-rendered view |

### 6.3 Memory Budget

| Component | Budget (10K events) | Budget (100K events) |
|-----------|-------------------|---------------------|
| Trace index | < 5 MB | < 50 MB |
| BM25 search index | < 3 MB | < 30 MB |
| View models (Kanban + Graph + Timeline) | < 15 MB | < 100 MB |
| DOM nodes | < 2000 (visible) | < 2000 (visible, virtual scroll) |
| Total client memory | < 30 MB | < 200 MB |

### 6.4 Network Budget

| Request | Budget | Rationale |
|---------|--------|-----------|
| Initial page load | < 500 KB (gzipped) | SPA bundle + initial snapshot |
| Snapshot API | < 1 MB per run | Full state for active run |
| SSE connection | < 1 KB per event | Compressed event payload |
| Metrics poll | < 5 KB per response | Aggregated metrics only |
| Search query | < 100 KB response | Top 50 results only |

---

## 7. Component Inventory

### 7.1 Primitive Components

| Component | Variants | Usage |
|-----------|----------|-------|
| **Badge** | Default, success, warning, error, info | State labels, tier tags, counts |
| **Card** | Default, elevated, glass | Entity containers, mission cards |
| **Button** | Primary, secondary, ghost, icon | Actions, controls |
| **Input** | Text, search, select, date-range | Filter controls |
| **Tooltip** | Default, rich (with actions) | Hover details |
| **Modal** | Default, fullscreen | Detail panels, settings |
| **Toast** | Success, warning, error, info | Transient notifications |
| **Progress bar** | Linear, circular | Entity progress, mission progress |
| **Avatar** | Entity icon (shape + color) | Node graph, card headers |
| **Separator** | Horizontal, vertical | Section dividers |
| **Tabs** | Default, icon-only | View switching |
| **Accordion** | Default, nested | Expandable sections |

### 7.2 Dashboard-Specific Components

| Component | Description | Props |
|-----------|-------------|-------|
| **KanbanColumn** | Column with header, count, card list | `state`, `entities[]`, `collapsed` |
| **EntityCard** | Card representing an entity | `entity`, `variant`, `actions[]` |
| **NodeGraph** | Interactive dependency graph | `nodes[]`, `edges[]`, `layout` |
| **GraphNode** | Individual graph node | `entity`, `state`, `shape` |
| **Timeline** | Chronological event viewer | `events[]`, `playback`, `grouping` |
| **TimelineEvent** | Single event row | `event`, `highlighted` |
| **Waterfall** | Tool call latency visualization | `tool_calls[]`, `scale` |
| **WaterfallBar** | Single tool call bar | `tool_call`, `color` |
| **MetricsPanel** | Metrics dashboard panel | `metrics[]`, `refresh_rate` |
| **MetricChart** | Single metric visualization | `metric`, `chart_type` |
| **ArtifactExplorer** | File/artifact browser with lineage | `artifacts[]`, `lineage_graph` |
| **AlertZone** | P0 alert banner | `alerts[]`, `onDismiss` |
| **Breadcrumb** | Navigation breadcrumbs | `items[]` |
| **FilterBar** | Multi-dimension filter controls | `filters[]`, `presets[]`, `onApply` |
| **SearchBar** | Full-text search with suggestions | `onSearch`, `placeholder` |
| **PlaybackControls** | Timeline playback controls | `playing`, `speed`, `position`, `onControl` |
| **CorrelationBreadcrumb** | Correlation ID breadcrumb | `correlation_id` |
| **EntitySelector** | Dropdown to select entity scope | `runs[]`, `waves[]`, `workflows[]` |
| **GlassPanel** | Frosted glass container | `children`, `elevation` |
| **StatusIndicator** | Animated state indicator | `state`, `pulse` |

### 7.3 Component Implementation Notes

- All components must be **theme-aware** (dark mode default, high contrast variant)
- All components must support **ARIA attributes**
- All components must be **keyboard accessible**
- All interactive components must have **visible focus indicators**
- All components must respect **`prefers-reduced-motion`**
- Component props must be **TypeScript-typed**
- Components must be **unit-tested** (render, interaction, a11y)

---

## 8. Design QA Checklist

### 8.1 Visual QA

- [ ] All colors use design tokens (no hardcoded hex values)
- [ ] All spacing uses spacing scale (no arbitrary px values)
- [ ] All typography uses type scale (no arbitrary font sizes)
- [ ] Glassmorphism applied to all panel surfaces
- [ ] Dark mode renders correctly at all breakpoints
- [ ] Hover states visible on all interactive elements
- [ ] Focus states visible and distinct from hover
- [ ] No generic/default component appearances

### 8.2 Accessibility QA

- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 text, 3:1 large)
- [ ] All interactive elements reachable via keyboard
- [ ] All icons have aria-labels
- [ ] Charts and graphs have text descriptions
- [ ] `prefers-reduced-motion` respected
- [ ] Screen reader announces state changes (live regions)
- [ ] Touch targets minimum 44x44px
- [ ] High contrast mode functional

### 8.3 Performance QA

- [ ] Initial page load < 2.5s LCP
- [ ] SSE event processing < 16ms
- [ ] Virtual scroll renders 10K events without lag
- [ ] Graph layout computes in < 300ms for 100 nodes
- [ ] Memory usage < 30 MB for 10K events
- [ ] No memory leaks on extended sessions (30+ min)

### 8.4 Motion QA

- [ ] All animations communicate cognitive signals
- [ ] No gratuitous or decorative animations
- [ ] Motion durations use tokens
- [ ] Easing curves use tokens
- [ ] Reduced motion mode disables non-essential animations
- [ ] State transitions smooth and intentional
