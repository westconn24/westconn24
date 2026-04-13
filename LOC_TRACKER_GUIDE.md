# Benmore LOC Tracker — Team Guide

## What Is This?

A system that automatically tracks each developer's lines of code output per day using two methods:

1. **PR Tracker** (`loc.py`) — counts lines from merged pull requests
2. **Commit Tracker** (`loctest.py`) — counts lines from every individual commit across all repos and branches

Both run daily via a single GitHub Action. Numbers update every morning with no manual effort after setup.

**What it tracks:**
- Lines added and deleted per day
- Code only — `.md`, `.rst`, `.txt`, `.csv` files excluded
- Refactor-heavy items automatically filtered (>15k deletions ignored by default)
- Merge commits excluded from commit tracker to prevent double-counting

**Privacy:** Data lives in each developer's private `{username}/loc-data` repo. Only accessible to people with a GitHub PAT that has `repo` scope.

---

## PR Tracker vs Commit Tracker

| | PR Tracker (`loc.py`) | Commit Tracker (`loctest.py`) |
|---|---|---|
| **Data source** | Merged PRs only | All commits across all branches |
| **Captures** | Code that went through PR review | Everything — direct pushes, branch work, non-PR commits |
| **Double-counting** | Yes — merge PRs (dev→main) re-count the same lines | No — each commit counted once, merge commits skipped |
| **Best for** | Tracking reviewed/shipped code | Tracking total development output |
| **Log file** | `loc-log.json` | `loc-log-commits.json` |

**Which should I use?** The commit tracker gives a more accurate picture of actual work done. The PR tracker can overcount when code flows through branch hierarchies (feature→dev→staging→main), since each merge PR re-counts the full diff. Use commit tracker for total output, PR tracker for shipped/reviewed code.

---

## How It Works

1. A GitHub Action runs in each developer's private `{username}/loc-data` repo every morning at 6 AM UTC
2. **PR tracker** scans all merged PRs from the previous day → saves to `loc-log.json`
3. **Commit tracker** discovers repos via the Events API, scans all branches for commits → saves to `loc-log-commits.json`
4. Both strip out doc/data files and apply the same exclusion rules
5. The CLIs (`loc.py` and `loctest.py`) read those files using a PAT

---

## Fresh Setup (New Developer — ~5 min)

### Step 1 — Create a PAT

Go to: `github.com/settings/tokens` → **Generate new token (classic)**
- Note: `loc-tracker`
- Expiration: **No expiration**
- Scope: check the **`repo`** box (top-level)
- Click **Generate token** → copy it (starts with `ghp_`)

### Step 2 — Create your private `loc-data` repo

```bash
gh repo create YOUR_USERNAME/loc-data --private
```

### Step 3 — Copy the tracker files into it

```bash
gh repo clone YOUR_USERNAME/loc-data ~/YOUR_USERNAME-loc-data && cd ~/YOUR_USERNAME-loc-data
mkdir -p scripts .github/workflows
curl -sL -o scripts/track_prs.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_prs.py
curl -sL -o scripts/track_loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_loc.py
curl -sL -o .github/workflows/track-loc.yml https://raw.githubusercontent.com/westconn24/westconn24/main/.github/workflows/track-loc.yml
git add scripts/ .github/
git commit -m "Add LOC tracker"
git push
```

### Step 4 — Add your PAT as a secret in `loc-data`

Go to: `github.com/YOUR_USERNAME/loc-data/settings/secrets/actions`

Click **New repository secret**
- Name: `GH_PAT`
- Value: paste the `ghp_...` token

Click **Add secret**

### Step 5 — Run the workflow

```bash
gh workflow run track-loc.yml --repo YOUR_USERNAME/loc-data --field days_back=30
```

It backfills the last 30 days automatically. Takes ~2–3 minutes.

### Step 6 — Add token and CLIs to your shell

```bash
# Add token to shell (replace with your actual token)
echo 'export GH_LOC_TOKEN=ghp_your_token_here' >> ~/.zshrc && source ~/.zshrc

# Install both CLIs
curl -sL -o ~/loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/loc.py
curl -sL -o ~/loctest.py https://raw.githubusercontent.com/westconn24/westconn24/main/loctest.py
```

---

## Upgrade Setup (Already have `loc-data` repo with the old PR-only tracker)

If you already have a `loc-data` repo running the old PR-only tracker, run these commands to add the commit tracker alongside it:

```bash
cd ~/YOUR_USERNAME-loc-data

# Download the updated files
curl -sL -o scripts/track_prs.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_prs.py
curl -sL -o scripts/track_loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_loc.py
curl -sL -o .github/workflows/track-loc.yml https://raw.githubusercontent.com/westconn24/westconn24/main/.github/workflows/track-loc.yml

# Commit and push
git add scripts/ .github/
git commit -m "Add commit-based LOC tracking alongside PR tracking"
git push

# Backfill the commit log
gh workflow run track-loc.yml --repo YOUR_USERNAME/loc-data --field days_back=30

# Install the commit viewer CLI
curl -sL -o ~/loctest.py https://raw.githubusercontent.com/westconn24/westconn24/main/loctest.py
```

