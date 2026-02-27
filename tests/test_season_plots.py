"""
Tests for the season_plots visualization module.
"""
import json
import os
import sys
import tempfile

import pandas as pd
import pytest

# Add parent src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'visualization'))

import matplotlib
matplotlib.use('Agg')  # non-interactive backend for tests

import season_plots  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_matches():
    """Minimal season matches dataframe for tier 1."""
    return pd.DataFrame([
        {"MatchID": "M001", "BeyA": "Alpha", "BeyB": "Beta", "ScoreA": 4, "ScoreB": 2,
         "MatchType": "season", "SeasonID": "S1", "Tier": 1, "Matchday": 1},
        {"MatchID": "M002", "BeyA": "Alpha", "BeyB": "Gamma", "ScoreA": 2, "ScoreB": 4,
         "MatchType": "season", "SeasonID": "S1", "Tier": 1, "Matchday": 2},
        {"MatchID": "M003", "BeyA": "Beta", "BeyB": "Gamma", "ScoreA": 4, "ScoreB": 3,
         "MatchType": "season", "SeasonID": "S1", "Tier": 1, "Matchday": 3},
        # A non-season match that should be ignored
        {"MatchID": "M004", "BeyA": "Alpha", "BeyB": "Beta", "ScoreA": 3, "ScoreB": 4,
         "MatchType": "exhibition", "SeasonID": None, "Tier": None, "Matchday": None},
    ])


@pytest.fixture
def sample_rounds():
    """Minimal round data for M001–M003."""
    return pd.DataFrame([
        {"match_id": "M001", "round_number": 1, "winner": "Alpha", "finish_type": "burst", "points_awarded": 2},
        {"match_id": "M001", "round_number": 2, "winner": "Alpha", "finish_type": "spin", "points_awarded": 1},
        {"match_id": "M001", "round_number": 3, "winner": "Alpha", "finish_type": "extreme", "points_awarded": 3},
        {"match_id": "M001", "round_number": 4, "winner": "Beta", "finish_type": "pocket", "points_awarded": 2},
        {"match_id": "M001", "round_number": 5, "winner": "Beta", "finish_type": "spin", "points_awarded": 1},
        {"match_id": "M002", "round_number": 1, "winner": "Gamma", "finish_type": "burst", "points_awarded": 2},
        {"match_id": "M002", "round_number": 2, "winner": "Gamma", "finish_type": "spin", "points_awarded": 1},
        {"match_id": "M002", "round_number": 3, "winner": "Alpha", "finish_type": "spin", "points_awarded": 1},
        {"match_id": "M003", "round_number": 1, "winner": "Beta", "finish_type": "spin", "points_awarded": 1},
        {"match_id": "M003", "round_number": 2, "winner": "Beta", "finish_type": "pocket", "points_awarded": 2},
        {"match_id": "M003", "round_number": 3, "winner": "Gamma", "finish_type": "spin", "points_awarded": 1},
    ])


