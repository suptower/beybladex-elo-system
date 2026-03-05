"""
Beyblade ELO Rating System
This module implements an ELO rating system for Beyblade matches with dynamic K-factors,
dominance-based scoring, and comprehensive statistics tracking.

The system supports two modes:
- official: Starts all beyblades at the default ELO (1000)
- private: Uses existing ELO ratings from the official leaderboard as starting values

Features:
- Dynamic K-factor based on match experience (learning/intermediate/experienced)
- Dominance-based scoring that rewards dominant victories (Version 2)
- Match-by-match ELO history tracking
- Tournament-based leaderboards with position deltas
- Time series data for ELO progression
- Position tracking over time with passive/active change detection

K-Factor Rules:
- Learning (< 6 matches): K = 40
- Intermediate (6-14 matches): K = 24
- Experienced (15+ matches): K = 12

Dominance-Based Scoring (ELO Version 2):
- Winner gets: base_win_value (0.5) + dominance_bonus (0 to 0.5)
- Dominance bonus scales with point differential (max 6 points)
- Examples:
  - 4-3 win: Winner gets ~0.58 (close match)
  - 4-0 win: Winner gets ~0.83 (dominant)
  - 6-0 win: Winner gets 1.00 (overwhelming)

Functions:
    dynamic_k(matches): Calculate K-factor based on number of matches played
    expected(a, b): Calculate expected score for player A against player B
    calculate_score_with_dominance(sa, sb): Calculate score with dominance scaling
    update_elo(a, b, sa, sb, date, elos, stats, writer): Update ELO ratings after a match
    calculate_winrates(stats): Calculate win rates for all beyblades
    run_elo_pipeline(pipeline_config): Execute the complete ELO calculation pipeline

Output Files:
    - leaderboard.csv: Current tournament standings
    - elo_history.csv: Complete match-by-match ELO changes
    - elo_timeseries.csv: ELO progression per beyblade over matches
    - position_timeseries.csv: Position changes over time
    - leaderboards/leaderboard_N.csv: Per-tournament leaderboards

Usage:
    python beyblade_elo.py --mode official
    python beyblade_elo.py --mode private
"""
import csv
import argparse
import datetime
from collections import defaultdict
import os
import pandas as pd
import json

# Colors for Windows
os.system("")

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

START_ELO = 1000
K_LEARNING = 40
K_INTERMEDIATE = 24
K_EXPERIENCED = 12

# Default path for beyblade registry
DEFAULT_BEYS_DATA_FILE = "../../docs/data/beys/beys_data.json"
# ELO version for calculation changes
ELO_VERSION = 2  # Version 2: Dominance-based scoring

# Dominance calculation constants
WIN_THRESHOLD = 4
MAX_POINT_DIFF = 6
OVERKILL_WEIGHT = 0.25

# Arena constants
ARENA_XTREME = "Xtreme"
ARENA_DROP_ATTACK = "Drop Attack"
ARENA_COMBINED = "Combined"  # Tracks all matches from all arenas
SUPPORTED_ARENAS = [ARENA_XTREME, ARENA_DROP_ATTACK]
ALL_ARENAS = [ARENA_XTREME, ARENA_DROP_ATTACK, ARENA_COMBINED]  # Including combined

# ------------ Arena normalization ------------


def normalize_arena_name(arena):
    """Normalize arena name to canonical form."""
    if not arena:
        return ARENA_XTREME
    # Map common variations to canonical names
    arena_map = {
        "xtreme": ARENA_XTREME,
        "Xtreme": ARENA_XTREME,
        "drop attack": ARENA_DROP_ATTACK,
        "Drop Attack": ARENA_DROP_ATTACK,
        "DropAttack": ARENA_DROP_ATTACK,
        "drop_attack": ARENA_DROP_ATTACK,
        "combined": ARENA_COMBINED,
        "Combined": ARENA_COMBINED,
        "global": ARENA_COMBINED,
        "Global": ARENA_COMBINED
    }
    return arena_map.get(arena, arena)


# ------------ K-factor rules ------------


def dynamic_k(matches):
    if matches < 6:
        return K_LEARNING
    elif matches < 15:
        return K_INTERMEDIATE
    return K_EXPERIENCED

# ------------ Elo expected score ------------


def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))

# ------------ Dominance-based scoring ------------


def calculate_score_with_dominance(sa, sb):
    if sa == sb:
        return 0.5, 0.5

    winner_score = max(sa, sb)
    loser_score = min(sa, sb)
    diff = winner_score - loser_score

    # Base win value (minimum reward for a win)
    BASE_WIN = 0.75

    # Dominance scaling up to 4-0
    if diff >= 4:
        dominance = 1.0
    else:
        dominance = diff / 4.0  # 1 → 0.25, 2 → 0.5, 3 → 0.75

    score_winner = BASE_WIN + (1.0 - BASE_WIN) * dominance

    # Overkill bonus (beyond 4 points)
    if winner_score > WIN_THRESHOLD:
        overkill_points = winner_score - WIN_THRESHOLD
        max_overkill = MAX_POINT_DIFF - WIN_THRESHOLD  # 2
        score_winner += (overkill_points / max_overkill) * OVERKILL_WEIGHT

    score_loser = 1.0 - score_winner

    if sa > sb:
        return score_winner, score_loser
    else:
        return score_loser, score_winner

# ------------- Elo update for ONE MATCH -------------


