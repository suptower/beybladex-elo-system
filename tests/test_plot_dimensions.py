import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plot_styles import calculate_dynamic_plot_dimensions


class TestDynamicPlotDimensions:
    """Tests for dynamic plot dimension calculation."""

    def test_small_range(self):
        """Test dimensions for a small position range."""
        # Range of 3 positions (27-30)
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(27, 30)

        # Should have minimum height
        assert height >= 3.0
        # Y-limits should be close to data range with small padding
        assert ylim_max < 27
        assert ylim_min > 30
        # Visible range should be reasonable
        visible_range = ylim_min - ylim_max
        assert visible_range < 10

    def test_top_positions(self):
        """Test dimensions for top-tier positions (1-5)."""
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(1, 5)

        # Should start from 0.5 for top positions
        assert ylim_max == 0.5
        # Height should be minimum
        assert height >= 3.0
        # Should show small range
        visible_range = ylim_min - ylim_max
        assert visible_range < 10

    def test_mid_range_positions(self):
        """Test dimensions for mid-range positions."""
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(17, 20)

        # Should have appropriate padding
        assert ylim_max < 17
        assert ylim_min > 20
        # Height should be minimum
        assert height >= 3.0

    def test_large_range(self):
        """Test dimensions for large position range."""
        # Range of 39 positions (4-43)
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(4, 43)

        # Should have larger height
        assert height > 5.0
        # Should not exceed maximum
        assert height <= 12.0
        # Y-limits should accommodate full range
        assert ylim_max <= 4
        assert ylim_min >= 43

    def test_full_range(self):
        """Test dimensions when spanning full leaderboard."""
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(1, 43)

        # Should have maximum allowed height
        assert height > 7.0
        assert height <= 12.0
        # Should start from 0.5 since it includes position 1
        assert ylim_max == 0.5

    def test_ylim_order(self):
        """Test that y-limits are in correct order (inverted for position)."""
        height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(10, 20)

        # For position plots, ylim_max (top) < ylim_min (bottom)
        assert ylim_max < ylim_min

    def test_visible_range_calculation(self):
        """Test that visible range is reasonable."""
        test_cases = [
            (27, 30),
            (1, 5),
            (17, 20),
            (4, 43),
        ]

        for min_pos, max_pos in test_cases:
            height, ylim_max, ylim_min = calculate_dynamic_plot_dimensions(min_pos, max_pos)
            visible_range = ylim_min - ylim_max
            data_range = max_pos - min_pos

            # Visible range should be larger than data range (due to padding)
            assert visible_range > data_range
            # But not excessively larger
            assert visible_range < data_range * 3

    def test_height_scaling(self):
        """Test that height scales appropriately with range."""
        small_range = calculate_dynamic_plot_dimensions(27, 30)
        medium_range = calculate_dynamic_plot_dimensions(1, 17)
        large_range = calculate_dynamic_plot_dimensions(4, 43)

        # Larger ranges should have larger heights
        assert small_range[0] <= medium_range[0]
        assert medium_range[0] <= large_range[0]
