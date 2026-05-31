#!/usr/bin/env python3
"""
svg_engine.py  —  Custom SVG architecture diagram renderer.

Usage (CLI):
    python svg_engine.py diagram.json output.svg

Usage (import):
    from svg_engine import Diagram
    d = Diagram(config)
    svg = d.render()

Node format:
  ["label", "status"]
  ["label", "status", "category"]
  ["label", "status", "category", True]          # primary (bold + border ring)
  ["label", "status", "category", True, "icon"]  # explicit icon key override

Connection format:
  ["src_lane", "src_node", "dst_lane", "dst_node", "label"]
  ["src_lane", "src_node", "dst_lane", "dst_node", "label", True]  # bidirectional

Category format:
  "categories": {
    "script": {"color": "#6366f1", "mark": "dot", "label": "Script / Code"}
  }
  mark = "dot" | "stripe"  (default "dot")

Tech icons are auto-detected from node label extensions/keywords.
Pass show_icons=false in config to disable. Add an explicit 5th node element
(icon key string) to override auto-detection for a specific node.

Status values: existing | new | transitioning | retiring | operational | readonly
"""

import sys, json, re, os, urllib.request, urllib.error
from collections import defaultdict

ICON_CACHE_DIR = os.path.expanduser("~/.cache/spinediagrams")

CW   = 1600
FONT = "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

HEADER_H        = 48
MARGIN          = 12
COL_GAP         = 10
ROW_GAP         = 20
CONT_TITLE_H    = 26   # no icons
CONT_TITLE_H_ICO= 40   # with icon strip
CONT_PAD_V      = 7
CONT_PAD_H      = 8
NODE_H          = 24
NODE_GAP        = 4
NODE_R          = 5
NODE_ICON_SIZE  = 16   # px — icon inside each node row
HDR_ICON_SIZE   = 13   # px — icon in lane header strip

MARK_SIZE_DEFAULTS = {"dot": 4, "stripe": 3}
SPINE_LINE_MIN     = 22
SIDESTEP_CHANNEL_STEP = 6
SIDESTEP_EDGE_PAD     = 6

# ── Tech icon library ─────────────────────────────────────────────────────────
# SVG path data from Simple Icons (simpleicons.org), viewBox 0 0 24 24.
# fill   = brand colour applied to the path.
# rule   = SVG fill-rule; "evenodd" is needed for logos with cutout letters.
# type   = "path" (default) | "text" for lightweight text-badge fallback.

TECH_ICONS = {
    "python": {
        "name": "Python",
        "path": ("M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63"
                 "-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69"
                 ".05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3"
                 ".17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88"
                 "-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.3"
                 "6-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28"
                 ".25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 "
                 "1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23"
                 "-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59."
                 "28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42"
                 ".24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-"
                 ".17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04"
                 "-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2."
                 "01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-"
                 ".04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35"
                 ".07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.2"
                 "3.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z"),
        "fill": "#3776AB",
    },
    "javascript": {
        "name": "JavaScript",
        "path": ("M0 0h24v24H0V0zm22.034 18.276c-.175-1.095-.888-2.015-3.003-2.873-.736-.345-1.554-.5"
                 "85-1.797-1.14-.091-.33-.105-.51-.046-.705.15-.646.915-.84 1.515-.66.39.12.75.42.976."
                 "9 1.034-.676 1.034-.676 1.755-1.125-.27-.42-.404-.601-.586-.78-.63-.705-1.469-1.065-"
                 "2.834-1.034l-.705.089c-.676.165-1.32.525-1.71 1.005-1.14 1.291-.811 3.541.569 4.471"
                 " 1.365 1.02 3.361 1.244 3.616 2.205.24 1.17-.87 1.545-1.966 1.41-.811-.18-1.26-.586"
                 "-1.755-1.336l-1.83 1.051c.21.48.45.689.81 1.109 1.74 1.756 6.09 1.666 6.871-1.004.0"
                 "29-.09.24-.705.074-1.65l.046.067zm-8.983-7.245h-2.248c0 1.938-.009 3.864-.009 5.805 "
                 "0 1.232.063 2.363-.138 2.711-.33.689-1.18.601-1.566.48-.396-.196-.597-.466-.83-.855-"
                 ".063-.105-.11-.196-.127-.196l-1.825 1.125c.305.63.75 1.172 1.324 1.517.855.51 2.004."
                 "675 3.207.405.783-.226 1.458-.691 1.811-1.411.51-.93.402-2.07.397-3.346.012-2.054 0-"
                 "4.109 0-6.179l.004-.056z"),
        "fill": "#F7DF1E",
        "rule": "evenodd",
    },
    "gnubash": {
        "name": "GNU Bash",
        "path": ("M21.038 4.9l-7.577-4.498C13.009.134 12.505 0 12 0c-.505 0-1.009.134-1.462.403L2.961"
                 " 4.9C2.057 5.437 1.5 6.429 1.5 7.503v8.995c0 1.073.557 2.066 1.462 2.603l7.577 4.49"
                 "7C10.991 23.866 11.495 24 12 24c.505 0 1.009-.134 1.461-.402l7.577-4.497c.904-.537 1"
                 ".462-1.529 1.462-2.603V7.503C22.5 6.429 21.943 5.437 21.038 4.9zM20.459 6.797l-7.168"
                 " 4.427c-.894.523-1.553 1.109-1.553 2.187v8.833c0 .645.26 1.063.66 1.184a5.55 5.55 0 "
                 "01-.398.039c-.42 0-.833-.114-1.197-.33L3.226 18.64c-.741-.44-1.201-1.261-1.201-2.142"
                 "V7.503c0-.881.46-1.702 1.201-2.142l7.577-4.498c.363-.216.777-.33 1.197-.33.419 0 .83"
                 "3.114 1.197.33l7.577 4.498c.624.371 1.046 1.013 1.164 1.732-.254-.536-.82-.682-1.479"
                 "-.296zm-5.289 11.997l.013.646c.001.078-.05.167-.111.198l-.383.22c-.061.031-.111-.007"
                 "-.112-.085l-.007-.635c-.328.136-.66.169-.872.084-.04-.016-.057-.075-.041-.142l.139-.5"
                 "84c.016-.066.065-.138.105-.147.022-.011.043-.014.062-.006.229.077.521.041.802-.101.3"
                 "57-.181.596-.545.592-.907-.003-.328-.181-.465-.613-.468-.55.001-1.064-.107-1.072-.917"
                 "-.007-.667.34-1.361.889-1.8l-.007-.652c-.001-.08.048-.168.111-.2l.37-.236c.061-.031."
                 "111.007.112.087l.006.653c.273-.109.511-.138.726-.088.047.012.067.076.048.151l-.144.5"
                 "78c-.016.065-.065.137-.103.144-.019.01-.038.013-.057.009-.098-.022-.332-.073-.699.113"
                 "-.385.195-.52.53-.517.778.003.297.155.387.681.396.7.012 1.003.318 1.01 1.023.008.708"
                 "-.361 1.452-.927 1.907zm3.973-1.087c0 .06-.008.116-.058.145l-1.916 1.164c-.05.029-.0"
                 "9.004-.09-.056v-.494c0-.06.037-.093.087-.122l1.887-1.129c.05-.029.09-.004.09.056v.49"
                 "6z"),
        "fill": "#4EAA25",
    },
    "npm": {
        "name": "npm",
        "path": ("M1.763 0C.786 0 0 .786 0 1.763v20.474C0 23.214.786 24 1.763 24h20.474c.977 0 1.763-"
                 ".786 1.763-1.763V1.763C24 .786 23.214 0 22.237 0zM5.13 5.323l13.837.019-.009 13.836h"
                 "-3.464l.01-10.382h-3.456L12.04 19.17H5.113z"),
        "fill": "#CB3837",
    },
    "gmail": {
        "name": "Gmail / IMAP",
        "path": ("M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9."
                 "273H1.636A1.636 1.636 0 010 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 "
                 "12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"),
        "fill": "#EA4335",
    },
    "apple": {
        "name": "macOS",
        "path": ("M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 "
                 "3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987"
                 " 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688"
                 " 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.59"
                 "7-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c."
                 "843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-"
                 "1.273 3.714 1.338.104 2.715-.688 3.559-1.701"),
        "fill": "#555555",
    },
    "markdown": {
        "name": "Markdown",
        "path": ("M22.27 19.385H1.73A1.73 1.73 0 010 17.655V6.345a1.73 1.73 0 011.73-1.73h20.54A1.73 "
                 "1.73 0 0124 6.345v11.308a1.73 1.73 0 01-1.73 1.731zM5.769 15.923v-4.5l2.308 2.885 2"
                 ".307-2.885v4.5h2.308V8.078h-2.308l-2.307 2.885-2.308-2.885H3.46v7.847zM21.232 12h-2"
                 ".309V8.077h-2.307V12h-2.308l3.461 4.039z"),
        "fill": "#ffffff",
        "bg":   "#083F54",   # dark background behind the Markdown badge
        "rule": "nonzero",
    },
    "linkedin": {
        "name": "LinkedIn",
        "path": ("M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.1"
                 "36 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 "
                 "2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.06"
                 "3 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13"
                 ".019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 "
                 "24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"),
        "fill": "#0A66C2",
    },
    "json": {
        "name": "JSON",
        "type": "text",
        "chars": "{}",
        "fill": "#92400e",   # dark amber — matches the data category colour
    },
    "anthropic": {
        "name": "Anthropic / Claude",
        "path": "M17.3041 3.541h-3.6718l6.696 16.918H24Zm-10.6082 0L0 20.459h3.7442l1.3693-3.5527h7.0052l1.3693 3.5528h3.7442L10.5363 3.5409Zm-.3712 10.2232 2.2914-5.9456 2.2914 5.9456Z",
        "fill": "#d97706",   # amber to match brand-adjacent warmth
    },
}

