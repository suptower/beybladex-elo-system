#!/usr/bin/env python3
"""
XP and Level System for BeybladeX ELO System

Calculates experience points (XP) and levels for each Bey based on match
participation, ELO performance, win streaks, tournament placements and season
tier bonuses.

XP Formula (per match):
    XP = (Base XP + Result Bonus + Performance Bonus + Streak Bonus)
         * prestige_multiplier
    Max XP per match: 300

    Base XP:        100 (any valid match)
    Result Bonus:   +80 (win) / +20 (loss)
    Performance Bonus (Win):  min(1.5 * elo_gain, 50)
    Performance Bonus (Loss, underdog only):
        elo_diff  = opponent_elo - own_elo  (only when positive)
        closeness = 1 - (score_diff / max_score)
        bonus     = min(0.3 * elo_diff * closeness, 40)
    Streak Bonus:
        2 wins → +10, 3 wins → +20, 4 wins → +30, 5+ wins → +40

Level Curve:
    XP_needed(level) = 50 * level ** 1.3
    (XP to advance from level-1 → level; cumulative total determines current level)

Prestige:
    Triggered at level 50.  Level resets to 1, XP to 0, prestige counter +1.
    Prestige bonus: +5% XP per prestige level, capped at +25% (prestige ≥ 5).

Tournament XP:
    base   = 150 + participants * 25
    factor per placement:
        1st          → 3.0×
        2nd          → 2.5×
        Finalist     → 2.5× (same bracket position as 2nd)
        Top 10%      → 2.0×
        Top 25%      → 1.5×
        Top 50%      → 1.15×
        Participation → 1.0×

Season XP:
    Per matchday flat bonus:   Tier 1 → +150 / Tier 2 → +120 / Tier 3 → +100 / Tier 4 → +80
    End-of-season multiplier applied to total season XP earned:
        1st  → 3.0×  |  2nd → 2.2×  |  3rd → 1.8×
        4th  → 1.3×  |  Rest → 1.0×

Output files:
    docs/data/analytics/xp_leaderboard.json  – Current XP / level / prestige per Bey
    docs/data/analytics/xp_history.json      – Per-match XP breakdown (keyed by MatchID)

Usage:
    python xp_system.py
"""

import csv
import json
import os
import sys

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
BASE_XP = 100
WIN_BONUS = 80
LOSS_BONUS = 20

PERFORMANCE_WIN_MULTIPLIER = 1.5
PERFORMANCE_WIN_CAP = 50

PERFORMANCE_LOSS_MULTIPLIER = 0.3
PERFORMANCE_LOSS_CAP = 40

# Streak bonuses indexed by streak length (index 0 unused, 1 unused, 2…5+)
STREAK_BONUS = {2: 10, 3: 20, 4: 30}
STREAK_BONUS_MAX = 40        # 5+ wins
STREAK_BONUS_MAX_THRESHOLD = 5

MAX_XP_PER_MATCH = 300

# Level curve
LEVEL_XP_BASE = 50
LEVEL_XP_EXPONENT = 1.3

# Prestige
PRESTIGE_LEVEL = 50
PRESTIGE_XP_BONUS_PER_LEVEL = 0.05  # +5 % per prestige
PRESTIGE_XP_BONUS_CAP = 0.25        # max +25 %

# Tournament XP
TOURNAMENT_BASE = 150
TOURNAMENT_PARTICIPANTS_FACTOR = 25

# Season per-matchday XP by tier (1-indexed)
SEASON_MATCHDAY_XP = {1: 150, 2: 120, 3: 100, 4: 80}

# Season end-of-season placement multipliers (1-indexed, fallback 1.0)
SEASON_PLACEMENT_MULTIPLIER = {1: 3.0, 2: 2.2, 3: 1.8, 4: 1.3}


# ---------------------------------------------------------------------------
# Level helpers
# ---------------------------------------------------------------------------

def xp_needed_for_level(level: int) -> float:
    """Return the XP required to advance from level-1 to *level* (≥1)."""
    if level < 1:
        return 0.0
    return LEVEL_XP_BASE * (level ** LEVEL_XP_EXPONENT)


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
            # Reached prestige threshold – cap here (caller handles prestige logic)
            break
    return level, remaining


def prestige_multiplier(prestige: int) -> float:
    """Return the XP gain multiplier for the given prestige count."""
    bonus = min(prestige * PRESTIGE_XP_BONUS_PER_LEVEL, PRESTIGE_XP_BONUS_CAP)
    return 1.0 + bonus


# ---------------------------------------------------------------------------
# Match XP calculation helpers
# ---------------------------------------------------------------------------

def streak_bonus(current_streak: int) -> int:
    """Return streak XP bonus for the given consecutive-win count."""
    if current_streak >= STREAK_BONUS_MAX_THRESHOLD:
        return STREAK_BONUS_MAX
    return STREAK_BONUS.get(current_streak, 0)


def performance_bonus_win(elo_gain: float) -> float:
    """Performance bonus for a win based on ELO gain."""
    return min(PERFORMANCE_WIN_MULTIPLIER * max(elo_gain, 0.0), PERFORMANCE_WIN_CAP)


