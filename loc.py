#!/usr/bin/env python3
"""
loc - westconn24 lines of code tracker
Fetches live data from GitHub. No setup needed.

Usage:
  python loc.py              # last 7 days
  python loc.py --days 30    # last 30 days
  python loc.py --week       # this week summary only
  python loc.py --exclude Benmore-Studio/162-AeroSleuth  # skip a repo
"""

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_USER = "westconn24"
RAW_URL = "https://raw.githubusercontent.com/{user}/{user}/main/loc-log.json"


def fetch_log(user):
    url = RAW_URL.format(user=user)
    try:
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(f"No loc-log.json found for '{user}'. They need to set up the tracker first.")
        raise


def format_num(n):
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,}"


def filter_prs(entry, exclude_repos, max_deletions):
    prs = entry["prs"]
    if exclude_repos:
        prs = [p for p in prs if p["repo"] not in exclude_repos]
    if max_deletions is not None:
        prs = [p for p in prs if p["deletions"] <= max_deletions]
    return {
        **entry,
        "additions": sum(p["additions"] for p in prs),
        "deletions": sum(p["deletions"] for p in prs),
        "net": sum(p["additions"] - p["deletions"] for p in prs),
        "prs": prs,
    }


def print_day(entry, verbose=False):
    net = entry["net"]
    color = "\033[32m" if net >= 0 else "\033[31m"
    reset = "\033[0m"
    pr_count = len(entry["prs"])
    print(
        f"  {entry['date']}  "
        f"+{entry['additions']:>8,}  -{entry['deletions']:>8,}  "
        f"net {color}{format_num(net):>10}{reset}  "
        f"({pr_count} PR{'s' if pr_count != 1 else ''})"
    )
    if verbose:
        for pr in entry["prs"]:
            print(f"             #{pr['pr']:>4} {pr['repo']}: +{pr['additions']:,} -{pr['deletions']:,}  {pr['title'][:60]}")


def print_summary(entries):
    total_add = sum(e["additions"] for e in entries)
    total_del = sum(e["deletions"] for e in entries)
    net = total_add - total_del
    active = [e for e in entries if e["prs"]]
    avg = net // len(active) if active else 0
    color = "\033[32m" if net >= 0 else "\033[31m"
    reset = "\033[0m"

    print()
    print(f"  {'Total added':<16} {total_add:>10,}")
    print(f"  {'Total deleted':<16} {total_del:>10,}")
    print(f"  {'Net':<16} {color}{format_num(net):>10}{reset}")
    print(f"  {'Active days':<16} {len(active):>10} of {len(entries)}")
    print(f"  {'Avg net/day':<16} {format_num(avg):>10}")
    print()


def main():
    parser = argparse.ArgumentParser(description="GitHub LOC tracker")
    parser.add_argument("--user", "-u", default=DEFAULT_USER, help=f"GitHub username to pull stats for (default: {DEFAULT_USER})")
    parser.add_argument("--days", type=int, default=7, help="How many days back to show (default: 7)")
    parser.add_argument("--week", action="store_true", help="Show summary only, no daily breakdown")
    parser.add_argument("--exclude", metavar="REPO", action="append", default=[], help="Exclude a repo (e.g. Benmore-Studio/162-AeroSleuth). Repeatable.")
    parser.add_argument("--max-deletions", type=int, default=10000, metavar="N", help="Exclude PRs that delete more than N lines (default: 10000, use 0 to include all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show individual PRs per day")
    args = parser.parse_args()

    print("Fetching data...", end="\r")
    log = fetch_log(args.user)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
    max_del = None if args.max_deletions == 0 else args.max_deletions
    entries = [filter_prs(e, args.exclude, max_del) for e in log if e["date"] >= cutoff]

    if not entries:
        print("No data found for that range.")
        return

    exclude_note = f"  (excluding: {', '.join(args.exclude)})" if args.exclude else ""
    print(f"\n  {args.user} — last {args.days} days{exclude_note}\n")
    print(f"  {'Date':<12}  {'Added':>10}  {'Deleted':>10}  {'Net':>12}  PRs")
    print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*12}  ---")

    if not args.week:
        for entry in entries:
            print_day(entry, verbose=args.verbose)

    print_summary(entries)


if __name__ == "__main__":
    main()
