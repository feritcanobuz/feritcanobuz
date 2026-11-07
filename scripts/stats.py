"""GitHub profil kartlarini (stats, diller, 30 gunluk aktivite) SVG olarak uretir.

Kullanim: GH_TOKEN=... LOGIN=feritcanobuz python scripts/stats.py dist
Sadece standart kutuphane kullanir.
"""
import json
import os
import sys
import urllib.request
from html import escape

BG, TITLE, TEXT, ICON, BORDER = "#141321", "#fe428e", "#a9fef7", "#f8d847", "#e4e2e2"
HIDE_LANGS = {"HTML", "CSS"}
FONT = "font-family='Segoe UI, Ubuntu, Helvetica, Arial, sans-serif'"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        raise SystemExit(f"GraphQL hatasi: {data['errors']}")
    return data["data"]["user"]


def card(width, height, title, body):
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' "
        f"viewBox='0 0 {width} {height}' {FONT}>"
        f"<rect x='0.5' y='0.5' rx='4.5' width='{width - 1}' height='{height - 1}' "
        f"fill='{BG}' stroke='{BORDER}' stroke-opacity='0'/>"
        f"<text x='25' y='35' fill='{TITLE}' font-size='18' font-weight='600'>{escape(title)}</text>"
        f"{body}</svg>"
    )


def stats_svg(u):
    c = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [
        ("Contributions (last year)", c["contributionCalendar"]["totalContributions"]),
        ("Commits (last year)", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("Pull requests", c["totalPullRequestContributions"]),
        ("Issues", c["totalIssueContributions"]),
        ("Public repositories", u["repositories"]["totalCount"]),
        ("Stars earned", stars),
    ]
    body = ""
    for i, (label, value) in enumerate(rows):
        y = 70 + i * 25
        body += (
            f"<circle cx='31' cy='{y - 5}' r='4' fill='{ICON}'/>"
            f"<text x='45' y='{y}' fill='{TEXT}' font-size='14' font-weight='600'>{label}:</text>"
            f"<text x='290' y='{y}' fill='{TEXT}' font-size='14' font-weight='700'>{value}</text>"
        )
    name = u["name"] or "Feritcan"
    return card(495, 70 + len(rows) * 25, f"{name}'s GitHub Stats", body)


def langs_svg(u, count=8):
    sizes, colors = {}, {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            if n in HIDE_LANGS:
                continue
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or "#858585"
    top = sorted(sizes.items(), key=lambda x: -x[1])[:count]
    total = sum(s for _, s in top) or 1
    body, x = "<mask id='m'><rect x='25' y='55' width='445' height='8' rx='5' fill='white'/></mask>", 25.0
    for name, size in top:
        w = 445 * size / total
        body += f"<rect mask='url(#m)' x='{x:.2f}' y='55' width='{w:.2f}' height='8' fill='{colors[name]}'/>"
        x += w
    for i, (name, size) in enumerate(top):
        cx, cy = 25 + (i % 2) * 225, 90 + (i // 2) * 25
        body += (
            f"<circle cx='{cx + 5}' cy='{cy - 4}' r='5' fill='{colors[name]}'/>"
            f"<text x='{cx + 17}' y='{cy}' fill='{TEXT}' font-size='12'>"
            f"{escape(name)} {100 * size / total:.1f}%</text>"
        )
    return card(495, 90 + ((len(top) + 1) // 2) * 25, "Most Used Languages", body)


def activity_svg(u, days=30):
    cal = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]
           for d in w["contributionDays"]][-days:]
    W, H, L, R, T, B = 820, 300, 50, 20, 60, 50
    pw, ph = W - L - R, H - T - B
    peak = max([d["contributionCount"] for d in cal] + [4])
    step = pw / max(len(cal) - 1, 1)
    pts = [(L + i * step, T + ph - ph * d["contributionCount"] / peak) for i, d in enumerate(cal)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{L},{T + ph} {line} {L + pw},{T + ph}"
    body = ""
    for k in range(5):
        y = T + ph * k / 4
        val = round(peak * (4 - k) / 4)
        body += (f"<line x1='{L}' y1='{y:.1f}' x2='{L + pw}' y2='{y:.1f}' stroke='{TEXT}' "
                 f"stroke-opacity='0.12'/>"
                 f"<text x='{L - 10}' y='{y + 4:.1f}' fill='{TEXT}' font-size='11' "
                 f"text-anchor='end'>{val}</text>")
    body += (f"<polygon points='{area}' fill='{TITLE}' fill-opacity='0.15'/>"
             f"<polyline points='{line}' fill='none' stroke='{TITLE}' stroke-width='2.5'/>")
    for i, ((x, y), d) in enumerate(zip(pts, cal)):
        body += f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='{ICON}'/>"
        if i % 5 == 0 or i == len(cal) - 1:
            body += (f"<text x='{x:.1f}' y='{T + ph + 22}' fill='{TEXT}' font-size='11' "
                     f"text-anchor='middle'>{d['date'][5:]}</text>")
    return card(W, H, "Contributions in the last 30 days", body)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dist"
    os.makedirs(out, exist_ok=True)
    u = fetch(os.environ.get("LOGIN", "feritcanobuz"), os.environ["GH_TOKEN"])
    for name, svg in (("stats.svg", stats_svg(u)), ("top-langs.svg", langs_svg(u)),
                      ("activity.svg", activity_svg(u))):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("yazildi:", name)


if __name__ == "__main__":
    main()
