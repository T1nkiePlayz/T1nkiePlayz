#!/usr/bin/env python3
"""Generate assets/stats.svg and assets/langs.svg from the GitHub API.

Self-hosted replacement for third-party stats cards (which get rate limited
and render as broken images on the profile). Needs GH_TOKEN; public data only.
"""
import datetime as dt
import json
import os
import subprocess
from html import escape

USER = os.environ.get("GH_USER", "T1nkiePlayz")
BG, BORDER, TITLE, TEXT, MUTED = "#1e1e2e", "#45475a", "#cba6f7", "#cdd6f4", "#9399b2"
FONT = "font-family=\"'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif\""


def gql(query, **variables):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F", f"{k}={v}"]
    return json.loads(subprocess.check_output(args))["data"]


profile = gql("""query($u:String!){user(login:$u){name createdAt followers{totalCount}
  pullRequests{totalCount} issues{totalCount}
  repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false,first:100){totalCount
    nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}""",
              u=USER)["user"]

created = int(profile["createdAt"][:4])
commits = 0
for year in range(created, dt.date.today().year + 1):
    d = gql("""query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
      totalCommitContributions restrictedContributionsCount}}}""",
            u=USER, f=f"{year}-01-01T00:00:00Z", t=f"{year}-12-31T23:59:59Z")
    c = d["user"]["contributionsCollection"]
    commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]

repos = profile["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]
        langs.setdefault(n["name"], [0, n["color"] or "#888888"])[0] += e["size"]


def card(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<rect x=".5" y=".5" rx="10" width="{w-1}" height="{h-1}" fill="{BG}" stroke="{BORDER}"/>'
            f'<text x="24" y="36" {FONT} font-size="17" font-weight="700" fill="{TITLE}">{escape(title)}</text>{body}</svg>\n')


rows = [("Total commits", commits), ("Pull requests", profile["pullRequests"]["totalCount"]),
        ("Issues opened", profile["issues"]["totalCount"]), ("Public repos", profile["repositories"]["totalCount"]),
        ("Stars earned", stars), ("Followers", profile["followers"]["totalCount"])]
body = ""
for i, (label, value) in enumerate(rows):
    x, y = 24 + (i % 2) * 235, 74 + (i // 2) * 34
    body += (f'<text x="{x}" y="{y}" {FONT} font-size="12" fill="{MUTED}">{label}</text>'
             f'<text x="{x}" y="{y+18}" {FONT} font-size="17" font-weight="700" fill="{TEXT}">{value:,}</text>')
name = profile["name"] or USER
open("assets/stats.svg", "w").write(card(495, 180, f"{name}'s GitHub Stats", body))

total = sum(v[0] for v in langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
body, x = "", 24
bar_w = 447
body += '<clipPath id="c"><rect x="24" y="56" width="447" height="10" rx="5"/></clipPath><g clip-path="url(#c)">'
for n, (size, color) in top:
    w = bar_w * size / total
    body += f'<rect x="{x:.1f}" y="56" width="{w:.1f}" height="10" fill="{escape(color)}"/>'
    x += w
body += "</g>"
for i, (n, (size, color)) in enumerate(top):
    cx, cy = 24 + (i % 2) * 235, 92 + (i // 2) * 26
    body += (f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{escape(color)}"/>'
             f'<text x="{cx+18}" y="{cy}" {FONT} font-size="13" fill="{TEXT}">{escape(n)}'
             f' <tspan fill="{MUTED}">{100*size/total:.1f}%</tspan></text>')
open("assets/langs.svg", "w").write(card(495, 180, "Most Used Languages", body))
print("ok", commits, stars, [n for n, _ in top])