# Auto-detect icon key from node label. Returns None if no match.
# Order matters: more specific checks (full extension) run before keyword checks.
def _detect_icon(label):
    l = label.lower()
    if l.endswith(".py"):                          return "python"
    if l.endswith(".sh"):                          return "gnubash"
    if l.endswith(".js"):                          return "javascript"
    if l.endswith(".md"):                          return "markdown"
    if l.endswith(".json"):                        return "json"
    if "gmail" in l or "imap" in l:               return "gmail"
    if "npm" in l:                                 return "npm"
    if "launchd" in l or "plist" in l:            return "apple"
    if "linkedin" in l and not l.endswith(".py"): return "linkedin"
    if "cowork" in l or "anthropic" in l:         return "anthropic"
    return None


# ── Dynamic icon retrieval (Simple Icons CDN) ─────────────────────────────────

# Maps common shorthand names to canonical Simple Icons slugs.
SIMPLEICONS_ALIASES = {
    # GCP (Simple Icons includes GCP services; AWS/Azure service icons were removed)
    "gcp": "googlecloud", "google cloud": "googlecloud",
    "bigquery": "googlebigquery", "pubsub": "googlepubsub",
    # Databases
    "postgres": "postgresql", "mongo": "mongodb",
    "kafka": "apachekafka", "cassandra": "apachecassandra",
    "elastic": "elasticsearch",
    # Languages / runtimes
    # Simple Icons slugs "." as "dot": "Node.js"→"nodedotjs", "Vue.js"→"vuedotjs"
    # Labels ending in ".js" are handled automatically by _simpleicon_slug.
    # Aliases here cover shorthand forms that wouldn't derive correctly otherwise.
    "node": "nodedotjs", "nodejs": "nodedotjs",
    "golang": "go",
    "kotlin": "kotlin", "swift": "swift",
    "ruby": "ruby", "php": "php", "deno": "deno",
    # Frameworks — "Vue.js" / "Next.js" / "React" derive correctly via dot-rule
    "vue": "vuedotjs",
    "next": "nextdotjs", "nextjs": "nextdotjs",
    "angular": "angular",
    "django": "django", "flask": "flask", "fastapi": "fastapi",
    "rails": "rubyonrails", "laravel": "laravel",
    # DevOps / infra
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "terraform": "terraform", "ansible": "ansible",
    "github": "github", "gitlab": "gitlab",
    "jenkins": "jenkins", "circleci": "circleci",
    "nginx": "nginx", "grafana": "grafana", "prometheus": "prometheus",
    "datadog": "datadog", "sentry": "sentry", "kibana": "kibana",
    "cloudflare": "cloudflare",
    # SaaS / platforms
    "okta": "okta", "auth0": "auth0",
    "hubspot": "hubspot", "notion": "notion", "figma": "figma",
    "jira": "jira", "confluence": "confluence",
    "vercel": "vercel", "netlify": "netlify",
    # AI / ML
    "huggingface": "huggingface",
    # Messaging / queues
    "rabbitmq": "rabbitmq", "celery": "celery",
    # Other
    "graphql": "graphql", "airflow": "apacheairflow",
}


