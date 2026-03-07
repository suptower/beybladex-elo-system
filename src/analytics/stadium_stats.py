"""
Stadium Statistics Module

This module provides comprehensive stadium-specific analytics for the BeybladeX ELO system.
It analyzes how different arenas affect performance, archetypes, finishes, and the meta.

Features:
- Stadium overview statistics (matches, ELO behavior, dominance)
- Bey performance per stadium
- Archetype effectiveness per stadium
- Finish type distribution per stadium
- Comparative stadium analysis
- ELO behavior and volatility per stadium

Output:
- stadium_analytics.json: Complete stadium-specific statistics
"""

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import (
    MATCHES_CSV as _MATCHES_CSV,
    ROUNDS_CSV as _ROUNDS_CSV,
    ELO_HISTORY_CSV as _ELO_HISTORY_CSV,
    RPG_STATS_JSON as _RPG_STATS_JSON,
    STADIUM_ANALYTICS_JSON as _STADIUM_ANALYTICS_JSON,
)

# Colors for terminal output (ANSI escape codes work on most modern terminals)
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RED = "\033[31m"

# File paths
MATCHES_CSV = _MATCHES_CSV
ROUNDS_CSV = _ROUNDS_CSV
ELO_HISTORY_CSV = _ELO_HISTORY_CSV
RPG_STATS_JSON = _RPG_STATS_JSON
STADIUM_ANALYTICS_JSON = _STADIUM_ANALYTICS_JSON

# Stadium name normalization
STADIUM_ALIASES = {
    "Xtreme": "Xtreme Stadium",
    "Drop Attack": "Drop Attack Beystadium",
    "DropAttack": "Drop Attack Beystadium",
    "drop_attack": "Drop Attack Beystadium",
    "xtreme": "Xtreme Stadium"
}


def normalize_stadium_name(stadium):
    """Normalize stadium name to canonical form."""
    if not stadium:
        return "Xtreme Stadium"
    return STADIUM_ALIASES.get(stadium, stadium)


