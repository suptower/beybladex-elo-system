"""
Unit tests for tier_flow.py module.
Tests the tier assignment and snapshot computation functions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'visualization'))

import pandas as pd
from tier_flow import (
    assign_tier_by_quantile,
    assign_tier_by_threshold,
    compute_tier_snapshots,
    build_alluvial_data,
    TIER_QUANTILES,
    TIER_ORDER,
    TIER_COLORS,
)


class TestTierQuantiles:
    """Tests for tier quantile configuration."""

    def test_quantiles_are_decreasing(self):
        """Tier quantiles should be in decreasing order (S highest)."""
        quantile_values = [TIER_QUANTILES[tier] for tier in TIER_ORDER]
        for i in range(len(quantile_values) - 1):
            assert quantile_values[i] > quantile_values[i + 1], \
                f"Quantile for {TIER_ORDER[i]} should be > {TIER_ORDER[i + 1]}"

    def test_all_tiers_have_quantiles(self):
        """All tiers should have quantile definitions."""
        for tier in TIER_ORDER:
            assert tier in TIER_QUANTILES

    def test_all_tiers_have_colors(self):
        """All tiers should have color definitions."""
        for tier in TIER_ORDER:
            assert tier in TIER_COLORS

    def test_tier_order_has_five_tiers(self):
        """Should have exactly 5 tiers (S, A, B, C, D)."""
        assert len(TIER_ORDER) == 5
        assert TIER_ORDER == ["S", "A", "B", "C", "D"]


class TestAssignTierByQuantile:
    """Tests for the assign_tier_by_quantile function."""

    def test_top_elo_gets_s_tier(self):
        """Highest ELO should be assigned S tier."""
        elo_values = [900, 950, 1000, 1050, 1100, 1150, 1200]
        result = assign_tier_by_quantile(1200, elo_values)
        assert result == "S"

    def test_bottom_elo_gets_d_tier(self):
        """Lowest ELO should be assigned D tier."""
        elo_values = [900, 950, 1000, 1050, 1100, 1150, 1200]
        result = assign_tier_by_quantile(900, elo_values)
        assert result == "D"

    def test_middle_elo_gets_middle_tier(self):
        """Middle ELO should be assigned B or C tier."""
        elo_values = [900, 950, 1000, 1050, 1100, 1150, 1200]
        result = assign_tier_by_quantile(1000, elo_values)
        assert result in ["B", "C"]

    def test_empty_values_returns_default(self):
        """Empty ELO list should return default tier (C)."""
        result = assign_tier_by_quantile(1000, [])
        assert result == "C"

    def test_single_value_returns_s_tier(self):
        """Single ELO value should return S tier (top 100%)."""
        result = assign_tier_by_quantile(1000, [1000])
        assert result == "S"

    def test_two_values_distribution(self):
        """With two values, higher should be S, lower should be lower tier."""
        elo_values = [900, 1100]
        high_tier = assign_tier_by_quantile(1100, elo_values)
        low_tier = assign_tier_by_quantile(900, elo_values)
        # Higher value should have better tier
        assert TIER_ORDER.index(high_tier) <= TIER_ORDER.index(low_tier)


class TestAssignTierByThreshold:
    """Tests for the assign_tier_by_threshold function."""

    def test_high_elo_gets_s_tier(self):
        """ELO >= 1100 should be S tier."""
        assert assign_tier_by_threshold(1100) == "S"
        assert assign_tier_by_threshold(1150) == "S"
        assert assign_tier_by_threshold(1200) == "S"

    def test_a_tier_range(self):
        """ELO 1050-1099 should be A tier."""
        assert assign_tier_by_threshold(1050) == "A"
        assert assign_tier_by_threshold(1075) == "A"
        assert assign_tier_by_threshold(1099) == "A"

    def test_b_tier_range(self):
        """ELO 1000-1049 should be B tier."""
        assert assign_tier_by_threshold(1000) == "B"
        assert assign_tier_by_threshold(1025) == "B"
        assert assign_tier_by_threshold(1049) == "B"

    def test_c_tier_range(self):
        """ELO 950-999 should be C tier."""
        assert assign_tier_by_threshold(950) == "C"
        assert assign_tier_by_threshold(975) == "C"
        assert assign_tier_by_threshold(999) == "C"

    def test_low_elo_gets_d_tier(self):
        """ELO < 950 should be D tier."""
        assert assign_tier_by_threshold(949) == "D"
        assert assign_tier_by_threshold(900) == "D"
        assert assign_tier_by_threshold(800) == "D"


class TestComputeTierSnapshots:
    """Tests for the compute_tier_snapshots function."""

    def test_empty_dataframe_returns_empty(self):
        """Empty DataFrame should return empty list."""
        df = pd.DataFrame()
        result = compute_tier_snapshots(df)
        assert result == []

    def test_single_match_index(self):
        """Single match index should create snapshots."""
        df = pd.DataFrame({
            "Date": ["2025-01-01", "2025-01-01", "2025-01-01"],
            "Bey": ["BeyA", "BeyB", "BeyC"],
            "ELO": [1100, 1000, 900],
            "MatchIndex": [1, 1, 1]
        })
        df["Date"] = pd.to_datetime(df["Date"])
        result = compute_tier_snapshots(df, num_slices=1)
        assert len(result) == 1
        assert len(result[0]["beys"]) == 3

    def test_multiple_match_indices(self):
        """Multiple match indices should create multiple snapshots."""
        df = pd.DataFrame({
            "Date": ["2025-01-01"] * 6,
            "Bey": ["BeyA", "BeyB", "BeyA", "BeyB", "BeyA", "BeyB"],
            "ELO": [1000, 1000, 1050, 950, 1100, 900],
            "MatchIndex": [1, 1, 2, 2, 3, 3]
        })
        df["Date"] = pd.to_datetime(df["Date"])
        result = compute_tier_snapshots(df, num_slices=2)
        assert len(result) >= 1

    def test_tier_assignments_in_snapshots(self):
        """Each bey in snapshot should have tier assignment."""
        df = pd.DataFrame({
            "Date": ["2025-01-01"] * 3,
            "Bey": ["BeyA", "BeyB", "BeyC"],
            "ELO": [1100, 1000, 900],
            "MatchIndex": [1, 1, 1]
        })
        df["Date"] = pd.to_datetime(df["Date"])
        result = compute_tier_snapshots(df, num_slices=1)

        for bey_data in result[0]["beys"]:
            assert "tier" in bey_data
            assert bey_data["tier"] in TIER_ORDER


class TestBuildAlluvialData:
    """Tests for the build_alluvial_data function."""

    def test_empty_snapshots_returns_empty(self):
        """Empty snapshots should return empty data."""
        result = build_alluvial_data([], {})
        assert result["nodes"] == []
        assert result["links"] == []

    def test_single_snapshot_returns_empty_links(self):
        """Single snapshot should have no links (need 2 for flow)."""
        snapshots = [{
            "slice_index": 0,
            "match_index": 1,
            "label": "Match 1",
            "beys": [{"bey": "BeyA", "elo": 1000, "tier": "B"}],
            "elo_range": (1000, 1000)
        }]
        result = build_alluvial_data(snapshots, {})
        # With only one snapshot, we get minimal return with empty links list
        assert result["links"] == []

    def test_two_snapshots_creates_links(self):
        """Two snapshots with same bey should create links."""
        snapshots = [
            {
                "slice_index": 0,
                "match_index": 1,
                "label": "Match 1",
                "beys": [{"bey": "BeyA", "elo": 1000, "tier": "B"}],
                "elo_range": (1000, 1000)
            },
            {
                "slice_index": 1,
                "match_index": 2,
                "label": "Match 2",
                "beys": [{"bey": "BeyA", "elo": 1050, "tier": "A"}],
                "elo_range": (1050, 1050)
            }
        ]
        result = build_alluvial_data(snapshots, {})
        assert len(result["nodes"]) == 2
        assert len(result["link_sources"]) == 1

    def test_link_labels_indicate_flow_direction(self):
        """Link labels should indicate rising, falling, or stable."""
        snapshots = [
            {
                "slice_index": 0,
                "match_index": 1,
                "label": "Match 1",
                "beys": [{"bey": "BeyA", "elo": 1000, "tier": "B"}],
                "elo_range": (1000, 1000)
            },
            {
                "slice_index": 1,
                "match_index": 2,
                "label": "Match 2",
                "beys": [{"bey": "BeyA", "elo": 1100, "tier": "S"}],
                "elo_range": (1100, 1100)
            }
        ]
        result = build_alluvial_data(snapshots, {})
        assert len(result["links"]) == 1
        assert result["links"][0]["flow_type"] == "rising"

    def test_alluvial_includes_node_positions(self):
        """Alluvial data should include pre-calculated x and y positions."""
        snapshots = [
            {
                "slice_index": 0,
                "match_index": 1,
                "label": "Match 1",
                "beys": [{"bey": "BeyA", "elo": 1000, "tier": "B"}],
                "elo_range": (1000, 1000)
            },
            {
                "slice_index": 1,
                "match_index": 2,
                "label": "Match 2",
                "beys": [{"bey": "BeyA", "elo": 1050, "tier": "A"}],
                "elo_range": (1050, 1050)
            }
        ]
        result = build_alluvial_data(snapshots, {})
        assert "node_x" in result
        assert "node_y" in result
        assert len(result["node_x"]) == len(result["nodes"])
        assert len(result["node_y"]) == len(result["nodes"])


class TestTierFlowIntegration:
    """Integration tests for the complete tier flow pipeline."""

    def test_full_pipeline_with_sample_data(self):
        """Test complete pipeline with sample data."""
        # Create sample timeseries data
        df = pd.DataFrame({
            "Date": ["2025-01-01"] * 9,
            "Bey": ["BeyA", "BeyB", "BeyC"] * 3,
            "ELO": [
                1000, 1000, 1000,  # Match 1: All equal
                1050, 950, 1000,   # Match 2: A rises, B falls
                1100, 900, 1000,   # Match 3: A rises more, B falls more
            ],
            "MatchIndex": [1, 1, 1, 2, 2, 2, 3, 3, 3]
        })
        df["Date"] = pd.to_datetime(df["Date"])

        # Compute snapshots
        snapshots = compute_tier_snapshots(df, num_slices=3)
        assert len(snapshots) >= 2

        # Build alluvial data
        alluvial_data = build_alluvial_data(snapshots, {})
        assert len(alluvial_data["nodes"]) > 0
        assert len(alluvial_data["link_sources"]) > 0
