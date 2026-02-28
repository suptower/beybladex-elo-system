"""
Unit tests for season_meta_analytics.py module.

Tests cover all four analytical features:
  1. Archetype-Based Season Analytics
  2. Extended Power Ranking (Form-Based)
  3. Title Probability Model (Monte Carlo)
  4. Tier Elo Distribution & Strength Tracking
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from season_meta_analytics import (
    # Feature 1
    calculate_archetype_season_performance,
    calculate_archetype_matchup_matrix_season,
    calculate_archetype_meta_evolution,
    calculate_archetype_stability_index,
    # Feature 2
    calculate_power_score,
    generate_power_ranking,
    DEFAULT_POWER_SCORE_WEIGHTS,
    # Feature 3
    calculate_win_probability,
    simulate_season_completion,
    calculate_title_probabilities,
    # Feature 4
    calculate_tier_elo_timeseries,
    calculate_tier_strength_index,
    calculate_tier_competitiveness_index,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rpg_stats():
    """Minimal RPG stats with two archetypes."""
    return {
        "BeyA": {
            "archetype": {
                "id": "glass_cannon",
                "name": "Glass Cannon",
                "category": "offense",
                "icon": "💥",
                "color": "#ef4444",
            }
        },
        "BeyB": {
            "archetype": {
                "id": "glass_cannon",
                "name": "Glass Cannon",
                "category": "offense",
                "icon": "💥",
                "color": "#ef4444",
            }
        },
        "BeyC": {
            "archetype": {
                "id": "iron_wall",
                "name": "Iron Wall",
                "category": "defense",
                "icon": "🛡️",
                "color": "#3b82f6",
            }
        },
        "BeyD": {
            "archetype": {
                "id": "iron_wall",
                "name": "Iron Wall",
                "category": "defense",
                "icon": "🛡️",
                "color": "#3b82f6",
            }
        },
    }


def _make_season_match(mid, bey_a, bey_b, score_a, score_b,
                       matchday=1, tier=1, season_id="S1"):
    return {
        "match_id": mid,
        "bey_a": bey_a,
        "bey_b": bey_b,
        "score_a": score_a,
        "score_b": score_b,
        "match_type": "season",
        "season_id": season_id,
        "tier": tier,
        "matchday": matchday,
    }


def _make_elo_history(match_id, bey_a, elo_a, bey_b, elo_b):
    """Build a minimal elo_history dict entry for a single match."""
    return {match_id: {bey_a: elo_a, bey_b: elo_b}}


@pytest.fixture
def season_matches():
    """6 season matches providing each bey ≥ MIN_SEASON_MATCHES appearances."""
    return [
        _make_season_match("M001", "BeyA", "BeyB", 4, 2, matchday=1),
        _make_season_match("M002", "BeyA", "BeyC", 4, 1, matchday=1),
        _make_season_match("M003", "BeyA", "BeyD", 4, 0, matchday=2),
        _make_season_match("M004", "BeyB", "BeyC", 2, 4, matchday=2),
        _make_season_match("M005", "BeyB", "BeyD", 4, 3, matchday=3),
        _make_season_match("M006", "BeyC", "BeyD", 4, 2, matchday=3),
    ]


@pytest.fixture
def exhibition_match():
    return {
        "match_id": "E001",
        "bey_a": "BeyA",
        "bey_b": "BeyB",
        "score_a": 4,
        "score_b": 2,
        "match_type": "exhibition",
        "season_id": "",
        "tier": None,
        "matchday": None,
    }


# ===========================================================================
# Feature 1: Archetype-Based Season Analytics
# ===========================================================================

class TestCalculateArchetypeSeasonPerformance:

    def test_returns_correct_archetypes(self, season_matches, rpg_stats):
        result = calculate_archetype_season_performance(season_matches, rpg_stats)
        # Both archetypes should be present (each bey has 3 season matches)
        assert "glass_cannon" in result
        assert "iron_wall" in result

    def test_filters_exhibition_matches(self, season_matches, rpg_stats, exhibition_match):
        matches_with_exhibition = season_matches + [exhibition_match]
        result = calculate_archetype_season_performance(matches_with_exhibition, rpg_stats)
        # Stats should be the same as without the exhibition match
        result_no_exhibition = calculate_archetype_season_performance(season_matches, rpg_stats)
        assert result == result_no_exhibition

    def test_filters_unknown_archetypes(self, season_matches):
        rpg_unknown = {
            "BeyA": {"archetype": {"id": "unknown", "name": "Unknown",
                                   "category": "unknown", "icon": "❓", "color": "#000"}},
            "BeyC": {"archetype": {"id": "glass_cannon", "name": "Glass Cannon",
                                   "category": "offense", "icon": "💥", "color": "#ef4444"}},
            "BeyD": {"archetype": {"id": "glass_cannon", "name": "Glass Cannon",
                                   "category": "offense", "icon": "💥", "color": "#ef4444"}},
        }
        result = calculate_archetype_season_performance(season_matches, rpg_unknown)
        assert "unknown" not in result

    def test_requires_minimum_matches(self, rpg_stats):
        # Provide fewer matches than MIN_SEASON_MATCHES per bey
        few_matches = [
            _make_season_match("M001", "BeyA", "BeyB", 4, 2),
            _make_season_match("M002", "BeyA", "BeyC", 4, 1),
        ]
        result = calculate_archetype_season_performance(few_matches, rpg_stats)
        # BeyA has 2 matches < MIN_SEASON_MATCHES(3); BeyB,C,D have 1 each
        assert len(result) == 0

    def test_season_filter(self, rpg_stats):
        matches = [
            _make_season_match("M001", "BeyA", "BeyB", 4, 2, season_id="S1"),
            _make_season_match("M002", "BeyA", "BeyC", 4, 1, season_id="S1"),
            _make_season_match("M003", "BeyA", "BeyD", 4, 0, season_id="S1"),
            _make_season_match("M004", "BeyC", "BeyD", 4, 2, season_id="S2"),
            _make_season_match("M005", "BeyC", "BeyA", 4, 0, season_id="S2"),
            _make_season_match("M006", "BeyD", "BeyB", 4, 0, season_id="S2"),
        ]
        result_s1 = calculate_archetype_season_performance(matches, rpg_stats, season_id="S1")
        result_s2 = calculate_archetype_season_performance(matches, rpg_stats, season_id="S2")
        # Should only include archetypes from the filtered season
        assert result_s1 != result_s2

    def test_output_structure(self, season_matches, rpg_stats):
        result = calculate_archetype_season_performance(season_matches, rpg_stats)
        for arch_id, data in result.items():
            assert "avg_winrate" in data
            assert "avg_points_per_round" in data
            assert "stability_index" in data
            assert "bey_count" in data
            assert "total_season_matches" in data
            assert 0.0 <= data["avg_winrate"] <= 1.0

    def test_winrate_calculation(self, rpg_stats):
        """BeyA wins all 3 matches → glass_cannon avg_winrate should reflect that."""
        matches = [
            _make_season_match("M001", "BeyA", "BeyB", 4, 2),
            _make_season_match("M002", "BeyA", "BeyB", 4, 1),
            _make_season_match("M003", "BeyA", "BeyB", 4, 0),
        ]
        # Only BeyA and BeyB have matches; BeyB loses all 3
        result = calculate_archetype_season_performance(matches, rpg_stats)
        if "glass_cannon" in result:
            # BeyA: 3W 0L = 1.0; BeyB: 0W 3L = 0.0 → combined = 3/6 = 0.5
            assert abs(result["glass_cannon"]["avg_winrate"] - 0.5) < 0.01


class TestCalculateArchetypeMatchupMatrixSeason:

    def test_basic_matrix(self, season_matches, rpg_stats):
        result = calculate_archetype_matchup_matrix_season(season_matches, rpg_stats)
        assert "glass_cannon" in result or "iron_wall" in result

    def test_ignores_exhibition_matches(self, season_matches, rpg_stats, exhibition_match):
        result_with = calculate_archetype_matchup_matrix_season(
            season_matches + [exhibition_match], rpg_stats)
        result_without = calculate_archetype_matchup_matrix_season(season_matches, rpg_stats)
        assert result_with == result_without

    def test_winrate_sums_correctly(self, rpg_stats):
        """2 wins for glass_cannon vs iron_wall and 1 loss → winrate ≈ 0.6667."""
        matches = [
            _make_season_match("M001", "BeyA", "BeyC", 4, 2),
            _make_season_match("M002", "BeyA", "BeyC", 4, 1),
            _make_season_match("M003", "BeyC", "BeyA", 4, 2),
        ]
        result = calculate_archetype_matchup_matrix_season(matches, rpg_stats)
        if "glass_cannon" in result and "iron_wall" in result["glass_cannon"]:
            assert abs(result["glass_cannon"]["iron_wall"]["winrate"] - 0.6667) < 0.01

    def test_unknown_archetype_excluded(self, season_matches):
        rpg_partial = {
            "BeyA": {"archetype": {"id": "glass_cannon", "name": "Glass Cannon",
                                   "category": "offense", "icon": "💥", "color": "#ef4444"}},
            "BeyC": {"archetype": {"id": "unknown", "name": "Unknown",
                                   "category": "unknown", "icon": "❓", "color": "#000"}},
        }
        result = calculate_archetype_matchup_matrix_season(season_matches, rpg_partial)
        for arch, opponents in result.items():
            assert arch != "unknown"
            for opp in opponents:
                assert opp != "unknown"


class TestCalculateArchetypeMetaEvolution:

    def test_returns_matchday_keys(self, season_matches, rpg_stats):
        result = calculate_archetype_meta_evolution(season_matches, rpg_stats)
        assert 1 in result
        assert 2 in result
        assert 3 in result

    def test_win_shares_sum_to_one(self, season_matches, rpg_stats):
        result = calculate_archetype_meta_evolution(season_matches, rpg_stats)
        for md, shares in result.items():
            total = sum(shares.values())
            assert abs(total - 1.0) < 0.01, f"Matchday {md} shares don't sum to 1: {total}"

    def test_filters_exhibition(self, season_matches, rpg_stats, exhibition_match):
        result_with = calculate_archetype_meta_evolution(
            season_matches + [exhibition_match], rpg_stats)
        result_without = calculate_archetype_meta_evolution(season_matches, rpg_stats)
        assert result_with == result_without

    def test_empty_matches_returns_empty(self, rpg_stats):
        result = calculate_archetype_meta_evolution([], rpg_stats)
        assert result == {}


class TestCalculateArchetypeStabilityIndex:

    def test_basic_stability(self, season_matches, rpg_stats):
        arch_stats = calculate_archetype_season_performance(season_matches, rpg_stats)
        result = calculate_archetype_stability_index(arch_stats, season_matches, rpg_stats)
        for arch_id in arch_stats:
            assert arch_id in result
            assert "stability_index" in result[arch_id]
            assert result[arch_id]["stability_index"] >= 0.0

    def test_identical_bey_winrates_gives_zero_stability(self, rpg_stats):
        """Two Beys with identical winrates → stability index = 0."""
        matches = [
            _make_season_match("M001", "BeyA", "BeyC", 4, 2),
            _make_season_match("M002", "BeyA", "BeyD", 4, 2),
            _make_season_match("M003", "BeyA", "BeyC", 4, 2),
            _make_season_match("M004", "BeyB", "BeyC", 4, 2),
            _make_season_match("M005", "BeyB", "BeyD", 4, 2),
            _make_season_match("M006", "BeyB", "BeyC", 4, 2),
        ]
        arch_stats = calculate_archetype_season_performance(matches, rpg_stats)
        result = calculate_archetype_stability_index(arch_stats, matches, rpg_stats)
        if "glass_cannon" in result:
            # BeyA and BeyB both win all their matches → same winrate → std=0
            assert result["glass_cannon"]["stability_index"] == 0.0


# ===========================================================================
# Feature 2: Extended Power Ranking
# ===========================================================================

class TestDefaultPowerScoreWeights:

    def test_weights_sum_to_one(self):
        total = sum(DEFAULT_POWER_SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        for k, v in DEFAULT_POWER_SCORE_WEIGHTS.items():
            assert v > 0, f"Weight for '{k}' is not positive"

    def test_required_keys_present(self):
        required = {"season_winrate", "points_per_round", "global_elo_percentile",
                    "round_diff_per_match", "recent_form"}
        assert required <= set(DEFAULT_POWER_SCORE_WEIGHTS.keys())


class TestCalculatePowerScore:

    def _base_kwargs(self):
        return dict(
            bey="TestBey",
            season_wins=5,
            season_matches=10,
            total_points_scored=20,
            total_rounds=30,
            round_diff=5,
            global_elo=1100.0,
            recent_results=[True, True, True],
            all_elos=[900.0, 950.0, 1000.0, 1050.0, 1100.0],
        )

    def test_score_in_range(self):
        score = calculate_power_score(**self._base_kwargs())
        assert 0.0 <= score <= 100.0

    def test_higher_elo_increases_score(self):
        kwargs = self._base_kwargs()
        low_elo_score = calculate_power_score(**{**kwargs, "global_elo": 900.0})
        high_elo_score = calculate_power_score(**{**kwargs, "global_elo": 1100.0})
        assert high_elo_score > low_elo_score

    def test_higher_winrate_increases_score(self):
        base = self._base_kwargs()
        low_wr = calculate_power_score(**{**base, "season_wins": 2, "season_matches": 10})
        high_wr = calculate_power_score(**{**base, "season_wins": 9, "season_matches": 10})
        assert high_wr > low_wr

    def test_better_recent_form_increases_score(self):
        base = self._base_kwargs()
        bad_form = calculate_power_score(**{**base, "recent_results": [False, False, False]})
        good_form = calculate_power_score(**{**base, "recent_results": [True, True, True]})
        assert good_form > bad_form

    def test_custom_weights_applied(self):
        """Giving all weight to elo percentile changes the score."""
        base = self._base_kwargs()
        all_elo = calculate_power_score(**{
            **base,
            "weights": {"season_winrate": 0, "points_per_round": 0,
                        "global_elo_percentile": 1.0, "round_diff_per_match": 0,
                        "recent_form": 0},
        })
        all_wr = calculate_power_score(**{
            **base,
            "weights": {"season_winrate": 1.0, "points_per_round": 0,
                        "global_elo_percentile": 0, "round_diff_per_match": 0,
                        "recent_form": 0},
        })
        assert all_elo != all_wr

    def test_no_matches_returns_zero_components(self):
        score = calculate_power_score(
            bey="TestBey", season_wins=0, season_matches=0,
            total_points_scored=0, total_rounds=0, round_diff=0,
            global_elo=1000.0, recent_results=[], all_elos=[1000.0],
        )
        assert 0.0 <= score <= 100.0


class TestGeneratePowerRanking:

    def test_returns_sorted_by_power_score(self, season_matches, rpg_stats):
        bey_season_data = {
            "BeyA": {"wins": 3, "losses": 0, "matches": 3,
                     "points_scored": 12, "rounds": 15, "round_diff": 9},
            "BeyC": {"wins": 2, "losses": 1, "matches": 3,
                     "points_scored": 9, "rounds": 15, "round_diff": 3},
        }
        global_lb = {
            "BeyA": {"elo": 1100},
            "BeyB": {"elo": 1050},
            "BeyC": {"elo": 1000},
            "BeyD": {"elo": 950},
        }
        result = generate_power_ranking(bey_season_data, global_lb, season_matches)
        assert len(result) > 0
        for i in range(len(result) - 1):
            assert result[i]["power_score"] >= result[i + 1]["power_score"]

    def test_rank_delta_computation(self, season_matches):
        bey_season_data = {
            "BeyA": {"wins": 3, "losses": 0, "matches": 3,
                     "points_scored": 12, "rounds": 15, "round_diff": 9},
            "BeyB": {"wins": 0, "losses": 3, "matches": 3,
                     "points_scored": 3, "rounds": 15, "round_diff": -9},
        }
        global_lb = {
            "BeyA": {"elo": 900},   # ELO rank: 2nd
            "BeyB": {"elo": 1100},  # ELO rank: 1st
        }
        result = generate_power_ranking(bey_season_data, global_lb, season_matches)
        ranked_beys = {r["bey"]: r for r in result}
        if "BeyA" in ranked_beys and "BeyB" in ranked_beys:
            # BeyA should have better power rank despite lower ELO
            assert ranked_beys["BeyA"]["power_rank"] < ranked_beys["BeyB"]["power_rank"]

    def test_skips_beys_below_min_matches(self, season_matches):
        bey_season_data = {
            "BeyA": {"wins": 1, "losses": 0, "matches": 1,
                     "points_scored": 4, "rounds": 6, "round_diff": 2},
        }
        global_lb = {"BeyA": {"elo": 1000}}
        result = generate_power_ranking(bey_season_data, global_lb, season_matches)
        # 1 match < MIN_SEASON_MATCHES(3) → not included
        assert len(result) == 0


# ===========================================================================
# Feature 3: Title Probability Model
# ===========================================================================

class TestCalculateWinProbability:

    def test_equal_elo_returns_half(self):
        p = calculate_win_probability(1000, 1000)
        assert abs(p - 0.5) < 0.05

    def test_higher_elo_favoured(self):
        p = calculate_win_probability(1200, 1000)
        assert p > 0.5

    def test_lower_elo_unfavoured(self):
        p = calculate_win_probability(1000, 1200)
        assert p < 0.5

    def test_probability_in_bounds(self):
        for elo_a, elo_b in [(800, 1200), (1200, 800), (1000, 1000), (1500, 500)]:
            p = calculate_win_probability(elo_a, elo_b)
            assert 0.0 < p < 1.0

    def test_symmetry(self):
        p_a = calculate_win_probability(1100, 1000, use_form_adjustment=False)
        p_b = calculate_win_probability(1000, 1100, use_form_adjustment=False)
        assert abs(p_a + p_b - 1.0) < 0.0001

    def test_form_adjustment_shifts_probability(self):
        # Without form adjustment
        p_base = calculate_win_probability(1000, 1000, use_form_adjustment=False)
        # With form: A has perfect recent form, B has none
        p_adj = calculate_win_probability(
            1000, 1000, recent_form_a=1.0, recent_form_b=0.0,
            use_form_adjustment=True)
        assert p_adj > p_base

    def test_form_modifier_bounded(self):
        """Extreme form values should not push probability outside safe range."""
        p = calculate_win_probability(1000, 1000, recent_form_a=1.0, recent_form_b=0.0)
        assert 0.0 < p < 1.0


class TestSimulateSeasonCompletion:

    def _standings(self):
        return {
            "BeyA": {"season_points": 6, "point_diff": 4, "points_for": 12},
            "BeyB": {"season_points": 3, "point_diff": 0, "points_for": 8},
            "BeyC": {"season_points": 0, "point_diff": -4, "points_for": 4},
        }

    def _remaining(self):
        return [("BeyA", "BeyB"), ("BeyB", "BeyC"), ("BeyA", "BeyC")]

    def _elos(self):
        return {"BeyA": 1100.0, "BeyB": 1000.0, "BeyC": 900.0}

    def test_deterministic_with_seed(self):
        r1 = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(), seed=42)
        r2 = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(), seed=42)
        assert r1 == r2

    def test_different_seeds_different_results(self):
        r1 = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(), seed=42)
        r2 = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(), seed=99)
        # Very likely to differ with 10k simulations
        assert r1 != r2

    def test_position_counts_sum_to_n_simulations(self):
        n = 1000
        result = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(),
            n_simulations=n, seed=0)
        for bey, counts in result.items():
            assert sum(counts) == n

    def test_all_beys_have_position_distributions(self):
        result = simulate_season_completion(
            self._standings(), self._remaining(), self._elos(), n_simulations=100, seed=1)
        for bey in self._standings():
            assert bey in result

    def test_empty_standings_returns_empty(self):
        result = simulate_season_completion({}, [], {})
        assert result == {}

    def test_dominant_bey_wins_more_often(self):
        """A Bey with much higher Elo and more points should win most simulations."""
        standings = {
            "Strong": {"season_points": 15, "point_diff": 20, "points_for": 40},
            "Weak": {"season_points": 0, "point_diff": -20, "points_for": 10},
        }
        elos = {"Strong": 1400.0, "Weak": 800.0}
        remaining = [("Strong", "Weak")]
        result = simulate_season_completion(standings, remaining, elos,
                                            n_simulations=1000, seed=7)
        strong_wins = result["Strong"][0]  # position 1 count
        assert strong_wins > 900  # should win nearly all simulations


class TestCalculateTitleProbabilities:

    def _position_counts(self):
        return {
            "BeyA": [700, 200, 100],
            "BeyB": [200, 600, 200],
            "BeyC": [100, 200, 700],
        }

    def test_title_prob_matches_first_position_count(self):
        result = calculate_title_probabilities(self._position_counts(), n_simulations=1000)
        probs = {r["bey"]: r["title_prob"] for r in result}
        assert abs(probs["BeyA"] - 70.0) < 0.1
        assert abs(probs["BeyB"] - 20.0) < 0.1

    def test_sorted_by_title_prob_descending(self):
        result = calculate_title_probabilities(self._position_counts(), n_simulations=1000)
        probs = [r["title_prob"] for r in result]
        assert probs == sorted(probs, reverse=True)

    def test_promotion_prob_includes_top_spots(self):
        result = calculate_title_probabilities(
            self._position_counts(), n_simulations=1000, promotion_spots=2)
        probs = {r["bey"]: r for r in result}
        # BeyA: position 1 = 70%, position 2 = 20% → promo ≈ 90%
        assert abs(probs["BeyA"]["promotion_prob"] - 90.0) < 0.1

    def test_top3_prob_is_sum_of_top3_positions(self):
        result = calculate_title_probabilities(self._position_counts(), n_simulations=1000)
        for r in result:
            expected_top3 = sum(r["position_distribution"][:3])
            assert abs(r["top3_prob"] - expected_top3) < 0.1

    def test_empty_input_returns_empty(self):
        result = calculate_title_probabilities({}, n_simulations=1000)
        assert result == []


# ===========================================================================
# Feature 4: Tier Elo Distribution & Strength Tracking
# ===========================================================================


class TestCalculateTierEloTimeseries:

    def _matches(self):
        return [
            {"match_id": "M001", "bey_a": "BeyA", "bey_b": "BeyB",
             "score_a": 4, "score_b": 2, "match_type": "season",
             "season_id": "S1", "tier": 1, "matchday": 1},
            {"match_id": "M002", "bey_a": "BeyC", "bey_b": "BeyD",
             "score_a": 4, "score_b": 1, "match_type": "season",
             "season_id": "S1", "tier": 2, "matchday": 1},
            {"match_id": "M003", "bey_a": "BeyA", "bey_b": "BeyC",
             "score_a": 4, "score_b": 3, "match_type": "season",
             "season_id": "S1", "tier": 1, "matchday": 2},
        ]

    def _elo_history(self):
        h = {}
        h.update(_make_elo_history("M001", "BeyA", 1100.0, "BeyB", 1050.0))
        h.update(_make_elo_history("M002", "BeyC", 980.0, "BeyD", 960.0))
        h.update(_make_elo_history("M003", "BeyA", 1110.0, "BeyC", 970.0))
        return h

    def test_returns_tier_and_matchday_keys(self):
        result = calculate_tier_elo_timeseries(self._matches(), self._elo_history())
        assert 1 in result
        assert 2 in result
        assert 1 in result[1]  # matchday 1 in tier 1
        assert 2 in result[1]  # matchday 2 in tier 1

    def test_stats_keys_present(self):
        result = calculate_tier_elo_timeseries(self._matches(), self._elo_history())
        for tier_data in result.values():
            for md_stats in tier_data.values():
                assert "mean" in md_stats
                assert "median" in md_stats
                assert "max" in md_stats
                assert "min" in md_stats
                assert "iqr" in md_stats

    def test_min_lte_mean_lte_max(self):
        result = calculate_tier_elo_timeseries(self._matches(), self._elo_history())
        for tier_data in result.values():
            for md_stats in tier_data.values():
                assert md_stats["min"] <= md_stats["mean"] <= md_stats["max"]

    def test_filters_exhibition_matches(self):
        matches_with_exh = self._matches() + [{
            "match_id": "E001", "bey_a": "BeyA", "bey_b": "BeyB",
            "score_a": 4, "score_b": 2, "match_type": "exhibition",
            "season_id": "", "tier": 1, "matchday": 3,
        }]
        elo_hist = dict(self._elo_history())
        elo_hist["E001"] = {"BeyA": 1200.0, "BeyB": 800.0}
        result_with = calculate_tier_elo_timeseries(matches_with_exh, elo_hist)
        result_without = calculate_tier_elo_timeseries(self._matches(), self._elo_history())
        assert result_with == result_without

    def test_season_id_filter(self):
        matches = self._matches() + [{
            "match_id": "M010", "bey_a": "BeyA", "bey_b": "BeyB",
            "score_a": 4, "score_b": 2, "match_type": "season",
            "season_id": "S2", "tier": 1, "matchday": 1,
        }]
        elo_hist = dict(self._elo_history())
        elo_hist["M010"] = {"BeyA": 999.0, "BeyB": 888.0}

        result_s1 = calculate_tier_elo_timeseries(matches, elo_hist, season_id="S1")
        result_all = calculate_tier_elo_timeseries(matches, elo_hist)
        # S1 filter should give fewer data points
        if 1 in result_s1 and 1 in result_all:
            s1_vals = sum(len(v) for v in result_s1[1].values())
            all_vals = sum(len(v) for v in result_all[1].values())
            # Not strictly fewer (depends on matchday overlap) but should be different
            assert s1_vals <= all_vals


class TestCalculateTierStrengthIndex:

    def test_higher_mean_elo_tier_has_higher_strength(self):
        tier_ts = {
            1: {1: {"mean": 1100.0, "median": 1100.0, "max": 1200.0,
                    "min": 1000.0, "q1": 1050.0, "q3": 1150.0, "iqr": 100.0}},
            2: {1: {"mean": 1000.0, "median": 1000.0, "max": 1100.0,
                    "min": 900.0, "q1": 950.0, "q3": 1050.0, "iqr": 100.0}},
        }
        result = calculate_tier_strength_index(tier_ts)
        assert result[1] > result[2]

    def test_returns_dict_of_tier_to_float(self):
        tier_ts = {
            1: {1: {"mean": 1050.0, "median": 1050.0, "max": 1100.0,
                    "min": 1000.0, "q1": 1025.0, "q3": 1075.0, "iqr": 50.0}},
        }
        result = calculate_tier_strength_index(tier_ts)
        assert 1 in result
        assert isinstance(result[1], float)

    def test_empty_input(self):
        assert calculate_tier_strength_index({}) == {}


class TestCalculateTierCompetitivenessIndex:

    def test_lower_iqr_means_more_competitive(self):
        tier_ts = {
            1: {1: {"mean": 1000.0, "median": 1000.0, "max": 1050.0,
                    "min": 950.0, "q1": 975.0, "q3": 1025.0, "iqr": 50.0}},
            2: {1: {"mean": 1000.0, "median": 1000.0, "max": 1200.0,
                    "min": 800.0, "q1": 900.0, "q3": 1100.0, "iqr": 200.0}},
        }
        result = calculate_tier_competitiveness_index(tier_ts)
        # Tier 1 has lower IQR → more competitive
        assert result[1] < result[2]

    def test_returns_dict_of_tier_to_float(self):
        tier_ts = {
            1: {1: {"mean": 1000.0, "median": 1000.0, "max": 1100.0,
                    "min": 900.0, "q1": 950.0, "q3": 1050.0, "iqr": 100.0}},
        }
        result = calculate_tier_competitiveness_index(tier_ts)
        assert 1 in result
        assert isinstance(result[1], float)

    def test_empty_input(self):
        assert calculate_tier_competitiveness_index({}) == {}
