import requests
from datetime import datetime

username = "rmayormartins"
api_user_url = f"https://api.github.com/users/{username}"
api_repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"

user_data = requests.get(api_user_url).json()
repos_data = requests.get(api_repos_url).json()

created_at = datetime.strptime(user_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
days_on_github = (datetime.now() - created_at).days
created_at_str = created_at.strftime("%Y-%m-%d")

total_repos = len(repos_data)
total_stars = 0
total_forks = 0
language_count = {}
update_days = []
issue_counts = []
repo_stats = []

oldest_repo = {"name": None, "created_at": datetime.max}
newest_repo = {"name": None, "created_at": datetime.min}
most_forked_repo = {"name": None, "forks": -1}
most_updated_repo = {"name": None, "updated_days": -1}
recently_updated_repo = {"name": None, "updated_days": 9999}

for repo in repos_data:
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    issues = repo["open_issues_count"]
    lang = repo["language"]
    updated_at = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    created_repo_at = datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - updated_at).days

    total_stars += stars
    total_forks += forks
    if lang:
        language_count[lang] = language_count.get(lang, 0) + 1

    update_days.append(days_since_update)
    issue_counts.append(issues)
    repo_stats.append({
        "name": repo["name"],
        "stars": stars,
        "forks": forks,
        "issues": issues,
        "updated_days": days_since_update,
        "created_at": created_repo_at
    })

    if created_repo_at < oldest_repo["created_at"]:
        oldest_repo = {"name": repo["name"], "created_at": created_repo_at}
    if created_repo_at > newest_repo["created_at"]:
        newest_repo = {"name": repo["name"], "created_at": created_repo_at}
    if forks > most_forked_repo["forks"]:
        most_forked_repo = {"name": repo["name"], "forks": forks}
    if days_since_update > most_updated_repo["updated_days"]:
        most_updated_repo = {"name": repo["name"], "updated_days": days_since_update}
    if days_since_update < recently_updated_repo["updated_days"]:
        recently_updated_repo = {"name": repo["name"], "updated_days": days_since_update}

avg_stars = total_stars / total_repos if total_repos else 0
avg_forks = total_forks / total_repos if total_repos else 0
avg_update_days = sum(update_days) / total_repos if total_repos else 0
avg_issues = sum(issue_counts) / total_repos if total_repos else 0
top_language = max(language_count.items(), key=lambda x: x[1])[0] if language_count else "N/A"
top_languages = sorted(language_count.items(), key=lambda x: x[1], reverse=True)[:3]
repos_with_5plus_stars = len([r for r in repo_stats if r["stars"] >= 5])
unique_languages = len(language_count)

top_issues = sorted(repo_stats, key=lambda x: x["issues"], reverse=True)[:3]
top_starred = sorted(repo_stats, key=lambda x: x["stars"], reverse=True)[:3]

badges = []
if total_repos >= 30:
    badges.append("🥇 Repositórios 30+")
if total_forks >= 50:
    badges.append("🍴 Forks 50+")
if total_stars >= 20:
    badges.append("🌟 Estrelas 20+")
if days_on_github >= 365 * 5:
    badges.append("🕰️ Conta 5+ anos")
if avg_update_days < 90:
    badges.append("⚡ Manutenção ativa (< 90 dias)")

# Markdown format
markdown_output = """<!--START_STATS-->
#### My Stats Action

- 🔢 Repositórios públicos: **{}**
- ⭐ Total de estrelas: **{}** (média: {:.2f})
- 🍴 Total de forks: **{}** (média: {:.2f})
- 🏷️ Linguagem mais comum: **{}**
- 📆 Dias no GitHub: **{} dias** (desde {})
- ⌛ Média de dias sem atualização: **{:.1f}**
- 🐞 Média de issues por repo: **{:.2f}**
- 📚 Linguagens distintas: **{}**
- 🔝 Top linguagens: {}
- 💫 Repositórios com 5+ estrelas: **{}**
- 🔁 Repo mais bifurcado: `{}` ({} forks)
- ⏱️ Repo mais tempo sem update: `{}` ({} dias)
- 🔄 Atualização mais recente: `{}` (há {} dias)
- 🏅 Conquistas: {}

**Top repositórios por issues abertas:**""".format(
    total_repos, total_stars, avg_stars,
    total_forks, avg_forks, top_language,
    days_on_github, created_at_str, avg_update_days,
    avg_issues, unique_languages,
    ", ".join([f"{lang} ({count})" for lang, count in top_languages]),
    repos_with_5plus_stars,
    most_forked_repo["name"], most_forked_repo["forks"],
    most_updated_repo["name"], most_updated_repo["updated_days"],
    recently_updated_repo["name"], recently_updated_repo["updated_days"],
    ' | '.join(badges) if badges else 'Nenhuma ainda'
)

for r in top_issues:
    markdown_output += f"\n- `{r['name']}`: {r['issues']} issues, {r['stars']} ⭐, {r['forks']} 🍴, atualizado há {r['updated_days']} dias"

markdown_output += "\n\n**Top repositórios por estrelas:**"
for r in top_starred:
    markdown_output += f"\n- `{r['name']}`: {r['stars']} ⭐, {r['forks']} 🍴, atualizado há {r['updated_days']} dias"

markdown_output += f"\n\n**📜 Primeiro repo:** `{oldest_repo['name']}` (criado em {oldest_repo['created_at'].date()})\n"
markdown_output += f"\n**🆕 Mais recente:** `{newest_repo['name']}` (criado em {newest_repo['created_at'].date()})"
markdown_output += "\n<!--END_STATS-->\n"

# Atualizar o README.md entre os marcadores
with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

start = readme.find("<!--START_STATS-->")
end = readme.find("<!--END_STATS-->") + len("<!--END_STATS-->")

if start != -1 and end != -1:
    updated_readme = readme[:start] + markdown_output + readme[end:]
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_readme)
else:
    print("❌ Marcadores <!--START_STATS--> ou <!--END_STATS--> não encontrados no README.md")
