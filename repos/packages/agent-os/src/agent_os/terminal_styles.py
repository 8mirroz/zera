"""
Hermes / Zera Terminal Aesthetic Engine
========================================
Three production-grade terminal styles for reports, responses, and system output.

Styles:
  - void_prism:     Cyber/minimal — sharp geometry, shifting accent colors
  - neural_glass:   Luxury monochrome — frosted glass, editorial rhythm
  - phantom_pulse:  Retro-futurist CRT — amber phosphor, kinetic energy

Usage:
    from agent_os.terminal_styles import ThemeEngine

    engine = ThemeEngine(style="void_prism")
    print(engine.report_panel(title="System Status", data={"cpu": "12%", "mem": "4.2GB"}))
    print(engine.response_block("Task completed successfully", status="ok"))
"""

from __future__ import annotations

import os
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ─── Terminal Capability Detection ───────────────────────────────────────────

@dataclass
class TerminalCaps:
    """Detected terminal capabilities for adaptive rendering."""
    truecolor: bool = False
    unicode: bool = True
    width: int = 80
    height: int = 24
    hyperlinks: bool = False
    graphics_protocol: bool = False  # kitty / sixel

    @classmethod
    def detect(cls) -> "TerminalCaps":
        caps = cls()
        caps.truecolor = os.environ.get("COLORTERM", "") in ("truecolor", "24bit")
        caps.width = os.get_terminal_size().columns if sys.stdout.isatty() else 80
        caps.height = os.get_terminal_size().lines if sys.stdout.isatty() else 24
        caps.unicode = True
        term = os.environ.get("TERM", "")
        caps.hyperlinks = "xterm" in term or "alacritty" in term or "kitty" in term
        caps.graphics_protocol = "kitty" in term
        return caps


# ─── Color Palettes ──────────────────────────────────────────────────────────

# Truecolor RGB definitions — each style has its own palette
PALETTES = {
    "void_prism": {
        "bg":          (10, 10, 14),
        "surface":     (18, 18, 26),
        "surface_hi":  (26, 26, 38),
        "border":      (40, 40, 60),
        "border_hi":   (60, 60, 90),
        "text":        (220, 220, 235),
        "text_dim":    (130, 130, 155),
        "text_faint":  (80, 80, 100),
        "accent":      (139, 92, 246),    # violet
        "accent2":     (6, 182, 212),     # cyan
        "accent3":     (168, 85, 247),    # purple
        "success":     (34, 197, 94),     # green
        "warning":     (250, 204, 21),    # yellow
        "error":       (239, 68, 68),     # red
        "info":        (59, 130, 246),    # blue
    },
    "neural_glass": {
        "bg":          (15, 15, 18),
        "surface":     (22, 22, 26),
        "surface_hi":  (32, 32, 38),
        "border":      (50, 50, 58),
        "border_hi":   (70, 70, 80),
        "text":        (210, 205, 195),   # warm white
        "text_dim":    (140, 135, 125),
        "text_faint":  (85, 82, 76),
        "accent":      (217, 169, 52),    # amber gold
        "accent2":     (234, 196, 78),    # light gold
        "accent3":     (190, 145, 40),    # deep gold
        "success":     (143, 188, 89),    # muted green
        "warning":     (217, 169, 52),    # amber
        "error":       (200, 80, 70),     # muted red
        "info":        (130, 170, 200),   # steel blue
    },
    "phantom_pulse": {
        "bg":          (8, 6, 4),
        "surface":     (16, 13, 8),
        "surface_hi":  (28, 22, 14),
        "border":      (50, 40, 20),
        "border_hi":   (80, 65, 30),
        "text":        (230, 190, 120),   # amber phosphor
        "text_dim":    (160, 130, 75),
        "text_faint":  (90, 72, 40),
        "accent":      (255, 170, 50),    # bright amber
        "accent2":     (80, 220, 120),    # phosphor green
        "accent3":     (200, 80, 40),     # rust
        "success":     (80, 220, 120),    # phosphor green
        "warning":     (255, 170, 50),    # amber
        "error":       (220, 60, 40),     # rust red
        "info":        (120, 200, 230),   # cyan phosphor
    },
}


# ─── Fallback (No-Color) Glyph Sets ─────────────────────────────────────────

