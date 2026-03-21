#!/usr/bin/env python3
"""
XP and Level System for BeybladeX ELO System

Calculates experience points (XP) and levels for each Bey based on match
participation, ELO performance, win streaks, tournament placements and season
tier bonuses.

XP Formula (per match):
    raw_xp = (Base XP + Result Bonus + Performance Bonus + High Stakes Bonus
              + Match Length Bonus) * (1 + streak_multiplier)
    total_xp = apply_soft_cap(raw_xp * prestige_multiplier)

    Base XP:        130 (any valid match)
    Result Bonus:   +80 (win) / +20 (loss)

    Performance Bonus (Win):
        perf   = 1.5 * elo_gain
        bonus  = 60 * (1 - exp(-perf / 60)) + score_factor
        score_factor = (1 + (own_score - opp_score) / max_score) * 40
        soft cap: threshold=90, scale=25

    Performance Bonus (Loss):
        elo_diff = max(opp_elo - own_elo, 0)   (underdog component only)
        elo_bonus = 35 * (1 - exp(-0.9 * elo_diff / 35))
        closeness = 1 - (score_diff / max_score)
        bonus = elo_bonus + closeness * 40
        soft cap: threshold=30, scale=15

    High Stakes Bonus:
        raw = (own_elo + opp_elo + max(opp_elo - own_elo, 0)) / 2000 * 25
        soft cap: threshold=50, scale=20
        typical value: ~25 XP at 1000 ELO each

    Match Length Bonus:
        score_base = exp((2 * total_score - 8) / 4)
        raw = (15 * score_base - 10) * (1.1 if win else 1.0)
        soft cap: threshold=50, scale=30
        examples: 4:0 → ~5.5 XP (win), 4:3 → ~60.5 XP (win)

    Streak Multiplier (wins only):
        streak 2 → +8% | streak 3 → +16% | streak 4 → +25% | streak 5 → +34%
        streak 6 → +40% (soft cap starts here, scale=20%, safety hard cap=+120%)

    Total Soft Cap: threshold=500, scale=200 (asymptotic ~700 XP)

Level Curve:
    XP_needed(level) = 250 + level^1.65 * 4
    examples: level 1 → 254 XP | level 10 → 429 XP | level 30 → 1345 XP
    (XP to advance from level-1 → level; cumulative total determines current level)

Prestige:
    Triggered at level 50. Level resets to 1, XP to 0, prestige counter +1.
    Prestige bonus: +5% XP per prestige level, capped at +25% (prestige ≥ 5).

Tournament XP:
    base       = 180 + 32 * participants
    size_bonus = 1 + ((participants / 8)^2 / 100)
    total      = base * placement_multiplier * size_bonus

    Placement multipliers:
        1st          → 2.2x
        2nd          → 1.8x
        Top 10%      → 1.5x
        Top 25%      → 1.25x
        Top 50%      → 1.15x
        Participation → 1.0x

Season XP:
    Per matchday flat bonus by tier:
        Tier 1 → +100 / Tier 2 → +80 / Tier 3 → +60 / Tier 4 → +40

    End-of-season bonus: (placement_mult * tier_mult - 1) * season_total_xp
        Placement multipliers: 1st → 2.5x | 2nd → 2.25x | 3rd → 1.8x | 4th → 1.3x | rest → 1.0x
        Tier multipliers:      Tier 1 → 1.5x | Tier 2 → 1.3x | Tier 3 → 1.15x | Tier 4 → 1.0x

Output files:
    docs/data/analytics/xp_leaderboard.json  - Current XP / level / prestige per Bey
    docs/data/analytics/xp_history.json      - Per-match XP breakdown (keyed by MatchID)

Usage:
    python xp_system.py
"""


import csv
import json
import os
import sys
from math import exp

import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root

from src.config.paths import (  # noqa: E402
    MATCHES_CSV,
    ELO_HISTORY_CSV,
    TOURNAMENTS_JSON,
    TOURNAMENT_PLACEMENTS_JSON,
    XP_LEADERBOARD_JSON,
    XP_HISTORY_JSON,
    ANALYTICS_DIR,
)

# ---------------------------------------------------------------------------
# ANSI colours (no-op on non-tty)
# ---------------------------------------------------------------------------
if os.name == "nt":
    os.system("")

RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# ---------------------------------------------------------------------------
# XP constants
# ---------------------------------------------------------------------------
BASE_XP = 130
WIN_BONUS = 80
LOSS_BONUS = 20

SCORE_FACTOR_MULTIPLIER = 40

HIGH_STAKES_BONUS_SCALE = 25
HIGH_STAKES_ELO_REFERENCE = 2000
HIGH_STAKES_SOFT_CAP_THRESHOLD = 50
HIGH_STAKES_SOFT_CAP_SCALE = 20

MATCH_LENGTH_BONUS_SCALE = 15
MATCH_LENGTH_BONUS_OFFSET = 10
MATCH_LENGTH_SOFT_CAP_THRESHOLD = 50
MATCH_LENGTH_SOFT_CAP_SCALE = 30

