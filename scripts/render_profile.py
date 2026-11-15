#!/usr/bin/env python3
"""Render dark and light NAOBI-aligned SVG folio panels for mrraihan29."""

from __future__ import annotations

import json
import math
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
KYU_PATH = Path(__file__).resolve().parent / "kyu_fragment.xml"
WIB = timezone(timedelta(hours=7))

THEMES = {
    "dark": {
        "canvas": "#16130F",
        "raised": "#1F1B16",
        "ink": "#F1EEE6",
        "ink_sec": "#C9C2B5",
        "ink_muted": "#9A9083",
        "rule": "#3A342C",
        "grid": "#2C2721",
        "oxide": "#E0675B",
        "earth": "#E3BDA9",
        "ochre": "#C9A464",
        "sage": "#9FAA86",
        "steel": "#8AB0C9",
    },
    "light": {
        "canvas": "#F3F0E8",
        "raised": "#F9F7F1",
        "ink": "#171714",
        "ink_sec": "#393732",
        "ink_muted": "#6D6A63",
        "rule": "#D9D3C7",
        "grid": "#DED7C9",
        "oxide": "#914A3B",
        "earth": "#6E3B2C",
        "ochre": "#9C794B",
        "sage": "#5D7253",
        "steel": "#4A6B82",
    },
}

LANG_PALETTE = {
    "Python": "earth",
    "TypeScript": "steel",
    "Jupyter Notebook": "ochre",
    "CSS": "sage",
    "Svelte": "oxide",
    "Rust": "oxide",
    "HTML": "ochre",
}

FONT_SERIF = "'Newsreader', 'Spectral', Georgia, 'Times New Roman', serif"
FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, monospace"
FONT_KANJI = "'Naobi Mincho', 'Yu Mincho', 'Hiragino Mincho ProN', 'Noto Serif JP', Georgia, serif"


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
    events = fetch_json(f"https://api.github.com/users/{USERNAME}/events/public?per_page=20") or []

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


def smoothstep(a: float, b: float, x: float) -> float:
    x = min(1.0, max(0.0, (x - a) / (b - a)))
    return x * x * (3.0 - 2.0 * x)


def generate_brush_ribbons(variant: str, x0: float, y0: float, width: float) -> str:
    """Port of naobi.dev BrushAccent.astro dry-ink ribbon stroke geometry."""
    closing = variant == "closing"
    amp = 15.0 if closing else 3.2
    half0 = 26.0 if closing else 4.2
    count = 12 if closing else 8
    seed = 1457 if closing else 2789

    def rand() -> float:
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296.0

    def point(k: float) -> tuple[float, float, float, float]:
        phase = k * 2.6 + 0.4
        slope = amp * 2.6 * math.cos(phase) / width
        length = math.hypot(1.0, slope)
        return (x0 + k * width, y0 + amp * math.sin(phase), -slope / length, 1.0 / length)

    paths = []
    steps = 120
    for r in range(count):
        offset = -1.0 + (2.0 * r + 1.0) / count
        hw = (1.0 / count) * (0.85 + rand() * 0.5)
        end = 1.0 - 0.26 * rand() * (0.4 + 0.6 * abs(offset))
        pts_a: list[str] = []
        pts_b: list[str] = []
        for i in range(steps + 1):
            k = (i / steps) * end
            px, py, nx, ny = point(k)
            sh = 1.0 - 0.65 * smoothstep(0.35 if closing else 0.4, 1.0, k) * 0.95
            tail = max(0.0, (k - 0.72) / 0.28)
            w = half0 * (0.3 + 0.7 * smoothstep(0.0, 0.05, k)) * (1.0 - 0.85 * (tail ** 1.2))
            a = w * (offset + hw * sh)
            b = w * (offset - hw * sh)
            pts_a.append(f"{px + nx * a:.1f} {py + ny * a:.1f}")
            pts_b.append(f"{px + nx * b:.1f} {py + ny * b:.1f}")
        d = "M" + "L".join(pts_a) + "L" + "L".join(reversed(pts_b)) + "Z"
        op = 0.50 + rand() * 0.42
        paths.append(f'<path d="{d}" fill-opacity="{op:.2f}"/>')
    return "\n    ".join(paths)


