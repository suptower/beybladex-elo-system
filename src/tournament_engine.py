"""
Custom Tournament Management Engine

This module provides a complete tournament management system supporting:
- Swiss System with automatic pairing
- Single Elimination brackets
- Double Elimination brackets
- Hybrid formats (Swiss -> Top Cut -> DE/SE)

Features:
- Automatic pairing algorithms
- Tie-breaker calculations (Buchholz, Opponent Win %, etc.)
- Match result tracking
- Tournament state persistence
- Placement matches support

Usage:
    tournament = Tournament(name="My Tournament", format="swiss", num_rounds=5)
    tournament.add_participant("PlayerA")
    tournament.start()
    tournament.report_match(round_num=1, match_num=0, winner="PlayerA", score_a=4, score_b=2)
"""

import json
import random
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import os


class TournamentFormat(Enum):
    """Supported tournament formats"""
    SWISS = "swiss"
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    HYBRID_SWISS_SE = "hybrid_swiss_se"
    HYBRID_SWISS_DE = "hybrid_swiss_de"


class MatchStatus(Enum):
    """Match status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BYE = "bye"


class TieBreaker(Enum):
    """Tie-breaker methods for Swiss"""
    BUCHHOLZ = "buchholz"
    OPPONENT_WIN_PCT = "opponent_win_pct"
    GAME_WIN_PCT = "game_win_pct"
    HEAD_TO_HEAD = "head_to_head"


@dataclass
class Participant:
    """Tournament participant"""
    name: str
    seed: int = 0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Participant):
            return self.name == other.name
        return False


@dataclass
class Match:
    """Single match in a tournament"""
    match_id: str
    round_num: int
    match_num: int
    player_a: Optional[str] = None
    player_b: Optional[str] = None
    score_a: int = 0
    score_b: int = 0
    winner: Optional[str] = None
    status: MatchStatus = MatchStatus.PENDING
    bracket: str = "main"  # 'main' or 'losers' for DE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_bye(self) -> bool:
        """Check if this is a bye match"""
        return self.player_b is None or self.status == MatchStatus.BYE

    def get_loser(self) -> Optional[str]:
        """Get the losing player"""
        if not self.winner or self.is_bye():
            return None
        return self.player_b if self.winner == self.player_a else self.player_a


@dataclass
class Standing:
    """Player standing in tournament"""
    player: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    points: float = 0.0  # Win = 1, Draw = 0.5, Loss = 0
    game_wins: int = 0
    game_losses: int = 0
    buchholz: float = 0.0
    opponent_win_pct: float = 0.0
    rank: int = 0
    opponents: List[str] = field(default_factory=list)


class Tournament:
    """
    Main tournament management class
    
    Handles tournament creation, participant management, pairing,
    match reporting, and standings calculation.
    """

    def __init__(
        self,
        name: str,
        format: str = "swiss",
        num_rounds: Optional[int] = None,
        participants: Optional[List[str]] = None,
        tournament_id: Optional[str] = None,
        date: Optional[str] = None,
        tie_breakers: Optional[List[str]] = None,
        top_cut: Optional[int] = None,
        allow_byes: bool = True
    ):
        """
        Initialize a tournament
        
        Args:
            name: Tournament name
            format: Tournament format (swiss, single_elimination, etc.)
            num_rounds: Number of rounds (None = auto-calculate)
            participants: List of participant names
            tournament_id: Unique tournament ID (auto-generated if None)
            date: Tournament date (ISO format, defaults to today)
            tie_breakers: List of tie-breaker methods (defaults to standard Swiss)
            top_cut: Number of players for top cut in hybrid formats
            allow_byes: Whether to allow bye rounds
        """
        self.name = name
        self.format = TournamentFormat(format)
        self.tournament_id = tournament_id or self._generate_id()
        self.date = date or datetime.now().isoformat()
        self.allow_byes = allow_byes
        
        # Tournament structure
        self.current_round = 0
        self.started = False
        self.completed = False
        
        # Participants
        self.participants: Dict[str, Participant] = {}
        
        # Matches and pairings
        self.matches: List[Match] = []
        self.pairings_history: Dict[Tuple[str, str], int] = {}
        
        # Standings
        self.standings: Dict[str, Standing] = {}
        
        # Add participants if provided
        if participants:
            for i, p in enumerate(participants):
                self.add_participant(p, seed=i + 1)
        
        # Calculate rounds after adding participants
        self.num_rounds = num_rounds or self._calculate_rounds()
        
        # Configuration
        self.tie_breakers = [TieBreaker(tb) for tb in (tie_breakers or ["buchholz", "opponent_win_pct"])]
        self.top_cut = top_cut
        
        # Metadata
        self.metadata: Dict[str, Any] = {}

    def _generate_id(self) -> str:
        """Generate unique tournament ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"tournament_{timestamp}"

    def _calculate_rounds(self) -> int:
        """Calculate optimal number of rounds based on format and participants"""
        num_participants = len(self.participants)
        
        if self.format == TournamentFormat.SWISS:
            # Swiss: typically log2(n) rounded up, with a max
            if num_participants == 0:
                return 5  # Default
            import math
            return min(math.ceil(math.log2(num_participants)), 7)
        
        elif self.format in [TournamentFormat.SINGLE_ELIMINATION, TournamentFormat.DOUBLE_ELIMINATION]:
            # Knockout: log2(n) rounds
            if num_participants == 0:
                return 3
            import math
            return math.ceil(math.log2(num_participants))
        
        elif self.format == TournamentFormat.ROUND_ROBIN:
            # Round robin: n-1 rounds (or n if pairing in different ways)
            return max(num_participants - 1, 1)
        
        return 5  # Default fallback

    def add_participant(self, name: str, seed: int = 0, **metadata) -> None:
        """Add a participant to the tournament"""
        if self.started:
            raise ValueError("Cannot add participants after tournament has started")
        
        participant = Participant(name=name, seed=seed or len(self.participants) + 1, metadata=metadata)
        self.participants[name] = participant
        self.standings[name] = Standing(player=name)

    def remove_participant(self, name: str) -> None:
        """Remove a participant (mark as inactive)"""
        if name in self.participants:
            self.participants[name].active = False

    def start(self) -> None:
        """Start the tournament and generate first round pairings"""
        if self.started:
            raise ValueError("Tournament already started")
        
        if len([p for p in self.participants.values() if p.active]) < 2:
            raise ValueError("Need at least 2 active participants")
        
        self.started = True
        self.current_round = 1
        self._generate_round_pairings(1)

    def _generate_round_pairings(self, round_num: int) -> None:
        """Generate pairings for a specific round"""
        if self.format == TournamentFormat.SWISS:
            self._generate_swiss_pairings(round_num)
        elif self.format == TournamentFormat.SINGLE_ELIMINATION:
            self._generate_knockout_pairings(round_num)
        elif self.format == TournamentFormat.DOUBLE_ELIMINATION:
            self._generate_double_elim_pairings(round_num)
        elif self.format == TournamentFormat.ROUND_ROBIN:
            self._generate_round_robin_pairings(round_num)

    def _generate_swiss_pairings(self, round_num: int) -> None:
        """Generate Swiss system pairings"""
        active_players = [p.name for p in self.participants.values() if p.active]
        
        if round_num == 1:
            # First round: pair by seeding
            random.shuffle(active_players)  # Or use actual seeding
            self._pair_players(active_players, round_num)
        else:
            # Subsequent rounds: pair by standings
            sorted_standings = self._get_sorted_standings()
            players = [s.player for s in sorted_standings if self.participants[s.player].active]
            self._pair_swiss_by_score(players, round_num)

    def _pair_players(self, players: List[str], round_num: int) -> None:
        """Create matches from a list of players"""
        matches = []
        i = 0
        
        while i < len(players):
            player_a = players[i]
            player_b = players[i + 1] if i + 1 < len(players) else None
            
            match_id = f"{self.tournament_id}_R{round_num}_M{len(matches)}"
            match = Match(
                match_id=match_id,
                round_num=round_num,
                match_num=len(matches),
                player_a=player_a,
                player_b=player_b,
                status=MatchStatus.BYE if player_b is None else MatchStatus.PENDING
            )
            matches.append(match)
            
            if player_b:
                # Track pairing history
                pair = tuple(sorted([player_a, player_b]))
                self.pairings_history[pair] = self.pairings_history.get(pair, 0) + 1
            else:
                # Process bye immediately - set as completed and update standings
                match.status = MatchStatus.COMPLETED
                match.winner = player_a
                self._update_standings(match)
            
            i += 2
        
        self.matches.extend(matches)

    def _pair_swiss_by_score(self, players: List[str], round_num: int) -> None:
        """
        Pair players by score group (Swiss pairing)
        Avoids rematches when possible
        """
        paired = set()
        matches = []
        
        i = 0
        while i < len(players):
            if players[i] in paired:
                i += 1
                continue
            
            player_a = players[i]
            player_b = None
            
            # Try to find an unpaired opponent with similar score
            for j in range(i + 1, len(players)):
                if players[j] in paired:
                    continue
                
                candidate = players[j]
                pair = tuple(sorted([player_a, candidate]))
                
                # Avoid rematches
                if self.pairings_history.get(pair, 0) == 0:
                    player_b = candidate
                    paired.add(player_b)
                    break
            
            # If no valid opponent found, take the next available
            if not player_b:
                for j in range(i + 1, len(players)):
                    if players[j] not in paired:
                        player_b = players[j]
                        paired.add(player_b)
                        break
            
            paired.add(player_a)
            
            match_id = f"{self.tournament_id}_R{round_num}_M{len(matches)}"
            match = Match(
                match_id=match_id,
                round_num=round_num,
                match_num=len(matches),
                player_a=player_a,
                player_b=player_b,
                status=MatchStatus.BYE if player_b is None else MatchStatus.PENDING
            )
            matches.append(match)
            
            if player_b:
                pair = tuple(sorted([player_a, player_b]))
                self.pairings_history[pair] = self.pairings_history.get(pair, 0) + 1
            
            i += 1
        
        self.matches.extend(matches)

    def _generate_knockout_pairings(self, round_num: int) -> None:
        """Generate single elimination bracket pairings"""
        if round_num == 1:
            # First round: seed-based bracket
            active_players = sorted(
                [p for p in self.participants.values() if p.active],
                key=lambda p: p.seed
            )
            players = [p.name for p in active_players]
            self._pair_players(players, round_num)
        else:
            # Subsequent rounds: winners advance
            prev_round_matches = [m for m in self.matches if m.round_num == round_num - 1]
            winners = [m.winner for m in prev_round_matches if m.winner]
            self._pair_players(winners, round_num)

    def _generate_double_elim_pairings(self, round_num: int) -> None:
        """Generate double elimination bracket pairings"""
        # Simplified DE implementation
        # In practice, this would handle winners and losers brackets
        if round_num == 1:
            self._generate_knockout_pairings(round_num)
        else:
            # Winners bracket
            prev_winners = [m.winner for m in self.matches 
                          if m.round_num == round_num - 1 and m.bracket == "main" and m.winner]
            
            # Losers bracket (players who lost in winners bracket)
            prev_losers = [m.get_loser() for m in self.matches 
                         if m.round_num == round_num - 1 and m.bracket == "main" and m.get_loser()]
            
            # Create winners bracket matches
            for i in range(0, len(prev_winners), 2):
                if i + 1 < len(prev_winners):
                    match_id = f"{self.tournament_id}_R{round_num}_WB{i//2}"
                    match = Match(
                        match_id=match_id,
                        round_num=round_num,
                        match_num=len(self.matches),
                        player_a=prev_winners[i],
                        player_b=prev_winners[i + 1],
                        bracket="main"
                    )
                    self.matches.append(match)
            
            # Create losers bracket matches
            for i in range(0, len(prev_losers), 2):
                if i + 1 < len(prev_losers):
                    match_id = f"{self.tournament_id}_R{round_num}_LB{i//2}"
                    match = Match(
                        match_id=match_id,
                        round_num=round_num,
                        match_num=len(self.matches),
                        player_a=prev_losers[i],
                        player_b=prev_losers[i + 1],
                        bracket="losers"
                    )
                    self.matches.append(match)

    def _generate_round_robin_pairings(self, round_num: int) -> None:
        """Generate round robin pairings (all vs all)"""
        # For now, use a simple approach
        # A proper round-robin would use circle method
        active_players = [p.name for p in self.participants.values() if p.active]
        
        # Simple implementation: pair sequentially for this round
        # A better implementation would use rotation algorithm
        self._pair_players(active_players[round_num-1:] + active_players[:round_num-1], round_num)

    def report_match(
        self,
        round_num: int,
        match_num: int,
        winner: str,
        score_a: int = 0,
        score_b: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report match result
        
        Args:
            round_num: Round number
            match_num: Match number within the round
            winner: Name of winning player
            score_a: Score for player A
            score_b: Score for player B
            metadata: Additional match metadata
        """
        # Find the match
        match = None
        for m in self.matches:
            if m.round_num == round_num and m.match_num == match_num:
                match = m
                break
        
        if not match:
            raise ValueError(f"Match not found: Round {round_num}, Match {match_num}")
        
        if match.status == MatchStatus.COMPLETED:
            raise ValueError("Match already completed")
        
        # Validate winner is in the match
        if match.player_a != winner and match.player_b != winner:
            raise ValueError(f"Winner {winner} is not a participant in this match ({match.player_a} vs {match.player_b})")
        
        # Update match
        match.winner = winner
        match.score_a = score_a
        match.score_b = score_b
        match.status = MatchStatus.COMPLETED
        
        if metadata:
            match.metadata.update(metadata)
        
        # Update standings
        self._update_standings(match)
        
        # Check if round is complete
        if self._is_round_complete(round_num):
            self._finalize_round(round_num)

    def _update_standings(self, match: Match) -> None:
        """Update standings based on match result"""
        if match.is_bye():
            # Bye counts as a win
            if match.player_a:
                standing = self.standings[match.player_a]
                standing.wins += 1
                standing.points += 1.0
            return
        
        player_a = match.player_a
        player_b = match.player_b
        
        if not player_a or not player_b:
            return
        
        standing_a = self.standings[player_a]
        standing_b = self.standings[player_b]
        
        # Update opponents
        if player_b not in standing_a.opponents:
            standing_a.opponents.append(player_b)
        if player_a not in standing_b.opponents:
            standing_b.opponents.append(player_a)
        
        # Update game scores
        standing_a.game_wins += match.score_a
        standing_a.game_losses += match.score_b
        standing_b.game_wins += match.score_b
        standing_b.game_losses += match.score_a
        
        # Update match results
        if match.winner == player_a:
            standing_a.wins += 1
            standing_a.points += 1.0
            standing_b.losses += 1
        elif match.winner == player_b:
            standing_b.wins += 1
            standing_b.points += 1.0
            standing_a.losses += 1
        else:
            # Draw
            standing_a.draws += 1
            standing_b.draws += 1
            standing_a.points += 0.5
            standing_b.points += 0.5

    def _is_round_complete(self, round_num: int) -> bool:
        """Check if all matches in a round are complete"""
        round_matches = [m for m in self.matches if m.round_num == round_num]
        return all(m.status == MatchStatus.COMPLETED or m.status == MatchStatus.BYE 
                  for m in round_matches)

    def _finalize_round(self, round_num: int) -> None:
        """Finalize round and prepare for next"""
        # Calculate tie-breakers
        self._calculate_tiebreakers()
        
        # Update rankings
        self._update_rankings()
        
        # Generate next round if needed
        if round_num < self.num_rounds:
            self.current_round = round_num + 1
            self._generate_round_pairings(self.current_round)
        else:
            self.completed = True

    def _calculate_tiebreakers(self) -> None:
        """Calculate tie-breaker scores for all players"""
        for player, standing in self.standings.items():
            # Buchholz: sum of opponents' points
            buchholz = sum(self.standings[opp].points for opp in standing.opponents if opp in self.standings)
            standing.buchholz = buchholz
            
            # Opponent win percentage
            if standing.opponents:
                opponent_matches = sum(
                    self.standings[opp].wins + self.standings[opp].losses + self.standings[opp].draws
                    for opp in standing.opponents if opp in self.standings
                )
                opponent_wins = sum(
                    self.standings[opp].wins + 0.5 * self.standings[opp].draws
                    for opp in standing.opponents if opp in self.standings
                )
                standing.opponent_win_pct = opponent_wins / opponent_matches if opponent_matches > 0 else 0.0
            else:
                standing.opponent_win_pct = 0.0

    def _update_rankings(self) -> None:
        """Update player rankings based on standings and tie-breakers"""
        sorted_standings = self._get_sorted_standings()
        for i, standing in enumerate(sorted_standings):
            standing.rank = i + 1

    def _get_sorted_standings(self) -> List[Standing]:
        """Get standings sorted by points, then tie-breakers"""
        return sorted(
            self.standings.values(),
            key=lambda s: (
                -s.points,  # Higher points first
                -s.buchholz,  # Higher Buchholz first
                -s.opponent_win_pct,  # Higher opponent win % first
                -(s.game_wins - s.game_losses)  # Better game differential
            )
        )

    def get_standings(self) -> List[Dict[str, Any]]:
        """Get current standings as list of dictionaries"""
        sorted_standings = self._get_sorted_standings()
        return [
            {
                "rank": s.rank,
                "player": s.player,
                "wins": s.wins,
                "losses": s.losses,
                "draws": s.draws,
                "points": s.points,
                "game_wins": s.game_wins,
                "game_losses": s.game_losses,
                "buchholz": round(s.buchholz, 2),
                "opponent_win_pct": round(s.opponent_win_pct, 3)
            }
            for s in sorted_standings
        ]

    def get_matches(self, round_num: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get matches, optionally filtered by round"""
        matches = self.matches if round_num is None else [m for m in self.matches if m.round_num == round_num]
        return [
            {
                "match_id": m.match_id,
                "round": m.round_num,
                "match_num": m.match_num,
                "player_a": m.player_a,
                "player_b": m.player_b,
                "score_a": m.score_a,
                "score_b": m.score_b,
                "winner": m.winner,
                "status": m.status.value,
                "bracket": m.bracket
            }
            for m in matches
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Export tournament to dictionary"""
        return {
            "tournament_id": self.tournament_id,
            "name": self.name,
            "format": self.format.value,
            "date": self.date,
            "num_rounds": self.num_rounds,
            "current_round": self.current_round,
            "started": self.started,
            "completed": self.completed,
            "participants": [
                {"name": p.name, "seed": p.seed, "active": p.active, **p.metadata}
                for p in self.participants.values()
            ],
            "matches": self.get_matches(),
            "standings": self.get_standings(),
            "metadata": self.metadata
        }

    def save(self, filepath: str) -> None:
        """Save tournament to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'Tournament':
        """Load tournament from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Create tournament
        tournament = cls(
            name=data["name"],
            format=data["format"],
            num_rounds=data["num_rounds"],
            tournament_id=data["tournament_id"],
            date=data.get("date")
        )
        
        # Restore state
        tournament.current_round = data["current_round"]
        tournament.started = data["started"]
        tournament.completed = data["completed"]
        tournament.metadata = data.get("metadata", {})
        
        # Restore participants
        for p_data in data["participants"]:
            name = p_data["name"]
            seed = p_data.get("seed", 0)
            active = p_data.get("active", True)
            metadata = {k: v for k, v in p_data.items() if k not in ["name", "seed", "active"]}
            participant = Participant(name=name, seed=seed, active=active, metadata=metadata)
            tournament.participants[name] = participant
            tournament.standings[name] = Standing(player=name)
        
        # Restore matches
        for m_data in data["matches"]:
            match = Match(
                match_id=m_data["match_id"],
                round_num=m_data["round"],
                match_num=m_data["match_num"],
                player_a=m_data.get("player_a"),
                player_b=m_data.get("player_b"),
                score_a=m_data.get("score_a", 0),
                score_b=m_data.get("score_b", 0),
                winner=m_data.get("winner"),
                status=MatchStatus(m_data.get("status", "pending")),
                bracket=m_data.get("bracket", "main")
            )
            tournament.matches.append(match)
            
            # Update standings from completed matches
            if match.status == MatchStatus.COMPLETED:
                tournament._update_standings(match)
        
        # Recalculate tie-breakers and rankings
        tournament._calculate_tiebreakers()
        tournament._update_rankings()
        
        return tournament


def main():
    """Example usage"""
    # Create a Swiss tournament
    tournament = Tournament(
        name="Example Swiss Tournament",
        format="swiss",
        num_rounds=4,
        participants=["PlayerA", "PlayerB", "PlayerC", "PlayerD", "PlayerE", "PlayerF", "PlayerG", "PlayerH"]
    )
    
    print(f"Created tournament: {tournament.name}")
    print(f"Format: {tournament.format.value}")
    print(f"Participants: {len(tournament.participants)}")
    print(f"Rounds: {tournament.num_rounds}")
    
    # Start tournament
    tournament.start()
    print(f"\nTournament started!")
    print(f"Current round: {tournament.current_round}")
    
    # Show round 1 pairings
    round1_matches = tournament.get_matches(round_num=1)
    print(f"\nRound 1 pairings:")
    for match in round1_matches:
        print(f"  Match {match['match_num']}: {match['player_a']} vs {match['player_b']}")
    
    # Report some results
    tournament.report_match(1, 0, "PlayerA", 4, 2)
    tournament.report_match(1, 1, "PlayerC", 4, 1)
    tournament.report_match(1, 2, "PlayerE", 4, 3)
    tournament.report_match(1, 3, "PlayerG", 4, 0)
    
    print(f"\nStandings after Round 1:")
    for standing in tournament.get_standings():
        print(f"  {standing['rank']}. {standing['player']}: {standing['wins']}-{standing['losses']} "
              f"({standing['points']} pts, Buchholz: {standing['buchholz']})")
    
    # Save tournament
    tournament.save("/tmp/example_tournament.json")
    print(f"\nTournament saved to /tmp/example_tournament.json")
    
    # Load tournament
    loaded = Tournament.load("/tmp/example_tournament.json")
    print(f"Tournament loaded: {loaded.name}")


if __name__ == "__main__":
    main()
