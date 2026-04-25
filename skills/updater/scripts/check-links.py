#!/usr/bin/env python3
"""
check-links.py — Validate URLs in agent-toolkit reference files.

Extracts all URLs from .md files in the repo, checks each with a HEAD request,
and reports broken, redirected, or valid links.

Usage:
    python3 check-links.py                    # Check all reference files
    python3 check-links.py skills/requirements # Check specific directory

Output: prints a table of results and exits with code 1 if any links are broken.

Dependencies: stdlib only (no pip install needed).
"""

import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


def find_md_files(root_dir):
    """Find all .md files in directory, excluding .git and node_modules."""
    md_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'node_modules', '__pycache__', 'venv')]
        for f in filenames:
            if f.endswith('.md'):
                md_files.append(os.path.join(dirpath, f))
    return sorted(md_files)


def extract_urls(filepath):
    """Extract all URLs from a markdown file."""
    url_pattern = re.compile(r'https?://[^\s\)>\]"\']+')
    urls = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            for match in url_pattern.finditer(line):
                url = match.group().rstrip('.,;:)')
                urls.append((url, filepath, line_num))
    return urls


def check_url(url, timeout=10):
    """Check if URL is reachable. Returns (status, detail)."""
    try:
        req = urllib.request.Request(url, method='HEAD', headers={
            'User-Agent': 'agent-toolkit-link-checker/1.0'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return 'valid', str(resp.status)
            return 'redirected', str(resp.status)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return 'redirected', str(e.code)
        if e.code == 403:
            return 'blocked', '403 (may require browser)'
        if e.code == 404:
            return 'broken', '404 Not Found'
        return 'error', str(e.code)
    except urllib.error.URLError as e:
        return 'broken', str(e.reason)
    except Exception as e:
        return 'error', str(e)


def find_freshness_dates(filepath):
    """Find 'Last verified:' dates in a file."""
    dates = []
    date_pattern = re.compile(r'Last verified:\s*(\d{4}-\d{2}-\d{2})')
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            match = date_pattern.search(line)
            if match:
                date_str = match.group(1)
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    age_days = (datetime.now() - date).days
                    dates.append((date_str, age_days, filepath, line_num))
                except ValueError:
                    pass
    return dates


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    search_dir = repo_root

    if len(sys.argv) > 1:
        search_dir = repo_root / sys.argv[1]
        if not search_dir.exists():
            print(f"Directory not found: {search_dir}")
            sys.exit(1)

    print(f"Checking links in: {search_dir}")
    print(f"Repo root: {repo_root}")
    print()

    md_files = find_md_files(str(search_dir))
    print(f"Found {len(md_files)} markdown files")
    print()

    # Extract all URLs
    all_urls = []
    for f in md_files:
        all_urls.extend(extract_urls(f))

    # Deduplicate URLs (keep first occurrence for reporting)
    seen = {}
    unique_urls = []
    for url, filepath, line_num in all_urls:
        if url not in seen:
            seen[url] = (filepath, line_num)
            unique_urls.append((url, filepath, line_num))

    print(f"Found {len(all_urls)} URLs ({len(unique_urls)} unique)")
    print()

    # Check each URL
    broken = []
    redirected = []
    valid = []
    errors = []

    for i, (url, filepath, line_num) in enumerate(unique_urls):
        rel_path = os.path.relpath(filepath, repo_root)
        status, detail = check_url(url)

        symbol = {'valid': '✅', 'redirected': '🟡', 'broken': '❌', 'blocked': '⚠️', 'error': '⚠️'}
        print(f"  [{i+1}/{len(unique_urls)}] {symbol.get(status, '?')} {status}: {url}")

        entry = (url, rel_path, line_num, detail)
        if status == 'valid':
            valid.append(entry)
        elif status == 'broken':
            broken.append(entry)
        elif status == 'redirected':
            redirected.append(entry)
        else:
            errors.append(entry)

    # Check freshness dates
    print()
    print("Checking freshness dates...")
    all_dates = []
    for f in md_files:
        all_dates.extend(find_freshness_dates(f))

    stale = [(d, age, f, l) for d, age, f, l in all_dates if age > 180]
    fresh = [(d, age, f, l) for d, age, f, l in all_dates if age <= 180]

    # Report
    print()
    print("=" * 60)
    print("LINK CHECK RESULTS")
    print("=" * 60)
    print(f"  ✅ Valid:      {len(valid)}")
    print(f"  🟡 Redirected: {len(redirected)}")
    print(f"  ❌ Broken:     {len(broken)}")
    print(f"  ⚠️  Errors:     {len(errors)}")
    print()

    if broken:
        print("BROKEN LINKS:")
        for url, filepath, line_num, detail in broken:
            print(f"  ❌ {filepath}:{line_num}")
            print(f"     {url}")
            print(f"     Reason: {detail}")
            print()

    if redirected:
        print("REDIRECTED LINKS:")
        for url, filepath, line_num, detail in redirected:
            print(f"  🟡 {filepath}:{line_num}")
            print(f"     {url}")
            print(f"     Status: {detail}")
            print()

    print("=" * 60)
    print("FRESHNESS CHECK")
    print("=" * 60)
    print(f"  ✅ Fresh (< 6 months): {len(fresh)}")
    print(f"  🟡 Stale (> 6 months): {len(stale)}")
    print()

    if stale:
        print("STALE REFERENCES:")
        for date_str, age_days, filepath, line_num in stale:
            rel_path = os.path.relpath(filepath, repo_root)
            print(f"  🟡 {rel_path}:{line_num}")
            print(f"     Last verified: {date_str} ({age_days} days ago)")
            print()

    # Exit code
    if broken:
        print(f"FAIL: {len(broken)} broken link(s) found.")
        sys.exit(1)
    else:
        print("PASS: No broken links.")
        sys.exit(0)


if __name__ == '__main__':
    main()
