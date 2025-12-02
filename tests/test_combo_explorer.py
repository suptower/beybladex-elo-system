"""
Unit tests for combo_explorer.py module.
Tests the Parts Combination Explorer functionality.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from combo_explorer import (
    calculate_combo_rating,
    calculate_combo_synergy,
    find_beys_with_combo,
    build_synergy_lookup,
    generate_combo_data,
)


class TestCalculateComboRating:
    """Tests for the calculate_combo_rating function."""

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with all rating keys."""
        blade_stats = {"stats": {"contact_power": 3.0, "spin_control": 3.0,
                                 "deflection_ability": 3.0}}
        ratchet_stats = {"stats": {"burst_resistance": 3.0, "lock_stability": 3.0,
                                   "weight_efficiency": 3.0}}
        bit_stats = {"stats": {"tip_control": 3.0, "speed_rating": 3.0,
                               "stamina_output": 3.0}}

        result = calculate_combo_rating(blade_stats, ratchet_stats, bit_stats)

        assert "attack" in result
        assert "defense" in result
        assert "stamina" in result
        assert "control" in result
        assert "meta_impact" in result
        assert "overall" in result

    def test_high_stats_give_high_ratings(self):
        """High part stats should produce high combo ratings."""
        blade_stats = {"stats": {"contact_power": 5.0, "spin_control": 5.0,
                                 "deflection_ability": 5.0}}
        ratchet_stats = {"stats": {"burst_resistance": 5.0, "lock_stability": 5.0,
                                   "weight_efficiency": 5.0}}
        bit_stats = {"stats": {"tip_control": 5.0, "speed_rating": 5.0,
                               "stamina_output": 5.0}}

        result = calculate_combo_rating(blade_stats, ratchet_stats, bit_stats)

        assert result["attack"] == 10.0
        assert result["defense"] == 10.0
        assert result["stamina"] == 10.0
        assert result["overall"] == 100.0

    def test_low_stats_give_low_ratings(self):
        """Low part stats should produce low combo ratings."""
        blade_stats = {"stats": {"contact_power": 0.0, "spin_control": 0.0,
                                 "deflection_ability": 0.0}}
        ratchet_stats = {"stats": {"burst_resistance": 0.0, "lock_stability": 0.0,
                                   "weight_efficiency": 0.0}}
        bit_stats = {"stats": {"tip_control": 0.0, "speed_rating": 0.0,
                               "stamina_output": 0.0}}

        result = calculate_combo_rating(blade_stats, ratchet_stats, bit_stats)

        assert result["attack"] == 0.0
        assert result["defense"] == 0.0
        assert result["stamina"] == 0.0
        assert result["overall"] == 0.0

    def test_empty_stats_uses_defaults(self):
        """Empty stats should use default values (2.5)."""
        result = calculate_combo_rating({}, {}, {})

        # With default 2.5 for all stats:
        # attack = 2.5 + 2.5 = 5.0
        # defense = 2.5 + 2.5 = 5.0
        # stamina = 2.5 + 2.5 = 5.0
        # control = (2.5 + 2.5 + 2.5) / 1.5 = 5.0
        assert result["attack"] == 5.0
        assert result["defense"] == 5.0
        assert result["stamina"] == 5.0
        assert result["control"] == 5.0
        assert result["overall"] == 50.0

    def test_overall_in_valid_range(self):
        """Overall rating should be between 0 and 100."""
        import random
        for _ in range(10):
            blade_stats = {"stats": {
                "contact_power": random.uniform(0, 5),
                "spin_control": random.uniform(0, 5),
                "deflection_ability": random.uniform(0, 5)
            }}
            ratchet_stats = {"stats": {
                "burst_resistance": random.uniform(0, 5),
                "lock_stability": random.uniform(0, 5),
                "weight_efficiency": random.uniform(0, 5)
            }}
            bit_stats = {"stats": {
                "tip_control": random.uniform(0, 5),
                "speed_rating": random.uniform(0, 5),
                "stamina_output": random.uniform(0, 5)
            }}

            result = calculate_combo_rating(blade_stats, ratchet_stats, bit_stats)
            assert 0 <= result["overall"] <= 100


