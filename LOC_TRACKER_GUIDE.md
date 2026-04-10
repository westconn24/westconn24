# Benmore LOC Tracker — Team Guide

## What Is This?

A system that automatically tracks each developer's lines of code output per day by scanning merged GitHub pull requests. Numbers update every morning. No manual effort after setup.

**What it tracks:**
- Lines added and deleted per day, per PR
- Code only — `.md`, `.rst`, `.txt`, `.csv` files excluded
- Refactor-heavy PRs automatically filtered (>15k deletions ignored by default)

**Privacy:** Data lives in each developer's private `{username}/loc-data` repo. Only accessible to people with a GitHub PAT that has `repo` scope.

---

## How It Works

1. A GitHub Action runs in each developer's private `{username}/loc-data` repo every morning at 6 AM UTC
2. It scans all their merged PRs from the previous day across every repo they have access to
3. Fetches file-level stats to strip out doc/data files
4. Saves results to `loc-log.json` in the private `loc-data` repo
5. The CLI (`loc.py`) reads that file using a PAT — only authorized people can view it

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
curl -o scripts/track_loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_loc.py
curl -o .github/workflows/track-loc.yml https://raw.githubusercontent.com/westconn24/westconn24/main/.github/workflows/track-loc.yml
git add scripts/track_loc.py .github/workflows/track-loc.yml
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

It backfills the last 30 days automatically. Takes ~1–2 minutes.

### Step 6 — Add token and CLI to your shell

```bash
# Add token to shell (replace with your actual token)
echo 'export GH_LOC_TOKEN=ghp_your_token_here' >> ~/.zshrc && source ~/.zshrc

# Install the CLI
curl -o ~/loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/loc.py
```

---

## Migration Setup (Already had old tracker in profile repo)

If you previously set up the tracker in your `{username}/{username}` profile repo, run these commands to migrate to the new private `loc-data` setup:

```bash
# 1. Create the private loc-data repo
gh repo create YOUR_USERNAME/loc-data --private

# 2. Clone it and copy the updated tracker files
gh repo clone YOUR_USERNAME/loc-data ~/YOUR_USERNAME-loc-data && cd ~/YOUR_USERNAME-loc-data
mkdir -p scripts .github/workflows
curl -o scripts/track_loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/scripts/track_loc.py
curl -o .github/workflows/track-loc.yml https://raw.githubusercontent.com/westconn24/westconn24/main/.github/workflows/track-loc.yml
git add scripts/track_loc.py .github/workflows/track-loc.yml
git commit -m "Add LOC tracker"
git push

# 3. Add GH_PAT secret to loc-data
# Go to: github.com/YOUR_USERNAME/loc-data/settings/secrets/actions → New secret → Name: GH_PAT

# 4. Run the 30-day backfill
gh workflow run track-loc.yml --repo YOUR_USERNAME/loc-data --field days_back=30

# 5. Add token to shell and update CLI
echo 'export GH_LOC_TOKEN=ghp_your_token_here' >> ~/.zshrc && source ~/.zshrc
curl -o ~/loc.py https://raw.githubusercontent.com/westconn24/westconn24/main/loc.py

# 6. Remove old workflow from profile repo (cleanup)
cd ~/ && gh repo clone YOUR_USERNAME/YOUR_USERNAME ~/YOUR_USERNAME-profile
cd ~/YOUR_USERNAME-profile && rm -rf scripts .github
git add -A && git commit -m "Remove old LOC tracker" && git push
```

---

## Using the CLI

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

# Pass token explicitly instead of env var
python3 ~/loc.py --user YOUR_USERNAME --token ghp_...
```

### Example Output

```
westconn24 — last 7 days

Date               Added     Deleted           Net  PRs
------------  ----------  ----------  ------------  ---
2026-04-06  +  10,942  -     136  net    +10,806  (2 PRs)
2026-04-07  +  14,265  -   3,574  net    +10,691  (2 PRs)
2026-04-08  +  12,296  -   2,265  net    +10,031  (18 PRs)
2026-04-09  +  24,785  -   1,839  net    +22,946  (4 PRs)

Total added          62,288
Total deleted         7,814
Net                 +54,474
Active days               4 of 7
Avg net/day         +13,619
```

---

## Viewing the Whole Team

```bash
python3 ~/loc.py --user westconn24
python3 ~/loc.py --user ArkashJ
python3 ~/loc.py --user aniture
```

Note: you can only view someone's stats if your `GH_LOC_TOKEN` has `repo` scope access to their `loc-data` repo. Since all repos are under shared Benmore org membership this should work automatically.

---

## What It Doesn't Track

- Direct pushes to main (no PR = no data)
- Time spent reviewing PRs
- Design, planning, or async communication work

Use as a productivity signal — good for spotting gaps, not for ranking people.

---

## Maintenance

- Runs automatically every morning at 6 AM UTC — no action needed
- PAT never expires if set to "No expiration"
- If someone's numbers go to zero, their `GH_PAT` secret likely expired — regenerate at `github.com/settings/tokens` and update the secret in their `loc-data` repo
- To manually backfill any range: `gh workflow run track-loc.yml --repo USERNAME/loc-data --field days_back=N`
