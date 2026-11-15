#!/usr/bin/env python3
"""Render dark and light SVG profile panels for mrraihan29 from live GitHub data."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USERNAME = "mrraihan29"
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
WIB = timezone(timedelta(hours=7))

THEMES = {
    "dark": {
        "canvas": "#16130F",
        "card": "#1F1B16",
        "card_alt": "#26211B",
        "ink": "#F1EEE6",
        "ink_sec": "#C9C2B5",
        "ink_muted": "#9A9083",
        "line": "#3A342C",
        "grid": "#24201A",
        "oxide": "#E0675B",
        "earth": "#E3BDA9",
        "ochre": "#D4A96A",
        "sage": "#8FB58A",
        "steel": "#8AB0C9",
        "glow": "rgba(224,103,91,0.16)",
    },
    "light": {
        "canvas": "#F3F0E8",
        "card": "#FAF8F3",
        "card_alt": "#EFEAE0",
        "ink": "#171714",
        "ink_sec": "#4B4740",
        "ink_muted": "#7A7368",
        "line": "#D8D2C5",
        "grid": "#E7E2D6",
        "oxide": "#914A3B",
        "earth": "#684737",
        "ochre": "#9C794B",
        "sage": "#4B7447",
        "steel": "#3E6B89",
        "glow": "rgba(145,74,59,0.12)",
    },
}

LANG_PALETTE = {
    "Python": "steel",
    "TypeScript": "ochre",
    "Jupyter Notebook": "oxide",
    "CSS": "earth",
    "Svelte": "sage",
    "Rust": "oxide",
    "HTML": "earth",
}

FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, monospace"


def fetch_json(url: str) -> object | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-renderer",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def collect_github_metrics() -> dict:
    user = fetch_json(f"https://api.github.com/users/{USERNAME}") or {}
    repos = fetch_json(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=pushed") or []
    events = fetch_json(f"https://api.github.com/users/{USERNAME}/events/public?per_page=15") or []

    non_fork_repos = [r for r in repos if isinstance(r, dict) and not r.get("fork")]
    total_stars = sum(int(r.get("stargazers_count", 0)) for r in non_fork_repos)
    public_repos = int(user.get("public_repos") or len(non_fork_repos) or 16)

    lang_counts: Counter[str] = Counter()
    for r in non_fork_repos:
        lang = r.get("language")
        if lang:
            lang_counts[lang] += 1

    if not lang_counts:
        lang_counts = Counter({"Python": 5, "Jupyter Notebook": 3, "CSS": 3, "TypeScript": 1, "Svelte": 1})

    total_lang = sum(lang_counts.values())
    top_langs = [
        {"name": name, "count": count, "pct": round((count / total_lang) * 100)}
        for name, count in lang_counts.most_common(5)
    ]

    latest_repo = non_fork_repos[0]["name"] if non_fork_repos else "naobi-sdlc"
    latest_push_raw = non_fork_repos[0].get("pushed_at", "") if non_fork_repos else ""
    latest_event_type = "Push"
    latest_event_repo = latest_repo
    ship_events = {"PushEvent", "CreateEvent", "PullRequestEvent", "ReleaseEvent"}
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") in ship_events and ev.get("repo", {}).get("name"):
            latest_event_type = ev.get("type", "PushEvent").replace("Event", "")
            latest_event_repo = ev["repo"]["name"].split("/")[-1]
            latest_push_raw = ev.get("created_at") or latest_push_raw
            break

    now_wib = datetime.now(WIB)
    last_push_label = latest_push_raw[:10] if latest_push_raw else now_wib.strftime("%Y-%m-%d")

    return {
        "public_repos": public_repos,
        "total_stars": total_stars,
        "followers": int(user.get("followers") or 2),
        "top_langs": top_langs,
        "latest_repo": latest_event_repo,
        "latest_action": latest_event_type,
        "last_push": last_push_label,
        "updated_wib": now_wib.strftime("%Y-%m-%d %H:%M WIB"),
    }


def svg_header(width: int, height: int, title: str, t: dict[str, str]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <title>{escape(title)}</title>
  <style>
    .sans {{ font-family: {FONT_SANS}; }}
    .mono {{ font-family: {FONT_MONO}; }}
    .pulse {{ animation: pulse 2.8s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }}
    .spin {{ animation: spin 24s linear infinite; transform-box: fill-box; transform-origin: center; }}
    .sweep {{ animation: sweep 5.5s ease-in-out infinite; }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.45; transform: scale(1.35); }}
    }}
    @keyframes spin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes sweep {{
      0% {{ stroke-dashoffset: 320; }}
      50% {{ stroke-dashoffset: 0; }}
      100% {{ stroke-dashoffset: -320; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .pulse, .spin, .sweep {{ animation: none; }}
    }}
  </style>
  <defs>
    <pattern id="bp-grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{t['grid']}" stroke-width="1"/>
    </pattern>
    <linearGradient id="oxide-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{t['oxide']}"/>
      <stop offset="100%" stop-color="{t['ochre']}"/>
    </linearGradient>
    <linearGradient id="curve-fill" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{t['oxide']}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{t['oxide']}" stop-opacity="0.0"/>
    </linearGradient>
  </defs>"""


