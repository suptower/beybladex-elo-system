# matchup_matrix.py
"""
Matchup Matrix Generator for Beyblade Analytics

This module creates a comprehensive Bey-vs-Bey matchup matrix showing:
- Win rates for each matchup
- Number of matches played
- Average point differential
- Symmetric handling of matchups

The matrix provides insights into hard counters and matchup dynamics.
"""

import json
import csv
from collections import defaultdict
from typing import Dict, List, Tuple

from src.config.paths import (
    MATCHES_CSV,
    BEYS_DATA_JSON,
    LEADERBOARD_CSV,
    RPG_STATS_JSON,
    MATCHUP_MATRIX_JSON,
)

# File paths
OUTPUT_JSON = MATCHUP_MATRIX_JSON


def load_matches() -> List[Dict]:
    """Load all match data from CSV."""
    matches = []
    with open(MATCHES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(row)
    return matches


def load_bey_metadata() -> Tuple[Dict, Dict, Dict]:
    """
    Load bey metadata including ELO, tier, and archetype information.

    Returns:
        Tuple of (elo_map, tier_map, archetype_map)
    """
    # Load ELO and tier data from leaderboard
    elo_map = {}
    tier_map = {}
    try:
        with open(LEADERBOARD_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bey = row.get('Name') or row.get('Bey', '')
                elo = row.get('ELO') or row.get('CurrentElo', '1500')
                elo_map[bey] = float(elo)
                tier_map[bey] = row.get('Tier', 'Unranked')
    except FileNotFoundError:
        print(f"Warning: {LEADERBOARD_CSV} not found, using default values")

    # Load archetype data from RPG stats
    archetype_map = {}
    try:
        with open(RPG_STATS_JSON, 'r', encoding='utf-8') as f:
            rpg_data = json.load(f)
            for bey, bey_data in rpg_data.items():
                if isinstance(bey_data, dict):
                    archetype = bey_data.get('archetype', 'Unknown')
                    # Handle both string and object archetype formats
                    if isinstance(archetype, dict):
                        archetype_map[bey] = archetype.get('name', 'Unknown')
                    else:
                        archetype_map[bey] = archetype if archetype else 'Unknown'
    except FileNotFoundError:
        print(f"Warning: {RPG_STATS_JSON} not found, using default values")

    return elo_map, tier_map, archetype_map


def calculate_matchup_matrix(matches: List[Dict]) -> Dict:
    """
    Calculate the matchup matrix from match history.

    For each Bey pair (A, B), tracks:
    - Wins for A against B
    - Total matches between A and B
    - Score differential (A's score - B's score)

    Args:
        matches: List of match dictionaries

    Returns:
        Nested dictionary: matchup_data[beyA][beyB] = stats
    """
    matchup_data = defaultdict(lambda: defaultdict(lambda: {
        'wins': 0,
        'losses': 0,
        'total_matches': 0,
        'score_for': 0,
        'score_against': 0
    }))

    for match in matches:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])

        # Skip ties
        if score_a == score_b:
            continue

        # Update matchup stats for both directions
        matchup_data[bey_a][bey_b]['total_matches'] += 1
        matchup_data[bey_a][bey_b]['score_for'] += score_a
        matchup_data[bey_a][bey_b]['score_against'] += score_b

        matchup_data[bey_b][bey_a]['total_matches'] += 1
        matchup_data[bey_b][bey_a]['score_for'] += score_b
        matchup_data[bey_b][bey_a]['score_against'] += score_a

        if score_a > score_b:
            matchup_data[bey_a][bey_b]['wins'] += 1
            matchup_data[bey_b][bey_a]['losses'] += 1
        else:
            matchup_data[bey_b][bey_a]['wins'] += 1
            matchup_data[bey_a][bey_b]['losses'] += 1

    return matchup_data


