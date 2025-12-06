"""
Tournament Data Export for ELO Integration

This script exports completed tournament matches to the matches.csv format
for integration with the existing ELO calculation pipeline.
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tournament_manager import TournamentManager


def export_tournament_to_matches(tournament_id: str, output_file: str = "data/matches.csv", append: bool = True):
    """
    Export tournament matches to matches.csv format
    
    Args:
        tournament_id: Tournament ID to export
        output_file: Path to output CSV file
        append: If True, append to existing file; if False, create new file
    """
    manager = TournamentManager()
    
    try:
        tournament = manager.load_tournament(tournament_id)
    except ValueError as e:
        print(f"Error: {e}")
        return False
    
    if not tournament.completed:
        print(f"Warning: Tournament {tournament_id} is not yet completed")
        response = input("Export anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Prepare match data
    matches_data = []
    for match in tournament.matches:
        if match.status.value != 'completed':
            continue
        
        if match.is_bye():
            # Skip bye matches for ELO calculations
            continue
        
        # Format: winner, loser, winner_bey, loser_bey, score, date, format, tournament
        winner = match.winner
        loser = match.player_b if winner == match.player_a else match.player_a
        winner_score = match.score_a if winner == match.player_a else match.score_b
        loser_score = match.score_b if winner == match.player_a else match.score_a
        
        match_data = {
            'winner': winner,
            'loser': loser,
            'winner_bey': '',  # Would need to be added to tournament data
            'loser_bey': '',   # Would need to be added to tournament data
            'score': f"{winner_score}-{loser_score}",
            'date': tournament.date.split('T')[0] if 'T' in tournament.date else tournament.date,
            'format': 'Best of 5',  # Default, could be customizable
            'tournament': tournament.name,
            'round': f"Round {match.round_num}",
            'match_num': match.match_num
        }
        
        matches_data.append(match_data)
    
    if not matches_data:
        print(f"No completed matches to export from tournament {tournament_id}")
        return False
    
    # Write to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    mode = 'a' if append and output_path.exists() else 'w'
    file_exists = output_path.exists() and append
    
    with open(output_path, mode, newline='') as f:
        fieldnames = ['winner', 'loser', 'winner_bey', 'loser_bey', 'score', 'date', 'format', 'tournament']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for match_data in matches_data:
            # Remove tournament-specific fields before writing
            export_data = {k: v for k, v in match_data.items() if k in fieldnames}
            writer.writerow(export_data)
    
    print(f"Exported {len(matches_data)} matches from tournament '{tournament.name}' to {output_file}")
    return True


def export_all_tournaments(output_file: str = "data/matches.csv"):
    """
    Export all completed tournaments to matches.csv
    
    Args:
        output_file: Path to output CSV file
    """
    manager = TournamentManager()
    
    # Get all completed tournaments
    completed = manager.get_completed_tournaments()
    
    if not completed:
        print("No completed tournaments found")
        return
    
    print(f"Found {len(completed)} completed tournament(s)")
    
    # Clear the output file
    output_path = Path(output_file)
    if output_path.exists():
        response = input(f"File {output_file} exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Export cancelled")
            return
    
    success_count = 0
    for tournament_meta in completed:
        tournament_id = tournament_meta['id']
        if export_tournament_to_matches(tournament_id, output_file, append=(success_count > 0)):
            success_count += 1
    
    print(f"\nExported {success_count} tournament(s) successfully")


def add_tournament_metadata_to_matches(tournament_id: str):
    """
    Add tournament metadata to existing match entries
    
    This function updates the existing matches.csv to add tournament information
    for matches that came from tournaments.
    
    Args:
        tournament_id: Tournament ID
    """
    manager = TournamentManager()
    tournament = manager.load_tournament(tournament_id)
    
    # This would require updating the matches.csv structure
    # to support tournament metadata. For now, just export to a separate file.
    export_file = f"data/tournament_matches_{tournament_id}.csv"
    export_tournament_to_matches(tournament_id, export_file, append=False)
    print(f"Tournament matches exported to {export_file}")
    print("To integrate with main matches.csv, manually merge or use update.py")


def main():
    """Main entry point for the script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export tournament data for ELO integration')
    parser.add_argument('--tournament', '-t', help='Tournament ID to export')
    parser.add_argument('--all', '-a', action='store_true', help='Export all completed tournaments')
    parser.add_argument('--output', '-o', default='data/matches.csv', help='Output file path')
    parser.add_argument('--append', action='store_true', help='Append to existing file')
    
    args = parser.parse_args()
    
    if args.all:
        export_all_tournaments(args.output)
    elif args.tournament:
        export_tournament_to_matches(args.tournament, args.output, args.append)
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python export_tournament_data.py --tournament tournament_12345")
        print("  python export_tournament_data.py --all --output data/matches.csv")


if __name__ == '__main__':
    main()
