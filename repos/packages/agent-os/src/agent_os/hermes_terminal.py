"""
Hermes/Zera Terminal Aesthetics Engine
════════════════════════════════════════
Three production-ready terminal design styles for report formatting and response rendering.

Styles:
  - void_prism:     Cyber-minimal with geometric depth
  - neural_glass:   Luxury monochrome with layered transparency
  - phantom_pulse:  Retro-futurist CRT with kinetic energy

Usage:
    from agent_os.hermes_terminal import Terminal, Style
    t = Terminal(style=Style.VOID_PRISM)
    print(t.report("System Status", sections=[...]))
    print(t.response("Analysis complete", body="..."))

Author: Antigravity Core Platform
"""

from __future__ import annotations

import os
import sys
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Terminal Capability Detection ───────────────────────────────────────────

def _detect_truecolor() -> bool:
    """Detect if terminal supports 24-bit true color."""
    if "COLORTERM" in os.environ:
        val = os.environ["COLORTERM"].lower()
        if "truecolor" in val or "24bit" in val:
            return True
    term = os.environ.get("TERM", "")
    if "24bit" in term or "truecolor" in term:
        return True
    return False


def _detect_unicode_width_issues() -> bool:
    """Detect potential Unicode width mismatches."""
    # Simple heuristic: check if we're in a known problematic environment
    term = os.environ.get("TERM_PROGRAM", "")
    if "Apple_Terminal" in term:
        return True  # macOS Terminal has known issues
    return False


def _get_terminal_width() -> int:
    """Get terminal width, with safe fallback."""
    try:
        cols = os.get_terminal_size().columns
        return max(cols, 80)
    except OSError:
        return 80


# ─── Color Constants (Truecolor RGB) ─────────────────────────────────────────

# Style 1: VOID PRISM
VOID_BG = (10, 10, 14)
VOID_ACCENT = (139, 92, 246)       # Violet
VOID_ACCENT2 = (6, 182, 212)       # Cyan
VOID_DIM = (75, 75, 90)
VOID_TEXT = (220, 220, 230)
VOID_BRIGHT = (255, 255, 255)
VOID_SUCCESS = (34, 197, 94)
VOID_WARN = (234, 179, 8)
VOID_ERROR = (239, 68, 68)
VOID_BORDER = (55, 55, 75)

# Style 2: NEURAL GLASS
GLASS_BG = (18, 18, 20)
GLASS_ACCENT = (217, 169, 87)      # Warm gold
GLASS_DIM = (80, 80, 85)
GLASS_TEXT = (200, 200, 205)
GLASS_BRIGHT = (240, 240, 245)
GLASS_SUCCESS = (120, 180, 140)
GLASS_WARN = (200, 170, 100)
GLASS_ERROR = (190, 90, 90)
GLASS_BORDER = (50, 50, 55)
GLASS_HIGHLIGHT = (40, 40, 45)

# Style 3: PHANTOM PULSE
PHANTOM_BG = (8, 6, 4)
PHANTOM_AMBER = (255, 170, 0)
PHANTOM_AMBER_DIM = (160, 110, 0)
PHANTOM_AMBER_BRIGHT = (255, 200, 50)
PHANTOM_RUST = (180, 80, 30)
PHANTOM_PHOSPHOR = (0, 255, 65)
PHANTOM_TEXT = (220, 180, 120)
PHANTOM_DIM = (100, 80, 50)
PHANTOM_SUCCESS = (0, 200, 50)
PHANTOM_WARN = (200, 150, 0)
PHANTOM_ERROR = (220, 60, 30)
PHANTOM_BORDER = (80, 60, 30)


# ─── ANSI Escape Code Helpers ────────────────────────────────────────────────

def fg(r: int, g: int, b: int, truecolor: bool = True) -> str:
    """Foreground color escape."""
    if truecolor:
        return f"\033[38;2;{r};{g};{b}m"
    # Fallback to nearest 16-color (simplified)
    return "\033[37m"


def bg(r: int, g: int, b: int, truecolor: bool = True) -> str:
    """Background color escape."""
    if truecolor:
        return f"\033[48;2;{r};{g};{b}m"
    return "\033[40m"


def style(codes: list[int]) -> str:
    """Apply SGR codes (bold, dim, underline, etc.)."""
    return f"\033[{';'.join(str(c) for c in codes)}m"


BOLD = style([1])
DIM = style([2])
ITALIC = style([3])
UNDERLINE = style([4])
RESET = "\033[0m"

# OSC 8 hyperlink
def hyperlink(text: str, url: str) -> str:
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


# ─── Style Enum ──────────────────────────────────────────────────────────────

class Style(Enum):
    VOID_PRISM = "void_prism"
    NEURAL_GLASS = "neural_glass"
    PHANTOM_PULSE = "phantom_pulse"


def resolve_style() -> Style:
    """Resolve style from env var or default to VOID_PRISM."""
    env = os.environ.get("HERMES_STYLE", "").lower()
    if env == "neural_glass":
        return Style.NEURAL_GLASS
    elif env == "phantom_pulse":
        return Style.PHANTOM_PULSE
    return Style.VOID_PRISM


# ─── Glyph Sets ──────────────────────────────────────────────────────────────

