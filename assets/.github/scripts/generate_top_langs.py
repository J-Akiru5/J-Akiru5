#!/usr/bin/env python3
"""
Regenerates assets/top-langs.svg from real GitHub repo language data.
Standard library only. Auth: GH_TOKEN (workflow's GITHUB_TOKEN) for a
5000/hr rate limit instead of the 60/hr unauthenticated ceiling.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GH_USERNAME", "J-Akiru5")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "assets/top-langs.svg")

API = "https://api.github.com"

LANG_COLORS = {
    "TypeScript": "#3178C6", "JavaScript": "#E9D65B", "Python": "#22D3EE",
    "PHP": "#8B7BFF", "HTML": "#5CB4F5", "CSS": "#8B98A5", "Dart": "#34D399",
    "C++": "#F97316", "Vue": "#41B883", "Blade": "#F97316", "Swift": "#F97316",
}
DEFAULT_COLOR = "#8B98A5"


def gh_get(path):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_all_repos(login):
    repos, page = [], 1
    while True:
        batch = gh_get(f"/users/{login}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_languages(login, repo):
    return gh_get(f"/repos/{login}/{repo}/languages")


def build_svg(lang_totals, generated_at, repo_count):
    total = sum(lang_totals.values())
    top = sorted(lang_totals.items(), key=lambda x: -x[1])[:8]

    W, H = 1400, 120 + 36 * len(top)
    bar_area_w = 640
    max_bytes = top[0][1] if top else 1
    rows = []
    y0 = 100
    for i, (name, b) in enumerate(top):
        y = y0 + i * 36
        w = 60 + (bar_area_w - 60) * (b / max_bytes)
        pct = 100 * b / total if total else 0
        color = LANG_COLORS.get(name, DEFAULT_COLOR)
        rows.append(f'''
<text class="m d" x="56" y="{y+15:.0f}" font-size="12">{name}</text>
<rect x="180" y="{y}" width="{bar_area_w}" height="22" rx="6" fill="#FFFFFF" fill-opacity=".04"/>
<rect x="180" y="{y}" width="{w:.1f}" height="22" rx="6" fill="{color}" fill-opacity=".85"/>
<text class="m i" x="{180+bar_area_w+16}" y="{y+15:.0f}" font-size="12">{pct:.1f}%</text>''')
    rows_s = "\n".join(rows)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Top languages by bytes of code across {repo_count} public repositories. Auto-updated daily via GitHub Actions, last generated {generated_at}.">
<defs>
<filter id="blur1" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="46"/></filter>
<linearGradient id="glassStroke" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".18"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
<style>
.m{{font-family:"JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono","DejaVu Sans Mono",monospace}}
.s{{font-family:Inter,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}}
.i{{fill:#E6EDF3}}.d{{fill:#8B98A5}}.f{{fill:#55606B}}.c{{fill:#22D3EE}}
</style>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="#05070a"/>
<circle cx="1250" cy="50" r="180" fill="#8B7BFF" opacity=".18" filter="url(#blur1)"/>
<circle cx="120" cy="{H-40}" r="160" fill="#22D3EE" opacity=".14" filter="url(#blur1)"/>
<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="18" fill="#FFFFFF" fill-opacity=".045" stroke="url(#glassStroke)" stroke-width="1.4"/>
<text class="s i" x="56" y="62" font-size="22" font-weight="600">Top Languages</text>
<text class="m c" x="{W-56}" y="56" font-size="10.5" text-anchor="end" letter-spacing="1.1">AUTO-UPDATED</text>
<text class="m f" x="{W-56}" y="72" font-size="10.5" text-anchor="end">{generated_at} · {repo_count} repos · bytes-weighted</text>
{rows_s}
</svg>
'''


def main():
    repos = fetch_all_repos(USERNAME)
    non_forks = [r for r in repos if not r.get("fork") and not r.get("archived")]
    lang_totals = {}
    for r in non_forks:
        try:
            langs = fetch_languages(USERNAME, r["name"])
        except Exception as e:
            print(f"skip {r['name']}: {e}")
            continue
        for lang, b in langs.items():
            lang_totals[lang] = lang_totals.get(lang, 0) + b

    generated_at = datetime.now(timezone.utc).strftime("%b %-d, %Y")
    svg = build_svg(lang_totals, generated_at, len(non_forks))
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH}: {len(lang_totals)} languages across {len(non_forks)} repos")


if __name__ == "__main__":
    main()
