#!/usr/bin/env python3
"""
Season Initialization Utility

This script helps initialize a new season by:
1. Reading current ELO rankings from leaderboard.csv
2. Assigning Beys to tiers based on ELO
3. Creating season metadata
4. Optionally generating match schedule CSV templates

Usage:
    python src/season/init_season.py S1
    python src/season/init_season.py S2 --generate-schedule
    python src/season/init_season.py S3 --data-dir ./docs/data
    python src/season/init_season.py S3 --from-season S2
"""

import argparse
import csv
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from season_manager import (   # noqa: E402
    initialize_season,
    initialize_season_from_results,
    load_season_data,
    save_season_data,
    schedule_round_robin,
    TIERS,
    BEYS_PER_TIER
)

import os as _os   # noqa: E402
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root
from src.config.paths import DATA_DIR, LEADERBOARD_CSV, SEASONS_JSON   # noqa: E402

# Default paths
DEFAULT_DATA_DIR = DATA_DIR
DEFAULT_LEADERBOARD = LEADERBOARD_CSV

# Colors for output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"


def load_current_elo(leaderboard_file: str):
    """
    Load current ELO ratings from leaderboard.csv

    Args:
        leaderboard_file: Path to leaderboard.csv

    Returns:
        List of tuples (bey_name, elo_rating)
    """
    if not os.path.exists(leaderboard_file):
        raise FileNotFoundError(
            f"Leaderboard file not found: {leaderboard_file}")

    beys_with_elo = []
    with open(leaderboard_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try both 'Name' and 'Bey' columns for compatibility
            bey = row.get('Name') or row.get('Bey')
            elo_str = row.get('ELO') or row.get('Elo')
            if bey and elo_str:
                elo = float(elo_str)
                beys_with_elo.append((bey, elo))

    return beys_with_elo


def print_tier_assignments(season_data):
    """
    Print tier assignments in a readable format

    Args:
        season_data: Season data dictionary
    """
    print(f"\n{BOLD}{CYAN}Tier Assignments for {season_data['season_id']}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    tier_assignments = season_data['tier_assignments']

    # Group by tier
    tiers = {}
    for bey, data in tier_assignments.items():
        tier = data['tier']
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append((bey, data['start_elo']))

    # Print each tier
    for tier in range(1, TIERS + 1):
        print(f"{BOLD}Tier {tier}{RESET}")
        if tier in tiers:
            # Sort by ELO (highest first); treat None as 0 for sorting
            tier_beys = sorted(
                tiers[tier],
                key=lambda x: x[1] if x[1] is not None else 0,
                reverse=True
            )
            for i, (bey, elo) in enumerate(tier_beys, 1):
                elo_str = f"{elo:.0f}" if elo is not None else "N/A"
                print(f"  {i:2d}. {bey:20s} (ELO: {elo_str})")
        print()


def generate_schedule_csv(season_data, output_dir: str):
    """
    Generate match schedule CSV template for the season

    Args:
        season_data: Season data dictionary
        output_dir: Directory to save schedule files
    """
    season_id = season_data['season_id']
    tier_assignments = season_data['tier_assignments']

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate schedule for each tier
    for tier in range(1, TIERS + 1):
        # Get beys in this tier
        tier_beys = [
            bey for bey,
            data in tier_assignments.items() if data['tier'] == tier]

        # Generate round-robin schedule
        matches = schedule_round_robin(tier_beys)

        # Write to CSV
        filename = os.path.join(
            output_dir, f"{season_id}_tier{tier}_schedule.csv")
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'MatchID', 'Date', 'BeyA', 'BeyB', 'ScoreA', 'ScoreB',
                'MatchType', 'SeasonID', 'Tier', 'Matchday'
            ])

            # Distribute matches across matchdays
            matches_per_matchday = len(matches) // (BEYS_PER_TIER - 1)
            for matchday in range(1, BEYS_PER_TIER):
                start_idx = (matchday - 1) * matches_per_matchday
                end_idx = start_idx + matches_per_matchday
                if matchday == BEYS_PER_TIER - 1:
                    # Last matchday gets remaining matches
                    end_idx = len(matches)

                for idx in range(start_idx, end_idx):
                    if idx < len(matches):
                        bey_a, bey_b = matches[idx]
                        match_id = f"M{season_id}-T{tier}-MD{matchday:02d}-{idx - start_idx + 1:02d}"
                        writer.writerow([
                            match_id,
                            '',  # Date - to be filled in
                            bey_a,
                            bey_b,
                            '',  # ScoreA - to be filled in
                            '',  # ScoreB - to be filled in
                            'season',
                            season_id,
                            tier,
                            matchday
                        ])

        print(
            f"{GREEN}✓{RESET} Generated schedule for Tier {tier}: {filename}")


