import requests
from datetime import datetime

username = "rmayormartins"
output_file = "stats.md"
repos = requests.get(f"https://api.github.com/users/{username}/repos").json()

total_stars = 0
total_forks = 0
language_count = {}
update_days = []
repo_stats = []

for repo in repos:
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    issues = repo["open_issues_count"]
    lang = repo["language"]
    updated = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_ago = (datetime.now() - updated).days

    total_stars += stars
    total_forks += forks
    if lang:
        language_count[lang] = language_count.get(lang, 0) + 1
    update_days.append(days_ago)
    repo_stats.append((repo["name"], issues, stars, forks, days_ago))

top_lang = max(language_count, key=language_count.get)
repo_count = len(repos)
avg_stars = total_stars / repo_count
avg_days = sum(update_days) / repo_count
stars_list = [r[2] for r in repo_stats]
forks_list = [r[3] for r in repo_stats]
top_issues = sorted(repo_stats, key=lambda x: x[1], reverse=True)[:3]

# Lê README original
with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

# Atualiza o trecho entre "#### My Stats Action" e "---"
prefix = "#### My Stats Action"
suffix = "\n---"

start = content.find(prefix)
end = content.find(suffix, start)

new_section = f"""{prefix}

- 🔢 Repositórios públicos: **{repo_count}**
- ⭐ Total de estrelas: **{total_stars}** (média: {avg_stars:.2f})
- 🍴 Total de forks: **{total_forks}** (média: {sum(forks_list)/repo_count:.2f})
- 🏷️ Linguagem mais comum: **{top_lang}**
- ⌛ Média de dias sem atualização: **{avg_days:.1f}**

**Repositórios com mais issues abertas:**\n"""
for r in top_issues:
    new_section += f"- `{r[0]}`: {r[1]} issues, {r[2]} ⭐, {r[3]} 🍴, atualizado há {r[4]} dias\n"

# Atualiza o conteúdo
new_content = content[:start] + new_section + "\n" + content[end:]

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_content)
