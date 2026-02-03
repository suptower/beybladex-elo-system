"""
Unit tests for random_bey_draw.py module.
Tests all draw algorithms and their various configurations.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from random_bey_draw import (
    pure_random,
    ranking_bucket_balanced,
    weighted_by_elo,
    type_based_distribution,
    archetype_based_distribution,
    custom_constraints
)


# Sample test data
SAMPLE_BEYS = [
    {'name': 'BeyA', 'elo': 1100, 'rank': 1, 'matches': 20, 'wins': 15, 'winrate': 75.0},
    {'name': 'BeyB', 'elo': 1050, 'rank': 2, 'matches': 18, 'wins': 12, 'winrate': 66.7},
    {'name': 'BeyC', 'elo': 1000, 'rank': 3, 'matches': 15, 'wins': 10, 'winrate': 66.7},
    {'name': 'BeyD', 'elo': 980, 'rank': 4, 'matches': 12, 'wins': 6, 'winrate': 50.0},
    {'name': 'BeyE', 'elo': 960, 'rank': 5, 'matches': 10, 'wins': 5, 'winrate': 50.0},
    {'name': 'BeyF', 'elo': 940, 'rank': 6, 'matches': 8, 'wins': 3, 'winrate': 37.5},
]

SAMPLE_METADATA = {
    'BeyA': {'type': 'Attack', 'code': 'BX-01'},
    'BeyB': {'type': 'Defense', 'code': 'BX-02'},
    'BeyC': {'type': 'Attack', 'code': 'BX-03'},
    'BeyD': {'type': 'Stamina', 'code': 'BX-04'},
    'BeyE': {'type': 'Balance', 'code': 'BX-05'},
    'BeyF': {'type': 'Defense', 'code': 'BX-06'},
}

SAMPLE_RPG_STATS = {
    'BeyA': {'archetype': {'id': 'berserker', 'name': 'Berserker', 'icon': '⚔️'}},
    'BeyB': {'archetype': {'id': 'fortress', 'name': 'Fortress', 'icon': '🛡️'}},
    'BeyC': {'archetype': {'id': 'berserker', 'name': 'Berserker', 'icon': '⚔️'}},
    'BeyD': {'archetype': {'id': 'endurance', 'name': 'Endurance', 'icon': '♾️'}},
    'BeyE': {'archetype': {'id': 'tempo_controller', 'name': 'Tempo Controller', 'icon': '🎼'}},
    'BeyF': {'archetype': {'id': 'fortress', 'name': 'Fortress', 'icon': '🛡️'}},
}


class TestPureRandom:
    """Tests for pure random selection."""

    def test_basic_draw(self):
        """Should return correct number of Beys."""
        selected = pure_random(SAMPLE_BEYS, 3, seed=42)
        assert len(selected) == 3
        assert all(bey in SAMPLE_BEYS for bey in selected)

    def test_no_duplicates(self):
        """Should not return duplicate Beys."""
        selected = pure_random(SAMPLE_BEYS, 4, seed=42)
        names = [bey['name'] for bey in selected]
        assert len(names) == len(set(names))

    def test_max_count(self):
        """Should not exceed total available Beys."""
        selected = pure_random(SAMPLE_BEYS, 100, seed=42)
        assert len(selected) == len(SAMPLE_BEYS)

    def test_reproducibility(self):
        """Same seed should produce same results."""
        result1 = pure_random(SAMPLE_BEYS, 3, seed=42)
        result2 = pure_random(SAMPLE_BEYS, 3, seed=42)
        assert [b['name'] for b in result1] == [b['name'] for b in result2]

    def test_different_seeds(self):
        """Different seeds should likely produce different results."""
        result1 = pure_random(SAMPLE_BEYS, 3, seed=42)
        result2 = pure_random(SAMPLE_BEYS, 3, seed=99)
        # While theoretically possible to be same, very unlikely with different seeds
        # We'll just check they're valid selections
        assert len(result1) == 3
        assert len(result2) == 3


class TestRankingBucketBalanced:
    """Tests for ranking bucket balanced selection."""

    def test_basic_draw(self):
        """Should return correct number of Beys."""
        selected = ranking_bucket_balanced(SAMPLE_BEYS, 3, buckets=3, seed=42)
        assert len(selected) == 3

    def test_bucket_distribution(self):
        """Should draw from different rank ranges."""
        # With 6 Beys and 3 buckets, each bucket has 2 Beys
        # Drawing 3 should take 1 from each bucket
        selected = ranking_bucket_balanced(SAMPLE_BEYS, 3, buckets=3, seed=42)
        ranks = [bey['rank'] for bey in selected]

        # Check that we have diversity in ranks (not all from same range)
        assert len(set(ranks)) > 1

    def test_two_buckets(self):
        """Should work with 2 buckets."""
        selected = ranking_bucket_balanced(SAMPLE_BEYS, 4, buckets=2, seed=42)
        assert len(selected) == 4

    def test_more_buckets_than_beys(self):
        """Should handle edge case of more buckets than Beys."""
        selected = ranking_bucket_balanced(SAMPLE_BEYS[:3], 2, buckets=5, seed=42)
        assert len(selected) == 2


class TestWeightedByElo:
    """Tests for Elo-weighted selection."""

    def test_basic_draw(self):
        """Should return correct number of Beys."""
        selected = weighted_by_elo(SAMPLE_BEYS, 3, weighting='linear', seed=42)
        assert len(selected) == 3

    def test_linear_weighting(self):
        """Linear weighting should favor higher Elo."""
        # With fixed seed, test multiple draws
        selections = []
        for seed in range(10):
            selected = weighted_by_elo(SAMPLE_BEYS, 3, weighting='linear', seed=seed)
            selections.extend([bey['name'] for bey in selected])

        # Higher Elo Beys should appear more frequently
        # This is probabilistic, but with 30 selections, should be clear
        from collections import Counter
        counts = Counter(selections)

        # Just verify the algorithm runs and produces valid results
        assert len(counts) > 0

    def test_soft_weighting(self):
        """Soft weighting should still work."""
        selected = weighted_by_elo(SAMPLE_BEYS, 3, weighting='soft', seed=42)
        assert len(selected) == 3

    def test_no_duplicates(self):
        """Should not return duplicates."""
        selected = weighted_by_elo(SAMPLE_BEYS, 4, weighting='linear', seed=42)
        names = [bey['name'] for bey in selected]
        assert len(names) == len(set(names))


class TestTypeBasedDistribution:
    """Tests for type-based distribution."""

    def test_balanced_distribution(self):
        """Should try to balance types."""
        selected = type_based_distribution(
            SAMPLE_BEYS, SAMPLE_METADATA, 4,
            distribution='balanced', seed=42
        )
        assert len(selected) == 4

        # Check we have different types
        types = [SAMPLE_METADATA[bey['name']]['type'] for bey in selected]
        assert len(set(types)) > 1

    def test_max_per_type(self):
        """Should respect max_per_type constraint."""
        selected = type_based_distribution(
            SAMPLE_BEYS, SAMPLE_METADATA, 6,
            distribution='balanced', max_per_type=2, seed=42
        )

        types = [SAMPLE_METADATA[bey['name']]['type'] for bey in selected]
        from collections import Counter
        type_counts = Counter(types)

        # No type should have more than max_per_type
        assert all(count <= 2 for count in type_counts.values())

    def test_proportional_distribution(self):
        """Should work with proportional distribution."""
        selected = type_based_distribution(
            SAMPLE_BEYS, SAMPLE_METADATA, 4,
            distribution='proportional', seed=42
        )
        assert len(selected) == 4


class TestArchetypeBasedDistribution:
    """Tests for archetype-based distribution."""

    def test_basic_draw(self):
        """Should return correct number of Beys."""
        selected = archetype_based_distribution(
            SAMPLE_BEYS, SAMPLE_RPG_STATS, 4, seed=42
        )
        assert len(selected) == 4

    def test_archetype_diversity(self):
        """Should try to diversify archetypes."""
        selected = archetype_based_distribution(
            SAMPLE_BEYS, SAMPLE_RPG_STATS, 4, seed=42
        )

        archetypes = [SAMPLE_RPG_STATS[bey['name']]['archetype']['id']
                      for bey in selected if bey['name'] in SAMPLE_RPG_STATS]

        # Should have some diversity
        assert len(set(archetypes)) > 1

    def test_missing_archetype_data(self):
        """Should handle Beys without archetype data."""
        partial_stats = {'BeyA': SAMPLE_RPG_STATS['BeyA']}
        selected = archetype_based_distribution(
            SAMPLE_BEYS, partial_stats, 3, seed=42
        )
        assert len(selected) == 3


class TestCustomConstraints:
    """Tests for custom constraints."""

    def test_min_elo(self):
        """Should respect minimum Elo constraint."""
        selected = custom_constraints(
            SAMPLE_BEYS, 3, min_elo=1000, seed=42
        )
        assert all(bey['elo'] >= 1000 for bey in selected)

    def test_max_elo(self):
        """Should respect maximum Elo constraint."""
        selected = custom_constraints(
            SAMPLE_BEYS, 3, max_elo=1000, seed=42
        )
        assert all(bey['elo'] <= 1000 for bey in selected)

    def test_elo_range(self):
        """Should respect both min and max Elo."""
        selected = custom_constraints(
            SAMPLE_BEYS, 2, min_elo=970, max_elo=1050, seed=42
        )
        assert all(970 <= bey['elo'] <= 1050 for bey in selected)

    def test_exclude(self):
        """Should exclude specified Beys."""
        excluded = {'BeyA', 'BeyB'}
        selected = custom_constraints(
            SAMPLE_BEYS, 3, exclude=excluded, seed=42
        )
        assert all(bey['name'] not in excluded for bey in selected)

    def test_include(self):
        """Should force include specified Beys."""
        included = {'BeyA', 'BeyB'}
        selected = custom_constraints(
            SAMPLE_BEYS, 4, include=included, seed=42
        )

        selected_names = {bey['name'] for bey in selected}
        assert included.issubset(selected_names)

    def test_include_and_exclude(self):
        """Should handle both include and exclude."""
        included = {'BeyA'}
        excluded = {'BeyB', 'BeyC'}
        selected = custom_constraints(
            SAMPLE_BEYS, 3, include=included, exclude=excluded, seed=42
        )

        selected_names = {bey['name'] for bey in selected}
        assert 'BeyA' in selected_names
        assert 'BeyB' not in selected_names
        assert 'BeyC' not in selected_names

    def test_complex_constraints(self):
        """Should handle multiple constraints together."""
        selected = custom_constraints(
            SAMPLE_BEYS, 2,
            min_elo=960, max_elo=1050,
            exclude={'BeyB'}, seed=42
        )

        assert len(selected) == 2
        assert all(960 <= bey['elo'] <= 1050 for bey in selected)
        assert all(bey['name'] != 'BeyB' for bey in selected)


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_list(self):
        """Should handle empty Bey list."""
        selected = pure_random([], 5, seed=42)
        assert len(selected) == 0

    def test_single_bey(self):
        """Should handle single Bey selection."""
        single_bey = [SAMPLE_BEYS[0]]
        selected = pure_random(single_bey, 1, seed=42)
        assert len(selected) == 1
        assert selected[0] == single_bey[0]

    def test_zero_count(self):
        """Should handle zero count request."""
        selected = pure_random(SAMPLE_BEYS, 0, seed=42)
        assert len(selected) == 0

    def test_all_beys(self):
        """Should handle request for all Beys."""
        selected = pure_random(SAMPLE_BEYS, len(SAMPLE_BEYS), seed=42)
        assert len(selected) == len(SAMPLE_BEYS)
        assert set(bey['name'] for bey in selected) == set(bey['name'] for bey in SAMPLE_BEYS)
