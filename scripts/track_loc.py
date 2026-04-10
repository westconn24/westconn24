import requests
import json
import os
from datetime import datetime, timedelta, timezone

USERNAME = "westconn24"
PAT = os.environ.get("GH_PAT")
TOKEN = PAT or os.environ.get("GITHUB_TOKEN")
DAYS_BACK = int(os.environ.get("DAYS_BACK", "1"))


headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

log_file = "loc-log.json"
try:
    with open(log_file) as f:
        log = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    log = []

today = datetime.now(timezone.utc)
dates = [
    (today - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(1, DAYS_BACK + 1)
]

for date in dates:
    print(f"\n--- {date} ---")

    search_url = "https://api.github.com/search/issues"
    params = {
        "q": f"author:{USERNAME} type:pr is:merged merged:{date}",
        "per_page": 100
    }

    response = requests.get(search_url, headers=headers, params=params)
    data = response.json()

    total_additions = 0
    total_deletions = 0
    prs_processed = []

    for item in data.get("items", []):
        pr_number = item["number"]
        pr_url = item["url"].replace("/issues/", "/pulls/")
        pr_response = requests.get(pr_url, headers=headers)

        if pr_response.status_code == 200:
            pr_data = pr_response.json()
            additions = pr_data.get("additions", 0)
            deletions = pr_data.get("deletions", 0)
            total_additions += additions
            total_deletions += deletions
            repo_full_name = pr_data["base"]["repo"]["full_name"]
            prs_processed.append({
                "repo": repo_full_name,
                "pr": pr_number,
                "title": item["title"],
                "additions": additions,
                "deletions": deletions
            })
            print(f"  PR #{pr_number} in {repo_full_name}: +{additions} -{deletions}")

    if not prs_processed:
        print("  No merged PRs found")

    print(f"  Total: +{total_additions} -{total_deletions} (net {total_additions - total_deletions})")

    entry = {
        "date": date,
        "additions": total_additions,
        "deletions": total_deletions,
        "net": total_additions - total_deletions,
        "prs": prs_processed
    }

    existing = next((e for e in log if e["date"] == date), None)
    if existing:
        existing.update(entry)
    else:
        log.append(entry)

log.sort(key=lambda x: x["date"])

with open(log_file, "w") as f:
    json.dump(log, f, indent=2)

print(f"\nLog saved to {log_file} ({len(log)} total entries)")
