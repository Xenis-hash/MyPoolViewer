"""
MyPoolViewer — Blueprint Renderer  (Phase 4)
============================================
Generates a top-down 2D SVG pool diagram comprising:

  LAYER 1 — Pool shell
    • Rectangular pool body (with rounded corners)
    • Overflow channel (overflow / infinity types)
    • Infinity vanishing edge callout
    • Liner fill tint (skimmer / infinity types)

  LAYER 2 — Pool shell components (positioned to scale)
    • Main drains  (centred on pool floor, pair shown side by side)
    • Return inlets (evenly distributed around pool walls)
    • Skimmer box  (skimmer type only, on long wall)
    • Overflow grille segments (overflow / infinity perimeter)
    • Underwater lights (evenly distributed on long walls)
    • Robot cleaner (inside pool, corner)

  LAYER 3 — Engine room
    • Dimensioned rectangle adjacent to short pool wall
    • Equipment blocks placed on a grid:
        Filter cylinder, Pump, Treatment unit,
        Valve manifold, Air blower, Heater,
        Dehumidifier, Automation cabinet,
        Chemical tanks, Robot charging dock
    • Flow arrows connecting pool → strainer → pump
      → manifold → filter → treatment → pool

  LAYER 4 — Annotations
    • Dimension lines: pool W × L, engine room W × D
    • Equipment labels with catalog codes
    • North arrow + scale bar
    • Title block (pool type, filtration, volume, design flow)
    • Legend

Usage:
    from blueprint import generate_svg
    svg_str = generate_svg(pool_inputs, calculation_result)

Or CLI:
    python blueprint.py
"""

import math
import sys
import os

# Allow running standalone without server context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calculator import PoolInputs, CalculationResult, calculate, CSV_PATH