PERFORMANCE_WIN_BASE = 60
PERFORMANCE_WIN_MULTIPLIER = 1.5
PERF_WIN_SOFT_CAP_THRESHOLD = 90
PERF_WIN_SOFT_CAP_SCALE = 25

PERFORMANCE_LOSS_BASE = 35
PERFORMANCE_LOSS_MULTIPLIER = 0.9
PERF_LOSS_SOFT_CAP_THRESHOLD = 30
PERF_LOSS_SOFT_CAP_SCALE = 15

# Streak bonus (proportional multiplier on raw XP)
STREAK_BONUS_START = 2          # Minimum streak length for any bonus
STREAK_BONUS_PER_WIN_EARLY = 0.08   # +8% per win for streaks 2–3
STREAK_BONUS_EARLY_CAP = 3      # Last streak length using early rate
STREAK_BONUS_MID_BASE = 0.16    # Base bonus at streak 4 (= 2 * early rate)
STREAK_BONUS_PER_WIN_MID = 0.09  # +9% per win for streaks 4–5
STREAK_BONUS_MID_CAP = 5        # Last streak length using mid rate
STREAK_BONUS_LATE_BASE = 0.35   # Base bonus at streak 6
STREAK_BONUS_PER_WIN_LATE = 0.05  # +5% per win for streaks 6+
STREAK_BONUS_MAX = 1.2          # Hard safety cap (soft cap takes effect well before this)
STREAK_SOFT_CAP_THRESHOLD = 0.40  # +40% — soft cap starts here
STREAK_SOFT_CAP_SCALE = 0.20

SOFT_CAP_THRESHOLD = 500
SOFT_CAP_SCALE = 200

# Level curve
LEVEL_XP_BASE = 250
LEVEL_XP_MULTIPLIER = 4
LEVEL_XP_EXPONENT = 1.65

# Prestige
PRESTIGE_LEVEL = 50
PRESTIGE_XP_BONUS_PER_LEVEL = 0.05  # +5 % per prestige
PRESTIGE_XP_BONUS_CAP = 0.25        # max +25 %

# Tournament XP
TOURNAMENT_BASE = 180
TOURNAMENT_PARTICIPANTS_FACTOR = 32

# Season per-matchday XP by tier (1-indexed)
SEASON_MATCHDAY_XP = {1: 100, 2: 80, 3: 60, 4: 40}

# Season end-of-season placement multipliers (1-indexed, fallback 1.0)
SEASON_PLACEMENT_MULTIPLIER = {1: 2.5, 2: 2.25, 3: 1.8, 4: 1.3}
SEASON_PLACEMENT_TIER_MULTIPLIER = {1: 1.5, 2: 1.3, 3: 1.15, 4: 1.0}


# ---------------------------------------------------------------------------
# Level helpers
# ---------------------------------------------------------------------------

def xp_needed_for_level(level: int) -> float:
    """
    Return the XP required to advance from level-1 to *level* (≥1).

    Formula: 250 + level^1.65 * 4

    Examples:
        level  1 →   254 XP
        level 10 →   429 XP
        level 20 →   811 XP
        level 30 → 1,345 XP
        level 49 → 2,710 XP
    """
    if level < 1:
        return 0.0
    return LEVEL_XP_BASE + (level ** LEVEL_XP_EXPONENT) * LEVEL_XP_MULTIPLIER


def compute_level_and_xp(total_xp: float) -> tuple:
    """
    Convert *total_xp* (accumulated since last prestige) into (level, xp_in_level).

    This helper is primarily used in tests and for reporting.  The live pipeline
    state is managed by ``_apply_xp``, which handles prestige resets inline and
    ensures ``state["level"]`` is always in the range [1, PRESTIGE_LEVEL - 1].

    Note: this function caps at PRESTIGE_LEVEL without resetting — callers that
    need prestige logic should use ``_apply_xp`` instead.

    Returns:
        level         - current level (1-based, at most PRESTIGE_LEVEL)
        xp_in_level   - XP progress within the current level
    """
    level = 1
    remaining = total_xp
    while True:
        needed = xp_needed_for_level(level)
        if remaining < needed:
            break
        remaining -= needed
        level += 1
        if level >= PRESTIGE_LEVEL:
            # Reached prestige threshold - cap here (caller handles prestige logic)
            break
    return level, remaining


def prestige_multiplier(prestige: int) -> float:
    """
    Return the XP gain multiplier for the given prestige count.

    Each prestige level adds +5%, capped at +25% (prestige ≥ 5):
        prestige 0 → 1.00x
        prestige 1 → 1.05x
        prestige 2 → 1.10x
        prestige 3 → 1.15x
        prestige 4 → 1.20x
        prestige 5+ → 1.25x
    """
    bonus = min(prestige * PRESTIGE_XP_BONUS_PER_LEVEL, PRESTIGE_XP_BONUS_CAP)
    return 1.0 + bonus


# ---------------------------------------------------------------------------
# Shared soft cap helper
# ---------------------------------------------------------------------------

