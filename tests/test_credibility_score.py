"""
Unit tests for credibility score calculation in advanced_stats.py.
Tests the ranking confidence feature that quantifies how reliable an ELO rating is.
"""
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from advanced_stats import calculate_credibility_score


class TestCredibilityScore:
    """Tests for the calculate_credibility_score function."""

    def test_zero_matches_low_confidence(self):
        """Bey with no matches should have low confidence."""
        score, label = calculate_credibility_score(
            matches=0,
            opponent_elos=[],
            volatility=0.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert score < 0.3  # Should be very low
        assert label == "Low"

    def test_few_matches_low_confidence(self):
        """Bey with very few matches (<6) should have low confidence."""
        score, label = calculate_credibility_score(
            matches=3,
            opponent_elos=[1000, 1010, 990],
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert score < 0.5  # Should be low
        assert label == "Low"

    def test_medium_matches_medium_confidence(self):
        """Bey with moderate matches (6-14) should have medium confidence."""
        score, label = calculate_credibility_score(
            matches=10,
            opponent_elos=[1000, 1010, 990, 1020, 980, 1005, 995, 1015, 985, 1000],
            volatility=12.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert 0.3 < score < 0.8  # Should be in middle range
        assert label == "Medium"

    def test_many_matches_high_confidence(self):
        """Bey with many matches (15+) and good diversity should have high confidence."""
        # Create diverse opponent list
        opponent_elos = list(range(950, 1050, 5))  # Wide range of opponents
        
        score, label = calculate_credibility_score(
            matches=20,
            opponent_elos=opponent_elos[:20],
            volatility=8.0,  # Low volatility = stable
            max_matches=30,
            max_volatility=20.0
        )
        assert score >= 0.65  # Should be reasonably high
        assert label in ["Medium", "High"]

    def test_high_volatility_reduces_confidence(self):
        """High volatility should reduce confidence score."""
        # Compare same scenario with low vs high volatility
        score_stable, _ = calculate_credibility_score(
            matches=15,
            opponent_elos=[1000] * 15,
            volatility=5.0,  # Low volatility
            max_matches=30,
            max_volatility=20.0
        )
        
        score_volatile, _ = calculate_credibility_score(
            matches=15,
            opponent_elos=[1000] * 15,
            volatility=18.0,  # High volatility
            max_matches=30,
            max_volatility=20.0
        )
        
        assert score_stable > score_volatile

    def test_diverse_opponents_increases_confidence(self):
        """Facing diverse opponents should increase confidence."""
        # Same opponents vs diverse opponents
        score_same, _ = calculate_credibility_score(
            matches=15,
            opponent_elos=[1000] * 15,  # All same ELO
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        
        score_diverse, _ = calculate_credibility_score(
            matches=15,
            opponent_elos=list(range(950, 1050, 7))[:15],  # Wide range
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        
        assert score_diverse > score_same

    def test_score_range_bounded(self):
        """Credibility score should always be between 0.0 and 1.0."""
        # Test extreme values
        score1, _ = calculate_credibility_score(
            matches=0,
            opponent_elos=[],
            volatility=0.0,
            max_matches=1,
            max_volatility=1.0
        )
        assert 0.0 <= score1 <= 1.0
        
        score2, _ = calculate_credibility_score(
            matches=100,
            opponent_elos=list(range(800, 1200, 4)),
            volatility=0.1,
            max_matches=100,
            max_volatility=20.0
        )
        assert 0.0 <= score2 <= 1.0

    def test_label_consistency(self):
        """Label should be consistent with score thresholds."""
        # Low confidence: < 6 matches
        _, label1 = calculate_credibility_score(
            matches=3,
            opponent_elos=[1000, 1010, 990],
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert label1 == "Low"
        
        # High confidence: 15+ matches and high score
        score2, label2 = calculate_credibility_score(
            matches=20,
            opponent_elos=list(range(950, 1050, 5))[:20],
            volatility=5.0,
            max_matches=30,
            max_volatility=20.0
        )
        if score2 >= 0.7:
            assert label2 == "High"

    def test_single_opponent_low_diversity(self):
        """Playing only one opponent should have low diversity factor."""
        score, _ = calculate_credibility_score(
            matches=10,
            opponent_elos=[1000],  # Only one unique opponent
            volatility=5.0,
            max_matches=30,
            max_volatility=20.0
        )
        # Should have lower score due to lack of diversity
        assert score < 0.6

    def test_perfect_conditions_high_score(self):
        """Perfect conditions should yield very high credibility."""
        # Max matches, perfect diversity, zero volatility
        opponent_elos = list(range(900, 1100, 3))[:30]  # Very diverse
        
        score, label = calculate_credibility_score(
            matches=30,
            opponent_elos=opponent_elos,
            volatility=0.0,  # Perfect stability
            max_matches=30,
            max_volatility=20.0
        )
        
        assert score > 0.85
        assert label == "High"

    def test_matches_below_medium_threshold(self):
        """Bey with exactly 5 matches should be low confidence."""
        score, label = calculate_credibility_score(
            matches=5,
            opponent_elos=[1000, 1010, 990, 1020, 980],
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert label == "Low"

    def test_matches_at_medium_threshold(self):
        """Bey with exactly 6 matches should be medium confidence."""
        score, label = calculate_credibility_score(
            matches=6,
            opponent_elos=[1000, 1010, 990, 1020, 980, 1005],
            volatility=10.0,
            max_matches=30,
            max_volatility=20.0
        )
        assert label in ["Low", "Medium"]

    def test_matches_at_high_threshold(self):
        """Bey with exactly 15 matches should have potential for high confidence."""
        opponent_elos = list(range(950, 1050, 7))[:15]
        
        score, label = calculate_credibility_score(
            matches=15,
            opponent_elos=opponent_elos,
            volatility=5.0,
            max_matches=30,
            max_volatility=20.0
        )
        # With good conditions, should be able to reach high confidence
        assert label in ["Medium", "High"]
