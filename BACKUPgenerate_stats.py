"""
generate_stats.py
Atualiza o bloco "My Stats Action" do README.md entre os marcadores
<!--START_STATS--> e <!--END_STATS--> usando a API do GitHub.

Compatível com o formato atual do README do usuário rmayormartins.
"""

import os
import requests
from datetime import datetime
from statistics import stdev
from collections import Counter

# === Configuracao ===
USERNAME = "rmayormartins"
README_PATH = "README.md"
START_MARK = "<!--START_STATS-->"
END_MARK = "<!--END_STATS-->"

# Token opcional (evita rate limit; o workflow ja passa GITHUB_TOKEN)
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

API_USER = f"https://api.github.com/users/{USERNAME}"
API_REPOS = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated"


def fetch_all_repos():
    """Pagina todos os repositorios publicos do usuario."""
    repos = []
    page = 1
    while True:
        url = f"{API_REPOS}&page={page}"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        chunk = resp.json()
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


def main():
    user = requests.get(API_USER, headers=HEADERS, timeout=30).json()
    repos = fetch_all_repos()

    # Filtra forks (estatisticas focam em repos proprios; ajuste se preferir incluir)
    repos = [r for r in repos if not r.get("fork", False)]

    now = datetime.utcnow()
    created_at = datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_on_github = (now - created_at).days

    total_repos = len(repos)
    total_stars = sum(r["stargazers_count"] for r in repos)
    total_forks = sum(r["forks_count"] for r in repos)
    sizes = [r["size"] for r in repos]
    avg_size = sum(sizes) / total_repos if total_repos else 0

    # Linguagens
    langs = [r["language"] for r in repos if r["language"]]
    lang_counter = Counter(langs)
    top_langs = lang_counter.most_common(3)
    most_common_lang = top_langs[0][0] if top_langs else "N/A"
    unique_langs = len(lang_counter)

    # Atividade recente
    updated_days = []
    recent_90 = 0
    for r in repos:
        upd = datetime.strptime(r["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        d = (now - upd).days
        updated_days.append((r["name"], d))
        if d <= 90:
            recent_90 += 1
    percent_recent = (recent_90 / total_repos * 100) if total_repos else 0

    longest_inactive = max(updated_days, key=lambda x: x[1]) if updated_days else ("N/A", 0)
    most_recent = min(updated_days, key=lambda x: x[1]) if updated_days else ("N/A", 0)

    # Forks / Stars detalhes
    most_forked = max(repos, key=lambda r: r["forks_count"]) if repos else None
    issues = [r["open_issues_count"] for r in repos]
    avg_issues = sum(issues) / total_repos if total_repos else 0
    repos_5plus_stars = sum(1 for r in repos if r["stargazers_count"] >= 5)
    repos_pages = sum(1 for r in repos if r.get("has_pages"))
    repos_with_issues = sum(1 for r in repos if r["open_issues_count"] > 0)
    repos_zero_stars = sum(1 for r in repos if r["stargazers_count"] == 0)
    forks_gt_stars = sum(1 for r in repos if r["forks_count"] > r["stargazers_count"])

    star_list = [r["stargazers_count"] for r in repos]
    fork_list = [r["forks_count"] for r in repos]
    star_std = stdev(star_list) if len(star_list) > 1 else 0
    fork_std = stdev(fork_list) if len(fork_list) > 1 else 0

    # Tops por issues e stars
    top_by_issues = sorted(repos, key=lambda r: r["open_issues_count"], reverse=True)[:3]
    top_by_stars = sorted(repos, key=lambda r: r["stargazers_count"], reverse=True)[:3]

    # Primeiro / mais novo repo (pedimos sort=updated, entao usamos created_at)
    sorted_by_created = sorted(repos, key=lambda r: r["created_at"])
    first_repo = sorted_by_created[0] if sorted_by_created else None
    newest_repo = sorted_by_created[-1] if sorted_by_created else None

    # Achievements (texto livre, condicional)
    badges = []
    if total_repos >= 30:
        badges.append("🥇 30+ Repositories")
    if total_forks >= 50:
        badges.append("🍴 50+ Forks")
    if total_stars >= 20:
        badges.append("🌟 20+ Stars")
    if days_on_github >= 5 * 365:
        badges.append("🕰️ 5+ Years Account")
    badges_line = " | ".join(badges) if badges else "—"

    avg_stars = total_stars / total_repos if total_repos else 0
    avg_forks = total_forks / total_repos if total_repos else 0

    def fmt_days_ago(d):
        return f"{d} day{'s' if d != 1 else ''} ago"

    def line_repo(r):
        upd = datetime.strptime(r["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        d = (now - upd).days
        return (
            f"- {r['name']}: {r['open_issues_count']} issues, "
            f"{r['stargazers_count']} ⭐, {r['forks_count']} 🍴, updated {fmt_days_ago(d)}"
        )

    def line_repo_stars(r):
        upd = datetime.strptime(r["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        d = (now - upd).days
        return (
            f"- {r['name']}: {r['stargazers_count']} ⭐, "
            f"{r['forks_count']} 🍴, updated {fmt_days_ago(d)}"
        )

    block = []
    block.append(START_MARK)
    block.append("#### My Stats Action")
    block.append("")
    block.append(f"- 🔢 Public repositories: **{total_repos}**")
    block.append(f"- ⭐ Total stars: **{total_stars}** (avg: {avg_stars:.2f})")
    block.append(f"- 🍴 Total forks: **{total_forks}** (avg: {avg_forks:.2f})")
    block.append(f"- 📦 Avg repo size: **{avg_size:.1f} KB**")
    block.append(f"- 📆 Days on GitHub: **{days_on_github} days** (since {created_at.strftime('%Y-%m-%d')})")
    block.append(f"- 🏷️ Most common language: **{most_common_lang}**")
    block.append(f"- 📚 Unique languages: **{unique_langs}**")
    block.append(f"- 🔝 Top languages: {', '.join(f'{n} ({c})' for n, c in top_langs)}")
    block.append(f"- 📊 % updated in last 90 days: **{percent_recent:.1f}%**")
    if most_forked:
        block.append(f"- 🔁 Most forked repo: {most_forked['name']} ({most_forked['forks_count']} forks)")
    block.append(f"- ⏱️ Longest inactive repo: {longest_inactive[0]} ({longest_inactive[1]} days)")
    block.append(f"- 🔄 Most recently updated repo: {most_recent[0]} ({most_recent[1]} days ago)")
    block.append(f"- 🐞 Avg issues per repo: **{avg_issues:.2f}**")
    block.append(f"- 💫 Repositories with 5+ stars: **{repos_5plus_stars}**")
    block.append(f"- 🌐 GitHub Pages repos: **{repos_pages}**")
    block.append(f"- 🧵 Repos with open issues: **{repos_with_issues}**")
    block.append(f"- 🪙 Repos with 0 stars: **{repos_zero_stars}**")
    block.append(f"- ⚖️ Forks > Stars: **{forks_gt_stars}**")
    block.append(f"- 📈 Star standard deviation: **{star_std:.2f}**")
    block.append(f"- 📉 Forks standard deviation: **{fork_std:.2f}**")
    block.append(f"- 🏅 Achievements: {badges_line}")
    block.append("")
    block.append("**Top repositories by open issues:**")
    for r in top_by_issues:
        block.append(line_repo(r))
    block.append("")
    block.append("**Top repositories by stars:**")
    for r in top_by_stars:
        block.append(line_repo_stars(r))
    block.append("")
    if first_repo:
        block.append(f"**📜 First repository:** {first_repo['name']} (created on {first_repo['created_at'][:10]})")
        block.append("")
    if newest_repo:
        block.append(f"**🆕 Newest repository:** {newest_repo['name']} (created on {newest_repo['created_at'][:10]})")
    block.append(END_MARK)

    new_block = "\n".join(block)

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    s = readme.find(START_MARK)
    e = readme.find(END_MARK)
    if s == -1 or e == -1:
        raise SystemExit(f"❌ Marcadores {START_MARK} / {END_MARK} nao encontrados no README.md")

    updated = readme[:s] + new_block + readme[e + len(END_MARK):]

    if updated == readme:
        print("ℹ️ Sem mudancas nas estatisticas.")
    else:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
        print("✅ README.md atualizado com sucesso.")


if __name__ == "__main__":
    main()
