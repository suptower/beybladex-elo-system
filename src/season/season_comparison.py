"""
Season vs Global Performance Comparison Analytics

Compares each Bey's season performance (within-tier, points-based ranking)
against its position in the global ELO leaderboard.

Key metrics produced
--------------------
- Season Percentile  : 1 - (season_rank - 1) / (tier_size - 1)
- Global Percentile  : 1 - (global_rank - 1) / (total_beys - 1)
- PDI                : Season Percentile - Global Percentile
                       > 0 → overperformer, < 0 → underperformer
- Expected Wins      : sum of Elo win-probabilities over season matches
- Actual Wins        : wins in season matches
- PvE                : Actual Wins - Expected Wins

A tier-strength overview is also generated:
- Average Global Percentile per tier
- Average Elo per tier
- Average PDI per tier

Only matches with MatchType == "season" are used for season metrics.
Global ranking is Elo-based across all match types as currently implemented.

Output
------
docs/data/season/season_comparison.json
"""

import csv
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

from src.config.paths import (
    DATA_DIR,
    MATCHES_CSV,
    ELO_HISTORY_CSV,
    LEADERBOARD_CSV,
    SEASON_DATA_JSON,
    SEASON_COMPARISON_JSON,
)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR = DATA_DIR
MATCHES_FILE = MATCHES_CSV
ELO_HISTORY_FILE = ELO_HISTORY_CSV
LEADERBOARD_FILE = LEADERBOARD_CSV
SEASON_DATA_FILE = SEASON_DATA_JSON
OUTPUT_FILE = SEASON_COMPARISON_JSON

# Colors for terminal output
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"

# ---------------------------------------------------------------------------
# Elo probability helper
# ---------------------------------------------------------------------------

ELO_SCALE = 400.0  # standard Elo scale factor


def elo_win_probability(elo_a: float, elo_b: float) -> float:
    """Return the probability that A beats B under the standard Elo model."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / ELO_SCALE))


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

def rank_to_percentile(rank: int, total: int) -> float:
    """
    Convert a 1-based rank to a percentile in [0, 1].

    Formula: 1 - (rank - 1) / (total - 1)
    Edge case: total == 1  → percentile = 1.0
    """
    if total <= 1:
        return 1.0
    return 1.0 - (rank - 1) / (total - 1)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_matches(filepath: str = MATCHES_FILE) -> List[Dict]:
    """Load all matches from CSV and return as list of dicts."""
    matches = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(dict(row))
    return matches


def load_elo_history(filepath: str = ELO_HISTORY_FILE) -> List[Dict]:
    """Load ELO history CSV and return as list of dicts."""
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_leaderboard(filepath: str = LEADERBOARD_FILE) -> List[Dict]:
    """Load current global leaderboard CSV and return as list of dicts."""
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_season_data(filepath: str = SEASON_DATA_FILE) -> Dict:
    """Load season data JSON."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Season league table helper
# ---------------------------------------------------------------------------

def build_season_league_table(
    season_matches: List[Dict],
    season_id: str,
    tier: int,
) -> List[Dict]:
    """
    Build a final league table for *season_id* / *tier*.

    Ranking: Season Points → Point Diff → Points For → (alphabetical fallback).
    Returns a list of dicts sorted from 1st to last, each containing:
        bey, season_points, wins, point_diff, points_for, position
    """
    standings: Dict[str, Dict] = defaultdict(lambda: {
        "season_points": 0,
        "wins": 0,
        "point_diff": 0,
        "points_for": 0,
        "points_against": 0,
    })

    for m in season_matches:
        if m.get("MatchType") != "season":
            continue
        if m.get("SeasonID") != season_id:
            continue
        try:
            m_tier = int(m.get("Tier", 0))
        except (ValueError, TypeError):
            continue
        if m_tier != tier:
            continue

        bey_a = m["BeyA"]
        bey_b = m["BeyB"]
        try:
            score_a = int(m["ScoreA"])
            score_b = int(m["ScoreB"])
        except (ValueError, TypeError):
            continue

        # Season points (win=3, dominant win=4, loss=0)
        if score_a > score_b:
            diff = score_a - score_b
            sp_a = 4 if (diff >= 4 and score_b == 0) else 3
            sp_b = 0
        elif score_b > score_a:
            diff = score_b - score_a
            sp_b = 4 if (diff >= 4 and score_a == 0) else 3
            sp_a = 0
        else:
            sp_a = sp_b = 0

        standings[bey_a]["season_points"] += sp_a
        standings[bey_b]["season_points"] += sp_b
        standings[bey_a]["point_diff"] += score_a - score_b
        standings[bey_b]["point_diff"] += score_b - score_a
        standings[bey_a]["points_for"] += score_a
        standings[bey_b]["points_for"] += score_b
        standings[bey_a]["points_against"] += score_b
        standings[bey_b]["points_against"] += score_a
        if score_a > score_b:
            standings[bey_a]["wins"] += 1
        elif score_b > score_a:
            standings[bey_b]["wins"] += 1

    if not standings:
        return []

    table = [{"bey": bey, **data} for bey, data in standings.items()]
    table.sort(key=lambda x: (
        -x["season_points"],
        -x["point_diff"],
        -x["points_for"],
        x["bey"],
    ))
    for i, entry in enumerate(table, 1):
        entry["position"] = i
    return table