def update_elo(a, b, sa, sb, date, elos, stats, writer=None, match_id=None, arena=None, match_type=None,
               arena_elos=None, arena_stats=None, season_id=None, tier=None, matchday=None):
    """
    Update ELO ratings for a match.

    Args:
        a, b: Bey names
        sa, sb: Scores
        date: Match date
        elos: Dict of current ELO ratings (global/Xtreme)
        stats: Dict of global stats
        writer: CSV writer for history
        match_id: Match identifier
        arena: Arena name (defaults to Xtreme)
        match_type: Type of match (exhibition, season, etc.)
        arena_elos: Dict of arena-specific ELO ratings (arena -> bey -> elo)
        arena_stats: Dict of arena-specific stats (arena -> bey -> stats)
        season_id: Season identifier (e.g., 'S1')
        tier: Tier number (1-4)
        matchday: Matchday number

    Logic:
        - Season matches: Always update Xtreme ELO only
        - Exhibition matches: Update arena-specific ELO only
    """
    # Normalize arena name
    arena = normalize_arena_name(arena)
    match_type = match_type or 'exhibition'

    # Determine which arena's ELO to update
    # Season matches always use Xtreme ELO regardless of actual arena
    if match_type == 'season' or match_type == 'relegation' or match_type == 'season_cup':
        elo_arena = ARENA_XTREME
    else:
        elo_arena = arena

    # Get the appropriate ELO dict and stats dict
    if arena_elos is not None and elo_arena in arena_elos:
        active_elos = arena_elos[elo_arena]
        active_stats = arena_stats[elo_arena] if arena_stats else stats
    else:
        # Fallback to global (for backward compatibility)
        active_elos = elos
        active_stats = stats

    ra, rb = active_elos[a], active_elos[b]
    ea, eb = expected(ra, rb), expected(rb, ra)

    Ka = dynamic_k(active_stats[a]["matches"])
    Kb = dynamic_k(active_stats[b]["matches"])

    total = sa + sb
    if total == 0:
        return

    # Use dominance-based scoring (ELO Version 2)
    s_a, s_b = calculate_score_with_dominance(sa, sb)

    new_a = ra + Ka * (s_a - ea)
    new_b = rb + Kb * (s_b - eb)
    active_elos[a], active_elos[b] = new_a, new_b

    # Also update global elos if this is Xtreme arena (for backward compatibility)
    if elo_arena == ARENA_XTREME and arena_elos is not None:
        elos[a], elos[b] = new_a, new_b

    # ALWAYS update Combined arena for every match (regardless of which specific arena was used)
    if arena_elos is not None and ARENA_COMBINED in arena_elos and elo_arena != ARENA_COMBINED:
        # Get Combined arena ELOs and stats
        combined_elos = arena_elos[ARENA_COMBINED]
        combined_stats = arena_stats[ARENA_COMBINED] if arena_stats else stats

        # Calculate Combined arena update
        rc_a, rc_b = combined_elos[a], combined_elos[b]
        ec_a, ec_b = expected(rc_a, rc_b), expected(rc_b, rc_a)
        Kc_a = dynamic_k(combined_stats[a]["matches"])
        Kc_b = dynamic_k(combined_stats[b]["matches"])

        new_c_a = rc_a + Kc_a * (s_a - ec_a)
        new_c_b = rc_b + Kc_b * (s_b - ec_b)
        combined_elos[a], combined_elos[b] = new_c_a, new_c_b

        # Update Combined arena stats
        combined_stats[a]["for"] += sa
        combined_stats[a]["against"] += sb
        combined_stats[b]["for"] += sb
        combined_stats[b]["against"] += sa
        combined_stats[a]["matches"] += 1
        combined_stats[b]["matches"] += 1

        if sa > sb:
            combined_stats[a]["wins"] += 1
            combined_stats[b]["losses"] += 1
        else:
            combined_stats[b]["wins"] += 1
            combined_stats[a]["losses"] += 1

    # Write to history file
    if writer is not None:
        writer.writerow([
            match_id, date, a, b, sa, sb,
            round(ra, 2), round(rb, 2), round(new_a, 2), round(new_b, 2),
            arena, elo_arena,  # Add which arena's ELO was updated
            match_type or 'exhibition',
            season_id or '',
            tier or '',
            matchday or ''
        ])

    active_stats[a]["for"] += sa
    active_stats[a]["against"] += sb
    active_stats[b]["for"] += sb
    active_stats[b]["against"] += sa
    active_stats[a]["matches"] += 1
    active_stats[b]["matches"] += 1

    if sa > sb:
        active_stats[a]["wins"] += 1
        active_stats[b]["losses"] += 1
    else:
        active_stats[b]["wins"] += 1
        active_stats[a]["losses"] += 1

# ------------- Calculate winrates -------------


def calculate_winrates(stats):
    for s in stats.values():
        s["winrate"] = s["wins"] / s["matches"] if s["matches"] > 0 else 0.0

# ------------- Generate match-by-match leaderboard snapshots -------------


