"""Unit tests for src.analytics.xp_system."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analytics.xp_system import (
    BASE_XP,
    LEVEL_XP_BASE,
    LEVEL_XP_EXPONENT,
    LEVEL_XP_MULTIPLIER,
    LOSS_BONUS,
    PERF_LOSS_SOFT_CAP_SCALE,
    PERF_LOSS_SOFT_CAP_THRESHOLD,
    PERF_WIN_SOFT_CAP_SCALE,
    PERF_WIN_SOFT_CAP_THRESHOLD,
    PRESTIGE_LEVEL,
    PRESTIGE_XP_BONUS_CAP,
    PRESTIGE_XP_BONUS_PER_LEVEL,
    QUALIFICATION_XP,
    SEASON_CUP_XP,
    SOFT_CAP_SCALE,
    SOFT_CAP_THRESHOLD,
    TOURNAMENT_MATCH_XP,
    WIN_BONUS,
    _apply_xp,
    _default_bey_state,
    _iter_tier_placements,
    compute_level_and_xp,
    compute_match_xp,
    compute_tournament_xp,
    load_tournament_placements,
    normalize_bey_key,
    performance_bonus_loss,
    performance_bonus_win,
    placement_multiplier,
    prestige_multiplier,
    qualification_match_xp,
    season_cup_match_xp,
    season_end_xp,
    season_matchday_xp,
    streak_bonus,
    tournament_match_xp,
    xp_needed_for_level,
)


class TestXpNeededForLevel:
    def test_level_formula(self):
        expected = LEVEL_XP_BASE + (2 ** LEVEL_XP_EXPONENT) * LEVEL_XP_MULTIPLIER
        assert abs(xp_needed_for_level(2) - expected) < 1e-9

    def test_level_0_or_lower(self):
        assert xp_needed_for_level(0) == 0.0
        assert xp_needed_for_level(-1) == 0.0

    def test_increasing_curve(self):
        for level in range(1, 20):
            assert xp_needed_for_level(level + 1) > xp_needed_for_level(level)


class TestComputeLevelAndXp:
    def test_zero_xp(self):
        level, xp_in_level = compute_level_and_xp(0)
        assert level == 1
        assert xp_in_level == 0

    def test_exact_level_up(self):
        needed = xp_needed_for_level(1)
        level, xp_in_level = compute_level_and_xp(needed)
        assert level == 2
        assert abs(xp_in_level) < 1e-9


class TestPrestigeMultiplier:
    def test_base_multiplier(self):
        assert prestige_multiplier(0) == 1.0

    def test_linear_until_cap(self):
        expected = 1.0 + (2 * PRESTIGE_XP_BONUS_PER_LEVEL)
        assert abs(prestige_multiplier(2) - expected) < 1e-9

    def test_cap(self):
        assert abs(prestige_multiplier(99) - (1.0 + PRESTIGE_XP_BONUS_CAP)) < 1e-9


class TestStreakBonus:
    def test_no_bonus_below_2(self):
        assert streak_bonus(0) == 0.0
        assert streak_bonus(1) == 0.0

    def test_known_steps(self):
        # streak=2/3/4/5 map to +8%/+16%/+25%/+34% before soft-cap compression
        assert abs(streak_bonus(2) - 0.08) < 1e-9
        assert abs(streak_bonus(3) - 0.16) < 1e-9
        assert abs(streak_bonus(4) - 0.25) < 1e-9
        assert abs(streak_bonus(5) - 0.34) < 1e-9

    def test_soft_cap_applies_after_threshold(self):
        assert abs(streak_bonus(6) - 0.40) < 1e-9
        assert streak_bonus(12) > streak_bonus(6)
        # Soft-cap asymptote for streak bonus is ~0.60 (threshold 0.40 + scale 0.20).
        assert streak_bonus(50) < 0.61


class TestPerformanceBonusWin:
    def test_zero_gain(self):
        assert performance_bonus_win(0, 4, 2) > 0.0

    def test_higher_gain_gives_more_bonus(self):
        small = performance_bonus_win(5, 4, 2)
        large = performance_bonus_win(30, 4, 2)
        assert large > small

    def test_soft_cap_bound(self):
        result = performance_bonus_win(10_000, 10, 0)
        max_soft = PERF_WIN_SOFT_CAP_THRESHOLD + PERF_WIN_SOFT_CAP_SCALE
        assert result <= max_soft + 1e-6


class TestPerformanceBonusLoss:
    def test_not_underdog_still_can_get_closeness(self):
        result = performance_bonus_loss(1200, 1000, 3, 4)
        assert result > 0.0

    def test_underdog_gets_more(self):
        neutral = performance_bonus_loss(1000, 1000, 3, 4)
        underdog = performance_bonus_loss(900, 1100, 3, 4)
        assert underdog > neutral

    def test_zero_score_returns_zero(self):
        assert performance_bonus_loss(1000, 1200, 0, 0) == 0.0

    def test_soft_cap_bound(self):
        result = performance_bonus_loss(500, 20_000, 9, 10)
        max_soft = PERF_LOSS_SOFT_CAP_THRESHOLD + PERF_LOSS_SOFT_CAP_SCALE
        assert result <= max_soft + 1e-6


class TestComputeMatchXp:
    def _win_xp(self, **kwargs):
        defaults = {
            "won": True,
            "elo_gain": 10.0,
            "own_pre_elo": 1000,
            "opp_pre_elo": 1000,
            "own_score": 4,
            "opp_score": 2,
            "win_streak": 1,
            "prestige": 0,
        }
        defaults.update(kwargs)
        return compute_match_xp(**defaults)

    def _loss_xp(self, **kwargs):
        defaults = {
            "won": False,
            "elo_gain": -10.0,
            "own_pre_elo": 1000,
            "opp_pre_elo": 1000,
            "own_score": 2,
            "opp_score": 4,
            "win_streak": 0,
            "prestige": 0,
        }
        defaults.update(kwargs)
        return compute_match_xp(**defaults)

    def test_base_fields(self):
        result = self._win_xp()
        assert result["base_xp"] == BASE_XP
        assert result["result_bonus"] == WIN_BONUS
        assert result["won"] is True

    def test_loss_fields(self):
        result = self._loss_xp()
        assert result["result_bonus"] == LOSS_BONUS
        assert result["won"] is False

    def test_streak_increases_win_xp(self):
        a = self._win_xp(win_streak=1)
        b = self._win_xp(win_streak=6)
        assert b["total_xp"] > a["total_xp"]

    def test_prestige_increases_xp(self):
        normal = self._win_xp(prestige=0)
        boosted = self._win_xp(prestige=1)
        assert boosted["total_xp"] > normal["total_xp"]

    def test_global_soft_cap_bound(self):
        result = self._win_xp(
            elo_gain=10000,
            own_pre_elo=20000,
            opp_pre_elo=1000,
            own_score=30,
            opp_score=0,
            win_streak=200,
            prestige=50,
        )
        max_soft = SOFT_CAP_THRESHOLD + SOFT_CAP_SCALE
        assert result["total_xp"] <= max_soft + 1e-6


class TestTournamentXp:
    def test_multiplier_table(self):
        assert placement_multiplier(1, 32) == 2.2
        assert placement_multiplier(2, 32) == 1.8
        assert placement_multiplier(3, 32) == 1.5
        assert placement_multiplier(8, 32) == 1.25
        assert placement_multiplier(16, 32) == 1.15
        assert placement_multiplier(32, 32) == 1.0

    def test_invalid_rank_or_total(self):
        assert placement_multiplier(0, 32) == 1.0
        assert placement_multiplier(1, 0) == 1.0

    def test_winner_gets_most_xp(self):
        winner = compute_tournament_xp(1, 16)
        second = compute_tournament_xp(2, 16)
        last = compute_tournament_xp(16, 16)
        assert winner > second > last


class TestSeasonXp:
    def test_matchday_table(self):
        assert season_matchday_xp(1) == 100
        assert season_matchday_xp(2) == 80
        assert season_matchday_xp(3) == 60
        assert season_matchday_xp(4) == 40
        assert season_matchday_xp(99) == 0

    def test_season_end_bonus(self):
        # placement 1st (2.5x) and tier 1 multiplier (1.5x):
        # bonus = (2.5 * 1.5 - 1) * 1000 = 2750
        assert season_end_xp(1000.0, 1, 1) == 2750.0

    def test_season_end_no_bonus_outside_top4(self):
        assert season_end_xp(1000.0, 5, 4) == 0.0


class TestQualificationXp:
    def test_returns_qualification_xp_constant(self):
        assert qualification_match_xp() == QUALIFICATION_XP

    def test_value_is_positive(self):
        assert QUALIFICATION_XP > 0


class TestSeasonCupMatchXp:
    def test_known_rounds(self):
        assert season_cup_match_xp("season_cup") == SEASON_CUP_XP["season_cup"]
        assert season_cup_match_xp("season_cup_quarter") == SEASON_CUP_XP["season_cup_quarter"]
        assert season_cup_match_xp("season_cup_semi") == SEASON_CUP_XP["season_cup_semi"]
        assert season_cup_match_xp("season_cup_final") == SEASON_CUP_XP["season_cup_final"]

    def test_unknown_returns_zero(self):
        assert season_cup_match_xp("unknown_type") == 0

    def test_later_rounds_award_more_xp(self):
        assert SEASON_CUP_XP["season_cup_final"] > SEASON_CUP_XP["season_cup_semi"]
        assert SEASON_CUP_XP["season_cup_semi"] > SEASON_CUP_XP["season_cup_quarter"]
        assert SEASON_CUP_XP["season_cup_quarter"] > SEASON_CUP_XP["season_cup"]


class TestTournamentMatchXp:
    def test_known_rounds(self):
        assert tournament_match_xp("tournament") == TOURNAMENT_MATCH_XP["tournament"]
        assert tournament_match_xp("tournament_ro16") == TOURNAMENT_MATCH_XP["tournament_ro16"]
        assert tournament_match_xp("tournament_quarter") == TOURNAMENT_MATCH_XP["tournament_quarter"]
        assert tournament_match_xp("tournament_semi") == TOURNAMENT_MATCH_XP["tournament_semi"]
        assert tournament_match_xp("tournament_final") == TOURNAMENT_MATCH_XP["tournament_final"]

    def test_unknown_returns_zero(self):
        assert tournament_match_xp("exhibition") == 0
        assert tournament_match_xp("unknown_type") == 0

    def test_later_rounds_award_more_xp(self):
        assert TOURNAMENT_MATCH_XP["tournament_final"] > TOURNAMENT_MATCH_XP["tournament_semi"]
        assert TOURNAMENT_MATCH_XP["tournament_semi"] > TOURNAMENT_MATCH_XP["tournament_quarter"]
        assert TOURNAMENT_MATCH_XP["tournament_quarter"] > TOURNAMENT_MATCH_XP["tournament_ro16"]
        assert TOURNAMENT_MATCH_XP["tournament_ro16"] > TOURNAMENT_MATCH_XP["tournament"]


class TestApplyXp:
    def test_simple_xp_gain(self):
        state = _default_bey_state()
        _apply_xp(state, 25.0)
        assert abs(state["xp"] - 25.0) < 1e-9
        assert state["level"] == 1

    def test_level_up(self):
        state = _default_bey_state()
        _apply_xp(state, xp_needed_for_level(1))
        assert state["level"] == 2

    def test_prestige_resets_progress(self):
        state = _default_bey_state()
        # Add +1 to move past the level-49→50 threshold and trigger prestige reset.
        total_needed = sum(xp_needed_for_level(i) for i in range(1, PRESTIGE_LEVEL)) + 1.0
        _apply_xp(state, total_needed)
        assert state["prestige"] == 1
        assert state["level"] == 1
        assert state["xp"] == 0.0
        assert state["xp_in_level"] == 0.0


class TestLoadTournamentPlacements:
    def _write_json(self, tmp_path, data):
        import json
        from pathlib import Path

        path = Path(tmp_path) / "placements.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_missing_file(self, tmp_path):
        tournaments, season_end = load_tournament_placements(
            str(tmp_path / "missing.json")
        )
        assert tournaments == {}
        assert season_end == {}

    def test_flat_legacy(self, tmp_path):
        data = {
            "_comment": "ignored",
            "T1": {"participants": 8, "placements": ["BeyA", "BeyB"]},
        }
        path = self._write_json(tmp_path, data)
        tournaments, season_end = load_tournament_placements(path)
        assert "T1" in tournaments
        assert season_end == {}

    def test_nested_format(self, tmp_path):
        data = {
            "tournaments": {"T1": {"participants": 8, "placements": ["BeyA"]}},
            "season_end_placements": {
                "S1": {"date": "2025-12-31", "placements": ["BeyA"]}
            },
        }
        path = self._write_json(tmp_path, data)
        tournaments, season_end = load_tournament_placements(path)
        assert "T1" in tournaments
        assert "S1" in season_end


class TestSeasonEndTierParsing:
    def test_iter_legacy(self):
        entry = {"placements": ["A", "B"]}
        assert list(_iter_tier_placements(entry)) == [("all", ["A", "B"])]

    def test_iter_tiered(self):
        entry = {
            "tiers": {"1": {"placements": ["A"]}, "2": ["B"]}
        }
        got = dict(_iter_tier_placements(entry))
        assert got["1"] == ["A"]
        assert got["2"] == ["B"]

    def test_normalize_bey_key(self):
        assert normalize_bey_key("Dran Sword") == "dransword"
        assert normalize_bey_key("dran-sword") == "dransword"