GLYPHS = {
    "void_prism": {
        "header_left":  "◈",
        "header_right": "◈",
        "separator":    "━━━",
        "divider":      "┈┈┈",
        "bullet":       "▸",
        "bullet_active": "◆",
        "corner_tl":    "╭",
        "corner_tr":    "╮",
        "corner_bl":    "╰",
        "corner_br":    "╯",
        "edge_l":       "│",
        "edge_r":       "│",
        "edge_t":       "─",
        "edge_b":       "─",
        "arrow":        "→",
        "check":        "✓",
        "cross":        "✗",
        "warning":      "⚠",
        "info":         "◇",
        "pulse":        "⟐",
        "chevron":      "»",
        "diamond":      "◊",
    },
    "neural_glass": {
        "header_left":  "⟡",
        "header_right": "⟡",
        "separator":    "───",
        "divider":      "···",
        "bullet":       "·",
        "bullet_active": "◦",
        "corner_tl":    "┌",
        "corner_tr":    "┐",
        "corner_bl":    "└",
        "corner_br":    "┘",
        "edge_l":       "│",
        "edge_r":       "│",
        "edge_t":       "─",
        "edge_b":       "─",
        "arrow":        "→",
        "check":        "✓",
        "cross":        "✗",
        "warning":      "⚠",
        "info":         "○",
        "pulse":        "◌",
        "chevron":      "›",
        "diamond":      "◇",
    },
    "phantom_pulse": {
        "header_left":  "⚡",
        "header_right": "⚡",
        "separator":    "═══",
        "divider":      "───",
        "bullet":       "›",
        "bullet_active": "»",
        "corner_tl":    "╔",
        "corner_tr":    "╗",
        "corner_bl":    "╚",
        "corner_br":    "╝",
        "edge_l":       "║",
        "edge_r":       "║",
        "edge_t":       "═",
        "edge_b":       "═",
        "arrow":        "⇒",
        "check":        "✓",
        "cross":        "✗",
        "warning":      "⚠",
        "info":         "◉",
        "pulse":        "⊕",
        "chevron":      "»",
        "diamond":      "◆",
    },
}


# ─── ANSI Escape Code Helpers ────────────────────────────────────────────────

def rgb(r: int, g: int, b: int) -> str:
    """Truecolor foreground."""
    return f"\033[38;2;{r};{g};{b}m"


def rgb_bg(r: int, g: int, b: int) -> str:
    """Truecolor background."""
    return f"\033[48;2;{r};{g};{b}m"


BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
RESET = "\033[0m"


def colorize(text: str, r: int, g: int, b: int, bold: bool = False, dim: bool = False) -> str:
    """Apply truecolor to text."""
    c = rgb(r, g, b)
    prefix = ""
    if bold:
        prefix += BOLD
    if dim:
        prefix += DIM
    return f"{prefix}{c}{text}{RESET}"


def bg_fill(line: str, r: int, g: int, b: int, width: int = 80) -> str:
    """Fill a line with background color, padded to width."""
    padded = line.ljust(width)
    return f"{rgb_bg(r, g, b)}{padded}{RESET}"


# ─── Wave / Pulse Generators ─────────────────────────────────────────────────

def wave_pattern(width: int, style: str, phase: float = 0.0) -> str:
    """Generate a static wave/pulse pattern for dividers."""
    import math
    chars = []
    if style == "void_prism":
        symbols = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]
    elif style == "phantom_pulse":
        symbols = ["░", "▒", "▓", "█", "▓", "▒", "░", "·", "·"]
    else:  # neural_glass
        symbols = ["·", "·", "·", "◦", "○", "◦", "·", "·", "·"]

    for i in range(width):
        idx = int((math.sin((i / width) * 4 * math.pi + phase) + 1) / 2 * (len(symbols) - 1))
        chars.append(symbols[idx])
    return "".join(chars)


def energy_bar(filled: float, width: int = 30, style: str = "void_prism") -> str:
    """Progress/energy bar with style-appropriate fill characters."""
    filled_count = max(0, min(width, int(filled * width)))
    empty_count = width - filled_count

    if style == "void_prism":
        fill_char = "█"
        empty_char = "░"
    elif style == "phantom_pulse":
        fill_char = "█"
        empty_char = "▒"
    else:
        fill_char = "━"
        empty_char = "─"

    return fill_char * filled_count + empty_char * empty_count


