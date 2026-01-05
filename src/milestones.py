#!/usr/bin/env python3
"""
Milestones Module for Beyblade ELO Rating System

This module calculates statistical milestones and records across all Beyblades,
including win streaks, finish specialists, ELO extremes, upsets, and consistency metrics.

All milestones are automatically derived from existing match, round, and ELO history data.

Output Files:
- milestones.json: Complete milestone records organized by category

Categories:
1. Match & Win Records - Streaks, total wins, win rates
2. Finish Specialists - Finish type counts and diversity
3. ELO & Performance Extremes - Peak ELO, continuous upclimb/downfall
4. Upsets & Clutch Performance - Giant killers, biggest upsets
5. Consistency & Longevity - Total matches, tournaments, stability
"""

import csv
import json
import os
import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple

# Initialize Windows terminal for ANSI color support (no-op on Unix systems)
if os.name == 'nt':
    os.system("")

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# File paths
MATCHES_FILE = "./docs/data/matches.csv"
ROUNDS_FILE = "./docs/data/rounds.csv"
ELO_HISTORY_FILE = "./docs/data/elo_history.csv"
ELO_TIMESERIES_FILE = "./docs/data/elo_timeseries.csv"
TOURNAMENTS_FILE = "./docs/data/tournaments.json"
MILESTONES_FILE = "./docs/data/milestones.json"

# Configuration
MIN_MATCHES_FOR_WINRATE = 20  # Minimum matches to qualify for win rate records


def load_csv_to_dict(filepath: str) -> List[Dict[str, str]]:
    """Load CSV file and return as list of dictionaries."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def calculate_streaks(matches: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate longest win and losing streaks for each Bey.

    Returns dict with:
    - longest_win_streak: {bey: streak_length}
    - longest_losing_streak: {bey: streak_length}
    """
    current_win_streak = defaultdict(int)
    current_lose_streak = defaultdict(int)
    max_win_streak = defaultdict(int)
    max_lose_streak = defaultdict(int)

    for match in matches:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])

        winner = bey_a if score_a > score_b else bey_b
        loser = bey_b if winner == bey_a else bey_a

        # Update winner's streak
        current_win_streak[winner] += 1
        current_lose_streak[winner] = 0
        max_win_streak[winner] = max(max_win_streak[winner], current_win_streak[winner])

        # Update loser's streak
        current_lose_streak[loser] += 1
        current_win_streak[loser] = 0
        max_lose_streak[loser] = max(max_lose_streak[loser], current_lose_streak[loser])

    return {
        'longest_win_streak': dict(max_win_streak),
        'longest_losing_streak': dict(max_lose_streak)
    }


def calculate_total_wins(matches: List[Dict[str, str]]) -> Dict[str, int]:
    """Calculate total wins for each Bey."""
    wins = defaultdict(int)

    for match in matches:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])

        winner = bey_a if score_a > score_b else bey_b
        wins[winner] += 1

    return dict(wins)


def calculate_win_rates(matches: List[Dict[str, str]]) -> Dict[str, Tuple[float, int]]:
    """
    Calculate win rates for Beys with minimum match threshold.

    Returns dict of {bey: (win_rate, total_matches)}
    """
    wins = defaultdict(int)
    total_matches = defaultdict(int)

    for match in matches:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])

        total_matches[bey_a] += 1
        total_matches[bey_b] += 1

        winner = bey_a if score_a > score_b else bey_b
        wins[winner] += 1

    # Calculate win rates for Beys meeting minimum match threshold
    win_rates = {}
    for bey, matches_played in total_matches.items():
        if matches_played >= MIN_MATCHES_FOR_WINRATE:
            win_rate = (wins[bey] / matches_played) * 100
            win_rates[bey] = (win_rate, matches_played)

    return win_rates


