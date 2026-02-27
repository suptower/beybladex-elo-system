"""
Advanced Season Statistics & Analytics System

This module implements comprehensive statistics tracking and analytics for the
Beyblade league season. It supports round-level data tracking, advanced
performance metrics, and season awards generation.

Features:
- Round-level data tracking and aggregation
- Basic performance metrics (matches, wins, rounds, points)
- Efficiency metrics (PPR, avg rounds per match)
- Finish-type statistics (burst/pocket/extreme/spin)
- Defensive metrics (bursts suffered, defensive stability)
- Clutch & comeback metrics
- Advanced performance indices (OPI, Dominance Index, Volatility Index)
- Swiss vs Playoff phase separation
- Season awards (auto-generated)
- Tier-based and phase-based filtering
- Leaderboards and per-bey stat profiles
- JSON/CSV export
"""

import csv
import json
import os
import statistics
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass

# Colors for output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# Default paths
DEFAULT_DATA_DIR = "./docs/data"
DEFAULT_MATCHES_FILE = os.path.join(DEFAULT_DATA_DIR, "matches.csv")
DEFAULT_ROUNDS_FILE = os.path.join(DEFAULT_DATA_DIR, "rounds.csv")
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR


@dataclass
class Round:
    """Round entity - represents a single round in a match."""
    round_id: str
    match_id: str
    round_number: int
    bey_a: str
    bey_b: str
    winner: str
    loser: str
    finish_type: str  # BURST, POCKET, EXTREME, SPIN
    points_awarded: int
    round_duration: Optional[float] = None


@dataclass
class Match:
    """Match entity - represents a complete match."""
    match_id: str
    tier: Optional[int]
    phase: str  # Swiss, Playoffs, Placement, Exhibition
    bey_a: str
    bey_b: str
    final_score_a: int
    final_score_b: int
    winner: str
    total_rounds: int
    timestamp: str
    season_id: Optional[str] = None


