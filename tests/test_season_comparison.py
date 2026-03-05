"""
Unit tests for src/season_comparison.py

Tests cover:
- elo_win_probability
- rank_to_percentile
- build_season_league_table
- build_global_ranking
- build_pre_elo_map
- calculate_expected_wins
- compute_comparison (integration)
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'season'))

from season_comparison import (
    elo_win_probability,
    rank_to_percentile,
    build_season_league_table,
    build_global_ranking,
    build_pre_elo_map,
    calculate_expected_wins,
    compute_comparison,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_matches():
    """Minimal season matches (3 beys, Tier 1, Season S1)."""
    return [
        {"MatchID": "M001", "BeyA": "Alpha", "BeyB": "Beta",
         "ScoreA": "4", "ScoreB": "2", "MatchType": "season",
         "SeasonID": "S1", "Tier": "1", "Matchday": "1"},
        {"MatchID": "M002", "BeyA": "Alpha", "BeyB": "Gamma",
         "ScoreA": "2", "ScoreB": "4", "MatchType": "season",
         "SeasonID": "S1", "Tier": "1", "Matchday": "2"},
        {"MatchID": "M003", "BeyA": "Beta", "BeyB": "Gamma",
         "ScoreA": "4", "ScoreB": "3", "MatchType": "season",
         "SeasonID": "S1", "Tier": "1", "Matchday": "3"},
        # Non-season match – must be ignored everywhere
        {"MatchID": "M004", "BeyA": "Alpha", "BeyB": "Beta",
         "ScoreA": "4", "ScoreB": "0", "MatchType": "exhibition",
         "SeasonID": "", "Tier": "", "Matchday": ""},
    ]


@pytest.fixture
def sample_elo_history():
    return [
        {"MatchID": "M001", "BeyA": "Alpha", "BeyB": "Beta",
         "PreA": "1100", "PreB": "1050", "PostA": "1115", "PostB": "1035",
         "elo_arena_updated": "Xtreme", "MatchType": "season"},
        {"MatchID": "M002", "BeyA": "Alpha", "BeyB": "Gamma",
         "PreA": "1115", "PreB": "980", "PostA": "1100", "PostB": "995",
         "elo_arena_updated": "Xtreme", "MatchType": "season"},
        {"MatchID": "M003", "BeyA": "Beta", "BeyB": "Gamma",
         "PreA": "1035", "PreB": "995", "PostA": "1050", "PostB": "980",
         "elo_arena_updated": "Xtreme", "MatchType": "season"},
    ]


@pytest.fixture
def sample_leaderboard():
    return [
        {"Platz": "1", "Name": "Gamma", "ELO": "1120"},
        {"Platz": "2", "Name": "Alpha", "ELO": "1100"},
        {"Platz": "3", "Name": "Beta", "ELO": "1050"},
        {"Platz": "4", "Name": "Delta", "ELO": "1000"},
    ]


# ---------------------------------------------------------------------------
# elo_win_probability
# ---------------------------------------------------------------------------

class TestEloWinProbability:
    def test_equal_elo_returns_half(self):
        prob = elo_win_probability(1000, 1000)
        assert abs(prob - 0.5) < 1e-9

    def test_higher_elo_has_higher_probability(self):
        assert elo_win_probability(1100, 1000) > 0.5

    def test_lower_elo_has_lower_probability(self):
        assert elo_win_probability(900, 1000) < 0.5

    def test_probabilities_sum_to_one(self):
        p = elo_win_probability(1200, 1000)
        q = elo_win_probability(1000, 1200)
        assert abs(p + q - 1.0) < 1e-9

    def test_large_elo_gap(self):
        prob = elo_win_probability(2000, 1000)
        assert prob > 0.99


# ---------------------------------------------------------------------------
# rank_to_percentile
# ---------------------------------------------------------------------------

class TestRankToPercentile:
    def test_rank_1_of_1_returns_1(self):
        assert rank_to_percentile(1, 1) == 1.0

    def test_rank_1_of_n_returns_1(self):
        assert rank_to_percentile(1, 8) == 1.0

    def test_last_rank_returns_0(self):
        assert rank_to_percentile(8, 8) == 0.0

    def test_rank_2_of_8(self):
        result = rank_to_percentile(2, 8)
        expected = 1 - 1 / 7
        assert abs(result - expected) < 1e-9

    def test_rank_5_of_32(self):
        result = rank_to_percentile(5, 32)
        expected = 1 - 4 / 31
        assert abs(result - expected) < 1e-9

    def test_middle_rank(self):
        result = rank_to_percentile(3, 5)
        assert abs(result - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# build_season_league_table
# ---------------------------------------------------------------------------

class TestBuildSeasonLeagueTable:
    def test_returns_all_beys(self, sample_matches):
        table = build_season_league_table(sample_matches, "S1", 1)
        beys = {entry["bey"] for entry in table}
        assert beys == {"Alpha", "Beta", "Gamma"}

    def test_positions_are_sequential(self, sample_matches):
        table = build_season_league_table(sample_matches, "S1", 1)
        positions = [e["position"] for e in table]
        assert positions == list(range(1, len(table) + 1))

    def test_season_points_correct(self, sample_matches):
        table = build_season_league_table(sample_matches, "S1", 1)
        by_bey = {e["bey"]: e for e in table}
        # Alpha: won M001 (3 pts), lost M002 (0 pts) → 3
        # Beta:  lost M001 (0 pts), won M003 (3 pts) → 3
        # Gamma: won M002 (3 pts), lost M003 (0 pts) → 3
        for bey in ("Alpha", "Beta", "Gamma"):
            assert by_bey[bey]["season_points"] == 3

    def test_wrong_tier_returns_empty(self, sample_matches):
        table = build_season_league_table(sample_matches, "S1", 2)
        assert table == []

    def test_wrong_season_returns_empty(self, sample_matches):
        table = build_season_league_table(sample_matches, "S99", 1)
        assert table == []

    def test_exhibition_match_ignored(self, sample_matches):
        """M004 is exhibition; Alpha's dominant win should not count."""
        table = build_season_league_table(sample_matches, "S1", 1)
        by_bey = {e["bey"]: e for e in table}
        assert by_bey["Alpha"]["season_points"] == 3  # not 7

    def test_dominant_win_gives_4_points(self):
        matches = [
            {"MatchID": "M010", "BeyA": "X", "BeyB": "Y",
             "ScoreA": "4", "ScoreB": "0", "MatchType": "season",
             "SeasonID": "S1", "Tier": "1", "Matchday": "1"},
        ]
        table = build_season_league_table(matches, "S1", 1)
        by_bey = {e["bey"]: e for e in table}
        assert by_bey["X"]["season_points"] == 4
        assert by_bey["Y"]["season_points"] == 0

    def test_tiebreak_by_point_diff(self):
        """When season points are equal, higher point diff comes first."""
        matches = [
            # Alpha beats Beta 4-2; Alpha gets 3 pts
            {"MatchID": "M020", "BeyA": "Alpha", "BeyB": "Beta",
             "ScoreA": "4", "ScoreB": "2", "MatchType": "season",
             "SeasonID": "S2", "Tier": "1", "Matchday": "1"},
            # Beta beats Gamma 4-3; Beta gets 3 pts
            {"MatchID": "M021", "BeyA": "Beta", "BeyB": "Gamma",
             "ScoreA": "4", "ScoreB": "3", "MatchType": "season",
             "SeasonID": "S2", "Tier": "1", "Matchday": "2"},
            # Gamma beats Alpha 4-3; Gamma gets 3 pts
            {"MatchID": "M022", "BeyA": "Gamma", "BeyB": "Alpha",
             "ScoreA": "4", "ScoreB": "3", "MatchType": "season",
             "SeasonID": "S2", "Tier": "1", "Matchday": "3"},
        ]
        table = build_season_league_table(matches, "S2", 1)
        # All beys have 3 season points each (one win each)
        # Point diffs: Alpha = +2-1 = +1, Beta = -2+1 = -1, Gamma = +1-1... wait
        # Alpha: won vs Beta by 4-2 (+2), lost to Gamma 3-4 (-1) → diff +1, pts 3
        # Beta:  lost to Alpha 2-4 (-2), won vs Gamma 4-3 (+1) → diff -1, pts 3
        # Gamma: won vs Alpha 4-3 (+1), lost to Beta 3-4 (-1) → diff 0, pts 3
        # Ranking: Alpha (diff +1) > Gamma (diff 0) > Beta (diff -1)
        by_bey = {e["bey"]: e for e in table}
        assert by_bey["Alpha"]["season_points"] == 3
        assert by_bey["Beta"]["season_points"] == 3
        assert by_bey["Gamma"]["season_points"] == 3
        assert by_bey["Alpha"]["position"] == 1
        assert by_bey["Gamma"]["position"] == 2
        assert by_bey["Beta"]["position"] == 3