Your existing `loc.py` and `loc-log.json` keep working as before. The new commit tracker writes to a separate `loc-log-commits.json` file.

---

## Using the CLIs

### PR Tracker — `loc.py`

Tracks merged PRs. Good for seeing what shipped through code review.

```bash
# Your stats — last 7 days (default)
python3 ~/loc.py --user YOUR_USERNAME

# Last 30 days
python3 ~/loc.py --user YOUR_USERNAME --days 30

# Summary only, no daily breakdown
python3 ~/loc.py --user YOUR_USERNAME --week

# Show individual PRs per day
python3 ~/loc.py --user YOUR_USERNAME -v

# View someone else's stats
python3 ~/loc.py --user ArkashJ
python3 ~/loc.py --user aniture

# Adjust the refactor filter (default 15k, 0 = no filter)
python3 ~/loc.py --user YOUR_USERNAME --max-deletions 5000

# Exclude a specific repo
python3 ~/loc.py --user YOUR_USERNAME --exclude Benmore-Studio/162-AeroSleuth
```

### Commit Tracker — `loctest.py`

Tracks every individual commit across all branches. More accurate total output.

```bash
# Your stats — last 7 days (default, reads from GitHub)
python3 ~/loctest.py --user YOUR_USERNAME

# Last 30 days
python3 ~/loctest.py --user YOUR_USERNAME --days 30

# Summary only
python3 ~/loctest.py --user YOUR_USERNAME --week

# Show individual commits per day
python3 ~/loctest.py --user YOUR_USERNAME -v

# View someone else
python3 ~/loctest.py --user ArkashJ
python3 ~/loctest.py --user aniture

# Exclude a repo
python3 ~/loctest.py --user YOUR_USERNAME --exclude Benmore-Studio/162-AeroSleuth
```

### Example Output — PR Tracker

```
westconn24 — last 7 days

Date               Added     Deleted           Net  PRs
------------  ----------  ----------  ------------  ---
2026-04-06  +  10,942  -     136  net    +10,806  (2 PRs)
2026-04-07  +  14,265  -   3,574  net    +10,691  (2 PRs)
2026-04-08  +  12,296  -   2,265  net    +10,031  (18 PRs)
2026-04-09  +  24,593  -   1,839  net    +22,754  (4 PRs)

Total added          62,096
Total deleted         7,814
Net                 +54,282
Active days               4 of 7
Avg net/day         +13,571
```

### Example Output — Commit Tracker

```
westconn24 — last 7 days [remote]

Date               Added     Deleted           Net
------------  ----------  ----------  ------------  ------
2026-04-06  +   6,267  -     216  net     +6,051  (41 commits)
2026-04-07  +   7,847  -   2,738  net     +5,109  (20 commits)
2026-04-08  +  17,266  -   1,114  net    +16,152  (39 commits)
2026-04-09  +  16,875  -   2,511  net    +14,364  (58 commits)

Total added          48,255
Total deleted         6,579
Net                 +41,676
Total commits           158
Active days               4 of 7
Avg net/day         +10,419
```

---

## Viewing the Whole Team

```bash
# PR stats
python3 ~/loc.py --user westconn24
python3 ~/loc.py --user ArkashJ
python3 ~/loc.py --user aniture

# Commit stats
python3 ~/loctest.py --user westconn24
python3 ~/loctest.py --user ArkashJ
python3 ~/loctest.py --user aniture
```

Note: you can only view someone's stats if your `GH_LOC_TOKEN` has `repo` scope access to their `loc-data` repo. Shared Benmore org membership covers this automatically.

---

## What Each Tracker Captures

### PR Tracker (`loc.py`)
- Lines added/deleted in merged pull requests
- Can overcount when merge PRs flow code through branch hierarchies (feature→dev→main)
- Does NOT capture direct pushes or unmerged branch work

### Commit Tracker (`loctest.py`)
- Every individual commit across all repos and branches
- Skips merge commits (>1 parent) to prevent double-counting
- Captures direct pushes, branch work, and non-PR commits
- Uses the GitHub Events API to discover active repos, then scans all branches

### Neither Tracker Captures
- Time spent reviewing PRs
- Design, planning, or async communication work
- Non-GitHub contributions

Use as a productivity signal — good for spotting gaps, not for ranking people.

---

## Maintenance

- Runs automatically every morning at 6 AM UTC — no action needed
- Both trackers run in a single workflow, producing two separate log files
- PAT never expires if set to "No expiration"
- If someone's numbers go to zero, their `GH_PAT` secret likely expired — regenerate at `github.com/settings/tokens` and update the secret in their `loc-data` repo
- To manually backfill any range: `gh workflow run track-loc.yml --repo USERNAME/loc-data --field days_back=N`
