---
name: spinediagrams
description: >
  Generate clean architecture and system-design diagrams as SVG files.
  Use this skill whenever the user wants to visualise how services, systems,
  or components connect — migration diagrams, current-state vs target-state
  architectures, integration maps, data-flow diagrams, platform overviews,
  or any diagram that shows technology boxes with arrows between them.
  Triggers on phrases like: "draw a diagram", "make an architecture diagram",
  "show me how X connects to Y", "create a system diagram", "architecture SVG",
  "visualise the stack", "diagram this", or whenever the conversation has
  produced a list of components and integrations that would benefit from a
  visual. Always use this skill rather than trying to write SVG by hand.
---

# Architecture Diagram SVG Skill

Produces fixed-width (1600 px) SVG architecture diagrams with:
- A title / subtitle header band at the top
- A **6-column grid** with **up to 3 rows** of technology containers (each
  container holds colour-coded component nodes)
- **Orthogonal single-spine edge routing** — all connection lines travel
  through the spine zone(s) between adjacent rows so they never pass
  through container bodies
- A status-colour legend at the bottom

## Workflow

1. **Understand the diagram** — identify the technology containers (lanes),
   the components inside each, and the connections between them.
2. **Build the config dict** (see format below).
3. **Run the engine** and save the SVG.
4. **Present the file** to the user.

## Engine location

```
<skill_dir>/scripts/svg_engine.py
```

Import or call it directly:

```python
# Option A — import
import sys
sys.path.insert(0, "<skill_dir>/scripts")
from svg_engine import Diagram

d = Diagram(config)          # config is a dict (see format below)
svg = d.render()
with open("output.svg", "w") as f:
    f.write(svg)

# Option B — CLI (config must be written to a JSON file first)
# python <skill_dir>/scripts/svg_engine.py config.json output.svg
```

## Config format

```python
config = {
    "title": "Main Title — Optional subtitle",   # "—" splits title/subtitle
    "num_cols": 6,    # optional, default 6; increase for more lanes per row
    "aspect": "16:9", # optional, default "16:9". Also accepts "4:3" or a
                      # numeric width/height ratio. Canvas pads to this
                      # ratio by growing the spine, which spaces arrow
                      # labels further apart.

    # ── Lanes (containers) ──────────────────────────────────────────────────
    # Each key becomes the lane identifier used in nodes/connections.
    # For well-known vendors, just use the preset key (no colours needed).
    # For custom lanes, supply bg / border / header_bg.
    "lanes": {
        "sf": {                      # preset key → colours auto-filled
            "label": "Salesforce",
            "col": 0, "colspan": 2, "row": 0
        },
        "gcp": {
            "label": "GCP Platform",
            "col": 0, "colspan": 2, "row": 1
        },
        "custom": {                  # custom lane → supply colours
            "label": "My Service",
            "col": 2, "colspan": 1, "row": 0,
            "bg": "#f0fdf4", "border": "#16a34a", "header_bg": "#bbf7d0"
        }
    },

    # ── Nodes ───────────────────────────────────────────────────────────────
    # Each list entry: ["Node label", "status"]
    # Status values: existing | new | transitioning | retiring | operational | readonly
    "nodes": {
        "sf":  [["CRM", "existing"], ["Billing", "transitioning"]],
        "gcp": [["Cloud SQL", "new"], ["API Gateway", "new"]],
        "custom": [["Auth Service", "new"]]
    },

    # ── Connections ─────────────────────────────────────────────────────────
    # Each entry: [src_lane, src_node_label, dst_lane, dst_node_label, edge_label]
    # src/dst_node_label must exactly match a node label in that lane.
    # Edge label is shown inline on the routing line.
    "connections": [
        ["sf",  "Billing",  "gcp", "Cloud SQL",   "Pub/Sub sync"],
        ["gcp", "API Gateway", "sf", "CRM",        "Write-back"]
    ]
}
```

## Grid layout rules

The diagram has up to **3 rows** and up to `num_cols` columns (default 6).

Assign each lane a `col` (0-based), `colspan`, and `row` (`0` = top, `1` = middle,
`2` = bottom). Lane widths in a row must not overlap: `col + colspan` for each
lane must stay within `num_cols`. Row 2 is optional — omit it for a classic
2-row diagram.

**Suggested 2-row layout:**

| Row | Col 0-1 (span 2) | Col 2 | Col 3 | Col 4 | Col 5 |
|-----|-----------------|-------|-------|-------|-------|
| 0   | Large source (e.g. SF) | Mid-tier A | Mid-tier B | Mid-tier C | — |
| 1   | Large target (e.g. GCP) | Ext A | Ext B | Ext C | Ext D |

**3-row layout — classic 3-tier (frontend / backend / data + externals):**

| Row | Use it for |
|-----|------------|
| 0   | User-facing surfaces (browser, mobile, public APIs) |
| 1   | Backend services / orchestration / business logic |
| 2   | Data stores + external SaaS dependencies |

### Routing rules (important for 3-row diagrams)

Connections route through one of two spines:
- **Spine 0↔1** (between rows 0 and 1) carries: row 0↔0, row 0↔1, row 1↔1.
- **Spine 1↔2** (between rows 1 and 2) carries: row 1↔2, row 2↔2.

**Forbidden:** connections that span row 0 ↔ row 2 directly. They'd have to
cross row 1 container bodies, which defeats the no-overlap guarantee. The
engine raises `ValueError` listing the offending edges. Route through a row 1
container instead (recommended — usually models reality better), or split into
two diagrams.

## Preset lane keys (colours auto-applied)

| Key        | Label default      | Colour theme  |
|------------|--------------------|---------------|
| `sf`       | Salesforce         | Indigo        |
| `bench`    | Bench App          | Green         |
| `hubspot`  | HubSpot            | Orange        |
| `zapier`   | Zapier             | Purple        |
| `gcp`      | GCP Platform       | Sky blue      |
| `aws`      | AWS                | Amber         |
| `azure`    | Azure              | Blue          |
| `stripe`   | Stripe             | Pink          |
| `qbo`      | QuickBooks Online  | Yellow        |
| `postgres` | PostgreSQL         | Steel blue    |
| `redis`    | Redis              | Red           |
| `kafka`    | Kafka              | Deep purple   |
| `okta`     | Okta               | Amber         |
| `slack`    | Slack              | Violet        |
| `twilio`   | Twilio             | Rose          |
| `ses`      | Amazon SES         | Deep orange   |
| `docusign` | DocuSign           | Slate         |
| `saas`     | Third-Party SaaS   | Cool grey     |
| `generic`  | (any)              | Neutral grey  |

For any key not in this list, supply explicit `bg` / `border` / `header_bg`.

## Status colour guide

| Status        | Meaning                              | Colour  |
|---------------|--------------------------------------|---------|
| `existing`    | Unchanged, currently live            | Slate   |
| `new`         | Being built / not yet live           | Cyan    |
| `transitioning` | Partially moved / dual-write       | Amber   |
| `retiring`    | Being decommissioned                 | Red     |
| `operational` | Fully live on new platform           | Green   |
| `readonly`    | Still present but no writes          | Light grey |

## Tips

- Keep edge labels short (3-5 words) — they render at 9 px inside a white pill.
- Connections with no meaningful label can pass an empty string `""`.
- If you need more than 6 columns, set `"num_cols": 8` (or higher) — column
  widths shrink proportionally.
- The engine handles the routing automatically; you only need to specify
  which node connects to which.
- Save the final SVG to the user's workspace folder, then present it with
  `mcp__cowork__present_files` (Cowork) or tell the user the file path (Claude Code).
