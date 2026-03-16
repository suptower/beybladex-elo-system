#!/usr/bin/env python3
"""
Generate leaderboard CSV files for historical ELO model versions (V1 and V2).

Runs each archived ELO version against the current match data (Xtreme arena
only, mirroring how the V3 main leaderboard is computed) and writes the
resulting leaderboard to:
  - docs/data/leaderboard/leaderboard_v1.csv
  - docs/data/leaderboard/leaderboard_v2.csv

The output format matches the standard leaderboard CSV so the frontend can
display V1/V2 leaderboards through the same rendering logic used for V3.

Usage:
    python src/elo/generate_version_leaderboards.py
"""

import csv
import json
import os
from collections import defaultdict

import pandas as pd

import sys
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _root
from src.config.paths import (  # noqa: E402
    MATCHES_CSV,
    BEYS_DATA_JSON,
    LEADERBOARD_V1_CSV,
    LEADERBOARD_V2_CSV,
    LEADERBOARD_DIR,
)

# Terminal colour helpers
os.system("")
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# ── Constants ──────────────────────────────────────────────────────────────────
START_ELO = 1000
ARENA_FILTER = "Xtreme"

# V1/V2 shared K-factor tiers
K_LEARNING = 40
K_INTERMEDIATE = 24
K_EXPERIENCED = 12


def dynamic_k(n_matches: int) -> float:
    """Tiered K-factor used by V1 and V2."""
    if n_matches < 6:
        return K_LEARNING
    elif n_matches < 15:
        return K_INTERMEDIATE
    return K_EXPERIENCED


def expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


# ── V1 scoring (proportional) ─────────────────────────────────────────────────
def v1_score(sa: int, sb: int):
    """V1: proportional scoring — sa/(sa+sb)."""
    total = sa + sb
    if total == 0:
        return 0.5, 0.5
    return sa / total, sb / total


# ── V2 scoring (dominance-based) ─────────────────────────────────────────────
WIN_THRESHOLD = 4
MAX_POINT_DIFF = 6
OVERKILL_WEIGHT = 0.25
BASE_WIN = 0.75


def v2_score(sa: int, sb: int):
    """V2: dominance-based scoring."""
    if sa == sb:
        return 0.5, 0.5
    winner_score = max(sa, sb)
    loser_score = min(sa, sb)
    diff = winner_score - loser_score

    if diff >= 4:
        dominance = 1.0
    else:
        dominance = diff / 4.0

    score_winner = BASE_WIN + (1.0 - BASE_WIN) * dominance

    if winner_score > WIN_THRESHOLD:
        overkill_points = winner_score - WIN_THRESHOLD
        max_overkill = MAX_POINT_DIFF - WIN_THRESHOLD  # 2
        score_winner += (overkill_points / max_overkill) * OVERKILL_WEIGHT

    score_loser = 1.0 - score_winner

    if sa > sb:
        return score_winner, score_loser
    else:
        return score_loser, score_winner


# ── Match loading ─────────────────────────────────────────────────────────────
def load_xtreme_matches(filepath: str) -> list:
    """Load Xtreme-only matches (including season matches) from matches.csv."""
    matches = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            arena = row.get("arena", ARENA_FILTER)
            match_type = row.get("MatchType", "exhibition")
            # Include matches that update Xtreme ELO:
            # - Matches played in Xtreme arena
            # - Season/relegation/season_cup matches (always update Xtreme ELO)
            is_xtreme = arena == ARENA_FILTER
            is_season_type = match_type in ("season", "relegation", "season_cup")
            if not (is_xtreme or is_season_type):
                continue
            try:
                sa = int(row["ScoreA"])
                sb = int(row["ScoreB"])
            except (ValueError, KeyError):
                continue
            matches.append({
                "date": row.get("Date", ""),
                "bey_a": row["BeyA"],
                "bey_b": row["BeyB"],
                "score_a": sa,
                "score_b": sb,
            })
    matches.sort(key=lambda m: m["date"])
    return matches


