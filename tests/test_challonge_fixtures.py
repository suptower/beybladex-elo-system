"""
Unit tests for the Challonge Fixtures Integration module.

Tests cover:
- Tournament name parsing (extract_season_tier)
- Deterministic fixture ID generation (make_fixture_id)
- Challonge API JSON parsing (parse_challonge_json, challonge_to_fixtures)
- Played-match detection (load_played_matches)
- Remaining-match computation (compute_remaining_fixtures)
- CSV and JSON output writers
- High-level operations (update_fixtures_for_season, generate_remaining_plan, preview_season)
"""

import csv
import json
import os
import sys
import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.season.challonge_fixtures import (
    challonge_to_fixtures,
    compute_remaining_fixtures,
    extract_season_tier,
    generate_remaining_plan,
    load_played_matches,
    make_fixture_id,
    parse_challonge_json,
    preview_season,
    update_fixtures_for_season,
    write_fixtures_csv,
    write_remaining_plan_csv,
    write_remaining_plan_json,
)
from src.config.paths import SEASON_API_JSONS_DIR, MATCHES_CSV


# ---------------------------------------------------------------------------
# Helpers – minimal Challonge API v2.1 JSON builder
# ---------------------------------------------------------------------------

def _make_challonge_json(
    tournament_name: str,
    participants: dict,  # {id_str: name}
    matches: list,       # list of (p1_id, p2_id, score1, score2, round, state)
) -> dict:
    """Build a minimal Challonge API v2.1 JSON structure."""
    participant_items = [
        {
            "id": pid,
            "type": "participant",
            "attributes": {"name": name, "seed": i + 1},
        }
        for i, (pid, name) in enumerate(participants.items())
    ]

    match_items = []
    for idx, (p1_id, p2_id, s1, s2, rnd, state) in enumerate(matches):
        match_items.append({
            "id": str(1000 + idx),
            "type": "match",
            "attributes": {
                "state": state,
                "round": rnd,
                "identifier": chr(65 + idx),
                "scores": f"{s1} - {s2}",
                "points_by_participant": [
                    {"participant_id": int(p1_id), "scores": [s1]},
                    {"participant_id": int(p2_id), "scores": [s2]},
                ],
            },
        })

    return {
        "data": {
            "id": "99999",
            "type": "tournament",
            "attributes": {
                "name": tournament_name,
                "state": "underway",
                "tournament_type": "round robin",
            },
        },
        "included": participant_items + match_items,
    }


# ---------------------------------------------------------------------------
# Tests: extract_season_tier
# ---------------------------------------------------------------------------

class TestExtractSeasonTier:
    def test_tier_1(self):
        season_id, tier = extract_season_tier("SEASON 2 TIER I")
        assert season_id == "S2"
        assert tier == 1

    def test_tier_2(self):
        season_id, tier = extract_season_tier("SEASON 2 TIER II")
        assert season_id == "S2"
        assert tier == 2

    def test_tier_3(self):
        season_id, tier = extract_season_tier("SEASON 2 TIER III")
        assert season_id == "S2"
        assert tier == 3

    def test_tier_4(self):
        season_id, tier = extract_season_tier("SEASON 2 TIER IV")
        assert season_id == "S2"
        assert tier == 4

    def test_case_insensitive(self):
        season_id, tier = extract_season_tier("Season 3 Tier II")
        assert season_id == "S3"
        assert tier == 2

    def test_season_1(self):
        season_id, tier = extract_season_tier("SEASON 1 TIER I")
        assert season_id == "S1"
        assert tier == 1

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            extract_season_tier("RANDOM TOURNAMENT")

    def test_unsupported_roman_numeral_raises(self):
        with pytest.raises(ValueError):
            extract_season_tier("SEASON 2 TIER XIIV")


# ---------------------------------------------------------------------------
# Tests: make_fixture_id
# ---------------------------------------------------------------------------