def _soft_cap(value: float, threshold: float, scale: float) -> float:
    """
    Apply a soft cap to *value*.

    Values at or below *threshold* are returned unchanged. Above the threshold
    the excess is compressed via an exponential curve so the result approaches
    (threshold + scale) asymptotically without a hard ceiling.

    Formula: threshold + scale * (1 - exp(-(value - threshold) / scale))
    """
    if value <= threshold:
        return value
    overflow = value - threshold
    return threshold + scale * (1 - exp(-overflow / scale))


# ---------------------------------------------------------------------------
# Match XP calculation helpers
# ---------------------------------------------------------------------------

def streak_bonus(current_streak: int) -> float:
    """
    Return the streak XP multiplier for the given consecutive-win count.

    The raw multiplier is computed in three phases, then soft-capped:
        streak 2      → +8%
        streak 3      → +16%
        streak 4      → +25%
        streak 5      → +34%
        streak 6      → +40%  (soft cap threshold)
        streak 8      → +48%  (after soft cap compression)
        streak 10     → +53%
        streak 15     → +58%
        streak 20+    → ~+59% (asymptote)

    A hard safety cap of +120% remains in place but is never reached in
    practice due to the soft cap (threshold=+40%, scale=+20%).
    """
    if current_streak < STREAK_BONUS_START:
        return 0.0
    if current_streak <= STREAK_BONUS_EARLY_CAP:
        raw = STREAK_BONUS_PER_WIN_EARLY * (current_streak - 1)
    elif current_streak <= STREAK_BONUS_MID_CAP:
        raw = STREAK_BONUS_MID_BASE + STREAK_BONUS_PER_WIN_MID * (current_streak - STREAK_BONUS_EARLY_CAP)
    else:
        raw = min(
            STREAK_BONUS_LATE_BASE + STREAK_BONUS_PER_WIN_LATE * (current_streak - STREAK_BONUS_MID_CAP),
            STREAK_BONUS_MAX,
        )
    return _soft_cap(raw, STREAK_SOFT_CAP_THRESHOLD, STREAK_SOFT_CAP_SCALE)


def high_stakes_bonus(own_elo: float, opp_elo: float) -> float:
    """
    Additional flat bonus reflecting the ELO weight of the match.

    Formula:
        raw = (own_elo + opp_elo + max(opp_elo - own_elo, 0)) / 2000 * 25
        result = soft_cap(raw, threshold=50, scale=20)

    The underdog side (opp_elo > own_elo) receives a slightly higher raw
    value due to the diff term. Soft cap keeps extreme ELO gaps from
    dominating the XP total.

    Examples (no soft cap active until combined ELO > ~2000):
        1000 vs 1000 → 25.0 XP
        1200 vs 1200 → 30.0 XP
        2000 vs 2000 → 50.0 XP  (threshold)
        1000 vs 2000 → 50.0 XP  (threshold, underdog side)
    """
    combined = own_elo + opp_elo
    diff = abs(own_elo - opp_elo) if opp_elo > own_elo else 0.0
    raw = (combined + diff) / HIGH_STAKES_ELO_REFERENCE * HIGH_STAKES_BONUS_SCALE
    return round(_soft_cap(raw, HIGH_STAKES_SOFT_CAP_THRESHOLD, HIGH_STAKES_SOFT_CAP_SCALE), 2)


def match_length_bonus(own_score: int, opp_score: int) -> float:
    """
    Bonus for longer, more competitive matches based on total points scored.

    Formula:
        score_base = exp((2 * total_score - 8) / 4)
        raw = (15 * score_base - 10) * (1.1 if win else 1.0)
        result = soft_cap(raw, threshold=50, scale=30)

    The offset of 10 means even short matches yield a small positive bonus.
    The winner receives a 10% premium. The soft cap prevents very high-scoring
    matches from producing runaway XP totals.

    Examples (win / loss):
        4:0  →   5.5 /  5.0 XP
        4:1  →  16.2 / 14.7 XP
        4:2  →  33.9 / 30.8 XP
        4:3  →  60.5 / 56.4 XP  (soft cap active)
        5:3  →  76.1 / 74.5 XP
        6:4+ →  ~80 XP (asymptote)
    """
    total_score = own_score + opp_score
    score_base = exp((2 * total_score - 8) / 4)
    win_mult = 1.1 if own_score > opp_score else 1.0
    raw = (MATCH_LENGTH_BONUS_SCALE * score_base - MATCH_LENGTH_BONUS_OFFSET) * win_mult
    return round(_soft_cap(raw, MATCH_LENGTH_SOFT_CAP_THRESHOLD, MATCH_LENGTH_SOFT_CAP_SCALE), 2)


