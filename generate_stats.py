#!/usr/bin/env python3
"""
generate_stats.py  ·  My Stats Action (GitHub Telemetry)

Gera o painel de estatísticas do perfil e atualiza o README.md:

  1. assets/telemetry.svg
       Painel visual estilo mission control: KPIs, mapa de contribuições
       dos últimos 12 meses, linguagens, frescor dos repositórios e
       lançamentos por ano.

  2. Bloco do README.md entre <!--START_STATS--> e <!--END_STATS-->
       Imagem do painel + tabelas: atividade recente, destaques,
       sites no GitHub Pages, telemetria completa e inventário.

Usa só a biblioteca padrão do Python (3.9+), sem pip install.

Uso:
  python generate_stats.py                         busca tudo na API do GitHub
  python generate_stats.py --dump snapshot.json    busca e também salva os dados
  python generate_stats.py --offline snapshot.json gera a partir de dados salvos

O mapa de contribuições usa a API GraphQL, que exige token. No GitHub Actions
o GITHUB_TOKEN padrão é suficiente. Sem token o painel sai sem esse bloco.
"""

import argparse
import html
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from statistics import stdev

# =============================================================================
# Configuração
# =============================================================================
USERNAME = os.environ.get("STATS_USERNAME", "rmayormartins")
CALLSIGN = "PU4MAY"                  # indicativo exibido no cabeçalho do painel
README_PATH = "README.md"
SVG_PATH = "assets/telemetry.svg"    # também é o caminho usado no README
SIGNAL_PATH = "assets/signal-{}.svg" # ícones de "sinal" (recência) usados nas tabelas
START_MARK = "<!--START_STATS-->"
END_MARK = "<!--END_STATS-->"
INCLUDE_FORKS = False                # estatísticas focam nos repositórios próprios
RECENT_ROWS = 6                      # cartões de "Latest activity"
TOP_ROWS = 4                         # cartões de "Most starred & forked"
CARD_PATH = "assets/{}-{}.svg"       # assets/act-1.svg, assets/top-1.svg
BLOCK_HEADING = ""                   # título markdown antes do painel ("" = nenhum)
LANG_BARS = 6                        # linguagens no gráfico (o resto vira "Other")

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Paleta do painel. Contrastes medidos sobre a superfície dos painéis (#0f1722)
# e rampas conferidas com o validador de paletas (luminância monotônica).
C = {
    "card": "#0a0f16",      # fundo do cartão
    "panel": "#0f1722",     # superfície dos painéis
    "stroke": "#1c2836",    # bordas e divisórias (hairline)
    "baseline": "#2b3b4f",  # linha de base dos gráficos
    "ink": "#e6edf3",       # texto primário      15.2:1
    "ink2": "#a8b6c5",      # texto secundário     8.7:1
    "muted": "#7d8da0",     # rótulos e eixos      5.3:1
    "accent": "#3987e5",    # série única (barras e colunas)
    "bracket": "#3987e5",   # cantoneiras dos painéis
    "other": "#3a4a5e",     # agregado "Other" (de-ênfase)
    "good": "#0ca30c",      # status: sincronização OK (sempre com rótulo)
    "chip": "#243548",      # contorno das conquistas
}
FRESH_RAMP = ["#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]  # recente = claro
HEAT_RAMP = ["#17212e", "#104281", "#256abf", "#5598e7", "#9ec5f4"]   # nível 0 a 4

FRESH_BUCKETS = [          # (rótulo, limite superior em dias desde o último push)
    ("≤ 7 days", 7),
    ("8-30 days", 30),
    ("31-90 days", 90),
    ("91-365 days", 365),
    ("> 1 year", math.inf),
]
LANG_ALIAS = {"Jupyter Notebook": "Jupyter"}
PAGE_ICONS = [             # primeira palavra-chave encontrada no nome define o ícone
    (".github.io", "\U0001F3E0"), ("commander", "\U0001F6F0️"),
    ("radar", "\U0001F4E1"), ("telecom", "\U0001F4F6"), ("python", "\U0001F40D"),
    ("ia-", "\U0001F916"), ("ai-", "\U0001F916"), ("ifsc", "\U0001F393"),
]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


# =============================================================================
# Coleta
# =============================================================================
def http_json(url, payload=None, tries=3):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-stats-action",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code < 500 or attempt == tries:
                raise
        except urllib.error.URLError:
            if attempt == tries:
                raise
        time.sleep(2 * attempt)


def fetch_repos():
    repos, page = [], 1
    while True:
        chunk = http_json(f"{API}/users/{USERNAME}/repos?type=owner&per_page=100&page={page}")
        repos.extend(chunk)
        if len(chunk) < 100:
            return repos
        page += 1


GRAPHQL = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount contributionLevel } }
      }
    }
  }
}
"""


def fetch_graphql():
    if not TOKEN:
        print("Aviso: sem GITHUB_TOKEN, o painel sai sem o mapa de contribuições.")
        return None
    try:
        res = http_json(f"{API}/graphql", {"query": GRAPHQL, "variables": {"login": USERNAME}})
        user = (res.get("data") or {}).get("user")
        if res.get("errors") or not user:
            raise RuntimeError(res.get("errors") or "resposta vazia")
        return user
    except Exception as exc:  # o painel continua sem o bloco de contribuições
        print(f"Aviso: contribuições indisponíveis ({exc}).")
        return None


def fetch_snapshot():
    return {
        "user": http_json(f"{API}/users/{USERNAME}"),
        "repos": fetch_repos(),
        "graphql": fetch_graphql(),
    }


# =============================================================================
# Métricas
# =============================================================================
def parse_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def repo_url(r):
    return r.get("html_url") or f"https://github.com/{USERNAME}/{r['name']}"


def pages_url(r):
    home = (r.get("homepage") or "").strip()
    if "github.io" in home:
        return home
    if r["name"].lower() == f"{USERNAME}.github.io".lower():
        return f"https://{USERNAME}.github.io/"
    return f"https://{USERNAME}.github.io/{r['name']}/"


def contribution_metrics(gql, now):
    if not gql:
        return None
    coll = gql["contributionsCollection"]
    cal = coll["contributionCalendar"]
    levels = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
              "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    today = now.date().isoformat()
    days = []
    for w, week in enumerate(cal["weeks"]):
        for d in week["contributionDays"]:
            if d["date"] > today:
                continue
            wd = d.get("weekday")
            if wd is None:  # 0 = domingo, como no calendário do GitHub
                wd = (datetime.strptime(d["date"], "%Y-%m-%d").weekday() + 1) % 7
            days.append({"date": d["date"], "count": d["contributionCount"], "week": w,
                         "wd": wd, "level": levels.get(d.get("contributionLevel"))})
    if not days:
        return None
    if any(d["level"] is None for d in days):  # recalcula por quartis se faltar o nível
        nz = sorted(d["count"] for d in days if d["count"] > 0) or [1]
        q = [nz[int(len(nz) * f) - 1 if int(len(nz) * f) else 0] for f in (0.25, 0.5, 0.75)]
        for d in days:
            c = d["count"]
            d["level"] = 0 if c == 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4
    run = longest = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        longest = max(longest, run)
    i = len(days) - 1
    if days[i]["count"] == 0:  # o dia de hoje ainda pode estar em andamento
        i -= 1
    current = 0
    while i >= 0 and days[i]["count"] > 0:
        current += 1
        i -= 1
    best = max(days, key=lambda d: d["count"])
    return {
        "days": days,
        "weeks": len(cal["weeks"]),
        "total": cal["totalContributions"],
        "commits": coll["totalCommitContributions"],
        "prs": coll["totalPullRequestContributions"],
        "issues": coll["totalIssueContributions"],
        "reviews": coll["totalPullRequestReviewContributions"],
        "new_repos": coll["totalRepositoryContributions"],
        "private": coll.get("restrictedContributionsCount") or 0,
        "active_days": sum(1 for d in days if d["count"]),
        "longest": longest,
        "current": current,
        "best": best,
    }


def compute(snap, now):
    user = snap["user"]
    all_repos = snap["repos"]
    repos = [r for r in all_repos if INCLUDE_FORKS or not r.get("fork")]
    n = len(repos)

    for r in repos:
        r["_push"] = max(0, (now - parse_ts(r.get("pushed_at") or r["updated_at"])).days)
        r["_upd"] = max(0, (now - parse_ts(r["updated_at"])).days)
        r["_year"] = int(r["created_at"][:4])

    created = parse_ts(user["created_at"])
    days_on = (now - created).days
    stars = [r["stargazers_count"] for r in repos]
    forks = [r["forks_count"] for r in repos]
    issues = [r["open_issues_count"] for r in repos]
    sizes = [r["size"] for r in repos]
    langs = Counter(r["language"] for r in repos if r.get("language"))

    def pushed(r):  # timestamp ISO compara corretamente como texto
        return r.get("pushed_at") or r["updated_at"]

    by_push = sorted(repos, key=pushed, reverse=True)          # mais recente primeiro
    pages = [r for r in by_push if r.get("has_pages")]
    others = [r for r in by_push if r["name"].lower() != USERNAME.lower()]  # sem o repo do perfil
    by_created = sorted(repos, key=lambda r: r["created_at"])

    fresh = []
    lower = -1
    for label, upper in FRESH_BUCKETS:
        fresh.append((label, sum(1 for r in repos if lower < r["_push"] <= upper)))
        lower = upper

    years = Counter(r["_year"] for r in repos)
    first_year = min(years) if years else now.year
    launches = [(y, years.get(y, 0)) for y in range(first_year, now.year + 1)]

    top_langs = langs.most_common()
    lang_bars = [(LANG_ALIAS.get(k, k), v) for k, v in top_langs[:LANG_BARS]]
    rest = sum(v for _, v in top_langs[LANG_BARS:])
    if rest:
        lang_bars.append((f"Other ({len(top_langs) - LANG_BARS})", rest))

    contrib = contribution_metrics(snap.get("graphql"), now)
    followers = user.get("followers")
    if snap.get("graphql"):
        followers = snap["graphql"].get("followers", {}).get("totalCount", followers)

    m = {
        "now": now,
        "user": user,
        "repos": repos,
        "n": n,
        "n_all": len(all_repos),
        "stars": sum(stars),
        "forks": sum(forks),
        "avg_stars": sum(stars) / n if n else 0,
        "avg_forks": sum(forks) / n if n else 0,
        "star_std": stdev(stars) if n > 1 else 0,
        "fork_std": stdev(forks) if n > 1 else 0,
        "avg_size": sum(sizes) / n if n else 0,
        "total_size": sum(sizes),
        "largest": max(repos, key=lambda r: r["size"]) if repos else None,
        "avg_issues": sum(issues) / n if n else 0,
        "with_issues": [r for r in repos if r["open_issues_count"] > 0],
        "stars5": sum(1 for s in stars if s >= 5),
        "zero_stars": sum(1 for s in stars if s == 0),
        "forks_gt_stars": sum(1 for r in repos if r["forks_count"] > r["stargazers_count"]),
        "created": created,
        "days_on": days_on,
        "years_on": days_on / 365.25,
        "langs": langs,
        "top_langs": top_langs,
        "lang_bars": lang_bars,
        "pages": pages,
        "by_push": by_push,
        "recent": others[:RECENT_ROWS],
        "top": sorted((r for r in repos if r["stargazers_count"] + r["forks_count"] > 0),
                      key=lambda r: (-(r["stargazers_count"] + r["forks_count"]),
                                     -r["stargazers_count"], r["_push"]))[:TOP_ROWS],
        "active90": sum(1 for r in repos if r["_push"] <= 90),
        "most_forked": max(repos, key=lambda r: r["forks_count"]) if repos else None,
        "most_starred": max(repos, key=lambda r: r["stargazers_count"]) if repos else None,
        "dormant": by_push[-1] if repos else None,
        "latest": others[0] if others else None,
        "first": by_created[0] if repos else None,
        "newest": by_created[-1] if repos else None,
        "new_this_year": years.get(now.year, 0),
        "fresh": fresh,
        "launches": launches,
        "contrib": contrib,
        "followers": followers,
    }
    m["achievements"] = achievements(m)
    return m


def achievements(m):
    """Maior faixa atingida em cada família (texto curto, sem emoji, para o SVG)."""
    tiers = [
        ("REPOS", m["n"], [100, 50, 30, 10]),
        ("STARS", m["stars"], [100, 50, 20, 10]),
        ("FORKS", m["forks"], [100, 50, 20, 10]),
        ("SITES", len(m["pages"]), [50, 25, 10, 5]),
        ("YEARS", int(m["years_on"]), [20, 15, 10, 5, 1]),
    ]
    if m["contrib"]:
        tiers.append(("CONTRIB/YR", m["contrib"]["total"], [5000, 2000, 1000, 500, 100]))
    out = []
    for label, value, steps in tiers:
        hit = next((s for s in steps if value >= s), None)
        if hit:
            out.append(f"{hit // 1000}K+ {label}" if hit >= 1000 else f"{hit}+ {label}")
    return out


# =============================================================================
# Formatação
# =============================================================================
def esc(s):
    return html.escape(str(s), quote=True)


NB = " "  # espaço não separável: evita quebra de linha dentro das células


def ago(days):
    if days <= 0:
        return "today"
    if days < 30:
        return f"{days}{NB}d{NB}ago"
    if days < 365:
        return f"{days // 30}{NB}mo{NB}ago"
    return f"{days / 365.25:.1f}{NB}y{NB}ago"


def signal_level(days):
    """Nível de 'sinal' pela recência do último push: 5 = até 7 dias, 1 = mais de 1 ano."""
    return 5 - next(i for i, (_, up) in enumerate(FRESH_BUCKETS) if days <= up)


def signal_img(days):
    lvl = signal_level(days)
    return f'<img src="{SIGNAL_PATH.format(lvl)}" height="14" alt="signal {lvl}/5">'


def signal_svg(level):
    """Ícone de barras de sinal (estilo celular). Funciona em tema claro e escuro."""
    bars = []
    for i in range(5):
        h = 4 + i * 2.5
        on = i < level
        fill = C["accent"] if on else "#8b949e"
        alpha = "" if on else ' fill-opacity=".4"'
        bars.append(f'<rect x="{i * 5:.1f}" y="{16 - h:.1f}" width="3.4" height="{h:.1f}" '
                    f'rx="1" fill="{fill}"{alpha}/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="16" viewBox="0 0 24 16" '
            f'role="img" aria-label="signal {level} of 5">{"".join(bars)}</svg>\n')


def size_fmt(kb):
    return f"{kb / 1024:.1f}{NB}MB" if kb >= 1024 else f"{kb}{NB}KB"


def md_cell(s):
    return str(s).replace("|", "\\|")


def icon_for(name):
    low = name.lower()
    return next((ic for key, ic in PAGE_ICONS if key in low), "\U0001F310")


# =============================================================================
# SVG
# =============================================================================
W = 900
PAD = 22
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
SANS = "system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"


def hbar(x, y, w, h, r=4):
    """Barra horizontal: base quadrada à esquerda, ponta arredondada (4px)."""
    if w <= 0:
        return ""
    r = min(r, h / 2, w)
    return (f"M{x:.1f},{y:.1f}h{w - r:.1f}a{r:.1f},{r:.1f} 0 0 1 {r:.1f},{r:.1f}"
            f"v{h - 2 * r:.1f}a{r:.1f},{r:.1f} 0 0 1 {-r:.1f},{r:.1f}h{-(w - r):.1f}z")


def vbar(x, base, w, h, r=4):
    """Coluna: base quadrada embaixo, topo arredondado (4px)."""
    if h <= 0:
        return ""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{base:.1f}v{-(h - r):.1f}a{r:.1f},{r:.1f} 0 0 1 {r:.1f},{-r:.1f}"
            f"h{w - 2 * r:.1f}a{r:.1f},{r:.1f} 0 0 1 {r:.1f},{r:.1f}v{h - r:.1f}z")


def bracket_d(x, y, w, h, t=9):
    """Cantoneiras estilo HUD nos quatro cantos de um retângulo."""
    return (f"M{x:.1f},{y + t:.1f}V{y:.1f}H{x + t:.1f}"
            f"M{x + w - t:.1f},{y:.1f}H{x + w:.1f}V{y + t:.1f}"
            f"M{x + w:.1f},{y + h - t:.1f}V{y + h:.1f}H{x + w - t:.1f}"
            f"M{x + t:.1f},{y + h:.1f}H{x:.1f}V{y + h - t:.1f}")


class Svg:
    def __init__(self):
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, content, cls, anchor=None):
        a = f' text-anchor="{anchor}"' if anchor else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{a}>{content}</text>')

    def panel(self, x, y, w, h, title=None, note=None):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" '
                 f'fill="{C["panel"]}" stroke="{C["stroke"]}"/>')
        self.add(f'<path d="{bracket_d(x, y, w, h)}" fill="none" stroke="{C["bracket"]}" '
                 f'stroke-width="1.5" stroke-opacity=".7"/>')
        if title:
            self.text(x + 16, y + 26, esc(title), "pt")
            if note:
                self.text(x + w - 16, y + 26, esc(note), "pn", "end")
            self.add(f'<path d="M{x + 16:.1f},{y + 38.5:.1f}H{x + w - 16:.1f}" '
                     f'stroke="{C["stroke"]}"/>')


def svg_style():
    return f"""<style>