# ── ELO simulation ─────────────────────────────────────────────────────────────
def simulate_elo(matches: list, score_fn) -> tuple:
    """
    Simulate ELO for a list of matches using the given scoring function.

    Returns (elos dict, stats dict) after processing all matches.
    """
    elos = defaultdict(lambda: START_ELO)
    stats = defaultdict(lambda: {
        "wins": 0, "losses": 0,
        "for": 0, "against": 0,
        "matches": 0, "winrate": 0.0
    })

    for m in matches:
        a, b = m["bey_a"], m["bey_b"]
        sa, sb = m["score_a"], m["score_b"]

        pre_a, pre_b = elos[a], elos[b]
        exp_a = expected(pre_a, pre_b)

        ka = dynamic_k(stats[a]["matches"])
        kb = dynamic_k(stats[b]["matches"])

        act_a, act_b = score_fn(sa, sb)

        elos[a] = pre_a + ka * (act_a - exp_a)
        elos[b] = pre_b + kb * (act_b - (1.0 - exp_a))

        stats[a]["for"] += sa
        stats[a]["against"] += sb
        stats[b]["for"] += sb
        stats[b]["against"] += sa
        stats[a]["matches"] += 1
        stats[b]["matches"] += 1

        if sa > sb:
            stats[a]["wins"] += 1
            stats[b]["losses"] += 1
        elif sb > sa:
            stats[b]["wins"] += 1
            stats[a]["losses"] += 1

    # Compute winrates
    for s in stats.values():
        s["winrate"] = s["wins"] / s["matches"] if s["matches"] > 0 else 0.0

    return elos, stats


# ── Leaderboard generation ────────────────────────────────────────────────────
def build_leaderboard(elos: dict, stats: dict, all_beys: list) -> list:
    """
    Build a sorted leaderboard rows list from ELO and stats dicts.

    Beys registered in beys_data.json but without match history are
    included at START_ELO so the leaderboard is always complete.
    """
    # Ensure every registered Bey is present
    all_names = set(elos.keys())
    for name in all_beys:
        if name not in all_names:
            all_names.add(name)

    rows = []
    for name in all_names:
        elo = round(elos[name]) if name in elos else START_ELO
        s = stats[name]
        winrate_str = (
            f"{round(s['winrate'] * 100, 1)}%"
            if s["matches"] > 0
            else "0.0%"
        )
        rows.append({
            "Platz": 0,
            "Name": name,
            "ELO": elo,
            "Spiele": s["matches"],
            "Siege": s["wins"],
            "Niederlagen": s["losses"],
            "Winrate": winrate_str,
            "Gewonnene Punkte": s["for"],
            "Verlorene Punkte": s["against"],
            "Differenz": s["for"] - s["against"],
            "Positionsdelta": "→ 0",
            "ELOdelta": "0",
        })

    # Sort by ELO descending
    rows.sort(key=lambda r: r["ELO"], reverse=True)
    for pos, row in enumerate(rows, start=1):
        row["Platz"] = pos

    return rows


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n{CYAN}{'─' * 50}{RESET}")
    print(f"{CYAN}  Historical ELO Version Leaderboards{RESET}")
    print(f"{CYAN}{'─' * 50}{RESET}\n")

    # Load all registered Beys
    all_beys = []
    if os.path.exists(BEYS_DATA_JSON):
        with open(BEYS_DATA_JSON, encoding="utf-8") as fh:
            beys_data = json.load(fh)
        all_beys = [entry["name"] for entry in beys_data if "name" in entry]
        print(f"  Registered Beys loaded : {len(all_beys)}")
    else:
        print(f"{YELLOW}  Warning: beys_data.json not found, proceeding without full Bey list{RESET}")

    print(f"{YELLOW}Loading Xtreme matches from {MATCHES_CSV} …{RESET}")
    matches = load_xtreme_matches(MATCHES_CSV)
    print(f"  Xtreme matches loaded  : {len(matches)}")

    os.makedirs(LEADERBOARD_DIR, exist_ok=True)

    for version, score_fn, output_file in [
        ("V1", v1_score, LEADERBOARD_V1_CSV),
        ("V2", v2_score, LEADERBOARD_V2_CSV),
    ]:
        print(f"\n{YELLOW}Simulating {version} ELO …{RESET}")
        elos, stats = simulate_elo(matches, score_fn)
        rows = build_leaderboard(elos, stats, all_beys)

        pd.DataFrame(rows).to_csv(output_file, index=False)
        print(f"{GREEN}✔  {version} leaderboard written : {output_file}{RESET}")
        print(f"   Beys in leaderboard : {len(rows)}")
        if rows:
            top = rows[0]
            print(f"   Top Bey             : {top['Name']} (ELO {top['ELO']})")

    print()


if __name__ == "__main__":
    main()