def performance_bonus_win(elo_gain: float, own_score: int, opp_score: int) -> float:
    """
    Performance bonus for a win, combining ELO gain and score dominance.

    Formula:
        perf_bonus   = 60 * (1 - exp(-1.5 * elo_gain / 60))
        score_factor = (1 + (own_score - opp_score) / max_score) * 40
        raw = perf_bonus + score_factor
        result = soft_cap(raw, threshold=90, scale=25)

    The ELO component uses a saturating curve so upset wins (high elo_gain)
    are rewarded but cannot grow unboundedly. The score factor rewards
    dominant victories. Soft cap keeps combined extremes in check.

    Examples (elo_gain=20):
        4:0 →  87.1 XP   4:2 →  78.8 XP   4:3 →  72.5 XP
    Examples (elo_gain=100):
        4:0 → 110.9 XP   4:2 → 102.6 XP
    """
    perf = PERFORMANCE_WIN_MULTIPLIER * max(elo_gain, 0.0)
    perf_bonus = PERFORMANCE_WIN_BASE * (1 - exp(-perf / PERFORMANCE_WIN_BASE))
    score_factor = 1.0 + (own_score - opp_score) / max(own_score, opp_score) if max(own_score, opp_score) > 0 else 0
    score_factor *= SCORE_FACTOR_MULTIPLIER
    return _soft_cap(perf_bonus + score_factor, PERF_WIN_SOFT_CAP_THRESHOLD, PERF_WIN_SOFT_CAP_SCALE)


def performance_bonus_loss(
    own_pre_elo: float,
    opp_pre_elo: float,
    own_score: int,
    opp_score: int,
) -> float:
    """
    Performance bonus for a loss, rewarding underdogs and close defeats.

    Formula:
        elo_diff     = max(opp_elo - own_elo, 0)   (0 when not an underdog)
        elo_bonus    = 35 * (1 - exp(-0.9 * elo_diff / 35))
        closeness    = 1 - (score_diff / max_score)   (1.0 = close, 0.0 = dominant)
        score_factor = closeness * 40
        raw = elo_bonus + score_factor
        result = soft_cap(raw, threshold=30, scale=15)

    Only underdogs (opp_elo > own_elo) receive the ELO component. The score
    component is available to any loser based on match closeness.

    Examples:
        1000 vs 1000, 3:4 → 30.0 XP  (score component only)
        1000 vs 1000, 0:4 →  0.0 XP  (no closeness, no underdog advantage)
        900 vs 1100,  3:4 → 43.5 XP  (soft cap active)
        900 vs 1100,  0:4 → 34.1 XP
    """
    max_score = max(own_score, opp_score)
    if max_score == 0:
        return 0.0

    # ELO component: saturating curve based on elo_diff (underdog only)
    elo_diff = max(opp_pre_elo - own_pre_elo, 0.0)
    perf = PERFORMANCE_LOSS_MULTIPLIER * elo_diff
    elo_bonus = PERFORMANCE_LOSS_BASE * (1 - exp(-perf / PERFORMANCE_LOSS_BASE))

    # Score component: close loss = higher bonus (inverse of win score_factor)
    score_diff = abs(opp_score - own_score)
    closeness = 1.0 - (score_diff / max_score)  # 1.0 = close, 0.0 = dominant
    score_factor = closeness * SCORE_FACTOR_MULTIPLIER

    return _soft_cap(elo_bonus + score_factor, PERF_LOSS_SOFT_CAP_THRESHOLD, PERF_LOSS_SOFT_CAP_SCALE)


def apply_soft_cap(xp: float) -> float:
    """
    Apply a soft cap to the total XP for a single match event.

    Values at or below 500 XP pass through unchanged. Above 500, gains are
    compressed asymptotically toward ~700 XP (threshold=500, scale=200).

    This cap is applied to the fully assembled match XP (after prestige
    multiplier) and also to the season matchday bonus addition.
    """
    if xp <= SOFT_CAP_THRESHOLD:
        return xp
    overflow = xp - SOFT_CAP_THRESHOLD
    scaled_excess = SOFT_CAP_THRESHOLD + SOFT_CAP_SCALE * (1 - exp(-overflow / SOFT_CAP_SCALE))
    return round(scaled_excess, 2)


def compute_match_xp(
    won: bool,
    elo_gain: float,
    own_pre_elo: float,
    opp_pre_elo: float,
    own_score: int,
    opp_score: int,
    win_streak: int,
    prestige: int,
) -> dict:
    """
    Compute the full XP breakdown for a single bey in a single match.

    Assembly order:
        1. base_xp + result_bonus + performance_bonus + high_stakes_bonus
           + match_length_bonus  →  component_sum
        2. component_sum * (1 + streak_multiplier)  →  raw_xp
        3. raw_xp * prestige_multiplier             →  pre_cap_xp
        4. apply_soft_cap(pre_cap_xp)               →  total_xp

    The streak multiplier is only applied on wins; prestige multiplier
    applies to all matches.

    Returns a dict with keys:
        base_xp, result_bonus, performance_bonus, high_stakes_bonus,
        match_length_bonus, streak_bonus, prestige_multiplier,
        total_xp, elo_gain, won, win_streak
    """
    base = BASE_XP
    result_bonus = WIN_BONUS if won else LOSS_BONUS
    if won:
        perf_bonus = performance_bonus_win(elo_gain, own_score, opp_score)
    else:
        perf_bonus = performance_bonus_loss(own_pre_elo, opp_pre_elo, own_score, opp_score)
    s_bonus = streak_bonus(win_streak) if won else 0
    h_bonus = high_stakes_bonus(own_pre_elo, opp_pre_elo)
    ml_bonus = match_length_bonus(own_score, opp_score)
    raw_xp = (base + result_bonus + perf_bonus + h_bonus + ml_bonus) * (1.0 + s_bonus)
    mult = prestige_multiplier(prestige)
    total = apply_soft_cap(raw_xp * mult)
    return {
        "base_xp": base,
        "result_bonus": result_bonus,
        "performance_bonus": round(perf_bonus, 2),
        "high_stakes_bonus": h_bonus,
        "match_length_bonus": ml_bonus,
        "streak_bonus": s_bonus,
        "prestige_multiplier": round(mult, 4),
        "total_xp": round(total, 2),
        "elo_gain": round(elo_gain, 2),
        "won": won,
        "win_streak": win_streak,
    }


