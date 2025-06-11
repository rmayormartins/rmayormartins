import requests
from datetime import datetime
from statistics import stdev

# === Configuration ===
username = "rmayormartins"
api_user_url = f"https://api.github.com/users/{username}"
api_repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"

# === Data Collection ===
user_data = requests.get(api_user_url).json()
repos_data = requests.get(api_repos_url).json()

# === Account Info ===
created_at = datetime.strptime(user_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
days_on_github = (datetime.now() - created_at).days
created_at_str = created_at.strftime("%Y-%m-%d")

# === Statistics ===
total_repos = len(repos_data)
total_stars = 0
total_forks = 0
language_count = {}
update_days = []
issue_counts = []
stars_list = []
forks_list = []
size_total = 0
updated_last_90 = 0
pages_enabled = 0

repo_stats = []

oldest_repo = {"name": None, "created_at": datetime.max}
newest_repo = {"name": None, "created_at": datetime.min}
most_forked_repo = {"name": None, "forks": -1}
most_outdated_repo = {"name": None, "updated_days": -1}
most_recently_updated_repo = {"name": None, "updated_days": 9999}

for repo in repos_data:
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    issues = repo["open_issues_count"]
    lang = repo["language"]
    size = repo["size"]
    updated_at = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    created_repo_at = datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - updated_at).days

    total_stars += stars
    total_forks += forks
    size_total += size
    stars_list.append(stars)
    forks_list.append(forks)

    if lang:
        language_count[lang] = language_count.get(lang, 0) + 1
    if days_since_update <= 90:
        updated_last_90 += 1
    if repo.get("has_pages"):
        pages_enabled += 1

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
    if days_since_update > most_outdated_repo["updated_days"]:
        most_outdated_repo = {"name": repo["name"], "updated_days": days_since_update}
    if days_since_update < most_recently_updated_repo["updated_days"]:
        most_recently_updated_repo = {"name": repo["name"], "updated_days": days_since_update}

# === Final Calculations ===
avg_stars = total_stars / total_repos if total_repos else 0
avg_forks = total_forks / total_repos if total_repos else 0
avg_update_days = sum(update_days) / total_repos if total_repos else 0
avg_issues = sum(issue_counts) / total_repos if total_repos else 0
avg_size_kb = size_total / total_repos if total_repos else 0
top_language = max(language_count.items(), key=lambda x: x[1])[0] if language_count else "N/A"
top_languages = sorted(language_count.items(), key=lambda x: x[1], reverse=True)[:3]
repos_with_5plus_stars = len([r for r in repo_stats if r["stars"] >= 5])
unique_languages = len(language_count)
percent_updated_90 = (updated_last_90 / total_repos * 100) if total_repos else 0

repos_with_issues = len([r for r in repo_stats if r["issues"] > 0])
zero_star_repos = len([r for r in repo_stats if r["stars"] == 0])
forks_greater_than_stars = len([r for r in repo_stats if r["forks"] > r["stars"]])
std_stars = stdev(stars_list) if total_repos > 1 else 0
std_forks = stdev(forks_list) if total_repos > 1 else 0

top_issues = sorted(repo_stats, key=lambda x: x["issues"], reverse=True)[:3]
top_starred = sorted(repo_stats, key=lambda x: x["stars"], reverse=True)[:3]

# === Symbolic Badges ===
badges = []
if total_repos >= 30:
    badges.append("🥇 30+ Repositories")
if total_forks >= 50:
    badges.append("🍴 50+ Forks")
if total_stars >= 20:
    badges.append("🌟 20+ Stars")
if days_on_github >= 365 * 5:
    badges.append("🕰️ 5+ Years Account")
if avg_update_days < 90:
    badges.append("⚡ Active Maintenance (< 90 days)")

# === Markdown Output ===
markdown_output = """<!--START_STATS-->
#### My Stats Action

- 🔢 Public repositories: **{}**
- ⭐ Total stars: **{}** (avg: {:.2f})
- 🍴 Total forks: **{}** (avg: {:.2f})
- 📦 Avg repo size: **{:.1f} KB**
- 📆 Days on GitHub: **{} days** (since {})
- 🏷️ Most common language: **{}**
- 📚 Unique languages: **{}**
- 🔝 Top languages: {}
- 📊 % updated in last 90 days: **{:.1f}%**
- 🔁 Most forked repo: `{}` ({} forks)
- ⏱️ Longest inactive repo: `{}` ({} days)
- 🔄 Most recently updated repo: `{}` ({} days ago)
- 🐞 Avg issues per repo: **{:.2f}**
- 💫 Repositories with 5+ stars: **{}**
- 🌐 GitHub Pages repos: **{}**
- 🧵 Repos with open issues: **{}**
- 🪙 Repos with 0 stars: **{}**
- ⚖️ Forks > Stars: **{}**
- 📈 Star standard deviation: **{:.2f}**
- 📉 Forks standard deviation: **{:.2f}**
- 🏅 Achievements: {}

**Top repositories by open issues:**""".format(
    total_repos, total_stars, avg_stars,
    total_forks, avg_forks, avg_size_kb,
    days_on_github, created_at_str,
    top_language, unique_languages,
    ", ".join([f"{lang} ({count})" for lang, count in top_languages]),
    percent_updated_90,
    most_forked_repo["name"], most_forked_repo["forks"],
    most_outdated_repo["name"], most_outdated_repo["updated_days"],
    most_recently_updated_repo["name"], most_recently_updated_repo["updated_days"],
    avg_issues, repos_with_5plus_stars, pages_enabled,
    repos_with_issues, zero_star_repos, forks_greater_than_stars,
    std_stars, std_forks,
    ' | '.join(badges) if badges else 'None yet'
)

for r in top_issues:
    markdown_output += f"\n- `{r['name']}`: {r['issues']} issues, {r['stars']} ⭐, {r['forks']} 🍴, updated {r['updated_days']} days ago"

markdown_output += "\n\n**Top repositories by stars:**"
for r in top_starred:
    markdown_output += f"\n- `{r['name']}`: {r['stars']} ⭐, {r['forks']} 🍴, updated {r['updated_days']} days ago"

markdown_output += f"\n\n**📜 First repository:** `{oldest_repo['name']}` (created on {oldest_repo['created_at'].date()})"
markdown_output += f"\n\n**🆕 Newest repository:** `{newest_repo['name']}` (created on {newest_repo['created_at'].date()})"
markdown_output += "\n<!--END_STATS-->\n"

# === Update README.md ===
with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

start = readme.find("<!--START_STATS-->")
end = readme.find("<!--END_STATS-->") + len("<!--END_STATS-->")

if start != -1 and end != -1:
    updated_readme = readme[:start] + markdown_output + readme[end:]
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_readme)
else:
    print("❌ Markers <!--START_STATS--> or <!--END_STATS--> not found in README.md")
