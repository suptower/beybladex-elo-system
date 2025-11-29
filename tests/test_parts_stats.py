"""
Unit tests for parts_stats.py module.
Tests the Parts Performance Ranking functionality for Blades, Ratchets, and Bits.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from parts_stats import (
    clamp,
    load_parts_stats,
    calculate_total_score,
    get_blades_ranking,
    get_ratchets_ranking,
    get_bits_ranking,
    BLADE_STATS,
    RATCHET_STATS,
    BIT_STATS,
)


class TestClamp:
    """Tests for the clamp function."""

    def test_value_in_range(self):
        """Value in range should be unchanged."""
        assert clamp(3.0) == 3.0

    def test_value_below_min(self):
        """Value below min should be clamped to min."""
        assert clamp(-1.0) == 0.0

    def test_value_above_max(self):
        """Value above max should be clamped to max."""
        assert clamp(6.0) == 5.0

    def test_custom_range(self):
        """Custom range should work correctly."""
        assert clamp(50, 0, 100) == 50
        assert clamp(-10, 0, 100) == 0
        assert clamp(150, 0, 100) == 100


class TestStatConfigurations:
    """Tests for stat configuration dictionaries."""

    def test_blade_stats_has_required_keys(self):
        """Blade stats should have all required stat keys."""
        required_keys = {"contact_power", "spin_control", "deflection_ability"}
        assert required_keys == set(BLADE_STATS.keys())

    def test_ratchet_stats_has_required_keys(self):
        """Ratchet stats should have all required stat keys."""
        required_keys = {"burst_resistance", "lock_stability", "weight_efficiency"}
        assert required_keys == set(RATCHET_STATS.keys())

    def test_bit_stats_has_required_keys(self):
        """Bit stats should have all required stat keys."""
        required_keys = {"tip_control", "speed_rating", "stamina_output"}
        assert required_keys == set(BIT_STATS.keys())

    def test_all_stats_have_name_and_description(self):
        """All stat configurations should have name and description."""
        all_stats = [BLADE_STATS, RATCHET_STATS, BIT_STATS]
        for stats in all_stats:
            for stat_key, stat_info in stats.items():
                assert "name" in stat_info, f"{stat_key} missing name"
                assert "description" in stat_info, f"{stat_key} missing description"
                assert "icon" in stat_info, f"{stat_key} missing icon"


class TestCalculateTotalScore:
    """Tests for the calculate_total_score function."""

    def test_basic_total(self):
        """Should correctly sum all values."""
        stats = {"a": 1.0, "b": 2.0, "c": 3.0}
        assert calculate_total_score(stats) == 6.0

    def test_empty_stats(self):
        """Empty stats should return 0."""
        assert calculate_total_score({}) == 0

    def test_single_stat(self):
        """Single stat should return that value."""
        assert calculate_total_score({"test": 4.5}) == 4.5


class TestLoadPartsStats:
    """Tests for loading parts stats data."""

    def test_loads_data_structure(self):
        """Should load valid data structure."""
        data = load_parts_stats()
        assert "blades" in data
        assert "ratchets" in data
        assert "bits" in data
        assert "metadata" in data

    def test_blades_have_stats(self):
        """All blades should have stats."""
        data = load_parts_stats()
        for blade_name, blade_data in data["blades"].items():
            assert "stats" in blade_data, f"Blade {blade_name} missing stats"
            assert "type" in blade_data, f"Blade {blade_name} missing type"
            stats = blade_data["stats"]
            assert "contact_power" in stats
            assert "spin_control" in stats
            assert "deflection_ability" in stats

    def test_ratchets_have_stats(self):
        """All ratchets should have stats."""
        data = load_parts_stats()
        for ratchet_name, ratchet_data in data["ratchets"].items():
            assert "stats" in ratchet_data, f"Ratchet {ratchet_name} missing stats"
            stats = ratchet_data["stats"]
            assert "burst_resistance" in stats
            assert "lock_stability" in stats
            assert "weight_efficiency" in stats

    def test_bits_have_stats(self):
        """All bits should have stats."""
        data = load_parts_stats()
        for bit_name, bit_data in data["bits"].items():
            assert "stats" in bit_data, f"Bit {bit_name} missing stats"
            assert "category" in bit_data, f"Bit {bit_name} missing category"
            stats = bit_data["stats"]
            assert "tip_control" in stats
            assert "speed_rating" in stats
            assert "stamina_output" in stats


class TestStatsInRange:
    """Tests that all stats are within valid range."""

    def test_blade_stats_in_range(self):
        """All blade stats should be between 0 and 5."""
        data = load_parts_stats()
        for blade_name, blade_data in data["blades"].items():
            for stat_name, value in blade_data["stats"].items():
                assert 0 <= value <= 5, f"Blade {blade_name} {stat_name}={value} out of range"

    def test_ratchet_stats_in_range(self):
        """All ratchet stats should be between 0 and 5."""
        data = load_parts_stats()
        for ratchet_name, ratchet_data in data["ratchets"].items():
            for stat_name, value in ratchet_data["stats"].items():
                assert 0 <= value <= 5, f"Ratchet {ratchet_name} {stat_name}={value} out of range"

    def test_bit_stats_in_range(self):
        """All bit stats should be between 0 and 5."""
        data = load_parts_stats()
        for bit_name, bit_data in data["bits"].items():
            for stat_name, value in bit_data["stats"].items():
                assert 0 <= value <= 5, f"Bit {bit_name} {stat_name}={value} out of range"


class TestGetBladesRanking:
    """Tests for the get_blades_ranking function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_blades_ranking()
        assert isinstance(result, list)

    def test_contains_expected_fields(self):
        """Each blade should have expected fields."""
        result = get_blades_ranking()
        for blade in result:
            assert "name" in blade
            assert "type" in blade
            assert "contact_power" in blade
            assert "spin_control" in blade
            assert "deflection_ability" in blade
            assert "total" in blade

    def test_sorted_by_total_desc(self):
        """Default sort should be by total descending."""
        result = get_blades_ranking()
        totals = [blade["total"] for blade in result]
        assert totals == sorted(totals, reverse=True)

    def test_sort_by_contact_power(self):
        """Should sort by contact_power when specified."""
        result = get_blades_ranking(sort_by="contact_power")
        values = [blade["contact_power"] for blade in result]
        assert values == sorted(values, reverse=True)


