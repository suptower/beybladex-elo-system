import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gen_plots import generate_dynamic_yticks


class TestDynamicYticks:
    """Tests for dynamic ytick generation."""

    def test_small_range(self):
        """Test yticks for a small position range."""
        # Range of 4 positions (27-30)
        yticks = generate_dynamic_yticks(27, 30, 43)

        # Should include 1 (always), min, max, and positions in between
        assert 1 in yticks
        assert 27 in yticks
        assert 30 in yticks
        # Should have reasonable number of ticks
        assert 3 <= len(yticks) <= 8

    def test_medium_range(self):
        """Test yticks for a medium position range."""
        # Range of 16 positions (1-17)
        yticks = generate_dynamic_yticks(1, 17, 43)

        # Should include 1 (best position), max, and intermediate values
        assert 1 in yticks
        assert 17 in yticks
        # Should use step of 5 for this range
        assert 5 in yticks or 10 in yticks or 15 in yticks
        # Should have reasonable number of ticks
        assert 3 <= len(yticks) <= 8

    def test_large_range(self):
        """Test yticks for a large position range."""
        # Range of 39 positions (4-43)
        yticks = generate_dynamic_yticks(4, 43, 43)

        # Should include 1 (always), min, max
        assert 1 in yticks
        assert 4 in yticks
        assert 43 in yticks
        # Should use step of 10 for this range
        assert 10 in yticks or 20 in yticks or 30 in yticks
        # Should have reasonable number of ticks (not too many)
        assert 3 <= len(yticks) <= 10

    def test_full_range(self):
        """Test yticks when bey has visited all positions."""
        # Full range from 1 to 43
        yticks = generate_dynamic_yticks(1, 43, 43)

        # Should include 1 and 43
        assert 1 in yticks
        assert 43 in yticks
        # Should not be too many ticks
        assert len(yticks) <= 10

    def test_mid_range_positions(self):
        """Test yticks for positions that don't start at 1."""
        # Range from 17-33 (medium-low tier beys)
        yticks = generate_dynamic_yticks(17, 33, 43)

        # Should always include position 1 for reference
        assert 1 in yticks
        # Should include actual min and max
        assert 17 in yticks
        assert 33 in yticks
        # Should have intermediate ticks with appropriate spacing
        assert 20 in yticks or 25 in yticks or 30 in yticks

    def test_yticks_sorted(self):
        """Test that yticks are sorted in ascending order."""
        yticks = generate_dynamic_yticks(7, 38, 43)
        assert yticks == sorted(yticks)

    def test_yticks_unique(self):
        """Test that yticks contain no duplicates."""
        yticks = generate_dynamic_yticks(7, 38, 43)
        assert len(yticks) == len(set(yticks))

    def test_very_small_range(self):
        """Test yticks for very small range (e.g., 3 positions)."""
        # Range of 3 positions
        yticks = generate_dynamic_yticks(27, 30, 43)

        # Should include 1, and all positions in the range
        assert 1 in yticks
        assert 27 in yticks
        assert 28 in yticks or 29 in yticks  # Should have intermediate ticks
        assert 30 in yticks

    def test_high_positions_only(self):
        """Test yticks for beys that only exist in high (bad) positions."""
        # Range from 35-42
        yticks = generate_dynamic_yticks(35, 42, 43)

        # Should include 1 for reference
        assert 1 in yticks
        # Should include the actual range
        assert 35 in yticks
        assert 42 in yticks
        # Should have some intermediate ticks
        assert 40 in yticks or 38 in yticks

    def test_top_positions_only(self):
        """Test yticks for consistently top-performing beys."""
        # Range from 1-5 (very good bey)
        yticks = generate_dynamic_yticks(1, 5, 43)

        # Should include all positions in this small range
        assert 1 in yticks
        assert 5 in yticks
        # Should have intermediate values for such a small range
        assert len([t for t in yticks if 1 <= t <= 5]) >= 3