class TestCalculateComboSynergy:
    """Tests for the calculate_combo_synergy function."""

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with synergy keys."""
        synergy_lookup = {
            "blade_bit": {("TestBlade", "TestBit"): {"score": 60.0,
                                                     "has_sufficient_data": True}},
            "blade_ratchet": {("TestBlade", "3-60"): {"score": 55.0,
                                                      "has_sufficient_data": True}},
            "bit_ratchet": {("TestBit", "3-60"): {"score": 65.0,
                                                  "has_sufficient_data": True}},
        }

        result = calculate_combo_synergy("TestBlade", "3-60", "TestBit",
                                         synergy_lookup)

        assert "score" in result
        assert "blade_bit" in result
        assert "blade_ratchet" in result
        assert "bit_ratchet" in result
        assert "has_sufficient_data" in result

    def test_calculates_average_synergy(self):
        """Should calculate average of pairwise synergies."""
        synergy_lookup = {
            "blade_bit": {("A", "C"): {"score": 60.0, "has_sufficient_data": True}},
            "blade_ratchet": {("A", "B"): {"score": 50.0, "has_sufficient_data": True}},
            "bit_ratchet": {("C", "B"): {"score": 70.0, "has_sufficient_data": True}},
        }

        result = calculate_combo_synergy("A", "B", "C", synergy_lookup)

        # Average of 60, 50, 70 = 60
        assert result["score"] == 60.0
        assert result["has_sufficient_data"] is True

    def test_missing_synergy_returns_neutral(self):
        """Missing synergy data should return neutral score (50)."""
        synergy_lookup = {
            "blade_bit": {},
            "blade_ratchet": {},
            "bit_ratchet": {},
        }

        result = calculate_combo_synergy("Unknown", "1-60", "UnknownBit",
                                         synergy_lookup)

        assert result["score"] == 50.0
        assert result["has_sufficient_data"] is False

    def test_partial_data_marks_insufficient(self):
        """If any pair lacks data, has_sufficient_data should be False."""
        synergy_lookup = {
            "blade_bit": {("A", "C"): {"score": 60.0, "has_sufficient_data": True}},
            "blade_ratchet": {("A", "B"): {"score": 50.0, "has_sufficient_data": False}},
            "bit_ratchet": {("C", "B"): {"score": 70.0, "has_sufficient_data": True}},
        }

        result = calculate_combo_synergy("A", "B", "C", synergy_lookup)
        assert result["has_sufficient_data"] is False


class TestBuildSynergyLookup:
    """Tests for the build_synergy_lookup function."""

    def test_returns_dict_with_pair_types(self):
        """Should return dict with all pair type keys."""
        synergy_data = {
            "blade_bit": {"data": []},
            "blade_ratchet": {"data": []},
            "bit_ratchet": {"data": []},
        }

        result = build_synergy_lookup(synergy_data)

        assert "blade_bit" in result
        assert "blade_ratchet" in result
        assert "bit_ratchet" in result

    def test_builds_lookup_from_data(self):
        """Should build lookup dict from data list."""
        synergy_data = {
            "blade_bit": {
                "data": [
                    {"part1": "FoxBrush", "part2": "Flat", "score": 65.0,
                     "win_rate": 55.0, "matches": 10, "has_sufficient_data": True}
                ]
            },
            "blade_ratchet": {"data": []},
            "bit_ratchet": {"data": []},
        }

        result = build_synergy_lookup(synergy_data)

        assert ("FoxBrush", "Flat") in result["blade_bit"]
        assert result["blade_bit"][("FoxBrush", "Flat")]["score"] == 65.0

    def test_handles_empty_data(self):
        """Should handle empty synergy data."""
        synergy_data = {}
        result = build_synergy_lookup(synergy_data)

        assert result["blade_bit"] == {}
        assert result["blade_ratchet"] == {}
        assert result["bit_ratchet"] == {}


class TestFindBeysWithCombo:
    """Tests for the find_beys_with_combo function."""

    def test_finds_matching_bey(self):
        """Should find beys with matching combo."""
        beys_data = [
            {"name": "FoxBrush 3-60F", "code": "BX-01", "blade": "FoxBrush",
             "ratchet": "3-60", "bit": "Flat"},
            {"name": "DranSword 4-80B", "code": "BX-02", "blade": "DranSword",
             "ratchet": "4-80", "bit": "Ball"},
        ]

        result = find_beys_with_combo("FoxBrush", "3-60", "Flat", beys_data)

        assert len(result) == 1
        assert result[0]["name"] == "FoxBrush 3-60F"
        assert result[0]["code"] == "BX-01"

    def test_returns_empty_for_no_match(self):
        """Should return empty list when no match."""
        beys_data = [
            {"name": "DranSword 4-80B", "blade": "DranSword",
             "ratchet": "4-80", "bit": "Ball"},
        ]

        result = find_beys_with_combo("FoxBrush", "3-60", "Flat", beys_data)

        assert result == []

    def test_finds_multiple_matches(self):
        """Should find multiple beys with same combo."""
        beys_data = [
            {"name": "FoxBrush 3-60F V1", "code": "BX-01", "blade": "FoxBrush",
             "ratchet": "3-60", "bit": "Flat"},
            {"name": "FoxBrush 3-60F V2", "code": "BX-01A", "blade": "FoxBrush",
             "ratchet": "3-60", "bit": "Flat"},
        ]

        result = find_beys_with_combo("FoxBrush", "3-60", "Flat", beys_data)

        assert len(result) == 2


class TestGenerateComboData:
    """Tests for the generate_combo_data function."""

    def test_returns_expected_structure(self):
        """Should return dict with combos, parts, and metadata."""
        result = generate_combo_data()

        assert "combos" in result
        assert "parts" in result
        assert "metadata" in result
        assert isinstance(result["combos"], list)
        assert "blades" in result["parts"]
        assert "ratchets" in result["parts"]
        assert "bits" in result["parts"]

    def test_combos_have_required_fields(self):
        """Each combo should have all required fields."""
        result = generate_combo_data()

        if result["combos"]:
            combo = result["combos"][0]
            assert "blade" in combo
            assert "ratchet" in combo
            assert "bit" in combo
            assert "rating" in combo
            assert "synergy" in combo
            assert "combo_name" in combo

    def test_combos_sorted_by_rating(self):
        """Combos should be sorted by overall rating descending."""
        result = generate_combo_data()

        if len(result["combos"]) > 1:
            ratings = [c["rating"]["overall"] for c in result["combos"]]
            assert ratings == sorted(ratings, reverse=True)

    def test_metadata_has_counts(self):
        """Metadata should have total counts."""
        result = generate_combo_data()

        assert "total_combos" in result["metadata"]
        assert "total_blades" in result["metadata"]
        assert "total_ratchets" in result["metadata"]
        assert "total_bits" in result["metadata"]