# ---------------------------------------------------------------------------
# build_global_ranking
# ---------------------------------------------------------------------------

class TestBuildGlobalRanking:
    def test_returns_all_beys(self, sample_leaderboard):
        ranking = build_global_ranking(sample_leaderboard)
        assert set(ranking.keys()) == {"Gamma", "Alpha", "Beta", "Delta"}

    def test_rank_and_elo_correct(self, sample_leaderboard):
        ranking = build_global_ranking(sample_leaderboard)
        assert ranking["Alpha"]["global_rank"] == 2
        assert ranking["Alpha"]["elo"] == 1100.0

    def test_empty_leaderboard(self):
        assert build_global_ranking([]) == {}


# ---------------------------------------------------------------------------
# build_pre_elo_map
# ---------------------------------------------------------------------------

class TestBuildPreEloMap:
    def test_captures_first_pre_elo(self, sample_elo_history):
        season_match_ids = {"M001", "M002", "M003"}
        pre_elo = build_pre_elo_map(sample_elo_history, season_match_ids)
        assert abs(pre_elo["Alpha"] - 1100.0) < 1e-6
        assert abs(pre_elo["Beta"] - 1050.0) < 1e-6
        assert abs(pre_elo["Gamma"] - 980.0) < 1e-6

    def test_non_season_match_ignored(self, sample_elo_history):
        pre_elo = build_pre_elo_map(sample_elo_history, set())
        assert pre_elo == {}

    def test_only_first_match_used(self, sample_elo_history):
        """Alpha's pre_elo for M001 is 1100; M002 has 1115 (post M001). First must win."""
        season_match_ids = {"M001", "M002", "M003"}
        pre_elo = build_pre_elo_map(sample_elo_history, season_match_ids)
        assert abs(pre_elo["Alpha"] - 1100.0) < 1e-6


