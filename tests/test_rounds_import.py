"""
Unit tests for rounds import and merge functionality.

Tests the validation, spin-default behavior, and merging logic for
per-round finish type tracking.
"""
import json
import os
import sys
import tempfile

# Add tools and scripts directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from merge_rounds import (
    VALID_FINISH_TYPES,
    DEFAULT_FINISH_TYPE,
    load_challonge_csv,
    load_rounds_csv,
    compute_scores_from_rounds,
    merge_matches_and_rounds,
    validate_merged_data,
    load_finish_weights,
)


class TestValidFinishTypes:
    """Tests for valid finish type constants."""

    def test_valid_finish_types_contains_spin(self):
        """spin should be a valid finish type."""
        assert "spin" in VALID_FINISH_TYPES

    def test_valid_finish_types_contains_pocket(self):
        """pocket should be a valid finish type."""
        assert "pocket" in VALID_FINISH_TYPES

    def test_valid_finish_types_contains_burst(self):
        """burst should be a valid finish type."""
        assert "burst" in VALID_FINISH_TYPES

    def test_valid_finish_types_contains_extreme(self):
        """extreme should be a valid finish type."""
        assert "extreme" in VALID_FINISH_TYPES

    def test_default_finish_type_is_spin(self):
        """Default finish type should be spin."""
        assert DEFAULT_FINISH_TYPE == "spin"


class TestLoadFinishWeights:
    """Tests for finish weights loading."""

    def test_load_default_weights(self):
        """Should load default weights when config exists."""
        weights = load_finish_weights()
        assert "spin" in weights
        assert weights["spin"] == 1

    def test_weights_values(self):
        """Should have correct default weight values."""
        weights = load_finish_weights()
        assert weights.get("spin") == 1
        assert weights.get("pocket") == 2
        assert weights.get("burst") == 2
        assert weights.get("extreme") == 3

    def test_load_missing_config(self):
        """Should return default weights when config is missing."""
        weights = load_finish_weights("/nonexistent/path.json")
        assert "spin" in weights
        assert weights["spin"] == 1


class TestLoadChallongeCsv:
    """Tests for loading Challonge CSV exports."""

    def test_load_internal_format(self):
        """Should load internal CSV format correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,BeyA,BeyB,ScoreA,ScoreB\n")
            f.write("2025-09-07,ViperTail,WizardArc,4,2\n")
            f.flush()

            matches = load_challonge_csv(f.name)

            assert len(matches) == 1
            assert matches[0]["bey_a"] == "ViperTail"
            assert matches[0]["bey_b"] == "WizardArc"
            assert matches[0]["score_a"] == 4
            assert matches[0]["score_b"] == 2
            assert matches[0]["date"] == "2025-09-07"

        os.unlink(f.name)

    def test_generates_match_id_if_missing(self):
        """Should generate match_id if not present in CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date,BeyA,BeyB,ScoreA,ScoreB\n")
            f.write("2025-09-07,ViperTail,WizardArc,4,2\n")
            f.flush()

            matches = load_challonge_csv(f.name)

            assert matches[0]["match_id"] != ""
            assert "ViperTail" in matches[0]["match_id"]

        os.unlink(f.name)


