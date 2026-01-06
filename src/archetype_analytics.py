# archetype_analytics.py
"""
Archetype Effectiveness Dashboard Analytics Module

This module aggregates Beyblade-level statistics to the archetype level,
providing quantitative insights into archetype performance and interactions.

Core Metrics (per archetype):
- Average ELO: Mean ELO rating of all Beys in the archetype
- Average winrate: Overall win percentage
- Upset rate: Percentage of wins against higher-ELO opponents
- Average dominance: Mean point differential

Archetype vs Archetype Metrics:
- Winrate matrix: Head-to-head performance between archetypes
- Match volume: Number of matches between archetype pairs

Meta Insights:
- Dominant archetype: Highest overall performance
- Reliable archetype: Consistent but potentially capped
- Volatile archetype: High upset rate, creates unpredictability

Output:
- archetype_analytics.json: Complete archetype effectiveness data
"""

import csv
import json
import os
import statistics
from collections import defaultdict

# Initialize Windows terminal for ANSI color support (no-op on Unix systems)
os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"

# File paths
RPG_STATS_JSON = "./docs/data/rpg_stats.json"
ADVANCED_LEADERBOARD_CSV = "./docs/data/advanced_leaderboard.csv"
MATCHES_CSV = "./docs/data/matches.csv"
ELO_HISTORY_CSV = "./docs/data/elo_history.csv"
ARCHETYPE_ANALYTICS_JSON = "./docs/data/archetype_analytics.json"

# Minimum matches threshold for archetype analysis
MIN_MATCHES_FOR_ARCHETYPE = 3