def _simpleicon_slug(label):
    """Normalize a label to a Simple Icons slug, consulting the alias table first.

    Simple Icons derives slugs by replacing "." with "dot" before stripping
    non-alphanumeric characters (e.g. "Node.js" -> "nodedotjs"). We replicate
    that rule so labels like "Vue.js" or "Next.js" resolve correctly without
    needing explicit alias entries.
    """
    key = label.lower().strip()
    if key in SIMPLEICONS_ALIASES:
        return SIMPLEICONS_ALIASES[key]
    slug = re.sub(r"[^a-z0-9]", "", key.replace(".", "dot"))
    return slug if len(slug) >= 2 else None


_SIICONS_INDEX = {}  # slug -> {name, hex} — populated lazily from Simple Icons data file


def _load_siicons_index():
    """Load the Simple Icons name+color index into _SIICONS_INDEX (once per process).

    The index is cached to disk at ICON_CACHE_DIR/_index.json so the ~450 KB data
    file is only downloaded once per machine. Colors live in the data file; SVG paths
    live in per-icon SVG files — two separate fetches per new icon, but each cached
    permanently thereafter.
    """
    if _SIICONS_INDEX:
        return
    cache_path = os.path.join(ICON_CACHE_DIR, "_index.json")
    os.makedirs(ICON_CACHE_DIR, exist_ok=True)
    if os.path.exists(cache_path):
        try:
            _SIICONS_INDEX.update(json.load(open(cache_path)))
            return
        except Exception:
            pass
    url = "https://raw.githubusercontent.com/simple-icons/simple-icons/HEAD/data/simple-icons.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "spinediagrams/0.4"})
        with urllib.request.urlopen(req, timeout=12) as r:
            icons = json.load(r)
        idx = {}
        for icon in icons:
            title    = icon["title"]
            explicit = icon.get("slug", "")
            # Replicate Simple Icons slug rule: "." -> "dot", strip non-alnum
            derived  = re.sub(r"[^a-z0-9]", "", title.lower().replace(".", "dot"))
            slug     = explicit or derived
            entry    = {"name": title, "hex": f"#{icon.get('hex', '555555')}"}
            idx[slug] = entry
            if explicit and derived != slug:
                idx[derived] = entry   # also index by the derived form
        _SIICONS_INDEX.update(idx)
        try:
            json.dump(idx, open(cache_path, "w"))
        except Exception:
            pass
    except Exception:
        pass  # index unavailable — icons fall back to fill #555555


