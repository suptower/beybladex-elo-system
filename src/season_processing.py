"""
Season Processing Module

This module processes season data and generates season-specific outputs including:
- Season league tables for all tiers
- Promotion/relegation summaries
- Season archives with complete historical data
- Season Cup brackets and results
- Integration with existing ELO and statistics

This module is designed to be called from update.py pipeline.

Usage:
    python season_processing.py
    python season_processing.py --season S1
    python season_processing.py --all
"""

import csv
import json
import os
import argparse
import sys
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from season_cup import (  # noqa: E402
    load_season_cup_data,
    export_bracket_for_display
)
from season_manager import (  # noqa: E402
    get_league_table,
    get_promotion_relegation,
    generate_season_archive,
    load_season_data
)


# Default paths
DEFAULT_DATA_DIR = "./docs/data"
DEFAULT_MATCHES_FILE = os.path.join(DEFAULT_DATA_DIR, "matches.csv")
DEFAULT_FIXTURES_FILE = os.path.join(DEFAULT_DATA_DIR, "fixtures.csv")
DEFAULT_LEADERBOARD_FILE = os.path.join(DEFAULT_DATA_DIR, "leaderboard.csv")
DEFAULT_OUTPUT_FILE = os.path.join(DEFAULT_DATA_DIR, "season_data.json")