def load_rpg_stats():
    """Load RPG stats data including archetype assignments."""
    try:
        with open(RPG_STATS_JSON, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {RPG_STATS_JSON} not found. Run rpg_stats.py first.{RESET}")
        return {}


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


def calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history):
    """
    Calculate comprehensive statistics for each archetype.

    Returns:
        dict: Archetype statistics including avg ELO, winrate, upset rate, etc.
    """
    # Map each Bey to its archetype
    bey_to_archetype = {}
    for bey, data in rpg_stats.items():
        archetype_id = data.get('archetype', {}).get('id', 'unknown')
        if archetype_id != 'unknown':
            bey_to_archetype[bey] = archetype_id

    # Group Beys by archetype
    archetype_beys = defaultdict(list)
    for bey, archetype_id in bey_to_archetype.items():
        archetype_beys[archetype_id].append(bey)

    # Calculate stats for each archetype
    archetype_stats = {}

    for archetype_id, beys in archetype_beys.items():
        # Filter to only Beys with sufficient matches
        valid_beys = [
            bey for bey in beys
            if bey in leaderboard and leaderboard[bey]['matches'] >= MIN_MATCHES_FOR_ARCHETYPE
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
        archetype_match_count = 0

        for match in matches:
            winner = match['winner']
            loser = match['loser']

            if winner not in valid_beys:
                continue

            archetype_match_count += 1

            # Check if this was an upset (winner had lower ELO before match)
            match_id = match['match_id']
            if match_id in elo_history:
                winner_elo = elo_history[match_id].get(winner, 0)
                loser_elo = elo_history[match_id].get(loser, 0)
                if winner_elo > 0 and loser_elo > 0 and winner_elo < loser_elo:
                    upset_count += 1

        upset_rate = upset_count / archetype_match_count if archetype_match_count > 0 else 0

        # Get archetype metadata from first Bey
        archetype_data = rpg_stats[valid_beys[0]]['archetype']

        archetype_stats[archetype_id] = {
            'id': archetype_id,
            'name': archetype_data['name'],
            'category': archetype_data['category'],
            'icon': archetype_data['icon'],
            'color': archetype_data['color'],
            'bey_count': len(valid_beys),
            'beys': valid_beys,
            'avg_elo': round(avg_elo, 2),
            'elo_std': round(elo_std, 2),
            'avg_winrate': round(avg_winrate, 4),
            'avg_dominance': round(avg_dominance, 2),
            'upset_rate': round(upset_rate, 4),
            'total_matches': archetype_match_count,
        }

    return archetype_stats


def calculate_matchup_matrix(rpg_stats, matches, elo_history):
    """
    Calculate archetype vs archetype matchup statistics.

    Returns:
        dict: Matchup matrix with winrates and match counts
    """
    # Map each Bey to its archetype
    bey_to_archetype = {}
    for bey, data in rpg_stats.items():
        archetype_id = data.get('archetype', {}).get('id', 'unknown')
        if archetype_id != 'unknown':
            bey_to_archetype[bey] = archetype_id

    # Count matchups
    matchup_wins = defaultdict(lambda: defaultdict(int))
    matchup_total = defaultdict(lambda: defaultdict(int))

    for match in matches:
        winner = match['winner']
        loser = match['loser']

        winner_archetype = bey_to_archetype.get(winner)
        loser_archetype = bey_to_archetype.get(loser)

        if not winner_archetype or not loser_archetype:
            continue

        # Record win
        matchup_wins[winner_archetype][loser_archetype] += 1
        matchup_total[winner_archetype][loser_archetype] += 1
        matchup_total[loser_archetype][winner_archetype] += 1

    # Calculate winrates
    matchup_matrix = {}
    for archetype_a in matchup_total:
        matchup_matrix[archetype_a] = {}
        for archetype_b in matchup_total[archetype_a]:
            total = matchup_total[archetype_a][archetype_b]
            wins = matchup_wins[archetype_a][archetype_b]
            winrate = wins / total if total > 0 else 0
            matchup_matrix[archetype_a][archetype_b] = {
                'winrate': round(winrate, 4),
                'wins': wins,
                'losses': total - wins,
                'total': total,
            }

    return matchup_matrix


def generate_meta_insights(archetype_stats, matchup_matrix):
    """
    Generate high-level meta insights from archetype data.

    Returns:
        dict: Meta insights including dominant, reliable, and volatile archetypes
    """
    if not archetype_stats:
        return {}

    # Find dominant archetype (highest avg ELO)
    dominant = max(archetype_stats.values(), key=lambda x: x['avg_elo'])

    # Find most reliable archetype (high winrate, low upset rate)
    reliability_scores = {
        archetype_id: data['avg_winrate'] - data['upset_rate']
        for archetype_id, data in archetype_stats.items()
    }
    most_reliable_id = max(reliability_scores, key=reliability_scores.get)
    most_reliable = archetype_stats[most_reliable_id]

    # Find most volatile archetype (highest upset rate)
    most_volatile = max(archetype_stats.values(), key=lambda x: x['upset_rate'])

    # Find archetype with highest winrate
    highest_winrate = max(archetype_stats.values(), key=lambda x: x['avg_winrate'])

    # Find most active archetype (most matches)
    most_active = max(archetype_stats.values(), key=lambda x: x['total_matches'])

    insights = {
        'dominant_archetype': {
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
    print(f"{BOLD}{CYAN}  Archetype Effectiveness Analyzer{RESET}")
    print(f"{BOLD}{CYAN}========================================{RESET}\n")

    # Load data
    print(f"{CYAN}Loading data...{RESET}")
    rpg_stats = load_rpg_stats()
    leaderboard = load_leaderboard()
    matches = load_matches()
    elo_history = load_elo_history()

    if not rpg_stats:
        print(f"{YELLOW}No RPG stats data available. Exiting.{RESET}")
        return

    # Calculate statistics
    print(f"{CYAN}Calculating archetype statistics...{RESET}")
    archetype_stats = calculate_archetype_stats(rpg_stats, leaderboard, matches, elo_history)

    print(f"{CYAN}Calculating matchup matrix...{RESET}")
    matchup_matrix = calculate_matchup_matrix(rpg_stats, matches, elo_history)

    print(f"{CYAN}Generating meta insights...{RESET}")
    meta_insights = generate_meta_insights(archetype_stats, matchup_matrix)

    # Compile output
    output = {
        'archetype_stats': archetype_stats,
        'matchup_matrix': matchup_matrix,
        'meta_insights': meta_insights,
        'summary': {
            'total_archetypes': len(archetype_stats),
            'total_beys_classified': sum(data['bey_count'] for data in archetype_stats.values()),
            'total_matches_analyzed': sum(data['total_matches'] for data in archetype_stats.values()),
        }
    }

    # Save to JSON
    print(f"{CYAN}Writing to {ARCHETYPE_ANALYTICS_JSON}...{RESET}")
    with open(ARCHETYPE_ANALYTICS_JSON, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{GREEN}✓ Archetype analytics generated successfully!{RESET}")
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Total Archetypes: {output['summary']['total_archetypes']}")
    print(f"  Total Beys Classified: {output['summary']['total_beys_classified']}")
    print(f"  Total Matches Analyzed: {output['summary']['total_matches_analyzed']}")

    if meta_insights:
        print(f"\n{BOLD}Meta Insights:{RESET}")
        print(
            f"  Dominant: {meta_insights['dominant_archetype']['name']} "
            f"(ELO: {meta_insights['dominant_archetype']['avg_elo']:.1f})"
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