# ---------------------------------------------------------------------------
# Global ranking from leaderboard
# ---------------------------------------------------------------------------

def build_global_ranking(leaderboard_rows: List[Dict]) -> Dict[str, Dict]:
    """
    Parse the global leaderboard CSV and return a dict:
        {bey_name: {"global_rank": int, "elo": float}}
    The leaderboard is already sorted by ELO descending; "Platz" column
    contains the rank number.
    """
    ranking: Dict[str, Dict] = {}
    for row in leaderboard_rows:
        bey = row.get("Name", "").strip()
        if not bey:
            continue
        try:
            rank = int(row["Platz"])
            elo = float(row["ELO"])
        except (ValueError, KeyError):
            continue
        ranking[bey] = {"global_rank": rank, "elo": elo}
    return ranking


# ---------------------------------------------------------------------------
# ELO snapshot per bey at the time of season matches
# ---------------------------------------------------------------------------

def build_pre_elo_map(elo_history: List[Dict], season_match_ids: set) -> Dict[str, float]:
    """
    Return a map of {bey: pre_elo} for the first season match each bey played.

    This is the ELO each bey carried *into* the season and is used as the
    reference for Elo-based win-probability calculations.
    """
    pre_elo: Dict[str, float] = {}
    for row in elo_history:
        if row.get("MatchID") not in season_match_ids:
            continue
        for bey_col, elo_col in [("BeyA", "PreA"), ("BeyB", "PreB")]:
            bey = row.get(bey_col, "").strip()
            if bey and bey not in pre_elo:
                try:
                    pre_elo[bey] = float(row[elo_col])
                except (ValueError, KeyError):
                    pass
    return pre_elo


# ---------------------------------------------------------------------------
# Expected wins calculation
# ---------------------------------------------------------------------------

