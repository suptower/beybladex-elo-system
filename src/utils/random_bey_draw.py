"""
Random Bey Draw / Tournament Seeding Tool

This module provides algorithms for randomly selecting Beys from the leaderboard
for tournament seeding and quick event setup.

Supports multiple draw algorithms:
1. Pure Random - Uniform random selection
2. Ranking Bucket Balanced - Draw evenly from rank ranges
3. Weighted by Elo - Higher Elo = higher probability
4. Type-Based Distribution - Balanced mix of Attack/Defense/Stamina/Balance
5. Archetype-Based Distribution - Ensures diversity across playstyles
6. Custom Constraints - Min/max Elo, exclude/include specific Beys
"""

import random
import json
import math
from typing import List, Dict, Set, Optional
from collections import defaultdict


def load_leaderboard_data(leaderboard_path: str = './docs/data/leaderboard/leaderboard.csv') -> List[Dict]:
    """Load leaderboard data from CSV."""
    import csv
    beys = []
    with open(leaderboard_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            beys.append({
                'name': row['Name'],
                'elo': int(row['ELO']),
                'rank': int(row['Platz']),
                'matches': int(row['Spiele']),
                'wins': int(row['Siege']),
                'winrate': float(row['Winrate'].rstrip('%'))
            })
    return beys


def load_bey_metadata(beys_data_path: str = './docs/data/beys/beys_data.json') -> Dict[str, Dict]:
    """Load Bey metadata including types and descriptions."""
    with open(beys_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create a mapping from blade name to metadata
    bey_metadata = {}
    for bey in data:
        blade = bey['blade']
        bey_metadata[blade] = {
            'type': bey.get('type', 'Unknown'),
            'code': bey.get('code', ''),
            'description': bey.get('description', '')
        }
    return bey_metadata


def load_rpg_stats(rpg_path: str = './docs/data/analytics/rpg_stats.json') -> Dict[str, Dict]:
    """Load RPG stats including archetype information."""
    with open(rpg_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def pure_random(beys: List[Dict], count: int, seed: Optional[int] = None) -> List[Dict]:
    """
    Pure Random Selection - Uniform random selection from all Beys.

    Args:
        beys: List of Bey dictionaries
        count: Number of Beys to draw
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(beys))
    return random.sample(beys, count)


def ranking_bucket_balanced(
    beys: List[Dict],
    count: int,
    buckets: int = 3,
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Ranking Bucket Balanced - Draw evenly from rank ranges.

    Splits leaderboard into buckets (e.g., Top, Mid, Bottom) and draws
    roughly equal numbers from each bucket.

    Args:
        beys: List of Bey dictionaries (should be sorted by rank)
        count: Number of Beys to draw
        buckets: Number of ranking buckets to split into (default: 3)
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(beys))

    # Sort by rank to ensure proper bucketing
    sorted_beys = sorted(beys, key=lambda x: x['rank'])

    # Handle edge case: more buckets than Beys
    effective_buckets = min(buckets, len(sorted_beys))

    if effective_buckets == 0:
        return []

    # Split into buckets
    bucket_size = len(sorted_beys) // effective_buckets
    bey_buckets = []

    for i in range(effective_buckets):
        start = i * bucket_size
        end = start + bucket_size if i < effective_buckets - 1 else len(sorted_beys)
        if start < len(sorted_beys):
            bey_buckets.append(sorted_beys[start:end])

    # Calculate how many to draw from each bucket
    base_per_bucket = count // len(bey_buckets)
    remainder = count % len(bey_buckets)

    selected = []
    for i, bucket in enumerate(bey_buckets):
        if not bucket:
            continue
        # Distribute remainder to earlier buckets
        bucket_count = base_per_bucket + (1 if i < remainder else 0)
        bucket_count = min(bucket_count, len(bucket))
        if bucket_count > 0:
            selected.extend(random.sample(bucket, bucket_count))

    return selected


def weighted_by_elo(
    beys: List[Dict],
    count: int,
    weighting: str = 'linear',
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Weighted by Elo - Higher Elo = higher selection probability.

    Args:
        beys: List of Bey dictionaries
        count: Number of Beys to draw
        weighting: 'linear' or 'soft' (logarithmic)
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(beys))

    # Calculate weights based on Elo
    if weighting == 'soft':
        # Logarithmic weighting - reduces advantage of high Elo
        weights = [math.log(max(bey['elo'], 1)) for bey in beys]
    else:  # linear
        # Linear weighting - direct proportion to Elo
        weights = [bey['elo'] for bey in beys]

    # Ensure all weights are positive
    min_weight = min(weights)
    if min_weight <= 0:
        weights = [w - min_weight + 1 for w in weights]

    # Use random.choices for weighted selection without replacement
    selected = []
    remaining_beys = beys.copy()
    remaining_weights = weights.copy()

    for _ in range(count):
        chosen_bey = random.choices(remaining_beys, weights=remaining_weights, k=1)[0]
        idx = remaining_beys.index(chosen_bey)
        selected.append(chosen_bey)
        remaining_beys.pop(idx)
        remaining_weights.pop(idx)

    return selected


def type_based_distribution(
    beys: List[Dict],
    bey_metadata: Dict[str, Dict],
    count: int,
    distribution: str = 'balanced',
    max_per_type: Optional[int] = None,
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Type-Based Distribution - Ensures balanced mix of Bey types.

    Args:
        beys: List of Bey dictionaries
        bey_metadata: Metadata including type information
        count: Number of Beys to draw
        distribution: 'balanced' (equal from each) or 'proportional' (by availability)
        max_per_type: Optional maximum number per type
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(beys))

    # Group Beys by type
    beys_by_type = defaultdict(list)
    for bey in beys:
        bey_type = bey_metadata.get(bey['name'], {}).get('type', 'Unknown')
        beys_by_type[bey_type].append(bey)

    types = list(beys_by_type.keys())

    if distribution == 'balanced':
        # Try to draw equal numbers from each type
        per_type = count // len(types)
        remainder = count % len(types)

        selected = []
        for i, bey_type in enumerate(types):
            type_beys = beys_by_type[bey_type]
            type_count = per_type + (1 if i < remainder else 0)

            if max_per_type is not None:
                type_count = min(type_count, max_per_type)

            type_count = min(type_count, len(type_beys))
            selected.extend(random.sample(type_beys, type_count))

        # If we didn't get enough due to constraints, fill from remaining
        if len(selected) < count:
            remaining = [b for b in beys if b not in selected]
            needed = count - len(selected)
            selected.extend(random.sample(remaining, min(needed, len(remaining))))

    else:  # proportional
        # Draw proportionally to type availability
        selected = []
        for bey_type in types:
            type_beys = beys_by_type[bey_type]
            proportion = len(type_beys) / len(beys)
            type_count = round(count * proportion)

            if max_per_type is not None:
                type_count = min(type_count, max_per_type)

            type_count = min(type_count, len(type_beys))
            selected.extend(random.sample(type_beys, type_count))

        # Adjust to exact count
        if len(selected) < count:
            remaining = [b for b in beys if b not in selected]
            needed = count - len(selected)
            selected.extend(random.sample(remaining, min(needed, len(remaining))))
        elif len(selected) > count:
            selected = random.sample(selected, count)

    return selected


def archetype_based_distribution(
    beys: List[Dict],
    rpg_stats: Dict[str, Dict],
    count: int,
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Archetype-Based Distribution - Ensures diversity across playstyles.

    Args:
        beys: List of Bey dictionaries
        rpg_stats: RPG stats including archetype information
        count: Number of Beys to draw
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(beys))

    # Group Beys by archetype
    beys_by_archetype = defaultdict(list)
    beys_without_archetype = []

    for bey in beys:
        if bey['name'] in rpg_stats:
            archetype_id = rpg_stats[bey['name']]['archetype']['id']
            beys_by_archetype[archetype_id].append(bey)
        else:
            beys_without_archetype.append(bey)

    archetypes = list(beys_by_archetype.keys())

    if not archetypes:
        # No archetype data, fall back to pure random
        return random.sample(beys, count)

    # Try to draw evenly from each archetype
    per_archetype = count // len(archetypes)
    remainder = count % len(archetypes)

    selected = []
    for i, archetype in enumerate(archetypes):
        archetype_beys = beys_by_archetype[archetype]
        archetype_count = per_archetype + (1 if i < remainder else 0)
        archetype_count = min(archetype_count, len(archetype_beys))
        selected.extend(random.sample(archetype_beys, archetype_count))

    # Fill remaining from Beys without archetype if needed
    if len(selected) < count and beys_without_archetype:
        needed = count - len(selected)
        selected.extend(random.sample(beys_without_archetype, min(needed, len(beys_without_archetype))))

    # If still not enough, fill from any remaining
    if len(selected) < count:
        remaining = [b for b in beys if b not in selected]
        needed = count - len(selected)
        if remaining:
            selected.extend(random.sample(remaining, min(needed, len(remaining))))

    return selected


def custom_constraints(
    beys: List[Dict],
    count: int,
    min_elo: Optional[int] = None,
    max_elo: Optional[int] = None,
    exclude: Optional[Set[str]] = None,
    include: Optional[Set[str]] = None,
    seed: Optional[int] = None
) -> List[Dict]:
    """
    Custom Constraints - Advanced filtering with custom rules.

    Args:
        beys: List of Bey dictionaries
        count: Number of Beys to draw
        min_elo: Minimum Elo requirement
        max_elo: Maximum Elo requirement
        exclude: Set of Bey names to exclude
        include: Set of Bey names to force include
        seed: Optional random seed for reproducibility

    Returns:
        List of selected Beys
    """
    if seed is not None:
        random.seed(seed)

    exclude = exclude or set()
    include = include or set()

    # Start with included Beys
    selected = [b for b in beys if b['name'] in include]

    # Filter eligible Beys
    eligible = []
    for bey in beys:
        # Skip if already selected or excluded
        if bey in selected or bey['name'] in exclude:
            continue

        # Apply Elo constraints
        if min_elo is not None and bey['elo'] < min_elo:
            continue
        if max_elo is not None and bey['elo'] > max_elo:
            continue

        eligible.append(bey)

    # Draw remaining from eligible
    remaining_count = count - len(selected)
    if remaining_count > 0 and eligible:
        additional = random.sample(eligible, min(remaining_count, len(eligible)))
        selected.extend(additional)

    return selected[:count]


def draw_beys(
    algorithm: str,
    count: int,
    leaderboard_path: str = './docs/data/leaderboard/leaderboard.csv',
    beys_data_path: str = './docs/data/beys/beys_data.json',
    rpg_path: str = './docs/data/analytics/rpg_stats.json',
    **kwargs
) -> List[Dict]:
    """
    Main entry point for drawing Beys using specified algorithm.

    Args:
        algorithm: One of 'pure_random', 'ranking_bucket', 'weighted_elo',
                   'type_based', 'archetype_based', 'custom'
        count: Number of Beys to draw
        leaderboard_path: Path to leaderboard CSV
        beys_data_path: Path to Beys metadata JSON
        rpg_path: Path to RPG stats JSON
        **kwargs: Additional algorithm-specific parameters

    Returns:
        List of selected Beys with metadata
    """
    # Load data
    beys = load_leaderboard_data(leaderboard_path)

    # Execute algorithm
    if algorithm == 'pure_random':
        selected = pure_random(beys, count, kwargs.get('seed'))

    elif algorithm == 'ranking_bucket':
        selected = ranking_bucket_balanced(
            beys, count,
            kwargs.get('buckets', 3),
            kwargs.get('seed')
        )

    elif algorithm == 'weighted_elo':
        selected = weighted_by_elo(
            beys, count,
            kwargs.get('weighting', 'linear'),
            kwargs.get('seed')
        )

    elif algorithm == 'type_based':
        bey_metadata = load_bey_metadata(beys_data_path)
        selected = type_based_distribution(
            beys, bey_metadata, count,
            kwargs.get('distribution', 'balanced'),
            kwargs.get('max_per_type'),
            kwargs.get('seed')
        )

    elif algorithm == 'archetype_based':
        rpg_stats = load_rpg_stats(rpg_path)
        selected = archetype_based_distribution(
            beys, rpg_stats, count,
            kwargs.get('seed')
        )

    elif algorithm == 'custom':
        selected = custom_constraints(
            beys, count,
            kwargs.get('min_elo'),
            kwargs.get('max_elo'),
            kwargs.get('exclude'),
            kwargs.get('include'),
            kwargs.get('seed')
        )

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Enhance with metadata if available
    try:
        bey_metadata = load_bey_metadata(beys_data_path)
        rpg_stats = load_rpg_stats(rpg_path)

        for bey in selected:
            metadata = bey_metadata.get(bey['name'], {})
            bey['type'] = metadata.get('type', 'Unknown')
            bey['code'] = metadata.get('code', '')

            if bey['name'] in rpg_stats:
                archetype = rpg_stats[bey['name']]['archetype']
                bey['archetype'] = archetype['name']
                bey['archetype_icon'] = archetype['icon']
    except Exception:
        # If metadata loading fails, continue without it
        pass

    return selected


if __name__ == '__main__':
    """Command-line interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Random Bey Draw Tool')
    parser.add_argument('-n', '--count', type=int, default=8,
                        help='Number of Beys to draw (default: 8)')
    parser.add_argument('-a', '--algorithm',
                        choices=['pure_random', 'ranking_bucket', 'weighted_elo',
                                 'type_based', 'archetype_based', 'custom'],
                        default='pure_random',
                        help='Draw algorithm to use')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
    parser.add_argument('--buckets', type=int, default=3,
                        help='Number of ranking buckets (for ranking_bucket)')
    parser.add_argument('--weighting', choices=['linear', 'soft'], default='linear',
                        help='Weighting type (for weighted_elo)')
    parser.add_argument('--distribution', choices=['balanced', 'proportional'],
                        default='balanced',
                        help='Distribution type (for type_based)')
    parser.add_argument('--max-per-type', type=int,
                        help='Maximum per type (for type_based)')
    parser.add_argument('--min-elo', type=int, help='Minimum Elo (for custom)')
    parser.add_argument('--max-elo', type=int, help='Maximum Elo (for custom)')
    parser.add_argument('--exclude', nargs='+', help='Beys to exclude (for custom)')
    parser.add_argument('--include', nargs='+', help='Beys to force include (for custom)')

    args = parser.parse_args()

    kwargs = {
        'seed': args.seed,
        'buckets': args.buckets,
        'weighting': args.weighting,
        'distribution': args.distribution,
        'max_per_type': args.max_per_type,
        'min_elo': args.min_elo,
        'max_elo': args.max_elo,
        'exclude': set(args.exclude) if args.exclude else None,
        'include': set(args.include) if args.include else None,
    }

    selected = draw_beys(args.algorithm, args.count, **kwargs)

    print(f"\n🎲 Random Bey Draw - {args.algorithm}")
    print(f"Selected {len(selected)} Beys:\n")

    for i, bey in enumerate(selected, 1):
        type_str = f" ({bey.get('type', 'Unknown')})" if 'type' in bey else ""
        archetype_str = f" - {bey.get('archetype_icon', '')} {bey.get('archetype', '')}" if 'archetype' in bey else ""
        print(f"{i}. {bey['name']}: ELO {bey['elo']}, Rank #{bey['rank']}{type_str}{archetype_str}")
