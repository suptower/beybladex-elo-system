#!/usr/bin/env python3
"""
Generate changelog from Git commit history and write to JSON file.

This script extracts commit history from the Git repository and generates
a structured changelog that can be displayed on the website.

Features:
- Extracts commit hash, date, message, and author
- Categorizes commits by conventional commit prefixes (feat:, fix:, etc.)
- Supports filtering and limiting number of commits
- Outputs to docs/data/changelog.json

Usage:
    python src/generate_changelog.py [--limit N]

Output:
    Creates/updates docs/data/changelog.json with commit history
"""

import subprocess
import json
import os
import re
from datetime import datetime, timezone
import argparse

# Default repository URL for fallback
DEFAULT_REPO_URL = "https://github.com/suptower/beybladex-elo-system"


def categorize_commit(message):
    """
    Categorize a commit message based on conventional commit prefixes.

    Args:
        message (str): Commit message

    Returns:
        str: Category name (Feature, Fix, Balance, UI, Documentation, etc.)
    """
    # Define category mappings
    categories = {
        'feat': 'Feature',
        'fix': 'Fix',
        'balance': 'Balance',
        'ui': 'UI',
        'docs': 'Documentation',
        'style': 'Style',
        'refactor': 'Refactor',
        'perf': 'Performance',
        'test': 'Test',
        'build': 'Build',
        'ci': 'CI',
        'chore': 'Chore',
        'data': 'Data',
    }

    # Extract prefix from commit message
    match = re.match(r'^(\w+)(?:\([\w\-]+\))?:\s*', message.lower())
    if match:
        prefix = match.group(1)
        return categories.get(prefix, 'Other')

    return 'Other'


def get_commit_history(limit=50):
    """
    Extract commit history from Git repository.

    Args:
        limit (int): Maximum number of commits to retrieve

    Returns:
        list: List of commit dictionaries containing:
            - hash: Short commit hash (7 chars)
            - full_hash: Full commit hash
            - date: ISO formatted commit date
            - message: Commit message
            - author: Commit author name
            - category: Commit category
            - github_url: URL to commit on GitHub
    """
    # Validate limit parameter
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("Limit must be a positive integer")

    try:
        # Get commit history with custom format using %x00 as delimiter
        # Format: hash|full_hash|date|author|message
        # Using null byte separator to avoid issues with | in commit messages
        output = subprocess.check_output(
            [
                "git", "log",
                f"-{str(limit)}",
                "--pretty=format:%h%x00%H%x00%aI%x00%an%x00%s",
            ],
            text=True,
            timeout=30,
            encoding='utf-8'
        ).strip()

        commits = []
        for line in output.split('\n'):
            if not line:
                continue

            parts = line.split('\x00')
            if len(parts) != 5:
                continue

            short_hash, full_hash, date, author, message = parts

            # Determine category
            category = categorize_commit(message)

            # Build GitHub URL
            # Extract repo URL from git remote
            try:
                repo_url = subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"],
                    text=True,
                    timeout=5,
                    encoding='utf-8'
                ).strip()

                # Convert SSH URL to HTTPS if needed
                if repo_url.startswith('git@github.com:'):
                    repo_url = repo_url.replace('git@github.com:', 'https://github.com/')
                if repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]

                github_url = f"{repo_url}/commit/{full_hash}"
            except Exception:
                github_url = f"{DEFAULT_REPO_URL}/commit/{full_hash}"

            commits.append({
                'hash': short_hash,
                'full_hash': full_hash,
                'date': date,
                'message': message,
                'author': author,
                'category': category,
                'github_url': github_url
            })

        return commits

    except subprocess.CalledProcessError as e:
        print(f"Error getting commit history: {e}")
        return []


def write_changelog_json(commits, output_path):
    """
    Write changelog data to a JSON file.

    Args:
        commits (list): List of commit dictionaries
        output_path (str): Path to write the JSON file
    """
    changelog_data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'commit_count': len(commits),
        'commits': commits
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(changelog_data, f, indent=2, ensure_ascii=False)

    print(f"  Changelog written to {output_path}")
    print(f"  Total commits: {len(commits)}")

    # Print category summary
    categories = {}
    for commit in commits:
        cat = commit['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("  Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {cat}: {count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate changelog from Git commit history'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Maximum number of commits to include (default: 50)'
    )
    args = parser.parse_args()

    # Determine output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))
    output_path = os.path.join(repo_root, "docs", "data", "changelog.json")

    print(f"Generating changelog with up to {args.limit} commits...")
    commits = get_commit_history(limit=args.limit)

    if not commits:
        print("No commits found!")
        return

    write_changelog_json(commits, output_path)
    print("Changelog generation complete")


if __name__ == "__main__":
    main()