class BeySeasonStats:
    """Container for all statistics for a single Bey in a season."""

    def __init__(self, bey_name: str):
        self.bey_name = bey_name

        # Basic Performance Metrics
        self.matches_played = 0
        self.matches_won = 0
        self.matches_lost = 0
        self.total_points_scored = 0
        self.total_points_conceded = 0
        self.total_rounds_played = 0
        self.rounds_won = 0
        self.rounds_lost = 0

        # Finish-Type Statistics
        self.burst_wins = 0
        self.pocket_wins = 0
        self.extreme_wins = 0
        self.spin_wins = 0

        self.burst_losses = 0
        self.pocket_losses = 0
        self.extreme_losses = 0
        self.spin_losses = 0

        # Clutch & Comeback Metrics
        self.clutch_matches_won = 0  # Won at 2-2 or in final deciding round
        self.comeback_wins = 0  # Won after being down 0-1 or 0-2
        self.reverse_sweeps = 0  # Won 3-2 after being down 0-2

        # Raw data for variance calculation
        self.points_per_match = []
        self.round_diff_per_match = []

    @property
    def match_win_rate(self) -> float:
        """Calculate match win rate percentage."""
        if self.matches_played == 0:
            return 0.0
        return (self.matches_won / self.matches_played) * 100

    @property
    def points_differential(self) -> int:
        """Calculate points differential."""
        return self.total_points_scored - self.total_points_conceded

    @property
    def round_differential(self) -> int:
        """Calculate round differential."""
        return self.rounds_won - self.rounds_lost

    @property
    def points_per_round(self) -> float:
        """Calculate Points Per Round (PPR)."""
        if self.total_rounds_played == 0:
            return 0.0
        return self.total_points_scored / self.total_rounds_played

    @property
    def avg_rounds_per_match(self) -> float:
        """Calculate average rounds per match."""
        if self.matches_played == 0:
            return 0.0
        return self.total_rounds_played / self.matches_played

    @property
    def avg_points_per_match(self) -> float:
        """Calculate average points scored per match."""
        if self.matches_played == 0:
            return 0.0
        return self.total_points_scored / self.matches_played

    @property
    def total_finishes(self) -> int:
        """Calculate total finishes."""
        return self.burst_wins + self.pocket_wins + self.extreme_wins + self.spin_wins

    @property
    def burst_win_rate(self) -> float:
        """Calculate burst win rate as percentage of total wins."""
        if self.rounds_won == 0:
            return 0.0
        return (self.burst_wins / self.rounds_won) * 100

    @property
    def aggression_ratio(self) -> float:
        """Calculate aggression ratio: (Extreme + Pocket + Burst) / Total Wins."""
        if self.rounds_won == 0:
            return 0.0
        aggressive_wins = self.extreme_wins + self.pocket_wins + self.burst_wins
        return (aggressive_wins / self.rounds_won) * 100

    @property
    def defensive_stability_index(self) -> float:
        """Calculate defensive stability index: 1 - (Bursts Suffered / Total Rounds)."""
        if self.total_rounds_played == 0:
            return 1.0
        return 1.0 - (self.burst_losses / self.total_rounds_played)

    @property
    def clutch_win_rate(self) -> float:
        """Calculate clutch win rate."""
        if self.matches_played == 0:
            return 0.0
        return (self.clutch_matches_won / self.matches_played) * 100

    @property
    def offensive_power_index(self) -> float:
        """
        Calculate Offensive Power Index (OPI).
        Weighted finish scoring: Burst=3, Extreme=2.5, Pocket=2, Spin=1
        OPI = (3×Burst + 2.5×Extreme + 2×Pocket + 1×Spin) / Matches Played
        """
        if self.matches_played == 0:
            return 0.0

        weighted_score = (
            3 * self.burst_wins +
            2.5 * self.extreme_wins +
            2 * self.pocket_wins +
            1 * self.spin_wins
        )
        return weighted_score / self.matches_played

    @property
    def dominance_index(self, ppr_weight: float = 1.5) -> float:
        """
        Calculate Dominance Index.
        Dominance Index = (Points Differential per Match) + (PPR × Weight)
        """
        if self.matches_played == 0:
            return 0.0

        points_diff_per_match = self.points_differential / self.matches_played
        return points_diff_per_match + (self.points_per_round * ppr_weight)

    @property
    def volatility_index(self) -> float:
        """
        Calculate Volatility Index.
        Standard deviation of points scored per match.
        """
        if len(self.points_per_match) <= 1:
            return 0.0
        return statistics.stdev(self.points_per_match)

    def to_dict(self) -> Dict:
        """Convert stats to dictionary for export."""
        return {
            "bey_name": self.bey_name,

            # Basic Performance
            "matches_played": self.matches_played,
            "matches_won": self.matches_won,
            "matches_lost": self.matches_lost,
            "match_win_rate": round(self.match_win_rate, 2),
            "total_points_scored": self.total_points_scored,
            "total_points_conceded": self.total_points_conceded,
            "points_differential": self.points_differential,
            "total_rounds_played": self.total_rounds_played,
            "rounds_won": self.rounds_won,
            "rounds_lost": self.rounds_lost,
            "round_differential": self.round_differential,

            # Efficiency Metrics
            "points_per_round": round(self.points_per_round, 3),
            "avg_rounds_per_match": round(self.avg_rounds_per_match, 2),
            "avg_points_per_match": round(self.avg_points_per_match, 2),

            # Finish-Type Statistics
            "burst_wins": self.burst_wins,
            "pocket_wins": self.pocket_wins,
            "extreme_wins": self.extreme_wins,
            "spin_wins": self.spin_wins,
            "burst_losses": self.burst_losses,
            "pocket_losses": self.pocket_losses,
            "extreme_losses": self.extreme_losses,
            "spin_losses": self.spin_losses,
            "total_finishes": self.total_finishes,
            "burst_win_rate": round(self.burst_win_rate, 2),
            "aggression_ratio": round(self.aggression_ratio, 2),

            # Defensive Metrics
            "bursts_suffered": self.burst_losses,
            "pocket_outs_suffered": self.pocket_losses,
            "extreme_finishes_suffered": self.extreme_losses,
            "defensive_stability_index": round(self.defensive_stability_index, 3),

            # Clutch & Comeback Metrics
            "clutch_matches_won": self.clutch_matches_won,
            "clutch_win_rate": round(self.clutch_win_rate, 2),
            "comeback_wins": self.comeback_wins,
            "reverse_sweeps": self.reverse_sweeps,

            # Advanced Indices
            "offensive_power_index": round(self.offensive_power_index, 2),
            "dominance_index": round(self.dominance_index, 2),
            "volatility_index": round(self.volatility_index, 2),
        }