def render_hero(t: dict[str, str], m: dict) -> str:
    w, h = 900, 260
    parts = [
        svg_header(w, h, "Raihan (mrraihan29) - NAOBI Engineering Blueprint", t),
        f'  <rect width="{w}" height="{h}" rx="16" fill="{t["canvas"]}" stroke="{t["line"]}" stroke-width="1.2"/>',
        f'  <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="15" fill="url(#bp-grid)"/>',
        # Corner registration ticks
        f'  <path d="M 20 34 L 20 20 L 34 20 M {w-34} 20 L {w-20} 20 L {w-20} 34 M 20 {h-34} L 20 {h-20} L 34 {h-20} M {w-34} {h-20} L {w-20} {h-20} L {w-20} {h-34}" fill="none" stroke="{t["oxide"]}" stroke-width="1.5" opacity="0.75"/>',
        # Top status strip
        f'  <text x="42" y="46" class="mono" font-size="11" fill="{t["ink_muted"]}" letter-spacing="1.6">SPEC 00 // ENGINEERING TELEMETRY</text>',
        f'  <rect x="650" y="29" width="208" height="24" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <circle cx="667" cy="41" r="4" fill="{t["oxide"]}" class="pulse"/>',
        f'  <text x="680" y="45" class="mono" font-size="10.5" fill="{t["ink_sec"]}">BUILDING AT NAOBI · UTC+7</text>',
        # Identity headline
        f'  <text x="42" y="102" class="sans" font-size="38" font-weight="700" fill="{t["ink"]}" letter-spacing="-0.8">Raihan</text>',
        f'  <text x="192" y="102" class="mono" font-size="16" font-weight="500" fill="{t["oxide"]}">@mrraihan29</text>',
        f'  <text x="42" y="132" class="sans" font-size="15.5" font-weight="600" fill="{t["ink_sec"]}">Systems &amp; Applied ML Engineer</text>',
        f'  <text x="42" y="154" class="sans" font-size="14" fill="{t["ink_muted"]}">Crafting agentic tooling, probabilistic models &amp; resilient web software.</text>',
        # Accent divider + waveform
        f'  <line x1="42" y1="174" x2="640" y2="174" stroke="{t["line"]}" stroke-width="1"/>',
        f'  <path d="M 42 174 L 190 174 L 204 162 L 216 184 L 228 168 L 238 174 L 640 174" fill="none" stroke="url(#oxide-grad)" stroke-width="1.8" stroke-dasharray="160 160" class="sweep"/>',
        # Pill metadata row
        f'  <rect x="42" y="194" width="134" height="30" rx="8" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="56" y="213" class="mono" font-size="11.5" fill="{t["earth"]}">web // naobi.dev</text>',
        f'  <rect x="186" y="194" width="172" height="30" rx="8" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="200" y="213" class="mono" font-size="11.5" fill="{t["ink_sec"]}">focus // Agentic SDLC</text>',
        f'  <rect x="368" y="194" width="154" height="30" rx="8" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="382" y="213" class="mono" font-size="11.5" fill="{t["ink_sec"]}">ml // Bayesian RUL</text>',
        # Right-side orbital telemetry radar
        f'  <g transform="translate(762, 146)">',
        f'    <circle r="68" fill="{t["card"]}" stroke="{t["line"]}" stroke-width="1.2"/>',
        f'    <circle r="48" fill="none" stroke="{t["line"]}" stroke-dasharray="3 4" stroke-width="1"/>',
        f'    <circle r="28" fill="none" stroke="{t["oxide"]}" stroke-opacity="0.4" stroke-width="1"/>',
        f'    <line x1="-68" y1="0" x2="68" y2="0" stroke="{t["line"]}" stroke-width="1"/>',
        f'    <line x1="0" y1="-68" x2="0" y2="68" stroke="{t["line"]}" stroke-width="1"/>',
        f'    <g class="spin">',
        f'      <line x1="0" y1="0" x2="46" y2="-46" stroke="{t["oxide"]}" stroke-width="1.8"/>',
        f'      <circle cx="46" cy="-46" r="3.5" fill="{t["oxide"]}"/>',
        f'      <circle cx="-32" cy="24" r="2.5" fill="{t["ochre"]}"/>',
        f'    </g>',
        f'    <circle r="5.5" fill="{t["canvas"]}" stroke="{t["oxide"]}" stroke-width="2"/>',
        f'    <text x="0" y="88" text-anchor="middle" class="mono" font-size="10" fill="{t["ink_muted"]}">{m["public_repos"]} REPOS · {m["total_stars"]} STARS</text>',
        f'  </g>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_blueprint(t: dict[str, str]) -> str:
    w, h = 900, 350
    parts = [
        svg_header(w, h, "Engineering Blueprint - NAOBI & Applied ML", t),
        f'  <rect width="{w}" height="{h}" rx="16" fill="{t["canvas"]}" stroke="{t["line"]}" stroke-width="1.2"/>',
        f'  <text x="32" y="36" class="mono" font-size="11" fill="{t["ink_muted"]}" letter-spacing="1.6">SPEC 01 // ACTIVE ARCHITECTURE &amp; RESEARCH PILLARS</text>',
        # Left Card: NAOBI & Agentic Tooling
        f'  <rect x="28" y="54" width="412" height="270" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="48" y="82" class="mono" font-size="11" fill="{t["oxide"]}">01 // NAOBI &amp; AGENTIC TOOLING</text>',
        f'  <text x="48" y="106" class="sans" font-size="19" font-weight="700" fill="{t["ink"]}">Spec-Driven AI Systems</text>',
        # Schematic node graph
        f'  <line x1="98" y1="146" x2="218" y2="146" stroke="{t["line"]}" stroke-width="1.5"/>',
        f'  <line x1="252" y1="146" x2="366" y2="146" stroke="{t["line"]}" stroke-width="1.5"/>',
        f'  <path d="M 98 146 L 366 146" fill="none" stroke="url(#oxide-grad)" stroke-width="1.6" stroke-dasharray="140 140" class="sweep"/>',
        f'  <rect x="48" y="128" width="96" height="36" rx="8" fill="{t["card_alt"]}" stroke="{t["oxide"]}"/>',
        f'  <text x="96" y="150" text-anchor="middle" class="mono" font-size="11" fill="{t["ink"]}">naobi.dev</text>',
        f'  <rect x="186" y="128" width="102" height="36" rx="8" fill="{t["card_alt"]}" stroke="{t["ochre"]}"/>',
        f'  <text x="237" y="150" text-anchor="middle" class="mono" font-size="11" fill="{t["ink"]}">naobi-sdlc</text>',
        f'  <rect x="326" y="128" width="96" height="36" rx="8" fill="{t["card_alt"]}" stroke="{t["steel"]}"/>',
        f'  <text x="374" y="150" text-anchor="middle" class="mono" font-size="11" fill="{t["ink"]}">personal_os</text>',
        # Rows
        f'  <circle cx="56" cy="198" r="3.5" fill="{t["oxide"]}"/>',
        f'  <text x="70" y="202" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">naobi.dev</text>',
        f'  <text x="172" y="202" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Engineering studio &amp; digital garden</text>',
        f'  <circle cx="56" cy="234" r="3.5" fill="{t["ochre"]}"/>',
        f'  <text x="70" y="238" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">naobi-sdlc</text>',
        f'  <text x="172" y="238" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Phase-gated SDLC plugin for agents</text>',
        f'  <circle cx="56" cy="270" r="3.5" fill="{t["steel"]}"/>',
        f'  <text x="70" y="274" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">personal_os</text>',
        f'  <text x="172" y="274" class="sans" font-size="12.5" fill="{t["ink_sec"]}">TypeScript personal workspace engine</text>',
        f'  <text x="48" y="306" class="mono" font-size="10.5" fill="{t["ink_muted"]}">STACK: TypeScript · Python · Rust · MCP</text>',
        # Right Card: AI, ML & Reliability Engineering
        f'  <rect x="460" y="54" width="412" height="270" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="480" y="82" class="mono" font-size="11" fill="{t["oxide"]}">02 // AI, ML &amp; RELIABILITY</text>',
        f'  <text x="480" y="106" class="sans" font-size="19" font-weight="700" fill="{t["ink"]}">Probabilistic &amp; Sensor ML</text>',
        # Reliability curve plot
        f'  <rect x="480" y="122" width="372" height="56" rx="8" fill="{t["card_alt"]}" stroke="{t["line"]}"/>',
        f'  <path d="M 494 134 C 570 135, 620 144, 675 156 C 730 166, 780 170, 838 171 L 838 176 L 494 176 Z" fill="url(#curve-fill)"/>',
        f'  <path d="M 494 134 C 570 135, 620 144, 675 156 C 730 166, 780 170, 838 171" fill="none" stroke="{t["oxide"]}" stroke-width="2"/>',
        f'  <circle cx="675" cy="156" r="4" fill="{t["ochre"]}" class="pulse"/>',
        f'  <text x="762" y="140" class="mono" font-size="10" fill="{t["ink_muted"]}">P(RUL | y)</text>',
        # Rows
        f'  <circle cx="488" cy="198" r="3.5" fill="{t["oxide"]}"/>',
        f'  <text x="502" y="202" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">Bayesian_RUL</text>',
        f'  <text x="626" y="202" class="sans" font-size="12.5" fill="{t["ink_sec"]}">RP-001 reliability &amp; survival evidence</text>',
        f'  <circle cx="488" cy="234" r="3.5" fill="{t["sage"]}"/>',
        f'  <text x="502" y="238" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">OilFilterMonitor</text>',
        f'  <text x="626" y="238" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Predictive sensor diagnostics (ML)</text>',
        f'  <circle cx="488" cy="270" r="3.5" fill="{t["ochre"]}"/>',
        f'  <text x="502" y="274" class="mono" font-size="12" font-weight="600" fill="{t["ink"]}">Quant &amp; NN_Core</text>',
        f'  <text x="626" y="274" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Portfolio math &amp; neural nets from scratch</text>',
        f'  <text x="480" y="306" class="mono" font-size="10.5" fill="{t["ink_muted"]}">STACK: PyTorch · SciPy · Scikit-Learn · Jupyter</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_telemetry(t: dict[str, str], m: dict) -> str:
    w, h = 900, 210
    langs = m["top_langs"]
    bar_x, bar_y, bar_w, bar_h = 42, 92, 340, 12

    bar_segments = []
    legend_items = []
    cur_x = float(bar_x)
    total_pct = sum(item["pct"] for item in langs) or 100
    for idx, item in enumerate(langs):
        color_key = LANG_PALETTE.get(item["name"], "earth")
        color = t[color_key]
        seg_w = (item["pct"] / total_pct) * bar_w
        if idx == len(langs) - 1:
            seg_w = max(0.0, (bar_x + bar_w) - cur_x)
        bar_segments.append(
            f'  <rect x="{cur_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}"/>'
        )
        cur_x += seg_w

        col = idx % 2
        row = idx // 2
        lx = 46 + col * 186
        ly = 128 + row * 22
        label = "Jupyter" if item["name"] == "Jupyter Notebook" else item["name"]
        legend_items.append(
            f'  <circle cx="{lx}" cy="{ly - 4}" r="4" fill="{color}"/>\n'
            f'  <text x="{lx + 12}" y="{ly}" class="mono" font-size="11.5" fill="{t["ink_sec"]}">{escape(label)} ({item["pct"]}%)</text>'
        )

    parts = [
        svg_header(w, h, "Live GitHub Telemetry HUD", t),
        f'  <rect width="{w}" height="{h}" rx="16" fill="{t["canvas"]}" stroke="{t["line"]}" stroke-width="1.2"/>',
        f'  <text x="42" y="36" class="mono" font-size="11" fill="{t["ink_muted"]}" letter-spacing="1.6">SPEC 02 // LIVE REPOSITORY TELEMETRY (AUTO-SYNCED)</text>',
        f'  <text x="858" y="36" text-anchor="end" class="mono" font-size="10.5" fill="{t["ink_muted"]}">SYNC: {escape(m["updated_wib"])}</text>',
        # Column 1: Language distribution
        f'  <text x="42" y="74" class="sans" font-size="15" font-weight="700" fill="{t["ink"]}">Primary Stack Footprint</text>',
        f'  <clipPath id="bar-clip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6"/></clipPath>',
        '  <g clip-path="url(#bar-clip)">',
        *bar_segments,
        "  </g>",
        *legend_items,
        # Divider
        f'  <line x1="420" y1="56" x2="420" y2="184" stroke="{t["line"]}" stroke-width="1"/>',
        # Column 2: Snapshot counters
        f'  <rect x="444" y="60" width="184" height="58" rx="10" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="460" y="81" class="mono" font-size="10.5" fill="{t["ink_muted"]}">PUBLIC REPOS</text>',
        f'  <text x="460" y="106" class="mono" font-size="22" font-weight="700" fill="{t["ink"]}">{m["public_repos"]}</text>',
        f'  <rect x="444" y="128" width="184" height="58" rx="10" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <text x="460" y="149" class="mono" font-size="10.5" fill="{t["ink_muted"]}">STARS · FOLLOWERS</text>',
        f'  <text x="460" y="174" class="mono" font-size="18" font-weight="700" fill="{t["earth"]}">{m["total_stars"]} stars · {m["followers"]}</text>',
        # Column 3: Latest Shipped Signal
        f'  <rect x="646" y="60" width="212" height="126" rx="10" fill="{t["card"]}" stroke="{t["line"]}"/>',
        f'  <circle cx="664" cy="82" r="4" fill="{t["sage"]}" class="pulse"/>',
        f'  <text x="676" y="86" class="mono" font-size="10.5" fill="{t["sage"]}">LATEST SIGNAL</text>',
        f'  <text x="662" y="118" class="mono" font-size="13.5" font-weight="700" fill="{t["ink"]}">{escape(m["latest_repo"][:22])}</text>',
        f'  <text x="662" y="142" class="mono" font-size="11.5" fill="{t["ink_sec"]}">event // {escape(m["latest_action"])}</text>',
        f'  <text x="662" y="166" class="mono" font-size="11" fill="{t["ink_muted"]}">date  // {escape(m["last_push"])}</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = collect_github_metrics()

    for theme_name, palette in THEMES.items():
        (ASSETS_DIR / f"hero-{theme_name}.svg").write_text(render_hero(palette, metrics), encoding="utf-8")
        (ASSETS_DIR / f"blueprint-{theme_name}.svg").write_text(render_blueprint(palette), encoding="utf-8")
        (ASSETS_DIR / f"telemetry-{theme_name}.svg").write_text(render_telemetry(palette, metrics), encoding="utf-8")

    print(f"Rendered 6 SVGs into {ASSETS_DIR} (repos={metrics['public_repos']}, latest={metrics['latest_repo']})")


if __name__ == "__main__":
    main()
