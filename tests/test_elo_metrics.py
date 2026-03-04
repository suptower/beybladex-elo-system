"""
Unit tests for elo_metrics.py module.
Tests metric computation functions.
"""
import sys
import os
import math
import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from elo_metrics import compute_metrics, EPSILON


class TestComputeMetrics:
    """Tests for compute_metrics()."""

    def _make_rows(self, pairs):
        """Helper: create minimal elo_history rows from (ExpA, scoreA, scoreB) tuples."""
        rows = []
        for exp_a, score_a, score_b in pairs:
            rows.append({
                'arena': 'Xtreme',
                'ExpA': str(exp_a),
                'ScoreA': str(score_a),
                'ScoreB': str(score_b),
            })
        return rows

    def test_empty_after_filter(self):
        """Returns error dict when no Xtreme rows are available."""
        rows = [{'arena': 'Drop Attack', 'ExpA': '0.5', 'ScoreA': '4', 'ScoreB': '2'}]
        result = compute_metrics(rows)
        assert 'error' in result

    def test_n_matches(self):
        """Correct match count."""
        rows = self._make_rows([(0.5, 4, 2), (0.6, 3, 4), (0.7, 4, 0)])
        result = compute_metrics(rows)
        assert result['n_matches'] == 3

    def test_perfect_accuracy(self):
        """Accuracy = 1.0 when ELO always picks the correct winner."""
        # E > 0.5 → A wins for all rows
        rows = self._make_rows([(0.6, 4, 2), (0.7, 4, 1), (0.8, 4, 0)])
        result = compute_metrics(rows)
        assert result['accuracy'] == 1.0

    def test_zero_accuracy(self):
        """Accuracy = 0 when ELO always picks the wrong winner."""
        rows = self._make_rows([(0.6, 2, 4), (0.7, 1, 4)])
        result = compute_metrics(rows)
        assert result['accuracy'] == 0.0

    def test_brier_perfect(self):
        """Brier score = 0 for a perfect model."""
        # E = 1.0 when A wins, E = 0.0 when A loses
        rows = self._make_rows([(1.0, 4, 0), (0.0, 0, 4)])
        result = compute_metrics(rows)
        assert result['brier_score'] == pytest.approx(0.0, abs=1e-6)

    def test_brier_baseline(self):
        """Brier score ≈ 0.25 for an uninformed model that always predicts 0.5."""
        rows = self._make_rows([(0.5, 4, 0), (0.5, 0, 4), (0.5, 4, 0), (0.5, 0, 4)])
        result = compute_metrics(rows)
        assert result['brier_score'] == pytest.approx(0.25, abs=1e-6)
        assert result['brier_skill'] == pytest.approx(0.0, abs=1e-6)

    def test_brier_skill_positive(self):
        """Brier skill score is positive when predictions are better than baseline."""
        # All E = 0.8 and A always wins → BS = (0.8-1)^2 = 0.04 < 0.25
        rows = self._make_rows([(0.8, 4, 0)] * 5)
        result = compute_metrics(rows)
        assert result['brier_skill'] > 0

    def test_log_loss_baseline(self):
        """Log loss ≈ ln(2) for an uninformed model that always predicts 0.5."""
        rows = self._make_rows([(0.5, 4, 0), (0.5, 0, 4)])
        result = compute_metrics(rows)
        assert result['log_loss'] == pytest.approx(math.log(2), abs=1e-4)

    def test_draws_excluded(self):
        """Draws (scoreA == scoreB) are excluded from the evaluation set."""
        rows = self._make_rows([(0.5, 2, 2), (0.6, 4, 0)])
        result = compute_metrics(rows)
        assert result['n_matches'] == 1  # draw row skipped

    def test_non_xtreme_excluded(self):
        """Non-Xtreme rows are excluded."""
        rows = self._make_rows([(0.6, 4, 0)])
        rows.append({'arena': 'Drop Attack', 'ExpA': '0.3', 'ScoreA': '4', 'ScoreB': '0'})
        result = compute_metrics(rows)
        assert result['n_matches'] == 1

    def test_calibration_present(self):
        """Calibration list is returned and each entry has required fields."""
        rows = self._make_rows([(0.55, 4, 2), (0.65, 4, 1), (0.45, 1, 4)])
        result = compute_metrics(rows)
        assert 'calibration' in result
        assert len(result['calibration']) > 0
        for entry in result['calibration']:
            assert 'label' in entry
            assert 'mean_predicted' in entry
            assert 'actual_win_rate' in entry
            assert 'count' in entry

    def test_arena_filter_field(self):
        """arena_filter field is returned correctly."""
        rows = self._make_rows([(0.5, 4, 0)])
        result = compute_metrics(rows)
        assert result['arena_filter'] == 'Xtreme'