class Glyphs:
    """Unicode glyph collections per style."""

    VOID_PRISM = {
        "header_left": "◈ ",
        "header_right": " ◈",
        "separator": "◇",
        "divider": "◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆ ◇ ◆",
        "divider_thin": "◇ ─── ◇",
        "bullet": "◈",
        "bullet_sub": "├",
        "arrow": "▹",
        "check": "✓",
        "cross": "✕",
        "warn": "⚠",
        "info": "◉",
        "corner_tl": "◤",
        "corner_tr": "◥",
        "corner_bl": "◣",
        "corner_br": "◢",
        "line_v": "│",
        "line_h": "─",
        "line_cross": "┼",
        "progress_block": "▓",
        "progress_empty": "░",
        "diamond": "◇",
        "chevron_right": "▸",
        "chevron_double": "»",
    }

    NEURAL_GLASS = {
        "header_left": "⟡ ",
        "header_right": " ⟡",
        "separator": "·",
        "divider": "─ · ─ · ─ · ─ · ─ · ─ · ─ · ─",
        "divider_thin": "· ─── ·",
        "bullet": "·",
        "bullet_sub": ":",
        "arrow": "→",
        "check": "✓",
        "cross": "✗",
        "warn": "⚑",
        "info": "○",
        "corner_tl": "╭",
        "corner_tr": "╮",
        "corner_bl": "╰",
        "corner_br": "╯",
        "line_v": "│",
        "line_h": "─",
        "line_cross": "┼",
        "progress_block": "▄",
        "progress_empty": "▁",
        "diamond": "◇",
        "chevron_right": "›",
        "chevron_double": "»",
    }

    PHANTOM_PULSE = {
        "header_left": "⚡ ",
        "header_right": " ⚡",
        "separator": "┆",
        "divider": "━ ━ ╋ ━ ━ ╋ ━ ━ ╋ ━ ━ ╋ ━ ━",
        "divider_thin": "┆ ─── ┆",
        "bullet": "●",
        "bullet_sub": "•",
        "arrow": "▶",
        "check": "✔",
        "cross": "✘",
        "warn": "⚡",
        "info": "◉",
        "corner_tl": "╔",
        "corner_tr": "╗",
        "corner_bl": "╚",
        "corner_br": "╝",
        "line_v": "║",
        "line_h": "═",
        "line_cross": "╬",
        "progress_block": "█",
        "progress_empty": "▒",
        "diamond": "◆",
        "chevron_right": "▸",
        "chevron_double": "»",
    }


# ─── Layout Utilities ────────────────────────────────────────────────────────

def center(text: str, width: int) -> str:
    return text.center(width)


def pad(text: str, width: int, left: int = 2, right: int = 2) -> str:
    """Add left/right padding to each line."""
    lines = text.split("\n")
    pad_l = " " * left
    pad_r = " " * right
    total = width - left - right
    result = []
    for line in lines:
        wrapped = textwrap.wrap(line, width=total) if len(line) > total else [line]
        for w in wrapped:
            result.append(f"{pad_l}{w:<{total}}{pad_r}")
    return "\n".join(result)


def wrap_text(text: str, width: int) -> str:
    """Word-wrap text to width."""
    return "\n".join(textwrap.wrap(text, width=width))


# ═════════════════════════════════════════════════════════════════════════════
#  STYLE 1: VOID PRISM
#  Cyber-minimal with geometric depth
# ═════════════════════════════════════════════════════════════════════════════

