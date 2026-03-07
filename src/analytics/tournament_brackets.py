"""
Tournament Bracket Generator for Low-Data Beys

This module creates tournament brackets specifically designed for Beyblades with
low match counts to help gather more statistical data efficiently.

Features:
- Identifies beys with low match counts
- Generates tournament brackets (Round-Robin, Single Elimination)
- Provides tournament recommendations based on data needs
- Creates ready-to-use matchup schedules

Output:
- tournament_brackets.json: Tournament bracket recommendations and schedules
"""
import csv
import json
import statistics
from collections import defaultdict
from datetime import date, timedelta

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import (
    LEADERBOARD_CSV,
    MATCHES_CSV,
    TOURNAMENT_BRACKETS_JSON,
)

# Colors for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"

# File paths
TOURNAMENT_BRACKETS_OUTPUT = TOURNAMENT_BRACKETS_JSON

# Configuration constants
CONFIG = {
    "low_data_threshold_percentile": 0.40,  # Below 40th percentile
    "min_matches_for_tournament": 2,  # Minimum matches to be considered
    "min_participants": 4,  # Minimum participants for a tournament
    "round_robin_max_participants": 8,  # Max participants for round-robin
    "preferred_bracket_sizes": [4, 8, 16],  # Preferred tournament sizes
}