# Colors for output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def load_matches_with_elo(matches_file: str = DEFAULT_MATCHES_FILE,
                          leaderboard_file: str = DEFAULT_LEADERBOARD_FILE) -> List[Dict]:
    """
    Load matches from CSV and enrich with current ELO data.

    Args:
        matches_file: Path to matches.csv
        leaderboard_file: Path to leaderboard.csv with current ELO

    Returns:
        List of match dictionaries with ELO data
    """
    # Load current ELO ratings
    elo_ratings = {}
    if os.path.exists(leaderboard_file):
        with open(leaderboard_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bey = row.get("Bey")
                elo = float(row.get("Elo", 1000))
                elo_ratings[bey] = elo

    # Load matches
    matches = []
    with open(matches_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            match = {
                "match_id": row.get("MatchID", ""),
                "date": row.get("Date", ""),
                "bey_a": row.get("BeyA", ""),
                "bey_b": row.get("BeyB", ""),
                "score_a": int(row.get("ScoreA", 0)),
                "score_b": int(row.get("ScoreB", 0)),
                "match_type": row.get("MatchType", "exhibition"),
                "season_id": row.get("SeasonID", ""),
                "tier": int(row.get("Tier", 0)) if row.get("Tier") else None,
                "matchday": int(row.get("Matchday", 0)) if row.get("Matchday") else None,
                "elo_a": elo_ratings.get(row.get("BeyA", ""), 1000),
                "elo_b": elo_ratings.get(row.get("BeyB", ""), 1000)
            }
            matches.append(match)

    return matches


def load_fixtures(fixtures_file: str = DEFAULT_FIXTURES_FILE) -> List[Dict]:
    """
    Load upcoming fixtures from fixtures.csv.

    Args:
        fixtures_file: Path to fixtures CSV file

    Returns:
        List of fixture dictionaries
    """
    if not os.path.exists(fixtures_file):
        return []

    fixtures = []
    with open(fixtures_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fixture = {
                "fixture_id": row.get("FixtureID", ""),
                "date": row.get("Date", ""),
                "bey_a": row.get("BeyA", ""),
                "bey_b": row.get("BeyB", ""),
                "match_type": row.get("MatchType", "season").lower(),
                "season_id": row.get("SeasonID", ""),
                "tier": int(row["Tier"]) if row.get("Tier") else None,
                "matchday": int(row["Matchday"]) if row.get("Matchday") else None,
                "status": "scheduled"  # Mark as scheduled
            }
            fixtures.append(fixture)

    return fixtures


def get_active_seasons(matches: List[Dict]) -> List[str]:
    """
    Get list of all season IDs from matches.

    Args:
        matches: List of match dictionaries

    Returns:
        List of unique season IDs
    """
    season_ids = set()
    for match in matches:
        season_id = match.get("season_id")
        if season_id and match.get("match_type") in ["season", "relegation", "season_cup"]:
            season_ids.add(season_id)

    return sorted(list(season_ids))


def get_initial_tier_assignments(season_id: str, data_dir: str) -> Dict:
    """
    Load initial tier assignments from seasons.json.

    Args:
        season_id: Season identifier
        data_dir: Data directory

    Returns:
        Dictionary mapping tier number to list of bey dictionaries
    """
    seasons_file = os.path.join(data_dir, "seasons.json")
    if not os.path.exists(seasons_file):
        return {}

    with open(seasons_file, "r", encoding="utf-8") as f:
        seasons_data = json.load(f)

    season_data = seasons_data.get(season_id)
    if not season_data:
        return {}

    tier_assignments = season_data.get("tier_assignments", {})
    if not tier_assignments:
        return {}

    # Organize by tier
    tiers = {1: [], 2: [], 3: [], 4: []}
    for bey, data in tier_assignments.items():
        tier = data.get("tier")
        if tier in tiers:
            tiers[tier].append({
                "bey": bey,
                "elo": data.get("start_elo", 1000)
            })

    # Sort each tier by ELO descending
    for tier in tiers:
        tiers[tier].sort(key=lambda x: -x["elo"])

    return tiers


def create_initial_league_table(tier_beys: List[Dict]) -> List[Dict]:
    """
    Create an initial league table with all zeros for stats.

    Args:
        tier_beys: List of bey dictionaries with bey name and elo

    Returns:
        Initial league table with all stats at zero
    """
    table = []
    for i, bey_data in enumerate(tier_beys, 1):
        table.append({
            "position": i,
            "bey": bey_data["bey"],
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "season_points": 0,
            "points_for": 0,
            "points_against": 0,
            "point_diff": 0,
            "elo": bey_data["elo"]
        })
    return table


def organize_fixtures_by_matchday(fixtures: List[Dict]) -> Dict:
    """
    Organize fixtures by matchday.

    Args:
        fixtures: List of fixture dictionaries

    Returns:
        Dictionary mapping matchday to list of fixtures
    """
    by_matchday = {}
    for fixture in fixtures:
        matchday = fixture.get("matchday")
        if matchday:
            if matchday not in by_matchday:
                by_matchday[matchday] = []
            by_matchday[matchday].append(fixture)

    return by_matchday


def organize_fixtures_by_tier(fixtures: List[Dict]) -> Dict:
    """
    Organize fixtures by tier.

    Args:
        fixtures: List of fixture dictionaries

    Returns:
        Dictionary mapping tier to list of fixtures
    """
    by_tier = {}
    for fixture in fixtures:
        tier = fixture.get("tier")
        if tier:
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(fixture)

    return by_tier


def process_season(season_id: str, matches: List[Dict], fixtures: List[Dict],
                   data_dir: str = DEFAULT_DATA_DIR) -> Dict:
    """
    Process all data for a specific season including fixtures.

    Args:
        season_id: Season identifier
        matches: List of all completed matches
        fixtures: List of all scheduled fixtures
        data_dir: Data directory

    Returns:
        Complete season data dictionary
    """
    print(f"{CYAN}Processing Season {season_id}...{RESET}")

    # Filter matches for this season
    season_matches = [
        m for m in matches
        if m.get("season_id") == season_id and m.get("match_type") == "season"
    ]

    # Filter fixtures for this season
    season_fixtures = [
        f for f in fixtures
        if f.get("season_id") == season_id and f.get("match_type") == "season"
    ]

    # Get initial tier assignments
    initial_tiers = get_initial_tier_assignments(season_id, data_dir)

    if not season_matches and not initial_tiers and not season_fixtures:
        print(f"{YELLOW}  No season data found for {season_id}{RESET}")
        return None

    # Generate league tables for all tiers
    league_tables = {}
    for tier in range(1, 5):
        if season_matches:
            # Use actual match data
            table = get_league_table(matches, tier, season_id)
        elif tier in initial_tiers and initial_tiers[tier]:
            # Use initial assignments with zero stats
            table = create_initial_league_table(initial_tiers[tier])
        else:
            table = None

        if table:
            league_tables[tier] = table
            print(f"{GREEN}  Tier {tier}: {len(table)} teams{RESET}")

    if not league_tables:
        print(f"{YELLOW}  No league tables generated for {season_id}{RESET}")
        return None

    # Determine promotion/relegation (only if matches played)
    promotion_relegation = None
    if season_matches:
        promotion_relegation = get_promotion_relegation(
            load_season_data(season_id, data_dir) or {},
            league_tables
        )
        print(f"  Promotions: {len(promotion_relegation['automatic_promotion'])}")
        print(f"  Relegations: {len(promotion_relegation['automatic_relegation'])}")
        print(f"  Relegation matches: {len(promotion_relegation['relegation_matches'])}")

    # Check for Season Cup data
    cup_bracket = load_season_cup_data(season_id, data_dir)
    cup_display = None
    if cup_bracket:
        cup_display = export_bracket_for_display(cup_bracket)
        print("  Season Cup: Found bracket data")

    # Generate season archive
    archive = generate_season_archive(
        season_id, matches, league_tables, promotion_relegation, data_dir
    )

    # Add Season Cup data if available
    if cup_display:
        archive["season_cup"] = cup_display

    # Add fixtures data
    if season_fixtures:
        archive["fixtures"] = {
            "upcoming_matches": season_fixtures,
            "total_fixtures": len(season_fixtures),
            "fixtures_by_matchday": organize_fixtures_by_matchday(season_fixtures),
            "fixtures_by_tier": organize_fixtures_by_tier(season_fixtures)
        }
        print(f"  Upcoming fixtures: {len(season_fixtures)}")

    return archive


def get_all_seasons(matches: List[Dict], data_dir: str) -> List[str]:
    """
    Get list of all season IDs from both matches and seasons.json.

    Args:
        matches: List of match dictionaries
        data_dir: Data directory

    Returns:
        List of unique season IDs
    """
    season_ids = set()

    # Get seasons from matches
    for match in matches:
        season_id = match.get("season_id")
        if season_id and match.get("match_type") in ["season", "relegation", "season_cup"]:
            season_ids.add(season_id)

    # Get seasons from seasons.json
    seasons_file = os.path.join(data_dir, "seasons.json")
    if os.path.exists(seasons_file):
        with open(seasons_file, "r", encoding="utf-8") as f:
            seasons_data = json.load(f)
            season_ids.update(seasons_data.keys())

    return sorted(list(season_ids))


def process_all_seasons(matches: List[Dict], fixtures: List[Dict],
                        data_dir: str = DEFAULT_DATA_DIR) -> Dict:
    """
    Process all seasons and generate comprehensive season data.

    Args:
        matches: List of all completed matches
        fixtures: List of all scheduled fixtures
        data_dir: Data directory

    Returns:
        Dictionary with all season data
    """
    all_seasons = get_all_seasons(matches, data_dir)

    if not all_seasons:
        print(f"{YELLOW}No seasons found{RESET}")
        return {"seasons": {}}

    print(f"{BOLD}{CYAN}Found {len(all_seasons)} season(s): {', '.join(all_seasons)}{RESET}")

    all_season_data = {"seasons": {}}

    for season_id in all_seasons:
        season_data = process_season(season_id, matches, fixtures, data_dir)
        if season_data:
            all_season_data["seasons"][season_id] = season_data

    return all_season_data


def save_season_output(data: Dict, output_file: str = DEFAULT_OUTPUT_FILE) -> None:
    """
    Save processed season data to JSON file.

    Args:
        data: Season data dictionary
        output_file: Output file path
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"{GREEN}Saved season data to {output_file}{RESET}")


def generate_season_summary(data: Dict) -> None:
    """
    Print a summary of processed season data.

    Args:
        data: Season data dictionary
    """
    seasons = data.get("seasons", {})

    if not seasons:
        print(f"{YELLOW}No seasons to summarize{RESET}")
        return

    print(f"\n{BOLD}{CYAN}Season Summary{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    for season_id, season_data in seasons.items():
        print(f"{BOLD}{season_id}{RESET}")
        print(f"  League Champion: {season_data.get('league_champion', 'TBD')}")
        print(f"  Cup Winner: {season_data.get('cup_winner', 'TBD')}")
        print(f"  Total Matches: {season_data.get('statistics', {}).get('total_matches', 0)}")

        # Show tier champions
        league_tables = season_data.get("league_tables", {})
        for tier_str, table in league_tables.items():
            if table and len(table) > 0:
                champion = table[0]["bey"]
                print(f"  Tier {tier_str} Champion: {champion}")

        print()


def main():
    """Main entry point for season processing."""
    parser = argparse.ArgumentParser(
        description="Process season data for tiered league system"
    )
    parser.add_argument(
        "--season",
        type=str,
        help="Process specific season (e.g., S1)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all seasons (default)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=DEFAULT_DATA_DIR,
        help="Data directory path"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="Output file path"
    )

    args = parser.parse_args()

    print(f"{BOLD}{CYAN}Season Processing Module{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    # Load matches with ELO data
    print(f"{YELLOW}Loading matches...{RESET}")
    matches_file = os.path.join(args.data_dir, "matches.csv")
    fixtures_file = os.path.join(args.data_dir, "fixtures.csv")
    leaderboard_file = os.path.join(args.data_dir, "leaderboard.csv")

    try:
        matches = load_matches_with_elo(matches_file, leaderboard_file)
        print(f"{GREEN}Loaded {len(matches)} matches{RESET}")
    except FileNotFoundError as e:
        print(f"{YELLOW}Warning: {e}{RESET}")
        print(f"{YELLOW}No completed matches found{RESET}")
        matches = []

    # Load fixtures
    print(f"{YELLOW}Loading fixtures...{RESET}")
    fixtures = load_fixtures(fixtures_file)
    print(f"{GREEN}Loaded {len(fixtures)} fixtures{RESET}\n")

    if not matches and not fixtures:
        print(f"{YELLOW}No season data to process{RESET}")
        return

    # Process seasons
    if args.season:
        # Process specific season
        season_data = process_season(args.season, matches, fixtures, args.data_dir)
        if season_data:
            all_data = {"seasons": {args.season: season_data}}
        else:
            all_data = {"seasons": {}}
    else:
        # Process all seasons
        all_data = process_all_seasons(matches, fixtures, args.data_dir)

    # Save output
    save_season_output(all_data, args.output)

    # Print summary
    generate_season_summary(all_data)

    print(f"\n{GREEN}{BOLD}✓ Season processing complete!{RESET}")


if __name__ == "__main__":
    main()
