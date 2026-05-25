#!/usr/bin/env python3
"""
Example: 3-tier web app architecture.

Demonstrates spinediagrams' 3-row layout — row 0 (user-facing surfaces),
row 1 (backend services), row 2 (data stores + external SaaS). 14
connections distributed across two spines (0↔1 and 1↔2) with even
spacing so no labels collide.

Run:
    python examples/3-tier-web-app.py
    open examples/3-tier-web-app.svg
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skill", "scripts"))

from svg_engine import Diagram

config = {
    "title": "3-tier web app — classic frontend / backend / data",
    "aspect": "16:9",
    "num_cols": 6,
    "lanes": {
        # Row 0 — user-facing
        "web":     {"label": "Web app",     "col": 0, "colspan": 3, "row": 0},
        "mobile":  {"label": "Mobile",      "col": 3, "colspan": 3, "row": 0},
        # Row 1 — backend services
        "api":     {"label": "API gateway", "col": 0, "colspan": 2, "row": 1},
        "auth":    {"label": "Auth svc",    "col": 2, "colspan": 2, "row": 1, "bg": "#fffbeb", "border": "#b45309", "header_bg": "#fde68a"},
        "billing": {"label": "Billing svc", "col": 4, "colspan": 2, "row": 1, "bg": "#f0fdf4", "border": "#16a34a", "header_bg": "#bbf7d0"},
        # Row 2 — data + externals
        "postgres":{"label": "Postgres",    "col": 0, "colspan": 2, "row": 2},
        "redis":   {"label": "Redis",       "col": 2, "colspan": 1, "row": 2},
        "stripe":  {"label": "Stripe",      "col": 3, "colspan": 1, "row": 2},
        "okta":    {"label": "Okta",        "col": 4, "colspan": 2, "row": 2},
    },
    "nodes": {
        "web":     [["React SPA", "operational"], ["WebSocket client", "operational"]],
        "mobile":  [["iOS app",  "operational"], ["Android app", "operational"]],
        "api":     [["REST routes", "operational"], ["WS hub", "operational"]],
        "auth":    [["Login flow", "transitioning"], ["JWT issuer", "transitioning"]],
        "billing": [["Invoicing", "operational"], ["Webhook receiver", "operational"]],
        "postgres":[["users", "new"], ["billing_events", "new"]],
        "redis":   [["session cache", "new"]],
        "stripe":  [["Charges API", "new"], ["Webhooks", "new"]],
        "okta":    [["OIDC", "new"], ["SCIM", "new"]],
    },
    "connections": [
        # row 0 ↔ row 1
        ["web",    "React SPA",        "api",     "REST routes",      "HTTPS"],
        ["web",    "WebSocket client", "api",     "WS hub",           "WSS"],
        ["mobile", "iOS app",          "api",     "REST routes",      "HTTPS"],
        ["mobile", "Android app",      "api",     "REST routes",      "HTTPS"],
        # row 1 ↔ row 1
        ["api",    "REST routes",      "auth",    "JWT issuer",       "verify JWT"],
        ["api",    "REST routes",      "billing", "Invoicing",        "forward"],
        # row 1 ↔ row 2
        ["api",    "REST routes",      "postgres","users",            "reads"],
        ["api",    "WS hub",           "redis",   "session cache",    "pub/sub"],
        ["auth",   "Login flow",       "okta",    "OIDC",             "OAuth2"],
        ["auth",   "JWT issuer",       "redis",   "session cache",    "stores claims"],
        ["billing","Invoicing",        "postgres","billing_events",   "writes"],
        ["billing","Webhook receiver", "stripe",  "Webhooks",         "verifies sigs"],
        ["billing","Invoicing",        "stripe",  "Charges API",      "POST /charges"],
        # row 2 ↔ row 2
        ["stripe", "Webhooks",         "postgres","billing_events",   "(via billing)"],
    ],
}

svg = Diagram(config).render()
out = os.path.join(HERE, "3-tier-web-app.svg")
open(out, "w").write(svg)
print(f"Written: {out}")
