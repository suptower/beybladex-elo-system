"""
Table Snapshots Generator

Generates league table snapshots at each matchday for visualization.
Shows position deltas (change from previous matchday) for tracking movement.

This module is designed to be called from season_processing.py pipeline.

Output:
    CSV files with table snapshots: docs/data/table_snapshots_{season_id}_{tier}.csv

Columns:
    - matchday: Matchday number
    - position: Final position in table after this matchday
    - bey: Bey name
    - matches: Total matches played
    - wins: Total wins
    - losses: Total losses
    - season_points: Total season points
    - points_for: Total round points scored
    - points_against: Total round points conceded
    - point_diff: Points for - Points against
    - elo: Current ELO rating
    - position_delta: Change in position from previous matchday (can be +N, -N, or 0)
"""

import csv
import os
from collections import defaultdict
from typing import Dict, List

from season_manager import calculate_season_points


def generate_table_snapshot(matches: List[Dict], matchday: int, tier: int, season_id: str) -> List[Dict]:
    """
    Generate table standings snapshot after a specific matchday.

    Args:
        matches: All season matches
        matchday: The matchday number to calculate standings for
        tier: Tier number
        season_id: Season identifier

    Returns:
        List of standings dictionaries sorted by position
    """
    # Filter matches up to and including this matchday
    relevant_matches = [
        m for m in matches
        if m.get("match_type") == "season"
        and m.get("season_id") == season_id
        and m.get("tier") == tier
        and m.get("matchday") is not None
        and int(m.get("matchday")) <= matchday
    ]

    # Initialize standings
    standings = defaultdict(lambda: {
        "bey": "",
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "season_points": 0,
        "points_for": 0,
        "points_against": 0,
        "point_diff": 0,
        "elo": 0
    })

    # Process matches
    for match in relevant_matches:
        bey_a = match["bey_a"]
        bey_b = match["bey_b"]
        score_a = int(match["score_a"])
        score_b = int(match["score_b"])

        # Calculate season points
        sp_a, sp_b = calculate_season_points(score_a, score_b)

        # Update standings for bey_a
        standings[bey_a]["bey"] = bey_a
        standings[bey_a]["matches"] += 1
        standings[bey_a]["season_points"] += sp_a
        standings[bey_a]["points_for"] += score_a
        standings[bey_a]["points_against"] += score_b
        if score_a > score_b:
            standings[bey_a]["wins"] += 1
        elif score_a < score_b:
            standings[bey_a]["losses"] += 1

        # Update standings for bey_b
        standings[bey_b]["bey"] = bey_b
        standings[bey_b]["matches"] += 1
        standings[bey_b]["season_points"] += sp_b
        standings[bey_b]["points_for"] += score_b
        standings[bey_b]["points_against"] += score_a
        if score_b > score_a:
            standings[bey_b]["wins"] += 1
        elif score_b < score_a:
            standings[bey_b]["losses"] += 1

        # Get ELO from match if available
        if "elo_a" in match and match["elo_a"]:
            standings[bey_a]["elo"] = float(match.get("elo_a", 1000))
        if "elo_b" in match and match["elo_b"]:
            standings[bey_b]["elo"] = float(match.get("elo_b", 1000))

    # Calculate point differences
    for bey_data in standings.values():
        bey_data["point_diff"] = bey_data["points_for"] - bey_data["points_against"]

    # Convert to list and sort
    table = list(standings.values())
    table.sort(key=lambda x: (
        -x["season_points"],  # Higher is better
        -x["point_diff"],     # Higher is better
        -x["points_for"],     # Higher is better
        -x["elo"]             # Higher is better
    ))

    return table


def calculate_position_deltas(current_table: List[Dict], previous_table: List[Dict]) -> Dict[str, int]:
    """
    Calculate position changes from previous matchday.

    Args:
        current_table: Current matchday standings
        previous_table: Previous matchday standings

    Returns:
        Dictionary mapping bey name to position delta (+N for up, -N for down, 0 for same)
    """
    if not previous_table:
        # First matchday, no deltas
        return {entry["bey"]: 0 for entry in current_table}

    # Get previous positions
    prev_positions = {entry["bey"]: idx + 1 for idx, entry in enumerate(previous_table)}

    # Calculate deltas
    deltas = {}
    for idx, entry in enumerate(current_table):
        bey = entry["bey"]
        current_pos = idx + 1
        prev_pos = prev_positions.get(bey, current_pos)
        # Positive delta means moved up (better position, lower number)
        deltas[bey] = prev_pos - current_pos

    return deltas


def generate_all_table_snapshots(matches: List[Dict], season_id: str,
                                 output_dir: str = "./docs/data") -> None:
    """
    Generate table snapshots for all matchdays and tiers in a season.

    Args:
        matches: All matches data
        season_id: Season identifier
        output_dir: Directory to save CSV files
    """
    # Get all matchdays per tier
    matchdays_by_tier = defaultdict(set)
    for match in matches:
        if (match.get("match_type") == "season"
                and match.get("season_id") == season_id
                and match.get("matchday") is not None):
            tier = match.get("tier")
            matchday = int(match.get("matchday"))
            matchdays_by_tier[tier].add(matchday)

    # Process each tier
    for tier in sorted(matchdays_by_tier.keys()):
        matchdays = sorted(matchdays_by_tier[tier])

        if not matchdays:
            continue

        output_file = os.path.join(output_dir, f"table_snapshots_{season_id}_tier{tier}.csv")

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "matchday", "position", "bey", "matches", "wins", "losses",
                "season_points", "points_for", "points_against", "point_diff",
                "elo", "position_delta"
            ])

            previous_table = []
            for matchday in matchdays:
                current_table = generate_table_snapshot(matches, matchday, tier, season_id)
                deltas = calculate_position_deltas(current_table, previous_table)

                for position, entry in enumerate(current_table, start=1):
                    bey = entry["bey"]
                    delta = deltas[bey]

                    writer.writerow([
                        matchday,
                        position,
                        bey,
                        entry["matches"],
                        entry["wins"],
                        entry["losses"],
                        entry["season_points"],
                        entry["points_for"],
                        entry["points_against"],
                        entry["point_diff"],
                        round(entry["elo"], 2),
                        delta
                    ])

                previous_table = current_table

        print(f"Generated table snapshots for {season_id} Tier {tier}: {output_file}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    # Example usage
    print("Table Snapshots Generator")
    print("This module should be called from season_processing.py")
    print("\nTo generate snapshots manually:")
    print("  from table_snapshots import generate_all_table_snapshots")
    print("  generate_all_table_snapshots(matches, 'S1')")