def load_season_archive(prev_season_id: str, data_dir: str) -> dict:
    """
    Load a completed season's processed archive from season_data.json.

    The archive is generated by ``python update.py`` (or
    ``season_processing.py``) after a season ends and contains the
    ``promotion_relegation`` result produced by ``get_promotion_relegation()``.

    The archive is read from ``<data_dir>/season/season_data.json``, where
    ``data_dir`` is the root data directory (e.g., ``docs/data``).

    Args:
        prev_season_id: Identifier of the completed season (e.g., "S1").
        data_dir: Root data directory (e.g., ``docs/data``).  The archive is
            resolved under the ``season/`` subdirectory of this path.

    Returns:
        The archive dict for the season.

    Raises:
        FileNotFoundError: If ``season_data.json`` does not exist.
        ValueError: If no data is found for ``prev_season_id``.
    """
    season_dir = os.path.join(data_dir, "season")
    archive_file = os.path.join(season_dir, "season_data.json")
    if not os.path.exists(archive_file):
        raise FileNotFoundError(
            f"Processed season archive not found: {archive_file}\n"
            f"Run 'python update.py' after season {prev_season_id} ends "
            "to generate it."
        )
    with open(archive_file, "r", encoding="utf-8") as f:
        all_archives = json.load(f)

    season_archive = all_archives.get("seasons", {}).get(prev_season_id)
    if season_archive is None:
        raise ValueError(
            f"No archive data found for season '{prev_season_id}' "
            f"in {archive_file}.\n"
            "Make sure the season has been fully processed by update.py."
        )
    return season_archive