def _fetch_simpleicon(slug):
    """Fetch icon data for a Simple Icons slug. Returns dict or None.

    Strategy:
      1. Check per-icon disk cache (permanent; also caches confirmed 404s).
      2. Load color index (downloaded once, cached permanently).
      3. Fetch SVG path from raw GitHub icons directory.
      4. Combine path + color, cache, return.

    Transient network errors are not cached so they retry on the next run.
    """
    os.makedirs(ICON_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(ICON_CACHE_DIR, f"{slug}.json")

    if os.path.exists(cache_path):
        try:
            cached = json.load(open(cache_path))
            return None if cached.get("not_found") else cached
        except Exception:
            pass

    _load_siicons_index()
    meta = _SIICONS_INDEX.get(slug, {})

    svg_url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/HEAD/icons/{slug}.svg"
    try:
        req = urllib.request.Request(svg_url, headers={"User-Agent": "spinediagrams/0.4"})
        with urllib.request.urlopen(req, timeout=6) as r:
            svg = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                json.dump({"not_found": True}, open(cache_path, "w"))
            except Exception:
                pass
        return None
    except Exception:
        return None  # transient error — don't cache

    path_m  = re.search(r'd="([^"]+)"', svg)
    title_m = re.search(r'<title>([^<]+)</title>', svg)
    if not path_m:
        return None

    data = {
        "name": meta.get("name") or (title_m.group(1) if title_m else slug.title()),
        "path": path_m.group(1),
        "fill": meta.get("hex", "#555555"),
    }
    try:
        json.dump(data, open(cache_path, "w"))
    except Exception:
        pass
    return data


def _fetch_dynamic_icon(label):
    """Attempt to resolve an unrecognized label to a Simple Icons icon.

    On success, mutates TECH_ICONS so the rest of the rendering pipeline
    works unchanged. Returns the icon key or None.
    """
    slug = _simpleicon_slug(label)
    if not slug:
        return None
    if slug in TECH_ICONS:
        return slug
    data = _fetch_simpleicon(slug)
    if data:
        TECH_ICONS[slug] = data
        return slug
    return None


# ── Predefined lane colour palettes ──────────────────────────────────────────
LANE_PRESETS = {
    "sf"      : ("#eef2ff", "#6366f1", "#c7d2fe"),
    "bench"   : ("#f0fdf4", "#16a34a", "#bbf7d0"),
    "hubspot" : ("#fff7ed", "#ea580c", "#fed7aa"),
    "zapier"  : ("#fdf4ff", "#a855f7", "#e9d5ff"),
    "gcp"     : ("#f0f9ff", "#0284c7", "#bae6fd"),
    "aws"     : ("#fff8f0", "#d97706", "#fde68a"),
    "azure"   : ("#eff6ff", "#2563eb", "#bfdbfe"),
    "stripe"  : ("#fdf2f8", "#db2777", "#fbcfe8"),
    "qbo"     : ("#fefce8", "#ca8a04", "#fef08a"),
    "postgres": ("#f0f9ff", "#0369a1", "#e0f2fe"),
    "redis"   : ("#fff1f2", "#be123c", "#fecdd3"),
    "kafka"   : ("#fdf4ff", "#7e22ce", "#f3e8ff"),
    "okta"    : ("#fffbeb", "#b45309", "#fde68a"),
    "slack"   : ("#f5f3ff", "#7c3aed", "#ede9fe"),
    "twilio"  : ("#fff1f2", "#e11d48", "#fecdd3"),
    "ses"     : ("#fff7ed", "#c2410c", "#fed7aa"),
    "docusign": ("#f8fafc", "#475569", "#e2e8f0"),
    "saas"    : ("#f9fafb", "#374151", "#e5e7eb"),
    "generic" : ("#f8fafc", "#64748b", "#e2e8f0"),
}

STATUS_COLOR = {
    "existing"     : ("#f1f5f9", "#334155"),
    "new"          : ("#0891B2", "#ffffff"),
    "transitioning": ("#B45309", "#ffffff"),
    "retiring"     : ("#DC2626", "#ffffff"),
    "operational"  : ("#15803D", "#ffffff"),
    "readonly"     : ("#cbd5e1", "#475569"),
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

STATUS_DESCRIPTIONS = {
    "existing":      "Component already exists; unchanged in this plan.",
    "new":           "Being actively built — not yet live.",
    "transitioning": "Mid-migration; running in dual-write or parallel mode.",
    "retiring":      "Being decommissioned. Do not add new dependencies.",
    "operational":   "Fully live on the new platform.",
    "readonly":      "Present but not written by the agent or system. Edited manually.",
}


def _esc(s):
    return (str(s)
            .replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _col_bounds(col, colspan, num_cols, margin_left, margin_right, col_gap):
    avail = CW - margin_left - margin_right - (num_cols - 1) * col_gap
    col_w = avail // num_cols
    x = margin_left + col * (col_w + col_gap)
    w = colspan * col_w + (colspan - 1) * col_gap
    return x, w, col_w


def _cont_height(n, cont_title_h):
    return cont_title_h + CONT_PAD_V + n * (NODE_H + NODE_GAP) - NODE_GAP + CONT_PAD_V


def _parse_aspect(val):
    if val is None:                return 16 / 9
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        s = val.strip()
        if ":" in s:
            w, h = s.split(":", 1)
            return float(w) / float(h)
        return float(s)
    return 16 / 9


def _parse_node(n, show_icons, fetch_icons=True):
    label   = n[0]
    status  = n[1]
    cat     = n[2] if len(n) > 2 and n[2] is not None else None
    primary = len(n) > 3 and bool(n[3])
    if len(n) > 4:
        icon = n[4]   # explicit override (None = suppress icon for this node)
    elif show_icons:
        icon = _detect_icon(label)
        if icon is None and fetch_icons:
            icon = _fetch_dynamic_icon(label)
    else:
        icon = None
    return {"label": label, "status": status, "category": cat,
            "primary": primary, "icon": icon}


def _resolve_cat(cat_cfg, default_mark):
    color = cat_cfg.get("color")
    mark  = cat_cfg.get("mark", default_mark)
    if color is None:
        if "stripe" in cat_cfg:
            color, mark = cat_cfg["stripe"], cat_cfg.get("mark", "stripe")
        elif "dot" in cat_cfg:
            color, mark = cat_cfg["dot"], cat_cfg.get("mark", "dot")
        else:
            color = "#888888"
    size  = cat_cfg.get("mark_size", MARK_SIZE_DEFAULTS.get(mark, 4))
    label = cat_cfg.get("label", "")
    return color, mark, size, label


def _wrap_text(text, max_chars=52):
    """Word-wrap text into lines of at most max_chars characters (max 4 lines)."""
    if not text:
        return []
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if len(test) <= max_chars:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines[:4]


def _render_tooltip(o, elem_x, elem_y, elem_h, lines, indent="  ", max_width=370):
    """Emit a dark floating tooltip box anchored above (or below) an element.

    elem_x/y/h — bounding box of the element being described
    lines       — list of text strings (from _wrap_text)
    """
    if not lines:
        return
    font_sz   = 11
    line_h    = 15
    pad_x, pad_y = 9, 6

    tip_w = min(max_width, int(max(len(l) for l in lines) * 6.8 + 2 * pad_x) + 4)
    tip_h = len(lines) * line_h + 2 * pad_y

    # Prefer above the element; fall back to below if too close to canvas top.
    ty = elem_y - tip_h - 6 if elem_y - tip_h - 6 >= 4 else elem_y + elem_h + 4
    tx = max(4, min(elem_x, CW - tip_w - 4))

    o.append(f'{indent}<g class="tip">')
    o.append(f'{indent}  <rect x="{tx}" y="{ty}" width="{tip_w}" height="{tip_h}" '
             f'rx="4" fill="#1e293b" opacity="0.93"/>')
    for i, line in enumerate(lines):
        lx = tx + pad_x
        ly = ty + pad_y + (i + 1) * line_h - 3
        o.append(f'{indent}  <text x="{lx}" y="{ly}" font-size="{font_sz}" '
                 f'fill="#f8fafc">{_esc(line)}</text>')
    o.append(f'{indent}</g>')


def _render_icon(o, icon_key, ix, iy, size, indent="  "):
    """Emit SVG elements for a tech icon at position (ix, iy) scaled to `size` px."""
    icon_def = TECH_ICONS.get(icon_key)
    if not icon_def:
        return
    fill = icon_def["fill"]
    if icon_def.get("type") == "text":
        # Lightweight text badge: render chars centered in the icon bounding box.
        cx = ix + size // 2
        cy = iy + size // 2 + max(2, int(size * 0.18))
        fs = max(7, int(size * 0.58))
        o.append(f'{indent}<text x="{cx}" y="{cy}" text-anchor="middle" font-size="{fs}" '
                 f'font-weight="800" font-family="ui-monospace,monospace" fill="{fill}">'
                 f'{_esc(icon_def["chars"])}</text>')
        return
    scale = size / 24.0
    bg    = icon_def.get("bg")
    rule  = icon_def.get("rule", "nonzero")
    if bg:
        o.append(f'{indent}<rect x="{ix}" y="{iy}" width="{size}" height="{size}" rx="2" fill="{bg}"/>')
    o.append(f'{indent}<g transform="translate({ix},{iy}) scale({scale:.4f})">')
    o.append(f'{indent}  <path d="{icon_def["path"]}" fill="{fill}" fill-rule="{rule}"/>')
    o.append(f'{indent}</g>')


# ── Main class ────────────────────────────────────────────────────────────────

class Diagram:
    def __init__(self, config):
        if isinstance(config, str):
            config = json.loads(config)

        self.title         = config.get("title", "Architecture Diagram")
        self.num_cols      = int(config.get("num_cols", 6))
        self.target_aspect = _parse_aspect(config.get("aspect", "16:9"))
        lanes_cfg          = config.get("lanes", {})
        nodes_cfg          = config.get("nodes", {})
        self.raw_conns     = config.get("connections", [])
        self.show_icons    = config.get("show_icons", True)

        self.edge_color      = config.get("edge_color", None)
        self.edge_dashed     = config.get("edge_dashed", True)
        self.categories      = config.get("categories", {})
        self.default_cat_mark= config.get("category_mark", "dot")
        self.descriptions    = config.get("descriptions", {})
        # fetch_icons: false disables dynamic Simple Icons retrieval (offline / fast mode)
        self.fetch_icons     = config.get("fetch_icons", True)

        # Determine if any node has a detectable icon so we can size headers.
        _has_icon = False
        if self.show_icons:
            for nlist in nodes_cfg.values():
                for n in nlist:
                    explicit = n[4] if len(n) > 4 else None
                    auto     = _detect_icon(n[0])
                    if explicit or auto:
                        _has_icon = True
                        break
                if _has_icon:
                    break
        self.has_any_icon  = _has_icon
        self.cont_title_h  = CONT_TITLE_H_ICO if _has_icon else CONT_TITLE_H

        # Legend configuration
        legend_cfg = config.get("legend", "default")
        if legend_cfg is False or legend_cfg == "hide":
            self.show_legend    = False
            self.legend_entries = []
        elif isinstance(legend_cfg, list):
            self.show_legend    = True
            self.legend_entries = legend_cfg
        else:
            self.show_legend    = True
            self.legend_entries = [(STATUS_COLOR[s][0], l, STATUS_DESCRIPTIONS.get(s, "")) for s, l in LEGEND_ENTRIES]

        self.show_cat_legend = bool(self.categories)

        if self.show_legend and self.show_cat_legend:
            self.bot_pad = 92
        elif self.show_legend or self.show_cat_legend:
            self.bot_pad = 52
        else:
            self.bot_pad = 16

        # Anchor spreading
        _src_groups = defaultdict(list)
        _dst_groups = defaultdict(list)
        for _idx, _conn in enumerate(self.raw_conns):
            if len(_conn) >= 4:
                _src_groups[(_conn[0], _conn[1])].append(_idx)
                _dst_groups[(_conn[2], _conn[3])].append(_idx)
        self._conn_src_frac = {}
        self._conn_dst_frac = {}
        for _key, _indices in _src_groups.items():
            _n = len(_indices)
            for _rank, _idx in enumerate(_indices):
                self._conn_src_frac[_idx] = (_rank + 1) / (_n + 1)
        for _key, _indices in _dst_groups.items():
            _n = len(_indices)
            _sorted = sorted(
                _indices,
                key=lambda _i: (lanes_cfg.get(self.raw_conns[_i][0], {}).get("col", 0)
                                + lanes_cfg.get(self.raw_conns[_i][0], {}).get("colspan", 1) / 2.0)
            )
            for _rank, _idx in enumerate(_sorted):
                self._conn_dst_frac[_idx] = (_rank + 1) / (_n + 1)

        # Sidestep pre-pass
        self.conn_meta = {}
        n_left = n_right = 0
        for idx, conn in enumerate(self.raw_conns):
            if len(conn) < 4:
                continue
            sl = lanes_cfg.get(conn[0])
            dl = lanes_cfg.get(conn[2])
            if sl is None or dl is None:
                continue
            r1, r2 = int(sl.get("row", 0)), int(dl.get("row", 0))
            if min(r1, r2) == 0 and max(r1, r2) == 2:
                src_mid = sl.get("col", 0) + sl.get("colspan", 1) / 2
                dst_mid = dl.get("col", 0) + dl.get("colspan", 1) / 2
                if (src_mid + dst_mid) / 2 < self.num_cols / 2:
                    self.conn_meta[idx] = {"type": "sidestep", "side": "left",  "ch_idx": n_left}
                    n_left += 1
                else:
                    self.conn_meta[idx] = {"type": "sidestep", "side": "right", "ch_idx": n_right}
                    n_right += 1
        self.n_sidestep_left  = n_left
        self.n_sidestep_right = n_right

        def _margin(n):
            return MARGIN if n == 0 else SIDESTEP_EDGE_PAD + n * SIDESTEP_CHANNEL_STEP + 6
        self.margin_left  = _margin(n_left)
        self.margin_right = _margin(n_right)

        self.conts = {}
        for key, lane in lanes_cfg.items():
            col     = int(lane.get("col", 0))
            colspan = int(lane.get("colspan", 1))
            row     = int(lane.get("row", 0))
            nodes   = nodes_cfg.get(key, [])
            x, w, _ = _col_bounds(col, colspan, self.num_cols,
                                   self.margin_left, self.margin_right, COL_GAP)
            preset    = LANE_PRESETS.get(key, LANE_PRESETS["generic"])
            bg        = lane.get("bg",        preset[0])
            border    = lane.get("border",    preset[1])
            header_bg = lane.get("header_bg", preset[2])
            parsed_nodes = [_parse_node(n, self.show_icons, self.fetch_icons) for n in nodes]

            # Smart header icon layout: calculate how many icons fit inline vs. overflow
            seen_ik, lane_icons = set(), []
            for nd in parsed_nodes:
                ik = nd.get("icon")
                if ik and ik not in seen_ik and ik in TECH_ICONS:
                    seen_ik.add(ik); lane_icons.append(ik)
            if lane_icons:
                lbl_px  = len(lane.get("label", key)) * 7.2
                avail   = w // 2 - int(lbl_px) // 2 - 14
                n_fits  = max(0, (avail + 3) // (HDR_ICON_SIZE + 3)) if avail >= HDR_ICON_SIZE else 0
                n_fits  = min(n_fits, len(lane_icons))
                icons_l1 = lane_icons[:n_fits]
                icons_l2 = lane_icons[n_fits:]
            else:
                icons_l1 = icons_l2 = []
            cth = CONT_TITLE_H_ICO if icons_l2 else CONT_TITLE_H

            self.conts[key] = {
                "key": key, "label": lane.get("label", key),
                "col": col, "colspan": colspan, "row": row,
                "x": x, "w": w,
                "h": _cont_height(len(parsed_nodes), cth),
                "bg": bg, "border": border, "header_bg": header_bg,
                "nodes": parsed_nodes,
                "cont_title_h": cth,
                "icons_line1": icons_l1,
                "icons_line2": icons_l2,
            }

        self.sidestep_x = {}
        for idx, meta in self.conn_meta.items():
            if meta.get("type") != "sidestep":
                continue
            offset = SIDESTEP_EDGE_PAD + meta["ch_idx"] * SIDESTEP_CHANNEL_STEP
            self.sidestep_x[idx] = offset if meta["side"] == "left" else CW - offset

        self._compute_y()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _compute_y(self):
        row_h = {0: 0, 1: 0, 2: 0}
        for c in self.conts.values():
            row_h[c["row"]] = max(row_h[c["row"]], c["h"])
        has_row2 = row_h[2] > 0

        n_spine01 = n_spine12 = 0
        for idx, conn in enumerate(self.raw_conns):
            if len(conn) < 4:
                continue
            sc = self.conts.get(conn[0])
            dc = self.conts.get(conn[2])
            if sc is None or dc is None:
                continue
            r1, r2 = sc["row"], dc["row"]
            lo, hi = min(r1, r2), max(r1, r2)
            if lo == 0 and hi == 2:
                meta = self.conn_meta[idx]
                meta["sp01_idx"] = n_spine01
                meta["sp12_idx"] = n_spine12
                n_spine01 += 1
                n_spine12 += 1
            elif hi <= 1:
                self.conn_meta[idx] = {"type": "spine01", "sp01_idx": n_spine01}
                n_spine01 += 1
            else:
                self.conn_meta[idx] = {"type": "spine12", "sp12_idx": n_spine12}
                n_spine12 += 1

        spine01 = max(20, 16 + max(0, n_spine01 - 1) * SPINE_LINE_MIN)
        spine12 = max(20, 16 + max(0, n_spine12 - 1) * SPINE_LINE_MIN) if has_row2 else 0

        baseline_h = (HEADER_H + 6 + row_h[0] + spine01 + row_h[1]
                      + (spine12 + row_h[2] if has_row2 else 0) + self.bot_pad)

        target_h = int(CW / self.target_aspect)
        if baseline_h < target_h:
            extra = target_h - baseline_h
            if not has_row2 or (n_spine01 + n_spine12) == 0:
                spine01 += extra
            else:
                share01 = int(extra * max(1, n_spine01) / (max(1, n_spine01) + max(1, n_spine12)))
                spine01 += share01
                spine12 += extra - share01

        self.spine01_gap = spine01
        self.spine12_gap = spine12
        self.has_row2    = has_row2

        self.row0_y   = HEADER_H + 6
        self.row0_bot = self.row0_y + row_h[0]
        self.row1_y   = self.row0_bot + spine01
        self.row1_bot = self.row1_y + row_h[1]
        if has_row2:
            self.row2_y   = self.row1_bot + spine12
            self.row2_bot = self.row2_y + row_h[2]
            self.canvas_h = self.row2_bot + self.bot_pad
        else:
            self.row2_y = self.row2_bot = self.row1_bot
            self.canvas_h = self.row1_bot + self.bot_pad

        self.spine01_lines = self._distribute_spine(self.row0_bot + 8, self.row1_y - 8, n_spine01)
        self.spine12_lines = (self._distribute_spine(self.row1_bot + 8, self.row2_y - 8, n_spine12)
                              if has_row2 else [])
        self.spine_y = (self.row0_bot + self.row1_y) // 2

        for c in self.conts.values():
            r = c["row"]
            c["y"] = self.row0_y if r == 0 else self.row1_y if r == 1 else self.row2_y

    @staticmethod
    def _distribute_spine(top, bot, n):
        if n <= 0: return []
        if n == 1: return [(top + bot) // 2]
        step = (bot - top) / (n - 1)
        return [int(top + i * step) for i in range(n)]

    def _node_rect(self, c, idx):
        nx = c["x"] + CONT_PAD_H
        nw = c["w"] - 2 * CONT_PAD_H
        ny = c["y"] + c["cont_title_h"] + CONT_PAD_V + idx * (NODE_H + NODE_GAP)
        return nx, ny, nw, NODE_H

    def _find_node(self, lane_key, label):
        c = self.conts.get(lane_key)
        if c is None: return None, -1
        for i, n in enumerate(c["nodes"]):
            if n["label"] == label:
                return c, i
        return c, -1

    # ── Routing ──────────────────────────────────────────────────────────────

    def _route(self, src_lane, src_label, dst_lane, dst_label, idx):
        src_c, si = self._find_node(src_lane, src_label)
        dst_c, di = self._find_node(dst_lane, dst_label)
        if src_c is None or dst_c is None:
            return None

        def anchor_x(c, i, frac):
            if i >= 0:
                nx, _, nw, _ = self._node_rect(c, i)
                return nx + int(nw * frac)
            return c["x"] + int(c["w"] * frac)

        sx = anchor_x(src_c, si, self._conn_src_frac.get(idx, 0.5))
        dx = anchor_x(dst_c, di, self._conn_dst_frac.get(idx, 0.5))

        meta = self.conn_meta.get(idx)
        if meta is None: return None
        kind = meta["type"]

        if kind == "sidestep":
            sp01 = self.spine01_lines[meta["sp01_idx"]]
            sp12 = self.spine12_lines[meta["sp12_idx"]]
            ch_x = self.sidestep_x[idx]
            src_edge = src_c["y"] + src_c["h"] if src_c["row"] == 0 else src_c["y"]
            dst_edge = dst_c["y"] + dst_c["h"] if dst_c["row"] == 0 else dst_c["y"]
            if src_c["row"] == 0:
                return [(sx,src_edge),(sx,sp01),(ch_x,sp01),(ch_x,sp12),(dx,sp12),(dx,dst_edge)]
            else:
                return [(sx,src_edge),(sx,sp12),(ch_x,sp12),(ch_x,sp01),(dx,sp01),(dx,dst_edge)]

        if kind == "spine01":
            spine = self.spine01_lines[meta["sp01_idx"]]
            def edge(c): return c["y"] + c["h"] if c["row"] == 0 else c["y"]
        else:
            spine = self.spine12_lines[meta["sp12_idx"]]
            def edge(c): return c["y"] + c["h"] if c["row"] == 1 else c["y"]

        return [(sx, edge(src_c)), (sx, spine), (dx, spine), (dx, edge(dst_c))]

    # ── SVG render ───────────────────────────────────────────────────────────

    def render(self):
        h = int(self.canvas_h)
        o = []

        o.append(f'<svg viewBox="0 0 {CW} {h}" xmlns="http://www.w3.org/2000/svg" '
                 f'style="font-family:{FONT}; background:#ffffff;">')

        arr_color = self.edge_color if self.edge_color else "#64748b"
        o.append(f"""  <defs>
    <marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L7,3 z" fill="{arr_color}"/>
    </marker>
    <marker id="arr-rev" markerWidth="7" markerHeight="7" refX="1" refY="3" orient="auto">
      <path d="M7,0 L7,6 L0,3 z" fill="{arr_color}"/>
    </marker>
    <style>
      .tip {{ visibility: hidden; pointer-events: none; }}
      .has-tip:hover > .tip {{ visibility: visible; }}
    </style>
  </defs>""")

        # Header band
        o.append(f'  <rect x="0" y="0" width="{CW}" height="{HEADER_H}" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
        parts = self.title.split(" — ", 1)
        o.append(f'  <text x="{CW//2}" y="18" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">{_esc(parts[0])}</text>')
        if len(parts) > 1:
            o.append(f'  <text x="{CW//2}" y="36" text-anchor="middle" font-size="11" fill="#64748b">{_esc(parts[1])}</text>')

        # Containers
        for key, c in self.conts.items():
            x, y, w, ch = c["x"], c["y"], c["w"], c["h"]
            cth         = c["cont_title_h"]
            icons_line1 = c.get("icons_line1", [])
            icons_line2 = c.get("icons_line2", [])
            r           = 8

            o.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{ch}" rx="{r}" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
            cid = f"clip_{key}"
            o.append(f'  <clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{cth}" rx="{r}"/></clipPath>')
            o.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{cth}" fill="{c["header_bg"]}" clip-path="url(#{cid})"/>')

            # Lane label: top of header when overflow icons need a second row, centered otherwise
            label_y = y + 14 if icons_line2 else y + cth - 7
            o.append(f'  <text x="{x+w//2}" y="{label_y}" text-anchor="middle" font-size="12" font-weight="600" fill="{c["border"]}">{_esc(c["label"])}</text>')

            # Line 1 icons: inline with label (left side, vertically centered in header)
            if icons_line1:
                ix = x + 6
                iy = y + (cth - HDR_ICON_SIZE) // 2
                for ik in icons_line1:
                    tech_name = TECH_ICONS[ik].get("name", ik)
                    o.append(f'  <g class="has-tip">')
                    o.append(f'    <rect x="{ix-2}" y="{iy-2}" width="{HDR_ICON_SIZE+4}" '
                             f'height="{HDR_ICON_SIZE+4}" fill-opacity="0" pointer-events="all"/>')
                    _render_icon(o, ik, ix, iy, HDR_ICON_SIZE, indent="    ")
                    _render_tooltip(o, ix, iy, HDR_ICON_SIZE, [tech_name], indent="    ")
                    o.append(f'  </g>')
                    ix += HDR_ICON_SIZE + 3

            # Line 2 icons: overflow row (only present when icons don't all fit inline)
            if icons_line2:
                ix = x + 6
                iy = y + 24
                for ik in icons_line2:
                    tech_name = TECH_ICONS[ik].get("name", ik)
                    o.append(f'  <g class="has-tip">')
                    o.append(f'    <rect x="{ix-2}" y="{iy-2}" width="{HDR_ICON_SIZE+4}" '
                             f'height="{HDR_ICON_SIZE+4}" fill-opacity="0" pointer-events="all"/>')
                    _render_icon(o, ik, ix, iy, HDR_ICON_SIZE, indent="    ")
                    _render_tooltip(o, ix, iy, HDR_ICON_SIZE, [tech_name], indent="    ")
                    o.append(f'  </g>')
                    ix += HDR_ICON_SIZE + 3

            o.append(f'  <line x1="{x}" y1="{y+cth}" x2="{x+w}" y2="{y+cth}" stroke="{c["border"]}" stroke-width="0.8" opacity="0.5"/>')

            # Nodes
            for i, node in enumerate(c["nodes"]):
                nx, ny, nw, nh = self._node_rect(c, i)
                fill, fc = STATUS_COLOR.get(node["status"], ("#64748b", "#fff"))
                is_primary = node.get("primary", False)
                cat        = node.get("category")
                icon_key   = node.get("icon")
                has_icon   = icon_key and icon_key in TECH_ICONS

                cat_cfg    = self.categories.get(cat, {}) if cat else {}
                mark_color = mark_type = mark_size = None
                if cat and cat in self.categories:
                    mark_color, mark_type, mark_size, _ = _resolve_cat(
                        self.categories[cat], self.default_cat_mark
                    )

                desc       = self.descriptions.get(node["label"], "")
                desc_lines = _wrap_text(desc) if desc else []
                fw         = "700" if is_primary else "500"

                # Outer group: node background + primary border
                o.append(f'  <g>')
                o.append(f'    <title>{_esc(node["label"])}</title>')
                border_attr = f' stroke="{c["border"]}" stroke-width="1"' if is_primary else ''
                o.append(f'    <rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="{NODE_R}" fill="{fill}"{border_attr}/>')

                if has_icon:
                    isize = NODE_ICON_SIZE
                    ix    = nx + 3
                    iy    = ny + (nh - isize) // 2
                    tx    = ix + isize + 4

                    # Icon hover zone — shows tech name
                    tech_name = TECH_ICONS[icon_key].get("name", icon_key)
                    o.append(f'    <g class="has-tip">')
                    o.append(f'      <rect x="{ix-1}" y="{ny+1}" width="{isize+3}" height="{nh-2}" '
                             f'fill-opacity="0" pointer-events="all"/>')
                    _render_icon(o, icon_key, ix, iy, isize, indent="      ")
                    _render_tooltip(o, ix, ny, nh, [tech_name], indent="      ")
                    o.append(f'    </g>')

                    # Text hover zone — shows description
                    text_w = nw - (isize + 9)
                    if desc_lines:
                        o.append(f'    <g class="has-tip">')
                        o.append(f'      <rect x="{tx-2}" y="{ny+1}" width="{text_w}" height="{nh-2}" '
                                 f'fill-opacity="0" pointer-events="all"/>')
                        o.append(f'      <text x="{tx}" y="{ny+nh//2+4}" text-anchor="start" '
                                 f'font-size="11" font-weight="{fw}" fill="{fc}">{_esc(node["label"])}</text>')
                        _render_tooltip(o, tx, ny, nh, desc_lines, indent="      ")
                        o.append(f'    </g>')
                    else:
                        o.append(f'    <text x="{tx}" y="{ny+nh//2+4}" text-anchor="start" '
                                 f'font-size="11" font-weight="{fw}" fill="{fc}">{_esc(node["label"])}</text>')
                else:
                    # No tech icon — category mark + centered text. Whole node is the hover zone.
                    node_open = f'    <g class="has-tip">' if desc_lines else '    <g>'
                    o.append(node_open)
                    if mark_color and mark_type:
                        if mark_type == "dot":
                            r_dot = mark_size
                            cx_d = nx + nw - r_dot - 5
                            cy_d = ny + r_dot + 4
                            o.append(f'      <circle cx="{cx_d}" cy="{cy_d}" r="{r_dot+1}" fill="white"/>')
                            o.append(f'      <circle cx="{cx_d}" cy="{cy_d}" r="{r_dot}" fill="{mark_color}"/>')
                        elif mark_type == "stripe":
                            o.append(f'      <rect x="{nx+1}" y="{ny+NODE_R}" width="{mark_size}" '
                                     f'height="{nh-2*NODE_R}" fill="{mark_color}" rx="1"/>')
                    o.append(f'      <text x="{nx+nw//2}" y="{ny+nh//2+4}" text-anchor="middle" '
                             f'font-size="11" font-weight="{fw}" fill="{fc}">{_esc(node["label"])}</text>')
                    if desc_lines:
                        _render_tooltip(o, nx, ny, nh, desc_lines, indent="      ")
                    o.append(f'    </g>')

                o.append(f'  </g>')

        # Edges
        for idx, conn in enumerate(self.raw_conns):
            sl, src_lbl, dl, dst_lbl = conn[0], conn[1], conn[2], conn[3]
            elbl  = conn[4] if len(conn) > 4 else ""
            bidir = bool(conn[5]) if len(conn) > 5 else False
            pts   = self._route(sl, src_lbl, dl, dst_lbl, idx)
            if not pts:
                continue
            color      = self.edge_color if self.edge_color else EDGE_PALETTE[idx % len(EDGE_PALETTE)]
            d          = "M " + " L ".join(f"{int(p[0])} {int(p[1])}" for p in pts)
            dash       = ' stroke-dasharray="5,3"' if self.edge_dashed else ''
            bidir_attr = ' marker-start="url(#arr-rev)"' if bidir else ''
            o.append(f'  <path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{dash}{bidir_attr} marker-end="url(#arr)" opacity="0.85"/>')
            if elbl and len(pts) >= 3:
                best = None
                for i in range(len(pts) - 1):
                    if pts[i][1] == pts[i+1][1]:
                        length = abs(pts[i+1][0] - pts[i][0])
                        if best is None or length > best[0]:
                            best = (length, pts[i], pts[i+1])
                if best is not None:
                    _, p1, p2 = best
                    mx = (p1[0] + p2[0]) / 2
                    my = (p1[1] + p2[1]) / 2
                    lw = max(60, len(elbl) * 6 + 10)
                    o.append(f'  <rect x="{int(mx-lw/2)}" y="{int(my-8)}" width="{lw}" height="14" rx="3" fill="white" opacity="0.92"/>')
                    o.append(f'  <text x="{int(mx)}" y="{int(my+3)}" text-anchor="middle" font-size="9" fill="{color}" font-weight="600">{_esc(elbl)}</text>')

        # Category legend
        if self.show_cat_legend:
            cat_entries = []
            for k, v in self.categories.items():
                color, mark, _, label = _resolve_cat(v, self.default_cat_mark)
                cat_desc = v.get("description", "")
                cat_entries.append((color, mark, label or k.replace("_", " ").title(), cat_desc))
            ly    = (h - 72) if self.show_legend else (h - 36)
            lx    = self.margin_left
            avail = CW - self.margin_left - self.margin_right
            bw    = avail // max(1, len(cat_entries))
            o.append(f'  <rect x="{lx-4}" y="{ly-14}" width="{avail+8}" height="32" rx="4" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
            for i, (color, mark, label, cat_desc) in enumerate(cat_entries):
                ex = lx + i * bw
                cat_lines = _wrap_text(cat_desc, max_chars=40) if cat_desc else []
                if cat_lines:
                    o.append(f'  <g class="has-tip">')
                    o.append(f'    <rect x="{ex-2}" y="{ly-14}" width="{bw}" height="32" '
                             f'fill-opacity="0" pointer-events="all"/>')
                if mark == "dot":
                    o.append(f'  <circle cx="{ex+6}" cy="{ly}" r="5" fill="white"/>')
                    o.append(f'  <circle cx="{ex+6}" cy="{ly}" r="4" fill="{color}"/>')
                else:
                    o.append(f'  <rect x="{ex}" y="{ly-6}" width="4" height="13" rx="2" fill="{color}"/>')
                o.append(f'  <text x="{ex+17}" y="{ly+5}" font-size="11" fill="#374151">{_esc(label)}</text>')
                if cat_lines:
                    _render_tooltip(o, ex, ly - 14, 32, cat_lines, indent="    ")
                    o.append(f'  </g>')

        # Status legend
        if self.show_legend:
            lx, ly = self.margin_left, h - 36
            avail  = CW - self.margin_left - self.margin_right
            bw     = avail // max(1, len(self.legend_entries))
            o.append(f'  <rect x="{lx-4}" y="{ly-14}" width="{avail+8}" height="32" rx="4" fill="#f8fafc" stroke="#e2e8f0" stroke-width="1"/>')
            for i, entry in enumerate(self.legend_entries):
                fill, lbl = entry[0], entry[1]
                desc = entry[2] if len(entry) > 2 else ""
                ex = lx + i * bw
                desc_lines = _wrap_text(desc, max_chars=40) if desc else []
                if desc_lines:
                    o.append(f'  <g class="has-tip">')
                    o.append(f'    <rect x="{ex-2}" y="{ly-14}" width="{bw}" height="32" '
                             f'fill-opacity="0" pointer-events="all"/>')
                o.append(f'  <rect x="{ex}" y="{ly-6}" width="13" height="13" rx="3" fill="{fill}"/>')
                o.append(f'  <text x="{ex+17}" y="{ly+5}" font-size="11" fill="#374151">{_esc(lbl)}</text>')
                if desc_lines:
                    _render_tooltip(o, ex, ly - 14, 32, desc_lines, indent="    ")
                    o.append(f'  </g>')

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
