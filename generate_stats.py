!pip install requests

import requests
from datetime import datetime
from statistics import stdev
import re
from collections import Counter
import pandas as pd

# === Configuration ===
username = "rmayormartins"
api_user_url = f"https://api.github.com/users/{username}"
api_repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"

# === Data Collection ===
user_data = requests.get(api_user_url).json()
repos_data = requests.get(api_repos_url).json()

# === Advanced Stats Initialization ===
readme_present_count = 0
language_none_count = 0
description_lengths = []
longest_name = {"name": "", "length": 0}
most_words_in_name = {"name": "", "words": 0}
longest_inactive = {"name": "", "days": -1}
above_avg_size_repos = []

repo_name_keywords = []

total_size = 0
update_days = []

repo_stats = []

for repo in repos_data:
    name = repo["name"]
    lang = repo["language"]
    description = repo["description"] or ""
    size = repo["size"]
    updated_at = datetime.strptime(repo["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - updated_at).days

    total_size += size
    update_days.append(days_since_update)

    if "readme" in name.lower() or description.strip():
        readme_present_count += 1
    if lang is None:
        language_none_count += 1

    description_lengths.append(len(description))

    if len(name) > longest_name["length"]:
        longest_name = {"name": name, "length": len(name)}

    word_count = len(name.replace("-", " ").replace("_", " ").split())
    if word_count > most_words_in_name["words"]:
        most_words_in_name = {"name": name, "words": word_count}

    if days_since_update > longest_inactive["days"]:
        longest_inactive = {"name": name, "days": days_since_update}

    repo_name_keywords += re.findall(r"[a-zA-Z]+", name.lower())

    repo_stats.append({
        "name": name,
        "description_len": len(description),
        "days_since_update": days_since_update,
        "size": size
    })

avg_size = total_size / len(repos_data)
above_avg_size_repos = [r["name"] for r in repo_stats if r["size"] > avg_size]

min_description_repo = min(repo_stats, key=lambda x: x["description_len"])
most_frequent_name_keywords = Counter(repo_name_keywords).most_common(5)

results = pd.DataFrame({
    "Estatística": [
        "Repositórios com README ou descrição",
        "Porcentagem com README ou descrição",
        "Porcentagem sem linguagem definida",
        "Média de caracteres na descrição",
        "Repositório com menor descrição",
        "Repositório mais inativo",
        "Repositórios acima da média de tamanho",
        "Nome mais longo de repositório",
        "Nome com mais palavras",
        "Palavras-chave mais comuns no nome dos repositórios"
    ],
    "Valor": [
        readme_present_count,
        f"{readme_present_count / len(repos_data) * 100:.2f}%",
        f"{language_none_count / len(repos_data) * 100:.2f}%",
        f"{sum(description_lengths) / len(description_lengths):.2f}",
        f"{min_description_repo['name']} ({min_description_repo['description_len']} caracteres)",
        f"{longest_inactive['name']} ({longest_inactive['days']} dias)",
        ", ".join(above_avg_size_repos),
        f"{longest_name['name']} ({longest_name['length']} caracteres)",
        f"{most_words_in_name['name']} ({most_words_in_name['words']} palavras)",
        ", ".join([f"{word} ({count})" for word, count in most_frequent_name_keywords])
    ]
})

results
