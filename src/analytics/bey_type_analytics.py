# bey_type_analytics.py
"""
Native Bey Type Effectiveness Dashboard Analytics Module

This module aggregates Beyblade-level statistics to the native type level,
providing quantitative insights into type performance and interactions.

Core Metrics (per type):
- Average ELO: Mean ELO rating of all Beys in the type
- Average winrate: Overall win percentage
- Upset rate: Percentage of wins against higher-ELO opponents
- Average dominance: Mean point differential

Type vs Type Metrics:
- Winrate matrix: Head-to-head performance between types
- Match volume: Number of matches between type pairs

Meta Insights:
- Dominant type: Highest overall performance
- Reliable type: Consistent but potentially capped
- Volatile type: High upset rate, creates unpredictability

Output:
- bey_type_analytics.json: Complete type effectiveness data
"""

import csv
import json
import os
import statistics
from collections import defaultdict

import sys
import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root
from src.config.paths import (  # noqa: E402
    BEYS_DATA_JSON as _BEYS_DATA_JSON,
    ADVANCED_LEADERBOARD_CSV as _ADVANCED_LEADERBOARD_CSV,
    MATCHES_CSV as _MATCHES_CSV,
    ELO_HISTORY_CSV as _ELO_HISTORY_CSV,
    BEY_TYPE_ANALYTICS_JSON as _BEY_TYPE_ANALYTICS_JSON,
)

# Initialize Windows terminal for ANSI color support (no-op on Unix systems)
os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"

# File paths
BEYS_DATA_JSON = _BEYS_DATA_JSON
ADVANCED_LEADERBOARD_CSV = _ADVANCED_LEADERBOARD_CSV
MATCHES_CSV = _MATCHES_CSV
ELO_HISTORY_CSV = _ELO_HISTORY_CSV
BEY_TYPE_ANALYTICS_JSON = _BEY_TYPE_ANALYTICS_JSON

# Minimum matches threshold for type analysis
MIN_MATCHES_FOR_TYPE = 3

BEY_TYPE_DEFINITIONS = {
    "attack": {
        "name": "Attack",
        "icon": "⚔️",
        "color": "#ef4444",
    },
    "defense": {
        "name": "Defense",
        "icon": "🛡️",
        "color": "#3b82f6",
    },
    "stamina": {
        "name": "Stamina",
        "icon": "💪",
        "color": "#10b981",
    },
    "balance": {
        "name": "Balance",
        "icon": "⚖️",
        "color": "#8b5cf6",
    },
}

TYPE_ALIASES = {
    "defence": "defense",
}


def normalize_bey_type(raw_type: str | None) -> str | None:
    """Normalize a raw type string to a known type id."""
    if not raw_type:
        return None
    normalized = raw_type.strip().lower()
    normalized = TYPE_ALIASES.get(normalized, normalized)
    return normalized if normalized in BEY_TYPE_DEFINITIONS else None


def load_bey_types(beys_data_path: str = BEYS_DATA_JSON) -> dict[str, str]:
    """
    Load native bey types from beys_data.json.

    Returns:
        Dictionary mapping blade name → normalized type id.
    """
    try:
        with open(beys_data_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"{YELLOW}Warning: {beys_data_path} not found or invalid.{RESET}")
        return {}

    bey_types: dict[str, str] = {}
    for entry in data:
        blade = entry.get("blade")
        type_value = normalize_bey_type(entry.get("type"))
        if blade and type_value:
            bey_types[blade] = type_value
    return bey_types


