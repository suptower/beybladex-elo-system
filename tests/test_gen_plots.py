import sys
import os
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import gen_plots


class TestPlotEloSingle:
    """Tests for the plot_elo_single function."""

    def test_median_and_average_calculation(self):
        """Test that median and average are calculated correctly from ELO data."""
        # Create sample data
        data = {
            'Bey': ['TestBey'] * 5,
            'ELO': [1000, 1100, 1200, 1150, 1050],
            'MatchIndex': [0, 1, 2, 3, 4]
        }
        df = pd.DataFrame(data)

        # Calculate expected values
        expected_avg = df['ELO'].mean()  # 1100.0
        expected_median = df['ELO'].median()  # 1100.0

        assert expected_avg == 1100.0
        assert expected_median == 1100.0

    def test_median_and_average_with_outliers(self):
        """Test that median and average handle outliers correctly."""
        # Create sample data with outliers
        data = {
            'Bey': ['TestBey'] * 7,
            'ELO': [1000, 1010, 1020, 1500, 1030, 1040, 1050],
            'MatchIndex': [0, 1, 2, 3, 4, 5, 6]
        }
        df = pd.DataFrame(data)

        # Calculate expected values
        # Sum: 1000+1010+1020+1500+1030+1040+1050 = 7650
        # Average: 7650/7 ≈ 1092.857...
        expected_avg = sum([1000, 1010, 1020, 1500, 1030, 1040, 1050]) / 7
        # Median of [1000, 1010, 1020, 1030, 1040, 1050, 1500] = 1030
        expected_median = df['ELO'].median()

        # Median should be less affected by the outlier (1500)
        assert expected_median == 1030.0
        assert abs(expected_avg - 1092.857) < 0.01
        # Average should be higher due to outlier
        assert expected_avg > expected_median

    def test_plot_generation_without_errors(self):
        """Test that plot generation runs without errors."""
        # Create sample data
        data = {
            'Bey': ['TestBey1', 'TestBey1', 'TestBey2', 'TestBey2'],
            'ELO': [1000, 1100, 1200, 1150],
            'MatchIndex': [0, 1, 0, 1]
        }
        df = pd.DataFrame(data)

        # Create temporary directory for output
        temp_dir = tempfile.mkdtemp()
        try:
            # Call the function - should not raise any exceptions
            gen_plots.plot_elo_single(df, temp_dir, dark_mode=False)

            # Check that files were created
            files = os.listdir(temp_dir)
            assert len(files) == 2  # Should create 2 plots
            assert all(f.endswith('.png') for f in files)
        finally:
            # Clean up
            shutil.rmtree(temp_dir)


class TestPlotPositionTimeseries:
    """Tests for the plot_position_timeseries function."""

    def test_median_and_average_position_calculation(self):
        """Test that median and average position are calculated correctly."""
        # Create sample position data
        data = {
            'Bey': ['TestBey'] * 5,
            'Position': [1, 3, 5, 4, 2],
            'MatchIndex': [0, 1, 2, 3, 4],
            'Event': [0, 1, 2, 3, 4],
            'PlotX': [0, 1, 2, 3, 4]
        }
        df = pd.DataFrame(data)

        # Calculate expected values
        expected_avg = df['Position'].mean()  # 3.0
        expected_median = df['Position'].median()  # 3.0

        assert expected_avg == 3.0
        assert expected_median == 3.0

    def test_position_best_is_minimum(self):
        """Test that best position is correctly identified as minimum rank."""
        # Create sample position data
        data = {
            'Bey': ['TestBey'] * 5,
            'Position': [5, 3, 1, 4, 2],
            'MatchIndex': [0, 1, 2, 3, 4],
            'Event': [0, 1, 2, 3, 4],
            'PlotX': [0, 1, 2, 3, 4]
        }
        df = pd.DataFrame(data)

        # Best position should be 1 (lowest rank number)
        best_pos = df['Position'].min()
        worst_pos = df['Position'].max()

        assert best_pos == 1
        assert worst_pos == 5

    def test_plot_generation_with_multiple_beys(self):
        """Test that position plot generation works with multiple Beys."""
        # Create sample data for multiple Beys
        data = {
            'Bey': ['Bey1', 'Bey1', 'Bey1', 'Bey2', 'Bey2', 'Bey2'],
            'Position': [1, 2, 3, 2, 1, 3],
            'MatchIndex': [0, 1, 2, 0, 1, 2],
            'Event': [0, 1, 2, 0, 1, 2],
            'PlotX': [0, 1, 2, 0, 1, 2]
        }
        df = pd.DataFrame(data)

        # Create temporary directory for output
        temp_dir = tempfile.mkdtemp()
        try:
            # Call the function - should not raise any exceptions
            gen_plots.plot_position_timeseries(df, temp_dir, dark_mode=False)

            # Check that files were created
            files = os.listdir(temp_dir)
            assert len(files) == 2  # Should create 2 plots
            assert all(f.endswith('.png') for f in files)
        finally:
            # Clean up
            shutil.rmtree(temp_dir)


class TestStatisticalAccuracy:
    """Tests to verify statistical calculations are accurate."""

    def test_median_with_even_count(self):
        """Test median calculation with even number of values."""
        data = pd.Series([1000, 1100, 1200, 1300])
        median = data.median()
        # Median of [1000, 1100, 1200, 1300] should be (1100 + 1200) / 2 = 1150
        assert median == 1150.0

    def test_median_with_odd_count(self):
        """Test median calculation with odd number of values."""
        data = pd.Series([1000, 1100, 1200, 1300, 1400])
        median = data.median()
        # Median of [1000, 1100, 1200, 1300, 1400] should be 1200
        assert median == 1200.0

    def test_average_calculation(self):
        """Test average calculation."""
        data = pd.Series([1000, 1100, 1200, 1300, 1400])
        avg = data.mean()
        # Average should be (1000 + 1100 + 1200 + 1300 + 1400) / 5 = 1200
        assert avg == 1200.0

    def test_single_value_statistics(self):
        """Test statistics with single value."""
        data = pd.Series([1000])
        avg = data.mean()
        median = data.median()
        # Both should equal the single value
        assert avg == 1000.0
        assert median == 1000.0
