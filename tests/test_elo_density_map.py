"""
Unit tests for elo_density_map.py module.
Tests the ELO density computation and analysis functions.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'visualization')
)

import pandas as pd
from elo_density_map import (
    compute_histogram_data,
    compute_kde,
    compute_elo_snapshots,
    compute_density_matrix,
    compute_summary_statistics,
    DEFAULT_BINS,
)


class TestComputeHistogramData:
    """Tests for the compute_histogram_data function."""

    def test_empty_values_returns_empty_dict(self):
        """Empty input should return empty lists."""
        result = compute_histogram_data([])
        assert result["bin_edges"] == []
        assert result["bin_centers"] == []
        assert result["counts"] == []
        assert result["density"] == []

    def test_single_value(self):
        """Single value should produce valid histogram."""
        result = compute_histogram_data([1000])
        assert len(result["bin_edges"]) == DEFAULT_BINS + 1
        assert len(result["bin_centers"]) == DEFAULT_BINS
        assert len(result["counts"]) == DEFAULT_BINS
        assert sum(result["counts"]) == 1

    def test_multiple_values(self):
        """Multiple values should distribute across bins."""
        elos = [900, 950, 1000, 1050, 1100]
        result = compute_histogram_data(elos)
        assert sum(result["counts"]) == len(elos)
        assert sum(result["density"]) > 0.99  # Should sum to ~1

    def test_custom_range(self):
        """Custom range should be respected."""
        elos = [1000, 1010, 1020]
        result = compute_histogram_data(elos, range_min=900, range_max=1100)
        assert result["bin_edges"][0] == 900
        assert result["bin_edges"][-1] == 1100

    def test_custom_bins(self):
        """Custom bin count should be respected."""
        elos = [1000, 1050, 1100]
        bins = 10
        result = compute_histogram_data(elos, bins=bins)
        assert len(result["bin_centers"]) == bins
        assert len(result["counts"]) == bins

    def test_density_sums_to_one(self):
        """Density values should sum to approximately 1."""
        elos = [900, 950, 1000, 1050, 1100, 1150]
        result = compute_histogram_data(elos)
        assert abs(sum(result["density"]) - 1.0) < 0.01


class TestComputeKDE:
    """Tests for the compute_kde function."""

    def test_empty_values_returns_empty(self):
        """Less than 2 values should return empty result."""
        result = compute_kde([])
        assert result["x"] == []
        assert result["density"] == []
        assert result["bandwidth"] == 0

    def test_single_value_returns_empty(self):
        """Single value should return empty (needs 2+ for KDE)."""
        result = compute_kde([1000])
        assert result["x"] == []
        assert result["density"] == []

    def test_two_values(self):
        """Two values should produce valid KDE."""
        result = compute_kde([1000, 1050])
        assert len(result["x"]) == 200  # Default num_points
        assert len(result["density"]) == 200
        assert result["bandwidth"] > 0

    def test_kde_is_smooth(self):
        """KDE should produce a smooth curve."""
        elos = [900, 950, 1000, 1050, 1100]
        result = compute_kde(elos)

        # Check that density values are non-negative
        assert all(d >= 0 for d in result["density"])

        # Check that density has a peak near the center
        max_idx = result["density"].index(max(result["density"]))
        assert 50 < max_idx < 150  # Peak should be roughly in middle

    def test_custom_range(self):
        """Custom x_range should be respected."""
        elos = [1000, 1050, 1100]
        result = compute_kde(elos, x_range=(900, 1200))
        assert min(result["x"]) >= 900
        assert max(result["x"]) <= 1200

    def test_custom_bandwidth(self):
        """Custom bandwidth should be respected."""
        elos = [1000, 1050, 1100]
        result = compute_kde(elos, bandwidth=20)
        assert result["bandwidth"] == 20.0

    def test_num_points(self):
        """Custom num_points should be respected."""
        elos = [1000, 1050]
        result = compute_kde(elos, num_points=50)
        assert len(result["x"]) == 50
        assert len(result["density"]) == 50


class TestComputeEloSnapshots:
    """Tests for the compute_elo_snapshots function."""

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty list."""
        df = pd.DataFrame()
        result = compute_elo_snapshots(df)
        assert result == []

    def test_single_bey_single_match(self):
        """Single Bey with one match."""
        df = pd.DataFrame({
            "Date": ["2025-01-01"],
            "Bey": ["TestBey"],
            "ELO": [1000],
            "MatchIndex": [0],
        })
        result = compute_elo_snapshots(df)
        assert len(result) == 1
        assert result[0]["match_index"] == 0
        assert result[0]["elo_values"] == [1000.0]
        assert result[0]["mean"] == 1000.0

    def test_multiple_beys(self):
        """Multiple Beys should all be included."""
        df = pd.DataFrame({
            "Date": ["2025-01-01"] * 3,
            "Bey": ["Bey1", "Bey2", "Bey3"],
            "ELO": [900, 1000, 1100],
            "MatchIndex": [0, 0, 0],
        })
        result = compute_elo_snapshots(df)
        assert len(result) == 1
        assert result[0]["count"] == 3
        assert set(result[0]["elo_values"]) == {900.0, 1000.0, 1100.0}

    def test_multiple_match_indices(self):
        """Multiple match indices should create multiple snapshots."""
        df = pd.DataFrame({
            "Date": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-02"],
            "Bey": ["Bey1", "Bey1", "Bey1", "Bey1"],
            "ELO": [1000, 1020, 1040, 1060],
            "MatchIndex": [0, 1, 2, 3],
        })
        result = compute_elo_snapshots(df)
        assert len(result) == 4

    def test_snapshot_statistics(self):
        """Statistics should be calculated correctly."""
        df = pd.DataFrame({
            "Date": ["2025-01-01"] * 3,
            "Bey": ["Bey1", "Bey2", "Bey3"],
            "ELO": [900, 1000, 1100],
            "MatchIndex": [0, 0, 0],
        })
        result = compute_elo_snapshots(df)
        snap = result[0]

        assert snap["mean"] == 1000.0
        assert snap["median"] == 1000.0
        assert snap["min"] == 900.0
        assert snap["max"] == 1100.0
        assert snap["std"] > 0