# ---------------------------------------------------------------------------
# Tournament XP
# ---------------------------------------------------------------------------

def placement_multiplier(rank: int, total: int) -> float:
    """
    Return the XP multiplier for a bey finishing *rank*-th out of *total*.

    rank is 1-indexed (1 = winner). Returns 1.0 (participation) when *total*
    or *rank* is not positive (invalid input).

    Multiplier table:
        1st       → 2.2x
        2nd       → 1.8x
        Top 10%   → 1.5x
        Top 25%   → 1.25x
        Top 50%   → 1.15x
        Rest      → 1.0x
    """
    if total <= 0 or rank <= 0:
        return 1.0
    if rank == 1:
        return 2.2
    if rank == 2:
        return 1.8
    pct = rank / total
    if pct <= 0.10:
        return 1.5
    if pct <= 0.25:
        return 1.25
    if pct <= 0.50:
        return 1.15
    return 1.0


def compute_tournament_xp(rank: int, participants: int) -> float:
    """
    Return the XP awarded for a tournament placement.

    Formula:
        base       = 180 + 32 * participants
        size_bonus = 1 + ((participants / 8)^2 / 100)
        total      = base * placement_multiplier(rank, participants) * size_bonus

    The size_bonus provides a small quadratic scaling for larger tournaments,
    e.g. 8 participants → 1.01x, 16 participants → 1.04x, 32 → 1.16x.
    """
    base = TOURNAMENT_BASE + TOURNAMENT_PARTICIPANTS_FACTOR * participants
    size_bonus = 1 + (((participants / 8) ** 2) / 100)
    mult = placement_multiplier(rank, participants) * size_bonus
    return round(base * mult, 2)


# ---------------------------------------------------------------------------
# Season XP
# ---------------------------------------------------------------------------

def season_matchday_xp(tier: int) -> int:
    """
    Return the flat per-matchday XP bonus for the given season tier (1–4).

    Tier 1 → 100 XP | Tier 2 → 80 XP | Tier 3 → 60 XP | Tier 4 → 40 XP

    Returns 0 for any tier not in the table.
    """
    return SEASON_MATCHDAY_XP.get(tier, 0)


def season_end_xp(season_total_xp: float, placement: int, tier: int) -> float:
    """
    Return the end-of-season bonus XP for a bey.

    The bonus is additive: (combined_multiplier - 1) * season_total_xp,
    so the bey's total season contribution becomes season_total_xp * combined_multiplier.

    combined_multiplier = placement_mult * tier_mult

    Placement multipliers: 1st → 2.5x | 2nd → 2.25x | 3rd → 1.8x | 4th → 1.3x | rest → 1.0x
    Tier multipliers:      Tier 1 → 1.5x | Tier 2 → 1.3x | Tier 3 → 1.15x | Tier 4 → 1.0x

    Example: 1st place in Tier 1 with 900 XP earned during the season:
        combined = 2.5 * 1.5 = 3.75x  →  bonus = (3.75 - 1) * 900 = 2,475 XP
    """
    mult = SEASON_PLACEMENT_MULTIPLIER.get(placement, 1.0) * SEASON_PLACEMENT_TIER_MULTIPLIER.get(tier, 1.0)
    return round((mult - 1.0) * season_total_xp, 2)


def normalize_bey_key(name: str) -> str:
    """Normalize bey name for loose matching across manual config files."""
    if not name:
        return ""
    return "".join(ch for ch in str(name).lower() if ch not in " _-")


def normalize_season_id(season_id: str) -> str:
    """Normalize season ID for consistent matching."""
    if not season_id:
        return ""
    return str(season_id).strip().upper()


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _default_bey_state() -> dict:
    """Return a fresh bey tracking state."""
    return {
        "xp": 0.0,
        "level": 1,
        "prestige": 0,
        "xp_in_level": 0.0,
        "win_streak": 0,
        "season_xp": {},   # season_id -> {tier -> xp earned from matchday bonuses}
        "total_matches": 0,
        "total_wins": 0,
    }


