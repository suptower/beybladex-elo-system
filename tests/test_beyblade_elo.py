"""
Unit tests for beyblade_elo.py module.
Tests the ELO calculation functions including K-factor, expected scores,
ELO updates, and winrate calculations, plus arena-specific ELO tracking.
"""
import sys
import os
import math

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from collections import defaultdict
from beyblade_elo import (
    dynamic_k,
    k_effective,
    expected,
    calculate_score_with_margin,
    calculate_score_with_dominance,
    update_elo,
    calculate_winrates,
    normalize_arena_name,
    K_MIN,
    K_MAX,
    K_TAU,
    FORM_EMA_ALPHA,
    FORM_ALPHA,
    MARGIN_A,
    MARGIN_B,
    START_ELO,
    ARENA_XTREME,
    ARENA_DROP_ATTACK
)


class TestDynamicK:
    """Tests for the dynamic_k function (smooth exponential decay, Version 3)."""

    def test_k_at_zero_matches_equals_k_max(self):
        """K-factor at 0 matches should equal K_MAX (maximum volatility)."""
        assert abs(dynamic_k(0) - K_MAX) < 1e-9

    def test_k_decreases_with_more_matches(self):
        """K-factor should decrease as match count increases."""
        assert dynamic_k(0) > dynamic_k(10)
        assert dynamic_k(10) > dynamic_k(50)
        assert dynamic_k(50) > dynamic_k(200)

    def test_k_approaches_k_min_for_many_matches(self):
        """K-factor should approach K_MIN for very large match counts."""
        k_large = dynamic_k(1000)
        assert abs(k_large - K_MIN) < 0.01

    def test_k_bounded_between_k_min_and_k_max(self):
        """K-factor should always be between K_MIN and K_MAX."""
        for n in [0, 1, 5, 10, 20, 50, 100, 500]:
            k = dynamic_k(n)
            assert K_MIN <= k <= K_MAX, f"K out of bounds for {n} matches: {k}"

    def test_k_exponential_formula(self):
        """K-factor should follow K_MIN + (K_MAX - K_MIN) * exp(-N / K_TAU)."""
        for n in [0, 5, 10, 20, 50]:
            expected_k = K_MIN + (K_MAX - K_MIN) * math.exp(-n / K_TAU)
            assert abs(dynamic_k(n) - expected_k) < 1e-9


