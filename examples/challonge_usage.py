#!/usr/bin/env python3
"""
Example: How to use the Challonge scraper

This example demonstrates the usage of the Challonge scraper to import
tournament data into the BeybladeX Elo system.

Note: This example requires internet access to challonge.com
"""

import subprocess
import sys

def example_basic_scraping():
    """Example: Basic tournament scraping"""
    print("=" * 60)
    print("Example 1: Basic Tournament Scraping")
    print("=" * 60)
    print()
    print("Command:")
    print("  python scripts/challonge_scraper.py https://challonge.com/om3hx2e9")
    print()
    print("This will:")
    print("  1. Fetch tournament data from the URL")
    print("  2. Extract all completed matches")
    print("  3. Append matches to csv/matches.csv")
    print("  4. Use the detected tournament date")
    print()


def example_dry_run():
    """Example: Dry-run mode to preview matches"""
    print("=" * 60)
    print("Example 2: Preview Matches (Dry-Run)")
    print("=" * 60)
    print()
    print("Command:")
    print("  python scripts/challonge_scraper.py om3hx2e9 --dry-run")
    print()
    print("This will:")
    print("  1. Fetch tournament data")
    print("  2. Display all matches that would be imported")
    print("  3. NOT write anything to matches.csv")
    print("  4. Useful for verifying data before importing")
    print()


def example_custom_date():
    """Example: Specify custom tournament date"""
    print("=" * 60)
    print("Example 3: Custom Tournament Date")
    print("=" * 60)
    print()
    print("Command:")
    print("  python scripts/challonge_scraper.py zjbg6ab3 --date 2025-09-15")
    print()
    print("This will:")
    print("  1. Fetch tournament data")
    print("  2. Use 2025-09-15 as the date for all matches")
    print("  3. Append matches to csv/matches.csv")
    print()


def example_full_workflow():
    """Example: Complete workflow from scraping to Elo update"""
    print("=" * 60)
    print("Example 4: Complete Workflow")
    print("=" * 60)
    print()
    print("Step 1: Preview the tournament data")
    print("  python scripts/challonge_scraper.py om3hx2e9 --dry-run")
    print()
    print("Step 2: Import the tournament data")
    print("  python scripts/challonge_scraper.py om3hx2e9")
    print()
    print("Step 3: Review the imported matches")
    print("  tail -n 20 csv/matches.csv")
    print()
    print("Step 4: Update Elo ratings")
    print("  python update.py")
    print()
    print("Step 5: View updated leaderboard")
    print("  head -n 20 csv/leaderboard.csv")
    print()


def example_multiple_tournaments():
    """Example: Import multiple tournaments"""
    print("=" * 60)
    print("Example 5: Import Multiple Tournaments")
    print("=" * 60)
    print()
    print("Import first tournament:")
    print("  python scripts/challonge_scraper.py om3hx2e9 --date 2025-09-07")
    print()
    print("Import second tournament:")
    print("  python scripts/challonge_scraper.py zjbg6ab3 --date 2025-09-14")
    print()
    print("Update all Elo ratings:")
    print("  python update.py")
    print()


def main():
    """Run all examples"""
    print()
    print("#" * 60)
    print("# Challonge Scraper Usage Examples")
    print("#" * 60)
    print()
    
    example_basic_scraping()
    example_dry_run()
    example_custom_date()
    example_full_workflow()
    example_multiple_tournaments()
    
    print("=" * 60)
    print("For more information, see:")
    print("  - CHALLONGE_SCRAPER.md for detailed documentation")
    print("  - python scripts/challonge_scraper.py --help for all options")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