# ─── Theme Engine ────────────────────────────────────────────────────────────

@dataclass
class ThemeEngine:
    """Centralized terminal aesthetic engine for Hermes/Zera output."""

    style: str = "void_prism"
    width: int = 0
    caps: TerminalCaps = field(default_factory=TerminalCaps.detect)

    def __post_init__(self):
        if self.style not in PALETTES:
            raise ValueError(f"Unknown style: {self.style}. Choose from: {', '.join(PALETTES.keys())}")
        if self.width <= 0:
            self.width = self.caps.width
        self.palette = PALETTES[self.style]
        self.glyphs = GLYPHS[self.style]

    # ─── Color Helpers ───────────────────────────────────────────────────

    def _c(self, name: str) -> tuple[int, int, int]:
        return self.palette[name]

    def _dim_color(self, name: str, factor: float = 0.5) -> tuple[int, int, int]:
        r, g, b = self.palette[name]
        return (int(r * factor), int(g * factor), int(b * factor))

    # ─── Panel Borders ───────────────────────────────────────────────────

    def box_top(self, title: str = "") -> str:
        """Top border of a box, with optional centered title."""
        g = self.glyphs
        c = self._c
        w = self.width

        if title:
            title_str = f" {g['header_left']} {title} {g['header_right']} "
            inner_w = w - 2
            title_start = max(0, (inner_w - len(title_str)) // 2)
            line = g["corner_tl"] + g["edge_t"] * title_start + title_str
            remaining = w - len(line) - 1
            line += g["edge_t"] * remaining + g["corner_tr"]
        else:
            line = g["corner_tl"] + g["edge_t"] * (w - 2) + g["corner_tr"]

        return colorize(line, *c["border"])

    def box_side(self, text: str = "", pad: int = 1) -> str:
        """Side border line with optional left-aligned text."""
        g = self.glyphs
        c = self._c
        w = self.width
        inner_w = w - 2

        if text:
            padded_text = " " * pad + text + " " * (inner_w - len(text) - pad)
        else:
            padded_text = " " * inner_w

        return f"{colorize(g['edge_l'], *c['border'])}{colorize(padded_text, *c['text_dim'])}{colorize(g['edge_r'], *c['border'])}"

    def box_bottom(self) -> str:
        """Bottom border of a box."""
        g = self.glyphs
        c = self._c
        w = self.width
        return colorize(g["corner_bl"] + g["edge_b"] * (w - 2) + g["corner_br"], *c["border"])

    # ─── Separators ──────────────────────────────────────────────────────

    def separator(self, label: str = "") -> str:
        """Section separator with optional label."""
        g = self.glyphs
        c = self._c
        w = self.width

        if self.style == "void_prism":
            sep_char = "━"
        elif self.style == "phantom_pulse":
            sep_char = "═"
        else:
            sep_char = "─"

        if label:
            label_str = f" {g['diamond']} {label} "
            avail = w - len(label_str) - 2
            left = avail // 3
            right = avail - left
            line = sep_char * left + label_str + sep_char * right
        else:
            line = sep_char * w

        return colorize(line, *c["border"])

    def wave_divider(self, phase: float = 0.0) -> str:
        """Animated-style wave pattern divider."""
        c = self._c
        pattern = wave_pattern(self.width, self.style, phase)
        return colorize(pattern, *c["text_faint"])

    # ─── Report Panel ────────────────────────────────────────────────────

    def report_panel(
        self,
        title: str,
        data: dict[str, Any] | None = None,
        status: str = "info",
        footer: str = "",
    ) -> str:
        """
        Render a structured report panel.

        Example output (void_prism):

        ╭──────────────────────────────────────────────────────────────╮
        │  ◈ System Status ◈                                          │
        │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
        │  ▸ cpu:    12%    ████████████████████████████████████░░░░  │
        │  ▸ memory: 4.2GB  ████████████████████████░░░░░░░░░░░░░░░░  │
        │  ▸ disk:   67%    █████████████████████████████████░░░░░░░  │
        │                                                            │
        │  ◇ Updated 2026-04-15 14:32                                │
        ╰──────────────────────────────────────────────────────────────╯
        """
        lines: list[str] = []
        c = self._c

        # Header
        lines.append(self.box_top(title))

        # Accent line under title
        accent_line = colorize(self.glyphs["separator"] * min(40, self.width // 2), *c["accent"])
        lines.append(f"{colorize(' ', *c['surface'])}{accent_line}{colorize(' ' * (self.width - len(accent_line) - 1), *c['surface'])}")

        # Data rows
        if data:
            lines.append("")
            for key, value in data.items():
                label = f"  {self.glyphs['bullet']} {key}:"
                value_str = str(value)

                # Try to detect numeric value for energy bar
                bar = ""
                clean_val = value_str.replace("%", "").replace("GB", "").replace("MB", "")
                try:
                    num = float(clean_val)
                    if "%" in value_str:
                        ratio = num / 100.0
                    elif num < 1.0:
                        ratio = num
                    else:
                        ratio = min(num / 100.0, 1.0)
                    bar = "  " + energy_bar(ratio, min(20, self.width // 5), self.style)
                except (ValueError, TypeError):
                    pass

                row = f"{label.ljust(14)} {value_str}{bar}"
                lines.append(colorize(row, *c["text"]))

            lines.append("")

        # Footer
        if footer:
            lines.append(colorize(f"  {self.glyphs['info']} {footer}", *c["text_dim"]))

        lines.append(self.box_bottom())
        return "\n".join(lines)

    # ─── Response Block ──────────────────────────────────────────────────

    def response_block(
        self,
        text: str,
        status: str = "ok",
        label: str = "",
        timestamp: str = "",
    ) -> str:
        """
        Render a response / status block.

        Example output (neural_glass):

        ┌──────────────────────────────────────────────────────────────┐
        │ ⟡ RESPONSE                                                  │
        │                                                             │
        │   Task completed successfully.                              │
        │   3 files modified. 0 errors.                               │
        │                                                             │
        │   · 2026-04-15 14:32  ✓ ok                                 │
        └──────────────────────────────────────────────────────────────┘
        """
        lines: list[str] = []
        c = self._c
        g = self.glyphs

        # Status color
        status_colors = {
            "ok": "success",
            "success": "success",
            "error": "error",
            "fail": "error",
            "warning": "warning",
            "warn": "warning",
            "info": "info",
        }
        sc_name = status_colors.get(status, "info")
        sc = self._c(sc_name)

        # Header
        header_label = label.upper() if label else "RESPONSE"
        header_text = f"  {g['header_left']} {header_label} {g['header_right']}"
        lines.append(self.box_top())
        lines.append(colorize(header_text, *sc, bold=True))
        lines.append(colorize(f"  {g['separator'] * 20}", *c["border"]))
        lines.append("")

        # Wrap text to panel width
        inner_w = self.width - 6
        wrapped = textwrap.fill(text, width=inner_w)
        for line in wrapped.split("\n"):
            lines.append(colorize(f"  {line}", *c["text"]))

        lines.append("")

        # Footer with timestamp and status
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
        status_icon = g["check"] if status in ("ok", "success") else (g["cross"] if status in ("error", "fail") else g["warning"])
        footer_text = f"  {g['bullet']} {ts}  {status_icon} {status}"
        lines.append(colorize(footer_text, *c["text_dim"]))

        lines.append(self.box_bottom())
        return "\n".join(lines)

    # ─── Status Badge ────────────────────────────────────────────────────

    def badge(self, label: str, kind: str = "info") -> str:
        """Inline status badge."""
        c = self._c
        colors = {
            "success": "success",
            "ok": "success",
            "error": "error",
            "fail": "error",
            "warning": "warning",
            "warn": "warning",
            "info": "info",
            "active": "accent",
        }
        color_name = colors.get(kind, "info")
        col = self._c(color_name)

        if self.style == "void_prism":
            return f"[{colorize(label, *col, bold=True)}]"
        elif self.style == "phantom_pulse":
            return f"║{colorize(label, *col, bold=True)}║"
        else:
            return f" {colorize(f'· {label} ·', *col)} "

    # ─── Header Banner ───────────────────────────────────────────────────

    def header_banner(self, title: str, subtitle: str = "") -> str:
        """
        Full-width header banner.

        void_prism:
          ◈━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◈
          ◆  HERMES / ZERA
          ▸  Autonomous Development Platform
          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        phantom_pulse:
          ╔══════════════════════════════════════════════════════════════════╗
          ║  ⚡  HERMES / ZERA  ⚡
          ║  ⇒  Autonomous Development Platform
          ╚══════════════════════════════════════════════════════════════════╝
        """
        lines: list[str] = []
        c = self._c
        g = self.glyphs

        if self.style == "void_prism":
            lines.append(colorize(f"{g['header_left']}{g['separator'] * ((self.width - 2) // 3)}{g['header_right']}", *c["accent"]))
            lines.append(colorize(f"  {g['bullet_active']}  {title}", *c["accent"], bold=True))
            if subtitle:
                lines.append(colorize(f"  {g['bullet']}  {subtitle}", *c["text_dim"]))
            lines.append(colorize(g["separator"] * self.width, *c["border"]))

        elif self.style == "phantom_pulse":
            lines.append(self.box_top())
            lines.append(colorize(f"  {g['header_left']}  {title}  {g['header_right']}", *c["accent"], bold=True))
            if subtitle:
                lines.append(colorize(f"  {g['arrow']}  {subtitle}", *c["text_dim"]))
            lines.append(self.box_bottom())

        else:  # neural_glass
            lines.append(self.box_top())
            lines.append("")
            lines.append(colorize(f"  {g['header_left']}  {title}", *c["accent"], bold=True))
            if subtitle:
                lines.append(colorize(f"     {subtitle}", *c["text_dim"], dim=True))
            lines.append("")
            lines.append(self.box_bottom())

        return "\n".join(lines)

    # ─── Task List ───────────────────────────────────────────────────────

    def task_list(self, tasks: list[dict[str, Any]]) -> str:
        """
        Render a task / checklist.

        Each task: {"label": str, "status": "ok"|"pending"|"fail", "detail": str?}
        """
        lines: list[str] = []
        c = self._c
        g = self.glyphs

        for task in tasks:
            status = task.get("status", "pending")
            label = task.get("label", "")
            detail = task.get("detail", "")

            if status == "ok":
                icon = colorize(g["check"], *c["success"])
            elif status == "fail":
                icon = colorize(g["cross"], *c["error"])
            elif status == "warning":
                icon = colorize(g["warning"], *c["warning"])
            else:
                icon = colorize(g["pulse"], *c["text_faint"])

            row = f"  {icon}  {label}"
            if detail:
                row += colorize(f"  — {detail}", *c["text_faint"])
            lines.append(row)

        return "\n".join(lines)

    # ─── Key-Value Table ─────────────────────────────────────────────────

    def kv_table(self, data: dict[str, Any], label_width: int = 20) -> str:
        """Key-value table with aligned columns."""
        lines: list[str] = []
        c = self._c
        g = self.glyphs

        for key, value in data.items():
            k = colorize(f"  {g['bullet']} {key}:", *c["text_dim"]).ljust(label_width + 4)
            v = colorize(str(value), *c["text"])
            lines.append(f"{k} {v}")

        return "\n".join(lines)

    # ─── Error Block ─────────────────────────────────────────────────────

    def error_block(self, message: str, code: str = "", suggestion: str = "") -> str:
        """Error display block."""
        lines: list[str] = []
        c = self._c
        g = self.glyphs

        lines.append(self.box_top(colorize(f" {g['warning']} ERROR ", *c["error"], bold=True)))
        lines.append("")
        lines.append(colorize(f"  {message}", *c["error"], bold=True))
        lines.append("")

        if code:
            lines.append(colorize(f"  Code: {code}", *c["text_dim"]))

        if suggestion:
            lines.append("")
            lines.append(colorize(f"  {g['arrow']} {suggestion}", *c["text_dim"]))

        lines.append("")
        lines.append(self.box_bottom())
        return "\n".join(lines)

    # ─── Progress Block ──────────────────────────────────────────────────

    def progress_block(self, label: str, progress: float, detail: str = "") -> str:
        """Progress indicator with bar."""
        c = self._c
        g = self.glyphs
        bar_width = min(40, self.width - 20)
        bar = energy_bar(progress, bar_width, self.style)
        pct = f"{int(progress * 100)}%"

        line = f"  {g['bullet_active']} {label}  "
        line += colorize(bar, *c["accent"])
        line += f"  {colorize(pct, *c['accent'], bold=True)}"

        if detail:
            line += colorize(f"  — {detail}", *c["text_dim"])

        return line

    # ─── System Header (startup banner) ──────────────────────────────────

    def system_header(
        self,
        app: str = "HERMES / ZERA",
        version: str = "4.2",
        timestamp: str = "",
        extra: dict[str, str] | None = None,
    ) -> str:
        """Full system startup header."""
        lines: list[str] = []
        c = self._c
        g = self.glyphs
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.style == "void_prism":
            lines.append(colorize(f"{g['header_left']}{g['separator'] * ((self.width // 3))}{g['header_right']}", *c["accent3"]))
            lines.append("")
            lines.append(colorize(f"  {g['bullet_active']}{g['bullet_active']}{g['bullet_active']}  {app}", *c["accent"], bold=True))
            lines.append(colorize(f"  {g['diamond']}  v{version}", *c["accent2"]))
            lines.append("")
            lines.append(colorize(f"  {g['info']}  {ts}", *c["text_faint"]))
            if extra:
                for k, v in extra.items():
                    lines.append(colorize(f"  {g['bullet']}  {k}: {v}", *c["text_dim"]))
            lines.append("")
            lines.append(colorize(g["separator"] * self.width, *c["border"]))

        elif self.style == "phantom_pulse":
            lines.append(self.box_top())
            lines.append(colorize(f"  {g['header_left']}  {app}  {g['header_right']}", *c["accent"], bold=True))
            lines.append(colorize(f"  {g['arrow']}  v{version}", *c["accent3"]))
            lines.append(colorize(f"  {g['info']}  {ts}", *c["text_dim"]))
            if extra:
                for k, v in extra.items():
                    lines.append(colorize(f"  {g['bullet']}  {k}: {v}", *c["text_dim"]))
            lines.append(self.box_bottom())
            lines.append("")
            lines.append(self.wave_divider())

        else:  # neural_glass
            lines.append(self.box_top())
            lines.append("")
            lines.append(colorize(f"  {g['header_left']}  {app}", *c["accent"], bold=True))
            lines.append(colorize(f"     version {version}", *c["text_faint"]))
            lines.append("")
            lines.append(colorize(f"  {g['divider']}  {ts}", *c["text_dim"]))
            if extra:
                for k, v in extra.items():
                    lines.append(colorize(f"  {g['bullet']}  {k}: {v}", *c["text_dim"]))
            lines.append("")
            lines.append(self.box_bottom())

        return "\n".join(lines)

    # ─── Diff Summary ────────────────────────────────────────────────────

    def diff_summary(self, added: int = 0, modified: int = 0, deleted: int = 0) -> str:
        """Git-style diff summary with color-coded counts."""
        c = self._c
        g = self.glyphs

        parts = []
        if added:
            parts.append(colorize(f"+{added} added", *c["success"]))
        if modified:
            parts.append(colorize(f"~{modified} modified", *c["warning"]))
        if deleted:
            parts.append(colorize(f"-{deleted} deleted", *c["error"]))

        if not parts:
            return colorize(f"  {g['bullet']} no changes", *c["text_faint"])

        return "  ".join(parts)

    # ─── Trace Line (telemetry) ──────────────────────────────────────────

    def trace_line(self, level: str, component: str, message: str) -> str:
        """Single telemetry/trace line."""
        c = self._c
        ts = datetime.now().strftime("%H:%M:%S")

        level_colors = {
            "DEBUG": "text_faint",
            "INFO": "info",
            "OK": "success",
            "WARN": "warning",
            "ERROR": "error",
        }
        lc = level_colors.get(level.upper(), "text")

        lvl = colorize(f"[{level.upper()}]", *c[lc], bold=True)
        comp = colorize(f"[{component}]", *c["text_faint"])
        msg = colorize(message, *c["text"])
        time_s = colorize(ts, *c["text_faint"])

        return f"{time_s} {lvl} {comp} {msg}"


# ─── Convenience: Get Engine from Environment ─────────────────