#!/usr/bin/env python3
"""
Tournament Simulation Script for BeybladeX Elo System

This script simulates Beyblade tournaments using current Elo ratings to predict match outcomes.
Supports multiple tournament formats: single elimination, double elimination, and round-robin.
"""

import csv
import random
import argparse
import os
from datetime import date, timedelta
from collections import defaultdict

# Aktiviert ANSI-Farben in Windows-Terminals (macht nix auf anderen Systemen)
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"

# File paths
BEYS_FILE = "./csv/beys.csv"
LEADERBOARD_FILE = "./csv/leaderboard.csv"
MATCHES_FILE = "./csv/matches.csv"

# Default Elo values
DEFAULT_ELO = 1000


def load_beys():
    """Load list of Beyblades from beys.csv"""
    beys = []
    try:
        with open(BEYS_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    beys.append(row[0].strip())
    except FileNotFoundError:
        print(f"{RED}Error: {BEYS_FILE} not found{RESET}")
        return []
    return beys


def load_elos():
    """Load current Elo ratings from leaderboard.csv"""
    elos = {}
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["Name"]
                elo = float(row["ELO"])
                elos[name] = elo
    except FileNotFoundError:
        print(f"{YELLOW}Warning: {LEADERBOARD_FILE} not found, using default Elos{RESET}")
    return elos


def expected_score(elo_a, elo_b):
    """Calculate expected score for player A against player B"""
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def simulate_match(bey_a, bey_b, elo_a, elo_b, max_points=5):
    """
    Simulate a match between two Beyblades based on their Elo ratings.
    Returns (score_a, score_b) tuple.
    
    The match is simulated as a series of rounds where each round's winner
    is determined by Elo-based probability.
    """
    exp_a = expected_score(elo_a, elo_b)
    
    score_a = 0
    score_b = 0
    
    # Simulate rounds until one player reaches max_points
    while score_a < max_points and score_b < max_points:
        if random.random() < exp_a:
            score_a += 1
        else:
            score_b += 1
    
    return score_a, score_b


def simulate_single_elimination(participants, elos, start_date, verbose=True):
    """
    Simulate a single elimination tournament.
    Returns list of matches: [(date, bey_a, bey_b, score_a, score_b), ...]
    """
    if verbose:
        print(f"{CYAN}Starting Single Elimination Tournament{RESET}")
        print(f"{CYAN}Participants: {len(participants)}{RESET}")
    
    matches = []
    current_round = list(participants)
    round_num = 1
    current_date = start_date
    
    while len(current_round) > 1:
        if verbose:
            print(f"\n{BOLD}Round {round_num} ({len(current_round)} participants){RESET}")
        
        next_round = []
        
        # If odd number of participants, one gets a bye
        if len(current_round) % 2 == 1:
            bye_participant = current_round.pop(0)
            next_round.append(bye_participant)
            if verbose:
                print(f"  {YELLOW}{bye_participant} receives a bye{RESET}")
        
        # Pair up remaining participants
        for i in range(0, len(current_round), 2):
            bey_a = current_round[i]
            bey_b = current_round[i + 1]
            
            elo_a = elos.get(bey_a, DEFAULT_ELO)
            elo_b = elos.get(bey_b, DEFAULT_ELO)
            
            score_a, score_b = simulate_match(bey_a, bey_b, elo_a, elo_b)
            
            winner = bey_a if score_a > score_b else bey_b
            next_round.append(winner)
            
            matches.append((current_date.isoformat(), bey_a, bey_b, score_a, score_b))
            
            if verbose:
                print(f"  {bey_a} ({elo_a:.0f}) vs {bey_b} ({elo_b:.0f}): {score_a}-{score_b} → {GREEN}{winner}{RESET}")
        
        current_round = next_round
        round_num += 1
        current_date += timedelta(days=1)
    
    if verbose:
        print(f"\n{BOLD}{GREEN}Tournament Winner: {current_round[0]}{RESET}")
    
    return matches


def simulate_round_robin(participants, elos, start_date, verbose=True):
    """
    Simulate a round-robin tournament where each participant plays every other participant once.
    Returns list of matches: [(date, bey_a, bey_b, score_a, score_b), ...]
    """
    if verbose:
        print(f"{CYAN}Starting Round-Robin Tournament{RESET}")
        print(f"{CYAN}Participants: {len(participants)}{RESET}")
        print(f"{CYAN}Total matches: {len(participants) * (len(participants) - 1) // 2}{RESET}")
    
    matches = []
    current_date = start_date
    
    # Generate all unique pairs
    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            bey_a = participants[i]
            bey_b = participants[j]
            
            elo_a = elos.get(bey_a, DEFAULT_ELO)
            elo_b = elos.get(bey_b, DEFAULT_ELO)
            
            score_a, score_b = simulate_match(bey_a, bey_b, elo_a, elo_b)
            
            matches.append((current_date.isoformat(), bey_a, bey_b, score_a, score_b))
            
            if verbose:
                winner = bey_a if score_a > score_b else bey_b
                print(f"  {bey_a} ({elo_a:.0f}) vs {bey_b} ({elo_b:.0f}): {score_a}-{score_b} → {GREEN}{winner}{RESET}")
    
    # Calculate standings
    if verbose:
        standings = defaultdict(lambda: {"wins": 0, "losses": 0, "points_for": 0, "points_against": 0})
        for _, bey_a, bey_b, score_a, score_b in matches:
            standings[bey_a]["points_for"] += score_a
            standings[bey_a]["points_against"] += score_b
            standings[bey_b]["points_for"] += score_b
            standings[bey_b]["points_against"] += score_a
            
            if score_a > score_b:
                standings[bey_a]["wins"] += 1
                standings[bey_b]["losses"] += 1
            else:
                standings[bey_b]["wins"] += 1
                standings[bey_a]["losses"] += 1
        
        print(f"\n{BOLD}Final Standings:{RESET}")
        sorted_standings = sorted(standings.items(), 
                                  key=lambda x: (x[1]["wins"], x[1]["points_for"] - x[1]["points_against"]), 
                                  reverse=True)
        for i, (bey, stats) in enumerate(sorted_standings, 1):
            print(f"{i}. {bey}: {stats['wins']}W-{stats['losses']}L "
                  f"(+{stats['points_for'] - stats['points_against']})")
    
    return matches


def save_matches(matches, output_file, append=False):
    """Save simulated matches to CSV file"""
    mode = "a" if append else "w"
    
    with open(output_file, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if not append:
            writer.writerow(["Date", "BeyA", "BeyB", "ScoreA", "ScoreB"])
        
        for match in matches:
            writer.writerow(match)
    
    print(f"{GREEN}Matches saved to {output_file}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Simulate Beyblade tournaments using Elo ratings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single elimination tournament with 8 random participants
  python scripts/simulation.py -n 8 -f single-elimination
  
  # Round-robin tournament with specific participants
  python scripts/simulation.py -f round-robin -b FoxBrush ImpactDrake DranSword
  
  # Append simulated matches to matches.csv
  python scripts/simulation.py -n 16 -f single-elimination --append
  
  # Save to custom file with custom start date
  python scripts/simulation.py -n 8 -o simulated_matches.csv --date 2025-12-01
        """
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["single-elimination", "round-robin"],
        default="single-elimination",
        help="Tournament format (default: single-elimination)"
    )
    
    parser.add_argument(
        "-n", "--num-participants",
        type=int,
        help="Number of random participants to select"
    )
    
    parser.add_argument(
        "-b", "--beys",
        nargs="+",
        help="Specific Beyblades to include in tournament"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./sim_output/simulated_matches.csv",
        help="Output file for simulated matches (default: ./csv/simulated_matches.csv)"
    )
    
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to matches.csv instead of creating separate file"
    )
    
    parser.add_argument(
        "--date",
        help="Start date for tournament (ISO format YYYY-MM-DD, default: today)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode - minimal output"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible results"
    )
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"{CYAN}Using random seed: {args.seed}{RESET}")
    
    # Load data
    all_beys = load_beys()
    elos = load_elos()
    
    if not all_beys:
        print(f"{RED}No Beyblades found. Please check {BEYS_FILE}{RESET}")
        return 1
    
    # Select participants
    if args.beys:
        participants = args.beys
        # Validate that all specified beys exist
        for bey in participants:
            if bey not in all_beys:
                print(f"{YELLOW}Warning: {bey} not found in {BEYS_FILE}{RESET}")
    elif args.num_participants:
        if args.num_participants > len(all_beys):
            print(f"{YELLOW}Warning: Requested {args.num_participants} participants but only {len(all_beys)} available{RESET}")
            participants = all_beys
        else:
            participants = random.sample(all_beys, args.num_participants)
    else:
        print(f"{RED}Error: Must specify either --num-participants or --beys{RESET}")
        return 1
    
    # Set start date
    if args.date:
        try:
            start_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"{RED}Error: Invalid date format. Use YYYY-MM-DD{RESET}")
            return 1
    else:
        start_date = date.today()
    
    verbose = not args.quiet
    
    # Run simulation
    if args.format == "single-elimination":
        matches = simulate_single_elimination(participants, elos, start_date, verbose)
    else:  # round-robin
        matches = simulate_round_robin(participants, elos, start_date, verbose)
    
    # Save results
    if args.append:
        save_matches(matches, MATCHES_FILE, append=True)
        print(f"{YELLOW}Note: Run 'python update.py' to recalculate Elo ratings{RESET}")
    else:
        save_matches(matches, args.output, append=False)
    
    print(f"\n{BOLD}{GREEN}Simulation complete! {len(matches)} matches generated.{RESET}")
    return 0


if __name__ == "__main__":
    exit(main())
