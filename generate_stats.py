import requests
from datetime import datetime

# === Configurações ===
username = "rmayormartins"
api_user_url = f"https://api.github.com/users/{username}"
api_repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"

# === Requisições ===
user_data = requests.get(api_user_url).json()
repos_data = requests.get(api_repos_url).json()

# === Dados gerais do usuário ===
created_at = datetime.strptime(user_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
days_on_github = (datetime.now() - created_at).days
created_at_str = created_at.strftime("%Y-%m-%d")

# === Estatísticas de repositórios ===
total_repos = len(repos_data)
total_stars = 0
total_forks = 0
language_count = {}
update_days = []
issue_counts = []
repo_stats = []

oldest_repo = {"name": None, "created_at": datetime.max}
newest_repo = {"name": None, "created_at": datetime.min}

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

# === Cálculos estatísticos ===
avg_stars = total_stars / total_repos if total_repos else 0
avg_forks = total_forks / total_repos if total_repos else 0
avg_update_days = sum(update_days) / total_repos if total_repos else 0
avg_issues = sum(issue_counts) / total_repos if total_repos else 0
top_language = max(language_count.items(), key=lambda x: x[1])[0] if language_count else "N/A"

# === Top issues e estrelas ===
top_issues = sorted(repo_stats, key=lambda x: x["issues"], reverse=True)[:3]
top_starred = sorted(repo_stats, key=lambda x: x["stars"], reverse=True)[:3]

# === Badges simbólicas ===
badges = []
if total_repos >= 30:
    badges.append("🏇 Repositórios 30+")
if total_forks >= 50:
    badges.append("🍴 Forks 50+")
if total_stars >= 20:
    badges.append("🌟 Estrelas 20+")
if days_on_github >= 365 * 5:
    badges.append("🕰️ Conta 5+ anos")
if avg_update_days < 90:
    badges.append("⚡ Manutenção ativa (< 90 dias)")

# === Formatar saída final ===
markdown_output = f"""#### My Stats Action

- 📂 Repositórios públicos: **{total_repos}**
- ⭐ Total de estrelas: **{total_stars}** (média: {avg_stars:.2f})
- 🍴 Total de forks: **{total_forks}** (média: {avg_forks:.2f})
- 🏷️ Linguagem mais comum: **{top_language}**
- 🗖️ Dias no GitHub: **{days_on_github} dias** (desde {created_at_str})
- ⌛ Média de dias sem atualização: **{avg_update_days:.1f}**
- 🐞 Média de issues por repo: **{avg_issues:.2f}**
- 🏅 Conquistas: {' | '.join(badges) if badges else 'Nenhuma ainda'}

**Top repositórios por issues abertas:**"""
for r in top_issues:
    markdown_output += f"\n- `{r['name']}`: {r['issues']} issues, {r['stars']} ⭐, {r['forks']} 🍴, atualizado há {r['updated_days']} dias"

markdown_output += "\n\n**Top repositórios por estrelas:**"
for r in top_starred:
    markdown_output += f"\n- `{r['name']}`: {r['stars']} ⭐, {r['forks']} 🍴, atualizado há {r['updated_days']} dias"

markdown_output += f"\n\n**📜 Primeiro repo:** `{oldest_repo['name']}` (criado em {oldest_repo['created_at'].date()})"
markdown_output += f"\n**🆕 Mais recente:** `{newest_repo['name']}` (criado em {newest_repo['created_at'].date()})"

# === Gravar no README.md ===
with open("README.md", "r", encoding="utf-8") as f:
    readme_content = f.read()

start_marker = "#### My Stats Action"
end_marker = "---"

before = readme_content.split(start_marker)[0]
after = ""

# Captura tudo após a próxima ocorrência de --- (duas vezes para preservar estrutura do README)
split_parts = readme_content.split(start_marker)
if len(split_parts) > 1:
    after_parts = split_parts[1].split(end_marker, 1)
    if len(after_parts) > 1:
        after = end_marker + after_parts[1]

with open("README.md", "w", encoding="utf-8") as f:
    f.write(before + markdown_output + "\n\n" + after)

print("README.md atualizado com sucesso!")
