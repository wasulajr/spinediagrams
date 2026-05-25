#!/usr/bin/env python3
"""
Example: 3-tier app with row 0↔2 sidestep connections.

Shows the margin-sidestep feature — direct browser-to-CDN asset downloads
and direct browser-to-analytics beacon paths that bypass the backend.
Four sidesteps (2 left, 2 right) route around through the canvas margins
instead of crossing the middle row.

Run:
    python examples/3-tier-with-sidestep.py
    open examples/3-tier-with-sidestep.svg
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skill", "scripts"))
from svg_engine import Diagram

config = {
    "title": "3-tier + sidestep — direct browser → CDN / analytics paths",
    "aspect": "16:9", "num_cols": 6,
    "lanes": {
        "web":   {"label":"Web app","col":0,"colspan":2,"row":0},
        "mobile":{"label":"Mobile","col":2,"colspan":2,"row":0},
        "ext":   {"label":"3rd party widget","col":4,"colspan":2,"row":0,
                  "bg":"#fff7ed","border":"#ea580c","header_bg":"#fed7aa"},
        "api":   {"label":"API","col":0,"colspan":3,"row":1},
        "auth":  {"label":"Auth","col":3,"colspan":3,"row":1,
                  "bg":"#fffbeb","border":"#b45309","header_bg":"#fde68a"},
        "cdn":   {"label":"CDN (Cloudflare)","col":0,"colspan":2,"row":2,
                  "bg":"#fff7ed","border":"#ea580c","header_bg":"#fed7aa"},
        "pg":    {"label":"Postgres","col":2,"colspan":2,"row":2},
        "ga":    {"label":"Google Analytics","col":4,"colspan":2,"row":2,
                  "bg":"#fff7ed","border":"#ea580c","header_bg":"#fed7aa"},
    },
    "nodes": {
        "web":   [["React SPA","operational"], ["pageview tracker","operational"]],
        "mobile":[["iOS app","operational"]],
        "ext":   [["embedded JS","new"]],
        "api":   [["REST","operational"], ["WS","operational"]],
        "auth":  [["OIDC","operational"]],
        "cdn":   [["edge cache","new"], ["asset bucket","new"]],
        "pg":    [["users","new"]],
        "ga":    [["events API","new"]],
    },
    "connections": [
        ["web","React SPA","api","REST","HTTPS"],
        ["mobile","iOS app","api","REST","HTTPS"],
        ["api","REST","pg","users","reads"],
        ["api","REST","auth","OIDC","verify"],
        ["web","React SPA","cdn","edge cache","static assets"],
        ["web","pageview tracker","ga","events API","direct beacon"],
        ["mobile","iOS app","cdn","asset bucket","CDN downloads"],
        ["ext","embedded JS","ga","events API","direct beacon"],
    ],
}

if __name__ == "__main__":
    out = os.path.join(HERE, "3-tier-with-sidestep.svg")
    open(out, "w").write(Diagram(config).render())
    print(f"Written: {out}")