def load_leaderboard():
    """Load advanced leaderboard data."""
    leaderboard = {}
    try:
        with open(ADVANCED_LEADERBOARD_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bey = row['Bey']
                leaderboard[bey] = {
                    'elo': int(row['ELO']),
                    'wins': int(row['Wins']),
                    'losses': int(row['Losses']),
                    'matches': int(row['Matches']),
                    'winrate': float(row['Winrate'].rstrip('%')) / 100,
                    'avg_point_diff': float(row.get('AvgPointDiff', 0)),
                }
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {ADVANCED_LEADERBOARD_CSV} not found.{RESET}")
    return leaderboard


def load_matches():
    """Load match data for upset and matchup analysis."""
    matches = []
    try:
        with open(MATCHES_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                score_a = int(row['ScoreA'])
                score_b = int(row['ScoreB'])
                if score_a > score_b:
                    winner = row['BeyA']
                    loser = row['BeyB']
                    winner_score = score_a
                    loser_score = score_b
                else:
                    winner = row['BeyB']
                    loser = row['BeyA']
                    winner_score = score_b
                    loser_score = score_a
                matches.append({
                    'match_id': row['MatchID'],
                    'winner': winner,
                    'loser': loser,
                    'winner_score': winner_score,
                    'loser_score': loser_score,
                })
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {MATCHES_CSV} not found.{RESET}")
    return matches


def load_elo_history():
    """Load ELO history for determining upset analysis."""
    elo_by_match = {}
    try:
        with open(ELO_HISTORY_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row['MatchID']
                bey_a = row['BeyA']
                bey_b = row['BeyB']
                pre_a = float(row['PreA'])
                pre_b = float(row['PreB'])
                elo_by_match[match_id] = {
                    bey_a: pre_a,
                    bey_b: pre_b
                }
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {ELO_HISTORY_CSV} not found.{RESET}")
    return elo_by_match


def calculate_type_stats(bey_types, leaderboard, matches, elo_history):
    """
    Calculate comprehensive statistics for each native bey type.

    Returns:
        dict: Type statistics including avg ELO, winrate, upset rate, etc.
    """
    # Map each Bey to its native type
    bey_to_type = {
        bey: type_id for bey, type_id in bey_types.items()
        if type_id in BEY_TYPE_DEFINITIONS
    }

    # Group Beys by type
    type_beys = defaultdict(list)
    for bey, type_id in bey_to_type.items():
        type_beys[type_id].append(bey)

    # Calculate stats for each type
    type_stats = {}

    for type_id, beys in type_beys.items():
        # Filter to only Beys with sufficient matches
        valid_beys = [
            bey for bey in beys
            if bey in leaderboard and leaderboard[bey]['matches'] >= MIN_MATCHES_FOR_TYPE
        ]

        if not valid_beys:
            continue

        # Aggregate ELO
        elos = [leaderboard[bey]['elo'] for bey in valid_beys]
        avg_elo = statistics.mean(elos)
        elo_std = statistics.stdev(elos) if len(elos) > 1 else 0

        # Aggregate winrate
        total_wins = sum(leaderboard[bey]['wins'] for bey in valid_beys)
        total_matches = sum(leaderboard[bey]['matches'] for bey in valid_beys)
        avg_winrate = total_wins / total_matches if total_matches > 0 else 0

        # Aggregate dominance (point differential)
        dominances = [leaderboard[bey]['avg_point_diff'] for bey in valid_beys]
        avg_dominance = statistics.mean(dominances)

        # Calculate upset rate
        upset_count = 0
        type_win_count = 0

        for match in matches:
            winner = match['winner']
            loser = match['loser']

            if winner not in valid_beys:
                continue

            type_win_count += 1

            # Check if this was an upset (winner had lower ELO before match)
            match_id = match['match_id']
            if match_id in elo_history:
                winner_elo = elo_history[match_id].get(winner, 0)
                loser_elo = elo_history[match_id].get(loser, 0)
                if winner_elo > 0 and loser_elo > 0 and winner_elo < loser_elo:
                    upset_count += 1

        upset_rate = upset_count / type_win_count if type_win_count > 0 else 0

        type_data = BEY_TYPE_DEFINITIONS.get(type_id, {})

        type_stats[type_id] = {
            'id': type_id,
            'name': type_data.get('name', type_id.title()),
            'icon': type_data.get('icon', ''),
            'color': type_data.get('color', '#6b7280'),
            'bey_count': len(valid_beys),
            'beys': valid_beys,
            'avg_elo': round(avg_elo, 2),
            'elo_std': round(elo_std, 2),
            'avg_winrate': round(avg_winrate, 4),
            'avg_dominance': round(avg_dominance, 2),
            'upset_rate': round(upset_rate, 4),
            'total_matches': total_matches,
        }

    return type_stats


def calculate_matchup_matrix(bey_types, matches):
    """
    Calculate type vs type matchup statistics.

    Returns:
        dict: Matchup matrix with winrates and match counts
    """
    # Map each Bey to its type
    bey_to_type = {
        bey: type_id for bey, type_id in bey_types.items()
        if type_id in BEY_TYPE_DEFINITIONS
    }

    # Count matchups
    matchup_wins = defaultdict(lambda: defaultdict(int))
    matchup_total = defaultdict(lambda: defaultdict(int))

    for match in matches:
        winner = match['winner']
        loser = match['loser']

        winner_type = bey_to_type.get(winner)
        loser_type = bey_to_type.get(loser)

        if not winner_type or not loser_type:
            continue

        matchup_wins[winner_type][loser_type] += 1
        matchup_total[winner_type][loser_type] += 1
        matchup_total[loser_type][winner_type] += 1

    matchup_matrix = {}
    for type_a in matchup_total:
        matchup_matrix[type_a] = {}
        for type_b in matchup_total[type_a]:
            total = matchup_total[type_a][type_b]
            wins = matchup_wins[type_a][type_b]
            winrate = wins / total if total > 0 else 0
            matchup_matrix[type_a][type_b] = {
                'winrate': round(winrate, 4),
                'wins': wins,
                'losses': total - wins,
                'total': total,
            }

    return matchup_matrix


def generate_meta_insights(type_stats, matchup_matrix):
    """
    Generate high-level meta insights from type data.

    Returns:
        dict: Meta insights including dominant, reliable, and volatile types
    """
    if not type_stats:
        return {}

    dominant = max(type_stats.values(), key=lambda x: x['avg_elo'])

    reliability_scores = {
        type_id: data['avg_winrate'] - data['upset_rate']
        for type_id, data in type_stats.items()
    }
    most_reliable_id = max(reliability_scores, key=reliability_scores.get)
    most_reliable = type_stats[most_reliable_id]

    most_volatile = max(type_stats.values(), key=lambda x: x['upset_rate'])

    highest_winrate = max(type_stats.values(), key=lambda x: x['avg_winrate'])

    most_active = max(type_stats.values(), key=lambda x: x['total_matches'])

    insights = {
        'dominant_type': {
            'id': dominant['id'],
            'name': dominant['name'],
            'avg_elo': dominant['avg_elo'],
            'reason': 'Highest average ELO rating',
        },
        'most_reliable': {
            'id': most_reliable['id'],
            'name': most_reliable['name'],
            'avg_winrate': most_reliable['avg_winrate'],
            'upset_rate': most_reliable['upset_rate'],
            'reason': 'High winrate with low upset rate',
        },
        'most_volatile': {
            'id': most_volatile['id'],
            'name': most_volatile['name'],
            'upset_rate': most_volatile['upset_rate'],
            'reason': 'Highest upset rate',
        },
        'highest_winrate': {
            'id': highest_winrate['id'],
            'name': highest_winrate['name'],
            'avg_winrate': highest_winrate['avg_winrate'],
            'reason': 'Best overall win percentage',
        },
        'most_active': {
            'id': most_active['id'],
            'name': most_active['name'],
            'total_matches': most_active['total_matches'],
            'reason': 'Most matches played',
        },
    }

    return insights


def main():
    """Main execution function."""
    print(f"\n{BOLD}{CYAN}========================================{RESET}")
    print(f"{BOLD}{CYAN}  Native Bey Type Effectiveness Analyzer{RESET}")
    print(f"{BOLD}{CYAN}========================================{RESET}\n")

    print(f"{CYAN}Loading data...{RESET}")
    bey_types = load_bey_types()
    leaderboard = load_leaderboard()
    matches = load_matches()
    elo_history = load_elo_history()

    if not bey_types:
        print(f"{YELLOW}No bey type data available. Exiting.{RESET}")
        return

    print(f"{CYAN}Calculating type statistics...{RESET}")
    type_stats = calculate_type_stats(bey_types, leaderboard, matches, elo_history)

    print(f"{CYAN}Calculating matchup matrix...{RESET}")
    matchup_matrix = calculate_matchup_matrix(bey_types, matches)

    print(f"{CYAN}Generating meta insights...{RESET}")
    meta_insights = generate_meta_insights(type_stats, matchup_matrix)

    output = {
        'type_stats': type_stats,
        'matchup_matrix': matchup_matrix,
        'meta_insights': meta_insights,
        'summary': {
            'total_types': len(type_stats),
            'total_beys_classified': sum(data['bey_count'] for data in type_stats.values()),
            'total_matches_analyzed': len(matches),
        }
    }

    print(f"{CYAN}Writing to {BEY_TYPE_ANALYTICS_JSON}...{RESET}")
    with open(BEY_TYPE_ANALYTICS_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{GREEN}Bey type analytics generated successfully!{RESET}")
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Total Types: {output['summary']['total_types']}")
    print(f"  Total Beys Classified: {output['summary']['total_beys_classified']}")
    print(f"  Total Matches Analyzed: {output['summary']['total_matches_analyzed']}")

    if meta_insights:
        print(f"\n{BOLD}Meta Insights:{RESET}")
        print(
            f"  Dominant: {meta_insights['dominant_type']['name']} "
            f"(ELO: {meta_insights['dominant_type']['avg_elo']:.1f})"
        )
        print(
            f"  Most Reliable: {meta_insights['most_reliable']['name']} "
            f"(WR: {meta_insights['most_reliable']['avg_winrate']:.2%})"
        )
        print(
            f"  Most Volatile: {meta_insights['most_volatile']['name']} "
            f"(Upset Rate: {meta_insights['most_volatile']['upset_rate']:.2%})"
        )

    print()


if __name__ == "__main__":
    main()
