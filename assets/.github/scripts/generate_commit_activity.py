#!/usr/bin/env python3
"""
Regenerates assets/commits.svg from real GitHub contribution data.
Uses only the Python standard library (no pip install step needed in CI).
Auth: GH_TOKEN env var (the workflow's automatic GITHUB_TOKEN is enough —
contribution calendars are public data; the token just raises the rate limit).
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("GH_USERNAME", "J-Akiru5")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT_PATH = os.environ.get("OUT_PATH", "assets/commits.svg")

GRAPHQL_URL = "https://api.github.com/graphql"


def gh_graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(GRAPHQL_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_contribution_calendar(login, frm, to):
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
      }
    }
    """
    data = gh_graphql(query, {"login": login, "from": frm, "to": to})
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(c):
    if c == 0:
        return 0
    if c <= 2:
        return 1
    if c <= 6:
        return 2
    if c <= 15:
        return 3
    return 4


LEVEL_COLORS = {
    0: "#151b23",
    1: "#0e4a52",
    2: "#0f7a8c",
    3: "#22D3EE",
    4: "#8B7BFF",
}


def compute_week_streaks(weeks):
    """weeks: list of weeks, each a list of (date, count).
    A week 'counts' if it has at least one contribution anywhere in it.
    Returns (current_week_streak, longest_week_streak)."""
    week_has_activity = [any(c > 0 for _, c in w) for w in weeks]
    longest = running = 0
    for active in week_has_activity:
        running = running + 1 if active else 0
        longest = max(longest, running)
    current = 0
    for active in reversed(week_has_activity):
        if active:
            current += 1
        else:
            break
    return current, longest


def build_svg(total, current_streak, longest_streak, weeks, generated_at):
    W, H = 1400, 440
    cell, gap = 14, 4
    grid_x0, grid_y0 = 56, 220

    cells, months, prev_month = [], [], None
    for wi, week in enumerate(weeks):
        x = grid_x0 + wi * (cell + gap)
        first_day = datetime.strptime(week[0][0], "%Y-%m-%d")
        m = first_day.strftime("%b")
        if m != prev_month:
            months.append(f'<text x="{x:.1f}" y="{grid_y0-14}" class="m f" font-size="12">{m}</text>')
            prev_month = m
        for di, (date, count) in enumerate(week):
            y = grid_y0 + di * (cell + gap)
            color = LEVEL_COLORS[level(count)]
            cells.append(f'<rect x="{x:.1f}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}"/>')

    day_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
    daylabels = []
    for di, lbl in enumerate(day_labels):
        if lbl:
            y = grid_y0 + di * (cell + gap) + 11
            daylabels.append(f'<text x="20" y="{y}" class="m f" font-size="11.5">{lbl}</text>')

    cells_s, months_s, daylabels_s = "\n".join(cells), "\n".join(months), "\n".join(daylabels)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Commit activity. {total} contributions in the last 12 months. {current_streak}-day current streak. {longest_streak}-day longest streak. Auto-updated daily via GitHub Actions, last generated {generated_at}.">