class TestComputeDensityMatrix:
    """Tests for the compute_density_matrix function."""

    def test_empty_snapshots(self):
        """Empty snapshots should return empty result."""
        result = compute_density_matrix([])
        assert result["matrix"] == []
        assert result["match_indices"] == []

    def test_single_snapshot(self):
        """Single snapshot should create 1-row matrix."""
        snapshots = [{
            "match_index": 0,
            "elo_values": [900, 1000, 1100],
            "mean": 1000, "median": 1000, "std": 81.6,
            "min": 900, "max": 1100, "count": 3
        }]
        result = compute_density_matrix(snapshots, bins=10)
        assert len(result["matrix"]) == 1
        assert len(result["matrix"][0]) == 10
        assert len(result["bin_centers"]) == 10

    def test_multiple_snapshots(self):
        """Multiple snapshots should create multi-row matrix."""
        snapshots = [
            {"match_index": 0, "elo_values": [1000], "mean": 1000, "median": 1000,
             "std": 0, "min": 1000, "max": 1000, "count": 1},
            {"match_index": 1, "elo_values": [1000, 1050], "mean": 1025, "median": 1025,
             "std": 25, "min": 1000, "max": 1050, "count": 2},
        ]
        result = compute_density_matrix(snapshots, bins=10)
        assert len(result["matrix"]) == 2
        assert result["match_indices"] == [0, 1]

    def test_custom_global_range(self):
        """Custom global range should be respected."""
        snapshots = [{
            "match_index": 0, "elo_values": [1000],
            "mean": 1000, "median": 1000, "std": 0,
            "min": 1000, "max": 1000, "count": 1
        }]
        result = compute_density_matrix(
            snapshots, bins=10, global_range=(900, 1100)
        )
        assert result["bin_edges"][0] == 900
        assert result["bin_edges"][-1] == 1100