def _apply_xp(state: dict, xp: float) -> None:
    """
    Add *xp* to bey *state*, handling level-ups and prestige resets.

    Level-ups cascade: if enough XP is added to cross multiple level
    thresholds in one call, all intermediate levels are processed.
    When level reaches PRESTIGE_LEVEL (50), prestige is incremented,
    level resets to 1, and both xp and xp_in_level reset to 0.
    """
    state["xp"] += xp
    state["xp_in_level"] += xp
    # Check for level-ups (may cascade)
    while True:
        needed = xp_needed_for_level(state["level"])
        if state["xp_in_level"] < needed:
            break
        state["xp_in_level"] -= needed
        state["level"] += 1
        # Prestige trigger
        if state["level"] >= PRESTIGE_LEVEL:
            state["prestige"] += 1
            state["level"] = 1
            state["xp"] = 0.0
            state["xp_in_level"] = 0.0
            break


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def load_matches(path: str) -> list:
    """Load matches CSV, sorted chronologically by Date."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    rows.sort(key=lambda r: r["Date"])
    return rows


def load_elo_history(path: str) -> dict:
    """
    Load ELO history CSV and index by MatchID.

    Returns a dict: {match_id: {"BeyA": str, "BeyB": str,
                                "PreA": float, "PreB": float,
                                "PostA": float, "PostB": float,
                                "arena_updated": str}}
    Returns an empty dict if the file does not exist.
    """
    index = {}
    if not os.path.exists(path):
        return index
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row.get("MatchID", "")
            if not mid:
                continue
            index[mid] = {
                "BeyA": row.get("BeyA", ""),
                "BeyB": row.get("BeyB", ""),
                "PreA": float(row.get("PreA", 0) or 0),
                "PreB": float(row.get("PreB", 0) or 0),
                "PostA": float(row.get("PostA", 0) or 0),
                "PostB": float(row.get("PostB", 0) or 0),
                "arena_updated": row.get("elo_arena_updated", ""),
            }
    return index


def load_tournament_placements(path: str) -> tuple:
    """
    Load manually maintained tournament_placements.json.

    Supports two layouts of the JSON file:

    *Flat (legacy)*: tournament IDs are top-level keys.
    *Nested*: a ``"tournaments"`` key holds the placements dict and an optional
    ``"season_end_placements"`` key holds end-of-season placement data.

    Keys starting with ``_`` are treated as comments and ignored in both formats.

    Returns:
        (tournaments_dict, season_end_dict) where each value is a plain dict.
        Both dicts are empty when the file does not exist.
    """
    if not os.path.exists(path):
        return {}, {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    season_end = data.get("season_end_placements", {})

    if "tournaments" in data:
        tournaments = {
            k: v for k, v in data.get("tournaments", {}).items()
            if not str(k).startswith("_")
        }
        season_end = {
            k: v for k, v in season_end.items()
            if not str(k).startswith("_")
        }
    else:
        # Legacy flat format: filter out metadata keys
        tournaments = {
            k: v for k, v in data.items()
            if not k.startswith("_") and k != "season_end_placements"
        }

    return tournaments, season_end


def _iter_tier_placements(season_end_entry: dict):
    """
    Yield (tier_key, placements_list) pairs from a season_end entry.

    Supports two formats:

    1) Legacy single list:
       {"placements": ["BeyA", "BeyB", ...]}
       → yields ("all", [...])

    2) Tiered format (tier values may be a list or a dict with a
       "placements" key):
       {"tiers": {"1": ["BeyA", ...], "2": {"placements": ["BeyC", ...]}}}
       → yields ("1", [...]), ("2", [...])
    """
    if not isinstance(season_end_entry, dict):
        return

    # Legacy single-placement list
    legacy = season_end_entry.get("placements")
    if isinstance(legacy, list):
        yield "all", legacy
        return

    tiers = season_end_entry.get("tiers", {})
    if not isinstance(tiers, dict):
        return

    for tier_key, tier_data in tiers.items():
        if isinstance(tier_data, list):
            yield str(tier_key), tier_data
        elif isinstance(tier_data, dict):
            placements = tier_data.get("placements", [])
            if isinstance(placements, list):
                yield str(tier_key), placements


def load_tournaments(path: str) -> dict:
    """Return {tournament_id: tournament_dict} from tournaments.json."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {t["id"]: t for t in data.get("tournaments", [])}


