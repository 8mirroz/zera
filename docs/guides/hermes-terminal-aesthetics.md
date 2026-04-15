# Hermes/Zera Terminal Aesthetics Engine

> Three production-ready terminal design styles for reports, responses, and all CLI output.

---

## Quick Start

```bash
# Preview all 3 styles
python3 scripts/hermes_terminal_preview.py

# Preview single style
python3 scripts/hermes_terminal_preview.py void_prism
python3 scripts/hermes_terminal_preview.py neural_glass
python3 scripts/hermes_terminal_preview.py phantom_pulse

# Set default style
export HERMES_STYLE=neural_glass
```

---

## Three Styles

### 1. VOID PRISM — Cyber-Minimal with Geometric Depth

```
◤────────────────────────────────────────────────────────────────────────◥
│  ◈ System Report ◈                                                      │
◣────────────────────────────────────────────────────────────────────────◢

◇ System Health ◇ ◇ ◇
╼───────────────────────────────────────────────────────────────────────────╾
│  All subsystems operational.                                              │
╼───────────────────────────────────────────────────────────────────────────╾
    ◈ Agent OS: v4.2.0
    ◈ Active workflows: 12
```

**Design DNA:**
- Deep void black background
- Violet ↔ Cyan accent shift by context
- Sharp angular geometry (diamonds, chevrons, angled corners)
- Minimal but precise — every character earns its place
- Mood: precise, restrained, sharp

**Best for:** Developer tools, system diagnostics, operational dashboards

### 2. NEURAL GLASS — Luxury Monochrome with Layered Transparency

```
  ········································  

                    ⟡ System Report ⟡                        
  ········································  

─ · ─ · ─ · ─ · ─ · ─ · ─ · ─
  System Health

  ╭──────────────────────────────────────────────────────────────────────────╮
  │  All subsystems operational.                                              │
  ╰──────────────────────────────────────────────────────────────────────────╯
    ·  Agent OS: v4.2.0
    ·  Active workflows: 12
```

**Design DNA:**
- Warm dark gray, no bright colors
- Single gold/amber accent for purity
- Frosted glass effect via Unicode box-drawing + dim/bright layering
- Generous whitespace as design element
- Editorial rhythm with pull-quote callouts
- Mood: spacious, warm, editorial

**Best for:** Executive reports, knowledge summaries, editorial content

### 3. PHANTOM PULSE — Retro-Futurist CRT with Kinetic Energy

```
╔════════════════════════════════════════════════════════════════════════════╗
║                              System Report                                 ║
╚════════════════════════════════════════════════════════════════════════════╝
  ▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇▁▁▃▃▅▅▇▇

━ ━ ╋ ━ ━ ╋ ━ ━ ╋ ━ ━ ╋ ━ ━
  ● System Health

  ╔══════════════════════════════════════════════════════════════════════════╗
  ║  ════════════════════════════════════════════════════════════════════════  ║
  ║  All subsystems operational.                                              ║
  ╚══════════════════════════════════════════════════════════════════════════╝
```

**Design DNA:**
- Amber phosphor glow simulation
- Scanline mood, intentional noise texture
- Energy bar wave patterns
- Telemetry cockpit layout, mission-control feel
- Staged reveal, kinetic headers
- Mood: energetic, phosphor, mission-control

**Best for:** System monitoring, real-time dashboards, ops tools

---

## Python API

```python
from agent_os.hermes_terminal import Terminal, Style

# Create with specific style
t = Terminal(style=Style.VOID_PRISM)

# Quick constructors
t = Terminal.void_prism()
t = Terminal.neural_glass()
t = Terminal.phantom_pulse()

# Report formatting
report = t.report("System Status", [
    {
        "title": "Health Check",
        "content": "All systems nominal.",
        "items": ["Service A: OK", "Service B: OK"],
        "status": "ok",
    },
])
print(report)

# Response formatting
resp = t.response(
    "Task complete",
    body="All 234 tasks processed successfully.",
    metadata={"duration": "4.2s", "failures": 0},
)
print(resp)

# Runtime style switching
t.switch(Style.NEURAL_GLASS)

# Convenience functions
from agent_os.hermes_terminal import report, response, get_terminal
print(report("Title", sections))
```

---

## Configuration

Edit `configs/tooling/hermes_terminal.yaml`:

```yaml
terminal:
  style: void_prism   # void_prism | neural_glass | phantom_pulse
  width: null          # null = auto-detect
  truecolor: null      # null = auto-detect
```

Or via environment variable:

```bash
export HERMES_STYLE=neural_glass
```

---

## Terminal Capability Detection

The engine automatically detects:
- **Truecolor support** — via `COLORTERM` and `TERM` env vars
- **Terminal width** — via `os.get_terminal_size()`
- **Unicode width issues** — heuristic for known problematic terminals

Fallbacks are built-in:
- No truecolor → 16-color ANSI palette
- No Unicode → ASCII-only glyphs (planned)
- Narrow terminal → single-column layout degradation (planned)

---

## File Locations

| File | Purpose |
|------|---------|
| `repos/packages/agent-os/src/agent_os/hermes_terminal.py` | Core engine (1100+ lines) |
| `configs/tooling/hermes_terminal.yaml` | Configuration |
| `scripts/hermes_terminal_preview.py` | Demo/preview script |

---

## Architecture

```
Terminal (unified facade)
  │
  ├── VoidPrism      (cyber-minimal, geometric)
  ├── NeuralGlass    (luxury monochrome, editorial)
  └── PhantomPulse   (CRT retro-futurist, telemetry)
        │
        ├── header() / section() / panel() / card()
        ├── status_row() / progress() / kv_grid()
        ├── bullet_list() / divider()
        ├── report()    # full report with sections
        └── response()  # summary + body + metadata
```

Each style implements the same interface with different visual output.

---

*Created: 2026-04-15 | Status: Active | Part of Antigravity Core Platform*