class TestComputeSummaryStatistics:
    """Tests for the compute_summary_statistics function."""

    def test_empty_snapshots(self):
        """Empty snapshots should return empty stats."""
        result = compute_summary_statistics([])
        assert result["match_indices"] == []
        assert result["means"] == []

    def test_single_snapshot(self):
        """Single snapshot should have single values."""
        snapshots = [{
            "match_index": 0,
            "elo_values": [900, 1000, 1100],
            "mean": 1000.0,
            "median": 1000.0,
            "std": 81.65,
            "min": 900.0,
            "max": 1100.0,
            "count": 3,
        }]
        result = compute_summary_statistics(snapshots)
        assert len(result["match_indices"]) == 1
        assert result["means"][0] == 1000.0
        assert result["medians"][0] == 1000.0
        assert result["ranges"][0] == 200.0  # 1100 - 900

    def test_multiple_snapshots(self):
        """Multiple snapshots should track changes over time."""
        snapshots = [
            {"match_index": 0, "elo_values": [1000], "mean": 1000, "median": 1000,
             "std": 0, "min": 1000, "max": 1000, "count": 1},
            {"match_index": 1, "elo_values": [900, 1100], "mean": 1000, "median": 1000,
             "std": 100, "min": 900, "max": 1100, "count": 2},
        ]
        result = compute_summary_statistics(snapshots)
        assert len(result["match_indices"]) == 2
        assert result["stds"][0] == 0
        assert result["stds"][1] == 100

    def test_skewness_calculation(self):
        """Skewness should be calculated for distributions."""
        # Symmetric distribution should have near-zero skewness
        snapshots = [{
            "match_index": 0,
            "elo_values": [900, 950, 1000, 1050, 1100],
            "mean": 1000.0,
            "median": 1000.0,
            "std": 70.7,
            "min": 900.0,
            "max": 1100.0,
            "count": 5,
        }]
        result = compute_summary_statistics(snapshots)
        assert abs(result["skewness"][0]) < 0.5  # Should be near zero

    def test_skewness_with_low_std(self):
        """Skewness should be 0 when std is 0."""
        snapshots = [{
            "match_index": 0,
            "elo_values": [1000, 1000],
            "mean": 1000.0,
            "median": 1000.0,
            "std": 0.0,
            "min": 1000.0,
            "max": 1000.0,
            "count": 2,
        }]
        result = compute_summary_statistics(snapshots)
        assert result["skewness"][0] == 0.0


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_pipeline(self):
        """Test full pipeline from data to snapshots to matrix."""
        # Create sample data
        df = pd.DataFrame({
            "Date": pd.date_range("2025-01-01", periods=10, freq="D"),
            "Bey": ["Bey1"] * 5 + ["Bey2"] * 5,
            "ELO": [1000, 1020, 1040, 1060, 1080,
                    1000, 980, 960, 940, 920],
            "MatchIndex": [0, 1, 2, 3, 4, 0, 1, 2, 3, 4],
        })

        # Compute snapshots
        snapshots = compute_elo_snapshots(df)
        assert len(snapshots) == 5

        # Compute density matrix
        density_data = compute_density_matrix(snapshots, bins=10)
        assert len(density_data["matrix"]) == 5

        # Compute summary stats
        stats = compute_summary_statistics(snapshots)
        assert len(stats["match_indices"]) == 5

        # Mean should stay at 1000 (symmetric changes)
        for mean in stats["means"]:
            assert abs(mean - 1000) < 1

    def test_histogram_and_kde_consistency(self):
        """Histogram and KDE should both peak near same location."""
        elos = [900, 950, 1000, 1050, 1100]

        hist_data = compute_histogram_data(elos, bins=20)
        kde_data = compute_kde(elos)

        # Find peak locations
        hist_peak_idx = hist_data["counts"].index(max(hist_data["counts"]))
        hist_peak_elo = hist_data["bin_centers"][hist_peak_idx]

        kde_peak_idx = kde_data["density"].index(max(kde_data["density"]))
        kde_peak_elo = kde_data["x"][kde_peak_idx]

        # Both peaks should be near 1000 (within 150 ELO range)
        assert abs(hist_peak_elo - 1000) < 150
        assert abs(kde_peak_elo - 1000) < 50
