"""
Unit tests for update.py module.
Tests the update pipeline functions including argument parsing, script execution,
and logging functionality.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock

import update


class TestParseArgs:
    """Tests for the parse_args function."""

    def test_default_args(self):
        """Default arguments should have all optional flags as False."""
        with patch('sys.argv', ['update.py']):
            args = update.parse_args()
            assert args.all is False
            assert args.stats_only is False
            assert args.plots_only is False
            assert args.skip_plots is False
            assert args.upload is False
            assert args.pdf is False
            assert args.verbose is False

    def test_all_flag(self):
        """--all flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--all']):
            args = update.parse_args()
            assert args.all is True

    def test_all_short_flag(self):
        """-a flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '-a']):
            args = update.parse_args()
            assert args.all is True

    def test_stats_only_flag(self):
        """--stats-only flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--stats-only']):
            args = update.parse_args()
            assert args.stats_only is True

    def test_plots_only_flag(self):
        """--plots-only flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--plots-only']):
            args = update.parse_args()
            assert args.plots_only is True

    def test_skip_plots_flag(self):
        """--skip-plots flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--skip-plots']):
            args = update.parse_args()
            assert args.skip_plots is True

    def test_skip_plots_short_flag(self):
        """-s flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '-s']):
            args = update.parse_args()
            assert args.skip_plots is True

    def test_upload_flag(self):
        """--upload flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--upload']):
            args = update.parse_args()
            assert args.upload is True

    def test_upload_short_flag(self):
        """-u flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '-u']):
            args = update.parse_args()
            assert args.upload is True

    def test_pdf_flag(self):
        """--pdf flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--pdf']):
            args = update.parse_args()
            assert args.pdf is True

    def test_pdf_short_flag(self):
        """-p flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '-p']):
            args = update.parse_args()
            assert args.pdf is True

    def test_verbose_flag(self):
        """--verbose flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--verbose']):
            args = update.parse_args()
            assert args.verbose is True

    def test_verbose_short_flag(self):
        """-v flag should be parsed correctly."""
        with patch('sys.argv', ['update.py', '-v']):
            args = update.parse_args()
            assert args.verbose is True

    def test_combined_flags(self):
        """Multiple flags should be parsed correctly."""
        with patch('sys.argv', ['update.py', '--all', '--pdf', '--upload', '-v']):
            args = update.parse_args()
            assert args.all is True
            assert args.pdf is True
            assert args.upload is True
            assert args.verbose is True
            assert args.stats_only is False


class TestDeterminePipelineStages:
    """Tests for the determine_pipeline_stages function."""

    def test_default_stages(self):
        """Default arguments should run stats, analysis, and plots."""
        with patch('sys.argv', ['update.py']):
            args = update.parse_args()
            stages = update.determine_pipeline_stages(args)
            assert stages["run_stats"] is True
            assert stages["run_analysis"] is True
            assert stages["run_plots"] is True

    def test_all_flag_enables_plots(self):
        """--all flag should enable all stages including plots."""
        with patch('sys.argv', ['update.py', '--all']):
            args = update.parse_args()
            stages = update.determine_pipeline_stages(args)
            assert stages["run_stats"] is True
            assert stages["run_analysis"] is True
            assert stages["run_plots"] is True

    def test_stats_only_disables_analysis_and_plots(self):
        """--stats-only should only run stats."""
        with patch('sys.argv', ['update.py', '--stats-only']):
            args = update.parse_args()
            stages = update.determine_pipeline_stages(args)
            assert stages["run_stats"] is True
            assert stages["run_analysis"] is False
            assert stages["run_plots"] is False

    def test_plots_only_disables_stats_and_analysis(self):
        """--plots-only should only run plots."""
        with patch('sys.argv', ['update.py', '--plots-only']):
            args = update.parse_args()
            stages = update.determine_pipeline_stages(args)
            assert stages["run_stats"] is False
            assert stages["run_analysis"] is False
            assert stages["run_plots"] is True

    def test_skip_plots_disables_plots(self):
        """--skip-plots should disable plots but keep stats and analysis."""
        with patch('sys.argv', ['update.py', '--skip-plots']):
            args = update.parse_args()
            stages = update.determine_pipeline_stages(args)
            assert stages["run_stats"] is True
            assert stages["run_analysis"] is True
            assert stages["run_plots"] is False