class TestLoadRoundsCsv:
    """Tests for loading rounds CSV files."""

    def test_load_rounds_basic(self):
        """Should load rounds CSV correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("match_id,round_number,winner,finish_type,points_awarded,notes\n")
            f.write("M001,1,ViperTail,spin,1,Test note\n")
            f.write("M001,2,WizardArc,burst,2,\n")
            f.flush()

            rounds = load_rounds_csv(f.name)

            assert "M001" in rounds
            assert len(rounds["M001"]) == 2
            assert rounds["M001"][0]["winner"] == "ViperTail"
            assert rounds["M001"][0]["finish_type"] == "spin"
            assert rounds["M001"][1]["finish_type"] == "burst"

        os.unlink(f.name)

    def test_default_finish_type_to_spin(self):
        """Should default missing finish_type to spin."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("match_id,round_number,winner,finish_type,points_awarded,notes\n")
            f.write("M001,1,ViperTail,,1,\n")  # Empty finish_type
            f.flush()

            rounds = load_rounds_csv(f.name)

            assert rounds["M001"][0]["finish_type"] == "spin"

        os.unlink(f.name)

    def test_invalid_finish_type_defaults_to_spin(self):
        """Should default invalid finish_type to spin with warning."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("match_id,round_number,winner,finish_type,points_awarded,notes\n")
            f.write("M001,1,ViperTail,invalid_type,1,\n")
            f.flush()

            rounds = load_rounds_csv(f.name)

            assert rounds["M001"][0]["finish_type"] == "spin"

        os.unlink(f.name)

    def test_rounds_sorted_by_round_number(self):
        """Should sort rounds by round_number within each match."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("match_id,round_number,winner,finish_type,points_awarded,notes\n")
            f.write("M001,3,ViperTail,spin,1,\n")
            f.write("M001,1,WizardArc,burst,2,\n")
            f.write("M001,2,ViperTail,pocket,2,\n")
            f.flush()

            rounds = load_rounds_csv(f.name)

            assert rounds["M001"][0]["round_number"] == 1
            assert rounds["M001"][1]["round_number"] == 2
            assert rounds["M001"][2]["round_number"] == 3

        os.unlink(f.name)


class TestComputeScoresFromRounds:
    """Tests for score computation from round data."""

    def test_compute_scores_basic(self):
        """Should correctly compute scores from rounds."""
        rounds = [
            {"winner": "BeyA", "points_awarded": 1},
            {"winner": "BeyB", "points_awarded": 2},
            {"winner": "BeyA", "points_awarded": 2},
        ]
        score_a, score_b = compute_scores_from_rounds(rounds, "BeyA", "BeyB")
        assert score_a == 3
        assert score_b == 2

    def test_compute_scores_all_one_winner(self):
        """Should handle all rounds won by one player."""
        rounds = [
            {"winner": "BeyA", "points_awarded": 2},
            {"winner": "BeyA", "points_awarded": 3},
        ]
        score_a, score_b = compute_scores_from_rounds(rounds, "BeyA", "BeyB")
        assert score_a == 5
        assert score_b == 0

    def test_compute_scores_empty_rounds(self):
        """Should return zero scores for empty rounds."""
        score_a, score_b = compute_scores_from_rounds([], "BeyA", "BeyB")
        assert score_a == 0
        assert score_b == 0


class TestMergeMatchesAndRounds:
    """Tests for merging match and round data."""

    def test_merge_basic(self):
        """Should merge matches with rounds by match_id."""
        matches = [
            {"match_id": "M001", "date": "2025-09-07", "bey_a": "BeyA", "bey_b": "BeyB", "score_a": 3, "score_b": 2}
        ]
        rounds_by_match = {
            "M001": [
                {"round_number": 1, "winner": "BeyA", "points_awarded": 1, "finish_type": "spin", "notes": ""},
                {"round_number": 2, "winner": "BeyB", "points_awarded": 2, "finish_type": "burst", "notes": ""},
                {"round_number": 3, "winner": "BeyA", "points_awarded": 2, "finish_type": "pocket", "notes": ""},
            ]
        }

        merged, stats = merge_matches_and_rounds(matches, rounds_by_match)

        assert len(merged) == 1
        assert "rounds" in merged[0]
        assert len(merged[0]["rounds"]) == 3
        assert stats["merged"] == 1
        assert stats["unmerged"] == 0

    def test_merge_score_mismatch_warning(self):
        """Should generate warning on score mismatch."""
        matches = [
            {"match_id": "M001", "date": "2025-09-07", "bey_a": "BeyA", "bey_b": "BeyB", "score_a": 5, "score_b": 3}
        ]
        rounds_by_match = {
            "M001": [
                {"round_number": 1, "winner": "BeyA", "points_awarded": 2, "finish_type": "spin", "notes": ""},
                {"round_number": 2, "winner": "BeyB", "points_awarded": 1, "finish_type": "spin", "notes": ""},
            ]
        }

        merged, stats = merge_matches_and_rounds(matches, rounds_by_match)

        assert stats["score_mismatches"] == 1
        # Should prefer rounds data
        assert merged[0]["score_a"] == 2
        assert merged[0]["score_b"] == 1

    def test_merge_unmatched_warning(self):
        """Should track matches without rounds."""
        matches = [
            {"match_id": "M001", "date": "2025-09-07", "bey_a": "BeyA", "bey_b": "BeyB", "score_a": 3, "score_b": 2},
            {"match_id": "M002", "date": "2025-09-07", "bey_a": "BeyC", "bey_b": "BeyD", "score_a": 4, "score_b": 1}
        ]
        rounds_by_match = {
            "M001": [
                {"round_number": 1, "winner": "BeyA", "points_awarded": 3, "finish_type": "spin", "notes": ""},
            ]
        }

        merged, stats = merge_matches_and_rounds(matches, rounds_by_match)

        assert stats["merged"] == 1
        assert stats["unmerged"] == 1

    def test_backward_compatibility_no_rounds(self):
        """Should work correctly when no rounds provided."""
        matches = [
            {"match_id": "M001", "date": "2025-09-07", "bey_a": "BeyA", "bey_b": "BeyB", "score_a": 3, "score_b": 2}
        ]
        rounds_by_match = {}

        merged, stats = merge_matches_and_rounds(matches, rounds_by_match)

        assert len(merged) == 1
        assert "rounds" not in merged[0]
        assert stats["unmerged"] == 1