def main():
    """Main entry point for season initialization"""
    parser = argparse.ArgumentParser(
        description="Initialize a new season from current ELO rankings or previous season results"
    )
    parser.add_argument(
        'season_id',
        type=str,
        help='Season identifier (e.g., S1, S2, S3)'
    )
    parser.add_argument(
        '--from-season',
        type=str,
        default=None,
        metavar='PREV_SEASON_ID',
        help=(
            'Initialize tier assignments from promotion/relegation results of '
            'a completed season (e.g., --from-season S2). '
            'Requires that update.py has already been run for that season so '
            'that season_data.json contains its promotion_relegation data. '
            'When this flag is used the leaderboard is only consulted for '
            'current ELO values, not for ordering.'
        )
    )
    parser.add_argument(
        '--leaderboard',
        type=str,
        default=DEFAULT_LEADERBOARD,
        help='Path to leaderboard.csv (default: ./docs/data/leaderboard/leaderboard.csv)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default=DEFAULT_DATA_DIR,
        help='Data directory path (default: ./docs/data)'
    )
    parser.add_argument(
        '--generate-schedule',
        action='store_true',
        help='Generate match schedule CSV templates for each tier'
    )
    parser.add_argument(
        '--schedule-dir',
        type=str,
        default='./season_schedules',
        help='Directory to save schedule files (default: ./season_schedules)'
    )

    args = parser.parse_args()

    print(f"{BOLD}{CYAN}Season Initialization Utility{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    try:
        # Always load ELO rankings — needed for start_elo values and as a
        # tiebreaker / fill-in source even when --from-season is used.
        print(f"{YELLOW}Loading ELO rankings from {args.leaderboard}...{RESET}")
        beys_with_elo = load_current_elo(args.leaderboard)
        print(f"{GREEN}✓{RESET} Loaded {len(beys_with_elo)} Beys\n")

        elo_lookup = dict(beys_with_elo)

        # Derive the season subdirectory from --data-dir so all reads/writes
        # respect the user-provided root rather than the repo default.
        season_dir = os.path.join(args.data_dir, "season")

        if args.from_season:
            # --- Promotion/relegation-based initialisation ---
            prev_id = args.from_season
            print(
                f"{YELLOW}Loading season '{prev_id}' promotion/relegation "
                f"results from season_data.json...{RESET}"
            )
            season_archive = load_season_archive(prev_id, args.data_dir)
            promotion_relegation = season_archive.get("promotion_relegation")
            if not promotion_relegation:
                raise ValueError(
                    f"Season '{prev_id}' archive does not contain "
                    "promotion_relegation data. "
                    "Run 'python update.py' after the season ends."
                )
            print(f"{GREEN}✓{RESET} Loaded promotion/relegation data\n")

            print(f"{YELLOW}Loading '{prev_id}' tier composition from seasons.json...{RESET}")
            prev_season_data = load_season_data(prev_id, season_dir)
            if not prev_season_data:
                raise ValueError(
                    f"Season '{prev_id}' not found in seasons.json."
                )
            prev_tier_assignments = prev_season_data.get("tier_assignments", {})
            prev_qualification_pool = prev_season_data.get("qualification_pool", [])
            print(
                f"{GREEN}✓{RESET} Loaded {len(prev_tier_assignments)} bey "
                "tier assignments\n"
            )

            print(
                f"{YELLOW}Initializing {args.season_id} from '{prev_id}' "
                f"promotion/relegation results...{RESET}"
            )
            season_data, warnings = initialize_season_from_results(
                args.season_id,
                prev_tier_assignments,
                prev_qualification_pool,
                promotion_relegation,
                elo_lookup,
            )
            print(f"{GREEN}✓{RESET} Season initialized\n")

            if warnings:
                print(f"{BOLD}{YELLOW}Warnings:{RESET}")
                for w in warnings:
                    print(f"  {YELLOW}⚠{RESET}  {w}")
                print()

        else:
            # --- ELO-based initialisation (original behaviour) ---
            print(f"{YELLOW}Initializing {args.season_id}...{RESET}")
            season_data = initialize_season(
                args.season_id, beys_with_elo, args.data_dir)
            print(f"{GREEN}✓{RESET} Season initialized\n")

        # Save season data
        print(f"{YELLOW}Saving season metadata...{RESET}")
        save_season_data(season_data, season_dir)
        saved_path = os.path.join(season_dir, os.path.basename(SEASONS_JSON))
        print(f"{GREEN}✓{RESET} Saved to {saved_path}\n")

        # Print tier assignments
        print_tier_assignments(season_data)

        # Generate schedule if requested
        if args.generate_schedule:
            print(f"\n{YELLOW}Generating match schedules...{RESET}\n")
            generate_schedule_csv(season_data, args.schedule_dir)

        # Print next steps
        print(f"\n{BOLD}{GREEN}✓ Season {args.season_id} initialized successfully!{RESET}\n")
        print(f"{BOLD}Next Steps:{RESET}")
        print(
            "1. Review tier assignments above to ensure they're correct")

        if args.generate_schedule:
            print(
                f"2. Find schedule templates in {args.schedule_dir}/")
            print("3. Fill in dates and match results")
            print(
                "4. Import completed matches to docs/data/matches/matches.csv")
        else:
            print(
                "2. Create season matches manually or use --generate-schedule")
            print("3. Add matches to docs/data/matches/matches.csv with:")
            print("   - MatchType: season")
            print(f"   - SeasonID: {args.season_id}")
            print("   - Tier: 1-4")
            print("   - Matchday: 1-7")

        print("5. Run 'python update.py' to process season data")
        print(
            f"6. View results at /seasons.html#{args.season_id}\n")

        # Show qualification pool if any
        if args.from_season:
            qual_pool = season_data.get("qualification_pool", [])
            if qual_pool:
                print(f"{BOLD}{YELLOW}Qualification Pool ({len(qual_pool)} Beys):{RESET}")
                for entry in qual_pool:
                    bey = entry.get("bey", "?")
                    elo = entry.get("elo", 0)
                    print(f"  • {bey:20s} (ELO: {elo:.0f})")
                print()
        elif len(beys_with_elo) > 32:
            print(f"{BOLD}{YELLOW}Qualification Pool:{RESET}")
            print(f"  {len(beys_with_elo) - 32} Beys outside Top 32 will enter Qualification Tournament")
            print("  for Tier IV slots in the next season.\n")

    except FileNotFoundError as e:
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1)
    except ValueError as e:
        print(f"{RED}Error: {e}{RESET}")
        if not args.from_season:
            print(
                f"{YELLOW}Hint: Ensure you have at least 32 Beys in the leaderboard for league tiers{RESET}")
            print(
                f"{YELLOW}      Additional Beys will be placed in Qualification Pool{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