@pytest.fixture
def sample_stats_json():
    """Minimal season statistics JSON for radar chart."""
    return {
        "phase": "all",
        "statistics": {
            "Alpha": {
                "match_win_rate": 50.0,
                "points_per_round": 1.2,
                "burst_win_rate": 30.0,
                "defensive_stability_index": 0.9,
                "clutch_win_rate": 20.0,
            },
            "Beta": {
                "match_win_rate": 66.67,
                "points_per_round": 1.1,
                "burst_win_rate": 0.0,
                "defensive_stability_index": 0.85,
                "clutch_win_rate": 0.0,
            },
            "Gamma": {
                "match_win_rate": 33.33,
                "points_per_round": 0.9,
                "burst_win_rate": 50.0,
                "defensive_stability_index": 1.0,
                "clutch_win_rate": 0.0,
            },
        },
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestBuildPositionTable:
    """Tests for the position-table helper."""

    def test_returns_dict_of_dicts(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.build_position_table(season_only, tier=1)
        assert isinstance(result, dict)
        for md, standings in result.items():
            assert isinstance(standings, dict)

    def test_correct_matchdays(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.build_position_table(season_only, tier=1)
        assert set(result.keys()) == {1, 2, 3}

    def test_all_beys_ranked(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.build_position_table(season_only, tier=1)
        # After matchday 3 all three beys should have a ranking
        assert set(result[3].keys()) == {"Alpha", "Beta", "Gamma"}

    def test_winner_ranked_first(self, sample_matches):
        """After matchday 1, Alpha (winner) should be ranked #1."""
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.build_position_table(season_only, tier=1)
        # Alpha won M001 → 3 pts, Beta lost → 0 pts (Gamma not played yet → 0 pts)
        assert result[1]["Alpha"] == 1

    def test_empty_result_for_wrong_tier(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.build_position_table(season_only, tier=99)
        assert result == {}


class TestPlotFunctions:
    """Smoke tests: each plot function should run without raising errors."""

    def test_bump_chart(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_bump_chart(season_only, tier=1, outdir=outdir, season_id="S1")
        assert os.path.exists(os.path.join(outdir, "bump_chart_tier1.png"))

    def test_cumulative_points(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_cumulative_points(season_only, tier=1, outdir=outdir, season_id="S1")
        assert os.path.exists(os.path.join(outdir, "cumulative_points_tier1.png"))

    def test_finish_distribution(self, sample_matches, sample_rounds, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_finish_distribution(
            season_only, sample_rounds, tier=1, outdir=outdir, season_id="S1"
        )
        assert os.path.exists(os.path.join(outdir, "finish_distribution_tier1.png"))

    def test_h2h_matrix(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_h2h_matrix(season_only, tier=1, outdir=outdir, season_id="S1")
        assert os.path.exists(os.path.join(outdir, "h2h_matrix_tier1.png"))

    def test_points_per_match(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_points_per_match(season_only, tier=1, outdir=outdir, season_id="S1")
        assert os.path.exists(os.path.join(outdir, "points_per_match_tier1.png"))

    def test_radar_chart(self, sample_stats_json, tmp_path):
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        tier_beys = ["Alpha", "Beta", "Gamma"]
        season_plots.plot_radar_chart(
            sample_stats_json, tier_beys=tier_beys, tier=1,
            outdir=outdir, season_id="S1"
        )
        assert os.path.exists(os.path.join(outdir, "radar_chart_tier1.png"))

    def test_empty_tier_skips_gracefully(self, sample_matches, tmp_path):
        """Plot functions should not raise errors when given an empty tier."""
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        # Tier 99 has no matches – functions should return silently
        season_plots.plot_bump_chart(season_only, tier=99, outdir=outdir, season_id="S1")
        season_plots.plot_cumulative_points(season_only, tier=99, outdir=outdir, season_id="S1")
        season_plots.plot_h2h_matrix(season_only, tier=99, outdir=outdir, season_id="S1")
        season_plots.plot_points_per_match(season_only, tier=99, outdir=outdir, season_id="S1")
        season_plots.plot_position_range_projection(season_only, tier=99, outdir=outdir, season_id="S1")

    def test_dark_mode_plots_created(self, sample_matches, tmp_path):
        """Dark mode plots should be saved to the dark/ subdirectory."""
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_bump_chart(
            season_only, tier=1, outdir=outdir, season_id="S1", dark_mode=True
        )
        assert os.path.exists(os.path.join(outdir, "dark", "bump_chart_tier1_dark.png"))

    def test_position_range_projection(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_position_range_projection(
            season_only, tier=1, outdir=outdir, season_id="S1"
        )
        assert os.path.exists(os.path.join(outdir, "position_range_projection_tier1.png"))

    def test_position_range_projection_dark(self, sample_matches, tmp_path):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        outdir = str(tmp_path)
        os.makedirs(os.path.join(outdir, "dark"), exist_ok=True)
        season_plots.plot_position_range_projection(
            season_only, tier=1, outdir=outdir, season_id="S1", dark_mode=True
        )
        assert os.path.exists(
            os.path.join(outdir, "dark", "position_range_projection_tier1_dark.png")
        )


class TestComputePositionRangeProjection:
    """Unit tests for compute_position_range_projection."""

    def test_returns_list(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=1)
        assert isinstance(result, list)
        assert len(result) == 3  # Alpha, Beta, Gamma

    def test_empty_tier_returns_empty(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=99)
        assert result == []

    def test_required_keys(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=1)
        for entry in result:
            for key in ("bey", "current_points", "remaining_matches",
                        "p_min", "p_max", "current_rank", "best_rank", "worst_rank"):
                assert key in entry, f"Missing key '{key}' in {entry}"

    def test_p_min_equals_current_points(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        for entry in season_plots.compute_position_range_projection(season_only, tier=1):
            assert entry["p_min"] == entry["current_points"]

    def test_p_max_gte_p_min(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        for entry in season_plots.compute_position_range_projection(season_only, tier=1):
            assert entry["p_max"] >= entry["p_min"]

    def test_best_rank_lte_current_lte_worst_rank(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        for entry in season_plots.compute_position_range_projection(season_only, tier=1):
            assert entry["best_rank"] <= entry["current_rank"]
            assert entry["current_rank"] <= entry["worst_rank"]

    def test_sorted_by_current_rank(self, sample_matches):
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=1)
        ranks = [d["current_rank"] for d in result]
        assert ranks == sorted(ranks)

    def test_winner_has_most_points(self, sample_matches):
        """After all matches, Beta (2W) leads with most season points."""
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=1)
        # All 3 matches played; Beta wins M001 & M003 → 6 pts
        by_bey = {d["bey"]: d for d in result}
        assert by_bey["Beta"]["current_points"] >= by_bey["Alpha"]["current_points"]
        assert by_bey["Beta"]["current_points"] >= by_bey["Gamma"]["current_points"]

    def test_no_remaining_when_all_played(self, sample_matches):
        """When all round-robin matches are done, remaining_matches == 0 for every bey."""
        season_only = sample_matches[sample_matches["MatchType"] == "season"]
        result = season_plots.compute_position_range_projection(season_only, tier=1)
        for entry in result:
            assert entry["remaining_matches"] == 0
            assert entry["p_max"] == entry["p_min"]

    def test_projection_with_remaining_matches(self):
        """Projection logic should behave correctly when matches remain to be played."""
        # 2 of 3 round-robin matches played; Beta and Gamma each have 1 remaining.
        partial_matches = pd.DataFrame([
            {"MatchID": "M001", "BeyA": "Alpha", "BeyB": "Beta", "ScoreA": 4, "ScoreB": 2,
             "MatchType": "season", "SeasonID": "S1", "Tier": 1, "Matchday": 1},
            {"MatchID": "M002", "BeyA": "Alpha", "BeyB": "Gamma", "ScoreA": 2, "ScoreB": 4,
             "MatchType": "season", "SeasonID": "S1", "Tier": 1, "Matchday": 2},
            # Beta vs Gamma NOT yet played → remaining_matches == 1 for both
        ])
        result = season_plots.compute_position_range_projection(partial_matches, tier=1)

        assert any(entry["remaining_matches"] > 0 for entry in result)

        for entry in result:
            assert entry["p_max"] >= entry["p_min"]
            if entry["remaining_matches"] > 0:
                assert entry["p_max"] > entry["p_min"]
            assert entry["best_rank"] <= entry["current_rank"] <= entry["worst_rank"]


class TestManifest:

    def test_manifest_structure(self, tmp_path, sample_matches, sample_rounds,
                                sample_stats_json, monkeypatch):
        """generate_season_plots should write a valid manifest.json per season."""
        # We'll monkeypatch the load_data and BASE_OUTPUT_DIR
        monkeypatch.setattr(season_plots, "BASE_OUTPUT_DIR", str(tmp_path / "plots" / "season"))
        monkeypatch.setattr(season_plots, "load_data", lambda: (
            sample_matches,
            sample_rounds,
            {"seasons": {"S1": {
                "season_id": "S1",
                "start_date": "2026-01-01",
                "end_date": None,
                "league_tables": {},
                "matchdays": {},
                "statistics": {},
            }}},
            sample_stats_json,
        ))
        # Override the season stats file lookup to avoid filesystem access
        # Only intercept the season-specific stats file path, not all os.path.exists calls
        original_exists = os.path.exists
        monkeypatch.setattr(
            os.path, "exists",
            lambda p: False if "season_statistics_S" in p else original_exists(p)
        )

        season_plots.generate_season_plots()

        manifest_path = tmp_path / "plots" / "season" / "S1" / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["season_id"] == "S1"
        assert "tiers" in manifest
        assert "1" in manifest["tiers"]
        tier_data = manifest["tiers"]["1"]
        assert "plots" in tier_data
        assert "dark_plots" in tier_data
        assert len(tier_data["plots"]) == 14
        assert len(tier_data["dark_plots"]) == 14
        # Combined (all-tiers) section
        assert "combined" in manifest
        combined_data = manifest["combined"]
        assert "plots" in combined_data
        assert "dark_plots" in combined_data
        assert len(combined_data["plots"]) == 4
        assert len(combined_data["dark_plots"]) == 4