def _xml(s: str) -> str:
    """Escape special XML characters in text content."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ══════════════════════════════════════════════════════════════════════════════
# 1. DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

PALETTE = {
    "bg":           "#0a0e1a",   # slide background
    "paper":        "#0f1628",   # drawing area
    "pool_water":   "#0e2a3a",   # pool fill
    "pool_edge":    "#4dd9ec",   # pool outline
    "pool_edge2":   "#1a8fa0",   # secondary edge
    "overflow_ch":  "#0d2233",   # overflow channel
    "engine_bg":    "#141d35",   # engine room fill
    "engine_edge":  "#6b7fa3",   # engine room outline
    "equip_fill":   "#0f1e38",   # equipment block fill
    "equip_edge":   "#1a8fa0",   # equipment block outline
    "flow_arrow":   "#4dd9ec",   # flow direction arrows
    "return_arrow": "#c9a84c",   # return flow arrows
    "dim_line":     "#6b7fa3",   # dimension lines
    "dim_text":     "#9ab0c8",   # dimension text
    "label_text":   "#f0f4f8",   # primary labels
    "label_muted":  "#6b7fa3",   # secondary labels
    "code_text":    "#4dd9ec",   # catalog code text
    "accent":       "#c9a84c",   # gold accent
    "drain":        "#1a8fa0",   # drain symbol
    "inlet":        "#22b5cc",   # inlet symbol
    "light":        "#f0e860",   # light symbol
    "skimmer":      "#2a7fa0",   # skimmer symbol
    "grille":       "#4dd9ec",   # overflow grille
    "robot":        "#8898c8",   # robot symbol
    "shimmer1":     "rgba(77,217,236,0.04)",
    "shimmer2":     "rgba(77,217,236,0.07)",
    # Shorthand aliases
    "teal":         "#1a8fa0",
    "aqua":         "#4dd9ec",
}

# Fonts (web-safe fallbacks, no external deps)
FONT_TITLE  = "Georgia, 'Times New Roman', serif"
FONT_BODY   = "'Calibri', 'Helvetica Neue', Arial, sans-serif"
FONT_CODE   = "'Courier New', Courier, monospace"

# SVG canvas
CANVAS_W    = 1400
CANVAS_H    = 900
MARGIN      = 60      # outer margin px
TITLE_H     = 80      # title block height
LEGEND_H    = 50      # legend strip height
DRAWING_PAD = 24      # inner padding around drawing area

# Engine room is always to the RIGHT of the pool
ENGINE_GAP  = 40      # gap between pool and engine room
MIN_ER_W    = 180     # minimum engine room width (px)


# ══════════════════════════════════════════════════════════════════════════════
# 2. LAYOUT CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

class Layout:
    """
    Converts real-world metres into SVG pixel coordinates.

    The available drawing area is split into:
        [pool zone]  [gap]  [engine room zone]

    Scale is determined by fitting both into the available width,
    constrained to also fit the pool height.
    """

    def __init__(self, inp: PoolInputs, result: CalculationResult):
        self.inp    = inp
        self.result = result

        # Available drawing rectangle
        self.draw_x = MARGIN + DRAWING_PAD
        self.draw_y = MARGIN + TITLE_H + DRAWING_PAD
        self.draw_w = CANVAS_W - 2 * (MARGIN + DRAWING_PAD)
        self.draw_h = CANVAS_H - self.draw_y - LEGEND_H - MARGIN - DRAWING_PAD

        # Engine room real-world dimensions (metres)
        er_area = result.engine_room_m2
        er_depth_m = max(2.5, math.sqrt(er_area / 1.6))   # aspect ~1.6 : 1
        er_width_m = er_area / er_depth_m

        # Scale: fit pool + gap + engine room in available width
        # and pool height in available height
        gap_m = 1.5   # real-world gap in metres (symbolic)
        total_w_m = inp.width_m + gap_m + er_width_m
        scale_x = self.draw_w / total_w_m
        scale_y = self.draw_h / inp.length_m
        self.scale = min(scale_x, scale_y) * 0.88   # 12% breathing room

        # Pool pixel dimensions
        self.pool_px_w = inp.width_m  * self.scale
        self.pool_px_l = inp.length_m * self.scale

        # Centre everything vertically
        total_px_h = self.pool_px_l
        y_offset   = (self.draw_h - total_px_h) / 2

        # Pool origin (top-left of pool)
        self.pool_x = self.draw_x + (self.draw_w - (total_w_m * self.scale)) / 2
        self.pool_y = self.draw_y + y_offset

        # Engine room pixel dimensions
        self.er_px_w = er_width_m * self.scale
        self.er_px_h = er_depth_m * self.scale
        self.er_x    = self.pool_x + self.pool_px_w + gap_m * self.scale
        self.er_y    = self.pool_y + (self.pool_px_l - self.er_px_h) / 2

        # Store for label use
        self.er_width_m  = er_width_m
        self.er_depth_m  = er_depth_m
        self.gap_m       = gap_m

    def m2px(self, metres: float) -> float:
        return metres * self.scale

    def pool_cx(self) -> float:
        return self.pool_x + self.pool_px_w / 2

    def pool_cy(self) -> float:
        return self.pool_y + self.pool_px_l / 2


# ══════════════════════════════════════════════════════════════════════════════
# 3. SVG HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _attrs(**kw) -> str:
    parts = []
    for k, v in kw.items():
        attr = k.replace("_", "-")
        parts.append(f'{attr}="{v}"')
    return " ".join(parts)


def rect(x, y, w, h, rx=0, **kw) -> str:
    return f'<rect {_attrs(x=round(x,2), y=round(y,2), width=round(w,2), height=round(h,2), rx=rx, **kw)}/>'


def circle(cx, cy, r, **kw) -> str:
    return f'<circle {_attrs(cx=round(cx,2), cy=round(cy,2), r=round(r,2), **kw)}/>'


def line(x1, y1, x2, y2, **kw) -> str:
    return f'<line {_attrs(x1=round(x1,2), y1=round(y1,2), x2=round(x2,2), y2=round(y2,2), **kw)}/>'


def text(x, y, content, **kw) -> str:
    attrs = _attrs(x=round(x,2), y=round(y,2), **kw)
    return f'<text {attrs}>{_xml(content)}</text>'


def arrow_marker(id_: str, color: str, size: int = 8) -> str:
    """SVG <defs> marker for arrowheads."""
    return f'''<marker id="{id_}" markerWidth="{size}" markerHeight="{size}"
        refX="{size-1}" refY="{size//2}" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,{size} L{size},{size//2} z" fill="{color}"/>
    </marker>'''


def dim_line(x1, y1, x2, y2, label, offset=22, vertical=False) -> str:
    """Dimension line with arrowheads and centred label."""
    col = PALETTE["dim_line"]
    tc  = PALETTE["dim_text"]
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    parts = []
    # Main line
    parts.append(f'<line x1="{round(x1,2)}" y1="{round(y1,2)}" '
                 f'x2="{round(x2,2)}" y2="{round(y2,2)}" '
                 f'stroke="{col}" stroke-width="1" '
                 f'marker-start="url(#dimstart)" marker-end="url(#dimend)"/>')
    # Tick lines
    if vertical:
        parts.append(line(x1 - 8, y1, x1 + 8, y1, stroke=col, stroke_width="0.8"))
        parts.append(line(x2 - 8, y2, x2 + 8, y2, stroke=col, stroke_width="0.8"))
        # Label (rotated)
        parts.append(f'<text x="{round(mid_x - offset,2)}" y="{round(mid_y,2)}" '
                     f'fill="{tc}" font-family="{FONT_BODY}" font-size="11" '
                     f'text-anchor="middle" '
                     f'transform="rotate(-90 {round(mid_x-offset,2)} {round(mid_y,2)})">'
                     f'{label}</text>')
    else:
        parts.append(line(x1, y1 - 8, x1, y1 + 8, stroke=col, stroke_width="0.8"))
        parts.append(line(x2, y2 - 8, x2, y2 + 8, stroke=col, stroke_width="0.8"))
        parts.append(text(mid_x, mid_y - offset + 4, label,
                          fill=tc, font_family=FONT_BODY, font_size="11",
                          text_anchor="middle"))
    return "\n".join(parts)


def equip_block(x, y, w, h, code, label, sublabel="", color=None, symbol=None) -> str:
    """Labelled equipment block for the engine room."""
    ec  = color or PALETTE["equip_edge"]
    parts = []
    parts.append(rect(x, y, w, h, rx=3,
                      fill=PALETTE["equip_fill"],
                      stroke=ec, stroke_width="1"))
    # Top accent bar
    parts.append(rect(x, y, w, 3, rx=0, fill=ec))
    # Symbol / icon (simple geometric)
    if symbol == "cylinder":
        cx = x + w / 2
        cr = min(w * 0.28, h * 0.28)
        parts.append(circle(cx, y + h * 0.38, cr,
                            fill="none", stroke=ec, stroke_width="1.2"))
        parts.append(line(cx - cr, y + h * 0.38, cx - cr, y + h * 0.55,
                          stroke=ec, stroke_width="1"))
        parts.append(line(cx + cr, y + h * 0.38, cx + cr, y + h * 0.55,
                          stroke=ec, stroke_width="1"))
        parts.append(f'<ellipse cx="{round(cx,2)}" cy="{round(y+h*0.55,2)}" '
                     f'rx="{round(cr,2)}" ry="{round(cr*0.3,2)}" '
                     f'fill="none" stroke="{ec}" stroke-width="1"/>')
    elif symbol == "pump":
        cx = x + w * 0.38; cy = y + h * 0.38; r2 = min(w, h) * 0.2
        parts.append(circle(cx, cy, r2, fill="none", stroke=ec, stroke_width="1.2"))
        # impeller blades
        for angle in range(0, 360, 72):
            rad = math.radians(angle)
            bx = cx + r2 * 0.6 * math.cos(rad)
            by = cy + r2 * 0.6 * math.sin(rad)
            parts.append(line(cx, cy, round(bx,2), round(by,2),
                              stroke=ec, stroke_width="0.8"))
    elif symbol == "box":
        bw = w * 0.5; bh = h * 0.35
        parts.append(rect(x + (w - bw)/2, y + h * 0.12, bw, bh,
                          rx=2, fill="none", stroke=ec, stroke_width="1"))

    # Labels
    fs_label  = max(8, min(11, w / 7))
    fs_sub    = max(7, min(9,  w / 9))
    fs_code   = max(6, min(8,  w / 10))
    lx = x + w / 2
    ly = y + h - (18 if sublabel else 12)
    parts.append(text(lx, ly, label,
                      fill=PALETTE["label_text"],
                      font_family=FONT_BODY,
                      font_size=str(round(fs_label, 1)),
                      text_anchor="middle", font_weight="400"))
    if sublabel:
        parts.append(text(lx, y + h - 8, sublabel,
                          fill=PALETTE["label_muted"],
                          font_family=FONT_BODY,
                          font_size=str(round(fs_sub, 1)),
                          text_anchor="middle"))
    if code:
        parts.append(text(lx, y + 12, code,
                          fill=PALETTE["code_text"],
                          font_family=FONT_CODE,
                          font_size=str(round(fs_code, 1)),
                          text_anchor="middle"))
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# 4. LAYER RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def render_defs() -> str:
    """SVG <defs>: markers, gradients, patterns."""
    p = PALETTE
    return f"""<defs>
  {arrow_marker('dimstart', p['dim_line'], 6)}
  {arrow_marker('dimend',   p['dim_line'], 6)}
  {arrow_marker('flowarr',  p['flow_arrow'], 7)}
  {arrow_marker('retarr',   p['return_arrow'], 7)}
  <marker id="dimstart" markerWidth="6" markerHeight="6"
    refX="1" refY="3" orient="auto-start-reverse" markerUnits="strokeWidth">
    <path d="M0,3 L6,0 L6,6 z" fill="{p['dim_line']}"/>
  </marker>
  <radialGradient id="waterGrad" cx="50%" cy="40%" r="60%">
    <stop offset="0%"   stop-color="#1a4a6a" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="#0a1e2e" stop-opacity="1"/>
  </radialGradient>
  <pattern id="shimmer" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
    <line x1="0" y1="15" x2="60" y2="15" stroke="rgba(77,217,236,0.05)" stroke-width="1"/>
    <line x1="0" y1="35" x2="60" y2="35" stroke="rgba(77,217,236,0.05)" stroke-width="1"/>
    <line x1="0" y1="55" x2="60" y2="55" stroke="rgba(77,217,236,0.05)" stroke-width="1"/>
  </pattern>
  <filter id="glow">
    <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>"""


def render_pool_body(ly: Layout) -> str:
    """Layer 1: Pool shell, water fill, overflow channel."""
    inp  = ly.inp
    p    = PALETTE
    px   = ly.pool_x
    py   = ly.pool_y
    pw   = ly.pool_px_w
    pl   = ly.pool_px_l
    chan = ly.m2px(0.35)   # overflow channel width in px
    parts = []

    if inp.pool_type in ("overflow", "infinity"):
        # Overflow channel all around
        parts.append(rect(px - chan, py - chan,
                          pw + 2 * chan, pl + 2 * chan,
                          rx=6,
                          fill=p["overflow_ch"],
                          stroke=p["pool_edge2"],
                          stroke_width="1"))
        # Grille pattern dots on channel
        for side in range(4):
            n_dots = 8 if side % 2 == 0 else 12
            for i in range(n_dots):
                if side == 0:   # top
                    gx = px + (i + 0.5) * pw / n_dots
                    gy = py - chan / 2
                elif side == 1: # bottom
                    gx = px + (i + 0.5) * pw / n_dots
                    gy = py + pl + chan / 2
                elif side == 2: # left
                    gx = px - chan / 2
                    gy = py + (i + 0.5) * pl / n_dots
                else:           # right
                    gx = px + pw + chan / 2
                    gy = py + (i + 0.5) * pl / n_dots
                parts.append(circle(gx, gy, 1.5, fill=p["pool_edge"], opacity="0.6"))

    # Pool water body
    parts.append(rect(px, py, pw, pl, rx=4,
                      fill="url(#waterGrad)",
                      stroke=p["pool_edge"],
                      stroke_width="2"))
    # Shimmer overlay
    parts.append(rect(px, py, pw, pl, rx=4,
                      fill="url(#shimmer)", opacity="1"))

    # Infinity vanishing edge callout (right wall replaced by dashed line)
    if inp.pool_type == "infinity":
        # Replace right wall with dashed vanishing edge
        parts.append(line(px + pw, py, px + pw, py + pl,
                          stroke=p["pool_edge"],
                          stroke_width="1.5",
                          stroke_dasharray="8,4",
                          opacity="0.7"))
        # Vanishing edge arrow
        arr_y = py + pl / 2
        parts.append(f'<line x1="{round(px+pw,2)}" y1="{round(arr_y,2)}" '
                     f'x2="{round(px+pw+30,2)}" y2="{round(arr_y,2)}" '
                     f'stroke="{p["pool_edge"]}" stroke-width="1" '
                     f'marker-end="url(#flowarr)" stroke-dasharray="4,3"/>')
        parts.append(text(px + pw + 34, arr_y + 4, "∞ edge",
                          fill=p["pool_edge"], font_family=FONT_BODY, font_size="9",
                          opacity="0.8"))

    # Depth indicator (diagonal line in corner)
    parts.append(line(px + 6, py + pl - 6, px + 26, py + pl - 26,
                      stroke=p["pool_edge2"], stroke_width="0.8", opacity="0.4"))
    parts.append(text(px + 10, py + pl - 8, f"depth {inp.depth_m:.1f}m",
                      fill=p["dim_text"], font_family=FONT_BODY,
                      font_size="9", opacity="0.7"))

    return "\n".join(parts)


def render_pool_components(ly: Layout) -> str:
    """Layer 2: Drains, inlets, skimmer, lights, robot — all inside/on the pool."""
    inp  = ly.inp
    r    = ly.result
    p    = PALETTE
    px   = ly.pool_x
    py   = ly.pool_y
    pw   = ly.pool_px_w
    pl   = ly.pool_px_l
    parts = []

    # ── Main drains (pair, centred on pool floor) ──────────────────
    n_drains = len(r.main_drains)
    drain_r  = max(6, ly.m2px(0.12))
    for i in range(n_drains):
        spacing = pw * 0.18
        dx = px + pw / 2 + (i - (n_drains - 1) / 2) * spacing
        dy = py + pl * 0.78
        parts.append(circle(dx, dy, drain_r,
                            fill=p["equip_fill"],
                            stroke=p["drain"], stroke_width="1.5"))
        # Drain cross
        for angle in [0, 90]:
            rad = math.radians(angle)
            parts.append(line(dx - drain_r * 0.65 * math.cos(rad),
                              dy - drain_r * 0.65 * math.sin(rad),
                              dx + drain_r * 0.65 * math.cos(rad),
                              dy + drain_r * 0.65 * math.sin(rad),
                              stroke=p["drain"], stroke_width="0.9"))
        if i == 0:
            parts.append(text(dx, dy + drain_r + 10, "DRAIN",
                              fill=p["label_muted"], font_family=FONT_BODY,
                              font_size="7.5", text_anchor="middle"))

    # ── Return inlets (distributed on walls) ──────────────────────
    n_inlets   = len(r.return_inlets)
    inlet_size = max(5, ly.m2px(0.08))
    # Distribute: 40% on left wall, 40% on right wall, 20% on far wall
    n_lr = max(1, round(n_inlets * 0.4))
    n_far= max(0, n_inlets - 2 * n_lr)
    inlet_positions = []
    for i in range(n_lr):  # left wall
        iy = py + pl * 0.15 + (pl * 0.7) * i / max(n_lr - 1, 1)
        inlet_positions.append((px + inlet_size / 2, iy, "left"))
    for i in range(n_lr):  # right wall
        iy = py + pl * 0.15 + (pl * 0.7) * i / max(n_lr - 1, 1)
        inlet_positions.append((px + pw - inlet_size / 2, iy, "right"))
    for i in range(n_far): # far wall
        ix = px + pw * 0.3 + pw * 0.4 * i / max(n_far - 1, 1)
        inlet_positions.append((ix, py + inlet_size / 2, "top"))

    for ix, iy, side in inlet_positions[:n_inlets]:
        parts.append(rect(ix - inlet_size / 2, iy - inlet_size / 2,
                          inlet_size, inlet_size, rx=1,
                          fill=p["inlet"], opacity="0.75"))
    parts.append(text(inlet_positions[0][0] + inlet_size + 3,
                      inlet_positions[0][1] + 3,
                      f"INLET", fill=p["label_muted"],
                      font_family=FONT_BODY, font_size="7"))

    # ── Skimmer (skimmer type only, on left wall near surface) ────
    if inp.pool_type == "skimmer":
        sk_w = ly.m2px(0.28); sk_h = ly.m2px(0.22)
        sk_x = px - sk_w * 0.5
        sk_y = py + pl * 0.15
        parts.append(rect(sk_x, sk_y, sk_w, sk_h, rx=2,
                          fill=p["skimmer"], stroke=p["pool_edge"], stroke_width="1",
                          opacity="0.85"))
        parts.append(text(sk_x + sk_w / 2, sk_y + sk_h / 2 + 4,
                          "SKM", fill=p["label_text"],
                          font_family=FONT_BODY, font_size="8", text_anchor="middle"))

    # ── Underwater lights (on long walls, evenly spaced) ──────────
    n_lights = len(r.lighting)
    light_r  = max(4, ly.m2px(0.10))
    n_per_side = max(1, n_lights // 2)
    for side, wx in enumerate([px + light_r, px + pw - light_r]):
        for i in range(n_per_side):
            ly_pos = py + pl * 0.25 + (pl * 0.5) * i / max(n_per_side - 1, 1)
            # Glow effect circle
            parts.append(circle(wx, ly_pos, light_r * 2.5,
                                fill=PALETTE["light"], opacity="0.06"))
            parts.append(circle(wx, ly_pos, light_r,
                                fill=PALETTE["light"], opacity="0.75"))
    if n_lights > 0:
        lx0 = px + light_r
        ly0 = py + pl * 0.25
        parts.append(text(lx0 + light_r + 3, ly0 + 3, "LIGHT",
                          fill=p["label_muted"], font_family=FONT_BODY, font_size="7"))

    # ── Robot cleaner (inside pool, bottom-right corner) ──────────
    if r.robot_cleaner:
        rb_w = ly.m2px(0.45); rb_h = ly.m2px(0.32)
        rb_x = px + pw - rb_w - ly.m2px(0.4)
        rb_y = py + pl - rb_h - ly.m2px(0.4)
        parts.append(rect(rb_x, rb_y, rb_w, rb_h, rx=3,
                          fill=p["equip_fill"],
                          stroke=p["robot"], stroke_width="0.8"))
        # Wheels
        for wx in [rb_x + rb_w * 0.2, rb_x + rb_w * 0.8]:
            parts.append(rect(wx - 3, rb_y + rb_h - 4, 6, 5, rx=2,
                              fill=p["robot"], opacity="0.7"))
        parts.append(text(rb_x + rb_w / 2, rb_y + rb_h / 2 + 3,
                          "ROBOT", fill=p["robot"],
                          font_family=FONT_BODY, font_size="7.5",
                          text_anchor="middle"))

    return "\n".join(parts)


def render_engine_room(ly: Layout) -> str:
    """Layer 3: Engine room with equipment blocks and flow arrows."""
    r    = ly.result
    inp  = ly.inp
    p    = PALETTE
    ex   = ly.er_x
    ey   = ly.er_y
    ew   = ly.er_px_w
    eh   = ly.er_px_h
    parts = []

    # ── Engine room shell ─────────────────────────────────────────
    parts.append(rect(ex, ey, ew, eh, rx=4,
                      fill=p["engine_bg"],
                      stroke=p["engine_edge"], stroke_width="1.5"))
    # Label
    parts.append(text(ex + ew / 2, ey + 16,
                      "ENGINE ROOM",
                      fill=p["engine_edge"],
                      font_family=FONT_BODY, font_size="9",
                      text_anchor="middle", font_weight="400",
                      letter_spacing="2"))

    # ── Equipment placement grid ──────────────────────────────────
    # Grid: 2 columns × up to 5 rows, left-to-right, top-to-bottom
    # Order: Filter (large) | Pump | Manifold | Treatment | Heater |
    #        Blower | Automation | Chemical tanks | Dehumidifier (if indoor)
    pad  = 14
    col_w = (ew - 3 * pad) / 2
    row_start = ey + 28
    row_h = (eh - 28 - pad) / 5

    def block(col, row, label, sublabel, code, sym, color=None,
              rowspan=1, colspan=1):
        bx = ex + pad + col * (col_w + pad)
        by = row_start + row * row_h + pad * 0.3
        bw = col_w * colspan + pad * (colspan - 1)
        bh = row_h * rowspan - pad * 0.4
        return equip_block(bx, by, bw, bh, code, label, sublabel, color, sym)

    equip_rows = []

    # Filter — takes 2 rows on left to reflect its size
    if r.filter:
        equip_rows.append(block(0, 0, "Filter",
                                r.filter.model[:22] if len(r.filter.model) > 22 else r.filter.model,
                                r.filter.code[:14],
                                "cylinder", p["equip_edge"], rowspan=2))

    # Pump — right of filter
    if r.pump:
        equip_rows.append(block(1, 0, "Pump",
                                f"{r.pump.power_hp or '?'}HP",
                                r.pump.code[:14], "pump", p["pool_edge"]))

    # Valve manifold
    if r.valve_manifold:
        equip_rows.append(block(1, 1, "Manifold",
                                "5-valve", r.valve_manifold.code[:14],
                                "box", p["equip_edge"]))

    # Treatment
    if r.treatment:
        lbl = r.treatment.model.split()[0]
        equip_rows.append(block(0, 2, "Treatment",
                                f"×{r.n_chlorinators}" if r.n_chlorinators > 1 else lbl,
                                r.treatment.code[:14], "box", p["accent"]))

    # Heater
    if r.heater:
        equip_rows.append(block(1, 2, "Heater",
                                f"{r.heater.power_kw:.0f}kW",
                                r.heater.code[:14], "box", p["accent"]))

    # Air blower (only if present)
    if r.air_blower:
        equip_rows.append(block(0, 3, "Blower", "airscouring",
                                r.air_blower.code[:14], "box", p["equip_edge"]))

    # Automation cabinet
    if r.automation:
        equip_rows.append(block(1, 3, "Automation",
                                "Connect&amp;Go", r.automation.code[:14],
                                "box", p["equip_edge"]))

    # Chemical tanks (always present)
    equip_rows.append(block(0, 4, "Chemical", "tanks", "", "cylinder", p["equip_edge"]))

    # Dehumidifier (indoor only)
    if r.dehumidifier:
        equip_rows.append(block(1, 4, "Dehumidifier",
                                r.dehumidifier.model.split()[1] + " l/h"
                                if len(r.dehumidifier.model.split()) > 2 else "",
                                r.dehumidifier.code[:14], "box", p["equip_edge"]))

    parts.extend(equip_rows)

    # ── Flow arrows: pool → engine room ──────────────────────────
    # Suction pipe (pool bottom-left → engine room left)
    pool_suction_x = ly.pool_x + ly.pool_px_w * 0.25
    pool_suction_y = ly.pool_y + ly.pool_px_l * 0.78   # at drain level
    er_inlet_x = ex
    er_inlet_y = ey + eh * 0.65
    mid_x = (pool_suction_x + er_inlet_x) / 2

    parts.append(f'<polyline points="{round(pool_suction_x,2)},{round(pool_suction_y,2)} '
                 f'{round(pool_suction_x,2)},{round(er_inlet_y,2)} '
                 f'{round(er_inlet_x,2)},{round(er_inlet_y,2)}" '
                 f'fill="none" stroke="{p["flow_arrow"]}" stroke-width="1.5" '
                 f'stroke-dasharray="6,3" marker-end="url(#flowarr)"/>')
    parts.append(text(pool_suction_x + 4, er_inlet_y - 5,
                      "suction", fill=p["flow_arrow"],
                      font_family=FONT_BODY, font_size="8", opacity="0.7"))

    # Return pipe (engine room → pool return inlets)
    er_outlet_x = ex
    er_outlet_y = ey + eh * 0.35
    pool_ret_x  = ly.pool_x
    pool_ret_y  = ly.pool_y + ly.pool_px_l * 0.3

    parts.append(f'<polyline points="{round(er_outlet_x,2)},{round(er_outlet_y,2)} '
                 f'{round(pool_ret_x,2)},{round(er_outlet_y,2)} '
                 f'{round(pool_ret_x,2)},{round(pool_ret_y,2)}" '
                 f'fill="none" stroke="{p["return_arrow"]}" stroke-width="1.5" '
                 f'stroke-dasharray="6,3" marker-end="url(#retarr)"/>')
    parts.append(text(pool_ret_x + 4, er_outlet_y - 5,
                      "return", fill=p["return_arrow"],
                      font_family=FONT_BODY, font_size="8", opacity="0.7"))

    return "\n".join(parts)


def render_dimensions(ly: Layout) -> str:
    """Layer 4a: Dimension lines for pool and engine room."""
    inp  = ly.inp
    px   = ly.pool_x
    py   = ly.pool_y
    pw   = ly.pool_px_w
    pl   = ly.pool_px_l
    ex   = ly.er_x
    ey   = ly.er_y
    ew   = ly.er_px_w
    eh   = ly.er_px_h
    parts = []

    # Pool width (above pool)
    parts.append(dim_line(px, py - 30, px + pw, py - 30,
                          f"{inp.width_m:.1f} m", offset=14))
    # Pool length (left of pool)
    parts.append(dim_line(px - 36, py, px - 36, py + pl,
                          f"{inp.length_m:.1f} m", offset=18, vertical=True))
    # Engine room width (below engine room)
    parts.append(dim_line(ex, ey + eh + 22, ex + ew, ey + eh + 22,
                          f"{ly.er_width_m:.1f} m", offset=14))
    # Engine room depth (right of engine room)
    parts.append(dim_line(ex + ew + 22, ey, ex + ew + 22, ey + eh,
                          f"{ly.er_depth_m:.1f} m", offset=18, vertical=True))

    return "\n".join(parts)


def render_annotations(ly: Layout) -> str:
    """Layer 4b: Equipment labels outside pool, compass, scale bar."""
    p    = PALETTE
    px   = ly.pool_x
    py   = ly.pool_y
    pw   = ly.pool_px_w
    pl   = ly.pool_px_l
    parts = []

    # Pool centre label
    parts.append(text(px + pw / 2, py + pl / 2 - 14,
                      f"POOL",
                      fill=p["pool_edge"], font_family=FONT_TITLE,
                      font_size="16", text_anchor="middle",
                      opacity="0.25", font_style="italic"))
    parts.append(text(px + pw / 2, py + pl / 2 + 6,
                      f"{ly.result.volume_m3:.0f} m³",
                      fill=p["pool_edge2"], font_family=FONT_TITLE,
                      font_size="12", text_anchor="middle",
                      opacity="0.35", font_style="italic"))

    # Compass / North arrow (bottom-left of drawing)
    nx = MARGIN + 28
    ny = CANVAS_H - LEGEND_H - MARGIN - 28
    parts.append(f'<line x1="{nx}" y1="{ny+14}" x2="{nx}" y2="{ny-10}" '
                 f'stroke="{p["dim_line"]}" stroke-width="1.5" '
                 f'marker-end="url(#dimend)"/>')
    parts.append(text(nx, ny - 14, "N",
                      fill=p["dim_text"], font_family=FONT_BODY,
                      font_size="10", text_anchor="middle", font_weight="bold"))

    # Scale bar (bottom-left, beside compass)
    sb_x    = nx + 20
    sb_y    = ny + 10
    scale_m = 2.0
    sb_px   = ly.m2px(scale_m)
    parts.append(rect(sb_x, sb_y - 4, sb_px, 4,
                      fill=p["dim_line"], opacity="0.6"))
    parts.append(text(sb_x + sb_px / 2, sb_y + 9,
                      f"{scale_m:.0f} m",
                      fill=p["dim_text"], font_family=FONT_BODY,
                      font_size="9", text_anchor="middle"))
    parts.append(text(sb_x, sb_y + 9, "0",
                      fill=p["dim_text"], font_family=FONT_BODY,
                      font_size="8", text_anchor="middle"))

    return "\n".join(parts)


def render_title_block(inp: PoolInputs, result: CalculationResult) -> str:
    """Title block across the top of the canvas."""
    p   = PALETTE
    ty  = MARGIN
    th  = TITLE_H
    parts = []

    # Title bar bg
    parts.append(rect(MARGIN, ty, CANVAS_W - 2 * MARGIN, th,
                      rx=4, fill=p["engine_bg"],
                      stroke=p["pool_edge2"], stroke_width="0.8"))
    # Left accent bar
    parts.append(rect(MARGIN, ty, 4, th, fill=p["pool_edge"]))

    # Project name
    parts.append(text(MARGIN + 18, ty + 24,
                      "MyPoolViewer",
                      fill=p["pool_edge"], font_family=FONT_TITLE,
                      font_size="20", font_weight="400"))
    parts.append(text(MARGIN + 18, ty + 42,
                      "Pool Blueprint — Top View",
                      fill=p["label_muted"], font_family=FONT_BODY,
                      font_size="11"))

    # Pool specs (centre)
    specs = [
        ("Type",       inp.pool_type.title()),
        ("Dimensions", f"{inp.width_m} × {inp.length_m} × {inp.depth_m} m"),
        ("Volume",     f"{result.volume_m3:.0f} m³"),
        ("Filtration", inp.filtration.title()),
        ("Design Flow",f"{result.design_flow_m3h:.1f} m³/h"),
        ("Engine Room",f"~{result.engine_room_m2:.1f} m²"),
    ]
    cx = CANVAS_W / 2 - len(specs) * 55
    for i, (lbl, val) in enumerate(specs):
        sx = cx + i * 115
        parts.append(text(sx, ty + 28,
                          lbl.upper(),
                          fill=p["label_muted"], font_family=FONT_BODY,
                          font_size="8", charspacing="1"))
        parts.append(text(sx, ty + 48,
                          val, fill=p["label_text"],
                          font_family=FONT_BODY, font_size="12",
                          font_weight="400"))

    # BOM count (right)
    parts.append(text(CANVAS_W - MARGIN - 18, ty + 32,
                      f"{len(result.bom)}",
                      fill=p["accent"], font_family=FONT_TITLE,
                      font_size="28", text_anchor="end"))
    parts.append(text(CANVAS_W - MARGIN - 18, ty + 52,
                      "BOM items",
                      fill=p["label_muted"], font_family=FONT_BODY,
                      font_size="10", text_anchor="end"))

    return "\n".join(parts)


def render_legend(result: CalculationResult) -> str:
    """Legend strip at the bottom of the canvas."""
    p   = PALETTE
    ly  = CANVAS_H - MARGIN - LEGEND_H
    lh  = LEGEND_H
    lx  = MARGIN
    lw  = CANVAS_W - 2 * MARGIN
    parts = []

    parts.append(rect(lx, ly, lw, lh, rx=3,
                      fill=p["engine_bg"],
                      stroke=p["engine_edge"], stroke_width="0.5"))

    symbols = [
        (p["drain"],   "●", "Main Drain"),
        (p["inlet"],   "■", "Return Inlet"),
        (p["light"],   "●", "Underwater Light"),
        (p["skimmer"], "■", "Skimmer"),
        (p["pool_edge"],"─ ─", "Overflow Grille"),
        (p["flow_arrow"],"-- →", "Suction Flow"),
        (p["return_arrow"],"-- →", "Return Flow"),
        (p["robot"],   "▭", "Robot Cleaner"),
    ]
    col_w = lw / len(symbols)
    for i, (color, sym, label) in enumerate(symbols):
        sx = lx + (i + 0.5) * col_w
        parts.append(text(sx, ly + 20, sym,
                          fill=color, font_family=FONT_BODY,
                          font_size="13", text_anchor="middle"))
        parts.append(text(sx, ly + 36, label,
                          fill=p["label_muted"], font_family=FONT_BODY,
                          font_size="9", text_anchor="middle"))

    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# 5. MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def generate_svg(inp: PoolInputs, result: CalculationResult) -> str:
    """
    Generate a complete standalone SVG blueprint string.

    Parameters
    ----------
    inp    : PoolInputs     — user configuration
    result : CalculationResult — output from calculate()

    Returns
    -------
    str — complete SVG document, embeddable or saveable as .svg
    """
    ly = Layout(inp, result)

    body_parts = [
        # Canvas background
        rect(0, 0, CANVAS_W, CANVAS_H, fill=PALETTE["bg"]),
        # Drawing area background
        rect(MARGIN, MARGIN + TITLE_H,
             CANVAS_W - 2 * MARGIN,
             CANVAS_H - 2 * MARGIN - TITLE_H - LEGEND_H,
             rx=4, fill=PALETTE["paper"]),

        render_pool_body(ly),
        render_pool_components(ly),
        render_engine_room(ly),
        render_dimensions(ly),
        render_annotations(ly),
        render_title_block(inp, result),
        render_legend(result),
    ]

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{CANVAS_W}" height="{CANVAS_H}"
     viewBox="0 0 {CANVAS_W} {CANVAS_H}">
{render_defs()}
{"  ".join(f"<!-- {i} -->\n{part}" for i, part in enumerate(body_parts))}
</svg>'''

    return svg


# ══════════════════════════════════════════════════════════════════════════════
# 6. CLI — generate test blueprints for all 3 pool types
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blueprints")
    os.makedirs(out_dir, exist_ok=True)

    test_cases = [
        ("skimmer_chlorine",
         PoolInputs(4, 8, 1.4, "skimmer", "chlorine",
                    heating=True, liner_style="touch", liner_color="elegance",
                    light_color="rgb")),
        ("overflow_saltwater",
         PoolInputs(8, 16, 1.5, "overflow", "saltwater",
                    heating=True, light_color="rgbw",
                    ladder_type="overflow-1000")),
        ("infinity_magnesium_indoor",
         PoolInputs(6, 12, 1.5, "infinity", "magnesium",
                    indoor=True, heating=True,
                    liner_style="vogue", drain_color="anthracite",
                    light_color="warm-white")),
        ("competition_overflow",
         PoolInputs(12.5, 25, 2.0, "overflow", "saltwater", heating=True)),
    ]

    for filename, inp in test_cases:
        result = calculate(inp, CSV_PATH)
        svg    = generate_svg(inp, result)
        path   = os.path.join(out_dir, f"{filename}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"✓  {path}  ({len(svg)//1024}KB)")

    print(f"\nAll blueprints written to {out_dir}/")
