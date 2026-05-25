# spinediagrams

Clean architecture and system-design diagrams as SVG — designed to be authored by LLMs.

You describe the diagram as a Python dict (or JSON), the engine renders a 1600px-wide SVG with smart orthogonal arrow routing. Every connection routes through a single shared spine between rows, so arrows never cross container bodies and labels don't collide.

Built as a Claude Code [skill](https://docs.claude.com/en/docs/claude-code/skills), but the renderer is a 350-line stdlib-only Python script — drop it into any project.

## Why spinediagrams

- **Deterministic.** Same config → same SVG. No LLM in the render loop.
- **Single-spine routing.** All arrows route through one shared zone between adjacent rows. No arrows over containers; no labels piled on each other.
- **2 or 3 rows.** Default 2-row layout for source/target diagrams; opt into 3 rows (`"row": 2`) for classic 3-tier (frontend / backend / data + externals) with two spine zones.
- **Aspect-ratio aware.** Defaults to 16:9 (slide-friendly), also accepts 4:3 or a numeric ratio. Extra vertical room is spent on arrow spacing — the more connections you have, the more breathing room each label gets.
- **Zero deps.** Pure Python stdlib. No matplotlib, no graphviz, no node toolchain.
- **Preset vendor palettes.** `sf`, `gcp`, `aws`, `azure`, `stripe`, `postgres`, `kafka`, `okta`, `slack`, and more come with colors built in.

## Install (as a Claude Code skill)

Download `dist/spinediagrams.skill` and drop it into `~/.claude/skills/` (unzip it first — the file is a zip archive):

```bash
curl -L -o /tmp/spinediagrams.skill \
  https://github.com/wasulajr/spinediagrams/raw/main/dist/spinediagrams.skill
unzip /tmp/spinediagrams.skill -d ~/.claude/skills/
```

Then in any Claude Code session, ask for an architecture diagram — the skill triggers automatically on phrases like "draw a diagram", "show me how X connects to Y", "create a system diagram", "visualise the stack".

## Use directly (no Claude required)

```python
import sys
sys.path.insert(0, "skill/scripts")
from svg_engine import Diagram

config = {
    "title": "My System — Subtitle",
    "aspect": "16:9",
    "lanes": {
        "sf":  {"label": "Salesforce",  "col": 0, "colspan": 2, "row": 0},
        "gcp": {"label": "GCP Platform","col": 0, "colspan": 2, "row": 1},
    },
    "nodes": {
        "sf":  [["CRM", "operational"], ["Billing", "transitioning"]],
        "gcp": [["Cloud SQL", "new"], ["API Gateway", "new"]],
    },
    "connections": [
        ["sf",  "Billing",     "gcp", "Cloud SQL",   "Pub/Sub sync"],
        ["gcp", "API Gateway", "sf",  "CRM",         "Write-back"],
    ],
}

svg = Diagram(config).render()
open("output.svg", "w").write(svg)
```

Or via CLI:

```bash
python skill/scripts/svg_engine.py config.json output.svg
```

## Config format

See [`skill/SKILL.md`](skill/SKILL.md) for the full schema. Required fields:

- `title` — `"Main Title — Optional subtitle"` (em-dash splits the two)
- `lanes` — keyed dict of containers (each gets `col`, `colspan`, `row`, optional preset key or explicit colors)
- `nodes` — keyed dict of `[label, status]` pairs per lane
- `connections` — list of `[src_lane, src_node, dst_lane, dst_node, edge_label]`

Optional:

- `num_cols` — column count (default 6)
- `aspect` — target aspect ratio: `"16:9"` (default), `"4:3"`, or a number

## Examples

[`examples/sf-initial-setup-agent.py`](examples/sf-initial-setup-agent.py) — a real 16-connection 2-row diagram for a Salesforce metadata retrieval tool.

```bash
python examples/sf-initial-setup-agent.py
open examples/sf-initial-setup-agent.svg
```

![sf-initial-setup-agent local runtime stack](examples/sf-initial-setup-agent.svg)

[`examples/3-tier-web-app.py`](examples/3-tier-web-app.py) — a 14-connection 3-row diagram covering frontend, backend services, data stores + externals.

```bash
python examples/3-tier-web-app.py
open examples/3-tier-web-app.svg
```

![3-tier web app](examples/3-tier-web-app.svg)

## Status colors

| Status | Color | Meaning |
|---|---|---|
| `existing` | Slate | Unchanged, currently live |
| `new` | Cyan | Being built / not yet live |
| `transitioning` | Amber | Partially moved / dual-write |
| `retiring` | Red | Being decommissioned |
| `operational` | Green | Fully live on new platform |
| `readonly` | Light grey | Still present but no writes |

## Contributing

PRs welcome. The whole renderer is one file ([`skill/scripts/svg_engine.py`](skill/scripts/svg_engine.py)) — small, focused, no abstraction layers. Ideas:

- Smart label staggering to avoid label-on-vertical-drop occlusion
- More than 3 rows (generalize the 0↔1 + 1↔2 spine model to N rows)
- Margin-sidestep routing so row 0 ↔ row 2 connections can be drawn without crossing middle-row containers
- Additional vendor presets
- Pyproject + PyPI package

## License

MIT — see [LICENSE](LICENSE).
