#!/usr/bin/env python3
"""
svg_engine.py  —  Custom SVG architecture diagram renderer.

Usage (CLI):
    python svg_engine.py diagram.json output.svg

Usage (import):
    from svg_engine import Diagram
    d = Diagram(config)
    svg = d.render()

Config format (JSON or dict):
{
  "title": "My System — Subtitle",
  "lanes": {
    "key": {
      "label": "Display Name",
      "col": 0,         # 0-based column index
      "colspan": 2,     # columns to span (default 1)
      "row": 0,         # 0 = top row, 1 = bottom row
      "bg":        "#eef2ff",   # container fill
      "border":    "#6366f1",   # border + label colour
      "header_bg": "#c7d2fe"    # header band fill
    }
  },
  "nodes": {
    "key": [
      ["Node label", "status"]
    ]
  },
  "connections": [
    ["src_lane", "src_node_label", "dst_lane", "dst_node_label", "edge_label"]
  ],
  "num_cols": 6        # optional, default 6
}

Status values: existing | new | transitioning | retiring | operational | readonly

Predefined lane styles (use these keys to skip specifying colours):
  sf, bench, hubspot, zapier, gcp, stripe, qbo, docusign, saas,
  aws, azure, postgres, redis, kafka, okta, slack, twilio, ses,
  generic (neutral grey)
"""

import sys, json, re, os

# ── Canvas ────────────────────────────────────────────────────────────────────
CW   = 1600
FONT = "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# ── Layout ────────────────────────────────────────────────────────────────────
HEADER_H    = 48
MARGIN      = 12
COL_GAP     = 10
ROW_GAP     = 20
BOT_PAD     = 52
CONT_TITLE_H = 26
CONT_PAD_V  = 7
CONT_PAD_H  = 8
NODE_H      = 24
NODE_GAP    = 4
NODE_R      = 5

# ── Predefined lane colour palettes ──────────────────────────────────────────
LANE_PRESETS = {
    # Salesforce ecosystem
    "sf"      : ("#eef2ff", "#6366f1", "#c7d2fe"),
    "bench"   : ("#f0fdf4", "#16a34a", "#bbf7d0"),
    "hubspot" : ("#fff7ed", "#ea580c", "#fed7aa"),
    "zapier"  : ("#fdf4ff", "#a855f7", "#e9d5ff"),
    # Cloud / infra
    "gcp"     : ("#f0f9ff", "#0284c7", "#bae6fd"),
    "aws"     : ("#fff8f0", "#d97706", "#fde68a"),
    "azure"   : ("#eff6ff", "#2563eb", "#bfdbfe"),
    # Payments / finance
    "stripe"  : ("#fdf2f8", "#db2777", "#fbcfe8"),
    "qbo"     : ("#fefce8", "#ca8a04", "#fef08a"),
    # Data stores
    "postgres": ("#f0f9ff", "#0369a1", "#e0f2fe"),
    "redis"   : ("#fff1f2", "#be123c", "#fecdd3"),
    "kafka"   : ("#fdf4ff", "#7e22ce", "#f3e8ff"),
    # Comms / auth
    "okta"    : ("#fffbeb", "#b45309", "#fde68a"),
    "slack"   : ("#f5f3ff", "#7c3aed", "#ede9fe"),
    "twilio"  : ("#fff1f2", "#e11d48", "#fecdd3"),
    "ses"     : ("#fff7ed", "#c2410c", "#fed7aa"),
    # Misc SaaS
    "docusign": ("#f8fafc", "#475569", "#e2e8f0"),
    "saas"    : ("#f9fafb", "#374151", "#e5e7eb"),
    # Fallback
    "generic" : ("#f8fafc", "#64748b", "#e2e8f0"),
}

STATUS_COLOR = {
    "existing"     : ("#475569", "#ffffff"),
    "new"          : ("#0891B2", "#ffffff"),
    "transitioning": ("#B45309", "#ffffff"),
    "retiring"     : ("#DC2626", "#ffffff"),
    "operational"  : ("#15803D", "#ffffff"),
    "readonly"     : ("#94A3B8", "#1e293b"),
}

