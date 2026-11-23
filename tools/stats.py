"""Builds the README stats cards from the GitHub API (no third-party service):

    assets/activity-{dark,light}.svg   contributions per day, last 30 days
    assets/languages-{dark,light}.svg  languages across my repositories (private ones
                                       too when STATS_TOKEN can read them)

Run by .github/workflows/stats.yml once a day. Locally:

    GITHUB_TOKEN=$(gh auth token) python3 tools/stats.py

Standard library only. The cards are plain SVG with system fonts (images in a
README cannot load web fonts), coloured like the banner.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.request
from xml.sax.saxutils import escape

USER = "AxAce67"
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets"
W = 840
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

THEMES = {
    "dark": {"ink": "#f0f6fc", "muted": "#9198a1", "line": "#3d444d", "track": "#21262d", "bar": "#3fb950", "bar0": "#2a3038"},
    "light": {"ink": "#1f2328", "muted": "#59636e", "line": "#d1d9e0", "track": "#eff2f5", "bar": "#1a7f37", "bar0": "#e1e5ea"},
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) { ...langs }
  }
  # a fine-grained token lists private repositories only through viewer
  viewer { login repositories(first: 100, ownerAffiliations: OWNER, isFork: false) { ...langs } }
}
fragment langs on RepositoryConnection {
  nodes { isPrivate languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
}
"""

# markup and generated files, not what I write
SKIP_LANGUAGES = {"HTML", "CSS", "SCSS", "Dockerfile", "Makefile", "Shell", "Batchfile", "PowerShell"}


def fetch() -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": f"{USER}-readme-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    data = body.get("data") or {}
    if not data.get("user"):
        raise SystemExit(body.get("errors"))
    user = data["user"]
    viewer = data.get("viewer") or {}  # a bot token may not be allowed to read viewer
    # STATS_TOKEN belongs to me, so its viewer also sees my private repositories;
    # the workflow's built-in token is a bot, so fall back to the public list
    if viewer.get("login") == USER:
        user["repositories"] = viewer["repositories"]
    # counts only (no names) so the Actions log shows what the token can see
    repos = user["repositories"]["nodes"]
    print(f"token viewer: {viewer.get('login') or '(none)'}; repositories: {len(repos)}, private: {sum(r['isPrivate'] for r in repos)}")
    if body.get("errors"):
        print("api notes:", [e.get("message", "")[:120] for e in body["errors"]])
    return user


def card(t: dict, height: int, title: str, right: str, inner: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="12" fill="none" stroke="{t["line"]}"/>'
        f'<text x="28" y="40" font-family="{MONO}" font-size="13" letter-spacing="1.2" fill="{t["muted"]}">{escape(title)}</text>'
        f'<text x="{W - 28}" y="40" text-anchor="end" font-family="{MONO}" font-size="13" fill="{t["muted"]}">{escape(right)}</text>'
        f"{inner}</svg>"
    )


def activity(user: dict, t: dict) -> str:
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days = [d for d in days if d["date"] <= dt.date.today().isoformat()][-30:]
    counts = [d["contributionCount"] for d in days]
    total30 = sum(counts)
    streak = 0
    for c in reversed(counts[:-1] if counts and counts[-1] == 0 else counts):  # today may still be empty
        if c == 0:
            break
        streak += 1
    peak = max(counts) or 1
    x0, y_base, h_max = 28, 214, 112
    gap = 4
    bw = (W - 2 * x0 - gap * (len(counts) - 1)) / len(counts)
    # faint guide lines at the peak and half of it, labelled on the right
    grid = []
    for frac in (1, 0.5):
        gy = y_base - h_max * frac
        grid.append(
            f'<line x1="{x0}" y1="{gy:.1f}" x2="{W - x0}" y2="{gy:.1f}" stroke="{t["bar0"]}" stroke-dasharray="2 4"/>'
        )
    bars = []
    for i, c in enumerate(counts):
        h = max(3, c / peak * h_max) if c else 3
        x = x0 + i * (bw + gap)
        bars.append(
            f'<rect x="{x:.1f}" y="{y_base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" fill="{t["bar"] if c else t["bar0"]}">'
            f'<title>{days[i]["date"]}: {c}</title></rect>'
        )
        if c:  # the count above each bar: hover titles do not work in a README image
            bars.append(
                f'<text x="{x + bw / 2:.1f}" y="{y_base - h - 5:.1f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{t["muted"]}">{c}</text>'
            )
    stats = (
        f'<text x="28" y="76" font-family="{SANS}" font-size="26" font-weight="600" fill="{t["ink"]}">{total30:,}'
        f'<tspan font-size="14" font-weight="400" fill="{t["muted"]}" dx="8">contributions in 30 days</tspan></text>'
    )
    # a date under every 7th bar, counted back from today
    ticks = []
    for i in range(len(days) - 1, -1, -7):
        x = x0 + i * (bw + gap) + bw / 2
        label = dt.date.fromisoformat(days[i]["date"]).strftime("%b %-d")
        ticks.append(f'<text x="{x:.1f}" y="{y_base + 20}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{t["muted"]}">{label}</text>')
    axis = "".join(ticks)
    right = f"{streak}-day streak · {cal['totalContributions']:,} in the past year"
    return card(t, 250, "ACTIVITY", right, stats + "".join(grid) + "".join(bars) + axis)


def languages(user: dict, t: dict) -> str:
    sizes: dict[str, list] = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name in SKIP_LANGUAGES:
                continue
            sizes.setdefault(name, [0, e["node"]["color"] or "#8b949e"])[0] += e["size"]
    # with STATS_TOKEN (read-only, set in the workflow) private repositories count
    # too; only the language totals are shown, never repository names
    scope = "all repositories" if any(r["isPrivate"] for r in user["repositories"]["nodes"]) else "public repositories"
    ranked = sorted(sizes.items(), key=lambda kv: -kv[1][0])
    total = sum(v[0] for _, v in ranked) or 1
    top, rest = ranked[:6], sum(v[0] for _, v in ranked[6:])
    parts = [(n, v[0], v[1]) for n, v in top] + ([("Other", rest, t["muted"])] if rest else [])

    x, y, w, h = 28, 62, W - 56, 10
    segs = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{t["track"]}"/>']
    clip = f'<clipPath id="r"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/></clipPath>'
    cx = x
    for _, size, color in parts:
        sw = size / total * w
        segs.append(f'<rect x="{cx:.1f}" y="{y}" width="{sw + .5:.1f}" height="{h}" fill="{color}"/>')
        cx += sw
    legend = []
    col_w = (W - 56) / 4
    for i, (name, size, color) in enumerate(parts):
        lx = 28 + (i % 4) * col_w
        ly = 108 + (i // 4) * 28
        legend.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text x="{lx + 16}" y="{ly}" font-family="{SANS}" font-size="14" fill="{t["ink"]}">{escape(name)}'
            f'<tspan font-family="{MONO}" font-size="12" fill="{t["muted"]}" dx="6">{size / total * 100:.1f}%</tspan></text>'
        )
    rows = (len(parts) + 3) // 4
    height = 108 + rows * 28 + 8
    inner = f"<defs>{clip}</defs><g clip-path=\"url(#r)\">{''.join(segs)}</g>{''.join(legend)}"
    return card(t, height, "LANGUAGES", scope, inner)


def main() -> None:
    user = fetch()
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"activity-{name}.svg").write_text(activity(user, t))
        (OUT / f"languages-{name}.svg").write_text(languages(user, t))
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
