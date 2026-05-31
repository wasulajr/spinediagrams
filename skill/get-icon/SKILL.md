# /get-icon — spinediagrams icon finder

Finds SVG icon data for a named technology and outputs a ready-to-paste
`TECH_ICONS` entry for `svg_engine.py`. Tries Simple Icons, then Iconify,
then a web search. Falls back to a text badge and tells the user if nothing
is found.

## Invocation

`/get-icon Redis` — use the argument as the technology name  
`/get-icon`       — ask the user what technology they want

## Step 1: Get the technology name

If the skill was invoked with an argument, use it verbatim. Otherwise ask:

> What technology do you want an icon for?

---

## Step 2: Check if it's already supported

Run this to check whether the technology is already in the engine:

```bash
python3 - <<'EOF'
import sys, re
sys.path.insert(0, "/Users/stephenwasula/.claude/skills/spinediagrams/scripts")
from svg_engine import TECH_ICONS, SIMPLEICONS_ALIASES, _detect_icon

name = "TECHNOLOGY_NAME_HERE"
icon_key = _detect_icon(name)
alias_key = SIMPLEICONS_ALIASES.get(name.lower().strip())
builtin = name.lower().replace(".", "dot").replace(" ", "") in TECH_ICONS

print(f"detect_icon: {icon_key}")
print(f"alias:       {alias_key}")
print(f"builtin:     {builtin}")
EOF
```

If any result is non-None/non-False, tell the user the technology is already
supported (show which key resolves it) and stop — no further action needed.

---

## Step 3: Derive the slug

Apply the Simple Icons slug rule to the technology name:
1. Lowercase and strip whitespace
2. Replace every `.` with the word `dot`
3. Strip all remaining non-alphanumeric characters

Examples: `Node.js` → `nodedotjs` | `Vue.js` → `vuedotjs` | `Redis` → `redis`

Also keep the plain lowercase-stripped form (without the dot→word step) as an
alternate slug to try if the first fails.

---

## Step 4: Try Simple Icons (preferred source)

Fetch the SVG using the Bash tool:

```bash
python3 - <<'EOF'
import urllib.request, urllib.error, json, re, sys

slug = "SLUG_HERE"
name = "TECHNOLOGY_NAME_HERE"

# 1. Fetch the SVG path
svg_url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/HEAD/icons/{slug}.svg"
try:
    with urllib.request.urlopen(svg_url, timeout=8) as r:
        svg = r.read().decode()
    print("SVG_OK")
    paths = re.findall(r'<path([^>]+)>', svg)
    print(f"PATHS={len(paths)}")
    for p in paths:
        d = re.search(r'\bd="([^"]+)"', p)
        fill = re.search(r'\bfill="([^"]+)"', p)
        rule = re.search(r'fill-rule="([^"]+)"', p)
        print(f"D={d.group(1) if d else ''}")
        print(f"FILL={fill.group(1) if fill else ''}")
        print(f"RULE={rule.group(1) if rule else ''}")
except urllib.error.HTTPError as e:
    print(f"SVG_{e.code}")
except Exception as e:
    print(f"SVG_ERR:{e}")

# 2. Fetch the brand color from the data file
data_url = "https://raw.githubusercontent.com/simple-icons/simple-icons/HEAD/data/simple-icons.json"
try:
    with urllib.request.urlopen(data_url, timeout=12) as r:
        icons = json.load(r)
    for icon in icons:
        derived = re.sub(r'[^a-z0-9]', '', icon['title'].lower().replace('.', 'dot'))
        explicit = icon.get('slug', '') or derived
        if explicit == slug or derived == slug:
            print(f"COLOR=#{icon.get('hex', '555555')}")
            print(f"TITLE={icon['title']}")
            break
    else:
        print("COLOR=#555555")
        print("TITLE=")
except Exception as e:
    print(f"COLOR_ERR:{e}")
    print("COLOR=#555555")
EOF
```

**If the SVG fetch succeeds (SVG_OK):**

Parse the output to build the TECH_ICONS entry:
- Single path, no fill in path → use `"path"` + `"fill"` from COLOR
- Single path with `fill="..."` in the path element → use that fill
- `fill-rule="evenodd"` → add `"rule": "evenodd"`
- Multiple paths with different fills → use `"paths"` list
- viewBox for Simple Icons is always `0 0 24 24` — **do not include `"viewbox"`**

Proceed to Step 7 to output the result.

**If the SVG fetch returns 404:**
Continue to Step 5.

---

## Step 5: Try Iconify logos set

