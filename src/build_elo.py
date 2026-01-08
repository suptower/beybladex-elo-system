"""
Build-Aware ELO Calculator Extension

This module extends beyblade_elo.py to support build-level ELO tracking while
maintaining 100% backward compatibility with stock-only workflows.

Key features:
- Reads BuildA/BuildB columns from matches.csv (optional)
- Falls back to stock builds if columns are empty
- Tracks ELO at both build and blade levels
- Hierarchical aggregation (Build → Blade)
- Blade-anchored ELO with build divergence

Usage:
    from build_elo import run_build_elo_pipeline
    
    config = {
        "mode": "official",
        "input_file": "./docs/data/matches.csv",
        "leaderboard": "./docs/data/leaderboard.csv",
        ...
    }
    run_build_elo_pipeline(config)
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
import pandas as pd

from src.build_manager import BuildManager
from src.beyblade_elo import (
    START_ELO, dynamic_k, expected, calculate_score_with_dominance,
    calculate_winrates, BOLD, CYAN, GREEN, YELLOW, RESET
)

# Add RED if not available in beyblade_elo
RED = "\033[31m"

# Build initialization offset
BUILD_START_OFFSET = 25  # Custom builds start 25 ELO below their blade


def aggregate_blade_elo(build_manager: BuildManager, build_elos: dict) -> dict:
    """
    Aggregate build ELOs to blade level using weighted average.
    
    Args:
        build_manager: BuildManager instance with build registry
        build_elos: Dict mapping build_id -> current ELO
        
    Returns:
        Dict mapping blade -> aggregated ELO
    """
    blade_elos = {}
    blade_data = defaultdict(lambda: {"weighted_sum": 0.0, "total_weight": 0.0})
    
    for build_id, elo in build_elos.items():
        build = build_manager.get_build(build_id)
        if not build:
            continue
        
        # Weight by sqrt(match_count) to balance experience
        weight = max(1.0, build.match_count ** 0.5)
        
        blade_data[build.blade]["weighted_sum"] += elo * weight
        blade_data[build.blade]["total_weight"] += weight
    
    # Calculate weighted averages
    for blade, data in blade_data.items():
        if data["total_weight"] > 0:
            blade_elos[blade] = data["weighted_sum"] / data["total_weight"]
        else:
            blade_elos[blade] = START_ELO
    
    return blade_elos


def update_build_elo(build_a_id, build_b_id, sa, sb, date, 
                     build_elos, build_stats, build_manager, writer=None, match_id=None):
    """
    Update ELO for builds after a match.
    Similar to beyblade_elo.update_elo but works at build level.
    
    Args:
        build_a_id: Build ID for player A
        build_b_id: Build ID for player B
        sa, sb: Scores for A and B
        date: Match date
        build_elos: Dict of build ELOs
        build_stats: Dict of build statistics
        build_manager: BuildManager instance
        writer: CSV writer for history (optional)
        match_id: Match identifier (optional)
    """
    ra, rb = build_elos[build_a_id], build_elos[build_b_id]
    ea, eb = expected(ra, rb), expected(rb, ra)
    
    Ka = dynamic_k(build_stats[build_a_id]["matches"])
    Kb = dynamic_k(build_stats[build_b_id]["matches"])
    
    total = sa + sb
    if total == 0:
        return
    
    # Use dominance-based scoring (same as Version 2)
    s_a, s_b = calculate_score_with_dominance(sa, sb)
    
    new_a = ra + Ka * (s_a - ea)
    new_b = rb + Kb * (s_b - eb)
    
    elo_change_a = new_a - ra
    elo_change_b = new_b - rb
    
    build_elos[build_a_id], build_elos[build_b_id] = new_a, new_b
    
    # Update build usage in manager
    build_manager.update_build_usage(build_a_id, date, elo_change_a)
    build_manager.update_build_usage(build_b_id, date, elo_change_b)
    
    # Write history if writer provided
    if writer is not None:
        writer.writerow([
            match_id, date, 
            build_a_id, build_b_id, 
            sa, sb, 
            round(ra, 2), round(rb, 2), 
            round(new_a, 2), round(new_b, 2)
        ])
    
    # Update stats
    build_stats[build_a_id]["for"] += sa
    build_stats[build_a_id]["against"] += sb
    build_stats[build_b_id]["for"] += sb
    build_stats[build_b_id]["against"] += sa
    build_stats[build_a_id]["matches"] += 1
    build_stats[build_b_id]["matches"] += 1
    
    if sa > sb:
        build_stats[build_a_id]["wins"] += 1
        build_stats[build_b_id]["losses"] += 1
    else:
        build_stats[build_b_id]["wins"] += 1
        build_stats[build_a_id]["losses"] += 1


def run_build_elo_pipeline(pipeline_config):
    """
    Run ELO pipeline with build support.
    
    Extends standard ELO pipeline to:
    1. Read BuildA/BuildB columns from matches.csv
    2. Resolve builds (or fall back to stock)
    3. Track ELO at build level
    4. Aggregate to blade level
    5. Generate build-aware leaderboards
    
    Args:
        pipeline_config: Configuration dict with keys:
            - mode: "official" or "private"
            - input_file: Path to matches.csv
            - leaderboard: Output leaderboard path
            - history: Output history path
            - build_leaderboard: Output for build-level leaderboard (new)
            - start_elos: Starting ELOs for private mode (optional)
            - beys_data_file: Path to beys_data.json (optional)
    """
    pipeline_mode = pipeline_config["mode"]
    input_file = pipeline_config["input_file"]
    leaderboard_file = pipeline_config["leaderboard"]
    history_file = pipeline_config["history"]
    build_leaderboard_file = pipeline_config.get("build_leaderboard", 
                                                  "./docs/data/build_leaderboard.csv")
    pipeline_start_elos = pipeline_config.get("start_elos")
    
    print(f"{BOLD}{CYAN}Running Build-Aware ELO Pipeline — Mode: {pipeline_mode}{RESET}")
    print(f"{YELLOW}Reading matches from {input_file}...{RESET}")
    
    # Initialize build manager
    build_manager = BuildManager()
    build_manager.load_builds()
    
    if len(build_manager.builds) == 0:
        print(f"{YELLOW}No builds found, initializing from stock beys...{RESET}")
        build_manager.initialize_from_stock_beys()
        build_manager.save_builds()
    
    # Initialize ELO and stats at build level
    build_elos = defaultdict(lambda: START_ELO)
    build_stats = defaultdict(
        lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0, "winrate": 0.0}
    )
    
    # Initialize stock builds with starting ELOs if provided (private mode)
    if pipeline_start_elos is not None:
        print(f"{CYAN}Initializing build ELOs from blade starting values...{RESET}")
        for blade, elo in pipeline_start_elos.items():
            stock_build_id = build_manager.get_stock_build(blade)
            if stock_build_id:
                build_elos[stock_build_id] = elo
    
    # Process matches
    with open(input_file, newline="", encoding="utf-8") as f_in, \
         open(history_file, "w", newline="", encoding="utf-8") as f_hist:
        
        reader = csv.DictReader(f_in)
        writer = csv.writer(f_hist)
        writer.writerow([
            "MatchID", "Date", "BuildA", "BuildB", "ScoreA", "ScoreB", 
            "PreA", "PreB", "PostA", "PostB"
        ])
        
        matches = sorted(reader, key=lambda m: m["Date"])
        
        for m in matches:
            blade_a = m["BeyA"]
            blade_b = m["BeyB"]
            
            # Resolve builds (with fallback to stock)
            try:
                build_a_id = build_manager.resolve_build_from_match(
                    blade_a, m.get("BuildA", "").strip()
                )
                build_b_id = build_manager.resolve_build_from_match(
                    blade_b, m.get("BuildB", "").strip()
                )
            except ValueError as e:
                print(f"{RED}Error resolving builds for match {m.get('MatchID', '?')}: {e}{RESET}")
                continue
            
            # Initialize custom builds near their blade's current ELO
            for build_id in [build_a_id, build_b_id]:
                if build_id not in build_elos:
                    build = build_manager.get_build(build_id)
                    if build and not build.is_stock:
                        # Find current blade ELO
                        blade_elos = aggregate_blade_elo(build_manager, build_elos)
                        blade_elo = blade_elos.get(build.blade, START_ELO)
                        build_elos[build_id] = blade_elo - BUILD_START_OFFSET
            
            # Update build ELO
            update_build_elo(
                build_a_id, build_b_id,
                int(m["ScoreA"]), int(m["ScoreB"]),
                m["Date"], build_elos, build_stats, build_manager,
                writer, m.get("MatchID", "")
            )
        
        calculate_winrates(build_stats)
    
    # Save updated builds
    build_manager.save_builds()
    
    # Generate leaderboards
    print(f"{CYAN}Generating leaderboards...{RESET}")
    
    # 1. Build-level leaderboard
    build_rows = []
    for build_id, stat in build_stats.items():
        build = build_manager.get_build(build_id)
        if not build:
            continue
        
        build_rows.append({
            "Rank": 0,  # Will be set after sorting
            "BuildID": build_id,
            "Blade": build.blade,
            "Ratchet": build.ratchet,
            "Bit": build.bit,
            "IsStock": build.is_stock,
            "Status": build.status,
            "Elo": round(build_elos[build_id], 2),
            "Wins": stat["wins"],
            "Losses": stat["losses"],
            "WinRate": round(stat["winrate"], 3),
            "For": stat["for"],
            "Against": stat["against"],
            "Matches": stat["matches"]
        })
    
    # Sort by ELO
    build_rows.sort(key=lambda x: x["Elo"], reverse=True)
    for idx, row in enumerate(build_rows, 1):
        row["Rank"] = idx
    
    # Save build leaderboard
    if build_rows:
        df_builds = pd.DataFrame(build_rows)
        df_builds.to_csv(build_leaderboard_file, index=False)
        print(f"{GREEN}Saved build leaderboard to {build_leaderboard_file}{RESET}")
    
    # 2. Blade-level leaderboard (aggregated)
    blade_elos = aggregate_blade_elo(build_manager, build_elos)
    
    # Aggregate stats to blade level
    blade_stats = defaultdict(
        lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0}
    )
    
    for build_id, stat in build_stats.items():
        build = build_manager.get_build(build_id)
        if not build:
            continue
        
        blade = build.blade
        blade_stats[blade]["wins"] += stat["wins"]
        blade_stats[blade]["losses"] += stat["losses"]
        blade_stats[blade]["for"] += stat["for"]
        blade_stats[blade]["against"] += stat["against"]
        blade_stats[blade]["matches"] += stat["matches"]
    
    # Calculate blade winrates
    for stat in blade_stats.values():
        stat["winrate"] = stat["wins"] / stat["matches"] if stat["matches"] > 0 else 0.0
    
    # Generate blade leaderboard rows
    blade_rows = []
    for blade, elo in blade_elos.items():
        stat = blade_stats[blade]
        blade_rows.append({
            "Rank": 0,
            "Bey": blade,
            "Elo": round(elo, 2),
            "Wins": stat["wins"],
            "Losses": stat["losses"],
            "WinRate": round(stat["winrate"], 3),
            "For": stat["for"],
            "Against": stat["against"],
            "Matches": stat["matches"]
        })
    
    # Sort by ELO
    blade_rows.sort(key=lambda x: x["Elo"], reverse=True)
    for idx, row in enumerate(blade_rows, 1):
        row["Rank"] = idx
    
    # Save blade leaderboard (standard format) - always create even if empty
    df_blades = pd.DataFrame(blade_rows) if blade_rows else pd.DataFrame(columns=[
        "Rank", "Bey", "Elo", "Wins", "Losses", "WinRate", "For", "Against", "Matches"
    ])
    df_blades.to_csv(leaderboard_file, index=False)
    print(f"{GREEN}Saved blade leaderboard to {leaderboard_file}{RESET}")
    
    print(f"{GREEN}✓ Build-aware ELO pipeline complete{RESET}")
    print(f"{CYAN}  Total builds tracked: {len(build_elos)}{RESET}")
    print(f"{CYAN}  Total blades: {len(blade_elos)}{RESET}")
    print(f"{CYAN}  Total matches: {sum(s['matches'] for s in build_stats.values()) // 2}{RESET}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build-Aware ELO Calculator")
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                       help="ELO mode")
    parser.add_argument("--matches", default="./docs/data/matches.csv",
                       help="Input matches CSV")
    parser.add_argument("--leaderboard", default="./docs/data/leaderboard.csv",
                       help="Output blade leaderboard CSV")
    parser.add_argument("--build-leaderboard", default="./docs/data/build_leaderboard.csv",
                       help="Output build leaderboard CSV")
    parser.add_argument("--history", default="./docs/data/elo_history.csv",
                       help="Output ELO history CSV")
    
    args = parser.parse_args()
    
    config = {
        "mode": args.mode,
        "input_file": args.matches,
        "leaderboard": args.leaderboard,
        "build_leaderboard": args.build_leaderboard,
        "history": args.history,
        "start_elos": None
    }
    
    run_build_elo_pipeline(config)