class VoidPrism:
    """Cyber-minimal terminal style: deep void, sharp geometry, accent shifts."""

    def __init__(self, tc: bool = True):
        self.tc = tc
        self.g = Glyphs.VOID_PRISM
        self.c = {
            "accent": fg(*VOID_ACCENT, tc),
            "accent2": fg(*VOID_ACCENT2, tc),
            "dim": fg(*VOID_DIM, tc),
            "text": fg(*VOID_TEXT, tc),
            "bright": fg(*VOID_BRIGHT, tc),
            "success": fg(*VOID_SUCCESS, tc),
            "warn": fg(*VOID_WARN, tc),
            "error": fg(*VOID_ERROR, tc),
            "border": fg(*VOID_BORDER, tc),
            "bold": BOLD,
            "dim_style": DIM,
            "reset": RESET,
        }

    # ── Headers ─────────────────────────────────────────────────────
    def header(self, title: str, subtitle: str = "", width: int = 80) -> str:
        c = self.c
        g = self.g
        inner_w = width - 6  # account for corners + padding

        # Angled header
        top = f"{c['border']}{g['corner_tl']}{g['line_h'] * (inner_w - 2)}{g['corner_tr']}{c['reset']}"
        mid = (
            f"{c['border']}{g['line_v']}{c['reset']} "
            f"{c['bold']}{c['accent']}{g['header_left']}{title}{g['header_right']}{c['reset']}"
        )
        # Right-align to fill
        mid_padded = mid + " " * (width - len(mid.replace(c['bold'], '').replace(c['accent'], '').replace(c['reset'], '').replace(c['border'], '')))
        # Recalculate properly
        visible_mid = f" {g['header_left']}{title}{g['header_right']}"
        spaces_after = inner_w - 2 - len(visible_mid)
        if spaces_after < 0:
            spaces_after = 0
        mid = (
            f"{c['border']}{g['line_v']}{c['reset']}"
            f" {c['bold']}{c['accent']}{visible_mid}{c['reset']}"
            f"{' ' * spaces_after}"
            f"{c['border']}{g['line_v']}{c['reset']}"
        )
        bot = f"{c['border']}{g['corner_bl']}{g['line_h'] * (inner_w - 2)}{g['corner_br']}{c['reset']}"

        lines = [top, mid, bot]
        if subtitle:
            sub = f"  {c['dim']}{subtitle}{c['reset']}"
            lines.append(sub)
        return "\n".join(lines)

    # ── Section ─────────────────────────────────────────────────────
    def section(self, title: str, width: int = 80) -> str:
        c = self.c
        g = self.g
        inner = width - 4
        left = f"{c['accent']}{g['diamond']}{c['reset']} "
        right = f" {c['dim']}{g['divider']}{c['reset']}"
        # Fill remaining with thin line
        used = len(left.replace(c['accent'], '').replace(c['reset'], '')) + \
               len(title) + \
               len(right.replace(c['dim'], '').replace(c['reset'], ''))
        # Simplified: just use a fixed divider
        return f"{left}{c['bold']}{c['text']}{title}{c['reset']}{c['dim']}{' ' + g['separator'] + ' ' + g['separator'] + ' ' + g['separator']}{c['reset']}"

    # ── Panel ───────────────────────────────────────────────────────
    def panel(self, title: str, content: str, width: int = 80,
              accent_color: str = "accent") -> str:
        c = self.c
        g = self.g
        inner_w = width - 4
        color = c[accent_color] if accent_color in c else c["accent"]

        lines = []
        # Top border
        lines.append(f"{c['border']}╼{g['line_h'] * (inner_w - 1)}╾{c['reset']}")
        # Title line
        title_text = f"  {c['bold']}{color}{title}{c['reset']}" if title else ""
        title_vis = len(title) + 2 if title else 0
        spaces_after = max(0, inner_w - 2 - title_vis)
        lines.append(f"{c['border']}{g['line_v']}{c['reset']}{title_text}{' ' * spaces_after}{c['border']}{g['line_v']}{c['reset']}")
        # Divider
        lines.append(f"{c['border']}{g['line_v']}{c['reset']}  {c['dim']}{g['line_h'] * (inner_w - 4)}{c['reset']}  {c['border']}{g['line_v']}{c['reset']}")
        # Content
        content_lines = content.split("\n")
        for cl in content_lines:
            wrapped = textwrap.wrap(cl, width=inner_w - 4) if len(cl) > inner_w - 4 else [cl]
            for wl in wrapped:
                pad = max(0, inner_w - 2 - len(wl))
                lines.append(f"{c['border']}{g['line_v']}{c['reset']}  {c['text']}{wl}{' ' * pad}{c['border']}{g['line_v']}{c['reset']}")
        # Bottom border
        lines.append(f"{c['border']}╼{g['line_h'] * (inner_w - 1)}╾{c['reset']}")
        return "\n".join(lines)

    # ── Status Row ──────────────────────────────────────────────────
    def status_row(self, label: str, value: str, status: str = "ok",
                   width: int = 80) -> str:
        c = self.c
        g = self.g
        status_map = {"ok": c["success"], "warn": c["warn"], "error": c["error"]}
        sc = status_map.get(status, c["success"])
        icon = {"ok": g["check"], "warn": g["warn"], "error": g["cross"]}.get(status, g["check"])

        label_padded = f"{c['dim']}{label}:{c['reset']}"
        val = f"{c['text']}{value}{c['reset']}"
        st = f"{sc}{icon} {status.upper()}{c['reset']}"

        # Calculate spacing
        label_vis = len(label) + 1  # +1 for colon
        val_vis = len(value)
        st_vis = len(status) + 2  # +2 for icon + space
        gap = width - 4 - label_vis - val_vis - st_vis
        if gap < 2:
            gap = 2

        return f"  {label_padded}{' ' * gap}{val}{' ' * 2}{st}"

    # ── Progress Bar ────────────────────────────────────────────────
    def progress(self, value: float, width: int = 40, label: str = "") -> str:
        c = self.c
        g = self.g
        filled = int(value * width)
        bar = f"{c['accent']}{g['progress_block'] * filled}{c['dim']}{g['progress_empty'] * (width - filled)}{c['reset']}"
        pct = f"{c['bold']}{c['text']}{int(value * 100)}%{c['reset']}"
        if label:
            return f"  {c['dim']}{label}:{c['reset']}  {bar} {pct}"
        return f"  {bar} {pct}"

    # ── Key-Value Grid ──────────────────────────────────────────────
    def kv_grid(self, items: list[tuple[str, str]], width: int = 80,
                cols: int = 2) -> str:
        c = self.c
        g = self.g
        lines = []
        col_w = width // cols
        for i in range(0, len(items), cols):
            row_items = items[i:i + cols]
            parts = []
            for k, v in row_items:
                kv = f"  {c['dim']}{k}:{c['reset']} {c['text']}{v}{c['reset']}"
                parts.append(kv.ljust(col_w))
            lines.append("".join(parts))
        return "\n".join(lines)

    # ── List/Bullet Points ──────────────────────────────────────────
    def bullet_list(self, items: list[str], indent: int = 4,
                    bullet_color: str = "accent") -> str:
        c = self.c
        g = self.g
        bc = c[bullet_color] if bullet_color in c else c["accent"]
        lines = []
        for item in items:
            wrapped = textwrap.wrap(item, width=76 - indent)
            for j, wl in enumerate(wrapped):
                if j == 0:
                    lines.append(f"{' ' * indent}{bc}{g['bullet']}{c['reset']} {c['text']}{wl}{c['reset']}")
                else:
                    lines.append(f"{' ' * (indent + 2)}{c['dim']}{g['separator']}{c['reset']} {c['text']}{wl}{c['reset']}")
        return "\n".join(lines)

    # ── Divider ─────────────────────────────────────────────────────
    def divider(self, width: int = 80, style_type: str = "thin") -> str:
        c = self.c
        g = self.g
        if style_type == "thin":
            return f"  {c['dim']}{g['divider_thin']}{c['reset']}"
        return f"  {c['dim']}{g['divider']}{c['reset']}"

    # ── Full Report ─────────────────────────────────────────────────
    def report(self, title: str, sections: list[dict[str, Any]],
               width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        parts = []
        parts.append(self.header(title))
        parts.append("")
        for sec in sections:
            sec_title = sec.get("title", "")
            sec_content = sec.get("content", "")
            sec_items = sec.get("items", [])
            sec_status = sec.get("status", "ok")

            parts.append(self.section(sec_title))
            if sec_content:
                parts.append(self.panel("", sec_content))
            if sec_items:
                parts.append(self.bullet_list(sec_items))
            if sec_status != "ok" and not sec_content and not sec_items:
                parts.append(f"  {c['warn']}{self.g['warn']} {sec_status}{c['reset']}")
            parts.append("")
            parts.append(self.divider(width, "thin"))
            parts.append("")

        return "\n".join(parts)

    # ── Response ────────────────────────────────────────────────────
    def response(self, summary: str, body: str = "", metadata: dict | None = None,
                 width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        c = self.c
        g = self.g
        parts = []
        parts.append(self.divider(width, "thin"))
        parts.append(f"  {c['bold']}{c['accent']}{g['arrow']}{c['reset']} {c['bold']}{c['text']}{summary}{c['reset']}")
        parts.append(self.divider(width, "thin"))
        if body:
            wrapped = textwrap.wrap(body, width=width - 4)
            for line in wrapped:
                parts.append(f"  {c['text']}{line}{c['reset']}")
        if metadata:
            parts.append("")
            parts.append(self.divider(width, "thin"))
            for k, v in metadata.items():
                parts.append(f"  {c['dim']}{k}:{c['reset']} {c['dim']}{v}{c['reset']}")
        parts.append("")
        return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
#  STYLE 2: NEURAL GLASS
#  Luxury monochrome with layered transparency
# ═════════════════════════════════════════════════════════════════════════════

class NeuralGlass:
    """Luxury monochrome style: frosted glass, generous whitespace, single gold accent."""

    def __init__(self, tc: bool = True):
        self.tc = tc
        self.g = Glyphs.NEURAL_GLASS
        self.c = {
            "accent": fg(*GLASS_ACCENT, tc),
            "dim": fg(*GLASS_DIM, tc),
            "text": fg(*GLASS_TEXT, tc),
            "bright": fg(*GLASS_BRIGHT, tc),
            "success": fg(*GLASS_SUCCESS, tc),
            "warn": fg(*GLASS_WARN, tc),
            "error": fg(*GLASS_ERROR, tc),
            "border": fg(*GLASS_BORDER, tc),
            "highlight": bg(*GLASS_HIGHLIGHT, tc),
            "bold": BOLD,
            "dim_style": DIM,
            "reset": RESET,
        }

    # ── Headers ─────────────────────────────────────────────────────
    def header(self, title: str, subtitle: str = "", width: int = 80) -> str:
        c = self.c
        g = self.g

        # Spacious, editorial header
        header_text = f"{g['header_left']}{c['bold']}{c['accent']}{title}{c['reset']}{g['header_right']}"
        visible_len = len(title) + 4  # header_left + header_right ≈ 4 chars
        left_pad = (width - visible_len) // 2
        right_pad = width - visible_len - left_pad

        line = f"{' ' * left_pad}{header_text}{' ' * right_pad}"

        # Top and bottom rules — thin, generous
        rule = f"{c['dim']}{' ' * 2}{g['separator'] * (width // 2)}{' ' * 2}{c['reset']}"

        parts = [rule, "", line]
        if subtitle:
            sub = f"{' ' * (left_pad + 2)}{c['dim']}{subtitle}{c['reset']}"
            parts.append(sub)
            parts.append("")
        parts.append(rule)
        return "\n".join(parts)

    # ── Section ─────────────────────────────────────────────────────
    def section(self, title: str, width: int = 80) -> str:
        c = self.c
        g = self.g
        return f"\n{c['dim']}{g['divider']}{c['reset']}\n{c['bold']}{c['text']}  {title}{c['reset']}\n"

    # ── Card (panel with depth) ─────────────────────────────────────
    def card(self, title: str, content: str, width: int = 80,
             accent: bool = False) -> str:
        c = self.c
        g = self.g
        inner_w = width - 6
        ac = c["accent"] if accent else c["border"]

        lines = []
        # Soft card frame
        lines.append(f"  {c['border']}{g['corner_tl']}{g['line_h'] * inner_w}{g['corner_tr']}{c['reset']}")
        # Title with highlight
        title_bg = f"{c['highlight']}"
        title_line = f"  {c['border']}{g['line_v']}{c['reset']}{title_bg}  {ac}{c['bold']}{title}{c['reset']}"
        spaces = inner_w - 2 - len(title)
        if spaces < 0:
            spaces = 0
        title_line += f"{' ' * spaces}{c['border']}{g['line_v']}{c['reset']}"
        lines.append(title_line)
        # Content with generous padding
        content_lines = content.split("\n")
        for cl in content_lines:
            wrapped = textwrap.wrap(cl, width=inner_w - 2) if len(cl) > inner_w - 2 else [cl]
            for wl in wrapped:
                lines.append(f"  {c['border']}{g['line_v']}{c['reset']}  {c['text']}{wl}{' ' * max(0, inner_w - 2 - len(wl))}{c['border']}{g['line_v']}{c['reset']}")
        # Bottom
        lines.append(f"  {c['border']}{g['corner_bl']}{g['line_h'] * inner_w}{g['corner_br']}{c['reset']}")
        return "\n".join(lines)

    # ── Status Row ──────────────────────────────────────────────────
    def status_row(self, label: str, value: str, status: str = "ok",
                   width: int = 80) -> str:
        c = self.c
        g = self.g
        status_map = {"ok": c["success"], "warn": c["warn"], "error": c["error"]}
        sc = status_map.get(status, c["success"])
        icon = {"ok": g["check"], "warn": g["warn"], "error": g["cross"]}.get(status, g["check"])

        return (
            f"  {c['dim']}{label}{c['reset']}"
            f"{' ' * 2}"
            f"{c['text']}{value}{c['reset']}"
            f"{' ' * 2}"
            f"{sc}{icon}{c['reset']}"
        )

    # ── Progress Bar ────────────────────────────────────────────────
    def progress(self, value: float, width: int = 40, label: str = "") -> str:
        c = self.c
        g = self.g
        filled = int(value * width)
        bar = f"{c['accent']}{g['progress_block'] * filled}{c['dim']}{g['progress_empty'] * (width - filled)}{c['reset']}"
        pct = f"{c['dim']}{int(value * 100)}%{c['reset']}"
        if label:
            return f"  {c['dim']}{label}{c['reset']}  {bar}  {pct}"
        return f"  {bar}  {pct}"

    # ── Pull Quote (editorial callout) ──────────────────────────────
    def pull_quote(self, text: str, attribution: str = "", width: int = 80) -> str:
        c = self.c
        g = self.g
        inner_w = width - 8
        lines = []
        lines.append(f"  {c['dim']}{g['line_h'] * 3}{c['reset']}")
        wrapped = textwrap.wrap(text, width=inner_w)
        for wl in wrapped:
            lines.append(f"    {c['accent']}{g['separator']}{c['reset']}  {c['italic']}{c['text']}{ITALIC}{wl}{c['reset']}")
        if attribution:
            lines.append(f"    {c['dim']}— {attribution}{c['reset']}")
        lines.append(f"  {c['dim']}{g['line_h'] * 3}{c['reset']}")
        return "\n".join(lines)

    # ── Key-Value Grid ──────────────────────────────────────────────
    def kv_grid(self, items: list[tuple[str, str]], width: int = 80,
                cols: int = 2) -> str:
        c = self.c
        col_w = width // cols
        lines = []
        for i in range(0, len(items), cols):
            row_items = items[i:i + cols]
            parts = []
            for k, v in row_items:
                kv = f"  {c['dim']}{k}{c['reset']}  {c['text']}{v}{c['reset']}"
                parts.append(kv.ljust(col_w))
            lines.append("".join(parts))
        return "\n".join(lines)

    # ── Bullet List ─────────────────────────────────────────────────
    def bullet_list(self, items: list[str], indent: int = 4) -> str:
        c = self.c
        g = self.g
        lines = []
        for item in items:
            wrapped = textwrap.wrap(item, width=76 - indent)
            for j, wl in enumerate(wrapped):
                if j == 0:
                    lines.append(f"{' ' * indent}{c['accent']}{g['bullet']}{c['reset']}  {c['text']}{wl}{c['reset']}")
                else:
                    lines.append(f"{' ' * (indent + 3)}{c['dim']}{wl}{c['reset']}")
        return "\n".join(lines)

    # ── Divider ─────────────────────────────────────────────────────
    def divider(self, width: int = 80) -> str:
        c = self.c
        g = self.g
        return f"\n{c['dim']}{' ' * 2}{g['separator'] * (width // 2)}{' ' * 2}{c['reset']}\n"

    # ── Full Report ─────────────────────────────────────────────────
    def report(self, title: str, sections: list[dict[str, Any]],
               width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        parts = []
        parts.append(self.header(title))
        parts.append("")
        for sec in sections:
            sec_title = sec.get("title", "")
            sec_content = sec.get("content", "")
            sec_items = sec.get("items", [])
            sec_accent = sec.get("accent", False)

            parts.append(self.section(sec_title))
            if sec_content:
                parts.append(self.card("", sec_content, accent=sec_accent))
            if sec_items:
                parts.append(self.bullet_list(sec_items))
            parts.append("")

        return "\n".join(parts)

    # ── Response ────────────────────────────────────────────────────
    def response(self, summary: str, body: str = "", metadata: dict | None = None,
                 width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        c = self.c
        g = self.g
        parts = []
        parts.append(self.divider(width))
        parts.append(f"  {c['accent']}{g['arrow']}{c['reset']}  {c['bold']}{c['text']}{summary}{c['reset']}")
        parts.append(self.divider(width))
        if body:
            parts.append("")
            wrapped = textwrap.wrap(body, width=width - 6)
            for line in wrapped:
                parts.append(f"    {c['text']}{line}{c['reset']}")
        if metadata:
            parts.append("")
            parts.append(self.divider(width))
            for k, v in metadata.items():
                parts.append(f"  {c['dim']}{k}{c['reset']}  {c['dim']}{v}{c['reset']}")
        parts.append("")
        return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
#  STYLE 3: PHANTOM PULSE
#  Retro-futurist CRT with kinetic energy
# ═════════════════════════════════════════════════════════════════════════════

class PhantomPulse:
    """Retro-futurist CRT style: amber phosphor, scanline mood, telemetry cockpit."""

    def __init__(self, tc: bool = True):
        self.tc = tc
        self.g = Glyphs.PHANTOM_PULSE
        self.c = {
            "amber": fg(*PHANTOM_AMBER, tc),
            "amber_dim": fg(*PHANTOM_AMBER_DIM, tc),
            "amber_bright": fg(*PHANTOM_AMBER_BRIGHT, tc),
            "rust": fg(*PHANTOM_RUST, tc),
            "phosphor": fg(*PHANTOM_PHOSPHOR, tc),
            "text": fg(*PHANTOM_TEXT, tc),
            "dim": fg(*PHANTOM_DIM, tc),
            "success": fg(*PHANTOM_SUCCESS, tc),
            "warn": fg(*PHANTOM_WARN, tc),
            "error": fg(*PHANTOM_ERROR, tc),
            "border": fg(*PHANTOM_BORDER, tc),
            "bold": BOLD,
            "dim_style": DIM,
            "reset": RESET,
        }

    # ── Headers ─────────────────────────────────────────────────────
    def header(self, title: str, subtitle: str = "", width: int = 80) -> str:
        c = self.c
        g = self.g
        inner_w = width - 4

        # Double-line box with amber title
        top = f"{c['border']}{g['corner_tl']}{g['line_h'] * inner_w}{g['corner_tr']}{c['reset']}"
        inner_border = f"{c['border']}{g['line_v']}{' ' * inner_w}{g['line_v']}{c['reset']}"

        title_centered = f"{c['amber_bright']}{c['bold']} {title} {c['reset']}"
        title_vis = len(title) + 2
        left_sp = (inner_w - title_vis) // 2
        right_sp = inner_w - title_vis - left_sp
        if left_sp < 0:
            left_sp = 0
            right_sp = 0
        title_line = f"{c['border']}{g['line_v']}{' ' * left_sp}{title_centered}{' ' * right_sp}{c['border']}{g['line_v']}{c['reset']}"

        bot = f"{c['border']}{g['corner_bl']}{g['line_h'] * inner_w}{g['corner_br']}{c['reset']}"

        lines = [top, inner_border, title_line, inner_border, bot]
        if subtitle:
            lines.append(f"  {c['amber_dim']}⟨ {subtitle} ⟩{c['reset']}")
        # Energy bar beneath header
        lines.append(self._energy_bar(width))
        return "\n".join(lines)

    def _energy_bar(self, width: int = 80) -> str:
        """Kinetic energy bar — static representation of system energy."""
        c = self.c
        g = self.g
        inner_w = width - 4
        # Create a wave-like pattern using block characters
        wave = ""
        for i in range(inner_w):
            phase = (i % 8) / 8.0
            if phase < 0.25:
                wave += f"{c['amber_dim']}▁{c['reset']}"
            elif phase < 0.5:
                wave += f"{c['amber']}▃{c['reset']}"
            elif phase < 0.75:
                wave += f"{c['amber_bright']}▅{c['reset']}"
            else:
                wave += f"{c['amber']}▇{c['reset']}"
        return f"  {wave}"

    # ── Section ─────────────────────────────────────────────────────
    def section(self, title: str, width: int = 80) -> str:
        c = self.c
        g = self.g
        return (
            f"\n{c['border']}{g['divider']}{c['reset']}\n"
            f"  {c['amber']}{c['bold']}{g['bullet']} {title}{c['reset']}\n"
        )

    # ── Telemetry Panel ─────────────────────────────────────────────
    def panel(self, title: str, content: str, width: int = 80) -> str:
        c = self.c
        g = self.g
        inner_w = width - 6

        lines = []
        lines.append(f"  {c['border']}{g['corner_tl']}{g['line_h'] * inner_w}{g['corner_tr']}{c['reset']}")
        # Title
        title_text = f"  {c['amber']}{c['bold']}{title}{c['reset']}" if title else ""
        title_vis = len(title) + 2 if title else 0
        spaces_after = max(0, inner_w - 2 - title_vis)
        lines.append(f"  {c['border']}{g['line_v']}{c['reset']}{title_text}{' ' * spaces_after}{c['border']}{g['line_v']}{c['reset']}")
        # Rust separator
        lines.append(f"  {c['border']}{g['line_v']}{c['reset']}  {c['rust']}{g['line_h'] * (inner_w - 2)}{c['reset']}  {c['border']}{g['line_v']}{c['reset']}")
        # Content
        content_lines = content.split("\n")
        for cl in content_lines:
            wrapped = textwrap.wrap(cl, width=inner_w - 2) if len(cl) > inner_w - 2 else [cl]
            for wl in wrapped:
                pad = max(0, inner_w - 2 - len(wl))
                lines.append(f"  {c['border']}{g['line_v']}{c['reset']}  {c['text']}{wl}{' ' * pad}{c['border']}{g['line_v']}{c['reset']}")
        lines.append(f"  {c['border']}{g['corner_bl']}{g['line_h'] * inner_w}{g['corner_br']}{c['reset']}")
        return "\n".join(lines)

    # ── Status Row ──────────────────────────────────────────────────
    def status_row(self, label: str, value: str, status: str = "ok",
                   width: int = 80) -> str:
        c = self.c
        g = self.g
        status_map = {
            "ok": c["phosphor"],
            "warn": c["warn"],
            "error": c["error"],
        }
        sc = status_map.get(status, c["phosphor"])
        icon = {"ok": g["check"], "warn": g["warn"], "error": g["cross"]}.get(status, g["check"])

        return (
            f"  {c['amber_dim']}{label}:{c['reset']} "
            f"{c['text']}{value}{c['reset']}"
            f"  {sc}{icon} {status.upper()}{c['reset']}"
        )

    # ── Progress Bar ────────────────────────────────────────────────
    def progress(self, value: float, width: int = 40, label: str = "") -> str:
        c = self.c
        g = self.g
        filled = int(value * width)
        # Gradient effect: amber_bright → amber → amber_dim
        bar = ""
        for i in range(filled):
            ratio = i / max(filled - 1, 1)
            if ratio < 0.33:
                bar += f"{c['amber_bright']}{g['progress_block']}{c['reset']}"
            elif ratio < 0.66:
                bar += f"{c['amber']}{g['progress_block']}{c['reset']}"
            else:
                bar += f"{c['amber_dim']}{g['progress_block']}{c['reset']}"
        bar += f"{c['dim']}{g['progress_empty'] * (width - filled)}{c['reset']}"
        pct = f"{c['amber_bright']}{int(value * 100)}%{c['reset']}"
        if label:
            return f"  {c['amber_dim']}{label}:{c['reset']}  {bar} {pct}"
        return f"  {bar} {pct}"

    # ── Telemetry Grid ──────────────────────────────────────────────
    def telemetry_grid(self, items: list[tuple[str, str]], width: int = 80,
                       cols: int = 2) -> str:
        """Like kv_grid but with phosphor status dots."""
        c = self.c
        col_w = width // cols
        lines = []
        for k, v in items:
            lines.append(f"  {c['amber_dim']}{k}:{c['reset']}  {c['text']}{v}{c['reset']}")
        return "\n".join(lines)

    # ── Bullet List ─────────────────────────────────────────────────
    def bullet_list(self, items: list[str], indent: int = 4) -> str:
        c = self.c
        g = self.g
        lines = []
        for item in items:
            wrapped = textwrap.wrap(item, width=76 - indent)
            for j, wl in enumerate(wrapped):
                if j == 0:
                    lines.append(f"{' ' * indent}{c['amber']}{g['bullet']}{c['reset']}  {c['text']}{wl}{c['reset']}")
                else:
                    lines.append(f"{' ' * (indent + 3)}{c['dim']}{g['separator']} {c['text']}{wl}{c['reset']}")
        return "\n".join(lines)

    # ── Divider ─────────────────────────────────────────────────────
    def divider(self, width: int = 80) -> str:
        c = self.c
        g = self.g
        return f"\n{c['border']}{g['divider']}{c['reset']}\n"

    # ── Scanline Effect (decorative) ────────────────────────────────
    def scanline(self, width: int = 80, intensity: float = 0.3) -> str:
        """Subtle scanline decoration."""
        c = self.c
        g = self.g
        chars = []
        for i in range(width - 4):
            if i % 4 == 0:
                chars.append(f"{c['dim']}·{c['reset']}")
            else:
                chars.append(f"{c['dim']} {c['reset']}")
        return "  " + "".join(chars)

    # ── Full Report ─────────────────────────────────────────────────
    def report(self, title: str, sections: list[dict[str, Any]],
               width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        parts = []
        parts.append(self.header(title))
        parts.append("")
        for sec in sections:
            sec_title = sec.get("title", "")
            sec_content = sec.get("content", "")
            sec_items = sec.get("items", [])

            parts.append(self.section(sec_title))
            if sec_content:
                parts.append(self.panel("", sec_content))
            if sec_items:
                parts.append(self.bullet_list(sec_items))
            parts.append("")
            parts.append(self.scanline(width))
            parts.append("")

        return "\n".join(parts)

    # ── Response ────────────────────────────────────────────────────
    def response(self, summary: str, body: str = "", metadata: dict | None = None,
                 width: int | None = None) -> str:
        if width is None:
            width = _get_terminal_width()
        c = self.c
        g = self.g
        parts = []
        parts.append(self.divider(width))
        parts.append(f"  {c['amber_bright']}{c['bold']}{g['arrow']}{c['reset']} {c['bold']}{c['text']}{summary}{c['reset']}")
        parts.append(self.divider(width))
        if body:
            parts.append("")
            wrapped = textwrap.wrap(body, width=width - 6)
            for line in wrapped:
                parts.append(f"    {c['text']}{line}{c['reset']}")
        if metadata:
            parts.append("")
            parts.append(self.scanline(width))
            for k, v in metadata.items():
                parts.append(f"  {c['amber_dim']}{k}:{c['reset']} {c['dim']}{v}{c['reset']}")
        parts.append("")
        return "\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════════
#  UNIFIED TERMINAL CLASS
# ═════════════════════════════════════════════════════════════════════════════

class Terminal:
    """Unified terminal formatter with style switching."""

    def __init__(self, style: "Style | None" = None, width: "int | None" = None):
        self.style = style or resolve_style()
        self.width = width
        self._renderer: Any = None  # Set in _init_renderer
        self._init_renderer()

    def _init_renderer(self) -> None:
        tc = _detect_truecolor()
        if self.style == Style.VOID_PRISM:
            self._renderer = VoidPrism(tc)
        elif self.style == Style.NEURAL_GLASS:
            self._renderer = NeuralGlass(tc)
        elif self.style == Style.PHANTOM_PULSE:
            self._renderer = PhantomPulse(tc)

    # ── Delegate all methods to renderer ─────────────────────────────

    def header(self, title: str, subtitle: str = "") -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.header(title, subtitle, w)

    def section(self, title: str) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.section(title, w)

    def panel(self, title: str, content: str) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.panel(title, content, w)

    def card(self, title: str, content: str, accent: bool = False) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.card(title, content, w, accent)

    def status_row(self, label: str, value: str, status: str = "ok") -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.status_row(label, value, status, w)

    def progress(self, value: float, width: int = 40, label: str = "") -> str:
        return self._renderer.progress(value, width, label)

    def kv_grid(self, items: list[tuple[str, str]], cols: int = 2) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.kv_grid(items, w, cols)

    def telemetry_grid(self, items: list[tuple[str, str]], cols: int = 2) -> str:
        w = self.width or _get_terminal_width()
        if isinstance(self._renderer, PhantomPulse):
            return self._renderer.telemetry_grid(items, w, cols)
        return self._renderer.kv_grid(items, w, cols)

    def bullet_list(self, items: list[str]) -> str:
        return self._renderer.bullet_list(items)

    def divider(self) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.divider(w)

    def pull_quote(self, text: str, attribution: str = "") -> str:
        w = self.width or _get_terminal_width()
        if isinstance(self._renderer, NeuralGlass):
            return self._renderer.pull_quote(text, attribution, w)
        return f"\n  {DIM}「{text}」{RESET}\n"

    def report(self, title: str, sections: list[dict[str, Any]]) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.report(title, sections, w)

    def response(self, summary: str, body: str = "",
                 metadata: dict | None = None) -> str:
        w = self.width or _get_terminal_width()
        return self._renderer.response(summary, body, metadata, w)

    # ── Style switching ─────────────────────────────────────────────
    def switch(self, style: Style) -> None:
        """Switch to a different style at runtime."""
        self.style = style
        self._renderer = {
            Style.VOID_PRISM: VoidPrism(_detect_truecolor()),
            Style.NEURAL_GLASS: NeuralGlass(_detect_truecolor()),
            Style.PHANTOM_PULSE: PhantomPulse(_detect_truecolor()),
        }[style]

    # ── Quick constructors ──────────────────────────────────────────
    @classmethod
    def void_prism(cls, **kw: Any) -> "Terminal":
        return cls(style=Style.VOID_PRISM, **kw)

    @classmethod
    def neural_glass(cls, **kw: Any) -> "Terminal":
        return cls(style=Style.NEURAL_GLASS, **kw)

    @classmethod
    def phantom_pulse(cls, **kw: Any) -> "Terminal":
        return cls(style=Style.PHANTOM_PULSE, **kw)


# ─── Convenience Functions (module-level API) ─────────────────────────────────

def get_terminal() -> Terminal:
    """Get a terminal with the currently configured style."""
    return Terminal()


def report(title: str, sections: list[dict[str, Any]]) -> str:
    """Quick report with default style."""
    return get_terminal().report(title, sections)


def response(summary: str, body: str = "", metadata: dict | None = None) -> str:
    """Quick response with default style."""
    return get_terminal().response(summary, body, metadata)


# ─── CLI Demo ─────────────────────────────────────────────────────────────────

def _demo() -> None:
    """Run a full demo of all three styles."""

    sample_sections = [
        {
            "title": "System Health",
            "content": "All subsystems operational. Memory usage nominal. No anomalies detected in the last 47 cycles.",
            "items": ["Agent OS: v4.2.0", "Active workflows: 12", "Model routing: OpenRouter primary"],
            "status": "ok",
        },
        {
            "title": "Task Execution",
            "content": "Processed 234 tasks in the last hour. Average completion time: 4.2s. Zero failures.",
            "items": ["C1 trivial: 89 completed", "C3 medium: 42 completed", "C4 complex: 3 completed"],
            "status": "ok",
        },
        {
            "title": "Memory Index",
            "content": "BM25 index contains 14,892 entries. LightRAG nodes: 3,201. Retrieval latency: 12ms avg.",
            "status": "ok",
        },
    ]

    sample_metadata = {
        "command_id": "zera:status",
        "client": "hermes",
        "timestamp": "2026-04-15T14:32:00Z",
        "style": "auto-detected",
    }

    for style in Style:
        t = Terminal(style=style)
        print(f"\n{'=' * 80}")
        print(f"  STYLE: {style.value.upper()}")
        print(f"{'=' * 80}\n")

        print(t.report("⚕ Hermes/Zera — System Report", sample_sections))
        print()
        print(t.response(
            "Analysis complete — all systems nominal",
            body="The system is operating within expected parameters. "
                 "No degradation detected across any monitored axis. "
                 "Next full diagnostic scheduled for 06:00 UTC.",
            metadata=sample_metadata,
        ))
        print("\n")


if __name__ == "__main__":
    _demo()