def performance_bonus_loss(
    own_pre_elo: float,
    opp_pre_elo: float,
    own_score: int,
    opp_score: int,
) -> float:
    """
    Performance bonus for an underdog loss.

    Only applies when opponent_elo > own_elo.
    """
    elo_diff = opp_pre_elo - own_pre_elo
    if elo_diff <= 0:
        return 0.0
    max_score = max(own_score, opp_score)
    if max_score == 0:
        return 0.0
    score_diff = abs(opp_score - own_score)
    closeness = 1.0 - (score_diff / max_score)
    return min(PERFORMANCE_LOSS_MULTIPLIER * elo_diff * closeness, PERFORMANCE_LOSS_CAP)


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
    Compute XP breakdown for a single bey in a single match.

    Returns a dict with all component values and the capped total.
    """
    base = BASE_XP
    result_bonus = WIN_BONUS if won else LOSS_BONUS
    if won:
        perf_bonus = performance_bonus_win(elo_gain)
    else:
        perf_bonus = performance_bonus_loss(own_pre_elo, opp_pre_elo, own_score, opp_score)
    s_bonus = streak_bonus(win_streak) if won else 0
    raw_xp = base + result_bonus + perf_bonus + s_bonus
    mult = prestige_multiplier(prestige)
    total = min(raw_xp * mult, MAX_XP_PER_MATCH)
    return {
        "base_xp": base,
        "result_bonus": result_bonus,
        "performance_bonus": round(perf_bonus, 2),
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

    rank is 1-indexed (1 = winner).  Returns 1.0 (participation) when *total*
    or *rank* is not positive (invalid input).
    """
    if total <= 0 or rank <= 0:
        return 1.0
    if rank == 1:
        return 3.0
    if rank == 2:
        return 2.5
    pct = rank / total
    if pct <= 0.10:
        return 2.0
    if pct <= 0.25:
        return 1.5
    if pct <= 0.50:
        return 1.15
    return 1.0


def compute_tournament_xp(rank: int, participants: int) -> float:
    """Return XP awarded for a tournament placement."""
    base = TOURNAMENT_BASE + TOURNAMENT_PARTICIPANTS_FACTOR * participants
    mult = placement_multiplier(rank, participants)
    return round(base * mult, 2)


# ---------------------------------------------------------------------------
# Season XP
# ---------------------------------------------------------------------------

def season_matchday_xp(tier: int) -> int:
    """Return per-matchday XP bonus for the given tier (1–4)."""
    return SEASON_MATCHDAY_XP.get(tier, 0)


def season_end_xp(season_total_xp: float, placement: int) -> float:
    """
    Return the end-of-season bonus XP.

    The bonus is (multiplier - 1) * season_total_xp so that the total
    season contribution becomes season_total_xp * multiplier.
    """
    mult = SEASON_PLACEMENT_MULTIPLIER.get(placement, 1.0)
    return round((mult - 1.0) * season_total_xp, 2)


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
        "season_xp": {},   # season_id → xp earned from matchday bonuses
        "total_matches": 0,
        "total_wins": 0,
    }


def _apply_xp(state: dict, xp: float) -> None:
    """Add *xp* to bey *state*, handling level-ups and prestige resets."""
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
    """Load matches CSV, sorted chronologically."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    rows.sort(key=lambda r: r["Date"])
    return rows


def load_elo_history(path: str) -> dict:
    """
    Load ELO history CSV and index by MatchID.

    Returns a dict: {match_id: {"bey_a": ..., "bey_b": ...}}
    where each inner value is a dict with pre/post ELO for BeyA and BeyB.
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
        tournaments = data["tournaments"]
    else:
        # Legacy flat format: filter out metadata keys
        tournaments = {
            k: v for k, v in data.items()
            if not k.startswith("_") and k != "season_end_placements"
        }

    return tournaments, season_end


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
        events.append({
            "type": "season_end",
            "date": sdata.get("date", _DATE_LAST),
            "season_id": sid,
            "data": sdata,
        })

    # Stable sort: matches first within any given date
    _EVENT_ORDER = {"match": 0, "tournament": 1, "season_end": 1}
    events.sort(key=lambda e: (e["date"], _EVENT_ORDER.get(e["type"], 2)))

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
            season_id = m.get("SeasonID", "")
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
                        min(xp_dict["total_xp"] + md_xp, MAX_XP_PER_MATCH), 2
                    )
            else:
                xp_a["season_matchday_xp"] = 0
                xp_b["season_matchday_xp"] = 0

            # Track season XP (matchday bonus only – for end-of-season multiplier)
            if season_id and tier is not None:
                md_xp_for_season = season_matchday_xp(tier)
                state_a["season_xp"][season_id] = (
                    state_a["season_xp"].get(season_id, 0.0) + md_xp_for_season
                )
                state_b["season_xp"][season_id] = (
                    state_b["season_xp"].get(season_id, 0.0) + md_xp_for_season
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
                rank = rank_idx + 1
                t_xp = compute_tournament_xp(rank, participants)
                _apply_xp(get_state(bey), t_xp)

        elif etype == "season_end":
            sid = event["season_id"]
            placements_list = event["data"].get("placements", [])
            for rank_idx, bey in enumerate(placements_list):
                if not bey:
                    continue
                rank = rank_idx + 1
                state = get_state(bey)
                season_total = state["season_xp"].get(sid, 0.0)
                if season_total > 0:
                    bonus = season_end_xp(season_total, rank)
                    _apply_xp(state, bonus)

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