def load_matches():
    """Load all match data with arena information."""
    matches = []
    try:
        with open(MATCHES_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stadium = normalize_stadium_name(row.get('arena', 'Xtreme'))
                matches.append({
                    'match_id': row['MatchID'],
                    'date': row['Date'],
                    'bey_a': row['BeyA'],
                    'bey_b': row['BeyB'],
                    'score_a': int(row['ScoreA']),
                    'score_b': int(row['ScoreB']),
                    'match_type': row.get('MatchType', 'exhibition'),
                    'season_id': row.get('SeasonID', ''),
                    'tier': row.get('Tier', ''),
                    'stadium': stadium
                })
    except FileNotFoundError:
        print(f"{RED}Error: {MATCHES_CSV} not found{RESET}")
        return []
    return matches


def load_rounds():
    """Load round-level data with finish types."""
    rounds = []
    try:
        with open(ROUNDS_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rounds.append({
                    'match_id': row['match_id'],
                    'round_number': int(row['round_number']),
                    'winner': row['winner'],
                    'finish_type': row.get('finish_type', 'spin'),
                    'points_awarded': int(row['points_awarded'])
                })
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {ROUNDS_CSV} not found. Finish type stats will be unavailable.{RESET}")
        return []
    return rounds


def load_elo_history():
    """Load ELO history with arena information."""
    history = []
    try:
        with open(ELO_HISTORY_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Arena column is the last column in elo_history.csv
                stadium = normalize_stadium_name(row.get('arena', 'Xtreme'))
                history.append({
                    'match_id': row['MatchID'],
                    'date': row['Date'],
                    'bey_a': row['BeyA'],
                    'bey_b': row['BeyB'],
                    'score_a': int(row['ScoreA']),
                    'score_b': int(row['ScoreB']),
                    'old_elo_a': float(row['PreA']),
                    'old_elo_b': float(row['PreB']),
                    'new_elo_a': float(row['PostA']),
                    'new_elo_b': float(row['PostB']),
                    'stadium': stadium
                })
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {ELO_HISTORY_CSV} not found{RESET}")
        return []
    return history


def load_rpg_stats():
    """Load RPG stats for archetype information."""
    try:
        with open(RPG_STATS_JSON, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {RPG_STATS_JSON} not found. Archetype stats will be unavailable.{RESET}")
        return {}


def calculate_stadium_overview(matches, elo_history):
    """Calculate general statistics per stadium."""
    stadium_stats = defaultdict(lambda: {
        'total_matches': 0,
        'total_points': 0,
        'match_scores': [],
        'seasons': defaultdict(int),
        'tiers': defaultdict(int),
        'match_types': defaultdict(int)
    })

    for match in matches:
        stadium = match['stadium']
        stats = stadium_stats[stadium]

        stats['total_matches'] += 1
        total_score = match['score_a'] + match['score_b']
        stats['total_points'] += total_score
        stats['match_scores'].append(total_score)

        if match['season_id']:
            stats['seasons'][match['season_id']] += 1
        if match['tier']:
            stats['tiers'][match['tier']] += 1
        stats['match_types'][match['match_type']] += 1

    # Calculate derived statistics
    overview = {}
    for stadium, stats in stadium_stats.items():
        if stats['total_matches'] > 0:
            overview[stadium] = {
                'total_matches': stats['total_matches'],
                'average_match_score': round(stats['total_points'] / stats['total_matches'], 2),
                'match_score_distribution': {
                    'min': min(stats['match_scores']),
                    'max': max(stats['match_scores']),
                    'median': round(statistics.median(stats['match_scores']), 2),
                    'stdev': round(statistics.stdev(stats['match_scores']), 2) if len(stats['match_scores']) > 1 else 0
                },
                'matches_per_season': dict(stats['seasons']),
                'matches_per_tier': dict(stats['tiers']),
                'matches_per_type': dict(stats['match_types'])
            }

    return overview


def calculate_score_distribution_per_stadium(matches):
    """Calculate match score distribution per stadium.

    Each match is represented as winner_score-loser_score so that
    4-0 always means 'winner got 4, loser got 0' regardless of which
    side (A or B) won.
    """
    stadium_scores = defaultdict(Counter)
    stadium_totals = defaultdict(int)

    for match in matches:
        stadium = match['stadium']
        sa, sb = match['score_a'], match['score_b']
        winner_score = max(sa, sb)
        loser_score = min(sa, sb)
        score_key = f"{winner_score}-{loser_score}"
        stadium_scores[stadium][score_key] += 1
        stadium_totals[stadium] += 1

    result = {}
    for stadium, scores in stadium_scores.items():
        total = stadium_totals[stadium]
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: (-int(x[0].split('-')[0]), -int(x[0].split('-')[1]))
        )
        result[stadium] = {
            'scores': [
                {
                    'score': score,
                    'count': count,
                    'percentage': round(count / total * 100, 1)
                }
                for score, count in sorted_scores
            ],
            'total_matches': total
        }

    return result


def calculate_bey_performance_per_stadium(matches, elo_history):
    """Calculate Bey performance statistics per stadium."""
    bey_stats = defaultdict(lambda: defaultdict(lambda: {
        'matches': 0,
        'wins': 0,
        'losses': 0,
        'points_for': 0,
        'points_against': 0,
        'elo_changes': []
    }))

    # Process matches
    for match in matches:
        stadium = match['stadium']
        bey_a = match['bey_a']
        bey_b = match['bey_b']

        # Update stats for both beys
        bey_stats[stadium][bey_a]['matches'] += 1
        bey_stats[stadium][bey_b]['matches'] += 1

        bey_stats[stadium][bey_a]['points_for'] += match['score_a']
        bey_stats[stadium][bey_a]['points_against'] += match['score_b']
        bey_stats[stadium][bey_b]['points_for'] += match['score_b']
        bey_stats[stadium][bey_b]['points_against'] += match['score_a']

        if match['score_a'] > match['score_b']:
            bey_stats[stadium][bey_a]['wins'] += 1
            bey_stats[stadium][bey_b]['losses'] += 1
        else:
            bey_stats[stadium][bey_b]['wins'] += 1
            bey_stats[stadium][bey_a]['losses'] += 1

    # Process ELO changes
    for entry in elo_history:
        stadium = entry['stadium']
        bey_a = entry['bey_a']
        bey_b = entry['bey_b']

        elo_change_a = entry['new_elo_a'] - entry['old_elo_a']
        elo_change_b = entry['new_elo_b'] - entry['old_elo_b']

        bey_stats[stadium][bey_a]['elo_changes'].append(elo_change_a)
        bey_stats[stadium][bey_b]['elo_changes'].append(elo_change_b)

    # Calculate derived statistics
    performance = {}
    for stadium, beys in bey_stats.items():
        performance[stadium] = {}
        for bey, stats in beys.items():
            if stats['matches'] > 0:
                winrate = stats['wins'] / stats['matches']
                avg_elo_change = statistics.mean(stats['elo_changes']) if stats['elo_changes'] else 0
                performance[stadium][bey] = {
                    'matches': stats['matches'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'winrate': round(winrate, 3),
                    'points_for': stats['points_for'],
                    'points_against': stats['points_against'],
                    'point_differential': stats['points_for'] - stats['points_against'],
                    'avg_points_per_match': round(stats['points_for'] / stats['matches'], 2),
                    'avg_elo_change': round(avg_elo_change, 2)
                }

        # Sort by winrate and identify top/bottom performers
        sorted_beys = sorted(
            performance[stadium].items(),
            key=lambda x: (x[1]['winrate'], x[1]['matches']),
            reverse=True
        )

        performance[stadium + '_rankings'] = {
            'best_performers': [{'bey': b, **s} for b, s in sorted_beys[:5]] if sorted_beys else [],
            'worst_performers': [{'bey': b, **s} for b, s in sorted_beys[-5:]] if len(sorted_beys) >= 5 else []
        }

    return performance


def calculate_archetype_effectiveness_per_stadium(matches, rpg_stats):
    """Calculate archetype performance per stadium."""
    if not rpg_stats:
        return {}

    # Build bey to archetype mapping
    bey_to_archetype = {}
    for bey, stats in rpg_stats.items():
        if 'archetype' in stats:
            archetype = stats['archetype']
            if isinstance(archetype, dict):
                bey_to_archetype[bey] = archetype.get('name', archetype.get('id', 'Unknown'))
            else:
                bey_to_archetype[bey] = archetype

    archetype_stats = defaultdict(lambda: defaultdict(lambda: {
        'matches': 0,
        'wins': 0,
        'points_for': 0,
        'points_against': 0,
        'vs_archetype': defaultdict(lambda: {'wins': 0, 'matches': 0})
    }))

    for match in matches:
        stadium = match['stadium']
        bey_a = match['bey_a']
        bey_b = match['bey_b']

        archetype_a = bey_to_archetype.get(bey_a)
        archetype_b = bey_to_archetype.get(bey_b)

        if not archetype_a or not archetype_b:
            continue

        # Update archetype stats
        archetype_stats[stadium][archetype_a]['matches'] += 1
        archetype_stats[stadium][archetype_b]['matches'] += 1

        archetype_stats[stadium][archetype_a]['points_for'] += match['score_a']
        archetype_stats[stadium][archetype_a]['points_against'] += match['score_b']
        archetype_stats[stadium][archetype_b]['points_for'] += match['score_b']
        archetype_stats[stadium][archetype_b]['points_against'] += match['score_a']

        # Track wins and matchup performance
        if match['score_a'] > match['score_b']:
            archetype_stats[stadium][archetype_a]['wins'] += 1
            archetype_stats[stadium][archetype_a]['vs_archetype'][archetype_b]['wins'] += 1
            archetype_stats[stadium][archetype_a]['vs_archetype'][archetype_b]['matches'] += 1
            archetype_stats[stadium][archetype_b]['vs_archetype'][archetype_a]['matches'] += 1
        else:
            archetype_stats[stadium][archetype_b]['wins'] += 1
            archetype_stats[stadium][archetype_b]['vs_archetype'][archetype_a]['wins'] += 1
            archetype_stats[stadium][archetype_b]['vs_archetype'][archetype_a]['matches'] += 1
            archetype_stats[stadium][archetype_a]['vs_archetype'][archetype_b]['matches'] += 1

    # Calculate derived statistics
    effectiveness = {}
    for stadium, archetypes in archetype_stats.items():
        effectiveness[stadium] = {}
        for archetype, stats in archetypes.items():
            if stats['matches'] > 0:
                winrate = stats['wins'] / stats['matches']
                dominance = stats['points_for'] - stats['points_against']

                # Calculate vs_archetype winrates
                vs_archetype_winrates = {}
                for opp_arch, vs_stats in stats['vs_archetype'].items():
                    if vs_stats['matches'] > 0:
                        winrate_vs = round(
                            vs_stats['wins'] / vs_stats['matches'], 3)
                        vs_archetype_winrates[opp_arch] = {
                            'winrate': winrate_vs,
                            'matches': vs_stats['matches']
                        }

                effectiveness[stadium][archetype] = {
                    'matches': stats['matches'],
                    'wins': stats['wins'],
                    'winrate': round(winrate, 3),
                    'avg_dominance': round(dominance / stats['matches'], 2),
                    'total_dominance': dominance,
                    'vs_archetype': vs_archetype_winrates
                }

    return effectiveness


def calculate_finish_type_statistics_per_stadium(matches, rounds):
    """Calculate finish type distribution per stadium."""
    if not rounds:
        return {}

    # Map match_id to stadium
    match_to_stadium = {m['match_id']: m['stadium'] for m in matches}

    finish_stats = defaultdict(lambda: {
        'spin': 0,
        'burst': 0,
        'pocket': 0,
        'stadium_exit': 0,
        'extreme': 0,
        'total_rounds': 0,
        'total_points': 0
    })

    for round_data in rounds:
        stadium = match_to_stadium.get(
            round_data['match_id'], 'Xtreme Stadium')
        finish_type = round_data['finish_type']
        points = round_data['points_awarded']

        stats = finish_stats[stadium]
        stats[finish_type] += 1
        stats['total_rounds'] += 1
        stats['total_points'] += points

    # Calculate percentages and averages
    result = {}
    for stadium, stats in finish_stats.items():
        if stats['total_rounds'] > 0:
            result[stadium] = {
                'finish_counts': {
                    'spin': stats['spin'],
                    'burst': stats['burst'],
                    'pocket': stats['pocket'],
                    'stadium_exit': stats['stadium_exit'],
                    'extreme': stats['extreme']
                },
                'finish_percentages': {
                    'spin': round(stats['spin'] / stats['total_rounds'] * 100, 1),
                    'burst': round(stats['burst'] / stats['total_rounds'] * 100, 1),
                    'pocket': round(stats['pocket'] / stats['total_rounds'] * 100, 1),
                    'stadium_exit': round(stats['stadium_exit'] / stats['total_rounds'] * 100, 1),
                    'extreme': round(stats['extreme'] / stats['total_rounds'] * 100, 1)
                },
                'total_rounds': stats['total_rounds'],
                'avg_points_per_round': round(stats['total_points'] / stats['total_rounds'], 2)
            }

    return result


def calculate_elo_behavior_per_stadium(elo_history):
    """Analyze ELO behavior and volatility per stadium."""
    elo_behavior = defaultdict(lambda: {
        'elo_changes': [],
        'wins': 0,
        'upsets': 0,
        'dominant_wins': 0
    })

    for entry in elo_history:
        stadium = entry['stadium']
        behavior = elo_behavior[stadium]

        elo_change_a = entry['new_elo_a'] - entry['old_elo_a']
        elo_change_b = entry['new_elo_b'] - entry['old_elo_b']

        behavior['elo_changes'].append(abs(elo_change_a))
        behavior['elo_changes'].append(abs(elo_change_b))

        # Winner
        if entry['score_a'] > entry['score_b']:
            behavior['wins'] += 1
            # Upset if lower ELO won
            if entry['old_elo_a'] < entry['old_elo_b']:
                behavior['upsets'] += 1
            # Dominant win (4-0, 5-0, 6-0, etc.)
            if entry['score_b'] == 0 or (entry['score_a'] - entry['score_b']) >= 4:
                behavior['dominant_wins'] += 1
        else:
            behavior['wins'] += 1
            if entry['old_elo_b'] < entry['old_elo_a']:
                behavior['upsets'] += 1
            if entry['score_a'] == 0 or (entry['score_b'] - entry['score_a']) >= 4:
                behavior['dominant_wins'] += 1

    # Calculate summary statistics
    result = {}
    for stadium, behavior in elo_behavior.items():
        if behavior['elo_changes'] and behavior['wins'] > 0:
            elo_changes = behavior['elo_changes']
            stdev = (statistics.stdev(elo_changes)
                     if len(elo_changes) > 1 else 0)

            result[stadium] = {
                'avg_elo_change': round(statistics.mean(elo_changes), 2),
                'elo_volatility': round(stdev, 2),
                'upset_frequency': round(
                    behavior['upsets'] / behavior['wins'] * 100, 1),
                'dominant_win_frequency': round(
                    behavior['dominant_wins'] / behavior['wins'] * 100, 1),
                'total_matches': behavior['wins']
            }

    return result


def calculate_comparative_analysis(bey_performance, archetype_effectiveness, finish_stats, elo_behavior):
    """Generate comparative analysis between stadiums."""
    comparisons = []

    stadiums = list(bey_performance.keys())
    stadiums = [s for s in stadiums if not s.endswith('_rankings')]

    for i, stadium_a in enumerate(stadiums):
        for stadium_b in stadiums[i + 1:]:
            comparison = {
                'stadium_a': stadium_a,
                'stadium_b': stadium_b,
                'bey_winrate_deltas': {},
                'archetype_shifts': {},
                'finish_type_shifts': {},
                'elo_volatility_delta': 0
            }

            # Compare bey performance
            for bey in bey_performance[stadium_a]:
                if bey in bey_performance[stadium_b]:
                    wr_a = bey_performance[stadium_a][bey]['winrate']
                    wr_b = bey_performance[stadium_b][bey]['winrate']
                    delta = wr_b - wr_a
                    if abs(delta) > 0.05:  # Only significant changes
                        comparison['bey_winrate_deltas'][bey] = round(delta, 3)

            # Compare archetype effectiveness
            if stadium_a in archetype_effectiveness and stadium_b in archetype_effectiveness:
                for archetype in archetype_effectiveness[stadium_a]:
                    if archetype in archetype_effectiveness[stadium_b]:
                        wr_a = archetype_effectiveness[stadium_a][archetype]['winrate']
                        wr_b = archetype_effectiveness[stadium_b][archetype]['winrate']
                        delta = wr_b - wr_a
                        if abs(delta) > 0.05:
                            comparison['archetype_shifts'][archetype] = round(delta, 3)

            # Compare finish types
            if stadium_a in finish_stats and stadium_b in finish_stats:
                for finish_type in ['spin', 'burst', 'pocket', 'stadium_exit', 'extreme']:
                    pct_a = finish_stats[stadium_a]['finish_percentages'][finish_type]
                    pct_b = finish_stats[stadium_b]['finish_percentages'][finish_type]
                    comparison['finish_type_shifts'][finish_type] = round(pct_b - pct_a, 1)

            # Compare ELO volatility
            if stadium_a in elo_behavior and stadium_b in elo_behavior:
                vol_a = elo_behavior[stadium_a]['elo_volatility']
                vol_b = elo_behavior[stadium_b]['elo_volatility']
                comparison['elo_volatility_delta'] = round(vol_b - vol_a, 2)

            comparisons.append(comparison)

    return comparisons


def generate_stadium_analytics():
    """Main function to generate complete stadium analytics."""
    print(f"{CYAN}{BOLD}=== Stadium Statistics Generator ==={RESET}")
    print(f"{CYAN}Loading data files...{RESET}")

    # Load data
    matches = load_matches()
    rounds = load_rounds()
    elo_history = load_elo_history()
    rpg_stats = load_rpg_stats()

    if not matches:
        print(f"{RED}Error: No match data found. Aborting.{RESET}")
        return

    print(f"{GREEN}Loaded {len(matches)} matches{RESET}")
    print(f"{GREEN}Loaded {len(elo_history)} ELO history entries{RESET}")
    print(f"{GREEN}Loaded {len(rounds)} rounds{RESET}")

    # Calculate all analytics
    print(f"{CYAN}Calculating stadium overview...{RESET}")
    overview = calculate_stadium_overview(matches, elo_history)

    print(f"{CYAN}Calculating Bey performance per stadium...{RESET}")
    bey_performance = calculate_bey_performance_per_stadium(matches, elo_history)

    print(f"{CYAN}Calculating archetype effectiveness per stadium...{RESET}")
    archetype_effectiveness = calculate_archetype_effectiveness_per_stadium(matches, rpg_stats)

    print(f"{CYAN}Calculating score distribution per stadium...{RESET}")
    score_distribution = calculate_score_distribution_per_stadium(matches)

    print(f"{CYAN}Calculating finish type statistics per stadium...{RESET}")
    finish_stats = calculate_finish_type_statistics_per_stadium(matches, rounds)

    print(f"{CYAN}Analyzing ELO behavior per stadium...{RESET}")
    elo_behavior = calculate_elo_behavior_per_stadium(elo_history)

    print(f"{CYAN}Generating comparative analysis...{RESET}")
    comparisons = calculate_comparative_analysis(bey_performance, archetype_effectiveness, finish_stats, elo_behavior)

    # Combine all results
    analytics = {
        'generated_at': datetime.now().isoformat(),
        'stadium_overview': overview,
        'bey_performance': bey_performance,
        'archetype_effectiveness': archetype_effectiveness,
        'score_distribution': score_distribution,
        'finish_type_statistics': finish_stats,
        'elo_behavior': elo_behavior,
        'comparative_analysis': comparisons
    }

    # Save to JSON
    print(f"{CYAN}Saving stadium analytics...{RESET}")
    with open(STADIUM_ANALYTICS_JSON, 'w') as f:
        json.dump(analytics, f, indent=2)

    print(f"{GREEN}Stadium analytics saved to {STADIUM_ANALYTICS_JSON}{RESET}")

    # Print summary
    print(f"\n{BOLD}Stadium Summary:{RESET}")
    for stadium in overview:
        print(f"  {YELLOW}{stadium}{RESET}: {overview[stadium]['total_matches']} matches")


if __name__ == "__main__":
    generate_stadium_analytics()