def render_hanko_seal(x: float, y: float, t: dict[str, str], scale: float = 1.0) -> str:
    return f"""  <g transform="translate({x}, {y}) rotate(-3) scale({scale})">
    <rect x="0" y="0" width="24" height="44" rx="2" fill="{t['oxide']}"/>
    <text x="12" y="19" text-anchor="middle" class="kanji" font-size="14" fill="{t['canvas']}">直</text>
    <text x="12" y="36" text-anchor="middle" class="kanji" font-size="14" fill="{t['canvas']}">毘</text>
  </g>"""


def svg_open(width: int, height: int, title: str, t: dict[str, str]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <title>{escape(title)}</title>
  <style>
    .serif {{ font-family: {FONT_SERIF}; }}
    .sans {{ font-family: {FONT_SANS}; }}
    .mono {{ font-family: {FONT_MONO}; }}
    .kanji {{ font-family: {FONT_KANJI}; }}
    .ink-breathe {{ animation: inkBreathe 6s ease-in-out infinite; }}
    @keyframes inkBreathe {{
      0%, 100% {{ opacity: 0.94; }}
      50% {{ opacity: 0.78; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .ink-breathe {{ animation: none; opacity: 0.92; }}
    }}
  </style>"""


def render_hero(t: dict[str, str]) -> str:
    w, h = 900, 300
    kyu_markup = KYU_PATH.read_text(encoding="utf-8") if KYU_PATH.exists() else ""
    parts = [
        svg_open(w, h, "Raihan (@mrraihan29) — Careful AI and systems for engineers at NAOBI", t),
        f'  <rect width="{w}" height="{h}" rx="4" fill="{t["canvas"]}" stroke="{t["rule"]}" stroke-width="1"/>',
        # Left editorial column
        f'  <text x="48" y="48" class="mono" font-size="11.5" fill="{t["earth"]}">naobi.dev</text>',
        f'  <text x="48" y="108" class="serif" font-size="50" font-weight="500" fill="{t["ink"]}" letter-spacing="-0.8">Raihan</text>',
        f'  <text x="218" y="108" class="mono" font-size="15" fill="{t["ink_muted"]}">@mrraihan29</text>',
        f'  <text x="48" y="148" class="serif" font-size="22" font-weight="400" fill="{t["ink"]}">Careful AI and resilient systems for engineers.</text>',
        f'  <text x="48" y="180" class="sans" font-size="14.5" fill="{t["ink_sec"]}">Research, agentic workflows, and cost estimating at NAOBI.</text>',
        f'  <text x="48" y="202" class="sans" font-size="14.5" fill="{t["ink_sec"]}">AI helps organise technical evidence; calculations stay inspectable.</text>',
        # Hairline footer strip on left
        f'  <line x1="48" y1="234" x2="528" y2="234" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="48" y="258" class="sans" font-size="13" font-weight="500" fill="{t["earth"]}">Engineer at NAOBI</text>',
        f'  <line x1="176" y1="246" x2="176" y2="262" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="192" y="258" class="sans" font-size="13" fill="{t["ink_muted"]}">Jakarta (UTC+7)</text>',
        f'  <line x1="308" y1="246" x2="308" y2="262" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="324" y="258" class="sans" font-size="12.5" fill="{t["ink_muted"]}">Research, systems &amp; ML</text>',
        # Right calligraphy field (mirroring naobi.dev KanjiField)
        f'  <line x1="576" y1="36" x2="852" y2="36" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="576" y="54" class="mono" font-size="11" fill="{t["ink_muted"]}">直毘 / Open inquiry</text>',
        f'  <g transform="translate(616, 62) scale(1.56)" color="{t["ink"]}" class="ink-breathe">',
        f'    {kyu_markup}',
        f'  </g>',
        render_hanko_seal(824, 68, t, scale=0.95),
        f'  <line x1="576" y1="242" x2="852" y2="242" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="576" y="262" class="sans" font-size="12.5" font-weight="500" fill="{t["ink"]}">究 Research</text>',
        f'  <text x="654" y="262" class="sans" font-size="12.5" fill="{t["ink_muted"]}">— questions worth understanding.</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_folio(t: dict[str, str]) -> str:
    w, h = 900, 380
    brush = generate_brush_ribbons("divider", 48.0, 74.0, 804.0)
    parts = [
        svg_open(w, h, "Selected work and active engineering research", t),
        f'  <rect width="{w}" height="{h}" rx="4" fill="{t["canvas"]}" stroke="{t["rule"]}" stroke-width="1"/>',
        # Section heading
        f'  <text x="48" y="52" class="serif" font-size="26" font-weight="500" fill="{t["ink"]}" letter-spacing="-0.4">Selected work</text>',
        f'  <text x="852" y="52" text-anchor="end" class="sans" font-size="13" fill="{t["ink_muted"]}">First product, agentic tooling, and reliability research</text>',
        # Organic dry-brush divider (from BrushAccent.astro)
        f'  <g fill="{t["ink"]}" opacity="0.72">',
        f'    {brush}',
        f'  </g>',
        # Vertical hairline separating the two editorial columns (no nested boxes)
        f'  <line x1="450" y1="104" x2="450" y2="342" stroke="{t["rule"]}" stroke-width="1"/>',
        # Left column: NAOBI & engineering systems
        f'  <text x="48" y="122" class="serif" font-size="19" font-weight="500" fill="{t["ink"]}">NAOBI &amp; engineering systems</text>',
        f'  <line x1="48" y1="136" x2="418" y2="136" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="48" y="164" class="sans" font-size="14" font-weight="600" fill="{t["earth"]}">AI cost estimating</text>',
        f'  <text x="418" y="164" text-anchor="end" class="mono" font-size="11" fill="{t["oxide"]}">first product</text>',
        f'  <text x="48" y="185" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Traceable price evidence, CAPEX options &amp; Excel export.</text>',
        f'  <text x="48" y="203" class="sans" font-size="12.5" fill="{t["ink_muted"]}">It proposes; the estimator approves.</text>',
        f'  <line x1="48" y1="220" x2="418" y2="220" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="48" y="246" class="mono" font-size="13.5" font-weight="600" fill="{t["ink"]}">naobi-sdlc</text>',
        f'  <text x="418" y="246" text-anchor="end" class="mono" font-size="11" fill="{t["ink_muted"]}">Python</text>',
        f'  <text x="48" y="267" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Phase-gated SDLC workflow plugin keeping agent edits inspectable.</text>',
        f'  <line x1="48" y1="284" x2="418" y2="284" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="48" y="310" class="mono" font-size="13.5" font-weight="600" fill="{t["ink"]}">personal_os</text>',
        f'  <text x="418" y="310" text-anchor="end" class="mono" font-size="11" fill="{t["ink_muted"]}">TypeScript</text>',
        f'  <text x="48" y="331" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Local-first workspace environment and operational tooling.</text>',
        # Right column: Probabilistic ML & reliability
        f'  <text x="482" y="122" class="serif" font-size="19" font-weight="500" fill="{t["ink"]}">Probabilistic ML &amp; reliability</text>',
        f'  <line x1="482" y1="136" x2="852" y2="136" stroke="{t["rule"]}" stroke-width="1"/>',
        # Exact analytical survival figure (L-axes + gridlines, no rounded card)
        f'  <g transform="translate(482, 148)">',
        f'    <line x1="0" y1="16" x2="370" y2="16" stroke="{t["grid"]}" stroke-width="1"/>',
        f'    <line x1="0" y1="32" x2="370" y2="32" stroke="{t["grid"]}" stroke-width="1"/>',
        f'    <line x1="123" y1="0" x2="123" y2="48" stroke="{t["grid"]}" stroke-width="1"/>',
        f'    <line x1="246" y1="0" x2="246" y2="48" stroke="{t["grid"]}" stroke-width="1"/>',
        f'    <line x1="0" y1="0" x2="0" y2="48" stroke="{t["rule"]}" stroke-width="1.2"/>',
        f'    <line x1="0" y1="48" x2="370" y2="48" stroke="{t["rule"]}" stroke-width="1.2"/>',
        f'    <path d="M 0 6 C 78 7, 132 16, 188 28 C 244 39, 300 43, 368 44" fill="none" stroke="{t["earth"]}" stroke-width="1.8"/>',
        f'    <path d="M 0 11 C 84 13, 138 24, 196 35 C 250 43, 304 45, 368 46" fill="none" stroke="{t["oxide"]}" stroke-width="1.4" stroke-dasharray="4 3"/>',
        f'    <text x="370" y="11" text-anchor="end" class="mono" font-size="10.5" fill="{t["ink_muted"]}">P(RUL | y), C-MAPSS</text>',
        f'  </g>',
        f'  <text x="482" y="220" class="mono" font-size="13" font-weight="600" fill="{t["ink"]}">RP-001_Bayesian_RUL_Reliability</text>',
        f'  <text x="852" y="220" text-anchor="end" class="mono" font-size="11" fill="{t["ink_muted"]}">Python</text>',
        f'  <text x="482" y="241" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Interval quality vs. decision quality for remaining useful life.</text>',
        f'  <line x1="482" y1="258" x2="852" y2="258" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="482" y="284" class="mono" font-size="13" font-weight="600" fill="{t["ink"]}">OilFilterMonitoringSystem</text>',
        f'  <text x="852" y="284" text-anchor="end" class="mono" font-size="11" fill="{t["ink_muted"]}">Jupyter</text>',
        f'  <text x="482" y="305" class="sans" font-size="12.5" fill="{t["ink_sec"]}">Predictive maintenance diagnostics from sensor telemetry.</text>',
        f'  <line x1="482" y1="322" x2="852" y2="322" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="482" y="346" class="mono" font-size="12.5" fill="{t["earth"]}">quant-portfolio-analysis, NN_From_Scratch</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_ledger(t: dict[str, str], m: dict) -> str:
    w, h = 900, 196
    langs = m["top_langs"]
    bar_x, bar_y, bar_w, bar_h = 48, 92, 360, 8

    bar_segments = []
    legend_items = []
    cur_x = float(bar_x)
    total_pct = sum(item["pct"] for item in langs) or 100
    for idx, item in enumerate(langs):
        color = t[LANG_PALETTE.get(item["name"], "earth")]
        seg_w = (item["pct"] / total_pct) * bar_w
        if idx == len(langs) - 1:
            seg_w = max(0.0, (bar_x + bar_w) - cur_x)
        bar_segments.append(
            f'  <rect x="{cur_x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}"/>'
        )
        cur_x += seg_w

        col = idx % 2
        row = idx // 2
        lx = 48 + col * 188
        ly = 124 + row * 21
        label = "Jupyter" if item["name"] == "Jupyter Notebook" else item["name"]
        legend_items.append(
            f'  <rect x="{lx}" y="{ly - 8}" width="8" height="8" rx="1" fill="{color}"/>\n'
            f'  <text x="{lx + 14}" y="{ly}" class="mono" font-size="11.5" fill="{t["ink_sec"]}">{escape(label)} ({item["pct"]}%)</text>'
        )

    parts = [
        svg_open(w, h, "Live GitHub repository ledger", t),
        f'  <rect width="{w}" height="{h}" rx="4" fill="{t["canvas"]}" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="48" y="42" class="serif" font-size="22" font-weight="500" fill="{t["ink"]}">Repository ledger</text>',
        f'  <text x="852" y="42" text-anchor="end" class="mono" font-size="11" fill="{t["ink_muted"]}">Synced {escape(m["updated_wib"])}</text>',
        f'  <line x1="48" y1="58" x2="852" y2="58" stroke="{t["rule"]}" stroke-width="1"/>',
        # Left: Language share
        f'  <text x="48" y="79" class="sans" font-size="13" font-weight="500" fill="{t["ink_sec"]}">Languages across non-fork repositories</text>',
        f'  <clipPath id="bar-clip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="2"/></clipPath>',
        '  <g clip-path="url(#bar-clip)">',
        *bar_segments,
        "  </g>",
        *legend_items,
        # Tabular vertical hairlines (no nested cards)
        f'  <line x1="444" y1="74" x2="444" y2="168" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="466" y="88" class="sans" font-size="12.5" fill="{t["ink_muted"]}">Public repositories</text>',
        f'  <text x="466" y="122" class="serif" font-size="32" font-weight="500" fill="{t["ink"]}">{m["public_repos"]}</text>',
        f'  <text x="466" y="152" class="sans" font-size="12" fill="{t["ink_muted"]}">{m["total_stars"]} stars, {m["followers"]} followers</text>',
        f'  <line x1="620" y1="74" x2="620" y2="168" stroke="{t["rule"]}" stroke-width="1"/>',
        f'  <text x="642" y="88" class="sans" font-size="12.5" fill="{t["ink_muted"]}">Latest repository activity</text>',
        f'  <text x="642" y="120" class="mono" font-size="15.5" font-weight="600" fill="{t["earth"]}">{escape(m["latest_repo"][:22])}</text>',
        f'  <text x="642" y="144" class="sans" font-size="12.5" fill="{t["ink_sec"]}">{escape(m["latest_action"])} on {escape(m["last_push"])}</text>',
        f'  <text x="642" y="164" class="sans" font-size="11.5" fill="{t["ink_muted"]}">Updated daily via GitHub Actions</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def render_closing(t: dict[str, str]) -> str:
    w, h = 900, 144
    brush = generate_brush_ribbons("closing", 48.0, 74.0, 804.0)
    parts = [
        svg_open(w, h, "Room to think. Work you can check. — naobi.dev", t),
        f'  <rect width="{w}" height="{h}" rx="4" fill="{t["canvas"]}" stroke="{t["rule"]}" stroke-width="1"/>',
        # Soft translucent brush wash (matching naobi.dev home-close)
        f'  <g fill="{t["ink"]}" opacity="0.14">',
        f'    {brush}',
        f'  </g>',
        f'  <text x="822" y="126" text-anchor="end" class="kanji" font-size="118" fill="{t["ink"]}" opacity="0.04">毘</text>',
        f'  <text x="450" y="64" text-anchor="middle" class="serif" font-size="28" font-weight="500" fill="{t["ink"]}" letter-spacing="-0.4">Room to think.</text>',
        f'  <text x="450" y="98" text-anchor="middle" class="serif" font-size="28" font-weight="500" fill="{t["ink"]}" letter-spacing="-0.4">Work you can check.</text>',
        f'  <text x="450" y="124" text-anchor="middle" class="mono" font-size="11.5" fill="{t["earth"]}">naobi.dev</text>',
        render_hanko_seal(840, 26, t, scale=0.85),
        "</svg>",
    ]
    return "\n".join(parts)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = collect_github_metrics()

    for theme_name, palette in THEMES.items():
        (ASSETS_DIR / f"hero-{theme_name}.svg").write_text(render_hero(palette), encoding="utf-8")
        (ASSETS_DIR / f"folio-{theme_name}.svg").write_text(render_folio(palette), encoding="utf-8")
        (ASSETS_DIR / f"ledger-{theme_name}.svg").write_text(render_ledger(palette, metrics), encoding="utf-8")
        (ASSETS_DIR / f"closing-{theme_name}.svg").write_text(render_closing(palette), encoding="utf-8")

    print(f"Rendered 8 NAOBI folio SVGs into {ASSETS_DIR} (repos={metrics['public_repos']}, latest={metrics['latest_repo']})")


if __name__ == "__main__":
    main()