def calculate_expected_wins(
    season_matches: List[Dict],
    season_id: str,
    tier: int,
    pre_elo_map: Dict[str, float],
) -> Dict[str, float]:
    """
    For each bey in *tier*, sum win-probabilities across all its season matches
    using the standard Elo formula.

    Uses pre-season Elo (first seen in ELO history for that bey).
    Falls back to the opponent's pre-season Elo and vice versa if not found.

    Returns {bey: expected_wins}
    """
    expected: Dict[str, float] = defaultdict(float)

    for m in season_matches:
        if m.get("MatchType") != "season":
            continue
        if m.get("SeasonID") != season_id:
            continue
        try:
            m_tier = int(m.get("Tier", 0))
        except (ValueError, TypeError):
            continue
        if m_tier != tier:
            continue

        bey_a = m["BeyA"]
        bey_b = m["BeyB"]

        elo_a = pre_elo_map.get(bey_a, 1000.0)
        elo_b = pre_elo_map.get(bey_b, 1000.0)

        prob_a = elo_win_probability(elo_a, elo_b)
        expected[bey_a] += prob_a
        expected[bey_b] += (1.0 - prob_a)

    return dict(expected)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_comparison(
    matches: List[Dict],
    elo_history: List[Dict],
    leaderboard_rows: List[Dict],
    season_id: Optional[str] = None,
    tier_filter: Optional[int] = None,
) -> Dict:
    """
    Compute the full season vs global comparison for one or all seasons/tiers.

    Parameters
    ----------
    matches         : all rows from matches.csv
    elo_history     : all rows from elo_history.csv
    leaderboard_rows: all rows from leaderboard.csv
    season_id       : if provided, only this season is processed
    tier_filter     : if provided, only this tier is processed

    Returns
    -------
    Dict with keys:
        "seasons": {
            season_id: {
                "tiers": {
                    tier_str: {
                        "beys": [ {bey stats} ... ],
                        "tier_strength": { avg_global_percentile, avg_elo, avg_pdi }
                    }
                }
            }
        }
    """
    global_ranking = build_global_ranking(leaderboard_rows)
    total_beys = len(global_ranking)

    # Determine which seasons to process
    season_ids_in_matches = sorted({
        m.get("SeasonID", "")
        for m in matches
        if m.get("MatchType") == "season" and m.get("SeasonID", "")
    })
    if season_id:
        season_ids_in_matches = [s for s in season_ids_in_matches if s == season_id]

    result: Dict = {"seasons": {}}

    for sid in season_ids_in_matches:
        # Find tiers present in this season
        tiers_in_season = sorted({
            int(m.get("Tier", 0))
            for m in matches
            if m.get("MatchType") == "season" and m.get("SeasonID") == sid
            and m.get("Tier", "").strip()
        })
        if tier_filter is not None:
            tiers_in_season = [t for t in tiers_in_season if t == tier_filter]

        # Build pre-Elo map for this season's matches
        season_match_ids = {
            m["MatchID"]
            for m in matches
            if m.get("MatchType") == "season" and m.get("SeasonID") == sid
        }
        pre_elo_map = build_pre_elo_map(elo_history, season_match_ids)

        season_result: Dict = {"tiers": {}}

        for tier in tiers_in_season:
            # Build league table
            table = build_season_league_table(matches, sid, tier)
            if not table:
                continue
            tier_size = len(table)

            # Expected wins
            expected_wins_map = calculate_expected_wins(
                matches, sid, tier, pre_elo_map
            )

            bey_stats = []
            for entry in table:
                bey = entry["bey"]
                season_rank = entry["position"]
                actual_wins = entry["wins"]

                season_percentile = rank_to_percentile(season_rank, tier_size)

                g = global_ranking.get(bey)
                if g and total_beys > 0:
                    global_rank = g["global_rank"]
                    elo = g["elo"]
                    global_percentile = rank_to_percentile(global_rank, total_beys)
                else:
                    global_rank = None
                    elo = pre_elo_map.get(bey, 1000.0)
                    global_percentile = None

                pdi = (
                    round(season_percentile - global_percentile, 4)
                    if global_percentile is not None
                    else None
                )

                exp_wins = expected_wins_map.get(bey, 0.0)
                pve = round(actual_wins - exp_wins, 4)

                bey_stats.append({
                    "bey": bey,
                    "tier": tier,
                    "season_id": sid,
                    "season_rank": season_rank,
                    "tier_size": tier_size,
                    "season_percentile": round(season_percentile, 4),
                    "global_rank": global_rank,
                    "global_percentile": (
                        round(global_percentile, 4) if global_percentile is not None else None
                    ),
                    "pdi": pdi,
                    "elo": round(elo, 1),
                    "actual_wins": actual_wins,
                    "expected_wins": round(exp_wins, 4),
                    "pve": pve,
                    "season_points": entry["season_points"],
                    "point_diff": entry["point_diff"],
                })

            # Tier strength summary (only beys with a valid global percentile)
            valid = [b for b in bey_stats if b["global_percentile"] is not None]
            valid_pdi = [b for b in valid if b["pdi"] is not None]
            if valid:
                avg_global_pct = sum(b["global_percentile"] for b in valid) / len(valid)
                avg_elo = sum(b["elo"] for b in valid) / len(valid)
                avg_pdi = (
                    sum(b["pdi"] for b in valid_pdi) / len(valid_pdi)
                    if valid_pdi else 0.0
                )
            else:
                avg_global_pct = avg_elo = avg_pdi = 0.0

            season_result["tiers"][str(tier)] = {
                "beys": bey_stats,
                "tier_strength": {
                    "avg_global_percentile": round(avg_global_pct, 4),
                    "avg_elo": round(avg_elo, 1),
                    "avg_pdi": round(avg_pdi, 4),
                },
            }

        result["seasons"][sid] = season_result

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(
    data_dir: str = DEFAULT_DATA_DIR,
    output_file: str = OUTPUT_FILE,
    season_id: Optional[str] = None,
    tier_filter: Optional[int] = None,
) -> None:
    """Load data, compute comparison metrics and write output JSON."""
    matches_path = os.path.join(data_dir, "matches/matches.csv")
    elo_history_path = os.path.join(data_dir, "elo/elo_history.csv")
    leaderboard_path = os.path.join(data_dir, "leaderboard/leaderboard.csv")

    matches = load_matches(matches_path)
    elo_history = load_elo_history(elo_history_path)
    leaderboard_rows = load_leaderboard(leaderboard_path)

    result = compute_comparison(
        matches=matches,
        elo_history=elo_history,
        leaderboard_rows=leaderboard_rows,
        season_id=season_id,
        tier_filter=tier_filter,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    season_count = len(result.get("seasons", {}))
    print(f"{GREEN}✓ Season comparison analytics written to {output_file} "
          f"({season_count} season(s) processed){RESET}")


if __name__ == "__main__":
    main()