class TestExpected:
    """Tests for the expected function that calculates expected score."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        assert expected(1000, 1000) == 0.5
        assert expected(1500, 1500) == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        result = expected(1200, 1000)
        assert result > 0.5
        assert result < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        result = expected(1000, 1200)
        assert result < 0.5
        assert result > 0.0

    def test_400_point_difference(self):
        """400 point difference should give approximately 10:1 odds."""
        result = expected(1400, 1000)
        # 1 / (1 + 10^1) ≈ 0.909
        assert abs(result - 0.909) < 0.01

    def test_symmetry(self):
        """Expected scores of opponents should sum to 1."""
        e_a = expected(1200, 1000)
        e_b = expected(1000, 1200)
        assert abs(e_a + e_b - 1.0) < 0.0001


class TestKEffective:
    """Tests for the k_effective function (EMA-based K adjustment)."""

    def test_no_form_ema_returns_base_k(self):
        """None form_ema (no history) should return the base K unchanged."""
        k_base = dynamic_k(10)
        assert k_effective(k_base, None) == k_base

    def test_positive_form_increases_k(self):
        """Positive form EMA (wins above expectation) should increase K."""
        k_base = dynamic_k(10)
        assert k_effective(k_base, 0.4) > k_base

    def test_negative_form_increases_k(self):
        """Negative form EMA (losses below expectation) should also increase K."""
        k_base = dynamic_k(10)
        assert k_effective(k_base, -0.4) > k_base

    def test_neutral_form_keeps_base_k(self):
        """Zero form EMA should return base K unchanged."""
        k_base = dynamic_k(10)
        assert k_effective(k_base, 0.0) == k_base

    def test_ema_converges_smoothly(self):
        """EMA should converge: sustained positive deltas eventually dominate zero history."""
        form_ema = 0.0
        for _ in range(50):
            form_ema = FORM_EMA_ALPHA * 0.5 + (1 - FORM_EMA_ALPHA) * form_ema
        # After many sustained +0.5 deltas, EMA should be close to 0.5
        assert abs(form_ema - 0.5) < 0.01

    def test_k_eff_formula(self):
        """K_eff = K_base * (1 + FORM_ALPHA * |form_ema|)."""
        k_base = dynamic_k(10)
        form_ema = 0.3
        expected_k = k_base * (1 + FORM_ALPHA * abs(form_ema))
        assert abs(k_effective(k_base, form_ema) - expected_k) < 1e-9


class TestScoreWithMargin:
    """Tests for the calculate_score_with_margin function (tanh model, Version 3)."""

    def test_reference_win_4_0_gives_score_one(self):
        """4-0 is the reference win: S_winner=1.0, S_loser=1-1.0=0.0."""
        s_a, s_b = calculate_score_with_margin(4, 0, target=4)
        assert abs(s_a - 1.0) < 1e-9
        assert abs(s_b - 0.0) < 1e-9

    def test_close_win_4_3_gives_less_than_one(self):
        """4-3 win: m=1 < T=4, so S_winner < 1.0 and S_loser = 1 - S_winner > 0."""
        s_a, s_b = calculate_score_with_margin(4, 3, target=4)
        assert s_a < 1.0
        assert abs(s_a - 0.833) < 0.01
        assert abs(s_b - (1.0 - s_a)) < 1e-9
        assert s_b > 0.0  # loser is NOT as harshly penalised as for a 4-0 loss

    def test_dominant_win_6_0_gives_more_than_one(self):
        """6-0 win: m=6 > T=4, so S_winner > 1.0 and S_loser = 1 - S_winner < 0."""
        s_a, s_b = calculate_score_with_margin(6, 0, target=4)
        assert s_a > 1.0
        assert abs(s_b - (1.0 - s_a)) < 1e-9
        assert s_b < 0.0  # dominant loss is penalised more than a reference 4-0 loss

    def test_loser_gets_complement_of_winner(self):
        """Loser's score is always 1 - winner's score."""
        for sa, sb in [(4, 0), (4, 1), (4, 2), (4, 3), (5, 0), (7, 4)]:
            s_a, s_b = calculate_score_with_margin(sa, sb, target=4)
            assert abs(s_b - (1.0 - s_a)) < 1e-9

    def test_winner_identified_correctly(self):
        """When B wins, B gets the margin score and A gets 1 - S_winner."""
        s_a, s_b = calculate_score_with_margin(2, 4, target=4)
        assert abs(s_b - 0.856) < 0.01  # m=2, T=4: 1 + 0.18*tanh(2.2*(2-4)/4) ≈ 0.856
        assert abs(s_a - (1.0 - s_b)) < 1e-9

    def test_draw_gives_equal_scores(self):
        """Equal scores should give 0.5 each."""
        s_a, s_b = calculate_score_with_margin(3, 3)
        assert s_a == 0.5
        assert s_b == 0.5

    def test_zero_zero_draw(self):
        """0-0 should give equal scores."""
        s_a, s_b = calculate_score_with_margin(0, 0)
        assert s_a == 0.5
        assert s_b == 0.5

    def test_larger_margin_gives_higher_score(self):
        """Larger point differential should give higher score to winner."""
        s_4_3, _ = calculate_score_with_margin(4, 3)
        s_4_2, _ = calculate_score_with_margin(4, 2)
        s_4_0, _ = calculate_score_with_margin(4, 0)
        s_5_0, _ = calculate_score_with_margin(5, 0)
        assert s_4_3 < s_4_2 < s_4_0 < s_5_0

    def test_finals_target_7(self):
        """Race-to-7 finals: 7-0 should be reference (S_winner=1.0, S_loser=0.0)."""
        s_a, s_b = calculate_score_with_margin(7, 0, target=7)
        assert abs(s_a - 1.0) < 1e-9
        assert abs(s_b - 0.0) < 1e-9

    def test_finals_close_win(self):
        """Race-to-7 finals: 7-6 should give S_winner < 1.0, S_loser = 1 - S_winner."""
        s_a, s_b = calculate_score_with_margin(7, 6, target=7)
        assert s_a < 1.0
        assert abs(s_b - (1.0 - s_a)) < 1e-9

    def test_score_uses_margin_formula(self):
        """Winner score follows S = 1 + MARGIN_A * tanh(MARGIN_B * (m - T) / T)."""
        sa, sb = 4, 1
        s_a, _ = calculate_score_with_margin(sa, sb, target=4)
        m = sa - sb
        expected_s = 1 + MARGIN_A * math.tanh(MARGIN_B * (m - 4) / 4)
        assert abs(s_a - expected_s) < 1e-9

    def test_backward_compat_alias(self):
        """calculate_score_with_dominance should delegate to calculate_score_with_margin."""
        s_a1, s_b1 = calculate_score_with_margin(4, 2)
        s_a2, s_b2 = calculate_score_with_dominance(4, 2)
        assert abs(s_a1 - s_a2) < 1e-9
        assert abs(s_b1 - s_b2) < 1e-9


class TestUpdateElo:
    """Tests for the update_elo function that updates ratings after a match."""

    def _create_test_data(self):
        """Helper to create test data structures."""
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {
            "wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0
        })
        return elos, stats

    def test_winner_gains_elo(self):
        """Winner should gain ELO points."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 5, 3, "2024-01-01", elos, stats)

        assert elos["BeyA"] > 1000  # Winner gained
        assert elos["BeyB"] < 1000  # Loser lost

    def test_loser_loses_elo(self):
        """Loser should lose ELO points."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 2, 5, "2024-01-01", elos, stats)

        assert elos["BeyA"] < 1000  # Loser lost
        assert elos["BeyB"] > 1000  # Winner gained

    def test_stats_updated(self):
        """Match stats should be properly updated."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 5, 3, "2024-01-01", elos, stats)

        # Check BeyA stats
        assert stats["BeyA"]["matches"] == 1
        assert stats["BeyA"]["wins"] == 1
        assert stats["BeyA"]["losses"] == 0
        assert stats["BeyA"]["for"] == 5
        assert stats["BeyA"]["against"] == 3

        # Check BeyB stats
        assert stats["BeyB"]["matches"] == 1
        assert stats["BeyB"]["wins"] == 0
        assert stats["BeyB"]["losses"] == 1
        assert stats["BeyB"]["for"] == 3
        assert stats["BeyB"]["against"] == 5

    def test_elo_conservation_for_reference_win(self):
        """4-0 (reference win) conserves total ELO exactly (S_A=1.0, S_B=0.0, sum=1.0)."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        initial_total = elos["BeyA"] + elos["BeyB"]
        update_elo("BeyA", "BeyB", 4, 0, "2024-01-01", elos, stats)
        final_total = elos["BeyA"] + elos["BeyB"]

        # 4-0: m=4=T, tanh(0)=0, S_A=1.0, S_B=0.0, S_A+S_B=1.0 → ELO conserved
        assert abs(initial_total - final_total) < 0.001

    def test_zero_total_score_no_update(self):
        """A match with 0-0 score should not update anything."""
        elos, stats = self._create_test_data()
        elos["BeyA"] = 1000
        elos["BeyB"] = 1000

        update_elo("BeyA", "BeyB", 0, 0, "2024-01-01", elos, stats)

        assert elos["BeyA"] == 1000
        assert elos["BeyB"] == 1000

    def test_upset_victory(self):
        """Lower rated player winning should gain more ELO."""
        elos1, stats1 = self._create_test_data()
        elos1["BeyA"] = 1200
        elos1["BeyB"] = 1000

        elos2, stats2 = self._create_test_data()
        elos2["BeyC"] = 1000
        elos2["BeyD"] = 1000

        # Lower rated wins
        update_elo("BeyA", "BeyB", 3, 5, "2024-01-01", elos1, stats1)
        # Equal rated match
        update_elo("BeyC", "BeyD", 3, 5, "2024-01-01", elos2, stats2)

        # BeyB (underdog) gained more than BeyD (equal match)
        gain_underdog = elos1["BeyB"] - 1000
        gain_equal = elos2["BeyD"] - 1000
        assert gain_underdog > gain_equal

    def test_margin_affects_elo_gain(self):
        """Larger winning margin should result in larger ELO gains."""
        # Test three equal-rated matches with different margin levels
        elos_close, stats_close = self._create_test_data()
        elos_close["BeyA"] = 1000
        elos_close["BeyB"] = 1000

        elos_moderate, stats_moderate = self._create_test_data()
        elos_moderate["BeyC"] = 1000
        elos_moderate["BeyD"] = 1000

        elos_dominant, stats_dominant = self._create_test_data()
        elos_dominant["BeyE"] = 1000
        elos_dominant["BeyF"] = 1000

        # Close win: 4-3 (m=1, S < 1.0)
        update_elo("BeyA", "BeyB", 4, 3, "2024-01-01", elos_close, stats_close)

        # Moderate win: 4-2 (m=2, S slightly higher)
        update_elo("BeyC", "BeyD", 4, 2, "2024-01-01", elos_moderate, stats_moderate)

        # Reference win: 4-0 (m=4=T, S=1.0)
        update_elo("BeyE", "BeyF", 4, 0, "2024-01-01", elos_dominant, stats_dominant)

        # Calculate ELO gains
        gain_close = elos_close["BeyA"] - 1000
        gain_moderate = elos_moderate["BeyC"] - 1000
        gain_dominant = elos_dominant["BeyE"] - 1000

        # More dominant wins should result in larger ELO gains
        assert gain_close < gain_moderate < gain_dominant, \
            f"Expected gains to increase with dominance: {gain_close} < {gain_moderate} < {gain_dominant}"

    def test_overshoot_gives_more_than_reference_win(self):
        """5-0 and 6-0 (overshoot) should give more ELO gain than reference 4-0."""
        elos_4_0, stats_4_0 = self._create_test_data()
        elos_4_0["BeyA"] = 1000
        elos_4_0["BeyB"] = 1000

        elos_5_0, stats_5_0 = self._create_test_data()
        elos_5_0["BeyC"] = 1000
        elos_5_0["BeyD"] = 1000

        elos_6_0, stats_6_0 = self._create_test_data()
        elos_6_0["BeyE"] = 1000
        elos_6_0["BeyF"] = 1000

        # 4-0 win: reference (S=1.0)
        update_elo("BeyA", "BeyB", 4, 0, "2024-01-01", elos_4_0, stats_4_0)
        # 5-0 win: overshoot (S > 1.0)
        update_elo("BeyC", "BeyD", 5, 0, "2024-01-01", elos_5_0, stats_5_0)
        # 6-0 win: larger overshoot (S even higher)
        update_elo("BeyE", "BeyF", 6, 0, "2024-01-01", elos_6_0, stats_6_0)

        gain_4_0 = elos_4_0["BeyA"] - 1000
        gain_5_0 = elos_5_0["BeyC"] - 1000
        gain_6_0 = elos_6_0["BeyE"] - 1000

        assert gain_4_0 < gain_5_0 < gain_6_0, \
            f"Expected 4-0 < 5-0 < 6-0 gains: {gain_4_0} < {gain_5_0} < {gain_6_0}"


class TestCalculateWinrates:
    """Tests for the calculate_winrates function."""

    def test_perfect_winrate(self):
        """Player with all wins should have winrate of 1.0."""
        stats = {
            "BeyA": {"wins": 10, "losses": 0, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 1.0

    def test_zero_winrate(self):
        """Player with all losses should have winrate of 0.0."""
        stats = {
            "BeyA": {"wins": 0, "losses": 10, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.0

    def test_fifty_percent_winrate(self):
        """Player with equal wins/losses should have winrate of 0.5."""
        stats = {
            "BeyA": {"wins": 5, "losses": 5, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.5

    def test_no_matches_winrate(self):
        """Player with no matches should have winrate of 0.0."""
        stats = {
            "BeyA": {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.0

    def test_multiple_players(self):
        """Winrate calculation should work for multiple players."""
        stats = {
            "BeyA": {"wins": 8, "losses": 2, "for": 0, "against": 0, "matches": 10, "winrate": 0.0},
            "BeyB": {"wins": 3, "losses": 7, "for": 0, "against": 0, "matches": 10, "winrate": 0.0}
        }
        calculate_winrates(stats)
        assert stats["BeyA"]["winrate"] == 0.8
        assert stats["BeyB"]["winrate"] == 0.3


class TestArenaNameNormalization:
    """Tests for arena name normalization."""

    def test_normalize_xtreme_variations(self):
        """All Xtreme variations should normalize to canonical name."""
        assert normalize_arena_name("Xtreme") == ARENA_XTREME
        assert normalize_arena_name("xtreme") == ARENA_XTREME
        assert normalize_arena_name(None) == ARENA_XTREME
        assert normalize_arena_name("") == ARENA_XTREME

    def test_normalize_drop_attack_variations(self):
        """All Drop Attack variations should normalize to canonical name."""
        assert normalize_arena_name("Drop Attack") == ARENA_DROP_ATTACK
        assert normalize_arena_name("drop attack") == ARENA_DROP_ATTACK
        assert normalize_arena_name("DropAttack") == ARENA_DROP_ATTACK
        assert normalize_arena_name("drop_attack") == ARENA_DROP_ATTACK

    def test_normalize_unknown_arena(self):
        """Unknown arenas should return as-is."""
        assert normalize_arena_name("Custom Arena") == "Custom Arena"


class TestArenaSpecificELO:
    """Tests for arena-specific ELO tracking."""

    def test_exhibition_match_updates_arena_elo(self):
        """Exhibition matches should update the arena-specific ELO."""
        # Initialize structures
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        arena_elos = {
            ARENA_XTREME: defaultdict(lambda: START_ELO),
            ARENA_DROP_ATTACK: defaultdict(lambda: START_ELO)
        }
        arena_stats = {
            ARENA_XTREME: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}),
            ARENA_DROP_ATTACK: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        }

        # Play a match in Drop Attack arena (exhibition)
        update_elo("BeyA", "BeyB", 4, 2, "2025-01-01", elos, stats,
                   writer=None, match_id="M001", arena="Drop Attack", match_type="exhibition",
                   arena_elos=arena_elos, arena_stats=arena_stats)

        # Drop Attack ELO should be updated
        assert arena_elos[ARENA_DROP_ATTACK]["BeyA"] > START_ELO
        assert arena_elos[ARENA_DROP_ATTACK]["BeyB"] < START_ELO
        assert arena_stats[ARENA_DROP_ATTACK]["BeyA"]["matches"] == 1
        assert arena_stats[ARENA_DROP_ATTACK]["BeyA"]["wins"] == 1

        # Xtreme ELO should remain at start values
        assert arena_elos[ARENA_XTREME]["BeyA"] == START_ELO
        assert arena_elos[ARENA_XTREME]["BeyB"] == START_ELO
        assert arena_stats[ARENA_XTREME]["BeyA"]["matches"] == 0

    def test_season_match_updates_xtreme_elo_only(self):
        """Season matches should always update Xtreme ELO, regardless of arena played."""
        # Initialize structures
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        arena_elos = {
            ARENA_XTREME: defaultdict(lambda: START_ELO),
            ARENA_DROP_ATTACK: defaultdict(lambda: START_ELO)
        }
        arena_stats = {
            ARENA_XTREME: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}),
            ARENA_DROP_ATTACK: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        }

        # Play a season match in Drop Attack arena (should still update Xtreme ELO)
        update_elo("BeyC", "BeyD", 4, 1, "2025-01-01", elos, stats,
                   writer=None, match_id="M002", arena="Drop Attack", match_type="season",
                   arena_elos=arena_elos, arena_stats=arena_stats)

        # Xtreme ELO should be updated (season matches always use Xtreme)
        assert arena_elos[ARENA_XTREME]["BeyC"] > START_ELO
        assert arena_elos[ARENA_XTREME]["BeyD"] < START_ELO
        assert arena_stats[ARENA_XTREME]["BeyC"]["matches"] == 1
        assert arena_stats[ARENA_XTREME]["BeyC"]["wins"] == 1

        # Drop Attack ELO should remain unchanged
        assert arena_elos[ARENA_DROP_ATTACK]["BeyC"] == START_ELO
        assert arena_elos[ARENA_DROP_ATTACK]["BeyD"] == START_ELO
        assert arena_stats[ARENA_DROP_ATTACK]["BeyC"]["matches"] == 0

    def test_multiple_arenas_independent_ratings(self):
        """Beys should have independent ELO ratings in different arenas."""
        # Initialize structures
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        arena_elos = {
            ARENA_XTREME: defaultdict(lambda: START_ELO),
            ARENA_DROP_ATTACK: defaultdict(lambda: START_ELO)
        }
        arena_stats = {
            ARENA_XTREME: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}),
            ARENA_DROP_ATTACK: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        }

        # BeyE wins in Xtreme
        update_elo("BeyE", "BeyF", 4, 1, "2025-01-01", elos, stats,
                   writer=None, match_id="M003", arena="Xtreme", match_type="exhibition",
                   arena_elos=arena_elos, arena_stats=arena_stats)

        # BeyE loses in Drop Attack
        update_elo("BeyE", "BeyF", 2, 4, "2025-01-02", elos, stats,
                   writer=None, match_id="M004", arena="Drop Attack", match_type="exhibition",
                   arena_elos=arena_elos, arena_stats=arena_stats)

        # In Xtreme: BeyE should be higher rated
        assert arena_elos[ARENA_XTREME]["BeyE"] > arena_elos[ARENA_XTREME]["BeyF"]
        assert arena_stats[ARENA_XTREME]["BeyE"]["wins"] == 1
        assert arena_stats[ARENA_XTREME]["BeyE"]["losses"] == 0

        # In Drop Attack: BeyF should be higher rated
        assert arena_elos[ARENA_DROP_ATTACK]["BeyF"] > arena_elos[ARENA_DROP_ATTACK]["BeyE"]
        assert arena_stats[ARENA_DROP_ATTACK]["BeyE"]["wins"] == 0
        assert arena_stats[ARENA_DROP_ATTACK]["BeyE"]["losses"] == 1

    def test_relegation_match_updates_xtreme_elo(self):
        """Relegation matches should update Xtreme ELO like season matches."""
        # Initialize structures
        elos = defaultdict(lambda: START_ELO)
        stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        arena_elos = {
            ARENA_XTREME: defaultdict(lambda: START_ELO),
            ARENA_DROP_ATTACK: defaultdict(lambda: START_ELO)
        }
        arena_stats = {
            ARENA_XTREME: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}),
            ARENA_DROP_ATTACK: defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})
        }

        # Relegation match
        update_elo("BeyG", "BeyH", 4, 2, "2025-01-01", elos, stats,
                   writer=None, match_id="M005", arena="Xtreme", match_type="relegation",
                   arena_elos=arena_elos, arena_stats=arena_stats)

        # Should update Xtreme ELO only
        assert arena_elos[ARENA_XTREME]["BeyG"] > START_ELO
        assert arena_stats[ARENA_XTREME]["BeyG"]["matches"] == 1