class SeasonStatistics:
    """Main class for computing and managing season statistics."""

    def __init__(self, matches_file: str = DEFAULT_MATCHES_FILE,
                 rounds_file: str = DEFAULT_ROUNDS_FILE):
        self.matches_file = matches_file
        self.rounds_file = rounds_file

        # Data storage
        self.matches: List[Match] = []
        self.rounds: List[Round] = []

        # Statistics by phase and tier
        self.stats: Dict[str, Dict[str, BeySeasonStats]] = {
            "all": {},      # All matches combined
            "swiss": {},    # Regular season (Swiss) only
            "playoffs": {},  # Playoffs only
        }

    def load_data(self, season_id: Optional[str] = None,
                  tier: Optional[int] = None) -> None:
        """
        Load matches and rounds data from CSV files.

        Args:
            season_id: Optional season filter
            tier: Optional tier filter
        """
        print(f"{YELLOW}Loading match and round data...{RESET}")

        # Load matches
        self.matches = self._load_matches(season_id, tier)
        print(f"{GREEN}Loaded {len(self.matches)} matches{RESET}")

        # Load rounds
        self.rounds = self._load_rounds(self.matches)
        print(f"{GREEN}Loaded {len(self.rounds)} rounds{RESET}")

    def _load_matches(self, season_id: Optional[str] = None,
                      tier: Optional[int] = None) -> List[Match]:
        """Load matches from CSV file with optional filters."""
        matches = []

        if not os.path.exists(self.matches_file):
            print(f"{YELLOW}Warning: Matches file not found: {self.matches_file}{RESET}")
            return matches

        with open(self.matches_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only consider matches with MatchType = "season"
                match_type = row.get("MatchType", "").lower()
                if match_type != "season":
                    continue

                # Apply filters
                if season_id and row.get("SeasonID") != season_id:
                    continue
                if tier is not None and row.get("Tier"):
                    if int(row.get("Tier", 0)) != tier:
                        continue

                # Season matches are Swiss phase
                phase = "Swiss"

                # Determine winner
                score_a = int(row.get("ScoreA", 0))
                score_b = int(row.get("ScoreB", 0))
                bey_a = row.get("BeyA", "")
                bey_b = row.get("BeyB", "")
                winner = bey_a if score_a > score_b else bey_b

                match = Match(
                    match_id=row.get("MatchID", ""),
                    tier=int(row.get("Tier")) if row.get("Tier") else None,
                    phase=phase,
                    bey_a=bey_a,
                    bey_b=bey_b,
                    final_score_a=score_a,
                    final_score_b=score_b,
                    winner=winner,
                    total_rounds=score_a + score_b,
                    timestamp=row.get("Date", ""),
                    season_id=row.get("SeasonID")
                )
                matches.append(match)

        return matches

    def _load_rounds(self, matches: List[Match]) -> List[Round]:
        """Load rounds from CSV file, filtered by loaded matches."""
        rounds = []

        if not os.path.exists(self.rounds_file):
            print(f"{YELLOW}Warning: Rounds file not found: {self.rounds_file}{RESET}")
            return rounds

        # Get set of match IDs we care about
        match_ids = {m.match_id for m in matches}

        with open(self.rounds_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_id = row.get("match_id", "")

                # Only load rounds for matches we loaded
                if match_id not in match_ids:
                    continue

                winner = row.get("winner", "")
                finish_type = row.get("finish_type", "spin").upper()
                points = int(row.get("points_awarded", 1))
                round_num = int(row.get("round_number", 0))

                # Determine loser - for now we don't have this in CSV
                # We'll need to infer from match data
                loser = ""  # Will be filled during processing

                round_obj = Round(
                    round_id=f"{match_id}_R{round_num}",
                    match_id=match_id,
                    round_number=round_num,
                    bey_a="",  # Will be filled from match
                    bey_b="",  # Will be filled from match
                    winner=winner,
                    loser=loser,
                    finish_type=finish_type,
                    points_awarded=points,
                    round_duration=None
                )
                rounds.append(round_obj)

        # Fill in bey_a, bey_b, and loser from match data
        match_dict = {m.match_id: m for m in matches}
        for round_obj in rounds:
            if round_obj.match_id in match_dict:
                match = match_dict[round_obj.match_id]
                round_obj.bey_a = match.bey_a
                round_obj.bey_b = match.bey_b
                round_obj.loser = match.bey_a if round_obj.winner == match.bey_b else match.bey_b

        return rounds

    def compute_statistics(self) -> None:
        """Compute all statistics from loaded data."""
        print(f"{CYAN}Computing statistics...{RESET}")

        # Compute for all phases
        self._compute_phase_stats("all", self.matches, self.rounds)

        # Compute for Swiss only (Regular Season)
        swiss_matches = [m for m in self.matches if m.phase == "Swiss"]
        swiss_rounds = [r for r in self.rounds if r.match_id in {m.match_id for m in swiss_matches}]
        self._compute_phase_stats("swiss", swiss_matches, swiss_rounds)

        # Compute for Playoffs only
        playoff_matches = [m for m in self.matches if m.phase == "Playoffs"]
        playoff_rounds = [
            r for r in self.rounds
            if r.match_id in {m.match_id for m in playoff_matches}
        ]
        self._compute_phase_stats("playoffs", playoff_matches, playoff_rounds)

        print(f"{GREEN}Statistics computed successfully{RESET}")

    def _compute_phase_stats(self, phase: str, matches: List[Match], rounds: List[Round]) -> None:
        """Compute statistics for a specific phase."""
        stats_dict = {}

        # Group rounds by match
        rounds_by_match = defaultdict(list)
        for r in rounds:
            rounds_by_match[r.match_id].append(r)

        # Process each match
        for match in matches:
            match_rounds = rounds_by_match[match.match_id]

            # Initialize stats for both beys if needed
            for bey in [match.bey_a, match.bey_b]:
                if bey not in stats_dict:
                    stats_dict[bey] = BeySeasonStats(bey)

            stats_a = stats_dict[match.bey_a]
            stats_b = stats_dict[match.bey_b]

            # Update basic match stats
            stats_a.matches_played += 1
            stats_b.matches_played += 1

            stats_a.total_points_scored += match.final_score_a
            stats_a.total_points_conceded += match.final_score_b
            stats_b.total_points_scored += match.final_score_b
            stats_b.total_points_conceded += match.final_score_a

            if match.winner == match.bey_a:
                stats_a.matches_won += 1
                stats_b.matches_lost += 1
            else:
                stats_b.matches_won += 1
                stats_a.matches_lost += 1

            # Track points per match for volatility
            stats_a.points_per_match.append(match.final_score_a)
            stats_b.points_per_match.append(match.final_score_b)

            # Process rounds for detailed stats
            rounds_won_a = 0
            rounds_won_b = 0

            for round_obj in match_rounds:
                # Update round counts
                if round_obj.winner == match.bey_a:
                    stats_a.rounds_won += 1
                    stats_b.rounds_lost += 1
                    rounds_won_a += 1
                else:
                    stats_b.rounds_won += 1
                    stats_a.rounds_lost += 1
                    rounds_won_b += 1

                stats_a.total_rounds_played += 1
                stats_b.total_rounds_played += 1

                # Update finish type stats
                finish = round_obj.finish_type.upper()
                if round_obj.winner == match.bey_a:
                    # A wins this round
                    if finish == "BURST":
                        stats_a.burst_wins += 1
                        stats_b.burst_losses += 1
                    elif finish == "POCKET":
                        stats_a.pocket_wins += 1
                        stats_b.pocket_losses += 1
                    elif finish == "EXTREME":
                        stats_a.extreme_wins += 1
                        stats_b.extreme_losses += 1
                    elif finish == "SPIN":
                        stats_a.spin_wins += 1
                        stats_b.spin_losses += 1
                else:
                    # B wins this round
                    if finish == "BURST":
                        stats_b.burst_wins += 1
                        stats_a.burst_losses += 1
                    elif finish == "POCKET":
                        stats_b.pocket_wins += 1
                        stats_a.pocket_losses += 1
                    elif finish == "EXTREME":
                        stats_b.extreme_wins += 1
                        stats_a.extreme_losses += 1
                    elif finish == "SPIN":
                        stats_b.spin_wins += 1
                        stats_a.spin_losses += 1

            # Clutch and comeback detection
            self._detect_clutch_and_comebacks(match, match_rounds, stats_a, stats_b)

            # Track round differential per match
            stats_a.round_diff_per_match.append(rounds_won_a - rounds_won_b)
            stats_b.round_diff_per_match.append(rounds_won_b - rounds_won_a)

        self.stats[phase] = stats_dict

    def _detect_clutch_and_comebacks(
            self, match: Match, rounds: List[Round],
            stats_a: BeySeasonStats, stats_b: BeySeasonStats) -> None:
        """Detect clutch wins and comebacks."""
        if not rounds:
            return

        # Track score progression
        score_a, score_b = 0, 0
        score_history = [(0, 0)]

        for round_obj in sorted(rounds, key=lambda r: r.round_number):
            if round_obj.winner == match.bey_a:
                score_a += round_obj.points_awarded
            else:
                score_b += round_obj.points_awarded
            score_history.append((score_a, score_b))

        # Check if match was won at 2-2 or in a deciding final round
        # (Clutch match)
        final_score_a = match.final_score_a
        final_score_b = match.final_score_b

        # Common winning scores: 3-2, 4-2, 4-3, etc.
        # Clutch if the losing side had a chance to tie or win
        if match.winner == match.bey_a:
            if final_score_b >= final_score_a - 1:  # Close match
                stats_a.clutch_matches_won += 1
        else:
            if final_score_a >= final_score_b - 1:  # Close match
                stats_b.clutch_matches_won += 1

        # Detect comeback wins (won after being down 0-1 or 0-2)
        # Look at score after first 1-2 rounds
        if len(score_history) >= 2:
            early_score_a, early_score_b = score_history[1]
            if match.winner == match.bey_a and early_score_a < early_score_b:
                stats_a.comeback_wins += 1
            elif match.winner == match.bey_b and early_score_b < early_score_a:
                stats_b.comeback_wins += 1

        # Detect reverse sweeps (won 3+ after being down 0-2)
        if len(score_history) >= 3:
            # Check if down 0-2 at some point
            was_down_0_2_a = False
            was_down_0_2_b = False

            for i in range(len(score_history)):
                sa, sb = score_history[i]
                if sa == 0 and sb >= 2:
                    was_down_0_2_a = True
                if sb == 0 and sa >= 2:
                    was_down_0_2_b = True

            if match.winner == match.bey_a and was_down_0_2_a and final_score_a >= 3:
                stats_a.reverse_sweeps += 1
            elif match.winner == match.bey_b and was_down_0_2_b and final_score_b >= 3:
                stats_b.reverse_sweeps += 1

    def generate_leaderboards(self, phase: str = "all") -> Dict[str, List[Dict]]:
        """
        Generate leaderboards for various metrics.

        Args:
            phase: "all", "swiss", or "playoffs"

        Returns:
            Dictionary of leaderboards by metric
        """
        if phase not in self.stats:
            return {}

        stats_list = list(self.stats[phase].values())

        leaderboards = {
            "match_win_rate": sorted(stats_list, key=lambda s: s.match_win_rate, reverse=True),
            "points_differential": sorted(
                stats_list, key=lambda s: s.points_differential, reverse=True
            ),
            "round_differential": sorted(
                stats_list, key=lambda s: s.round_differential, reverse=True
            ),
            "offensive_power_index": sorted(
                stats_list, key=lambda s: s.offensive_power_index, reverse=True
            ),
            "dominance_index": sorted(stats_list, key=lambda s: s.dominance_index, reverse=True),
            "points_per_round": sorted(stats_list, key=lambda s: s.points_per_round, reverse=True),
            "aggression_ratio": sorted(stats_list, key=lambda s: s.aggression_ratio, reverse=True),
            "defensive_stability": sorted(
                stats_list, key=lambda s: s.defensive_stability_index,
                reverse=True
            ),
            "clutch_win_rate": sorted(stats_list, key=lambda s: s.clutch_win_rate, reverse=True),
            "volatility": sorted(stats_list, key=lambda s: s.volatility_index),  # Lower is better
        }

        return leaderboards

    def generate_awards(self, phase: str = "all", min_matches: int = 5) -> Dict[str, Dict]:
        """
        Generate season awards based on statistics.

        Args:
            phase: "all", "swiss", or "playoffs"
            min_matches: Minimum matches required for award eligibility

        Returns:
            Dictionary of awards with winners and their stats
        """
        if phase not in self.stats:
            return {}

        # Filter by minimum matches
        eligible_beys = [s for s in self.stats[phase].values() if s.matches_played >= min_matches]

        if not eligible_beys:
            return {}

        awards = {}

        # Most Dominant Bey (Highest Dominance Index)
        if eligible_beys:
            winner = max(eligible_beys, key=lambda s: s.dominance_index)
            awards["most_dominant"] = {
                "title": "Most Dominant Bey",
                "icon": "🏆",
                "winner": winner.bey_name,
                "value": round(winner.dominance_index, 2),
                "metric": "Dominance Index"
            }

        # Burst King (Most Burst Wins)
        burst_eligible = [s for s in eligible_beys if s.burst_wins > 0]
        if burst_eligible:
            winner = max(burst_eligible, key=lambda s: s.burst_wins)
            awards["burst_king"] = {
                "title": "Burst King",
                "icon": "💥",
                "winner": winner.bey_name,
                "value": winner.burst_wins,
                "metric": "Burst Wins"
            }

        # Stamina Master (Most Spin Wins)
        spin_eligible = [s for s in eligible_beys if s.spin_wins > 0]
        if spin_eligible:
            winner = max(spin_eligible, key=lambda s: s.spin_wins)
            awards["stamina_master"] = {
                "title": "Stamina Master",
                "icon": "🌀",
                "winner": winner.bey_name,
                "value": winner.spin_wins,
                "metric": "Spin Wins"
            }

        # Aggression Award (Highest Aggression Ratio)
        aggression_eligible = [s for s in eligible_beys if s.aggression_ratio > 0]
        if aggression_eligible:
            winner = max(aggression_eligible, key=lambda s: s.aggression_ratio)
            awards["aggression_award"] = {
                "title": "Aggression Award",
                "icon": "🔥",
                "winner": winner.bey_name,
                "value": round(winner.aggression_ratio, 2),
                "metric": "Aggression Ratio %"
            }

        # Iron Wall (Fewest Bursts Suffered per match)
        if eligible_beys:
            winner = min(eligible_beys, key=lambda s: s.burst_losses / max(s.matches_played, 1))
            awards["iron_wall"] = {
                "title": "Iron Wall",
                "icon": "🛡",
                "winner": winner.bey_name,
                "value": round(winner.burst_losses / winner.matches_played, 2),
                "metric": "Bursts Suffered per Match"
            }

        # Efficiency Award (Highest PPR)
        ppr_eligible = [s for s in eligible_beys if s.points_per_round > 0]
        if ppr_eligible:
            winner = max(ppr_eligible, key=lambda s: s.points_per_round)
            awards["efficiency_award"] = {
                "title": "Efficiency Award",
                "icon": "⚡",
                "winner": winner.bey_name,
                "value": round(winner.points_per_round, 3),
                "metric": "Points Per Round"
            }

        # Clutch Performer (Highest Clutch Win Rate)
        clutch_eligible = [s for s in eligible_beys if s.clutch_matches_won > 0]
        if clutch_eligible:
            winner = max(clutch_eligible, key=lambda s: s.clutch_win_rate)
            awards["clutch_performer"] = {
                "title": "Clutch Performer",
                "icon": "🧠",
                "winner": winner.bey_name,
                "value": round(winner.clutch_win_rate, 2),
                "metric": "Clutch Win Rate %"
            }

        # Statistical Leaders

        # Highest Match Win Rate
        if eligible_beys:
            winner = max(eligible_beys, key=lambda s: s.match_win_rate)
            awards["highest_win_rate"] = {
                "title": "Highest Match Win Rate",
                "icon": "📊",
                "winner": winner.bey_name,
                "value": round(winner.match_win_rate, 2),
                "metric": "Match Win Rate %"
            }

        # Best Points Differential
        if eligible_beys:
            winner = max(eligible_beys, key=lambda s: s.points_differential)
            awards["best_point_diff"] = {
                "title": "Best Points Differential",
                "icon": "📈",
                "winner": winner.bey_name,
                "value": winner.points_differential,
                "metric": "Points Differential"
            }

        # Best Round Differential
        if eligible_beys:
            winner = max(eligible_beys, key=lambda s: s.round_differential)
            awards["best_round_diff"] = {
                "title": "Best Round Differential",
                "icon": "🎯",
                "winner": winner.bey_name,
                "value": winner.round_differential,
                "metric": "Round Differential"
            }

        # Highest Offensive Power Index
        if eligible_beys:
            winner = max(eligible_beys, key=lambda s: s.offensive_power_index)
            awards["highest_opi"] = {
                "title": "Highest Offensive Power Index",
                "icon": "⚔️",
                "winner": winner.bey_name,
                "value": round(winner.offensive_power_index, 2),
                "metric": "Offensive Power Index"
            }

        # Most Consistent (Lowest Volatility)
        volatility_eligible = [s for s in eligible_beys if len(s.points_per_match) > 1]
        if volatility_eligible:
            winner = min(volatility_eligible, key=lambda s: s.volatility_index)
            awards["most_consistent"] = {
                "title": "Most Consistent",
                "icon": "📐",
                "winner": winner.bey_name,
                "value": round(winner.volatility_index, 2),
                "metric": "Volatility Index (lower is better)"
            }

        return awards

    def export_to_json(self, output_file: str, phase: str = "all",
                       include_awards: bool = True, min_matches: int = 5) -> None:
        """
        Export statistics to JSON file.

        Args:
            output_file: Output file path
            phase: "all", "swiss", or "playoffs"
            include_awards: Whether to include awards
            min_matches: Minimum matches for award eligibility
        """
        if phase not in self.stats:
            print(f"{YELLOW}No stats found for phase: {phase}{RESET}")
            return

        data = {
            "phase": phase,
            "statistics": {bey: stats.to_dict() for bey, stats in self.stats[phase].items()},
            "leaderboards": {},
            "awards": {}
        }

        # Generate leaderboards
        leaderboards = self.generate_leaderboards(phase)
        # Map leaderboard keys to property names
        metric_map = {
            "match_win_rate": "match_win_rate",
            "points_differential": "points_differential",
            "round_differential": "round_differential",
            "offensive_power_index": "offensive_power_index",
            "dominance_index": "dominance_index",
            "points_per_round": "points_per_round",
            "aggression_ratio": "aggression_ratio",
            "defensive_stability": "defensive_stability_index",
            "clutch_win_rate": "clutch_win_rate",
            "volatility": "volatility_index",
        }
        for metric, leaders in leaderboards.items():
            prop_name = metric_map.get(metric, metric)
            data["leaderboards"][metric] = [
                {
                    "rank": i + 1,
                    "bey": s.bey_name,
                    "value": round(getattr(s, prop_name), 3)
                    if isinstance(getattr(s, prop_name), float)
                    else getattr(s, prop_name)
                }
                for i, s in enumerate(leaders[:10])  # Top 10
            ]

        # Generate awards if requested
        if include_awards:
            data["awards"] = self.generate_awards(phase, min_matches=min_matches)

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"{GREEN}Exported statistics to {output_file}{RESET}")

    def export_to_csv(self, output_file: str, phase: str = "all") -> None:
        """
        Export statistics to CSV file.

        Args:
            output_file: Output file path
            phase: "all", "swiss", or "playoffs"
        """
        if phase not in self.stats:
            print(f"{YELLOW}No stats found for phase: {phase}{RESET}")
            return

        # Get all stats as dicts
        stats_dicts = [stats.to_dict() for stats in self.stats[phase].values()]

        if not stats_dicts:
            print(f"{YELLOW}No statistics to export{RESET}")
            return

        # Sort by dominance index
        stats_dicts.sort(key=lambda x: x["dominance_index"], reverse=True)

        # Write CSV
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=stats_dicts[0].keys())
            writer.writeheader()
            writer.writerows(stats_dicts)

        print(f"{GREEN}Exported statistics to {output_file}{RESET}")


