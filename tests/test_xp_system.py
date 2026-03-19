"""
Unit tests for xp_system.py module.
Tests XP calculation, level curve, prestige, tournament XP, and season XP.
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analytics.xp_system import (
    xp_needed_for_level,
    compute_level_and_xp,
    prestige_multiplier,
    streak_bonus,
    performance_bonus_win,
    performance_bonus_loss,
    compute_match_xp,
    compute_tournament_xp,
    placement_multiplier,
    season_matchday_xp,
    season_end_xp,
    load_tournament_placements,
    _apply_xp,
    _default_bey_state,
    BASE_XP,
    WIN_BONUS,
    LOSS_BONUS,
    PERFORMANCE_WIN_CAP,
    PERFORMANCE_LOSS_CAP,
    MAX_XP_PER_MATCH,
    PRESTIGE_LEVEL,
    LEVEL_XP_BASE,
    LEVEL_XP_EXPONENT,
)


class TestXpNeededForLevel:
    """Tests for the level XP curve."""

    def test_level_1_formula(self):
        """Level 1 XP should be 50 * 1^1.3 = 50."""
        assert abs(xp_needed_for_level(1) - 50.0) < 1e-9

    def test_level_2_formula(self):
        """Level 2 XP should follow 50 * 2^1.3."""
        expected = LEVEL_XP_BASE * (2 ** LEVEL_XP_EXPONENT)
        assert abs(xp_needed_for_level(2) - expected) < 1e-9

    def test_level_increases_with_level(self):
        """Higher levels require more XP than lower levels."""
        for lvl in range(1, 10):
            assert xp_needed_for_level(lvl) < xp_needed_for_level(lvl + 1)

    def test_level_0_returns_0(self):
        """Level 0 or below should return 0."""
        assert xp_needed_for_level(0) == 0.0
        assert xp_needed_for_level(-1) == 0.0


class TestComputeLevelAndXp:
    """Tests for XP-to-level conversion."""

    def test_zero_xp_is_level_1(self):
        level, xp_in = compute_level_and_xp(0)
        assert level == 1
        assert xp_in == 0

    def test_exactly_enough_xp_for_level_1(self):
        """Exactly enough XP to reach level 2 (i.e., completed level 1)."""
        needed = xp_needed_for_level(1)
        level, xp_in = compute_level_and_xp(needed)
        assert level == 2
        assert abs(xp_in) < 1e-9

    def test_halfway_through_level_1(self):
        half = xp_needed_for_level(1) / 2
        level, xp_in = compute_level_and_xp(half)
        assert level == 1
        assert abs(xp_in - half) < 1e-9

    def test_multi_level_advancement(self):
        """Accumulate enough XP for several levels."""
        total = sum(xp_needed_for_level(i) for i in range(1, 6))
        level, xp_in = compute_level_and_xp(total)
        assert level == 6
        assert abs(xp_in) < 1e-9


class TestPrestigeMultiplier:
    """Tests for prestige XP multiplier."""

    def test_prestige_0_gives_1x(self):
        assert prestige_multiplier(0) == 1.0

    def test_prestige_1_gives_1_05x(self):
        assert abs(prestige_multiplier(1) - 1.05) < 1e-9

    def test_prestige_5_gives_1_25x(self):
        assert abs(prestige_multiplier(5) - 1.25) < 1e-9

    def test_prestige_capped_at_1_25x(self):
        """Prestige beyond 5 should still give only 1.25× bonus."""
        assert abs(prestige_multiplier(10) - 1.25) < 1e-9
        assert abs(prestige_multiplier(100) - 1.25) < 1e-9


class TestStreakBonus:
    """Tests for win streak XP bonus."""

    def test_no_streak(self):
        assert streak_bonus(0) == 0
        assert streak_bonus(1) == 0

    def test_streak_2(self):
        assert streak_bonus(2) == 10

    def test_streak_3(self):
        assert streak_bonus(3) == 20

    def test_streak_4(self):
        assert streak_bonus(4) == 30

    def test_streak_5_and_above(self):
        assert streak_bonus(5) == 40
        assert streak_bonus(10) == 40


class TestPerformanceBonusWin:
    """Tests for win performance bonus."""

    def test_zero_elo_gain(self):
        assert performance_bonus_win(0) == 0.0

    def test_small_elo_gain(self):
        result = performance_bonus_win(10)
        assert abs(result - 15.0) < 1e-9

    def test_capped_at_50(self):
        assert performance_bonus_win(40) == PERFORMANCE_WIN_CAP  # 1.5*40=60 > 50

    def test_negative_elo_gain_gives_zero(self):
        """Negative ELO gain (bad win?) should give 0 bonus."""
        assert performance_bonus_win(-5) == 0.0


class TestPerformanceBonusLoss:
    """Tests for underdog loss performance bonus."""

    def test_no_bonus_when_own_elo_higher(self):
        """No bonus when own ELO ≥ opponent ELO."""
        result = performance_bonus_loss(1200, 1000, 2, 4)
        assert result == 0.0

    def test_bonus_when_underdog(self):
        """Underdog should receive a positive bonus."""
        result = performance_bonus_loss(1000, 1200, 2, 4)
        assert result > 0.0

    def test_close_loss_gives_more_bonus(self):
        """A closer loss should give more bonus than a blowout."""
        close = performance_bonus_loss(1000, 1200, 3, 4)
        blowout = performance_bonus_loss(1000, 1200, 0, 4)
        assert close > blowout

    def test_capped_at_40(self):
        """Bonus should be capped at PERFORMANCE_LOSS_CAP."""
        # Very large ELO diff, close score
        result = performance_bonus_loss(1000, 5000, 3, 4)
        assert result == PERFORMANCE_LOSS_CAP

    def test_zero_scores(self):
        result = performance_bonus_loss(1000, 1200, 0, 0)
        assert result == 0.0


class TestComputeMatchXp:
    """Tests for complete match XP breakdown."""

    def _win_xp(self, **kwargs):
        defaults = dict(
            won=True, elo_gain=10.0,
            own_pre_elo=1000, opp_pre_elo=1000,
            own_score=4, opp_score=2,
            win_streak=1, prestige=0,
        )
        defaults.update(kwargs)
        return compute_match_xp(**defaults)

    def _loss_xp(self, **kwargs):
        defaults = dict(
            won=False, elo_gain=-10.0,
            own_pre_elo=1000, opp_pre_elo=1000,
            own_score=2, opp_score=4,
            win_streak=0, prestige=0,
        )
        defaults.update(kwargs)
        return compute_match_xp(**defaults)

    def test_win_base(self):
        result = self._win_xp(elo_gain=0, win_streak=0)
        assert result["base_xp"] == BASE_XP
        assert result["result_bonus"] == WIN_BONUS
        assert result["won"] is True

    def test_loss_base(self):
        result = self._loss_xp(opp_pre_elo=1000)
        assert result["result_bonus"] == LOSS_BONUS
        assert result["won"] is False

    def test_max_xp_capped(self):
        """Even with best bonuses, XP should be capped at MAX_XP_PER_MATCH."""
        result = self._win_xp(
            elo_gain=50, win_streak=10, prestige=10
        )
        assert result["total_xp"] <= MAX_XP_PER_MATCH

    def test_prestige_bonus_applied(self):
        """Prestige 1 should give 5% more XP."""
        base_result = self._win_xp(elo_gain=0, win_streak=0, prestige=0)
        prestige_result = self._win_xp(elo_gain=0, win_streak=0, prestige=1)
        expected = min(base_result["total_xp"] * 1.05, MAX_XP_PER_MATCH)
        assert abs(prestige_result["total_xp"] - expected) < 0.01

    def test_streak_bonus_included_in_win(self):
        no_streak = self._win_xp(win_streak=1)
        with_streak = self._win_xp(win_streak=2)
        assert with_streak["total_xp"] > no_streak["total_xp"]

    def test_win_xp_greater_than_loss_xp(self):
        win = self._win_xp()
        loss = self._loss_xp()
        assert win["total_xp"] > loss["total_xp"]


class TestTournamentXp:
    """Tests for tournament XP calculation."""

    def test_winner_gets_highest_xp(self):
        winner = compute_tournament_xp(1, 32)
        second = compute_tournament_xp(2, 32)
        last = compute_tournament_xp(32, 32)
        assert winner > second > last

    def test_placement_multiplier_winner(self):
        assert placement_multiplier(1, 32) == 3.0

    def test_placement_multiplier_second(self):
        assert placement_multiplier(2, 32) == 2.5

    def test_placement_multiplier_top10pct(self):
        # 3/32 ≈ 9.4% → top 10%
        assert placement_multiplier(3, 32) == 2.0

    def test_placement_multiplier_top25pct(self):
        # 7/32 ≈ 21.9% → top 25%
        assert placement_multiplier(7, 32) == 1.5

    def test_placement_multiplier_top50pct(self):
        # 13/32 ≈ 40.6% → top 50%
        assert placement_multiplier(13, 32) == 1.15

    def test_placement_multiplier_participation(self):
        # 25/32 ≈ 78% → participation
        assert placement_multiplier(25, 32) == 1.0

    def test_placement_multiplier_zero_total_returns_participation(self):
        # Zero or negative total should not raise ZeroDivisionError
        assert placement_multiplier(1, 0) == 1.0
        assert placement_multiplier(1, -1) == 1.0

    def test_placement_multiplier_invalid_rank_returns_participation(self):
        assert placement_multiplier(0, 32) == 1.0
        assert placement_multiplier(-5, 32) == 1.0

    def test_tournament_xp_formula(self):
        participants = 32
        base = 150 + 25 * participants
        result = compute_tournament_xp(1, participants)
        assert abs(result - base * 3.0) < 1e-9


class TestSeasonXp:
    """Tests for season XP helpers."""

    def test_tier1_xp(self):
        assert season_matchday_xp(1) == 150

    def test_tier2_xp(self):
        assert season_matchday_xp(2) == 120

    def test_tier3_xp(self):
        assert season_matchday_xp(3) == 100

    def test_tier4_xp(self):
        assert season_matchday_xp(4) == 80

    def test_unknown_tier_gives_0(self):
        assert season_matchday_xp(99) == 0

    def test_season_end_first_place(self):
        """First place should triple the season XP (bonus = 2.0 * total)."""
        result = season_end_xp(1000.0, 1)
        assert abs(result - 2000.0) < 1e-9

    def test_season_end_no_bonus_for_others(self):
        """Placement outside top 4 should give zero bonus."""
        result = season_end_xp(1000.0, 5)
        assert result == 0.0


class TestApplyXp:
    """Tests for _apply_xp state mutation and prestige."""

    def test_simple_xp_gain(self):
        state = _default_bey_state()
        _apply_xp(state, 25.0)  # Less than xp_needed_for_level(1)=50, so no level-up
        assert abs(state["xp"] - 25.0) < 1e-9
        assert state["level"] == 1

    def test_level_up(self):
        state = _default_bey_state()
        needed = xp_needed_for_level(1)
        _apply_xp(state, needed)
        assert state["level"] == 2

    def test_prestige_trigger(self):
        """Levelling to PRESTIGE_LEVEL should trigger a prestige reset."""
        state = _default_bey_state()
        # Accumulate enough XP to reach prestige level
        total_needed = sum(xp_needed_for_level(i) for i in range(1, PRESTIGE_LEVEL))
        _apply_xp(state, total_needed)
        assert state["prestige"] == 1
        assert state["level"] == 1
        assert state["xp"] == 0.0

    def test_prestige_xp_resets_to_zero(self):
        """After prestige, accumulated XP resets."""
        state = _default_bey_state()
        total_needed = sum(xp_needed_for_level(i) for i in range(1, PRESTIGE_LEVEL))
        _apply_xp(state, total_needed)
        assert state["xp"] == 0.0
        assert state["xp_in_level"] == 0.0


class TestLoadTournamentPlacements:
    """Tests for load_tournament_placements supporting both file formats."""

    def _write_json(self, tmp_path, data):
        import json, tempfile, pathlib
        p = pathlib.Path(tmp_path) / "placements.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_missing_file_returns_empty_dicts(self, tmp_path):
        t, s = load_tournament_placements(str(tmp_path / "nonexistent.json"))
        assert t == {}
        assert s == {}

    def test_flat_legacy_format(self, tmp_path):
        data = {
            "_comment": "ignored",
            "T1": {"participants": 8, "placements": ["BeyA", "BeyB"]},
        }
        path = self._write_json(tmp_path, data)
        t, s = load_tournament_placements(path)
        assert "T1" in t
        assert s == {}

    def test_nested_format_with_season_end(self, tmp_path):
        data = {
            "tournaments": {"T1": {"participants": 8, "placements": ["BeyA"]}},
            "season_end_placements": {"S1": {"date": "2025-12-31", "placements": ["BeyA"]}},
        }
        path = self._write_json(tmp_path, data)
        t, s = load_tournament_placements(path)
        assert "T1" in t
        assert "S1" in s

    def test_flat_format_skips_comment_keys(self, tmp_path):
        data = {
            "_comment": "metadata",
            "T1": {"participants": 4, "placements": []},
        }
        path = self._write_json(tmp_path, data)
        t, _ = load_tournament_placements(path)
        assert "_comment" not in t
        assert "T1" in t