def load_leaderboard_data():
    """
    Load leaderboard data with match counts.

    Returns:
        dict: Beyblade name -> stats dict
    """
    beys = {}

    try:
        with open(LEADERBOARD_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Name']
                beys[name] = {
                    'elo': float(row['ELO']),
                    'matches': int(row['Spiele']),
                    'wins': int(row['Siege']),
                    'losses': int(row['Niederlagen']),
                    'winrate': float(row['Winrate'].rstrip('%')) / 100.0,
                    'rank': int(row['Platz'])
                }
    except FileNotFoundError:
        print(f"{RED}Error: {LEADERBOARD_CSV} not found{RESET}")
        return {}

    return beys


def load_matchup_history():
    """
    Load match history to determine which Beys have played each other.

    Returns:
        dict: (bey_a, bey_b) -> match count (normalized order)
    """
    matchups = defaultdict(int)

    try:
        with open(MATCHES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bey_a = row['BeyA']
                bey_b = row['BeyB']
                # Normalize order (alphabetical) to avoid duplicate pairs
                pair = tuple(sorted([bey_a, bey_b]))
                matchups[pair] += 1
    except FileNotFoundError:
        print(f"{RED}Error: {MATCHES_CSV} not found{RESET}")
        return {}

    return matchups


def identify_low_data_beys(beys):
    """
    Identify Beys with significantly fewer matches than average.

    Args:
        beys: Dict of bey stats

    Returns:
        list: Bey names that need more matches
    """
    if not beys:
        return []

    match_counts = [stats['matches'] for stats in beys.values()]

    # Use quantiles to find threshold, with bounds checking
    percentile = CONFIG['low_data_threshold_percentile']
    if percentile >= 1.0:
        percentile = 0.99

    quantiles = statistics.quantiles(match_counts, n=100)
    threshold_index = max(0, min(len(quantiles) - 1, int(percentile * 100) - 1))
    threshold = quantiles[threshold_index]

    low_data = [
        name for name, stats in beys.items()
        if stats['matches'] < threshold and stats['matches'] >= CONFIG['min_matches_for_tournament']
    ]

    return low_data


def generate_round_robin_bracket(participants, matchups):
    """
    Generate a round-robin tournament bracket.

    Args:
        participants: List of participant names
        matchups: Dict of existing matchup counts

    Returns:
        dict: Round-robin bracket with matchups
    """
    rounds = []
    n = len(participants)

    if n < 2:
        return {"rounds": []}

    # If odd number, add a dummy for bye rounds
    if n % 2 == 1:
        participants = participants + ["BYE"]
        n += 1

    # Use round-robin algorithm
    fixed = participants[0]
    rotating = participants[1:]

    for round_num in range(n - 1):
        round_matches = []
        current_round = [fixed] + rotating

        # Pair up: first with last, second with second-last, etc.
        for i in range(n // 2):
            bey_a = current_round[i]
            bey_b = current_round[n - 1 - i]

            # Skip if either is a bye
            if bey_a == "BYE" or bey_b == "BYE":
                continue

            # Get existing match count
            pair = tuple(sorted([bey_a, bey_b]))
            existing = matchups.get(pair, 0)

            round_matches.append({
                "bey_a": bey_a,
                "bey_b": bey_b,
                "existing_matches": existing
            })

        if round_matches:
            rounds.append({
                "round": round_num + 1,
                "matches": round_matches
            })

        # Rotate (keep first fixed, rotate others)
        rotating = [rotating[-1]] + rotating[:-1]

    return {
        "format": "round_robin",
        "participants": [p for p in participants if p != "BYE"],
        "total_rounds": len(rounds),
        "total_matches": sum(len(r["matches"]) for r in rounds),
        "rounds": rounds
    }


def generate_single_elimination_bracket(participants, matchups):
    """
    Generate a single elimination tournament bracket.

    Args:
        participants: List of participant names (should be power of 2)
        matchups: Dict of existing matchup counts

    Returns:
        dict: Single elimination bracket
    """
    import math

    n = len(participants)
    if n < 2:
        return {"rounds": []}

    # Pad to next power of 2
    next_power = 2 ** math.ceil(math.log2(n))
    byes_needed = next_power - n

    # Create initial bracket with byes
    current_round = participants.copy()

    # Add byes (will get auto-wins to next round)
    for i in range(byes_needed):
        current_round.append("BYE")

    rounds = []
    round_num = 1

    while len(current_round) > 1:
        round_matches = []
        next_round = []

        # Pair up adjacent participants
        for i in range(0, len(current_round), 2):
            bey_a = current_round[i]
            bey_b = current_round[i + 1]

            # Handle byes - winner advances automatically
            if bey_a == "BYE":
                next_round.append(bey_b)
                continue
            elif bey_b == "BYE":
                next_round.append(bey_a)
                continue

            # Get existing match count
            pair = tuple(sorted([bey_a, bey_b]))
            existing = matchups.get(pair, 0)

            round_matches.append({
                "match_id": f"R{round_num}M{len(round_matches) + 1}",
                "bey_a": bey_a,
                "bey_b": bey_b,
                "existing_matches": existing,
                "winner_advances_to": f"R{round_num + 1}M{len(next_round) // 2 + 1}"
            })

            # Winner TBD
            next_round.append(f"Winner of {round_matches[-1]['match_id']}")

        if round_matches:
            if len(current_round) == 2:
                round_name = "Finals"
            elif len(current_round) == 4:
                round_name = "Semi-Finals"
            elif len(current_round) == 8:
                round_name = "Quarter-Finals"
            else:
                round_name = f"Round of {len(current_round)}"

            rounds.append({
                "round": round_num,
                "name": round_name,
                "matches": round_matches
            })

        current_round = next_round
        round_num += 1

    return {
        "format": "single_elimination",
        "participants": participants,
        "total_rounds": len(rounds),
        "total_matches": sum(len(r["matches"]) for r in rounds),
        "rounds": rounds
    }


def recommend_tournament_type(low_data_beys, beys):
    """
    Recommend the best tournament type based on the number of low-data beys.

    Args:
        low_data_beys: List of bey names with low data
        beys: Dict of all bey stats

    Returns:
        dict: Tournament recommendation
    """
    n = len(low_data_beys)

    if n < CONFIG["min_participants"]:
        min_required = CONFIG['min_participants']
        return {
            "recommended": None,
            "reason": f"Not enough low-data beys ({n}). Minimum {min_required} needed.",
            "alternatives": ["Use individual match recommendations instead"]
        }

    # Calculate average matches for low-data beys
    avg_matches = statistics.mean([beys[name]['matches'] for name in low_data_beys])

    # Recommend based on count and data needs
    if n <= CONFIG["round_robin_max_participants"]:
        total_matches = n * (n - 1) // 2
        return {
            "recommended": "round_robin",
            "reason": (f"Round-robin is ideal for {n} participants. "
                       f"Each bey will play {n - 1} matches, "
                       f"totaling {total_matches} matches."),
            "benefits": [
                "Every bey plays every other bey",
                "Maximum data collection per bey",
                "Fair and balanced",
                f"Average current matches: {avg_matches:.1f}"
            ]
        }
    else:
        # Find nearest power of 2
        import math
        bracket_size = 2 ** math.ceil(math.log2(n))
        matches_per_winner = int(math.log2(bracket_size))

        return {
            "recommended": "single_elimination",
            "reason": (f"Single elimination is best for {n} participants. "
                       f"Bracket size: {bracket_size}, "
                       f"winner plays {matches_per_winner} matches."),
            "benefits": [
                "Efficient for large participant counts",
                "Creates exciting playoff-style competition",
                "Identifies top performers",
                f"Average current matches: {avg_matches:.1f}"
            ],
            "note": f"Some beys may need byes ({bracket_size - n} byes needed)"
        }


def generate_tournament_schedule(bracket, start_date=None):
    """
    Generate a dated schedule for a tournament bracket.

    Args:
        bracket: Tournament bracket dict
        start_date: Starting date (defaults to today)

    Returns:
        list: Dated matches ready for import
    """
    if start_date is None:
        start_date = date.today()
    elif isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    schedule = []
    current_date = start_date

    for round_data in bracket.get("rounds", []):
        round_num = round_data.get("round", 1)

        for match in round_data.get("matches", []):
            schedule.append({
                "date": current_date.isoformat(),
                "round": round_num,
                "bey_a": match["bey_a"],
                "bey_b": match["bey_b"],
                "existing_matches": match.get("existing_matches", 0)
            })

        # Move to next day for next round
        current_date += timedelta(days=1)

    return schedule


def run_tournament_bracket_pipeline():
    """
    Main pipeline to generate tournament brackets for low-data beys.

    Returns:
        dict: Complete tournament bracket recommendations
    """
    print(f"{CYAN}{BOLD}Generating Tournament Brackets for Low-Data Beys...{RESET}")

    # Load data
    print("  Loading leaderboard data...")
    beys = load_leaderboard_data()

    if not beys:
        print(f"{RED}Error: No beyblade data loaded{RESET}")
        return None

    print("  Loading matchup history...")
    matchups = load_matchup_history()

    # Identify low-data beys
    print("  Identifying low-data beys...")
    low_data_beys = identify_low_data_beys(beys)

    if not low_data_beys:
        print(f"{YELLOW}No low-data beys identified{RESET}")
        output = {
            "metadata": {
                "total_beys": len(beys),
                "low_data_beys": 0,
                "recommendation": "All beys have sufficient match data"
            },
            "brackets": []
        }
    else:
        # Sort by match count (lowest first) for prioritization
        low_data_beys.sort(key=lambda name: beys[name]['matches'])

        print(f"  Found {len(low_data_beys)} low-data beys")

        # Get tournament recommendation
        recommendation = recommend_tournament_type(low_data_beys, beys)

        # Generate brackets
        brackets = []

        if recommendation["recommended"] == "round_robin":
            print("  Generating round-robin bracket...")
            bracket = generate_round_robin_bracket(low_data_beys, matchups)
            schedule = generate_tournament_schedule(bracket)
            brackets.append({
                "type": "round_robin",
                "bracket": bracket,
                "schedule": schedule
            })

        elif recommendation["recommended"] == "single_elimination":
            print("  Generating single elimination bracket...")
            bracket = generate_single_elimination_bracket(low_data_beys, matchups)
            schedule = generate_tournament_schedule(bracket)
            brackets.append({
                "type": "single_elimination",
                "bracket": bracket,
                "schedule": schedule
            })

        # Also generate a smaller round-robin for the lowest data beys
        if len(low_data_beys) > CONFIG["round_robin_max_participants"]:
            print("  Generating focused round-robin for lowest-data beys...")
            focus_group = low_data_beys[:CONFIG["round_robin_max_participants"]]
            focus_bracket = generate_round_robin_bracket(focus_group, matchups)
            focus_schedule = generate_tournament_schedule(focus_bracket)
            brackets.append({
                "type": "round_robin_focused",
                "bracket": focus_bracket,
                "schedule": focus_schedule,
                "note": f"Focused on {len(focus_group)} beys with the lowest match counts"
            })

        # Create output structure
        all_matches = [s['matches'] for s in beys.values()]
        low_data_matches = [beys[n]['matches'] for n in low_data_beys]
        output = {
            "metadata": {
                "total_beys": len(beys),
                "low_data_beys": len(low_data_beys),
                "average_matches_all": statistics.mean(all_matches),
                "average_matches_low_data": statistics.mean(low_data_matches),
                "recommendation": recommendation
            },
            "low_data_bey_list": [
                {
                    "name": name,
                    "matches": beys[name]['matches'],
                    "elo": beys[name]['elo'],
                    "rank": beys[name]['rank']
                }
                for name in low_data_beys
            ],
            "brackets": brackets
        }

    # Save to JSON
    with open(TOURNAMENT_BRACKETS_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"{GREEN} Tournament brackets saved to {TOURNAMENT_BRACKETS_OUTPUT}{RESET}")

    # Print summary
    if low_data_beys:
        print(f"\n{BOLD}Tournament Bracket Summary:{RESET}")
        print(f"  Low-data beys: {len(low_data_beys)}")
        print(f"  Recommended format: {recommendation.get('recommended', 'N/A')}")
        print(f"  {recommendation.get('reason', '')}")
        print("\n  Low-data beys (sorted by match count):")
        for bey in low_data_beys[:10]:  # Show top 10
            stats = beys[bey]
            print(f"    - {bey}: {stats['matches']} matches (ELO: {stats['elo']:.0f})")
        if len(low_data_beys) > 10:
            print(f"    ... and {len(low_data_beys) - 10} more")

    return output


if __name__ == "__main__":
    run_tournament_bracket_pipeline()