class TestValidateMergedData:
    """Tests for validation of merged data."""

    def test_validate_valid_data(self):
        """Should pass validation for valid data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {
                "matches": [
                    {
                        "match_id": "M001",
                        "bey_a": "BeyA",
                        "bey_b": "BeyB",
                        "score_a": 3,
                        "score_b": 2,
                        "rounds": [
                            {"round_number": 1, "winner": "BeyA", "points_awarded": 1, "finish_type": "spin"},
                            {"round_number": 2, "winner": "BeyB", "points_awarded": 2, "finish_type": "burst"},
                            {"round_number": 3, "winner": "BeyA", "points_awarded": 2, "finish_type": "pocket"},
                        ]
                    }
                ]
            }
            json.dump(data, f)
            f.flush()

            result = validate_merged_data(f.name)
            assert result is True

        os.unlink(f.name)

    def test_validate_invalid_finish_type(self):
        """Should fail validation for invalid finish_type."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {
                "matches": [
                    {
                        "match_id": "M001",
                        "bey_a": "BeyA",
                        "bey_b": "BeyB",
                        "rounds": [
                            {"round_number": 1, "winner": "BeyA", "points_awarded": 1, "finish_type": "invalid"},
                        ]
                    }
                ]
            }
            json.dump(data, f)
            f.flush()

            result = validate_merged_data(f.name)
            assert result is False

        os.unlink(f.name)

    def test_validate_winner_not_in_players(self):
        """Should fail validation when winner not in players."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = {
                "matches": [
                    {
                        "match_id": "M001",
                        "bey_a": "BeyA",
                        "bey_b": "BeyB",
                        "rounds": [
                            {"round_number": 1, "winner": "BeyC", "points_awarded": 1, "finish_type": "spin"},
                        ]
                    }
                ]
            }
            json.dump(data, f)
            f.flush()

            result = validate_merged_data(f.name)
            assert result is False

        os.unlink(f.name)


class TestWeightedScoring:
    """Tests for weighted scoring based on finish types."""

    def test_weights_applied_correctly(self):
        """Should use correct weights for different finish types."""
        weights = load_finish_weights()

        # Verify weights are as expected
        assert weights["spin"] == 1
        assert weights["pocket"] == 2
        assert weights["burst"] == 2
        assert weights["extreme"] == 3

    def test_weighted_score_calculation(self):
        """Weighted scores should be calculable from rounds."""
        rounds = [
            {"winner": "BeyA", "points_awarded": 1, "finish_type": "spin"},      # 1 pt
            {"winner": "BeyA", "points_awarded": 2, "finish_type": "burst"},     # 2 pts
            {"winner": "BeyB", "points_awarded": 3, "finish_type": "extreme"},   # 3 pts
        ]

        weights = load_finish_weights()

        # Verify that points_awarded matches expected weights
        for r in rounds:
            assert r["points_awarded"] == weights[r["finish_type"]]
