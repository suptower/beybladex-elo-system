"""
Tournament Manager

Manages multiple tournaments, provides tournament discovery,
and integrates with the existing Beyblade X Elo system.

Features:
- Create and manage multiple tournaments
- Save tournaments to persistent storage
- Load tournament history
- Export tournament data for frontend
- Integration with match data and Elo calculations
"""

import os
import json
import sys
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tournament_engine import Tournament, TournamentFormat


class TournamentManager:
    """
    Manages tournament lifecycle and storage

    Handles creating, loading, saving tournaments and provides
    integration with the Beyblade X data pipeline.
    """

    def __init__(self, storage_dir: str = "data/tournaments"):
        """
        Initialize tournament manager

        Args:
            storage_dir: Directory to store tournament JSON files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Active tournaments (loaded in memory)
        self.tournaments: Dict[str, Tournament] = {}

        # Tournament metadata index
        self.index_file = self.storage_dir / "tournaments_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load tournament index from file"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {"tournaments": []}

    def _save_index(self) -> None:
        """Save tournament index to file"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def create_tournament(
        self,
        name: str,
        format: str,
        participants: Optional[List[str]] = None,
        num_rounds: Optional[int] = None,
        **kwargs
    ) -> Tournament:
        """
        Create a new tournament

        Args:
            name: Tournament name
            format: Tournament format (swiss, single_elimination, etc.)
            participants: List of participant names
            num_rounds: Number of rounds (auto-calculated if None)
            **kwargs: Additional tournament configuration

        Returns:
            Created tournament instance
        """
        tournament = Tournament(
            name=name,
            format=format,
            participants=participants or [],
            num_rounds=num_rounds,
            **kwargs
        )

        # Add to active tournaments
        self.tournaments[tournament.tournament_id] = tournament

        # Update index
        self._add_to_index(tournament)

        # Save tournament
        self.save_tournament(tournament.tournament_id)

        return tournament

    def _add_to_index(self, tournament: Tournament) -> None:
        """Add tournament to index"""
        metadata = {
            "id": tournament.tournament_id,
            "name": tournament.name,
            "format": tournament.format.value,
            "date": tournament.date,
            "started": tournament.started,
            "completed": tournament.completed,
            "num_participants": len(tournament.participants),
            "num_rounds": tournament.num_rounds
        }

        # Check if already in index
        for i, existing in enumerate(self.index["tournaments"]):
            if existing["id"] == tournament.tournament_id:
                self.index["tournaments"][i] = metadata
                self._save_index()
                return

        # Add new entry
        self.index["tournaments"].append(metadata)
        self._save_index()

    def load_tournament(self, tournament_id: str) -> Tournament:
        """
        Load a tournament from storage

        Args:
            tournament_id: Tournament ID to load

        Returns:
            Loaded tournament instance
        """
        if tournament_id in self.tournaments:
            return self.tournaments[tournament_id]

        filepath = self.storage_dir / f"{tournament_id}.json"
        if not filepath.exists():
            raise ValueError(f"Tournament {tournament_id} not found")

        tournament = Tournament.load(str(filepath))
        self.tournaments[tournament_id] = tournament

        return tournament

    def save_tournament(self, tournament_id: str) -> None:
        """
        Save a tournament to storage

        Args:
            tournament_id: Tournament ID to save
        """
        if tournament_id not in self.tournaments:
            raise ValueError(f"Tournament {tournament_id} not in memory")

        tournament = self.tournaments[tournament_id]
        filepath = self.storage_dir / f"{tournament_id}.json"
        tournament.save(str(filepath))

        # Update index
        self._add_to_index(tournament)

    def save_all(self) -> None:
        """Save all active tournaments"""
        for tournament_id in self.tournaments:
            self.save_tournament(tournament_id)

    def list_tournaments(
        self,
        format: Optional[str] = None,
        completed: Optional[bool] = None,
        started: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List tournaments with optional filtering

        Args:
            format: Filter by tournament format
            completed: Filter by completion status
            started: Filter by started status

        Returns:
            List of tournament metadata dictionaries
        """
        tournaments = self.index["tournaments"]

        if format is not None:
            tournaments = [t for t in tournaments if t["format"] == format]

        if completed is not None:
            tournaments = [t for t in tournaments if t["completed"] == completed]

        if started is not None:
            tournaments = [t for t in tournaments if t["started"] == started]

        # Sort by date (newest first)
        tournaments = sorted(tournaments, key=lambda t: t["date"], reverse=True)

        return tournaments

    def get_tournament_summary(self, tournament_id: str) -> Dict[str, Any]:
        """
        Get tournament summary with basic stats

        Args:
            tournament_id: Tournament ID

        Returns:
            Tournament summary dictionary
        """
        tournament = self.load_tournament(tournament_id)

        standings = tournament.get_standings()
        winner = standings[0]["player"] if standings and tournament.completed else None

        return {
            "id": tournament.tournament_id,
            "name": tournament.name,
            "format": tournament.format.value,
            "date": tournament.date,
            "started": tournament.started,
            "completed": tournament.completed,
            "num_participants": len(tournament.participants),
            "num_rounds": tournament.num_rounds,
            "current_round": tournament.current_round,
            "winner": winner,
            "num_matches": len(tournament.matches)
        }

    def export_for_frontend(self, output_file: str = "docs/data/tournaments.json", merge_existing: bool = True) -> None:
        """
        Export tournament data for frontend consumption

        Args:
            output_file: Path to output JSON file
            merge_existing: If True, merge with existing tournaments (e.g., from Challonge)
        """
        tournaments_data = []

        # Load existing tournaments if merging
        existing_tournaments = []
        if merge_existing:
            output_path = Path(output_file)
            if output_path.exists():
                with open(output_path, 'r') as f:
                    existing_data = json.load(f)
                    # Keep non-custom tournaments (e.g., Challonge imports)
                    existing_tournaments = [
                        t for t in existing_data.get("tournaments", [])
                        if not t.get("custom", False)
                    ]

        # Add custom tournaments
        for tournament_meta in self.index["tournaments"]:
            tournament_id = tournament_meta["id"]

            try:
                tournament = self.load_tournament(tournament_id)
                standings = tournament.get_standings()
                winner = standings[0]["player"] if standings and tournament.completed else "Ongoing"

                # Format for frontend
                tournament_data = {
                    "id": tournament_id,
                    "name": tournament.name,
                    "date": tournament.date,
                    "format": tournament.format.value.replace("_", " ").title(),
                    "players": len(tournament.participants),
                    "winner": winner,
                    "challonge": None,  # For backward compatibility
                    "parameter": None,
                    "custom": True  # Flag to indicate this is a custom tournament
                }

                tournaments_data.append(tournament_data)
            except Exception as e:
                print(f"Error loading tournament {tournament_id}: {e}")
                continue

        # Combine existing and custom tournaments
        all_tournaments = existing_tournaments + tournaments_data

        # Sort by date
        all_tournaments.sort(key=lambda t: t["date"], reverse=True)

        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump({"tournaments": all_tournaments}, f, indent=2)

        print(f"Exported {len(tournaments_data)} custom tournaments (merged with {len(existing_tournaments)} existing) to {output_file}")

    def export_tournament_details(self, tournament_id: str, output_dir: str = "docs/data/tournaments") -> None:
        """
        Export detailed tournament data for a specific tournament

        Args:
            tournament_id: Tournament ID to export
            output_dir: Directory to save tournament details
        """
        tournament = self.load_tournament(tournament_id)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export tournament data
        tournament_file = output_path / f"{tournament_id}.json"

        # Create detailed export with all data
        export_data = tournament.to_dict()

        # Add additional computed data
        export_data["summary"] = {
            "total_matches": len(tournament.matches),
            "completed_matches": len([m for m in tournament.matches if m.status.value == "completed"]),
            "rounds_completed": max([m.round_num for m in tournament.matches if m.status.value == "completed"], default=0),
            "participants_active": len([p for p in tournament.participants.values() if p.active])
        }

        with open(tournament_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported tournament details to {tournament_file}")

    def delete_tournament(self, tournament_id: str) -> None:
        """
        Delete a tournament

        Args:
            tournament_id: Tournament ID to delete
        """
        # Remove from memory
        if tournament_id in self.tournaments:
            del self.tournaments[tournament_id]

        # Remove from index
        self.index["tournaments"] = [
            t for t in self.index["tournaments"] if t["id"] != tournament_id
        ]
        self._save_index()

        # Remove file
        filepath = self.storage_dir / f"{tournament_id}.json"
        if filepath.exists():
            filepath.unlink()

    def get_active_tournaments(self) -> List[Dict[str, Any]]:
        """Get list of active (started but not completed) tournaments"""
        return self.list_tournaments(started=True, completed=False)

    def get_completed_tournaments(self) -> List[Dict[str, Any]]:
        """Get list of completed tournaments"""
        return self.list_tournaments(completed=True)

    def import_legacy_tournament(
        self,
        name: str,
        date: str,
        format: str,
        participants: List[str],
        matches: List[Dict[str, Any]],
        winner: Optional[str] = None
    ) -> Tournament:
        """
        Import a legacy tournament (e.g., from Challonge data)

        Args:
            name: Tournament name
            date: Tournament date (ISO format)
            format: Tournament format
            participants: List of participants
            matches: List of match data
            winner: Tournament winner (if completed)

        Returns:
            Imported tournament instance
        """
        # Create tournament
        tournament = self.create_tournament(
            name=name,
            format=format,
            participants=participants,
            date=date
        )

        # Start tournament
        tournament.start()

        # Import matches
        for match_data in matches:
            try:
                tournament.report_match(
                    round_num=match_data["round"],
                    match_num=match_data["match_num"],
                    winner=match_data["winner"],
                    score_a=match_data.get("score_a", 0),
                    score_b=match_data.get("score_b", 0)
                )
            except Exception as e:
                print(f"Error importing match: {e}")
                continue

        # Save
        self.save_tournament(tournament.tournament_id)

        return tournament


def main():
    """Example usage of TournamentManager"""
    manager = TournamentManager()

    # Create a new tournament
    tournament = manager.create_tournament(
        name="Example Tournament",
        format="swiss",
        participants=["Player1", "Player2", "Player3", "Player4", "Player5", "Player6"],
        num_rounds=3
    )

    print(f"Created tournament: {tournament.name}")
    print(f"ID: {tournament.tournament_id}")

    # Start tournament
    tournament.start()
    print(f"Tournament started, current round: {tournament.current_round}")

    # Simulate some matches
    round1_matches = tournament.get_matches(round_num=1)
    print(f"\nRound 1 matches:")
    for match in round1_matches:
        print(f"  Match {match['match_num']}: {match['player_a']} vs {match['player_b']}")

    # Report results
    for i, match in enumerate(round1_matches):
        if match['player_b']:  # Skip byes
            winner = match['player_a'] if i % 2 == 0 else match['player_b']
            tournament.report_match(1, match['match_num'], winner, 4, 2)

    # Save tournament
    manager.save_tournament(tournament.tournament_id)
    print(f"\nTournament saved!")

    # List all tournaments
    all_tournaments = manager.list_tournaments()
    print(f"\nTotal tournaments: {len(all_tournaments)}")
    for t in all_tournaments:
        print(f"  - {t['name']} ({t['format']}) - {t['date']}")

    # Export for frontend
    manager.export_for_frontend()
    manager.export_tournament_details(tournament.tournament_id)

    print("\nExport complete!")


if __name__ == "__main__":
    main()