text{{font-family:{MONO};}}
.h1{{font-size:15px;font-weight:700;letter-spacing:2.4px;fill:{C["ink"]};}}
.h1d{{font-size:15px;font-weight:400;letter-spacing:.5px;fill:{C["muted"]};}}
.hs{{font-size:12px;letter-spacing:.8px;fill:{C["muted"]};}}
.hb{{font-size:12px;font-weight:700;letter-spacing:1.2px;fill:{C["ink2"]};}}
.kl{{font-size:11.5px;font-weight:600;letter-spacing:1px;fill:{C["muted"]};}}
.kv{{font-family:{SANS};font-size:30px;font-weight:600;fill:{C["ink"]};}}
.ku{{font-family:{SANS};font-size:15px;font-weight:500;fill:{C["ink2"]};}}
.ks{{font-size:12px;fill:{C["ink2"]};}}
.pt{{font-size:12.5px;font-weight:700;letter-spacing:1.8px;fill:{C["ink"]};}}
.pn{{font-size:12px;fill:{C["muted"]};}}
.lb{{font-size:12.5px;fill:{C["ink2"]};}}
.vl{{font-size:12.5px;font-weight:700;fill:{C["ink"]};}}
.ax{{font-size:12px;fill:{C["muted"]};}}
.st{{font-size:12px;fill:{C["muted"]};}}
.sv{{font-size:12px;font-weight:700;fill:{C["ink"]};}}
.ch{{font-size:11.5px;font-weight:600;letter-spacing:1px;fill:{C["ink2"]};}}
.ft{{font-size:11.5px;letter-spacing:.5px;fill:{C["muted"]};}}
.led{{animation:pulse 2.4s ease-in-out infinite;}}
.gx{{transform-box:fill-box;transform-origin:left center;animation:gx .9s cubic-bezier(.2,.7,.2,1) both;}}
.gy{{transform-box:fill-box;transform-origin:center bottom;animation:gy .9s cubic-bezier(.2,.7,.2,1) both;}}
.sw{{animation:sw .5s ease-out both;}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
@keyframes gx{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes gy{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes sw{{from{{opacity:0}}to{{opacity:1}}}}
@media (prefers-reduced-motion:reduce){{.led,.gx,.gy,.sw{{animation:none}}}}
</style>"""


def svg_defs():
    return ('<defs><pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse">'
            '<circle cx="1" cy="1" r=".8" fill="#ffffff" fill-opacity=".05"/></pattern>'
            f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{C["accent"]}" '
            f'stop-opacity=".55"/><stop offset="1" stop-color="{C["accent"]}" stop-opacity="0"/>'
            '</linearGradient></defs>')


def svg_doc(w, h, title, desc, body, extra_css=""):
    """Moldura comum de todos os SVGs: estilo, defs, título e descrição acessível."""
    style = svg_style()
    if extra_css:
        style = style.replace("</style>", extra_css + "</style>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-labelledby="t d">'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
            f'{style}{svg_defs()}{body}</svg>\n')


def signal_bars(x, y, level, scale=1.0):
    """Barras de sinal desenhadas (mesmo desenho dos ícones das tabelas)."""
    out = []
    for i in range(5):
        h = (4 + i * 2.5) * scale
        on = i < level
        alpha = "" if on else ' fill-opacity=".4"'
        out.append(f'<rect x="{x + i * 5 * scale:.1f}" y="{y - h:.1f}" '
                   f'width="{3.4 * scale:.1f}" height="{h:.1f}" rx="1" '
                   f'fill="{C["accent"] if on else "#8b949e"}"{alpha}/>')
    return "".join(out)


CARD_W, CARD_H = 430, 92


def repo_card(name, line2, line3, level, live=False):
    """Cartão de repositório usado nas grades clicáveis do README."""
    s = Svg()
    s.add(f'<rect x=".5" y=".5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="8" '
          f'fill="{C["panel"]}" stroke="{C["stroke"]}"/>')
    s.add(f'<rect x=".5" y=".5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="8" fill="url(#dots)"/>')
    s.add(f'<rect x="1" y="1" width="4" height="{CARD_H - 2}" rx="2" fill="{C["accent"]}"/>')
    s.add(f'<path d="{bracket_d(12, 10, CARD_W - 24, CARD_H - 20, 8)}" fill="none" '
          f'stroke="{C["bracket"]}" stroke-width="1.5" stroke-opacity=".45"/>')
    limit = 30  # nome longo demais some atrás das barras de sinal
    shown = name if len(name) <= limit else name[:limit - 1] + "…"
    s.text(24, 38, esc(shown), "ct")
    s.text(24, 59, esc(line2), "cs")
    s.text(24, 79, esc(line3), "cu")
    s.add(signal_bars(CARD_W - 52, 40, level, 1.15))
    if live:
        s.add(f'<rect x="{CARD_W - 74:.1f}" y="58" width="52" height="19" rx="9.5" fill="none" '
              f'stroke="{C["chip"]}"/>')
        s.text(CARD_W - 48, 71, "LIVE", "pillc", "middle")
    return s.parts


CARD_CSS = f"""
.ct{{font-size:14.5px;font-weight:700;letter-spacing:.6px;fill:{C["ink"]};}}
.cs{{font-size:11.5px;fill:{C["ink2"]};}}
.cu{{font-size:11.5px;fill:{C["accent"]};}}
.pillc{{font-size:10.5px;font-weight:600;letter-spacing:1px;fill:{C["ink2"]};}}
"""


LABEL_PATH = "assets/lbl-{}.svg"


def label_bar(key, text, note=""):
    """Faixa fina de rótulo, versão reduzida das faixas de seção."""
    h, w = 30, W
    s = Svg()
    s.add(f'<rect x="0" y="6" width="4" height="{h - 12}" rx="2" fill="{C["accent"]}"/>')
    s.text(16, 20, esc(text), "lbt")
    x0 = 16 + len(text) * (12 * 0.62 + 2) + 16
    if note:
        s.text(w, 20, esc(note), "pn", "end")
        x1 = w - len(note) * (12 * 0.62) - 16
    else:
        x1 = w
    if x1 > x0 + 20:
        s.add(f'<path d="M{x0:.1f},15.5H{x1:.1f}" stroke="{C["stroke"]}"/>')
    css = f'.lbt{{font-size:12px;font-weight:700;letter-spacing:2px;fill:{C["ink2"]};}}'
    path = LABEL_PATH.format(key)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_doc(w, h, text, f"{text}{': ' + note if note else ''}",
                        "".join(s.parts), css))
    return path


def write_repo_cards(m):
    """Escreve assets/act-N.svg e assets/top-N.svg e devolve os dados para o markdown."""
    cards = []
    groups = [("act", m["recent"], "activity"), ("top", m["top"], "top")]
    for prefix, repos, kind in groups:
        for i, r in enumerate(repos, 1):
            lang = r.get("language") or "no language"
            if kind == "activity":
                line2 = f'{lang} · pushed {ago(r["_push"]).replace(NB, " ")}'
            else:
                st, fk = r["stargazers_count"], r["forks_count"]
                line2 = (f'{lang} · {st} star{"" if st == 1 else "s"} '
                         f'· {fk} fork{"" if fk == 1 else "s"}')
            line3 = f'github.com/{USERNAME}/{r["name"]}'
            if len(line3) > 44:
                line3 = line3[:43] + "…"
            level = signal_level(r["_push"])
            body = repo_card(r["name"], line2, line3, level, bool(r.get("has_pages")))
            desc = (f'{r["name"]}: {line2}. Last push {ago(r["_push"]).replace(NB, " ")}. '
                    f'Link: {repo_url(r)}')
            path = CARD_PATH.format(prefix, i)
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg_doc(CARD_W, CARD_H, r["name"], desc, "".join(body), CARD_CSS))
            cards.append((prefix, path, r, desc))
    return cards


def render_svg(m):
    s = Svg()
    now = m["now"]
    inner = W - 2 * PAD
    y = 0

    # ---- Cabeçalho --------------------------------------------------------
    s.text(PAD, 35, f'GITHUB TELEMETRY<tspan class="h1d" dx="12">// {esc(USERNAME)}</tspan>', "h1")
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    s.text(W - PAD - 18, 34,
           f'<tspan class="hb">{esc(CALLSIGN)}</tspan><tspan dx="10">·</tspan>'
           f'<tspan dx="10" class="hb">SYNC OK</tspan><tspan dx="10">{stamp}</tspan>', "hs", "end")
    s.add(f'<circle cx="{W - PAD - 5}" cy="30" r="8" fill="{C["good"]}" fill-opacity=".18" class="led"/>')
    s.add(f'<circle cx="{W - PAD - 5}" cy="30" r="4" fill="{C["good"]}" class="led"/>')
    s.add(f'<path d="M{PAD},56.5H{W - PAD}" stroke="{C["stroke"]}"/>')
    y = 70

    # ---- KPIs ---------------------------------------------------------------
    c = m["contrib"]
    kpis = [
        ("REPOSITORIES", f'{m["n"]:,}', "", f'+{m["new_this_year"]} in {now.year}'),
        ("STARS", f'{m["stars"]:,}', "", f'{m["avg_stars"]:.2f} per repo'),
        ("FORKS", f'{m["forks"]:,}', "", f'{m["avg_forks"]:.2f} per repo'),
        ("LIVE SITES", f'{len(m["pages"]):,}', "",
         f'{len(m["pages"]) / m["n"] * 100:.0f}% of repos' if m["n"] else ""),
    ]
    if c:
        kpis.append(("CONTRIBUTIONS", f'{c["total"]:,}', "", "last 12 months"))
    else:
        kpis.append(("ACTIVE 90D", f'{m["active90"]:,}', "",
                     f'{m["active90"] / m["n"] * 100:.1f}% of repos' if m["n"] else ""))
    kpis.append(("ON GITHUB", f'{m["years_on"]:.1f}', "yrs", f'since {m["created"]:%b %Y}'))
    gap = 10
    tw = (inner - gap * (len(kpis) - 1)) / len(kpis)
    th = 92
    for i, (label, value, unit, sub) in enumerate(kpis):
        x = PAD + i * (tw + gap)
        s.panel(x, y, tw, th)
        s.text(x + 14, y + 25, esc(label), "kl")
        u = f'<tspan class="ku" dx="5">{esc(unit)}</tspan>' if unit else ""
        s.text(x + 14, y + 61, f"{esc(value)}{u}", "kv")
        s.text(x + 14, y + 80, esc(sub), "ks")
    y += th + 14

    # ---- Mapa de contribuições --------------------------------------------
    if c:
        ph = 246
        s.panel(PAD, y, inner, ph, "CONTRIBUTIONS", "last 12 months · GitHub calendar")
        best = c["best"]
        best_day = datetime.strptime(best["date"], "%Y-%m-%d").strftime("%b %d")
        s.text(PAD + 16, y + 62,
               f'<tspan class="sv">{c["total"]:,}</tspan> contributions'
               f'<tspan dx="12">·</tspan><tspan dx="12" class="sv">{c["active_days"]}</tspan>'
               f' active days'
               f'<tspan dx="12">·</tspan><tspan dx="12">best day </tspan>'
               f'<tspan class="sv">{best["count"]}</tspan> ({best_day})'
               f'<tspan dx="12">·</tspan><tspan dx="12">longest streak </tspan>'
               f'<tspan class="sv">{c["longest"]} d</tspan>'
               f'<tspan dx="12">·</tspan><tspan dx="12">current </tspan>'
               f'<tspan class="sv">{c["current"]} d</tspan>', "st")
        label_w = 30
        weeks = max(c["weeks"], 1)
        pitch = min(15.0, (inner - 32 - label_w) / weeks)
        cell = pitch - 3
        grid_w = weeks * pitch - 3
        gx = PAD + 16 + label_w + (inner - 32 - label_w - grid_w) / 2
        gy = y + 94
        for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            s.text(gx - 8, gy + row * pitch + cell - 2, name, "ax", "end")
        last_month, last_x = None, -99
        for d in c["days"]:
            if d["wd"] == 0 or d is c["days"][0]:
                month = int(d["date"][5:7])
                x = gx + d["week"] * pitch
                if month != last_month and x - last_x > 3 * pitch and d["date"][8:] <= "07":
                    s.text(x, gy - 9, MONTHS[month - 1], "ax")
                    last_x = x
                last_month = month
        cols = {}
        for d in c["days"]:
            cols.setdefault(d["week"], []).append(d)
        for w, ds in sorted(cols.items()):
            delay = w * 18
            s.add(f'<g class="sw" style="animation-delay:{delay}ms">')
            for d in ds:
                s.add(f'<rect x="{gx + w * pitch:.1f}" y="{gy + d["wd"] * pitch:.1f}" '
                      f'width="{cell:.1f}" height="{cell:.1f}" rx="2.5" '
                      f'fill="{HEAT_RAMP[d["level"]]}"/>')
            s.add("</g>")
        ly = y + ph - 20
        parts = [("COMMITS", c["commits"]), ("PULL REQUESTS", c["prs"]),
                 ("ISSUES", c["issues"]), ("REVIEWS", c["reviews"]),
                 ("NEW REPOS", c["new_repos"])]
        if c["private"]:
            parts.append(("PRIVATE", c["private"]))
        pieces = []
        for i, (k, v) in enumerate(parts):
            opener = '<tspan dx="16">' if i else "<tspan>"
            pieces.append(f'{opener}{k} </tspan><tspan class="sv">{v:,}</tspan>')
        s.text(PAD + 16, ly, "".join(pieces), "st")
        lx = PAD + inner - 16
        s.text(lx, ly, "MORE", "ax", "end")
        sx = lx - 44
        for lvl in range(4, -1, -1):
            s.add(f'<rect x="{sx:.1f}" y="{ly - 10:.1f}" width="11" height="11" rx="2.5" '
                  f'fill="{HEAT_RAMP[lvl]}"/>')
            sx -= 15
        s.text(sx + 8, ly, "LESS", "ax", "end")
        y += ph + 14

    # ---- Linha inferior: linguagens, frescor, lançamentos ------------------
    ph = 214
    gap = 12
    pw = (inner - 2 * gap) / 3
    xs = [PAD + i * (pw + gap) for i in range(3)]

    # Linguagens (uma série: barras na mesma cor, valor na ponta)
    x0 = xs[0]
    s.panel(x0, y, pw, ph, "LANGUAGES", "by main language")
    bars = m["lang_bars"]
    lab_w = 88
    bmax = pw - 32 - lab_w - 30
    vmax = max((v for _, v in bars), default=1)
    for i, (name, v) in enumerate(bars):
        by = y + 58 + i * 21
        s.text(x0 + 16, by + 9, esc(name), "lb")
        bw = max(2, bmax * v / vmax)
        fill = C["other"] if name.startswith("Other") else C["accent"]
        s.add(f'<path d="{hbar(x0 + 16 + lab_w, by, bw, 10)}" fill="{fill}" class="gx" '
              f'style="animation-delay:{i * 60}ms"/>')
        s.text(x0 + 16 + lab_w + bw + 6, by + 9.5, f"{v}", "vl")

    # Frescor (parte do todo, rampa ordinal: recente = claro)
    x1 = xs[1]
    s.panel(x1, y, pw, ph, "FRESHNESS", "time since last push")
    total = sum(v for _, v in m["fresh"]) or 1
    bw_total = pw - 32
    usable = bw_total - 2 * (sum(1 for _, v in m["fresh"] if v) - 1)
    bx = x1 + 16
    segs = [(i, v) for i, (_, v) in enumerate(m["fresh"]) if v]
    for k, (i, v) in enumerate(segs):
        w = usable * v / total
        last = k == len(segs) - 1
        d = hbar(bx, y + 56, w, 14) if last else f"M{bx:.1f},{y + 56:.1f}h{w:.1f}v14h{-w:.1f}z"
        s.add(f'<path d="{d}" fill="{FRESH_RAMP[i]}" class="gx" style="animation-delay:{k * 80}ms"/>')
        bx += w + 2
    for i, (label, v) in enumerate(m["fresh"]):
        ry = y + 100 + i * 22
        s.add(f'<rect x="{x1 + 16:.1f}" y="{ry - 9:.1f}" width="10" height="10" rx="2" '
              f'fill="{FRESH_RAMP[i]}"/>')
        s.text(x1 + 34, ry, esc(label), "lb")
        s.text(x1 + pw - 62, ry, f"{v}", "vl", "end")
        s.text(x1 + pw - 16, ry, f"{v / total * 100:.0f}%", "ax", "end")

    # Lançamentos por ano (colunas, valor no topo)
    x2 = xs[2]
    s.panel(x2, y, pw, ph, "LAUNCHES", "new repos/yr · *YTD")
    launches = m["launches"][-6:]
    base = y + ph - 36
    hmax = 104
    vmax = max((v for _, v in launches), default=1) or 1
    slot = (pw - 32) / max(len(launches), 1)
    colw = min(22, slot * 0.55)
    s.add(f'<path d="M{x2 + 16:.1f},{base + 0.5:.1f}H{x2 + pw - 16:.1f}" stroke="{C["baseline"]}"/>')
    for i, (yr, v) in enumerate(launches):
        cx = x2 + 16 + slot * i + slot / 2
        h = hmax * v / vmax
        if h:
            s.add(f'<path d="{vbar(cx - colw / 2, base, colw, h)}" fill="{C["accent"]}" '
                  f'class="gy" style="animation-delay:{i * 60}ms"/>')
        s.text(cx, base - h - 7, f"{v}", "vl", "middle")
        s.text(cx, base + 18, f"{yr}" if yr != now.year else f"{yr}*", "ax", "middle")
    y += ph + 14

    # ---- Rodapé: conquistas (pílulas centralizadas) ---------------------------
    chips, used = [], 0.0
    for a in m["achievements"]:
        cw = len(a) * 8.1 + 40  # largura folgada: fontes monoespaçadas variam por sistema
        if used + cw > inner:
            break
        chips.append((a, cw))
        used += cw + 8
    cx = PAD + (inner - (used - 8)) / 2 if chips else PAD
    for a, cw in chips:
        s.add(f'<rect x="{cx:.1f}" y="{y + 1:.1f}" width="{cw:.1f}" height="24" rx="12" '
              f'fill="none" stroke="{C["chip"]}"/>')
        dx, dy = cx + 16, y + 13
        s.add(f'<path d="M{dx:.1f},{dy - 4:.1f}l4,4l-4,4l-4,-4z" fill="{C["accent"]}"/>')
        s.text(cx + 27, y + 17.5, esc(a), "ch")
        cx += cw + 8
    height = y + 25 + PAD

    bg = (f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1:.0f}" rx="12" '
          f'fill="{C["card"]}" stroke="{C["stroke"]}"/>'
          f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1:.0f}" rx="12" fill="url(#dots)"/>')
    return svg_doc(W, height, f"GitHub telemetry for {USERNAME}", alt_text(m),
                   bg + "\n".join(s.parts))


def alt_text(m):
    bits = [f'{m["n"]} repositories', f'{m["stars"]} stars', f'{m["forks"]} forks',
            f'{len(m["pages"])} GitHub Pages sites']
    if m["top_langs"]:
        bits.append(f'top language {m["top_langs"][0][0]}')
    if m["contrib"]:
        bits.append(f'{m["contrib"]["total"]} contributions in the last 12 months')
    return f"GitHub telemetry dashboard for {USERNAME}: " + ", ".join(bits)


# =============================================================================
# Markdown
# =============================================================================
def render_markdown(m):
    now = m["now"]
    L = [START_MARK, ""]
    if BLOCK_HEADING:  # o README novo já traz a faixa da seção acima do bloco
        L += [BLOCK_HEADING, ""]
    L += ['<p align="center">',
          f'  <img src="{SVG_PATH}" width="100%" alt="{esc(alt_text(m))}">',
          "</p>", ""]

    # Grades de cartões clicáveis (mesmo visual do painel; tabela do GitHub não aceita CSS)
    cards = m["cards"]
    for prefix, heading, note in (
            ("act", "LATEST ACTIVITY", f'last {len(m["recent"])} repositories pushed'),
            ("top", "MOST STARRED & FORKED", "all time")):
        group = [c for c in cards if c[0] == prefix]
        if not group:
            continue
        bar = label_bar(prefix, heading, note)
        L += [f'<img src="{bar}" width="100%" alt="{esc(heading)}: {esc(note)}">', "",
              '<p align="center">']
        for _, path, r, desc in group:
            L.append(f'  <a href="{repo_url(r)}"><img src="{path}" width="49%" '
                     f'alt="{esc(desc)}"></a>')
        L += ["</p>", ""]

    # Telemetria completa (métricas clássicas do My Stats Action)
    c = m["contrib"]
    tl = ", ".join(f"{k} ({v})" for k, v in m["top_langs"][:3]) or "-"
    wi = m["with_issues"]
    issues_txt = (f'{len(wi)} ({", ".join(r["name"] for r in wi[:3])})' if wi else "0")
    rows = [
        ("Public repositories", f'{m["n"]} ({m["n_all"]} incl. forks)',
         "Days on GitHub", f'{m["days_on"]:,} (since {m["created"]:%Y-%m-%d})'),
        ("Total stars", f'{m["stars"]} (avg {m["avg_stars"]:.2f})',
         "Total forks", f'{m["forks"]} (avg {m["avg_forks"]:.2f})'),
        ("Star std deviation", f'{m["star_std"]:.2f}',
         "Fork std deviation", f'{m["fork_std"]:.2f}'),
        ("Repos with 5+ stars", f'{m["stars5"]}',
         "Repos with 0 stars", f'{m["zero_stars"]}'),
        ("Forks > stars", f'{m["forks_gt_stars"]} repos',
         "Avg repo size", size_fmt(round(m["avg_size"]))),
        ("Largest repo", f'{m["largest"]["name"]} ({size_fmt(m["largest"]["size"])})'
         if m["largest"] else "-",
         "Total size", size_fmt(m["total_size"])),
        ("Most common language", m["top_langs"][0][0] if m["top_langs"] else "-",
         "Unique languages", f'{len(m["langs"])}'),
        ("Top languages", tl,
         "GitHub Pages sites", f'{len(m["pages"])}'),
        ("Pushed in last 90 days", f'{m["active90"]} ({m["active90"] / m["n"] * 100:.1f}%)'
         if m["n"] else "0",
         "Avg open issues per repo", f'{m["avg_issues"]:.2f}'),
        ("Most starred", f'{m["most_starred"]["name"]} ({m["most_starred"]["stargazers_count"]})'
         if m["most_starred"] else "-",
         "Most forked", f'{m["most_forked"]["name"]} ({m["most_forked"]["forks_count"]})'
         if m["most_forked"] else "-"),
        ("Latest push", f'{m["latest"]["name"]} ({ago(m["latest"]["_push"])})'
         if m["latest"] else "-",
         "Longest dormant", f'{m["dormant"]["name"]} ({m["dormant"]["_push"]:,} d)'
         if m["dormant"] else "-"),
        ("First repository", f'{m["first"]["name"]} ({m["first"]["created_at"][:10]})'
         if m["first"] else "-",
         "Newest repository", f'{m["newest"]["name"]} ({m["newest"]["created_at"][:10]})'
         if m["newest"] else "-"),
        ("Repos with open issues", issues_txt,
         "Followers", f'{m["followers"]:,}' if m["followers"] is not None else "-"),
    ]
    if c:
        rows += [
            ("Contributions (12 mo)", f'{c["total"]:,}',
             "Commits (12 mo)", f'{c["commits"]:,}'),
            ("Longest streak", f'{c["longest"]} days',
             "Current streak", f'{c["current"]} days'),
            ("Best day", f'{c["best"]["count"]} ({c["best"]["date"]})',
             "Active days (12 mo)", f'{c["active_days"]}'),
        ]
    L += ["<details>", "<summary><b>\U0001F4CA Full telemetry</b></summary>", "",
          "| Metric | Value | Metric | Value |", "|:--|:--|:--|:--|"]
    for a, b, c2, d in rows:
        L.append(f"| {md_cell(a)} | **{md_cell(b)}** | {md_cell(c2)} | **{md_cell(d)}** |")
    medals = " · ".join(f"\U0001F3C5 {a.title()}" for a in m["achievements"]) or "-"
    L += ["", f"**Achievements:** {medals}", "", "</details>", ""]

    # Sites no GitHub Pages (recolhido)
    L += ["<details>",
          f'<summary><b>\U0001F310 Live on GitHub Pages</b> ({len(m["pages"])} sites)</summary>',
          "", "| | Live site | Source | Language | Last deploy |",
          "|:-:|:--|:--|:--|--:|"]
    for r in m["pages"]:
        L.append(f'| {icon_for(r["name"])} | [{md_cell(r["name"])}]({pages_url(r)}) '
                 f'| [code]({repo_url(r)}) | {md_cell(r.get("language") or "-")} '
                 f'| {ago(r["_push"])} |')
    L += ["", "</details>", ""]

    # Inventário completo (recolhido)
    L += ["<details>",
          f'<summary><b>\U0001F5C2️ Repository inventory</b> ({m["n"]} repos, '
          f'\U0001F310 = live site)</summary>', "",
          "| Repository | Language | ⭐ | \U0001F374 | Created | Last push | Signal |",
          "|:--|:--|--:|--:|:--|--:|:-:|"]
    for r in m["by_push"]:
        site = f' [\U0001F310]({pages_url(r)})' if r.get("has_pages") else ""
        created = parse_ts(r["created_at"]).strftime(f"%b{NB}%Y")
        L.append(f'| [{md_cell(r["name"])}]({repo_url(r)}){site} '
                 f'| {md_cell(r.get("language") or "-")} | {r["stargazers_count"]} '
                 f'| {r["forks_count"]} | {created} '
                 f'| {ago(r["_push"])} | {signal_img(r["_push"])} |')
    L += ["", "</details>", "",
          '<p align="right"><sub>\U0001F916 Auto-updated daily by '
          '<a href="generate_stats.py">generate_stats.py</a> (GitHub Actions) · '
          f'last sync {now:%Y-%m-%d %H:%M} UTC</sub></p>',
          END_MARK]
    return "\n".join(L)


# =============================================================================
# Execução
# =============================================================================
def sync_alt_texts(readme):
    """Mantém o alt das imagens de assets/ igual ao <desc> do próprio SVG, para
    o texto alternativo não ficar defasado quando o conteúdo do painel muda."""
    def fix(match):
        src, alt = match.group(1), match.group(2)
        try:
            with open(src, encoding="utf-8") as f:
                svg = f.read()
        except OSError:
            return match.group(0)
        found = re.search(r'<desc id="d">(.*?)</desc>', svg, re.S)
        if not found or found.group(1) == alt:
            return match.group(0)
        return match.group(0).replace(f'alt="{alt}"', f'alt="{found.group(1)}"')

    return re.sub(r'<img src="(assets/[^"]+\.svg)"[^>]*? alt="([^"]*)"', fix, readme)


def main():
    ap = argparse.ArgumentParser(description="Atualiza o painel My Stats Action do README.")
    ap.add_argument("--offline", help="gera a partir de um snapshot JSON salvo")
    ap.add_argument("--dump", help="salva o snapshot buscado neste arquivo JSON")
    ap.add_argument("--now", help="data/hora de referência (ISO, UTC), útil em testes")
    ap.add_argument("--no-theme", action="store_true",
                    help="não regenerar os assets de estilo (generate_theme.py)")
    args = ap.parse_args()

    # A identidade visual do README (hero, faixas, painéis, cartões) vem do
    # generate_theme.py. Rodar aqui também evita README com imagem faltando
    # se o passo correspondente do workflow não existir ou não tiver rodado.
    if not args.no_theme:
        try:
            import generate_theme
            generate_theme.main()
        except Exception as exc:
            print(f"Aviso: identidade visual nao gerada ({exc}).")

    if args.offline:
        with open(args.offline, encoding="utf-8") as f:
            snap = json.load(f)
    else:
        snap = fetch_snapshot()
        if args.dump:
            with open(args.dump, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False)

    now = (datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
           if args.now else datetime.now(timezone.utc).replace(second=0, microsecond=0))
    m = compute(snap, now)

    os.makedirs(os.path.dirname(SVG_PATH) or ".", exist_ok=True)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(render_svg(m))
    for level in range(1, 6):
        with open(SIGNAL_PATH.format(level), "w", encoding="utf-8") as f:
            f.write(signal_svg(level))
    m["cards"] = write_repo_cards(m)

    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()
    s, e = readme.find(START_MARK), readme.find(END_MARK)
    if s == -1 or e == -1:
        raise SystemExit(f"Marcadores {START_MARK} / {END_MARK} não encontrados no README.md")
    updated = sync_alt_texts(readme[:s] + render_markdown(m) + readme[e + len(END_MARK):])
    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
    print(f"OK: {SVG_PATH} e README.md atualizados ({m['n']} repositórios).")

    # Confere se todo arquivo que o README aponta existe mesmo (imagem quebrada
    # no perfil é silenciosa; aqui ela aparece no log da Action).
    missing = sorted({p for p in re.findall(r'src="(assets/[^"]+)"', updated)
                      if not os.path.exists(p)})
    if missing:
        print("AVISO: o README aponta para arquivos que nao existem: " + ", ".join(missing))
    else:
        print("OK: todos os arquivos referenciados pelo README existem.")


if __name__ == "__main__":
    main()