class TestMakeFixtureId:
    def test_deterministic(self):
        fid1 = make_fixture_id("FoxBrush", "ImpactDrake", "S2", 1)
        fid2 = make_fixture_id("ImpactDrake", "FoxBrush", "S2", 1)
        assert fid1 == fid2

    def test_includes_season_and_tier(self):
        fid = make_fixture_id("BeyA", "BeyB", "S2", 3)
        assert "S2" in fid
        assert "T3" in fid

    def test_alphabetical_order(self):
        fid = make_fixture_id("ZZZ", "AAA", "S2", 1)
        assert fid == "S2_T1_AAA_ZZZ"

    def test_different_tiers_differ(self):
        fid1 = make_fixture_id("BeyA", "BeyB", "S2", 1)
        fid2 = make_fixture_id("BeyA", "BeyB", "S2", 2)
        assert fid1 != fid2

    def test_different_seasons_differ(self):
        fid1 = make_fixture_id("BeyA", "BeyB", "S1", 1)
        fid2 = make_fixture_id("BeyA", "BeyB", "S2", 1)
        assert fid1 != fid2


# ---------------------------------------------------------------------------
# Tests: parse_challonge_json / challonge_to_fixtures
# ---------------------------------------------------------------------------

class TestParseChallongeJson:
    def _write_json(self, tmpdir, name, participants, matches):
        data = _make_challonge_json(name, participants, matches)
        path = os.path.join(tmpdir, "test.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_basic_parsing(self, tmp_path):
        participants = {"1": "BeyA", "2": "BeyB"}
        matches = [("1", "2", 4, 2, 1, "complete")]
        path = self._write_json(str(tmp_path), "SEASON 2 TIER I",
                                participants, matches)
        result = parse_challonge_json(path)

        assert result["season_id"] == "S2"
        assert result["tier"] == 1
        assert len(result["matches"]) == 1
        match = result["matches"][0]
        assert match["bey_a"] == "BeyA"
        assert match["bey_b"] == "BeyB"
        assert match["score_a"] == 4
        assert match["score_b"] == 2
        assert match["matchday"] == 1
        assert match["state"] == "complete"

    def test_participants_resolved_to_names(self, tmp_path):
        participants = {"10": "FoxBrush", "20": "ImpactDrake"}
        matches = [("10", "20", 3, 4, 2, "complete")]
        path = self._write_json(str(tmp_path), "SEASON 2 TIER I",
                                participants, matches)
        result = parse_challonge_json(path)

        match = result["matches"][0]
        assert match["bey_a"] == "FoxBrush"
        assert match["bey_b"] == "ImpactDrake"

    def test_fixture_id_deterministic(self, tmp_path):
        participants = {"1": "ZBey", "2": "ABey"}
        matches = [("1", "2", 4, 0, 1, "complete")]
        path = self._write_json(str(tmp_path), "SEASON 2 TIER I",
                                participants, matches)
        result = parse_challonge_json(path)

        fid = result["matches"][0]["fixture_id"]
        expected = make_fixture_id("ZBey", "ABey", "S2", 1)
        assert fid == expected

    def test_open_matches_included(self, tmp_path):
        participants = {"1": "BeyA", "2": "BeyB"}
        matches = [
            ("1", "2", 4, 2, 1, "complete"),
            ("1", "2", 0, 0, 2, "open"),
        ]
        path = self._write_json(str(tmp_path), "SEASON 2 TIER II",
                                participants, matches)
        result = parse_challonge_json(path)
        assert len(result["matches"]) == 2

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_challonge_json("/nonexistent/path.json")

    def test_challonge_to_fixtures_returns_list(self, tmp_path):
        participants = {"1": "BeyA", "2": "BeyB"}
        matches = [("1", "2", 4, 2, 1, "complete")]
        path = self._write_json(str(tmp_path), "SEASON 2 TIER III",
                                participants, matches)
        fixtures = challonge_to_fixtures(path)
        assert isinstance(fixtures, list)
        assert len(fixtures) == 1


# ---------------------------------------------------------------------------
# Tests: load_played_matches
# ---------------------------------------------------------------------------

class TestLoadPlayedMatches:
    def _write_matches_csv(self, tmpdir, rows):
        """rows: list of (MatchID, Date, BeyA, BeyB, ScoreA, ScoreB, MatchType, SeasonID, Tier, Matchday, arena)"""
        path = os.path.join(tmpdir, "matches.csv")
        fieldnames = ["MatchID", "Date", "BeyA", "BeyB", "ScoreA", "ScoreB",
                      "MatchType", "SeasonID", "Tier", "Matchday", "arena"]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(zip(fieldnames, row)))
        return path

    def test_played_match_detected(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "BeyA", "BeyB", 4, 2, "season", "S2", 1, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2")
        assert frozenset(["BeyA", "BeyB"]) in played

    def test_zero_score_not_played(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "BeyA", "BeyB", 0, 0, "season", "S2", 1, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2")
        assert frozenset(["BeyA", "BeyB"]) not in played

    def test_wrong_season_excluded(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "BeyA", "BeyB", 4, 2, "season", "S1", 1, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2")
        assert frozenset(["BeyA", "BeyB"]) not in played

    def test_non_season_match_excluded(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "BeyA", "BeyB", 4, 2, "exhibition", "S2", 1, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2")
        assert frozenset(["BeyA", "BeyB"]) not in played

    def test_tier_filter(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "BeyA", "BeyB", 4, 2, "season", "S2", 1, 1, "Xtreme"),
            ("M0002", "2026-04-03", "BeyC", "BeyD", 3, 4, "season", "S2", 2, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2", tier=1)
        assert frozenset(["BeyA", "BeyB"]) in played
        assert frozenset(["BeyC", "BeyD"]) not in played

    def test_order_independent(self, tmp_path):
        rows = [
            ("M0001", "2026-04-03", "ZBey", "ABey", 4, 2, "season", "S2", 1, 1, "Xtreme"),
        ]
        path = self._write_matches_csv(str(tmp_path), rows)
        played = load_played_matches(path, "S2")
        assert frozenset(["ABey", "ZBey"]) in played

    def test_missing_csv_returns_empty(self, tmp_path):
        played = load_played_matches(
            os.path.join(str(tmp_path), "nonexistent.csv"), "S2"
        )
        assert played == set()


# ---------------------------------------------------------------------------
# Tests: compute_remaining_fixtures
# ---------------------------------------------------------------------------

class TestComputeRemainingFixtures:
    def _make_fixture(self, bey_a, bey_b, season_id="S2", tier=1, matchday=1):
        return {
            "fixture_id": make_fixture_id(bey_a, bey_b, season_id, tier),
            "bey_a": bey_a,
            "bey_b": bey_b,
            "season_id": season_id,
            "tier": tier,
            "matchday": matchday,
            "state": "open",
        }

    def test_empty_played_returns_all(self):
        fixtures = [self._make_fixture("A", "B"), self._make_fixture("C", "D")]
        remaining = compute_remaining_fixtures(fixtures, set())
        assert len(remaining) == 2

    def test_played_match_excluded(self):
        fixtures = [self._make_fixture("A", "B"), self._make_fixture("C", "D")]
        played = {frozenset(["A", "B"])}
        remaining = compute_remaining_fixtures(fixtures, played)
        assert len(remaining) == 1
        assert remaining[0]["bey_a"] == "C"
        assert remaining[0]["bey_b"] == "D"

    def test_all_played_returns_empty(self):
        fixtures = [self._make_fixture("A", "B"), self._make_fixture("C", "D")]
        played = {frozenset(["A", "B"]), frozenset(["C", "D"])}
        remaining = compute_remaining_fixtures(fixtures, played)
        assert len(remaining) == 0

    def test_order_independent_detection(self):
        """A played (B, A) pair should exclude fixture (A, B)."""
        fixtures = [self._make_fixture("A", "B")]
        played = {frozenset(["B", "A"])}  # reversed
        remaining = compute_remaining_fixtures(fixtures, played)
        assert len(remaining) == 0

    def test_preserves_order(self):
        fixtures = [
            self._make_fixture("A", "B", matchday=3),
            self._make_fixture("C", "D", matchday=1),
            self._make_fixture("E", "F", matchday=2),
        ]
        remaining = compute_remaining_fixtures(fixtures, set())
        assert [f["bey_a"] for f in remaining] == ["A", "C", "E"]


# ---------------------------------------------------------------------------
# Tests: write_fixtures_csv
# ---------------------------------------------------------------------------

class TestWriteFixturesCsv:
    def _make_fixture(self, bey_a, bey_b, tier=1, matchday=1):
        return {
            "fixture_id": make_fixture_id(bey_a, bey_b, "S2", tier),
            "bey_a": bey_a,
            "bey_b": bey_b,
            "date": "",
            "season_id": "S2",
            "tier": tier,
            "matchday": matchday,
        }

    def test_writes_header_and_rows(self, tmp_path):
        fixtures = [self._make_fixture("BeyA", "BeyB")]
        path = os.path.join(str(tmp_path), "fixtures.csv")
        write_fixtures_csv(fixtures, path)

        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["BeyA"] == "BeyA"
        assert rows[0]["BeyB"] == "BeyB"
        assert rows[0]["SeasonID"] == "S2"
        assert rows[0]["Tier"] == "1"
        assert rows[0]["Matchday"] == "1"
        assert rows[0]["MatchType"] == "season"

    def test_append_mode(self, tmp_path):
        fixtures1 = [self._make_fixture("BeyA", "BeyB")]
        fixtures2 = [self._make_fixture("BeyC", "BeyD")]
        path = os.path.join(str(tmp_path), "fixtures.csv")

        write_fixtures_csv(fixtures1, path, append=False)
        write_fixtures_csv(fixtures2, path, append=True)

        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 2


# ---------------------------------------------------------------------------
# Tests: write_remaining_plan_csv
# ---------------------------------------------------------------------------

class TestWriteRemainingPlanCsv:
    def _make_fixture(self, bey_a, bey_b, tier=1, matchday=1):
        return {
            "fixture_id": make_fixture_id(bey_a, bey_b, "S2", tier),
            "bey_a": bey_a,
            "bey_b": bey_b,
            "season_id": "S2",
            "tier": tier,
            "matchday": matchday,
        }

    def test_writes_session_format(self, tmp_path):
        fixtures = [self._make_fixture("BeyA", "BeyB")]
        path = os.path.join(str(tmp_path), "remaining.csv")
        write_remaining_plan_csv(fixtures, path)

        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row["MatchID"] == "M0001"
        assert row["BeyA"] == "BeyA"
        assert row["BeyB"] == "BeyB"
        assert row["MatchType"] == "season"
        assert row["arena"] == "Xtreme"
        assert row["ScoreA"] == ""
        assert row["ScoreB"] == ""
        assert row["Date"] == ""

    def test_sequential_match_ids(self, tmp_path):
        fixtures = [
            self._make_fixture("BeyA", "BeyB"),
            self._make_fixture("BeyC", "BeyD"),
            self._make_fixture("BeyE", "BeyF"),
        ]
        path = os.path.join(str(tmp_path), "remaining.csv")
        write_remaining_plan_csv(fixtures, path)

        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert rows[0]["MatchID"] == "M0001"
        assert rows[1]["MatchID"] == "M0002"
        assert rows[2]["MatchID"] == "M0003"


# ---------------------------------------------------------------------------
# Tests: write_remaining_plan_json
# ---------------------------------------------------------------------------

class TestWriteRemainingPlanJson:
    def _make_fixture(self, bey_a, bey_b, tier=1, matchday=1):
        return {
            "fixture_id": make_fixture_id(bey_a, bey_b, "S2", tier),
            "bey_a": bey_a,
            "bey_b": bey_b,
            "season_id": "S2",
            "tier": tier,
            "matchday": matchday,
        }

    def test_writes_json_array(self, tmp_path):
        fixtures = [self._make_fixture("BeyA", "BeyB")]
        path = os.path.join(str(tmp_path), "remaining.json")
        write_remaining_plan_json(fixtures, path)

        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["bey_a"] == "BeyA"
        assert data[0]["bey_b"] == "BeyB"
        assert data[0]["match_id"] == "M0001"
        assert data[0]["arena"] == "Xtreme"


# ---------------------------------------------------------------------------
# Integration tests using real API JSON files (if available)
# ---------------------------------------------------------------------------

class TestRealApiFiles:
    """Integration tests that use the actual API JSON files in the repo."""

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_parse_all_s2_tiers(self):
        """All 4 Season 2 API JSONs should parse without errors."""
        for tier in [1, 2, 3, 4]:
            path = os.path.join(SEASON_API_JSONS_DIR, "s2", f"s2_t{tier}.json")
            if not os.path.exists(path):
                continue
            result = parse_challonge_json(path)
            assert result["season_id"] == "S2"
            assert result["tier"] == tier
            assert len(result["matches"]) == 28  # 8 players, round-robin = 28

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_s2_tier1_participants(self):
        """Tier 1 should have exactly 8 participants."""
        path = os.path.join(SEASON_API_JSONS_DIR, "s2", "s2_t1.json")
        result = parse_challonge_json(path)
        assert len(result["participants"]) == 8

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_preview_season_s2(self):
        """Preview should show played matches and remaining matches for S2."""
        summary = preview_season("S2", matches_csv=MATCHES_CSV)

        assert summary["total_scheduled"] == 112  # 4 tiers × 28 matches
        assert summary["played"] > 0
        assert summary["remaining"] < summary["total_scheduled"]
        assert summary["played"] + summary["remaining"] == summary["total_scheduled"]

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_generate_remaining_plan_creates_files(self, tmp_path):
        """generate_remaining_plan should create a CSV file."""
        summary = generate_remaining_plan(
            "S2",
            matches_csv=MATCHES_CSV,
            output_dir=str(tmp_path),
            output_format="csv",
        )
        assert len(summary["output_files"]) == 1
        assert os.path.exists(summary["output_files"][0])

        # Remaining should be total - played
        assert summary["remaining"] == summary["total_scheduled"] - summary["played"]

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_generate_remaining_plan_both_formats(self, tmp_path):
        """generate_remaining_plan with format='both' creates CSV and JSON."""
        summary = generate_remaining_plan(
            "S2",
            matches_csv=MATCHES_CSV,
            output_dir=str(tmp_path),
            output_format="both",
        )
        assert len(summary["output_files"]) == 2
        csv_files = [f for f in summary["output_files"] if f.endswith(".csv")]
        json_files = [f for f in summary["output_files"] if f.endswith(".json")]
        assert len(csv_files) == 1
        assert len(json_files) == 1

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_update_fixtures_for_season(self, tmp_path):
        """update_fixtures_for_season should write all 112 fixtures."""
        output_csv = os.path.join(str(tmp_path), "fixtures.csv")
        summary = update_fixtures_for_season(
            "S2",
            fixtures_csv=output_csv,
        )
        assert summary["total"] == 112
        assert os.path.exists(output_csv)

        with open(output_csv, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == 112
        # Check all tiers represented
        tiers = {int(r["Tier"]) for r in rows}
        assert tiers == {1, 2, 3, 4}

    @pytest.mark.skipif(
        not os.path.isdir(os.path.join(SEASON_API_JSONS_DIR, "s2")),
        reason="Season 2 API JSON files not present",
    )
    def test_remaining_fixture_ids_are_deterministic(self, tmp_path):
        """Running generate_remaining_plan twice should produce identical output."""
        csv1 = os.path.join(str(tmp_path), "run1.csv")
        csv2 = os.path.join(str(tmp_path), "run2.csv")

        generate_remaining_plan(
            "S2", matches_csv=MATCHES_CSV,
            output_dir=str(tmp_path), output_format="csv",
        )
        import shutil
        shutil.copy(
            os.path.join(str(tmp_path), "remaining_s2.csv"), csv1
        )

        generate_remaining_plan(
            "S2", matches_csv=MATCHES_CSV,
            output_dir=str(tmp_path), output_format="csv",
        )
        shutil.copy(
            os.path.join(str(tmp_path), "remaining_s2.csv"), csv2
        )

        with open(csv1, encoding="utf-8") as f1, open(csv2, encoding="utf-8") as f2:
            assert f1.read() == f2.read()