EDGE_PALETTE = [
    "#1d4ed8", "#7c3aed", "#0f766e", "#b45309",
    "#9f1239", "#0369a1", "#6d28d9", "#0e7490",
    "#92400e", "#065f46", "#1e3a5f", "#4a044e",
]

LEGEND_ENTRIES = [
    ("existing",      "Existing"),
    ("new",           "New"),
    ("transitioning", "Transitioning"),
    ("retiring",      "Retiring"),
    ("operational",   "Operational"),
    ("readonly",      "Read-Only"),
]


def _esc(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _col_bounds(col, colspan, num_cols, margin, col_gap):
    avail = CW - 2 * margin - (num_cols - 1) * col_gap
    col_w = avail // num_cols
    x = margin + col * (col_w + col_gap)
    w = colspan * col_w + (colspan - 1) * col_gap
    return x, w, col_w


def _cont_height(n):
    return CONT_TITLE_H + CONT_PAD_V + n * (NODE_H + NODE_GAP) - NODE_GAP + CONT_PAD_V


def _parse_aspect(val):
    """Parse aspect ratio. Accepts '16:9', '4:3', a number, or None."""
    if val is None:
        return 16 / 9
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if ":" in s:
            w, h = s.split(":", 1)
            return float(w) / float(h)
        return float(s)
    return 16 / 9


# Minimum vertical spacing between spine lines so 14px label pills don't kiss.
SPINE_LINE_MIN = 22


# ── Main class ────────────────────────────────────────────────────────────────

class Diagram:
    def __init__(self, config):
        if isinstance(config, str):
            config = json.loads(config)

        self.title    = config.get("title", "Architecture Diagram")
        self.num_cols = int(config.get("num_cols", 6))
        self.target_aspect = _parse_aspect(config.get("aspect", "16:9"))
        lanes_cfg     = config.get("lanes", {})
        nodes_cfg     = config.get("nodes", {})
        self.raw_conns = config.get("connections", [])

        self.conts = {}
        for key, lane in lanes_cfg.items():
            col      = int(lane.get("col", 0))
            colspan  = int(lane.get("colspan", 1))
            row      = int(lane.get("row", 0))
            nodes    = nodes_cfg.get(key, [])
            x, w, _  = _col_bounds(col, colspan, self.num_cols, MARGIN, COL_GAP)

            # Resolve colours: explicit > preset lookup > generic
            preset = LANE_PRESETS.get(key, LANE_PRESETS["generic"])
            bg         = lane.get("bg",        preset[0])
            border     = lane.get("border",    preset[1])
            header_bg  = lane.get("header_bg", preset[2])

            self.conts[key] = {
                "key": key,
                "label": lane.get("label", key),
                "col": col, "colspan": colspan, "row": row,
                "x": x, "w": w,
                "h": _cont_height(len(nodes)),
                "bg": bg, "border": border, "header_bg": header_bg,
                "nodes": [{"label": n[0], "status": n[1]} for n in nodes],
            }

        self._compute_y()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _compute_y(self):
        row_h = {0: 0, 1: 0}
        for c in self.conts.values():
            row_h[c["row"]] = max(row_h[c["row"]], c["h"])

        # One spine line per raw connection (slot index = raw_conns index, so
        # unroutable connections leave a gap rather than shift later lines).
        n_conn = len(self.raw_conns)

        # Baseline spine: enough room for SPINE_LINE_MIN spacing per line,
        # plus a 16px buffer (8px clear above first / below last line).
        base_spine = max(ROW_GAP, 16 + max(0, n_conn - 1) * SPINE_LINE_MIN)
        self.row_gap = base_spine

        baseline_h = HEADER_H + 6 + row_h[0] + self.row_gap + row_h.get(1, 0) + BOT_PAD

        # Pad canvas toward target aspect by growing the spine — extra
        # vertical room translates directly into more space between arrow
        # labels, which is the actual readability win.
        target_h = int(CW / self.target_aspect)
        if baseline_h < target_h:
            self.row_gap += target_h - baseline_h

        self.row0_y   = HEADER_H + 6
        self.row1_y   = self.row0_y + row_h[0] + self.row_gap
        self.row0_bot = self.row0_y + row_h[0]
        self.row1_bot = self.row1_y + row_h.get(1, 0)
        self.canvas_h = self.row1_bot + BOT_PAD

        # Pre-compute the y position of every spine line, evenly distributed
        # across the available spine span. Single-line case sits centered.
        spine_top = self.row0_bot + 8
        spine_bot = self.row1_y - 8
        if n_conn <= 1:
            self.spine_lines = [(spine_top + spine_bot) // 2]
        else:
            span = spine_bot - spine_top
            step = span / (n_conn - 1)
            self.spine_lines = [int(spine_top + i * step) for i in range(n_conn)]
        # Legacy field still referenced elsewhere (centered fallback).
        self.spine_y = (spine_top + spine_bot) // 2

        for c in self.conts.values():
            c["y"] = self.row0_y if c["row"] == 0 else self.row1_y

    # ── Geometry helpers ─────────────────────────────────────────────────────

    def _node_rect(self, c, idx):
        nx = c["x"] + CONT_PAD_H
        nw = c["w"] - 2 * CONT_PAD_H
        ny = c["y"] + CONT_TITLE_H + CONT_PAD_V + idx * (NODE_H + NODE_GAP)
        return nx, ny, nw, NODE_H

    def _find_node(self, lane_key, label):
        c = self.conts.get(lane_key)
        if c is None:
            return None, -1
        for i, n in enumerate(c["nodes"]):
            if n["label"] == label:
                return c, i
        return c, -1

    # ── Routing ──────────────────────────────────────────────────────────────
    #
    # Every connection — same-row or cross-row — routes through the spine
    # zone between the two rows. The spine zone has no container bodies, so
    # the horizontal cross segment never overlaps anything. Each line gets
    # its own y within the spine via `offset = idx * 6`; the gap is sized
    # in _compute_y to fit all lines without clipping.
    #
    # Vertical drops always exit/enter the nearest edge of the container
    # facing the spine (bottom for row 0, top for row 1), so they're never
    # longer than ~half the row gap and never cross any container body.

    def _route(self, src_lane, src_label, dst_lane, dst_label, idx):
        src_c, si = self._find_node(src_lane, src_label)
        dst_c, di = self._find_node(dst_lane, dst_label)
        if src_c is None or dst_c is None:
            return None

        def anchor_x(c, i):
            if i >= 0:
                nx, _, nw, _ = self._node_rect(c, i)
                return nx + nw // 2
            return c["x"] + c["w"] // 2

        def spine_edge(c):
            # y coord of the container edge facing the spine.
            return c["y"] + c["h"] if c["row"] == 0 else c["y"]

        sx = anchor_x(src_c, si)
        dx = anchor_x(dst_c, di)
        # Each routable connection gets a dedicated, pre-computed spine line.
        spine = self.spine_lines[idx] if idx < len(self.spine_lines) else self.spine_y

        return [(sx, spine_edge(src_c)),
                (sx, spine), (dx, spine),
                (dx, spine_edge(dst_c))]

    # ── SVG render ───────────────────────────────────────────────────────────

    def render(self):
        h = int(self.canvas_h)
        o = []

        o.append(f'<svg viewBox="0 0 {CW} {h}" xmlns="http://www.w3.org/2000/svg" '
                 f'style="font-family:{FONT}; background:#ffffff;">')
        o.append("""  <defs>
    <marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="#64748b"/>
    </marker>
  </defs>""")

        # Header
        o.append(f'  <rect x="0" y="0" width="{CW}" height="{HEADER_H}" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
        parts = self.title.split(" — ", 1)
        o.append(f'  <text x="{CW//2}" y="18" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">{_esc(parts[0])}</text>')
        if len(parts) > 1:
            o.append(f'  <text x="{CW//2}" y="36" text-anchor="middle" font-size="12" fill="#64748b">{_esc(parts[1])}</text>')

        # Containers
        for key, c in self.conts.items():
            x, y, w, ch = c["x"], c["y"], c["w"], c["h"]
            r = 8
            o.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{ch}" rx="{r}" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
            cid = f"clip_{key}"
            o.append(f'  <clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{CONT_TITLE_H}" rx="{r}"/></clipPath>')
            o.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{CONT_TITLE_H}" fill="{c["header_bg"]}" clip-path="url(#{cid})"/>')
            o.append(f'  <line x1="{x}" y1="{y+CONT_TITLE_H}" x2="{x+w}" y2="{y+CONT_TITLE_H}" stroke="{c["border"]}" stroke-width="0.8" opacity="0.5"/>')
            o.append(f'  <text x="{x+w//2}" y="{y+CONT_TITLE_H-7}" text-anchor="middle" font-size="12" font-weight="600" fill="{c["border"]}">{_esc(c["label"])}</text>')

            for i, node in enumerate(c["nodes"]):
                nx, ny, nw, nh = self._node_rect(c, i)
                fill, fc = STATUS_COLOR.get(node["status"], ("#64748b", "#fff"))
                o.append(f'  <rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="{NODE_R}" fill="{fill}"/>')
                o.append(f'  <text x="{nx+nw//2}" y="{ny+nh//2+4}" text-anchor="middle" font-size="11" font-weight="500" fill="{fc}">{_esc(node["label"])}</text>')

        # Edges — all routed through the single spine; idx orders the stack.
        for idx, conn in enumerate(self.raw_conns):
            sl, src_lbl, dl, dst_lbl, elbl = conn[0], conn[1], conn[2], conn[3], conn[4] if len(conn) > 4 else ""
            pts = self._route(sl, src_lbl, dl, dst_lbl, idx)
            if not pts:
                continue
            color = EDGE_PALETTE[idx % len(EDGE_PALETTE)]
            d = "M " + " L ".join(f"{int(p[0])} {int(p[1])}" for p in pts)
            o.append(f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" stroke-dasharray="5,3" marker-end="url(#arr)" opacity="0.85"/>')
            if elbl and len(pts) >= 3:
                mx = (pts[1][0] + pts[2][0]) / 2
                my = (pts[1][1] + pts[2][1]) / 2
                lw = max(60, len(elbl) * 6 + 10)
                o.append(f'  <rect x="{int(mx-lw/2)}" y="{int(my-8)}" width="{lw}" height="14" rx="3" fill="white" opacity="0.92"/>')
                o.append(f'  <text x="{int(mx)}" y="{int(my+3)}" text-anchor="middle" font-size="9" fill="{color}" font-weight="600">{_esc(elbl)}</text>')

        # Legend
        lx, ly = MARGIN, h - 36
        bw = (CW - 2 * MARGIN) // len(LEGEND_ENTRIES)
        o.append(f'  <rect x="{lx-4}" y="{ly-14}" width="{CW-2*MARGIN+8}" height="32" rx="4" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
        for i, (status, lbl) in enumerate(LEGEND_ENTRIES):
            fill, _ = STATUS_COLOR[status]
            ex = lx + i * bw
            o.append(f'  <rect x="{ex}" y="{ly-6}" width="13" height="13" rx="3" fill="{fill}"/>')
            o.append(f'  <text x="{ex+17}" y="{ly+5}" font-size="11" fill="#374151">{lbl}</text>')

        o.append('</svg>')
        return "\n".join(o)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python svg_engine.py <config.json> <output.svg>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        cfg = json.load(f)
    d = Diagram(cfg)
    svg = d.render()
    with open(sys.argv[2], "w") as f:
        f.write(svg)
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    if m:
        print(f"Written: {sys.argv[2]}  ({m.group(1)}x{m.group(2)})")