<defs>
<filter id="blur1" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="46"/></filter>
<linearGradient id="glassStroke" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".18"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
<linearGradient id="lvlgrad" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#22D3EE"/><stop offset="1" stop-color="#8B7BFF"/></linearGradient>
<style>
.m{{font-family:"JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono","DejaVu Sans Mono",monospace}}
.s{{font-family:Inter,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}}
.i{{fill:#E6EDF3}}.d{{fill:#8B98A5}}.f{{fill:#55606B}}.c{{fill:#22D3EE}}
.r{{animation:rise .55s cubic-bezier(0,0,.2,1) both}}
@keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
@media(prefers-reduced-motion:reduce){{.r{{animation:none}}}}
</style>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="#05070a"/>
<circle cx="160" cy="70" r="200" fill="#22D3EE" opacity=".22" filter="url(#blur1)"/>
<circle cx="1240" cy="370" r="240" fill="#8B7BFF" opacity=".20" filter="url(#blur1)"/>
<circle cx="720" cy="410" r="180" fill="#22D3EE" opacity=".10" filter="url(#blur1)"/>
<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="18" fill="#FFFFFF" fill-opacity=".045" stroke="url(#glassStroke)" stroke-width="1.4"/>
<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="18" fill="none" stroke="#FFFFFF" stroke-opacity=".06"/>
<g class="r">
<text class="s i" x="56" y="62" font-size="23" font-weight="600" letter-spacing="-.3">Commit Activity</text>
<text class="m f" x="{W-56}" y="62" font-size="11.5" text-anchor="end" letter-spacing="1.3">SYNTAXURE · GLASS</text>
</g>
<g class="r" style="animation-delay:.08s">
<rect x="56" y="80" width="270" height="92" rx="14" fill="#FFFFFF" fill-opacity=".05" stroke="#FFFFFF" stroke-opacity=".08"/>
<text class="s" x="80" y="132" font-size="36" font-weight="700" fill="url(#lvlgrad)">{total:,}</text>
<text class="m d" x="80" y="156" font-size="11.5">Contributions · last 12 months</text>
</g>
<g class="r" style="animation-delay:.14s">
<rect x="342" y="80" width="270" height="92" rx="14" fill="#FFFFFF" fill-opacity=".05" stroke="#FFFFFF" stroke-opacity=".08"/>
<text class="s" x="366" y="132" font-size="36" font-weight="700" fill="url(#lvlgrad)">{current_streak}</text>
<text class="m d" x="366" y="156" font-size="11.5">Week Streak · current</text>
</g>
<g class="r" style="animation-delay:.2s">
<rect x="628" y="80" width="270" height="92" rx="14" fill="#FFFFFF" fill-opacity=".05" stroke="#FFFFFF" stroke-opacity=".08"/>
<text class="s" x="652" y="132" font-size="36" font-weight="700" fill="url(#lvlgrad)">{longest_streak}</text>
<text class="m d" x="652" y="156" font-size="11.5">Week Streak · longest (12mo)</text>
</g>
<g class="r" style="animation-delay:.26s">
<rect x="914" y="80" width="{W-40-914+20-56}" height="92" rx="14" fill="#FFFFFF" fill-opacity=".045" stroke="#FFFFFF" stroke-opacity=".07"/>
<text class="m c" x="938" y="112" font-size="10.5" letter-spacing="1.2">AUTO-UPDATED</text>
<text class="s i" x="936" y="140" font-size="15" font-weight="600">{generated_at}</text>
<text class="m f" x="938" y="160" font-size="10.5">via GitHub Actions, daily</text>
</g>
<g class="r" style="animation-delay:.32s">
{months_s}
{daylabels_s}
{cells_s}
</g>
<g class="r" style="animation-delay:.4s">
<text class="m f" x="56" y="{H-46}" font-size="11.5">Less</text>
<rect x="88" y="{H-56}" width="13" height="13" rx="3" fill="#151b23"/>
<rect x="106" y="{H-56}" width="13" height="13" rx="3" fill="#0e4a52"/>
<rect x="124" y="{H-56}" width="13" height="13" rx="3" fill="#0f7a8c"/>
<rect x="142" y="{H-56}" width="13" height="13" rx="3" fill="#22D3EE"/>
<rect x="160" y="{H-56}" width="13" height="13" rx="3" fill="#8B7BFF"/>
<text class="m f" x="182" y="{H-46}" font-size="11.5">More</text>
<text class="m f" x="{W-56}" y="{H-46}" font-size="11.5" text-anchor="end">source: github.com/{USERNAME} · GraphQL contributionsCollection</text>
</g>
</svg>
'''


def main():
    to = datetime.now(timezone.utc)
    frm = to - timedelta(days=365)
    cal = fetch_contribution_calendar(USERNAME, frm.isoformat(), to.isoformat())
    total = cal["totalContributions"]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
    current_streak, longest_streak = compute_week_streaks(weeks)
    # keep only the most recent 52 weeks for the drawn grid
    weeks = weeks[-52:]
    generated_at = to.strftime("%b %-d, %Y")
    svg = build_svg(total, current_streak, longest_streak, weeks, generated_at)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT_PATH}: total={total} current_streak={current_streak} longest_streak={longest_streak}")


if __name__ == "__main__":
    main()
