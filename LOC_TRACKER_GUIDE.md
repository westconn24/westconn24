# Benmore LOC Tracker — Team Guide

## What Is This?

A lightweight system that automatically tracks every developer's lines of code output per day by scanning merged GitHub pull requests. Numbers update every morning. No manual effort after setup.

Tracks:
- Lines added and deleted per day
- Which PRs and repos the work came from
- Code only — markdown/docs files excluded
- Refactor-heavy PRs automatically filtered out (>15k deletions)

---

## How It Works

1. A GitHub Action runs on each developer's profile repo every morning at 6 AM UTC
2. It scans all PRs they merged the previous day across every repo they have access to
3. Fetches file-level stats to exclude `.md`, `.rst`, and `.txt` files
4. Saves results to `loc-log.json` in their profile repo
5. The CLI (`loc.py`) reads that public JSON file — no auth needed to view

---

## Setup (Per Developer — ~5 min)

### Step 1 — Create a PAT

Go to: `github.com/settings/tokens` → **Generate new token (classic)**
- Note: `loc-tracker`
- Expiration: **No expiration**
- Scope: check the **`repo`** box (top-level)
- Click **Generate token** → copy it (starts with `ghp_`)

### Step 2 — Add it as a secret

Go to: `github.com/YOUR_USERNAME/YOUR_USERNAME/settings/secrets/actions`

Click **New repository secret**
- Name: `GH_PAT`
- Value: paste the `ghp_...` token

Click **Add secret**

### Step 3 — Copy the tracker files

Run these commands in your terminal (replace `YOUR_USERNAME` with your GitHub username):

```bash
gh repo clone YOUR_USERNAME/YOUR_USERNAME ~/YOUR_USERNAME && cd ~/YOUR_USERNAME
mkdir -p scripts .github/workflows
curl -o scripts/track_loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_loc.py
curl -o .github/workflows/track-loc.yml https://raw.githubusercontent.com/westconn24/westconn24/main/.github/workflows/track-loc.yml
git add scripts/track_loc.py .github/workflows/track-loc.yml
git commit -m "Add LOC tracker"
git push
```

> **Note:** If you don't have a profile repo yet, create one at `github.com/new` with a repo name that exactly matches your GitHub username.

### Step 4 — Run it for the first time

Go to: `github.com/YOUR_USERNAME/YOUR_USERNAME/actions`

Click **Track Daily LOC from PRs** → **Run workflow** → **Run workflow**

It will automatically backfill the last 30 days on first run. Takes ~1–2 minutes.

---

## Using the CLI

### Install

```bash
curl -o ~/loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/loc.py
```

### Commands

```bash
# View your own stats (default: last 7 days)
python3 ~/loc.py --user YOUR_USERNAME

# Last 30 days
python3 ~/loc.py --user YOUR_USERNAME --days 30

# Just the summary, no daily breakdown
python3 ~/loc.py --user YOUR_USERNAME --week

# See individual PRs per day
python3 ~/loc.py --user YOUR_USERNAME -v

# View someone else's stats
python3 ~/loc.py --user ArkashJ
python3 ~/loc.py --user westconn24

# Adjust the refactor filter (default 15k, use 0 for no filter)
python3 ~/loc.py --user YOUR_USERNAME --max-deletions 5000

# Exclude a specific repo
python3 ~/loc.py --user YOUR_USERNAME --exclude Benmore-Studio/162-AeroSleuth
```

### Example Output

```
westconn24 — last 7 days

Date               Added     Deleted           Net  PRs
------------  ----------  ----------  ------------  ---
2026-04-03  +  14,003  -   7,970  net     +6,033  (1 PR)
2026-04-06  +  10,942  -     136  net    +10,806  (2 PRs)
2026-04-07  +  14,265  -   3,574  net    +10,691  (2 PRs)
2026-04-08  +  12,296  -   2,265  net    +10,031  (18 PRs)
2026-04-09  +  24,785  -   1,839  net    +22,946  (4 PRs)

Total added          79,404
Total deleted        16,794
Net                 +62,610
Active days               6 of 7
Avg net/day         +10,435
```

---

## Team Roster

Once everyone is set up, check the whole team at once:

```bash
python3 ~/loc.py --user westconn24
python3 ~/loc.py --user ArkashJ
# add more as people join
```

---

## What It Doesn't Track

- Direct pushes to main (no PR = no data)
- Time spent reviewing other people's PRs
- Design, planning, or async communication work

Use this as a productivity signal — good for spotting gaps, not for ranking people.

---

## Maintenance

- Runs automatically every morning, no action needed
- The `GH_PAT` token never expires if set to "No expiration"
- If someone's numbers go to zero, their PAT likely expired — regenerate and update the secret
- To backfill any date range, go to Actions → Run workflow → set `days_back`