def run_xp_pipeline() -> None:
    """Execute the full XP calculation pipeline and write output files."""

    print(f"{CYAN}Running XP / Level System pipeline...{RESET}")

    # ------------------------------------------------------------------
    # Load inputs
    # ------------------------------------------------------------------
    print(f"{YELLOW}Loading matches from {MATCHES_CSV}...{RESET}")
    matches = load_matches(MATCHES_CSV)
    print(f"{GREEN}  {len(matches)} matches loaded.{RESET}")

    print(f"{YELLOW}Loading ELO history from {ELO_HISTORY_CSV}...{RESET}")
    elo_history = load_elo_history(ELO_HISTORY_CSV)
    print(f"{GREEN}  {len(elo_history)} ELO history entries loaded.{RESET}")

    print(f"{YELLOW}Loading tournament placements from {TOURNAMENT_PLACEMENTS_JSON}...{RESET}")
    tournament_placements, season_end_placements = load_tournament_placements(
        TOURNAMENT_PLACEMENTS_JSON
    )
    print(f"{GREEN}  {len(tournament_placements)} tournament placement entries loaded.{RESET}")
    print(f"{GREEN}  {len(season_end_placements)} season end-placement entries loaded.{RESET}")

    tournaments = load_tournaments(TOURNAMENTS_JSON)

    # ------------------------------------------------------------------
    # Build a unified chronological event list
    # ------------------------------------------------------------------
    # Each event has: {"type": "match"|"tournament"|"season_end", "date": str, ...}
    # Tournaments/season-ends use the date from their data or from tournaments.json;
    # events with no date fall back to "9999-12-31" so they are applied last.
    # Within the same date, matches are processed before non-match events.
    _DATE_LAST = "9999-12-31"

    events = []

    for m in matches:
        events.append({"type": "match", "date": m.get("Date", ""), "data": m})

    for tid, pdata in tournament_placements.items():
        if not isinstance(pdata, dict):
            continue
        # Prefer explicit date in the placement entry, then look up tournaments.json
        t_date = pdata.get("date", "")
        if not t_date:
            t_date = tournaments.get(tid, {}).get("date", _DATE_LAST)
        events.append({
            "type": "tournament",
            "date": t_date or _DATE_LAST,
            "tid": tid,
            "data": pdata,
        })

    for sid, sdata in season_end_placements.items():
        if not isinstance(sdata, dict):
            continue
        events.append({
            "type": "season_end",
            "date": sdata.get("date", _DATE_LAST),
            "season_id": normalize_season_id(sid),
            "data": sdata,
        })

    # Stable sort: matches first within any given date
    _EVENT_ORDER = {"match": 0, "tournament": 1, "season_end": 2}
    events.sort(key=lambda e: (e["date"], _EVENT_ORDER.get(e["type"], 2)))

    # Build quick normalized lookup so manual config names can still match
    # canonical names used in matches.csv / elo_history.csv.
    canonical_by_norm = {}
    for m in matches:
        for b in (m.get("BeyA", ""), m.get("BeyB", "")):
            n = normalize_bey_key(b)
            if n and n not in canonical_by_norm:
                canonical_by_norm[n] = b

    def resolve_bey_name(name: str) -> str:
        """Map a manual-config bey name to canonical match name when possible."""
        if not name:
            return ""
        return canonical_by_norm.get(normalize_bey_key(name), name)

    # ------------------------------------------------------------------
    # Process events in chronological order
    # ------------------------------------------------------------------
    bey_states: dict = {}   # bey_name → state dict
    xp_history: dict = {}   # match_id → per-bey breakdown

    def get_state(bey: str) -> dict:
        if bey not in bey_states:
            bey_states[bey] = _default_bey_state()
        return bey_states[bey]

    for event in events:
        etype = event["type"]

        if etype == "match":
            m = event["data"]
            match_id = m.get("MatchID", "")
            bey_a = m["BeyA"]
            bey_b = m["BeyB"]
            score_a = int(m["ScoreA"])
            score_b = int(m["ScoreB"])
            match_type = m.get("MatchType", "exhibition")
            season_id = normalize_season_id(m.get("SeasonID", ""))
            tier_str = m.get("Tier", "")
            tier = int(tier_str) if tier_str.isdigit() else None

            won_a = score_a > score_b
            won_b = score_b > score_a

            state_a = get_state(bey_a)
            state_b = get_state(bey_b)

            # ELO info for this match
            elo_info = elo_history.get(match_id, {})
            pre_a = elo_info.get("PreA", 0.0)
            pre_b = elo_info.get("PreB", 0.0)
            post_a = elo_info.get("PostA", 0.0)
            post_b = elo_info.get("PostB", 0.0)
            elo_gain_a = post_a - pre_a
            elo_gain_b = post_b - pre_b

            # Update win streaks before computing XP
            if won_a:
                state_a["win_streak"] += 1
                state_b["win_streak"] = 0
            elif won_b:
                state_b["win_streak"] += 1
                state_a["win_streak"] = 0
            # draws: no update (shouldn't exist in this system)

            # Compute match XP
            xp_a = compute_match_xp(
                won=won_a,
                elo_gain=elo_gain_a,
                own_pre_elo=pre_a,
                opp_pre_elo=pre_b,
                own_score=score_a,
                opp_score=score_b,
                win_streak=state_a["win_streak"],
                prestige=state_a["prestige"],
            )
            xp_b = compute_match_xp(
                won=won_b,
                elo_gain=elo_gain_b,
                own_pre_elo=pre_b,
                opp_pre_elo=pre_a,
                own_score=score_b,
                opp_score=score_a,
                win_streak=state_b["win_streak"],
                prestige=state_b["prestige"],
            )

            # Add season matchday XP bonus when applicable
            if match_type in ("season", "relegation") and tier is not None:
                md_xp = season_matchday_xp(tier)
                for xp_dict in (xp_a, xp_b):
                    xp_dict["season_matchday_xp"] = md_xp
                    xp_dict["total_xp"] = round(
                        apply_soft_cap(xp_dict["total_xp"] + md_xp), 2
                    )
            else:
                xp_a["season_matchday_xp"] = 0
                xp_b["season_matchday_xp"] = 0

            # Track season XP (matchday bonus only - for end-of-season multiplier)
            if season_id and tier is not None:
                md_xp_for_season = season_matchday_xp(tier)

                tier_key = str(tier)
                season_a = state_a["season_xp"].setdefault(season_id, {})
                season_b = state_b["season_xp"].setdefault(season_id, {})
                season_a[tier_key] = (
                    season_a.get(tier_key, 0.0) + md_xp_for_season
                )
                season_b[tier_key] = (
                    season_b.get(tier_key, 0.0) + md_xp_for_season
                )

            # Apply XP to state
            _apply_xp(state_a, xp_a["total_xp"])
            _apply_xp(state_b, xp_b["total_xp"])

            state_a["total_matches"] += 1
            state_b["total_matches"] += 1
            if won_a:
                state_a["total_wins"] += 1
            if won_b:
                state_b["total_wins"] += 1

            # Record history entry
            if match_id:
                xp_history[match_id] = {
                    "date": m.get("Date", ""),
                    "bey_a": {**xp_a, "bey": bey_a},
                    "bey_b": {**xp_b, "bey": bey_b},
                }

        elif etype == "tournament":
            placement_data = event["data"]
            tid = event["tid"]
            placements_list = placement_data.get("placements", [])
            participants = placement_data.get("participants", 0)
            if participants <= 0:
                participants = tournaments.get(tid, {}).get("players", 0)
            for rank_idx, bey in enumerate(placements_list):
                if not bey:
                    continue
                bey = resolve_bey_name(bey)
                rank = rank_idx + 1
                t_xp = compute_tournament_xp(rank, participants)
                state = get_state(bey)
                _apply_xp(state, t_xp)
                # Transparency: record non-match XP event history
                xp_history.setdefault("__events__", []).append({
                    "type": "tournament",
                    "date": event.get("date", ""),
                    "tournament_id": tid,
                    "bey": bey,
                    "rank": rank,
                    "participants": participants,
                    "xp_awarded": round(t_xp, 2),
                })

        elif etype == "season_end":
            sid = event["season_id"]
            sdata = event["data"]
            for tier_key, placements_list in _iter_tier_placements(sdata):
                for rank_idx, bey in enumerate(placements_list):
                    if not bey:
                        continue
                    bey = resolve_bey_name(bey)
                    rank = rank_idx + 1
                    state = get_state(bey)
                    season_bucket = state["season_xp"].get(normalize_season_id(sid), {})
                    if tier_key == "all":
                        season_total = sum(season_bucket.values())
                        # Legacy single-list format has no tier context.
                        # Use Tier 4 (neutral 1.0x tier multiplier).
                        tier_for_bonus = 4
                    else:
                        season_total = season_bucket.get(str(tier_key), 0.0)
                        tier_for_bonus = int(tier_key)
                    if season_total > 0:
                        bonus = season_end_xp(season_total, rank, tier_for_bonus)
                        _apply_xp(state, bonus)
                        xp_history.setdefault("__events__", []).append({
                            "type": "season_end",
                            "date": event.get("date", ""),
                            "season_id": normalize_season_id(sid),
                            "tier": tier_key,
                            "bey": bey,
                            "rank": rank,
                            "season_total_xp": round(season_total, 2),
                            "xp_awarded": round(bonus, 2),
                        })

    print(f"{GREEN}  XP events processed ({len(events)} total events).{RESET}")

    # ------------------------------------------------------------------
    # Build leaderboard output
    # ------------------------------------------------------------------
    leaderboard = []
    for bey, state in bey_states.items():
        xp_to_next = max(0.0, xp_needed_for_level(state["level"]) - state["xp_in_level"])
        prestige_display = f"⭐{'I' * state['prestige']}" if state["prestige"] > 0 else ""
        leaderboard.append({
            "bey": bey,
            "level": state["level"],
            "prestige": state["prestige"],
            "prestige_display": prestige_display,
            "xp": round(state["xp"], 2),
            "xp_in_level": round(state["xp_in_level"], 2),
            "xp_to_next_level": round(xp_to_next, 2),
            "xp_needed_for_level": round(xp_needed_for_level(state["level"]), 2),
            "total_matches": state["total_matches"],
            "total_wins": state["total_wins"],
            "win_streak": state["win_streak"],
        })

    # Sort by prestige desc, then level desc, then xp_in_level desc
    leaderboard.sort(
        key=lambda e: (e["prestige"], e["level"], e["xp_in_level"]),
        reverse=True,
    )
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    os.makedirs(ANALYTICS_DIR, exist_ok=True)

    print(f"{YELLOW}Writing XP leaderboard to {XP_LEADERBOARD_JSON}...{RESET}")
    with open(XP_LEADERBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2, ensure_ascii=False)
    print(f"{GREEN}  {len(leaderboard)} beys written.{RESET}")

    print(f"{YELLOW}Writing XP history to {XP_HISTORY_JSON}...{RESET}")
    with open(XP_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(xp_history, f, indent=2, ensure_ascii=False)
    print(f"{GREEN}  {len(xp_history)} match entries written.{RESET}")

    print(f"{GREEN}XP / Level System pipeline complete.{RESET}")


if __name__ == "__main__":
    run_xp_pipeline()
