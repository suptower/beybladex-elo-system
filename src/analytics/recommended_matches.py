"""
Recommended Matches Module for Beyblade ELO Rating System

This module generates data-driven match recommendations to improve ranking
quality, meta balance, and data coverage. It provides advisory matchups based
on statistical analysis of existing match data, ELO ratings, and metadata.

Recommendation Types:
1. Low-Data Beys (Exploration): Beys with significantly fewer matches
2. ELO Clarity: Beys with similar ELO that haven't played each other
3. High-Uncertainty: Beys with high volatility needing stable references
4. Meta-Balance: Frequently vs rarely played Beys
5. Upset Testing: Matches with high upset potential

Each recommendation includes:
- Information Value Score: Quantifies the value of the matchup
- Category: Type of recommendation
- Explanation: Why this matchup is recommended

Output:
- recommended_matches.json: All recommendations with scores and explanations
"""
import csv
import json
import statistics
from collections import defaultdict


# Colors for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"

# File paths
ELO_HISTORY_CSV = "./docs/data/elo/elo_history.csv"
LEADERBOARD_CSV = "./docs/data/leaderboard/leaderboard.csv"
ADVANCED_LEADERBOARD_CSV = "./docs/data/leaderboard/advanced_leaderboard.csv"
MATCHES_CSV = "./docs/data/matches/matches.csv"
RECOMMENDED_MATCHES_OUTPUT = "./docs/data/analytics/recommended_matches.json"

# Configuration constants
CONFIG = {
    "low_data_threshold_percentile": 0.40,  # Below 40th percentile is "low data"
    "elo_similarity_window": 30,  # Beys within 30 ELO are "similar"
    "top_n_recommendations": 10,  # Number of recommendations to output
    "min_matches_for_analysis": 3,  # Minimum matches needed for analysis
    "high_volatility_percentile": 0.75,  # Top 25% volatility is "high"
    "meta_balance_usage_threshold": 2.0,  # Usage ratio for meta balance
    "upset_elo_difference_min": 50,  # Minimum ELO gap for upset potential
    "max_existing_matches_threshold": 3,  # Skip matchups played this many times
    "division_by_zero_epsilon": 0.1,  # Small value to prevent division by zero
}


