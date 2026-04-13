"""
track_loc - Tracks ALL commits across active repos and all branches.
Uses the Events API to discover repos with recent pushes, then fetches
per-repo commits for full coverage. No pip dependencies (stdlib only).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("GH_USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
if not USERNAME:
    raise SystemExit("Could not determine GitHub username. Set GH_USERNAME env var.")

TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("No token. Set GH_PAT secret.")

DAYS_BACK = int(os.environ.get("DAYS_BACK", "1"))
EXCLUDE_EXTS = {".md", ".rst", ".txt", ".csv"}


def api_get(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Authorization", f"token {TOKEN}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 409:  # empty repo
            return []
        raise


def api_get_paginated(url, params=None, max_per_page=100):
    params = dict(params or {})
    params.setdefault("per_page", max_per_page)
    all_items = []
    page = 1
    while True:
        params["page"] = page
        items = api_get(url, params)
        if not isinstance(items, list) or not items:
            break
        all_items.extend(items)
        if len(items) < int(params["per_page"]):
            break
        page += 1
    return all_items


def find_active_repos():
    """Use the Events API to find repos the user has recently pushed to."""
    repos = set()
    for page in range(1, 11):
        events = api_get(
            f"https://api.github.com/users/{USERNAME}/events",
            {"per_page": 30, "page": page},
        )
        if not events:
            break
        for event in events:
            if event.get("type") == "PushEvent":
                repos.add(event["repo"]["name"])
        if len(events) < 30:
            break
    return sorted(repos)


def get_repo_commits(repo, since, until):
    """Get all commits by USERNAME in a repo, across all branches."""
    branches = api_get_paginated(f"https://api.github.com/repos/{repo}/branches")

    seen_shas = set()
    all_commits = []

    for branch in branches:
        commits = api_get_paginated(
            f"https://api.github.com/repos/{repo}/commits",
            {"author": USERNAME, "since": since, "until": until, "sha": branch["name"]},
        )
        for c in commits:
            if c["sha"] not in seen_shas:
                seen_shas.add(c["sha"])
                all_commits.append(c)

    return all_commits


def get_commit_file_stats(repo, sha):
    """Fetch file-level stats for a commit, excluding doc files."""
    data = api_get(f"https://api.github.com/repos/{repo}/commits/{sha}")
    additions = 0
    deletions = 0
    for f in data.get("files", []):
        ext = "." + f["filename"].rsplit(".", 1)[-1] if "." in f["filename"] else ""
        if ext.lower() not in EXCLUDE_EXTS:
            additions += f.get("additions", 0)
            deletions += f.get("deletions", 0)
    return additions, deletions


# --- Main ---

log_file = "loc-log-commits.json"
try:
    with open(log_file) as f:
        log = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    log = []

today = datetime.now(timezone.utc)
since = (today - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%dT00:00:00Z")
until = (today + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

# Discover repos from push events
print(f"Finding repos {USERNAME} has pushed to...")
repos = find_active_repos()
print(f"Active repos: {', '.join(repos)}\n")

# Collect all commits across repos, grouped by date
by_date = defaultdict(list)
seen_shas = set()

for i, repo in enumerate(repos):
    sys.stdout.write(f"\r  [{i+1}/{len(repos)}] {repo:<50}")
    sys.stdout.flush()

    try:
        commits = get_repo_commits(repo, since, until)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404, 451):
            continue
        raise

    for c in commits:
        sha = c["sha"]
        if sha in seen_shas:
            continue
        seen_shas.add(sha)

        # Skip merge commits
        if len(c.get("parents", [])) > 1:
            continue

        date_str = c["commit"]["author"]["date"][:10]
        by_date[date_str].append((repo, c))

print(f"\r  Scanned {len(repos)} repos, found {len(seen_shas)} unique commits" + " " * 30)

# Include all dates in range even if no commits
all_dates = set()
for i in range(DAYS_BACK + 1):
    all_dates.add((today - timedelta(days=i)).strftime("%Y-%m-%d"))
all_dates.update(by_date.keys())

for date in sorted(all_dates):
    print(f"\n--- {date} ---")
    day_commits = by_date.get(date, [])

    commits_processed = []
    total_add = 0
    total_del = 0

    for repo, c in day_commits:
        sha = c["sha"]
        msg = c["commit"]["message"].split("\n")[0]

        try:
            additions, deletions = get_commit_file_stats(repo, sha)
        except urllib.error.HTTPError as e:
            print(f"  error fetching {sha[:7]}: {e.code}")
            continue

        total_add += additions
        total_del += deletions

        commits_processed.append({
            "repo": repo,
            "sha": sha[:7],
            "message": msg[:80],
            "additions": additions,
            "deletions": deletions,
        })
        print(f"  {sha[:7]} {repo}: +{additions} -{deletions}  {msg[:60]}")

    if not commits_processed:
        print("  No commits found")

    net = total_add - total_del
    print(f"  Total: +{total_add} -{total_del} (net {net})")

    entry = {
        "date": date,
        "additions": total_add,
        "deletions": total_del,
        "net": net,
        "commits": commits_processed,
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
