"""
Icon library smoke test — renders one node per icon category.
Open the SVG in a browser (not Preview.app) to see hover tooltips.
"""
import sys, re
sys.path.insert(0, "../skill/scripts")
from svg_engine import Diagram

config = {
    "title": "spinediagrams Icon Library — v0.9 Smoke Test  ·  212 icons",
    "num_cols": 6,
    "aspect": "16:9",
    "edge_color": "#94a3b8",
    "edge_dashed": True,
    "legend": False,

    "lanes": {
        "languages": {
            "label": "Languages",
            "col": 0, "colspan": 2, "row": 0,
            "bg": "#fff", "border": "#7c3aed", "header_bg": "#ede9fe",
        },
        "frameworks": {
            "label": "Frameworks & Runtimes",
            "col": 2, "colspan": 2, "row": 0,
            "bg": "#fff", "border": "#0369a1", "header_bg": "#e0f2fe",
        },
        "databases": {
            "label": "Databases & Storage",
            "col": 4, "colspan": 2, "row": 0,
            "bg": "#fff", "border": "#15803d", "header_bg": "#dcfce7",
        },
        "cloud": {
            "label": "Cloud & Infra",
            "col": 0, "colspan": 2, "row": 1,
            "bg": "#fff", "border": "#b45309", "header_bg": "#fef3c7",
        },
        "devops": {
            "label": "DevOps & CI/CD",
            "col": 2, "colspan": 2, "row": 1,
            "bg": "#fff", "border": "#0f766e", "header_bg": "#ccfbf1",
        },
        "saas": {
            "label": "SaaS & Tooling",
            "col": 4, "colspan": 2, "row": 1,
            "bg": "#fff", "border": "#9f1239", "header_bg": "#fce7f3",
        },
    },

    "nodes": {
        "languages": [
            ["TypeScript",  "existing"],
            ["Go",          "existing"],
            ["Rust",        "existing"],
            ["PHP",         "existing"],
            ["Ruby",        "existing"],
            ["Kotlin",      "existing"],
            ["Swift",       "existing"],
            ["C#",          "existing"],
            ["C++",         "existing"],
            ["Scala",       "existing"],
            ["Elixir",      "existing"],
            ["Dart",        "existing"],
        ],
        "frameworks": [
            ["React",           "existing"],
            ["Angular",         "existing"],
            ["Vue.js",          "existing"],
            ["Next.js",         "existing"],
            ["Nuxt.js",         "existing"],
            ["Svelte",          "existing"],
            ["Django",          "existing"],
            ["FastAPI",         "existing"],
            ["Laravel",         "existing"],
            ["Ruby on Rails",   "existing"],
            ["NestJS",          "existing"],
            ["Node.js",         "existing"],
        ],
        "databases": [
            ["PostgreSQL",      "existing"],
            ["MongoDB",         "existing"],
            ["MySQL",           "existing"],
            ["SQLite",          "existing"],
            ["Neo4j",           "existing"],
            ["Apache Cassandra","existing"],
            ["InfluxDB",        "existing"],
            ["Supabase",        "existing"],
            ["ClickHouse",      "existing"],
            ["Snowflake",       "existing"],
            ["Redis",           "existing"],
            ["Elasticsearch",   "existing"],
        ],
        "cloud": [
            ["Docker",          "existing"],
            ["Kubernetes",      "existing"],
            ["Microsoft Azure", "existing"],
            ["Google Cloud",    "existing"],
            ["Heroku",          "existing"],
            ["Vercel",          "existing"],
            ["Netlify",         "existing"],
            ["Cloudflare",      "existing"],
            ["Terraform",       "existing"],
            ["Ansible",         "existing"],
            ["Pulumi",          "existing"],
            ["Helm",            "existing"],
        ],
        "devops": [
            ["Jenkins",         "existing"],
            ["CircleCI",        "existing"],
            ["GitHub Actions",  "existing"],
            ["ArgoCD",          "existing"],
            ["Grafana",         "existing"],
            ["Prometheus",      "existing"],
            ["Datadog",         "existing"],
            ["New Relic",       "existing"],
            ["Sentry",          "existing"],
            ["Playwright",      "existing"],
            ["SonarQube",       "existing"],
            ["VS Code",         "existing"],
        ],
        "saas": [
            ["Stripe",          "existing"],
            ["Salesforce",      "existing"],
            ["Figma",           "existing"],
            ["GitHub",          "existing"],
            ["GitLab",          "existing"],
            ["Jira",            "existing"],
            ["Notion",          "existing"],
            ["Slack",           "existing"],
            ["Discord",         "existing"],
            ["Microsoft Teams", "existing"],
            ["WebAssembly",     "existing"],
            ["GraphQL",         "existing"],
        ],
    },

    "connections": [],
}

d = Diagram(config)
svg = d.render()
out = "icon_smoke_test.svg"
with open(out, "w") as f:
    f.write(svg)
m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
print(f"Written: {out}  ({m.group(1)}x{m.group(2)} px)" if m else f"Written: {out}")
print("Open in a browser (not Preview.app) for hover tooltips on each icon.")