class TestGetRatchetsRanking:
    """Tests for the get_ratchets_ranking function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_ratchets_ranking()
        assert isinstance(result, list)

    def test_contains_expected_fields(self):
        """Each ratchet should have expected fields."""
        result = get_ratchets_ranking()
        for ratchet in result:
            assert "name" in ratchet
            assert "burst_resistance" in ratchet
            assert "lock_stability" in ratchet
            assert "weight_efficiency" in ratchet
            assert "total" in ratchet

    def test_sorted_by_total_desc(self):
        """Default sort should be by total descending."""
        result = get_ratchets_ranking()
        totals = [ratchet["total"] for ratchet in result]
        assert totals == sorted(totals, reverse=True)


class TestGetBitsRanking:
    """Tests for the get_bits_ranking function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_bits_ranking()
        assert isinstance(result, list)

    def test_contains_expected_fields(self):
        """Each bit should have expected fields."""
        result = get_bits_ranking()
        for bit in result:
            assert "name" in bit
            assert "category" in bit
            assert "tip_control" in bit
            assert "speed_rating" in bit
            assert "stamina_output" in bit
            assert "total" in bit

    def test_sorted_by_total_desc(self):
        """Default sort should be by total descending."""
        result = get_bits_ranking()
        totals = [bit["total"] for bit in result]
        assert totals == sorted(totals, reverse=True)


class TestPartsCounts:
    """Tests for expected part counts."""

    def test_has_blades(self):
        """Should have at least some blades."""
        data = load_parts_stats()
        assert len(data["blades"]) > 0

    def test_has_ratchets(self):
        """Should have at least some ratchets."""
        data = load_parts_stats()
        assert len(data["ratchets"]) > 0

    def test_has_bits(self):
        """Should have at least some bits."""
        data = load_parts_stats()
        assert len(data["bits"]) > 0
