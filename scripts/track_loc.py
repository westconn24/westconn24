import requests
import json
import os
from datetime import datetime, timedelta, timezone

USERNAME = "westconn24"
TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Tracking LOC from merged PRs for {USERNAME} on {yesterday}")

search_url = "https://api.github.com/search/issues"
params = {
    "q": f"author:{USERNAME} type:pr is:merged merged:{yesterday}",
    "per_page": 100
}

response = requests.get(search_url, headers=headers, params=params)
data = response.json()

total_additions = 0
total_deletions = 0
prs_processed = []

for item in data.get("items", []):
    parts = item["url"].split("/")
    owner = parts[5]
    repo = parts[6]
    pr_number = item["number"]

    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    pr_response = requests.get(pr_url, headers=headers)

    if pr_response.status_code == 200:
        pr_data = pr_response.json()
        additions = pr_data.get("additions", 0)
        deletions = pr_data.get("deletions", 0)
        total_additions += additions
        total_deletions += deletions
        prs_processed.append({
            "repo": f"{owner}/{repo}",
            "pr": pr_number,
            "title": item["title"],
            "additions": additions,
            "deletions": deletions
        })
        print(f"  PR #{pr_number} in {owner}/{repo}: +{additions} -{deletions}")

print(f"\nSummary for {yesterday}:")
print(f"  PRs merged: {len(prs_processed)}")
print(f"  Additions: +{total_additions}")
print(f"  Deletions: -{total_deletions}")
print(f"  Net:       {total_additions - total_deletions}")

log_file = "loc-log.json"
try:
    with open(log_file) as f:
        log = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    log = []

existing = next((e for e in log if e["date"] == yesterday), None)
if existing:
    existing.update({
        "additions": total_additions,
        "deletions": total_deletions,
        "net": total_additions - total_deletions,
        "prs": prs_processed
    })
else:
    log.append({
        "date": yesterday,
        "additions": total_additions,
        "deletions": total_deletions,
        "net": total_additions - total_deletions,
        "prs": prs_processed
    })

log.sort(key=lambda x: x["date"])

with open(log_file, "w") as f:
    json.dump(log, f, indent=2)

print(f"\nLog saved to {log_file}")
