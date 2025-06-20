import requests
from datetime import datetime
from statistics import stdev
from collections import Counter

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
readme_filled = 0
desc_lengths = []
undefined_langs = 0
above_avg_size_repos = []
longest_name = ("", 0)
most_words_name = ("", 0)
word_counter = Counter()
name_word_counter = Counter()

repo_stats = []

oldest_repo = {"name": None, "created_at": datetime.max}
newest_repo = {"name": None, "created_at": datetime.min}
most_forked_repo = {"name": None, "forks": -1}
most_outdated_repo = {"name": None, "updated_days": -1}
most_recently_updated_repo = {"name": None, "updated_days": 9999}
shortest_desc_repo = {"name": None, "length": float("inf")}

for repo in repos_data:
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    issues = repo["open_issues_count"]
    lang = repo["language"]
    size = repo["size"]
    updated_at = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    created_repo_at = datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - updated_at).days
    name = repo["name"]
    desc = repo.get("description") or ""

    total_stars += stars
    total_forks += forks
    size_total += size
    stars_list.append(stars)
    forks_list.append(forks)

    if lang:
        language_count[lang] = language_count.get(lang, 0) + 1
    else:
        undefined_langs += 1

    if days_since_update <= 90:
        updated_last_90 += 1
    if repo.get("has_pages"):
        pages_enabled += 1

    update_days.append(days_since_update)
    issue_counts.append(issues)
    repo_stats.append({
        "name": name,
        "stars": stars,
        "forks": forks,
        "issues": issues,
        "updated_days": days_since_update,
        "created_at": created_repo_at,
        "size": size
    })

    if created_repo_at < oldest_repo["created_at"]:
        oldest_repo = {"name": name, "created_at": created_repo_at}
    if created_repo_at > newest_repo["created_at"]:
        newest_repo = {"name": name, "created_at": created_repo_at}
    if forks > most_forked_repo["forks"]:
        most_forked_repo = {"name": name, "forks": forks}
    if days_since_update > most_outdated_repo["updated_days"]:
        most_outdated_repo = {"name": name, "updated_days": days_since_update}
    if days_since_update < most_recently_updated_repo["updated_days"]:
        most_recently_updated_repo = {"name": name, "updated_days": days_since_update}

    if desc:
        readme_filled += 1
        desc_lengths.append(len(desc))
        if len(desc) < shortest_desc_repo["length"]:
            shortest_desc_repo = {"name": name, "length": len(desc)}
        for word in desc.lower().split():
            word_counter[word.strip(".,:;()[]{}")[:30]] += 1

    if len(name) > longest_name[1]:
        longest_name = (name, len(name))

    name_word_count = len(name.split("-"))
    if name_word_count > most_words_name[1]:
        most_words_name = (name, name_word_count)

    for word in name.lower().split("-"):
        name_word_counter[word.strip(".,:;()[]{}")[:30]] += 1

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
percent_with_desc = (readme_filled / total_repos * 100) if total_repos else 0
percent_undefined_lang = (undefined_langs / total_repos * 100) if total_repos else 0
avg_desc_len = sum(desc_lengths) / len(desc_lengths) if desc_lengths else 0
above_avg_size_repos = [r["name"] for r in repo_stats if r["size"] > avg_size_kb]
top_keywords_readme = word_counter.most_common(3)
top_keywords_name = name_word_counter.most_common(3)

# === Markdown Output for Extra Stats ===
extra_stats_md = """<!--START_EXTRA_STATS-->
### 📊 Additional GitHub Repository Statistics

- 📝 Repositories with README or description: **{}**
- 🧾 % with README or description: **{:.1f}%**
- 🕳️ % without defined language: **{:.1f}%**
- ✏️ Average characters in descriptions: **{:.1f}**
- 📉 Repo with shortest description: {} ({} characters)
- 💤 Longest inactive repo: {} ({} days)
- 💾 Repositories above average size: {}
- 🔠 Longest repo name: {} ({} characters)
- 🗣️ Repo name with most words: {} ({} words)
- 🧩 Most common words in repo names: {}
- 🔤 Most common words in README/description: {}

<!--END_EXTRA_STATS-->
""".format(
    readme_filled,
    percent_with_desc,
    percent_undefined_lang,
    avg_desc_len,
    shortest_desc_repo["name"], shortest_desc_repo["length"],
    most_outdated_repo["name"], most_outdated_repo["updated_days"],
    ", ".join(above_avg_size_repos[:5]) if above_avg_size_repos else "None",
    longest_name[0], longest_name[1],
    most_words_name[0], most_words_name[1],
    ", ".join([f"{k} ({v})" for k, v in top_keywords_name]),
    ", ".join([f"{k} ({v})" for k, v in top_keywords_readme])
)

# === Update README.md ===
with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

start = readme.find("<!--START_EXTRA_STATS-->")
end = readme.find("<!--END_EXTRA_STATS-->") + len("<!--END_EXTRA_STATS-->")

if start != -1 and end != -1:
    updated_readme = readme[:start] + extra_stats_md + readme[end:]
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_readme)
else:
    print("❌ Markers <!--START_EXTRA_STATS--> or <!--END_EXTRA_STATS--> not found in README.md")