class TestRunScript:
    """Tests for the run_script function."""

    def test_successful_script_execution(self):
        """Successful script execution should return True and duration."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Success output",
                stderr=""
            )
            success, duration = update.run_script(
                "test_script.py",
                "Test Script"
            )
            assert success is True
            assert duration >= 0

    def test_failed_script_execution(self):
        """Failed script execution should return False."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error output"
            )
            success, duration = update.run_script(
                "test_script.py",
                "Test Script"
            )
            assert success is False
            assert duration >= 0

    def test_script_not_found(self):
        """Script not found should return False."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            success, duration = update.run_script(
                "nonexistent_script.py",
                "Nonexistent Script"
            )
            assert success is False

    def test_streaming_output(self):
        """Stream output mode should work correctly."""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = iter(["Line 1\n", "Line 2\n"])
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            success, duration = update.run_script(
                "test_script.py",
                "Test Script",
                stream_output=True
            )
            assert success is True


class TestLogStep:
    """Tests for the log_step function."""

    def test_log_step_info(self, capsys):
        """Info log level should print with arrow symbol."""
        update.log_step("Test message", "info")
        captured = capsys.readouterr()
        assert "→" in captured.out
        assert "Test message" in captured.out

    def test_log_step_success(self, capsys):
        """Success log level should print with checkmark."""
        update.log_step("Test message", "success")
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Test message" in captured.out

    def test_log_step_error(self, capsys):
        """Error log level should print with X."""
        update.log_step("Test message", "error")
        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Test message" in captured.out

    def test_log_step_header(self, capsys):
        """Header log level should print with decoration."""
        update.log_step("Test Header", "header")
        captured = capsys.readouterr()
        assert "=" in captured.out
        assert "Test Header" in captured.out

    def test_log_step_section(self, capsys):
        """Section log level should print with arrow prefix."""
        update.log_step("Test Section", "section")
        captured = capsys.readouterr()
        assert "▶" in captured.out
        assert "Test Section" in captured.out


def strip_ansi(text):
    """Remove ANSI escape sequences from text."""
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


class TestPrintSummary:
    """Tests for the print_summary function."""

    def test_print_summary_all_success(self, capsys):
        """Summary with all successes should show passed count."""
        results = [
            ("Step 1", True, 1.0),
            ("Step 2", True, 2.0),
            ("Step 3", True, 3.0),
        ]
        update.print_summary(results, 6.0)
        captured = capsys.readouterr()
        clean_out = strip_ansi(captured.out)
        assert "Passed: 3" in clean_out
        assert "completed successfully" in clean_out

    def test_print_summary_with_failures(self, capsys):
        """Summary with failures should show failure count."""
        results = [
            ("Step 1", True, 1.0),
            ("Step 2", False, 2.0),
            ("Step 3", True, 3.0),
        ]
        update.print_summary(results, 6.0)
        captured = capsys.readouterr()
        clean_out = strip_ansi(captured.out)
        assert "Passed: 2" in clean_out
        assert "Failed: 1" in clean_out
        assert "failure" in clean_out

    def test_print_summary_shows_duration(self, capsys):
        """Summary should show total duration."""
        results = [
            ("Step 1", True, 10.5),
        ]
        update.print_summary(results, 10.5)
        captured = capsys.readouterr()
        clean_out = strip_ansi(captured.out)
        assert "10.5s" in clean_out


class TestScriptPaths:
    """Tests for script path constants."""

    def test_all_script_paths_defined(self):
        """All required script paths should be defined."""
        assert hasattr(update, 'SCRIPT_BLADE_ELO')
        assert hasattr(update, 'SCRIPT_ADVANCED_STATS')
        assert hasattr(update, 'SCRIPT_RPG_STATS')
        assert hasattr(update, 'SCRIPT_UPSET_ANALYSIS')
        assert hasattr(update, 'SCRIPT_META_BALANCE')
        assert hasattr(update, 'SCRIPT_SYNERGY_HEATMAPS')
        assert hasattr(update, 'SCRIPT_COUNTER_CHECKER')
        assert hasattr(update, 'SCRIPT_COMBO_EXPLORER')
        assert hasattr(update, 'SCRIPT_GEN_PLOTS')
        assert hasattr(update, 'SCRIPT_PLOT_POSITIONS')
        assert hasattr(update, 'SCRIPT_SHEETS_UPLOAD')
        assert hasattr(update, 'SCRIPT_EXPORT_PDF')

    def test_script_paths_are_strings(self):
        """All script paths should be strings."""
        assert isinstance(update.SCRIPT_BLADE_ELO, str)
        assert isinstance(update.SCRIPT_ADVANCED_STATS, str)
        assert isinstance(update.SCRIPT_RPG_STATS, str)
        assert isinstance(update.SCRIPT_UPSET_ANALYSIS, str)
        assert isinstance(update.SCRIPT_META_BALANCE, str)
        assert isinstance(update.SCRIPT_SYNERGY_HEATMAPS, str)
        assert isinstance(update.SCRIPT_COUNTER_CHECKER, str)
        assert isinstance(update.SCRIPT_COMBO_EXPLORER, str)
        assert isinstance(update.SCRIPT_GEN_PLOTS, str)
        assert isinstance(update.SCRIPT_PLOT_POSITIONS, str)

    def test_script_paths_have_correct_extension(self):
        """All script paths should end with .py."""
        assert update.SCRIPT_BLADE_ELO.endswith('.py')
        assert update.SCRIPT_ADVANCED_STATS.endswith('.py')
        assert update.SCRIPT_RPG_STATS.endswith('.py')
        assert update.SCRIPT_UPSET_ANALYSIS.endswith('.py')
        assert update.SCRIPT_META_BALANCE.endswith('.py')
        assert update.SCRIPT_SYNERGY_HEATMAPS.endswith('.py')
        assert update.SCRIPT_COUNTER_CHECKER.endswith('.py')
        assert update.SCRIPT_COMBO_EXPLORER.endswith('.py')
        assert update.SCRIPT_GEN_PLOTS.endswith('.py')
        assert update.SCRIPT_PLOT_POSITIONS.endswith('.py')