def generate_match_snapshots(matches_list, input_file, snapshots_dir, pipeline_start_elos, all_bey_blades):
    """
    Generate leaderboard snapshots after each match.

    Args:
        matches_list: List of match dictionaries sorted by date
        input_file: Path to matches.csv (for logging)
        snapshots_dir: Directory to save snapshots
        pipeline_start_elos: Starting ELO values (for private mode)
        all_bey_blades: Set of all registered beys
    """
    print(f"{CYAN}Generating per-match leaderboard snapshots...{RESET}")

    # Create snapshots directory if it doesn't exist
    os.makedirs(snapshots_dir, exist_ok=True)

    # Initialize tracking structures
    snapshot_elos = defaultdict(lambda: START_ELO)
    snapshot_stats = defaultdict(
        lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
    )

    # Load start ratings for private ladder
    if pipeline_start_elos is not None:
        for bey, elo in pipeline_start_elos.items():
            snapshot_elos[bey] = elo

    # Initialize all beys from registry
    for bey_name in all_bey_blades:
        _ = snapshot_elos[bey_name]

    # Track previous positions and ELOs for delta calculations
    prev_positions = {}
    prev_elos = {}

    # Generate initial snapshot (match_index = 0, before any matches)
    sorted_beys = sorted(snapshot_elos.items(), key=lambda x: x[1], reverse=True)
    initial_rows = []
    for pos, (bey, elo) in enumerate(sorted_beys, start=1):
        s = snapshot_stats[bey]
        initial_rows.append({
            "Platz": pos,
            "Name": bey,
            "ELO": round(elo),
            "Spiele": s["matches"],
            "Siege": s["wins"],
            "Niederlagen": s["losses"],
            "Winrate": f"{round(s['winrate'] * 100, 1)}%",
            "Gewonnene Punkte": s["for"],
            "Verlorene Punkte": s["against"],
            "Differenz": s["for"] - s["against"],
            "Positionsdelta": "→ 0",
            "ELOdelta": "0"
        })
        prev_positions[bey] = pos
        prev_elos[bey] = elo

    snapshot_file = os.path.join(snapshots_dir, "leaderboard_0000.csv")
    pd.DataFrame(initial_rows).to_csv(snapshot_file, index=False)

    # Process each match and generate snapshots
    for match_idx, match in enumerate(matches_list, start=1):
        bey_a = match["BeyA"]
        bey_b = match["BeyB"]
        score_a = int(match["ScoreA"])
        score_b = int(match["ScoreB"])

        # Update ELO and stats (without writing to history file)
        update_elo(
            bey_a, bey_b, score_a, score_b,
            match["Date"], snapshot_elos, snapshot_stats,
            writer=None,  # Don't write to history
            match_id=match.get("MatchID", ""),
            arena=match.get("arena", "Xtreme")
        )

        # Calculate winrates
        calculate_winrates(snapshot_stats)

        # Generate leaderboard snapshot
        sorted_beys = sorted(snapshot_elos.items(), key=lambda x: x[1], reverse=True)
        snapshot_rows = []

        for pos, (bey, elo) in enumerate(sorted_beys, start=1):
            s = snapshot_stats[bey]

            # Calculate deltas relative to previous match
            prev_pos = prev_positions.get(bey, pos)
            prev_elo = prev_elos.get(bey, START_ELO)

            pos_delta = prev_pos - pos  # Positive = moved up
            elo_delta = round(elo - prev_elo)

            # Format position delta
            if pos_delta > 0:
                pos_delta_str = f"▲ {pos_delta}"
            elif pos_delta < 0:
                pos_delta_str = f"▼ {abs(pos_delta)}"
            else:
                pos_delta_str = "→ 0"

            # Format ELO delta
            if elo_delta > 0:
                elo_delta_str = f"+{elo_delta}"
            elif elo_delta < 0:
                elo_delta_str = f"{elo_delta}"
            else:
                elo_delta_str = "0"

            snapshot_rows.append({
                "Platz": pos,
                "Name": bey,
                "ELO": round(elo),
                "Spiele": s["matches"],
                "Siege": s["wins"],
                "Niederlagen": s["losses"],
                "Winrate": f"{round(s['winrate'] * 100, 1)}%",
                "Gewonnene Punkte": s["for"],
                "Verlorene Punkte": s["against"],
                "Differenz": s["for"] - s["against"],
                "Positionsdelta": pos_delta_str,
                "ELOdelta": elo_delta_str
            })

            # Update previous values for next iteration
            prev_positions[bey] = pos
            prev_elos[bey] = elo

        # Save snapshot with zero-padded match index
        snapshot_file = os.path.join(snapshots_dir, f"leaderboard_{match_idx:04d}.csv")
        pd.DataFrame(snapshot_rows).to_csv(snapshot_file, index=False)

        # Progress indicator every 50 matches
        progress_interval = 50
        if match_idx % progress_interval == 0:
            print(f"{GREEN}  Generated {match_idx} snapshots...{RESET}")

    print(f"{GREEN}Generated {len(matches_list) + 1} leaderboard snapshots "
          f"(0 to {len(matches_list)}) in {snapshots_dir}{RESET}")


# ----------------- ELO PIPELINE -------------------


