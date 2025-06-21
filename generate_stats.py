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

# === Statistics ===
total_repos = len(repos_data)
total_stars = 0
total_forks = 0
language_count = {}
update_days = []
issue_counts = []
desc_lengths = []
undefined_langs = 0
readme_filled = 0
repo_sizes = []
repo_name_lengths = []
repo_name_words = []
word_counter = Counter()
name_word_counter = Counter()

shortest_desc_repo = {"name": None, "length": float("inf")}
most_outdated_repo = {"name": None, "updated_days": -1}
above_avg_size_repos = []
longest_name = ("", 0)
most_words_name = ("", 0)

for repo in repos_data:
    name = repo["name"]
    desc = repo.get("description") or ""
    lang = repo["language"]
    updated_at = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - updated_at).days
    size = repo["size"]

    update_days.append(days_since_update)
    repo_sizes.append(size)
    repo_name_lengths.append(len(name))
    repo_name_words.append(len(name.split("-")))

    if lang is None:
        undefined_langs += 1

    if desc:
        readme_filled += 1
        desc_lengths.append(len(desc))
        if len(desc) < shortest_desc_repo["length"]:
            shortest_desc_repo = {"name": name, "length": len(desc)}
        for word in desc.lower().split():
            word_counter[word.strip(".,:;()[]{}")[:30]] += 1

    if days_since_update > most_outdated_repo["updated_days"]:
        most_outdated_repo = {"name": name, "updated_days": days_since_update}

    if len(name) > longest_name[1]:
        longest_name = (name, len(name))

    word_count = len(name.split("-"))
    if word_count > most_words_name[1]:
        most_words_name = (name, word_count)

    for word in name.lower().split("-"):
        name_word_counter[word.strip(".,:;()[]{}")[:30]] += 1

avg_desc_len = sum(desc_lengths) / len(desc_lengths) if desc_lengths else 0
avg_size = sum(repo_sizes) / len(repo_sizes) if repo_sizes else 0
percent_with_desc = (readme_filled / total_repos * 100) if total_repos else 0
percent_undefined_lang = (undefined_langs / total_repos * 100) if total_repos else 0
above_avg_size_repos = [repo["name"] for repo in repos_data if repo["size"] > avg_size]
top_keywords_readme = word_counter.most_common(3)
top_keywords_name = name_word_counter.most_common(3)

extra_stats_md = """<!--START_EXTRA_STATS-->
### 📊 Additional GitHub Repository Statistics

- 📝 Repositories with README or description: **{}**
- 🧾 % with README or description: **{:.1f}%**
- 🕳️ % without defined language: **{:.1f}%**
- ✏️ Average characters in descriptions: **{:.1f}**
- 📉 Repo with shortest description: `{}` ({} characters)
- 💤 Longest inactive repo: `{}` ({} days)
- 💾 Repositories above average size: {}
- 🔠 Longest repo name: `{}` ({} characters)
- 🗣️ Repo name with most words: `{}` ({} words)
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