def load_leaderboard_data():
    """
    Load leaderboard data with ELO ratings and basic stats.

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


def load_advanced_stats():
    """
    Load advanced statistics including volatility and trends.

    Returns:
        dict: Beyblade name -> advanced stats dict
    """
    advanced = {}

    try:
        with open(ADVANCED_LEADERBOARD_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Bey']
                advanced[name] = {
                    'volatility': float(row['Volatility']),
                    'trend': float(row['ELOTrend']),
                    'power_index': float(row['PowerIndex'])
                }
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {ADVANCED_LEADERBOARD_CSV} not found, using defaults{RESET}")
        return {}

    return advanced


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
        percentile = 0.99  # Cap at 99th percentile to avoid index errors

    quantiles = statistics.quantiles(match_counts, n=100)
    threshold_index = max(0, min(len(quantiles) - 1, int(percentile * 100) - 1))
    threshold = quantiles[threshold_index]

    low_data = [
        name for name, stats in beys.items()
        if stats['matches'] < threshold and stats['matches'] >= CONFIG['min_matches_for_analysis']
    ]

    return low_data


def identify_similar_elo_clusters(beys):
    """
    Identify groups of Beys with similar ELO ratings.

    Args:
        beys: Dict of bey stats

    Returns:
        list: List of (bey_a, bey_b, elo_diff) tuples for similar Beys
    """
    clusters = []
    bey_list = list(beys.items())

    for i, (name_a, stats_a) in enumerate(bey_list):
        for name_b, stats_b in bey_list[i + 1:]:
            elo_diff = abs(stats_a['elo'] - stats_b['elo'])
            if elo_diff <= CONFIG['elo_similarity_window']:
                clusters.append((name_a, name_b, elo_diff))

    return clusters


def identify_high_uncertainty_beys(beys, advanced_stats):
    """
    Identify Beys with high ELO volatility.

    Args:
        beys: Dict of bey stats
        advanced_stats: Dict of advanced stats including volatility

    Returns:
        list: Bey names with high uncertainty
    """
    if not advanced_stats:
        return []

    # Get volatility values for Beys in our dataset
    volatilities = []
    for name in beys:
        if name in advanced_stats:
            volatilities.append(advanced_stats[name]['volatility'])

    if not volatilities:
        return []

    # Use quantiles to find threshold, with bounds checking
    percentile = CONFIG['high_volatility_percentile']
    if percentile >= 1.0:
        percentile = 0.99  # Cap at 99th percentile to avoid index errors

    quantiles = statistics.quantiles(volatilities, n=100)
    threshold_index = max(0, min(len(quantiles) - 1, int(percentile * 100) - 1))
    threshold = quantiles[threshold_index]

    high_uncertainty = [
        name for name in beys
        if name in advanced_stats and advanced_stats[name]['volatility'] >= threshold
    ]

    return high_uncertainty


def calculate_usage_ratios(beys):
    """
    Calculate usage ratios for meta balance analysis.

    Args:
        beys: Dict of bey stats

    Returns:
        dict: Bey name -> usage ratio (matches / average)
    """
    if not beys:
        return {}

    avg_matches = statistics.mean([stats['matches'] for stats in beys.values()])

    return {
        name: stats['matches'] / avg_matches
        for name, stats in beys.items()
    }


def generate_low_data_recommendations(low_data_beys, beys, matchups):
    """
    Generate recommendations for low-data Beys.

    Args:
        low_data_beys: List of Bey names needing more data
        beys: Dict of all bey stats
        matchups: Dict of existing matchup counts

    Returns:
        list: Recommendation dicts
    """
    recommendations = []

    for bey in low_data_beys:
        elo = beys[bey]['elo']

        # Find reference opponents at different ELO levels
        # Target: -50 ELO, same ELO, +50 ELO
        targets = [elo - 50, elo, elo + 50]

        for target_elo in targets:
            # Find closest Bey to target ELO that hasn't been overplayed
            best_opponent = None
            best_diff = float('inf')

            for opponent, opp_stats in beys.items():
                if opponent == bey:
                    continue

                # Check if they've already played
                pair = tuple(sorted([bey, opponent]))
                existing_matches = matchups.get(pair, 0)

                # Skip if already played multiple times
                if existing_matches >= CONFIG['max_existing_matches_threshold']:
                    continue

                elo_diff = abs(opp_stats['elo'] - target_elo)
                if elo_diff < best_diff:
                    best_diff = elo_diff
                    best_opponent = opponent

            if best_opponent:
                pair = tuple(sorted([bey, best_opponent]))
                existing = matchups.get(pair, 0)

                # Information value: higher for fewer existing matches and needed data
                info_value = 100 - (existing * 10) + (10 / (beys[bey]['matches'] + 1))

                explanation = (
                    f"{bey} has only {beys[bey]['matches']} matches. "
                    f"Playing against {best_opponent} "
                    f"(ELO {beys[best_opponent]['elo']:.0f}) would help establish ranking."
                )
                recommendations.append({
                    'bey_a': bey,
                    'bey_b': best_opponent,
                    'category': 'low_data_exploration',
                    'info_value': round(info_value, 2),
                    'explanation': explanation,
                    'existing_matches': existing
                })

    return recommendations


def generate_elo_clarity_recommendations(clusters, beys, matchups):
    """
    Generate recommendations for Beys with similar ELO.

    Args:
        clusters: List of (bey_a, bey_b, elo_diff) tuples
        beys: Dict of all bey stats
        matchups: Dict of existing matchup counts

    Returns:
        list: Recommendation dicts
    """
    recommendations = []

    for bey_a, bey_b, elo_diff in clusters:
        pair = tuple(sorted([bey_a, bey_b]))
        existing = matchups.get(pair, 0)

        # Skip if they've played many times already
        if existing >= 2:
            continue

        # Higher value for closer ELO and fewer existing matches
        info_value = 80 - elo_diff - (existing * 15)

        # Bonus if they're in top rankings
        if beys[bey_a]['rank'] <= 10 and beys[bey_b]['rank'] <= 10:
            info_value += 20
            explanation = (
                f"Top-ranked Beys {bey_a} (#{beys[bey_a]['rank']}) and "
                f"{bey_b} (#{beys[bey_b]['rank']}) are within {elo_diff:.0f} ELO "
                f"but have only played {existing} time(s). Direct comparison needed."
            )
        else:
            explanation = (
                f"{bey_a} and {bey_b} have similar ELO ({elo_diff:.0f} difference) "
                f"but have only played {existing} time(s). "
                f"Direct matchup would clarify ranking."
            )

        recommendations.append({
            'bey_a': bey_a,
            'bey_b': bey_b,
            'category': 'elo_clarity',
            'info_value': round(info_value, 2),
            'explanation': explanation,
            'existing_matches': existing
        })

    return recommendations


def generate_uncertainty_recommendations(high_uncertainty_beys, beys, advanced_stats, matchups):
    """
    Generate recommendations for high-uncertainty Beys.

    Args:
        high_uncertainty_beys: List of Bey names with high volatility
        beys: Dict of all bey stats
        advanced_stats: Dict of advanced stats
        matchups: Dict of existing matchup counts

    Returns:
        list: Recommendation dicts
    """
    recommendations = []

    # Find stable reference Beys (low volatility, many matches)
    stable_refs = []
    if advanced_stats:
        for name, stats in beys.items():
            if name in advanced_stats and stats['matches'] >= 10:
                if advanced_stats[name]['volatility'] < statistics.mean(
                    [advanced_stats[n]['volatility'] for n in beys if n in advanced_stats]
                ):
                    stable_refs.append(name)

    for bey in high_uncertainty_beys:
        volatility = advanced_stats.get(bey, {}).get('volatility', 0)

        # Find closest stable reference
        best_ref = None
        best_diff = float('inf')

        for ref in stable_refs:
            if ref == bey:
                continue

            elo_diff = abs(beys[bey]['elo'] - beys[ref]['elo'])
            if elo_diff < best_diff:
                best_diff = elo_diff
                best_ref = ref

        if best_ref:
            pair = tuple(sorted([bey, best_ref]))
            existing = matchups.get(pair, 0)

            # Skip if played too many times
            if existing >= 2:
                continue

            info_value = 70 + (volatility * 2) - (existing * 10)

            explanation = (
                f"{bey} has high ELO volatility ({volatility:.1f}). "
                f"Playing against stable reference {best_ref} would help stabilize rating."
            )
            recommendations.append({
                'bey_a': bey,
                'bey_b': best_ref,
                'category': 'high_uncertainty',
                'info_value': round(info_value, 2),
                'explanation': explanation,
                'existing_matches': existing
            })

    return recommendations


def generate_meta_balance_recommendations(beys, matchups):
    """
    Generate recommendations to balance meta representation.

    Args:
        beys: Dict of all bey stats
        matchups: Dict of existing matchup counts

    Returns:
        list: Recommendation dicts
    """
    recommendations = []
    usage_ratios = calculate_usage_ratios(beys)

    # Find overplayed and underplayed Beys
    overplayed = [name for name, ratio in usage_ratios.items()
                  if ratio >= CONFIG['meta_balance_usage_threshold']]
    underplayed = [name for name, ratio in usage_ratios.items()
                   if ratio < 1 / CONFIG['meta_balance_usage_threshold']]

    for over_bey in overplayed:
        for under_bey in underplayed:
            pair = tuple(sorted([over_bey, under_bey]))
            existing = matchups.get(pair, 0)

            # Skip if already played
            if existing >= 1:
                continue

            info_value = (
                60 + (usage_ratios[over_bey] * 5) +
                (10 / (usage_ratios[under_bey] + CONFIG['division_by_zero_epsilon']))
            )

            explanation = (
                f"{over_bey} ({beys[over_bey]['matches']} matches) is frequently played "
                f"while {under_bey} ({beys[under_bey]['matches']} matches) is "
                f"underrepresented. This matchup would improve meta balance."
            )
            recommendations.append({
                'bey_a': over_bey,
                'bey_b': under_bey,
                'category': 'meta_balance',
                'info_value': round(info_value, 2),
                'explanation': explanation,
                'existing_matches': existing
            })

    return recommendations


def generate_upset_recommendations(beys, matchups):
    """
    Generate recommendations for potential upset matches.

    Args:
        beys: Dict of all bey stats
        matchups: Dict of existing matchup counts

    Returns:
        list: Recommendation dicts
    """
    recommendations = []
    bey_list = list(beys.items())

    for i, (strong_bey, strong_stats) in enumerate(bey_list):
        for weak_bey, weak_stats in bey_list[i + 1:]:
            elo_diff = strong_stats['elo'] - weak_stats['elo']

            # We want large ELO gaps for upset potential
            if abs(elo_diff) < CONFIG['upset_elo_difference_min']:
                continue

            # Determine which is actually stronger
            if elo_diff < 0:
                strong_bey, weak_bey = weak_bey, strong_bey
                strong_stats, weak_stats = weak_stats, strong_stats
                elo_diff = abs(elo_diff)

            pair = tuple(sorted([strong_bey, weak_bey]))
            existing = matchups.get(pair, 0)

            # Skip if already played multiple times
            if existing >= 2:
                continue

            # Higher value for larger ELO gaps and fewer existing matches
            info_value = 50 + (elo_diff / 5) - (existing * 15)

            explanation = (
                f"{strong_bey} (ELO {strong_stats['elo']:.0f}) vs "
                f"{weak_bey} (ELO {weak_stats['elo']:.0f}) has {elo_diff:.0f} ELO difference. "
                f"Testing this matchup could reveal rating inaccuracies."
            )
            recommendations.append({
                'bey_a': strong_bey,
                'bey_b': weak_bey,
                'category': 'upset_testing',
                'info_value': round(info_value, 2),
                'explanation': explanation,
                'existing_matches': existing
            })

    return recommendations


def run_recommendation_pipeline():
    """
    Main pipeline to generate all match recommendations.

    Returns:
        dict: Complete recommendations data structure
    """
    print(f"{CYAN}{BOLD}Generating Recommended Matches...{RESET}")

    # Load data
    print("  Loading leaderboard data...")
    beys = load_leaderboard_data()

    if not beys:
        print(f"{RED}Error: No beyblade data loaded{RESET}")
        return None

    print("  Loading advanced statistics...")
    advanced_stats = load_advanced_stats()

    print("  Loading matchup history...")
    matchups = load_matchup_history()

    # Generate recommendations by category
    print("  Analyzing low-data Beys...")
    low_data_beys = identify_low_data_beys(beys)
    low_data_recs = generate_low_data_recommendations(low_data_beys, beys, matchups)

    print("  Analyzing ELO clusters...")
    clusters = identify_similar_elo_clusters(beys)
    elo_clarity_recs = generate_elo_clarity_recommendations(clusters, beys, matchups)

    print("  Analyzing high-uncertainty Beys...")
    high_uncertainty_beys = identify_high_uncertainty_beys(beys, advanced_stats)
    uncertainty_recs = generate_uncertainty_recommendations(
        high_uncertainty_beys, beys, advanced_stats, matchups
    )

    print("  Analyzing meta balance...")
    meta_balance_recs = generate_meta_balance_recommendations(beys, matchups)

    print("  Analyzing upset potential...")
    upset_recs = generate_upset_recommendations(beys, matchups)

    # Combine all recommendations
    all_recs = (
        low_data_recs + elo_clarity_recs + uncertainty_recs +
        meta_balance_recs + upset_recs
    )

    # Sort by information value
    all_recs.sort(key=lambda x: x['info_value'], reverse=True)

    # Take top N
    top_recommendations = all_recs[:CONFIG['top_n_recommendations']]

    # Group by category for output
    by_category = defaultdict(list)
    for rec in all_recs:
        by_category[rec['category']].append(rec)

    # Create output structure
    output = {
        'metadata': {
            'total_recommendations': len(all_recs),
            'top_n': CONFIG['top_n_recommendations'],
            'categories': {
                'low_data_exploration': len(low_data_recs),
                'elo_clarity': len(elo_clarity_recs),
                'high_uncertainty': len(uncertainty_recs),
                'meta_balance': len(meta_balance_recs),
                'upset_testing': len(upset_recs)
            }
        },
        'top_recommendations': top_recommendations,
        'by_category': dict(by_category)
    }

    # Save to JSON
    with open(RECOMMENDED_MATCHES_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"{GREEN} Generated {len(all_recs)} recommendations{RESET}")
    print(f"{GREEN} Top {len(top_recommendations)} recommendations saved to {RECOMMENDED_MATCHES_OUTPUT}{RESET}")

    # Print summary
    print(f"\n{BOLD}Recommendation Summary:{RESET}")
    for category, count in output['metadata']['categories'].items():
        print(f"  {category}: {count} recommendations")

    return output


if __name__ == "__main__":
    run_recommendation_pipeline()