def calculate_finish_stats(rounds: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate finish type statistics for each Bey.

    Returns dict with:
    - spin_finishes: {bey: count}
    - burst_finishes: {bey: count}
    - pocket_finishes: {bey: count}
    - extreme_finishes: {bey: count}
    - finish_diversity: {bey: evenness_score} where 100 is perfect distribution
    """
    finish_counts = {
        'spin': defaultdict(int),
        'burst': defaultdict(int),
        'pocket': defaultdict(int),
        'extreme': defaultdict(int)
    }

    # Track all finish types per Bey
    bey_finish_counts = defaultdict(lambda: {'spin': 0, 'burst': 0, 'pocket': 0, 'extreme': 0})

    for round_data in rounds:
        winner = round_data['winner']
        finish_type = round_data['finish_type'].lower()

        if finish_type in finish_counts:
            finish_counts[finish_type][winner] += 1
            bey_finish_counts[winner][finish_type] += 1

    # Calculate finish diversity score (evenness of distribution)
    # Perfect distribution = 25% each = score of 100
    # Use coefficient of variation inverted and scaled to 0-100
    finish_diversity_scores = {}
    for bey, counts in bey_finish_counts.items():
        total_wins = sum(counts.values())
        if total_wins == 0:
            continue
        # Calculate percentages for each finish type
        percentages = [counts[ft] / total_wins * 100 for ft in ['spin', 'burst', 'pocket', 'extreme']]

        # Calculate deviation from perfect distribution (25% each)
        # Sum of squared differences from 25%
        deviations = sum((pct - 25) ** 2 for pct in percentages)

        # Max deviation would be 100% in one category: (100-25)^2 + 3*(0-25)^2 = 5625 + 1875 = 7500
        # Perfect distribution: 0 deviation
        # Score: 100 - (deviation / max_deviation * 100)
        max_deviation = 7500
        evenness_score = 100 - (deviations / max_deviation * 100)

        finish_diversity_scores[bey] = round(evenness_score, 1)

    return {
        'spin_finishes': dict(finish_counts['spin']),
        'burst_finishes': dict(finish_counts['burst']),
        'pocket_finishes': dict(finish_counts['pocket']),
        'extreme_finishes': dict(finish_counts['extreme']),
        'finish_diversity': finish_diversity_scores
    }


def calculate_elo_extremes(elo_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate ELO extremes for each Bey.

    Returns dict with:
    - highest_elo_ever: {bey: elo_value}
    - biggest_upclimb: {bey: (delta, from_elo, to_elo)}
    - biggest_downfall: {bey: (delta, from_elo, to_elo)}
    """
    highest_elo = defaultdict(lambda: 0)
    bey_elo_history = defaultdict(list)

    # Build ELO history per Bey
    for match in elo_history:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        post_a = float(match['PostA'])
        post_b = float(match['PostB'])

        bey_elo_history[bey_a].append(post_a)
        bey_elo_history[bey_b].append(post_b)

        highest_elo[bey_a] = max(highest_elo[bey_a], post_a)
        highest_elo[bey_b] = max(highest_elo[bey_b], post_b)

    # Calculate biggest continuous upclimb and downfall
    biggest_upclimb = {}
    biggest_downfall = {}

    for bey, elo_values in bey_elo_history.items():
        if len(elo_values) < 2:
            continue

        # Find largest continuous upclimb (lowest point to highest point after it)
        max_climb = 0
        climb_from = elo_values[0]
        climb_to = elo_values[0]
        min_elo = elo_values[0]

        for i, elo in enumerate(elo_values):
            if elo < min_elo:
                min_elo = elo

            climb = elo - min_elo
            if climb > max_climb:
                max_climb = climb
                climb_from = min_elo
                climb_to = elo

        if max_climb > 0:
            biggest_upclimb[bey] = (max_climb, climb_from, climb_to)

        # Find largest continuous downfall (highest point to lowest point after it)
        max_fall = 0
        fall_from = elo_values[0]
        fall_to = elo_values[0]
        max_elo = elo_values[0]

        for i, elo in enumerate(elo_values):
            if elo > max_elo:
                max_elo = elo

            fall = max_elo - elo
            if fall > max_fall:
                max_fall = fall
                fall_from = max_elo
                fall_to = elo

        if max_fall > 0:
            biggest_downfall[bey] = (max_fall, fall_from, fall_to)

    return {
        'highest_elo_ever': dict(highest_elo),
        'biggest_upclimb': biggest_upclimb,
        'biggest_downfall': biggest_downfall
    }


def calculate_upset_stats(elo_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate upset-related statistics.

    Returns dict with:
    - best_upsetter: {bey: upset_win_count}
    - biggest_single_upset: {bey: (elo_diff, opponent, match_id)}
    """
    upset_wins = defaultdict(int)
    biggest_upset = {}

    for match in elo_history:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])
        pre_a = float(match['PreA'])
        pre_b = float(match['PreB'])
        match_id = match['MatchID']

        winner = bey_a if score_a > score_b else bey_b
        loser = bey_b if winner == bey_a else bey_a
        winner_pre_elo = pre_a if winner == bey_a else pre_b
        loser_pre_elo = pre_b if winner == bey_a else pre_a

        # Check if this was an upset (lower ELO won)
        if winner_pre_elo < loser_pre_elo:
            elo_diff = loser_pre_elo - winner_pre_elo
            upset_wins[winner] += 1

            # Track biggest single upset (with opponent)
            if winner not in biggest_upset or elo_diff > biggest_upset[winner][0]:
                biggest_upset[winner] = (elo_diff, loser, match_id)

    return {
        'best_upsetter': dict(upset_wins),
        'biggest_single_upset': biggest_upset
    }


def calculate_top_rank_time(elo_timeseries: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate time spent in top 5 and top 10 rankings.

    Returns dict with:
    - time_in_top_5: {bey: match_count}
    - time_in_top_10: {bey: match_count}
    """
    # Group by match number to get rankings at each point
    matches_data = defaultdict(list)

    for row in elo_timeseries:
        bey = row['Bey']
        match_num = int(row['MatchIndex'])
        elo = float(row['ELO'])
        matches_data[match_num].append((bey, elo))

    top_5_time = defaultdict(int)
    top_10_time = defaultdict(int)

    # For each match, rank Beys and count time in top positions
    for match_num, bey_elos in matches_data.items():
        sorted_beys = sorted(bey_elos, key=lambda x: x[1], reverse=True)

        for rank, (bey, elo) in enumerate(sorted_beys, start=1):
            if rank <= 5:
                top_5_time[bey] += 1
            if rank <= 10:
                top_10_time[bey] += 1

    return {
        'time_in_top_5': dict(top_5_time),
        'time_in_top_10': dict(top_10_time)
    }


def calculate_longevity_stats(matches: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calculate longevity statistics.

    Returns dict with:
    - most_matches_played: {bey: count}
    """
    matches_played = defaultdict(int)

    for match in matches:
        bey_a = match['BeyA']
        bey_b = match['BeyB']

        matches_played[bey_a] += 1
        matches_played[bey_b] += 1

    return {
        'most_matches_played': dict(matches_played)
    }


def calculate_stability(elo_history: List[Dict[str, str]]) -> Dict[str, float]:
    """
    Calculate ELO stability (inverse of variance) for each Bey.

    Returns dict of {bey: variance}
    """
    bey_elos = defaultdict(list)

    for match in elo_history:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        post_a = float(match['PostA'])
        post_b = float(match['PostB'])

        bey_elos[bey_a].append(post_a)
        bey_elos[bey_b].append(post_b)

    stability = {}
    for bey, elos in bey_elos.items():
        if len(elos) >= 2:
            # Calculate variance
            mean_elo = sum(elos) / len(elos)
            variance = sum((elo - mean_elo) ** 2 for elo in elos) / len(elos)
            stability[bey] = variance

    return stability


def format_milestone_entry(bey: str, value: Any, category: str) -> Dict[str, Any]:
    """Format a milestone entry with consistent structure."""
    entry = {
        'bey': bey,
        'value': value
    }

    # Add formatted display text based on category
    if isinstance(value, tuple):
        if len(value) == 2:
            entry['display'] = f"{value[0]:.1f}"
        elif len(value) == 3:
            entry['display'] = f"{value[0]:.1f} ELO"
    elif isinstance(value, float):
        if 'rate' in category.lower() or 'win' in category.lower():
            entry['display'] = f"{value:.1f}%"
        else:
            entry['display'] = f"{value:.1f}"
    else:
        entry['display'] = str(value)

    return entry


def get_top_n_milestones(data: Dict[str, Any], n: int = 5) -> List[Dict[str, Any]]:
    """Get top N entries from a milestone category."""
    if not data:
        return []

    # Sort by value (handle tuples by using first element)
    def get_sort_key(item):
        value = item[1]
        if isinstance(value, tuple):
            return value[0]
        return value

    sorted_items = sorted(data.items(), key=get_sort_key, reverse=True)

    results = []
    for bey, value in sorted_items[:n]:
        results.append({
            'bey': bey,
            'value': value
        })

    return results


def get_bottom_n_milestones(data: Dict[str, Any], n: int = 5) -> List[Dict[str, Any]]:
    """Get bottom N entries from a milestone category (for stability - lowest variance is best)."""
    if not data:
        return []

    sorted_items = sorted(data.items(), key=lambda x: x[1])

    results = []
    for bey, value in sorted_items[:n]:
        results.append({
            'bey': bey,
            'value': value
        })

    return results


def calculate_giant_killer_from_top_ranks(elo_history: List[Dict[str, str]],
                                          elo_timeseries: List[Dict[str, str]],
                                          top_n: int = 10) -> Dict[str, int]:
    """
    Calculate Giant Killer metric: wins against Top-N Beys.

    This requires determining who was in top N at the time of each match,
    using pre-match ELO values.
    """
    # Build a dict to track current ELO for each Bey as we go through matches
    current_elo = defaultdict(lambda: 1000.0)  # Default starting ELO

    # Count wins against top N opponents
    giant_killer_wins = defaultdict(int)

    for match in elo_history:
        bey_a = match['BeyA']
        bey_b = match['BeyB']
        score_a = int(match['ScoreA'])
        score_b = int(match['ScoreB'])
        pre_a = float(match['PreA'])
        pre_b = float(match['PreB'])
        post_a = float(match['PostA'])
        post_b = float(match['PostB'])

        # Update current ELO values for both Beys (in case they haven't been seen yet)
        current_elo[bey_a] = pre_a
        current_elo[bey_b] = pre_b

        # Get top N Beys based on current ELO (pre-match)
        sorted_beys = sorted(current_elo.items(), key=lambda x: x[1], reverse=True)
        top_n_beys = {bey for bey, _ in sorted_beys[:top_n]}

        # Determine winner and loser
        winner = bey_a if score_a > score_b else bey_b
        loser = bey_b if winner == bey_a else bey_a

        # Check if winner beat a top N opponent
        if loser in top_n_beys:
            giant_killer_wins[winner] += 1

        # Update current ELO values with post-match values
        current_elo[bey_a] = post_a
        current_elo[bey_b] = post_b

    return dict(giant_killer_wins)


def compute_milestones():
    """Main function to compute all milestones and save to JSON."""
    print(f"{CYAN}=== Beyblade Milestones Calculation ==={RESET}")

    # Load data files
    print(f"{YELLOW}→{RESET} Loading data files...")
    matches = load_csv_to_dict(MATCHES_FILE)
    rounds = load_csv_to_dict(ROUNDS_FILE)
    elo_history = load_csv_to_dict(ELO_HISTORY_FILE)
    elo_timeseries = load_csv_to_dict(ELO_TIMESERIES_FILE)

    print(f"{YELLOW}→{RESET} Calculating Match & Win Records...")
    streaks = calculate_streaks(matches)
    total_wins = calculate_total_wins(matches)
    win_rates = calculate_win_rates(matches)

    print(f"{YELLOW}→{RESET} Calculating Finish Statistics...")
    finish_stats = calculate_finish_stats(rounds)

    print(f"{YELLOW}→{RESET} Calculating ELO Extremes...")
    elo_extremes = calculate_elo_extremes(elo_history)

    print(f"{YELLOW}→{RESET} Calculating Upset Statistics...")
    upset_stats = calculate_upset_stats(elo_history)

    print(f"{YELLOW}→{RESET} Calculating Giant Killer Stats...")
    giant_killer_top5 = calculate_giant_killer_from_top_ranks(elo_history, elo_timeseries, top_n=5)
    giant_killer_top10 = calculate_giant_killer_from_top_ranks(elo_history, elo_timeseries, top_n=10)

    print(f"{YELLOW}→{RESET} Calculating Top Rank Time...")
    top_rank_time = calculate_top_rank_time(elo_timeseries)

    print(f"{YELLOW}→{RESET} Calculating Longevity Statistics...")
    longevity = calculate_longevity_stats(matches)

    print(f"{YELLOW}→{RESET} Calculating Stability...")
    stability = calculate_stability(elo_history)

    # Compile all milestones
    milestones = {
        'match_and_win_records': {
            'longest_win_streak': get_top_n_milestones(streaks['longest_win_streak']),
            'longest_losing_streak': get_top_n_milestones(streaks['longest_losing_streak']),
            'most_total_wins': get_top_n_milestones(total_wins),
            'highest_win_rate': [
                {
                    'bey': bey,
                    'value': win_rate,
                    'matches': matches_count
                }
                for bey, (win_rate, matches_count) in sorted(
                    win_rates.items(), key=lambda x: x[1][0], reverse=True
                )[:5]
            ]
        },
        'finish_specialists': {
            'most_spin_finishes': get_top_n_milestones(finish_stats['spin_finishes']),
            'most_burst_finishes': get_top_n_milestones(finish_stats['burst_finishes']),
            'most_pocket_finishes': get_top_n_milestones(finish_stats['pocket_finishes']),
            'most_extreme_finishes': get_top_n_milestones(finish_stats['extreme_finishes']),
            'highest_finish_diversity': get_top_n_milestones(finish_stats['finish_diversity'])
        },
        'elo_performance_extremes': {
            'highest_elo_ever': get_top_n_milestones(elo_extremes['highest_elo_ever']),
            'biggest_elo_upclimb': [
                {
                    'bey': bey,
                    'climb': climb,
                    'from_elo': from_elo,
                    'to_elo': to_elo
                }
                for bey, (climb, from_elo, to_elo) in sorted(
                    elo_extremes['biggest_upclimb'].items(), key=lambda x: x[1][0], reverse=True
                )[:5]
            ],
            'biggest_elo_downfall': [
                {
                    'bey': bey,
                    'fall': fall,
                    'from_elo': from_elo,
                    'to_elo': to_elo
                }
                for bey, (fall, from_elo, to_elo) in sorted(
                    elo_extremes['biggest_downfall'].items(), key=lambda x: x[1][0], reverse=True
                )[:5]
            ]
        },
        'upsets_and_clutch': {
            'best_upsetter': get_top_n_milestones(upset_stats['best_upsetter']),
            'biggest_single_upset': [
                {
                    'bey': bey,
                    'elo_diff': elo_diff,
                    'opponent': opponent,
                    'match_id': match_id
                }
                for bey, (elo_diff, opponent, match_id) in sorted(
                    upset_stats['biggest_single_upset'].items(), key=lambda x: x[1][0], reverse=True
                )[:5]
            ],
            'giant_killer_top5': get_top_n_milestones(giant_killer_top5),
            'giant_killer_top10': get_top_n_milestones(giant_killer_top10)
        },
        'consistency_and_longevity': {
            'most_matches_played': get_top_n_milestones(longevity['most_matches_played']),
            'most_time_in_top_5': get_top_n_milestones(top_rank_time['time_in_top_5']),
            'most_time_in_top_10': get_top_n_milestones(top_rank_time['time_in_top_10']),
            'most_stable_bey': get_bottom_n_milestones(stability)
        },
        'metadata': {
            'generated_at': datetime.datetime.now().isoformat(),
            'total_matches': len(matches),
            'total_rounds': len(rounds),
            'min_matches_for_winrate': MIN_MATCHES_FOR_WINRATE
        }
    }

    # Save to JSON
    print(f"{YELLOW}→{RESET} Writing milestones to {MILESTONES_FILE}...")
    with open(MILESTONES_FILE, 'w', encoding='utf-8') as f:
        json.dump(milestones, f, indent=2, ensure_ascii=False)

    print(f"{GREEN}✓{RESET} Milestones calculation complete!")
    print(f"{GREEN}✓{RESET} Output: {MILESTONES_FILE}")


if __name__ == '__main__':
    compute_milestones()