def build_matrix_output(matchup_data: Dict, elo_map: Dict, tier_map: Dict, archetype_map: Dict) -> Dict:
    """
    Build the final output structure for the matchup matrix.

    Args:
        matchup_data: Raw matchup statistics
        elo_map: Bey name to ELO mapping
        tier_map: Bey name to tier mapping
        archetype_map: Bey name to archetype mapping

    Returns:
        Dictionary with beys list and matchup matrix
    """
    # Get all beys that have participated in matches
    all_beys = sorted(matchup_data.keys())

    # Build bey metadata list
    beys = []
    for bey in all_beys:
        beys.append({
            'name': bey,
            'elo': elo_map.get(bey, 1500),
            'tier': tier_map.get(bey, 'Unranked'),
            'archetype': archetype_map.get(bey, 'Unknown')
        })

    # Build matchup matrix
    matrix = {}
    for bey_a in all_beys:
        matrix[bey_a] = {}
        for bey_b in all_beys:
            if bey_a == bey_b:
                # Self-matchup - mark as N/A
                matrix[bey_a][bey_b] = {
                    'winrate': None,
                    'matches': 0,
                    'avg_diff': None
                }
            elif bey_b in matchup_data[bey_a]:
                stats = matchup_data[bey_a][bey_b]
                total = stats['total_matches']
                wins = stats['wins']

                if total > 0:
                    winrate = wins / total
                    avg_diff = (stats['score_for'] - stats['score_against']) / total
                else:
                    winrate = 0.0
                    avg_diff = 0.0

                matrix[bey_a][bey_b] = {
                    'winrate': round(winrate, 3),
                    'matches': total,
                    'wins': wins,
                    'losses': stats['losses'],
                    'avg_diff': round(avg_diff, 2)
                }
            else:
                # No matches between these beys
                matrix[bey_a][bey_b] = {
                    'winrate': None,
                    'matches': 0,
                    'avg_diff': None
                }

    return {
        'beys': beys,
        'matrix': matrix,
        'generated_at': None  # Will be filled by caller if needed
    }


def identify_hard_counters(matrix_data: Dict, min_matches: int = 5, winrate_threshold: float = 0.7) -> List[Dict]:
    """
    Identify hard counter matchups (high winrate with sufficient matches).

    Args:
        matrix_data: The matchup matrix data
        min_matches: Minimum matches required
        winrate_threshold: Minimum winrate to be considered a hard counter

    Returns:
        List of hard counter matchups
    """
    hard_counters = []
    matrix = matrix_data['matrix']

    for bey_a, opponents in matrix.items():
        for bey_b, stats in opponents.items():
            if (stats['matches'] >= min_matches and
                stats['winrate'] is not None and
                    stats['winrate'] >= winrate_threshold):

                hard_counters.append({
                    'counter': bey_a,
                    'counters': bey_b,
                    'winrate': stats['winrate'],
                    'matches': stats['matches'],
                    'avg_diff': stats['avg_diff']
                })

    # Sort by winrate descending, then by number of matches
    hard_counters.sort(key=lambda x: (-x['winrate'], -x['matches']))

    return hard_counters


def main():
    """Main function to generate matchup matrix data."""
    print("Loading match data...")
    matches = load_matches()
    print(f"Loaded {len(matches)} matches")

    print("Loading bey metadata...")
    elo_map, tier_map, archetype_map = load_bey_metadata()

    print("Calculating matchup matrix...")
    matchup_data = calculate_matchup_matrix(matches)

    print("Building output structure...")
    matrix_output = build_matrix_output(matchup_data, elo_map, tier_map, archetype_map)

    print("Identifying hard counters...")
    hard_counters = identify_hard_counters(matrix_output, min_matches=5, winrate_threshold=0.7)
    matrix_output['hard_counters'] = hard_counters

    print(f"Saving matchup matrix to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(matrix_output, f, indent=2, ensure_ascii=False)

    print("Matchup matrix generated successfully!")
    print(f"  - {len(matrix_output['beys'])} beys in matrix")
    print(f"  - {len(hard_counters)} hard counter matchups identified")


if __name__ == "__main__":
    main()
