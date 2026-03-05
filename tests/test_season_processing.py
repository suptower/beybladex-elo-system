"""
Unit tests for season_processing.py – refresh_qualification_pool function.
"""
import csv
import json
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'season'))

from season_processing import refresh_qualification_pool  # noqa: E402


def _write_leaderboard(data_dir: str, beys: dict) -> None:
    """Write a minimal leaderboard.csv with Name and ELO columns."""
    path = os.path.join(data_dir, "leaderboard.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "ELO"])
        writer.writeheader()
        for name, elo in beys.items():
            writer.writerow({"Name": name, "ELO": elo})


def _write_seasons(data_dir: str, seasons: dict) -> None:
    """Write seasons.json."""
    path = os.path.join(data_dir, "seasons.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seasons, f)


def _load_seasons(data_dir: str) -> dict:
    """Load seasons.json."""
    path = os.path.join(data_dir, "seasons.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _make_season(tier_beys, pool_beys):
    """Build a minimal season dict."""
    return {
        "season_id": "S1",
        "status": "active",
        "tier_assignments": {b: {"tier": 1, "start_elo": 1000} for b in tier_beys},
        "qualification_pool": [{"bey": b, "elo": 1000} for b in pool_beys],
    }


class TestRefreshQualificationPool:
    """Tests for refresh_qualification_pool()."""

    def test_returns_list(self, tmp_path):
        """Function should return a list."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1000})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})
        result = refresh_qualification_pool("S1", data_dir)
        assert isinstance(result, list)

    def test_new_bey_added_to_pool(self, tmp_path):
        """A bey in leaderboard but not in tiers/pool should be added to the pool."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1000, "Gamma": 950})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        result = refresh_qualification_pool("S1", data_dir)
        pool_beys = [e["bey"] for e in result]
        assert "Gamma" in pool_beys

    def test_tier_bey_not_added_to_pool(self, tmp_path):
        """A bey already in tier assignments must not appear in the pool."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1000})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        result = refresh_qualification_pool("S1", data_dir)
        pool_beys = [e["bey"] for e in result]
        assert "Alpha" not in pool_beys

    def test_existing_pool_bey_not_duplicated(self, tmp_path):
        """An existing pool member must appear exactly once after refresh."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1000})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        result = refresh_qualification_pool("S1", data_dir)
        pool_beys = [e["bey"] for e in result]
        assert pool_beys.count("Beta") == 1

    def test_elo_updated_for_existing_pool_member(self, tmp_path):
        """ELO of an existing pool bey should be updated to current leaderboard value."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1200})  # Beta ELO changed
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        result = refresh_qualification_pool("S1", data_dir)
        beta_entry = next(e for e in result if e["bey"] == "Beta")
        assert beta_entry["elo"] == 1200

    def test_pool_sorted_by_elo_descending(self, tmp_path):
        """Pool should be sorted by ELO descending after refresh."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 900, "Gamma": 1050, "Delta": 980})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta", "Gamma"])})

        result = refresh_qualification_pool("S1", data_dir)
        elos = [e["elo"] for e in result]
        assert elos == sorted(elos, reverse=True)

    def test_seasons_json_updated_on_disk(self, tmp_path):
        """seasons.json should be updated with the refreshed pool."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100, "Beta": 1000, "Gamma": 950})
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        refresh_qualification_pool("S1", data_dir)

        saved = _load_seasons(data_dir)
        pool_beys = [e["bey"] for e in saved["S1"]["qualification_pool"]]
        assert "Gamma" in pool_beys

    def test_empty_result_when_no_leaderboard(self, tmp_path):
        """Returns empty list when leaderboard.csv is absent."""
        data_dir = str(tmp_path)
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})
        result = refresh_qualification_pool("S1", data_dir)
        assert result == []

    def test_empty_result_when_season_missing(self, tmp_path):
        """Returns empty list when the season is not found in seasons.json."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {"Alpha": 1100})
        _write_seasons(data_dir, {"S2": _make_season(["Alpha"], [])})
        result = refresh_qualification_pool("S1", data_dir)
        assert result == []

    def test_multiple_new_beys_all_added(self, tmp_path):
        """All new beys absent from season should be added to the pool."""
        data_dir = str(tmp_path)
        _write_leaderboard(data_dir, {
            "Alpha": 1100, "Beta": 1000, "NewA": 990, "NewB": 970, "NewC": 960
        })
        _write_seasons(data_dir, {"S1": _make_season(["Alpha"], ["Beta"])})

        result = refresh_qualification_pool("S1", data_dir)
        pool_beys = [e["bey"] for e in result]
        assert "NewA" in pool_beys
        assert "NewB" in pool_beys
        assert "NewC" in pool_beys