def main():
    """Main entry point for season statistics generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate advanced season statistics")
    parser.add_argument("--season", type=str, help="Filter by season ID")
    parser.add_argument("--tier", type=int, help="Filter by tier")
    parser.add_argument("--phase", type=str, default="all",
                        choices=["all", "swiss", "playoffs"],
                        help="Phase to generate statistics for")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for generated files")
    parser.add_argument("--min-matches", type=int, default=5,
                        help="Minimum matches for award eligibility")

    args = parser.parse_args()

    print(f"{BOLD}{CYAN}Advanced Season Statistics Generator{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    # Initialize statistics engine
    stats = SeasonStatistics()

    # Load data
    stats.load_data(season_id=args.season, tier=args.tier)

    if not stats.matches:
        print(f"{YELLOW}No matches found{RESET}")
        return

    # Compute statistics
    stats.compute_statistics()

    # Export statistics
    phase_suffix = f"_{args.phase}" if args.phase != "all" else ""
    season_suffix = f"_{args.season}" if args.season else ""
    tier_suffix = f"_tier{args.tier}" if args.tier else ""

    # Export JSON
    json_file = os.path.join(
        args.output_dir,
        f"season_statistics{season_suffix}{tier_suffix}{phase_suffix}.json"
    )
    stats.export_to_json(
        json_file, phase=args.phase, include_awards=True,
        min_matches=args.min_matches
    )

    # Export CSV
    csv_file = os.path.join(
        args.output_dir,
        f"season_statistics{season_suffix}{tier_suffix}{phase_suffix}.csv"
    )
    stats.export_to_csv(csv_file, phase=args.phase)

    # Display awards
    print(f"\n{BOLD}{CYAN}Season Awards ({args.phase.upper()}){RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}\n")

    awards = stats.generate_awards(phase=args.phase, min_matches=args.min_matches)
    for award_key, award in awards.items():
        award_text = (
            f"{award['icon']} {BOLD}{award['title']}{RESET}: "
            f"{award['winner']} ({award['value']} {award['metric']})"
        )
        print(award_text)

    print(f"\n{GREEN}{BOLD}Season statistics generated successfully!{RESET}")

    # When called without --season, also generate per-season files for each
    # unique season found in the data, so the frontend can load season-specific
    # statistics (e.g. season_statistics_S1.json).
    if not args.season and not args.tier:
        season_ids = sorted({m.season_id for m in stats.matches if m.season_id})
        if season_ids:
            print(f"\n{CYAN}Generating per-season files: {', '.join(season_ids)}{RESET}")
            for season_id in season_ids:
                per_season_stats = SeasonStatistics()
                per_season_stats.load_data(season_id=season_id)
                if not per_season_stats.matches:
                    continue
                per_season_stats.compute_statistics()
                json_out = os.path.join(
                    args.output_dir,
                    f"season_statistics_{season_id}{phase_suffix}.json"
                )
                csv_out = os.path.join(
                    args.output_dir,
                    f"season_statistics_{season_id}{phase_suffix}.csv"
                )
                per_season_stats.export_to_json(
                    json_out, phase=args.phase, include_awards=True,
                    min_matches=args.min_matches
                )
                per_season_stats.export_to_csv(csv_out, phase=args.phase)
                print(f"  {GREEN}✓{RESET} {season_id}: {json_out}")


if __name__ == "__main__":
    main()