```bash
python3 - <<'EOF'
import urllib.request, urllib.error, re

slug = "SLUG_HERE"

for candidate in [slug, f"{slug}-icon", f"{slug}-logo", slug.replace("dot", "")]:
    url = f"https://api.iconify.design/logos/{candidate}.svg"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            svg = r.read().decode()
        vb = re.search(r'viewBox="([^"]+)"', svg)
        paths = re.findall(r'<path([^>]+)>', svg)
        print(f"FOUND={candidate}")
        print(f"VIEWBOX={vb.group(1) if vb else '0 0 24 24'}")
        print(f"NPATHS={len(paths)}")
        for p in paths:
            d = re.search(r'\bd="([^"]+)"', p)
            fill = re.search(r'\bfill="([^"]+)"', p)
            print(f"D={d.group(1) if d else ''}")
            print(f"FILL={fill.group(1) if fill else '#555555'}")
        break
    except urllib.error.HTTPError:
        print(f"MISS={candidate}")
    except Exception as e:
        print(f"ERR={e}")
EOF
```

**If found:** parse output and build the TECH_ICONS entry.

- If viewBox is not `0 0 24 24`, include `"viewbox"` in the entry
- If 1 path: single-path format
- If 2–4 paths with distinct fills: use `"paths"` list
- If 5+ paths: use only the 1–2 paths with the largest `d` strings (most detail)

Proceed to Step 7.

**If all Iconify candidates return 404:** continue to Step 6.

---

## Step 6: Web search fallback

Search for: `{technology name} SVG logo path`

Look for:
- A direct `.svg` file URL (fetch it and extract paths)
- A GitHub repo with an SVG logo file
- An official press kit page with SVG downloads

If a usable SVG is found, fetch it, extract paths using the same Python regex
pattern, and proceed to Step 7.

**If no SVG source found anywhere:**

Create a text badge:
- Derive 2–3 character initials (first letters of each word, or first 2–3 chars)
- Color: `#555555` (generic — flag it as needing a real brand color)

Tell the user clearly:

> No SVG icon was found for **{technology name}** in Simple Icons, Iconify, or
> via web search. A text badge entry has been created using the initials
> **{chars}**. You can update the `fill` color with the actual brand color once
> you find it, or replace the entry entirely if you locate an SVG source later.

---

## Step 7: Output the result

Output all three sections, clearly labeled and ready to paste.

### Section A — paste into TECH_ICONS in svg_engine.py (after the last entry, before the closing `}`)

```python
"key": {
    "name": "Full Brand Name",
    "path": "...",          # verbatim d=... value
    "fill": "#RRGGBB",
    # "rule": "evenodd",    # include only if source SVG had fill-rule="evenodd"
    # "viewbox": "0 0 N N", # include only if NOT a 24x24 Simple Icons source
},
```

For multi-path:
```python
"key": {
    "name": "Full Brand Name",
    "viewbox": "0 0 256 256",
    "paths": [
        {"d": "...", "fill": "#color1"},
        {"d": "...", "fill": "#color2"},
    ],
    "fill": "#primary_brand_color",
},
```

For text badge:
```python
"key": {
    "name": "Full Brand Name",
    "type": "text",
    "chars": "AB",
    "fill": "#555555",  # update with actual brand color
},
```

### Section B — paste into _detect_icon() in svg_engine.py (before `return None`)

```python
if "keyword" in l:   return "key"   # Full Brand Name
```

Choose the most natural keyword — part of the lowercased brand name that
wouldn't falsely match other technologies.

### Section C — paste into SIMPLEICONS_ALIASES (only if alias differs from key)

```python
"shorthand": "key",    # Full Brand Name
"other alias": "key",
```

Common aliases: abbreviations, common misspellings, the brand name without
`.js`/`.io` suffixes.

---

## Source priority summary

| Source | URL pattern | Notes |
|--------|-------------|-------|
| Simple Icons | `raw.githubusercontent.com/simple-icons/.../icons/{slug}.svg` | 24×24, no `viewbox` field needed |
| Iconify logos | `api.iconify.design/logos/{slug}.svg` | Any viewBox; include `viewbox` if not 24×24 |
| Web search | Direct SVG URL | Parse same as above |
| Text badge | (no network fetch) | Last resort; flag color as needing update |

## Critical rules

- **Never invent or hallucinate path data.** If no HTTP 200 response with a
  `<path d="...">` element is received, do not fabricate a path.
- Copy `d` attribute values exactly — do not shorten, summarize, or paraphrase.
- If `fill` cannot be determined from any source, use `#555555` and add a
  comment telling the user to update it.
- The TECH_ICONS `key` must be all lowercase, no spaces, special chars replaced:
  `.` → `dot`, everything else stripped.
