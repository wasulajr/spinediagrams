#!/usr/bin/env python3
"""
Example: real architecture diagram for sf-initial-setup-agent.

A 16-connection diagram covering local Python runtime, browser UI,
subprocess workers, external CLI tools, and external SaaS APIs.
Demonstrates the engine's single-spine routing under load.

Run:
    python examples/sf-initial-setup-agent.py
    open examples/sf-initial-setup-agent.svg
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skill", "scripts"))

from svg_engine import Diagram

config = {
    "title": "sf-initial-setup-agent — local runtime (v0.3.x, macOS, loopback-only; happy path never spends an Anthropic key)",
    "aspect": "16:9",
    "num_cols": 6,

    "lanes": {
        # ── TOP ROW ──────────────────────────────────────────────────────
        "browser": {
            "label": "Browser (default; 127.0.0.1 loopback)",
            "col": 0, "colspan": 2, "row": 0,
            "bg": "#f0fdfa", "border": "#0d9488", "header_bg": "#ccfbf1",
        },
        "entry": {
            "label": "Python entry (orchestrator + prereqs)",
            "col": 2, "colspan": 1, "row": 0,
        },
        "fastapi": {
            "label": "FastAPI / uvicorn (local web server)",
            "col": 3, "colspan": 2, "row": 0,
            "bg": "#f0fdf4", "border": "#16a34a", "header_bg": "#bbf7d0",
        },
        "fs": {
            "label": "Local filesystem state",
            "col": 5, "colspan": 1, "row": 0,
            "bg": "#f0f9ff", "border": "#0369a1", "header_bg": "#e0f2fe",
        },

        # ── BOTTOM ROW ───────────────────────────────────────────────────
        "retrieve": {
            "label": "Retrieve worker (subprocess; CI-runnable)",
            "col": 0, "colspan": 1, "row": 1,
            "bg": "#eff6ff", "border": "#2563eb", "header_bg": "#bfdbfe",
        },
        "trouble": {
            "label": "Troubleshooter (failure path only)",
            "col": 1, "colspan": 1, "row": 1,
            "bg": "#fffbeb", "border": "#b45309", "header_bg": "#fde68a",
        },
        "cli": {
            "label": "External CLI tools",
            "col": 2, "colspan": 1, "row": 1,
        },
        "sf": {
            "label": "Salesforce org (external SaaS)",
            "col": 3, "colspan": 2, "row": 1,
        },
        "anthropic": {
            "label": "Anthropic API (external SaaS)",
            "col": 5, "colspan": 1, "row": 1,
            "bg": "#fff7ed", "border": "#ea580c", "header_bg": "#fed7aa",
        },
    },

    "nodes": {
        "browser": [
            ["Wizard page (/)",            "operational"],
            ["Dashboard + live progress",  "operational"],
            ["Summary (/summary)",         "operational"],
            ["WebSocket client",           "operational"],
        ],
        "entry": [
            ["sf_initial_setup_agent.py", "operational"],
            ["prereqs.py (stdlib-only)",  "operational"],
        ],
        "fastapi": [
            ["uvicorn ASGI (127.0.0.1)", "operational"],
            ["web_ui.py (FastAPI)",      "operational"],
            ["Jinja2 templates",         "operational"],
            ["WebSocket endpoint",       "operational"],
        ],
        "fs": [
            ["~/.digadop-agents-env",  "operational"],
            ["~/.sf-…-config.json",     "operational"],
            ["<proj>/manifest/",        "operational"],
            ["<proj>/.5gl-sync-state",  "operational"],
        ],
        "retrieve": [
            ["retrieve_metadata.py",       "operational"],
            ["ThreadPoolExecutor × 6",     "operational"],
            ["JSON-line stderr events",    "operational"],
        ],
        "trouble": [
            ["troubleshoot.py",            "transitioning"],
            ["anthropic Python SDK",       "transitioning"],
            ["tools: run_sf, rerun_chunk", "transitioning"],
        ],
        "cli": [
            ["sf CLI v2 (Node)", "new"],
            ["jq",               "new"],
            ["Java JVM",         "new"],
        ],
        "sf": [
            ["Metadata API",         "new"],
            ["Tooling API (SOQL)",   "new"],
        ],
        "anthropic": [
            ["Claude Sonnet 4.6", "new"],
            ["messages API (HTTPS)", "new"],
        ],
    },

    "connections": [
        ["entry",   "sf_initial_setup_agent.py", "browser", "Wizard page (/)",           "opens browser"],
        ["entry",   "sf_initial_setup_agent.py", "fastapi", "uvicorn ASGI (127.0.0.1)",  "starts uvicorn (port 8765-8774)"],
        ["browser", "Wizard page (/)",           "fastapi", "web_ui.py (FastAPI)",       "HTTP GET/POST"],
        ["browser", "Dashboard + live progress", "fastapi", "WebSocket endpoint",        "WebSocket (live chunk progress)"],
        ["fastapi", "web_ui.py (FastAPI)",       "fs",      "~/.sf-…-config.json",       "config + API key"],
        ["fastapi", "web_ui.py (FastAPI)",       "fs",      "<proj>/.5gl-sync-state",    "writes after success"],
        ["retrieve", "ThreadPoolExecutor × 6",   "cli",       "sf CLI v2 (Node)",  "subprocess per chunk"],
        ["cli",      "sf CLI v2 (Node)",         "sf",        "Metadata API",      "retrieve / list metadata"],
        ["cli",      "sf CLI v2 (Node)",         "sf",        "Tooling API (SOQL)","SOQL on Folder/PackageLicense"],
        ["trouble",  "tools: run_sf, rerun_chunk","cli",      "sf CLI v2 (Node)",  "run_sf / rerun_chunk"],
        ["trouble",  "anthropic Python SDK",     "anthropic", "Claude Sonnet 4.6", "messages.create (HTTPS)"],
        ["fastapi",  "web_ui.py (FastAPI)",      "retrieve",  "retrieve_metadata.py", "spawns subprocess"],
        ["retrieve", "JSON-line stderr events",  "fastapi",   "web_ui.py (FastAPI)",  "parsed by parent → WebSocket"],
        ["fastapi",  "web_ui.py (FastAPI)",      "trouble",   "troubleshoot.py",      "spawns ONLY on chunk failure"],
        ["retrieve", "retrieve_metadata.py",     "fs",        "<proj>/manifest/",     "writes chunked manifests + logs"],
        ["entry",    "prereqs.py (stdlib-only)", "cli",       "sf CLI v2 (Node)",     "detects + offers install"],
    ],
}

if __name__ == "__main__":
    out = os.path.join(HERE, "sf-initial-setup-agent.svg")
    open(out, "w").write(Diagram(config).render())
    print(f"Written: {out}")