# ---------------------------------------------------------------------------
# calculate_expected_wins
# ---------------------------------------------------------------------------

class TestCalculateExpectedWins:
    def test_expected_wins_between_0_and_match_count(self, sample_matches, sample_elo_history):
        season_match_ids = {"M001", "M002", "M003"}
        pre_elo = build_pre_elo_map(sample_elo_history, season_match_ids)
        expected = calculate_expected_wins(sample_matches, "S1", 1, pre_elo)
        for bey in ("Alpha", "Beta", "Gamma"):
            assert 0.0 <= expected[bey] <= 2.0  # each plays 2 season matches

    def test_expected_wins_sum_equals_total_matches(self, sample_matches, sample_elo_history):
        """Sum of expected wins must equal total season matches played (3)."""
        season_match_ids = {"M001", "M002", "M003"}
        pre_elo = build_pre_elo_map(sample_elo_history, season_match_ids)
        expected = calculate_expected_wins(sample_matches, "S1", 1, pre_elo)
        total = sum(expected.values())
        assert abs(total - 3.0) < 1e-6  # 3 matches, each contributes exactly 1.0

    def test_no_season_matches_returns_empty(self, sample_matches, sample_elo_history):
        pre_elo = {}
        expected = calculate_expected_wins(sample_matches, "S99", 1, pre_elo)
        assert expected == {}


# ---------------------------------------------------------------------------
# compute_comparison (integration)
# ---------------------------------------------------------------------------

class TestComputeComparison:
    def test_returns_seasons_key(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        assert "seasons" in result

    def test_season_s1_present(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        assert "S1" in result["seasons"]

    def test_tier_1_has_three_beys(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        assert len(beys) == 3

    def test_pdi_is_float(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        for b in beys:
            if b["pdi"] is not None:
                assert isinstance(b["pdi"], float)

    def test_pve_equals_actual_minus_expected(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        for b in beys:
            diff = b["actual_wins"] - b["expected_wins"]
            assert abs(b["pve"] - diff) < 1e-4

    def test_season_percentile_range(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        for b in beys:
            assert 0.0 <= b["season_percentile"] <= 1.0

    def test_global_percentile_range(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        for b in beys:
            if b["global_percentile"] is not None:
                assert 0.0 <= b["global_percentile"] <= 1.0

    def test_tier_strength_present(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        ts = result["seasons"]["S1"]["tiers"]["1"]["tier_strength"]
        assert "avg_global_percentile" in ts
        assert "avg_elo" in ts
        assert "avg_pdi" in ts

    def test_season_filter(self, sample_matches, sample_elo_history, sample_leaderboard):
        result = compute_comparison(
            sample_matches, sample_elo_history, sample_leaderboard,
            season_id="S99"
        )
        assert result["seasons"] == {}

    def test_exhibition_not_counted(self, sample_matches, sample_elo_history, sample_leaderboard):
        """Alpha's dominant win M004 is exhibition and must not contribute to season stats."""
        result = compute_comparison(sample_matches, sample_elo_history, sample_leaderboard)
        beys = result["seasons"]["S1"]["tiers"]["1"]["beys"]
        by_bey = {b["bey"]: b for b in beys}
        # Alpha has 1 season win (M001)
        assert by_bey["Alpha"]["actual_wins"] == 1
