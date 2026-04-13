#!/usr/bin/env python3
"""
loctest - LOC viewer for commit-based tracking.
Reads from ~/loc-log-commits.json (built by track_loc_test.py).

Usage:
  python loctest.py              # last 7 days
  python loctest.py --days 30    # last 30 days
  python loctest.py --week       # summary only
  python loctest.py -v           # show individual commits
  python loctest.py --remote     # fetch from GitHub instead of local file
"""

import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_USER = "westconn24"
DEFAULT_LOCAL = os.path.expanduser("~/loc-log-commits.json")
REMOTE_URL = "https://api.github.com/repos/{user}/loc-data/contents/loc-log-commits.json"


def load_local(path):
    with open(path) as f:
        return json.load(f)


def load_remote(user, token=None):
    url = REMOTE_URL.format(user=user)
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            return json.loads(base64.b64decode(data["content"]))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit("No loc-log-commits.json found remotely. Use --local or run track_loc_test.py first.")
        if e.code == 401:
            raise SystemExit("Repo is private. Set GH_LOC_TOKEN or pass --token.")
        raise


def format_num(n):
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,}"


def filter_entry(entry, exclude_repos, max_deletions):
    key = "commits" if "commits" in entry else "prs"
    items = entry[key]
    if exclude_repos:
        items = [c for c in items if c["repo"] not in exclude_repos]
    if max_deletions is not None:
        items = [c for c in items if c["deletions"] <= max_deletions]
    return {
        "date": entry["date"],
        "additions": sum(c["additions"] for c in items),
        "deletions": sum(c["deletions"] for c in items),
        "net": sum(c["additions"] - c["deletions"] for c in items),
        key: items,
    }


def get_items(entry):
    return entry.get("commits", entry.get("prs", []))


def print_day(entry, verbose=False):
    items = get_items(entry)
    net = entry["net"]
    color = "\033[32m" if net >= 0 else "\033[31m"
    reset = "\033[0m"
    count = len(items)
    label = "commit" if "commits" in entry else "PR"
    plural = f"{label}s" if count != 1 else label
    print(
        f"  {entry['date']}  "
        f"+{entry['additions']:>8,}  -{entry['deletions']:>8,}  "
        f"net {color}{format_num(net):>10}{reset}  "
        f"({count} {plural})"
    )
    if verbose:
        for c in items:
            if "sha" in c:
                print(f"             {c['sha']}  {c['repo']}: +{c['additions']:,} -{c['deletions']:,}  {c['message'][:60]}")
            else:
                print(f"             #{c['pr']:>4} {c['repo']}: +{c['additions']:,} -{c['deletions']:,}  {c['title'][:60]}")


def print_summary(entries):
    total_add = sum(e["additions"] for e in entries)
    total_del = sum(e["deletions"] for e in entries)
    net = total_add - total_del
    active = [e for e in entries if get_items(e)]
    avg = net // len(active) if active else 0
    color = "\033[32m" if net >= 0 else "\033[31m"
    reset = "\033[0m"

    total_items = sum(len(get_items(e)) for e in entries)
    has_commits = any("commits" in e for e in entries)
    label = "commits" if has_commits else "PRs"

    print()
    print(f"  {'Total added':<16} {total_add:>10,}")
    print(f"  {'Total deleted':<16} {total_del:>10,}")
    print(f"  {'Net':<16} {color}{format_num(net):>10}{reset}")
    print(f"  {'Total ' + label:<16} {total_items:>10,}")
    print(f"  {'Active days':<16} {len(active):>10} of {len(entries)}")
    print(f"  {'Avg net/day':<16} {format_num(avg):>10}")
    print()


def main():
    parser = argparse.ArgumentParser(description="LOC viewer (commit-based)")
    parser.add_argument("--user", "-u", default=DEFAULT_USER)
    parser.add_argument("--token", "-t", default=os.environ.get("GH_LOC_TOKEN"))
    parser.add_argument("--days", type=int, default=7, help="Days back to show (default: 7)")
    parser.add_argument("--week", action="store_true", help="Summary only")
    parser.add_argument("--exclude", metavar="REPO", action="append", default=[])
    parser.add_argument("--max-deletions", type=int, default=15000, metavar="N",
                        help="Exclude items with more than N deletions (default: 15000, 0=include all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show individual commits")
    parser.add_argument("--remote", action="store_true", help="Fetch from GitHub instead of local file")
    parser.add_argument("--file", "-f", default=DEFAULT_LOCAL, help="Local log file path")
    args = parser.parse_args()

    if args.remote:
        print("Fetching from GitHub...", end="\r")
        log = load_remote(args.user, token=args.token)
    else:
        try:
            log = load_local(args.file)
        except FileNotFoundError:
            raise SystemExit(f"No local log at {args.file}. Run track_loc_test.py first, or use --remote.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
    max_del = None if args.max_deletions == 0 else args.max_deletions
    entries = [filter_entry(e, args.exclude, max_del) for e in log if e["date"] >= cutoff]

    if not entries:
        print("No data found for that range.")
        return

    source = "remote" if args.remote else "local"
    exclude_note = f"  (excluding: {', '.join(args.exclude)})" if args.exclude else ""
    print(f"\n  {args.user} — last {args.days} days [{source}]{exclude_note}\n")
    print(f"  {'Date':<12}  {'Added':>10}  {'Deleted':>10}  {'Net':>12}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*12}  ------")

    if not args.week:
        for entry in entries:
            print_day(entry, verbose=args.verbose)

    print_summary(entries)


if __name__ == "__main__":
    main()