def run_elo_pipeline(pipeline_config):
    pipeline_mode = pipeline_config["mode"]
    input_file = pipeline_config["input_file"]
    leaderboard_file = pipeline_config["leaderboard"]
    history_file = pipeline_config["history"]
    timeseries_file = pipeline_config["timeseries"]
    position_file = pipeline_config["positions"]
    pipeline_start_elos = pipeline_config["start_elos"]
    beys_data_path = pipeline_config.get("beys_data_file", DEFAULT_BEYS_DATA_FILE)

    print(f"{BOLD}{CYAN}Running ELO Pipeline — Mode: {pipeline_mode}{RESET}")
    print(f"{YELLOW}Reading matches from {input_file}...{RESET}")

    # Initialize ELO + stats (global - for backward compatibility, represents Xtreme)
    elos = defaultdict(lambda: START_ELO)
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0})

    # Initialize arena-specific ELO + stats
    arena_elos = {}
    arena_stats = {}
    for arena in ALL_ARENAS:  # Changed from SUPPORTED_ARENAS to ALL_ARENAS to include Combined
        arena_elos[arena] = defaultdict(lambda: START_ELO)
        arena_stats[arena] = defaultdict(
            lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
        )

    # Load all beys from beys_data.json to include beys without matches
    all_bey_blades = set()
    if os.path.exists(beys_data_path):
        print(f"{CYAN}Loading all beys from {beys_data_path}...{RESET}")
        try:
            with open(beys_data_path, "r", encoding="utf-8") as f:
                beys_data = json.load(f)
                for bey in beys_data:
                    blade_name = bey.get("blade")
                    if blade_name:
                        all_bey_blades.add(blade_name)
                        # Initialize in elos dict by accessing it (triggers defaultdict)
                        _ = elos[blade_name]
                        # Initialize in all arena dicts (including Combined)
                        for arena in ALL_ARENAS:
                            _ = arena_elos[arena][blade_name]
            print(f"{GREEN}Loaded {len(all_bey_blades)} beys from registry{RESET}")
        except FileNotFoundError:
            print(f"{YELLOW}Warning: beys_data.json not found at {beys_data_path}{RESET}")
        except json.JSONDecodeError as e:
            print(f"{YELLOW}Warning: Invalid JSON in beys_data.json: {e}{RESET}")
        except Exception as e:
            print(f"{YELLOW}Warning: Could not load beys_data.json: {e}{RESET}")

    # Load start ratings for private ladder
    if pipeline_start_elos is not None:
        print(f"{CYAN}Loading starting ELOs from official leaderboard...{RESET}")
        for bey, elo in pipeline_start_elos.items():
            elos[bey] = elo
            # Copy starting ELOs to all arenas
            for arena in ALL_ARENAS:  # Changed from SUPPORTED_ARENAS to ALL_ARENAS to include Combined
                arena_elos[arena][bey] = elo

    # --- Full history CSV ---
    with open(input_file, newline="", encoding="utf-8") as f_in, \
            open(history_file, "w", newline="", encoding="utf-8") as f_hist:

        reader = csv.DictReader(f_in)
        writer = csv.writer(f_hist)
        writer.writerow([
            "MatchID", "Date", "BeyA", "BeyB", "ScoreA", "ScoreB",
            "PreA", "PreB", "PostA", "PostB", "arena", "elo_arena_updated",
            "MatchType", "SeasonID", "Tier", "Matchday"
        ])

        matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))

        # Generate match-by-match snapshots
        snapshots_dir = pipeline_config.get("snapshots_dir", "./docs/data/leaderboard_snapshots")
        generate_match_snapshots(matches, input_file, snapshots_dir, pipeline_start_elos, all_bey_blades)

        # Identify tournament dates for tracking state at second-to-last date
        if matches:
            tournament_dates = sorted(set(m["Date"] for m in matches))
            second_to_last_date = tournament_dates[-2] if len(tournament_dates) >= 2 else None
        else:
            second_to_last_date = None

        # Track previous tournament state for delta calculations
        prev_tournament_arena_elos = {}
        prev_tournament_arena_positions = {}

        for idx, m in enumerate(matches):
            current_date = m["Date"]

            update_elo(
                m["BeyA"], m["BeyB"],
                int(m["ScoreA"]), int(m["ScoreB"]),
                current_date, elos, stats, writer,
                m.get("MatchID", ""),
                m.get("arena", "Xtreme"),
                m.get("MatchType", "exhibition"),
                arena_elos,
                arena_stats,
                m.get("SeasonID", ""),
                m.get("Tier", ""),
                m.get("Matchday", "")
            )

            # Check if we just finished processing all matches from the second-to-last tournament date
            if second_to_last_date and current_date == second_to_last_date:
                # Check if next match is from a different date (or this is the last match)
                is_last_match_of_date = (
                    idx == len(matches) - 1 or
                    matches[idx + 1]["Date"] != second_to_last_date
                )

                if is_last_match_of_date:
                    # Save arena states for delta calculation
                    for arena in ALL_ARENAS:
                        prev_tournament_arena_elos[arena] = dict(arena_elos[arena])
                        # Calculate positions at this point
                        arena_sorted = sorted(arena_elos[arena].items(), key=lambda x: x[1], reverse=True)
                        prev_tournament_arena_positions[arena] = {
                            bey: pos for pos, (bey, _) in enumerate(arena_sorted, start=1)
                        }

        # Calculate winrates for global and all arenas
        calculate_winrates(stats)
        for arena in ALL_ARENAS:  # Changed from SUPPORTED_ARENAS to ALL_ARENAS to include Combined
            calculate_winrates(arena_stats[arena])

    # --- Turnier-basierte Leaderboards mit Positionsdelta ---
    print(f"{CYAN}Computing tournament deltas and saving per-turnier CSVs...{RESET}")

    matches_df = pd.read_csv(input_file, parse_dates=["Date"])

    # Initialize tour_rows for case where there are no matches
    tour_rows = []

    if len(matches_df) > 0:
        tournament_dates = matches_df["Date"].drop_duplicates().sort_values().tolist()

        # Ausgangswerte für Turnier 1
        prev_positions = {}
        prev_elos = pipeline_start_elos.copy() if pipeline_start_elos else {}
        prev_stats = defaultdict(
            lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
        )

        for t_idx, t_date in enumerate(tournament_dates, start=1):
            tour_matches = matches_df[matches_df["Date"] == t_date].sort_values(["Date"])

            # Stats und Elos für dieses Turnier initialisieren mit Werten vom vorherigen Turnier
            temp_elos = defaultdict(lambda: START_ELO)
            temp_stats = defaultdict(
                lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
            )

            # Übernehmen der ELOs & Stats vom vorherigen Turnier
            for bey, elo in prev_elos.items():
                temp_elos[bey] = elo
            for bey, s in prev_stats.items():
                temp_stats[bey] = s.copy()  # deepcopy, damit Änderungen temp_stats nicht prev_stats beeinflussen

            # Matches für dieses Turnier durchlaufen
            for _, m in tour_matches.iterrows():
                update_elo(
                    m["BeyA"], m["BeyB"],
                    int(m["ScoreA"]), int(m["ScoreB"]),
                    m["Date"], temp_elos, temp_stats,
                    match_id=m.get("MatchID", ""),
                    arena=m.get("arena", "Xtreme")
                )

            calculate_winrates(temp_stats)

            # Sortiere nach ELO absteigend und erstelle Leaderboard
            sorted_beys = sorted(temp_elos.items(), key=lambda x: x[1], reverse=True)
            tour_rows = []

            for pos, (bey, elo) in enumerate(sorted_beys, start=1):
                s = temp_stats[bey]
                delta = prev_positions.get(bey, pos) - pos if prev_positions else 0
                prev_positions[bey] = pos
                prev_elo = prev_elos.get(bey, START_ELO) if prev_elos else START_ELO
                elo_delta = round(elo - prev_elo)

                if elo_delta > 0:
                    elo_delta_str = f"+{elo_delta}"
                elif elo_delta < 0:
                    elo_delta_str = f"{elo_delta}"  # Minus schon drin
                else:
                    elo_delta_str = "0"

                if delta > 0:
                    delta_str = f"▲ {delta}"
                elif delta < 0:
                    delta_str = f"▼ {abs(delta)}"
                else:
                    delta_str = "→ 0"

                tour_rows.append({
                    "Platz": pos,
                    "Name": bey,
                    "ELO": round(elo),
                    "Spiele": s["matches"],
                    "Siege": s["wins"],
                    "Niederlagen": s["losses"],
                    # convert to percentage string with 1 decimal
                    "Winrate": f"{round(s['winrate'] * 100, 1)}%",
                    "Gewonnene Punkte": s["for"],
                    "Verlorene Punkte": s["against"],
                    "Differenz": s["for"] - s["against"],
                    "Positionsdelta": delta_str,
                    "ELOdelta": elo_delta_str
                })

            out_file = f"./docs/data/leaderboard/leaderboard_{t_idx}.csv"
            pd.DataFrame(tour_rows).to_csv(out_file, index=False)

            # Update für nächstes Turnier
            prev_elos = temp_elos.copy()
            prev_stats = temp_stats.copy()

    # --- Aktuelles Turnier zusätzlich als leaderboard.csv ---
    # Use tour_rows from the last tournament iteration (which has correct deltas)
    # but correct the ELO values to match the sequential calculation (elos dict)
    # to ensure consistency with elo_history.csv and advanced_leaderboard.csv

    # Create a mapping of bey names to their correct ELO from sequential calculation
    correct_elos = {bey: round(elo) for bey, elo in elos.items()}

    # Add all beys from beys_data.json that don't have match history yet
    # Use Xtreme arena stats for the main leaderboard
    for bey_name in all_bey_blades:
        if bey_name not in [row["Name"] for row in tour_rows]:
            xtreme_stats = arena_stats[ARENA_XTREME][bey_name]
            tour_rows.append({
                "Platz": 0,  # Will be updated after sorting
                "Name": bey_name,
                "ELO": correct_elos.get(bey_name, START_ELO),
                "Spiele": xtreme_stats["matches"],
                "Siege": xtreme_stats["wins"],
                "Niederlagen": xtreme_stats["losses"],
                "Winrate": "0.0%",
                "Gewonnene Punkte": xtreme_stats["for"],
                "Verlorene Punkte": xtreme_stats["against"],
                "Differenz": xtreme_stats["for"] - xtreme_stats["against"],
                "Positionsdelta": "→ 0",
                "ELOdelta": "0"
            })

    # Update tour_rows with correct ELO values and Xtreme stats while preserving delta calculations
    for row in tour_rows:
        bey_name = row["Name"]
        if bey_name in correct_elos:
            row["ELO"] = correct_elos[bey_name]
        # Update stats to use Xtreme-only
        xtreme_stats = arena_stats[ARENA_XTREME][bey_name]
        row["Spiele"] = xtreme_stats["matches"]
        row["Siege"] = xtreme_stats["wins"]
        row["Niederlagen"] = xtreme_stats["losses"]
        row["Winrate"] = f"{round(xtreme_stats['winrate'] * 100, 1)}%" if xtreme_stats["matches"] > 0 else "0.0%"
        row["Gewonnene Punkte"] = xtreme_stats["for"]
        row["Verlorene Punkte"] = xtreme_stats["against"]
        row["Differenz"] = xtreme_stats["for"] - xtreme_stats["against"]

    # Resort by corrected ELO to ensure proper ranking
    tour_rows_sorted = sorted(tour_rows, key=lambda x: x["ELO"], reverse=True)

    # Update Platz (rank) based on new ELO order
    for pos, row in enumerate(tour_rows_sorted, start=1):
        row["Platz"] = pos

    # Copy tour_rows but only with names
    tour_rows_names_only = [{"Name": row["Name"]} for row in tour_rows_sorted]

    tour_rows_df = pd.DataFrame(tour_rows_sorted)
    tour_rows_df.to_csv(leaderboard_file, index=False)

    # Write names-only-leaderboard to docs/data/beys/beys.csv for easy access but remove header line
    pd.DataFrame(tour_rows_names_only).to_csv("./docs/data/beys/beys.csv", index=False, header=False)

    # matches_with_rounds.json is already in docs/data from merge_rounds.py
    # No need to copy from ./data anymore
    rounds_json_path = "./docs/data/matches/matches_with_rounds.json"
    if not os.path.exists(rounds_json_path):
        print(f"{YELLOW}Warning: Round data file not found at {rounds_json_path}{RESET}")

    print(f"{GREEN}Aktuelles Leaderboard geschrieben: {leaderboard_file}{RESET}")

    # --- Generate Arena-Specific Leaderboards ---
    print(f"{CYAN}Generating arena-specific leaderboards...{RESET}")
    for arena in ALL_ARENAS:  # Changed from SUPPORTED_ARENAS to ALL_ARENAS to include Combined
        arena_file_name = arena.lower().replace(" ", "_")
        arena_leaderboard_file = f"./docs/data/leaderboard_{arena_file_name}.csv"

        # Sort by arena-specific ELO
        arena_sorted_beys = sorted(arena_elos[arena].items(), key=lambda x: x[1], reverse=True)
        arena_rows = []

        for pos, (bey, arena_elo) in enumerate(arena_sorted_beys, start=1):
            s = arena_stats[arena][bey]

            # Calculate deltas relative to second-to-last tournament date
            prev_pos = prev_tournament_arena_positions.get(arena, {}).get(bey, pos)
            prev_elo = prev_tournament_arena_elos.get(arena, {}).get(bey, START_ELO)

            pos_delta = prev_pos - pos  # Positive = moved up
            elo_delta = round(arena_elo - prev_elo)

            # Format position delta
            if pos_delta > 0:
                pos_delta_str = f"▲ {pos_delta}"
            elif pos_delta < 0:
                pos_delta_str = f"▼ {abs(pos_delta)}"
            else:
                pos_delta_str = "→ 0"

            # Format ELO delta
            if elo_delta > 0:
                elo_delta_str = f"+{elo_delta}"
            elif elo_delta < 0:
                elo_delta_str = f"{elo_delta}"
            else:
                elo_delta_str = "0"

            arena_rows.append({
                "Platz": pos,
                "Name": bey,
                "ELO": round(arena_elo),
                "Spiele": s["matches"],
                "Siege": s["wins"],
                "Niederlagen": s["losses"],
                "Winrate": f"{round(s['winrate'] * 100, 1)}%" if s["matches"] > 0 else "0.0%",
                "Gewonnene Punkte": s["for"],
                "Verlorene Punkte": s["against"],
                "Differenz": s["for"] - s["against"],
                "Positionsdelta": pos_delta_str,
                "ELOdelta": elo_delta_str
            })

        pd.DataFrame(arena_rows).to_csv(arena_leaderboard_file, index=False)
        print(f"{GREEN}  {arena} leaderboard written: {arena_leaderboard_file}{RESET}")

    # --- Generate Combined Leaderboard with All Arena ELOs ---
    print(f"{CYAN}Generating combined leaderboard with all arena ELOs...{RESET}")
    combined_leaderboard_file = "./docs/data/leaderboard/leaderboard_all_arenas.csv"

    # Use Xtreme ELO for primary sorting (global/season ELO)
    xtreme_sorted_beys = sorted(arena_elos[ARENA_XTREME].items(), key=lambda x: x[1], reverse=True)
    combined_rows = []

    for pos, (bey, xtreme_elo) in enumerate(xtreme_sorted_beys, start=1):
        row = {
            "Platz": pos,
            "Name": bey,
            "ELO_Global": round(xtreme_elo),  # Xtreme is the global/season ELO
        }

        # Add per-arena ELOs and stats
        for arena in SUPPORTED_ARENAS:
            arena_col_name = arena.replace(" ", "")
            s = arena_stats[arena][bey]
            row[f"ELO_{arena_col_name}"] = round(arena_elos[arena][bey])
            row[f"Matches_{arena_col_name}"] = s["matches"]
            row[f"Wins_{arena_col_name}"] = s["wins"]
            row[f"Winrate_{arena_col_name}"] = f"{round(s['winrate'] * 100, 1)}%" if s["matches"] > 0 else "0.0%"

        combined_rows.append(row)

    pd.DataFrame(combined_rows).to_csv(combined_leaderboard_file, index=False)
    print(f"{GREEN}Combined arena leaderboard written: {combined_leaderboard_file}{RESET}")

    # --- Time series (default - uses Xtreme only for backward compatibility) ---
    print(f"{CYAN}Generating ELO timeseries...{RESET}")
    df_hist = pd.read_csv(history_file, parse_dates=["Date"]).reset_index(drop=True)

    # Filter to only Xtreme arena updates for default timeseries
    df_hist_xtreme = df_hist[df_hist["elo_arena_updated"] == ARENA_XTREME].copy()
    df_hist_xtreme["match_id"] = df_hist_xtreme.index + 1

    df_a = pd.DataFrame({"Date": df_hist_xtreme["Date"], "Bey": df_hist_xtreme["BeyA"], "ELO": pd.to_numeric(
        df_hist_xtreme["PostA"], errors="coerce"), "match_id": df_hist_xtreme["match_id"]})
    df_b = pd.DataFrame({"Date": df_hist_xtreme["Date"], "Bey": df_hist_xtreme["BeyB"], "ELO": pd.to_numeric(
        df_hist_xtreme["PostB"], errors="coerce"), "match_id": df_hist_xtreme["match_id"]})
    stacked = pd.concat([df_a, df_b], ignore_index=True).sort_values(["Bey", "match_id"]).reset_index(drop=True)
    stacked["MatchIndex"] = stacked.groupby("Bey").cumcount() + 1

    initial_entries = []
    for bey in stacked["Bey"].unique():
        earliest_date = stacked[stacked["Bey"] == bey]["Date"].min()
        initial_entries.append({"Date": earliest_date, "Bey": bey, "ELO": pipeline_start_elos.get(
            bey, START_ELO) if pipeline_start_elos else START_ELO, "match_id": 0, "MatchIndex": 0})

    stacked = pd.concat([pd.DataFrame(initial_entries), stacked], ignore_index=True)
    stacked = stacked.sort_values(["Bey", "MatchIndex"])
    stacked.to_csv(timeseries_file, index=False, encoding="utf-8")
    print(f"{GREEN}  Xtreme timeseries saved: {timeseries_file}{RESET}")

    # --- Generate arena-specific timeseries ---
    for arena in ALL_ARENAS:  # Changed from SUPPORTED_ARENAS to ALL_ARENAS to include Combined
        arena_file_name = arena.lower().replace(" ", "_")
        arena_timeseries_file = f"./docs/data/elo_timeseries_{arena_file_name}.csv"

        # For Combined arena, include ALL matches; for specific arenas, filter by arena
        if arena == ARENA_COMBINED:
            # Combined includes all matches regardless of which arena's ELO was updated
            df_hist_arena = df_hist.copy()
        else:
            # Filter to only this arena's updates
            df_hist_arena = df_hist[df_hist["elo_arena_updated"] == arena].copy()

        df_hist_arena["match_id"] = df_hist_arena.index + 1

        df_a_arena = pd.DataFrame({"Date": df_hist_arena["Date"], "Bey": df_hist_arena["BeyA"], "ELO": pd.to_numeric(
            df_hist_arena["PostA"], errors="coerce"), "match_id": df_hist_arena["match_id"]})
        df_b_arena = pd.DataFrame({
            "Date": df_hist_arena["Date"],
            "Bey": df_hist_arena["BeyB"],
            "ELO": pd.to_numeric(df_hist_arena["PostB"], errors="coerce"),
            "match_id": df_hist_arena["match_id"]
        })
        stacked_arena = pd.concat(
            [df_a_arena, df_b_arena], ignore_index=True
        ).sort_values(["Bey", "match_id"]).reset_index(drop=True)
        stacked_arena["MatchIndex"] = stacked_arena.groupby("Bey").cumcount() + 1

        initial_entries_arena = []
        for bey in stacked_arena["Bey"].unique():
            earliest_date = stacked_arena[stacked_arena["Bey"] == bey]["Date"].min()
            initial_entries_arena.append({"Date": earliest_date, "Bey": bey, "ELO": pipeline_start_elos.get(
                bey, START_ELO) if pipeline_start_elos else START_ELO, "match_id": 0, "MatchIndex": 0})

        stacked_arena = pd.concat([pd.DataFrame(initial_entries_arena), stacked_arena], ignore_index=True)
        stacked_arena = stacked_arena.sort_values(["Bey", "MatchIndex"])
        stacked_arena.to_csv(arena_timeseries_file, index=False, encoding="utf-8")
        print(f"{GREEN}  {arena} timeseries saved: {arena_timeseries_file}{RESET}")

    print(f"{GREEN}All timeseries files generated{RESET}")

    # --- Position Time Series ---
    print(f"{CYAN}Generating position time series...{RESET}")

    # Read the history to track positions after each match
    df_hist_full = pd.read_csv(history_file, parse_dates=["Date"])

    # Generate position timeseries for each arena
    for arena_idx, arena in enumerate(
        [ARENA_XTREME] + [a for a in SUPPORTED_ARENAS if a != ARENA_XTREME]
    ):
        arena_file_name = arena.lower().replace(" ", "_")
        arena_position_file = (
            position_file if arena == ARENA_XTREME
            else f"./docs/data/position_timeseries_{arena_file_name}.csv"
        )

        # Filter to only this arena's updates
        df_hist_arena = df_hist_full[df_hist_full["elo_arena_updated"] == arena].copy()

        if len(df_hist_arena) == 0:
            # No matches for this arena, create empty file
            empty_columns = [
                "Event", "MatchIndex", "Played", "PassiveChange", "Date",
                "Bey", "ELO", "Position", "Spiele", "Siege", "Niederlagen", "Winrate"
            ]
            pd.DataFrame(columns=empty_columns).to_csv(
                arena_position_file, index=False, encoding="utf-8"
            )
            print(f"{YELLOW}  {arena} position timeseries: No matches, empty file created{RESET}")
            continue

        # Initialize tracking structures
        current_elos = defaultdict(lambda: START_ELO)
        current_stats = defaultdict(lambda: {
            "wins": 0, "losses": 0, "for": 0, "against": 0,
            "matches": 0, "winrate": 0.0
        })

        # Load start ratings for private ladder
        if pipeline_start_elos is not None:
            for bey, elo in pipeline_start_elos.items():
                current_elos[bey] = elo

        # Calculate initial positions (before any matches)
        sorted_beys = sorted(current_elos.items(), key=lambda x: x[1], reverse=True)
        previous_positions = {bey: pos for pos, (bey, elo) in enumerate(sorted_beys, start=1)}

        position_rows = []
        match_counters = defaultdict(int)

        # Process each match in chronological order
        for match_idx, match in df_hist_arena.iterrows():
            date = match["Date"]
            bey_a = match["BeyA"]
            bey_b = match["BeyB"]

            # Update ELOs from match
            current_elos[bey_a] = match["PostA"]
            current_elos[bey_b] = match["PostB"]

            # Update stats
            score_a = match["ScoreA"]
            score_b = match["ScoreB"]

            for bey, score_self, score_opp in [(bey_a, score_a, score_b), (bey_b, score_b, score_a)]:
                current_stats[bey]["matches"] += 1
                current_stats[bey]["for"] += score_self
                current_stats[bey]["against"] += score_opp
                if score_self > score_opp:
                    current_stats[bey]["wins"] += 1
                else:
                    current_stats[bey]["losses"] += 1
                if current_stats[bey]["matches"] > 0:
                    current_stats[bey]["winrate"] = current_stats[bey]["wins"] / current_stats[bey]["matches"]

            # Calculate current leaderboard positions for ALL beys
            sorted_beys = sorted(current_elos.items(), key=lambda x: x[1], reverse=True)
            current_positions = {bey: pos for pos, (bey, elo) in enumerate(sorted_beys, start=1)}

            affected_beys = set()
            affected_beys.add(bey_a)
            affected_beys.add(bey_b)

            # Only record positions for beys that actually played in this match
            # This ensures each entry corresponds to when the bey played, avoiding oscillations
            for bey in current_positions.keys():
                if bey not in (bey_a, bey_b):
                    old_pos = previous_positions.get(bey)
                    new_pos = current_positions[bey]
                    if old_pos != new_pos:
                        affected_beys.add(bey)

            for bey in affected_beys:
                old_pos = previous_positions.get(bey)
                new_pos = current_positions[bey]

                # passive oder aktive Änderung?
                pos_changed = old_pos != new_pos

                # Wir erstellen EINEN Eintrag pro Match für jeden Bey,
                # aber markieren, ob er aktiv gespielt hat:
                played = (bey == bey_a) or (bey == bey_b)

                s = current_stats[bey]
                elo = current_elos[bey]

                # MatchIndex: nur erhöhen wenn aktiver Spieler
                if played:
                    match_counters[bey] += 1

                position_rows.append({
                    "Event": match_idx + 1,
                    "MatchIndex": match_counters[bey],
                    "Played": int(played),
                    "PassiveChange": int(pos_changed and not played),
                    "Date": date,
                    "Bey": bey,
                    "ELO": round(elo),
                    "Position": new_pos,
                    "Spiele": s["matches"],
                    "Siege": s["wins"],
                    "Niederlagen": s["losses"],
                    "Winrate": s["winrate"]
                })

            # Update previous positions for next iteration
            previous_positions = current_positions.copy()

        # Save position timeseries
        position_df = pd.DataFrame(position_rows)
        position_df.to_csv(arena_position_file, index=False, encoding="utf-8")
        print(f"{GREEN}  {arena} position timeseries saved: {arena_position_file}{RESET}")

    print(f"{GREEN}All position timeseries files generated{RESET}")


# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()

    mode = args.mode

    if mode == "official":
        config = {
            "mode": "official",
            "input_file": "../../docs/data/matches/matches.csv",
            "leaderboard": "../../docs/data/leaderboard/leaderboard.csv",
            "history": "../../docs/data/elo/elo_history.csv",
            "timeseries": "../../docs/data/elo/elo_timeseries.csv",
            "positions": "../../docs/data/analytics/position_timeseries.csv",
            "start_elos": None
        }
    else:
        df = pd.read_csv("../../docs/data/leaderboard/leaderboard.csv")
        start_elos = dict(zip(df["Name"], df["ELO"]))
        config = {
            "mode": "private",
            "input_file": "../../docs/data/matches/private_matches.csv",
            "leaderboard": "../../docs/data/leaderboard/private_leaderboard.csv",
            "history": "../../docs/data/elo/private_elo_history.csv",
            "timeseries": "../../docs/data/elo/private_elo_timeseries.csv",
            "positions": "../../docs/data/private_position_timeseries.csv",
            "start_elos": start_elos
        }

    run_elo_pipeline(config)
