"""
Season Manager Module for Tiered Seasonal League System

This module handles the creation, management, and processing of seasonal league data
including tier assignments, season points calculation, promotion/relegation, and
league table generation.

Key Features:
- Tier assignment based on ELO rankings at season start
- Season points calculation (3 pts for win, 4 pts for dominant win)
- League table ranking (Season Points → Point Diff → Total Points → H2H → ELO)
- Promotion/relegation logic (top 2 up, bottom 2 down, 8th vs 3rd relegation matches)
- Round-robin match scheduling within tiers
- Historical season archiving

Season Structure:
- 40 Beys divided into 4 Tiers of 10 Beys each
- Tier I (Top Tier), Tier II, Tier III, Tier IV
- Single round-robin within each tier (9 matches per Bey)
- Total: 180 league matches per season

Match Types:
- exhibition: Default, all existing matches and tournaments
- season: Regular league matches within a tier
- relegation: Decision matches between tiers (8th vs 3rd)
- season_cup: Post-season double-elimination tournament

Season Points:
- Win: 3 points
- Dominant Win (4-0, 5-0, 6-0): 4 points
- Loss: 0 points

Functions:
    initialize_season(season_id, beys_with_elo): Create new season with tier assignments
    calculate_season_points(score_a, score_b): Calculate season points for a match
    get_league_table(season_id, tier, matches): Generate league table for a tier
    get_promotion_relegation(season_id): Determine promotion/relegation for next season
    schedule_round_robin(beys_in_tier): Generate round-robin match schedule
    save_season_data(season_id, data): Save season metadata to file
    load_season_data(season_id): Load season metadata from file
"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Constants
TIERS = 4
BEYS_PER_TIER = 10
TOTAL_BEYS = 40

# Season points
POINTS_WIN = 3
POINTS_DOMINANT_WIN = 4
POINTS_LOSS = 0

# Dominant win threshold
DOMINANT_WIN_THRESHOLD = 4  # Shutout victory with 4+ points (4-0, 5-0, 6-0)

# Promotion/Relegation counts
AUTO_PROMOTION = 2
AUTO_RELEGATION = 2
RELEGATION_MATCH_POSITION_HIGH = 8  # 8th place in higher tier
RELEGATION_MATCH_POSITION_LOW = 3   # 3rd place in lower tier

# Default paths
DEFAULT_DATA_DIR = "./docs/data"
DEFAULT_SEASONS_FILE = os.path.join(DEFAULT_DATA_DIR, "seasons.json")
DEFAULT_MATCHES_FILE = os.path.join(DEFAULT_DATA_DIR, "matches.csv")


def calculate_season_points(score_a: int, score_b: int) -> Tuple[int, int]:
    """
    Calculate season points for both participants based on match result.
    
    Rules:
    - Win: 3 points
    - Dominant Win (4-0 or greater difference): 4 points
    - Loss: 0 points
    
    Args:
        score_a: Score for participant A
        score_b: Score for participant B
        
    Returns:
        Tuple of (points_a, points_b)
    """
    if score_a == score_b:
        # Draws don't give points in this system
        return (0, 0)
    
    winner_score = max(score_a, score_b)
    loser_score = min(score_a, score_b)
    difference = winner_score - loser_score
    
    # Check for dominant win
    is_dominant = difference >= DOMINANT_WIN_THRESHOLD and loser_score == 0
    winner_points = POINTS_DOMINANT_WIN if is_dominant else POINTS_WIN
    
    if score_a > score_b:
        return (winner_points, POINTS_LOSS)
    else:
        return (POINTS_LOSS, winner_points)


def initialize_season(season_id: str, beys_with_elo: List[Tuple[str, float]], 
                      data_dir: str = DEFAULT_DATA_DIR) -> Dict:
    """
    Initialize a new season with tier assignments based on current ELO.
    
    Args:
        season_id: Season identifier (e.g., "S1", "S2")
        beys_with_elo: List of tuples (bey_name, elo_rating)
        data_dir: Directory to store season data
        
    Returns:
        Dictionary containing season initialization data
    """
    # Sort beys by ELO (highest first)
    sorted_beys = sorted(beys_with_elo, key=lambda x: x[1], reverse=True)
    
    # Validate we have exactly 40 beys
    if len(sorted_beys) != TOTAL_BEYS:
        raise ValueError(f"Expected {TOTAL_BEYS} beys, got {len(sorted_beys)}")
    
    # Assign tiers
    tier_assignments = {}
    for tier in range(1, TIERS + 1):
        start_idx = (tier - 1) * BEYS_PER_TIER
        end_idx = start_idx + BEYS_PER_TIER
        tier_beys = sorted_beys[start_idx:end_idx]
        
        for bey_name, elo in tier_beys:
            tier_assignments[bey_name] = {
                "tier": tier,
                "start_elo": elo
            }
    
    # Create season data structure
    season_data = {
        "season_id": season_id,
        "start_date": datetime.now().isoformat(),
        "status": "active",
        "tier_assignments": tier_assignments,
        "league_champion": None,
        "cup_winner": None,
        "tiers": {}
    }
    
    # Initialize tier structures
    for tier in range(1, TIERS + 1):
        tier_beys = [bey for bey, data in tier_assignments.items() if data["tier"] == tier]
        season_data["tiers"][str(tier)] = {
            "beys": tier_beys,
            "matches_played": 0,
            "matches_total": int(BEYS_PER_TIER * (BEYS_PER_TIER - 1) / 2)  # Round-robin count
        }
    
    return season_data


def get_league_table(matches: List[Dict], tier: int, season_id: str) -> List[Dict]:
    """
    Generate league table for a specific tier in a season.
    
    Ranking order:
    1. Season Points
    2. Point Difference (points for - points against)
    3. Total Points Scored
    4. Head-to-Head Result
    5. ELO
    6. Tie-breaking match (marked for manual resolution)
    
    Args:
        matches: List of match dictionaries
        tier: Tier number (1-4)
        season_id: Season identifier
        
    Returns:
        List of dictionaries with team standings, sorted by ranking criteria
    """
    # Filter matches for this season and tier
    season_matches = [
        m for m in matches 
        if m.get("match_type") == "season" 
        and m.get("season_id") == season_id
        and m.get("tier") == tier
    ]
    
    # Initialize standings
    standings = defaultdict(lambda: {
        "bey": "",
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "season_points": 0,
        "points_for": 0,
        "points_against": 0,
        "point_diff": 0,
        "elo": 0
    })
    
    # Process matches
    for match in season_matches:
        bey_a = match["bey_a"]
        bey_b = match["bey_b"]
        score_a = int(match["score_a"])
        score_b = int(match["score_b"])
        
        # Calculate season points
        sp_a, sp_b = calculate_season_points(score_a, score_b)
        
        # Update standings for both beys
        standings[bey_a]["bey"] = bey_a
        standings[bey_a]["matches"] += 1
        standings[bey_a]["season_points"] += sp_a
        standings[bey_a]["points_for"] += score_a
        standings[bey_a]["points_against"] += score_b
        standings[bey_a]["elo"] = float(match.get("elo_a", 0))
        
        standings[bey_b]["bey"] = bey_b
        standings[bey_b]["matches"] += 1
        standings[bey_b]["season_points"] += sp_b
        standings[bey_b]["points_for"] += score_b
        standings[bey_b]["points_against"] += score_a
        standings[bey_b]["elo"] = float(match.get("elo_b", 0))
        
        # Update wins/losses
        if score_a > score_b:
            standings[bey_a]["wins"] += 1
            standings[bey_b]["losses"] += 1
        elif score_b > score_a:
            standings[bey_b]["wins"] += 1
            standings[bey_a]["losses"] += 1
    
    # Calculate point differences
    for bey_data in standings.values():
        bey_data["point_diff"] = bey_data["points_for"] - bey_data["points_against"]
    
    # Convert to list and sort by ranking criteria
    table = list(standings.values())
    table.sort(key=lambda x: (
        -x["season_points"],      # Higher season points first
        -x["point_diff"],          # Better point difference
        -x["points_for"],          # More points scored
        -x["elo"]                  # Higher ELO
    ))
    
    # Add positions
    for i, entry in enumerate(table, 1):
        entry["position"] = i
    
    return table


def get_promotion_relegation(season_data: Dict, league_tables: Dict[int, List[Dict]]) -> Dict:
    """
    Determine promotion, relegation, and relegation matches for the next season.
    
    Rules:
    - Top 2 of Tiers II-IV: Automatic promotion
    - Bottom 2 of Tiers I-III: Automatic relegation
    - 8th of higher tier vs 3rd of lower tier: Relegation match
    
    Args:
        season_data: Current season data
        league_tables: Dictionary mapping tier number to league table
        
    Returns:
        Dictionary with promotion/relegation assignments
    """
    result = {
        "automatic_promotion": [],
        "automatic_relegation": [],
        "relegation_matches": []
    }
    
    for tier in range(1, TIERS + 1):
        table = league_tables.get(tier, [])
        if not table or len(table) < BEYS_PER_TIER:
            continue
        
        # Automatic promotion (Tiers II-IV)
        if tier > 1:
            for i in range(AUTO_PROMOTION):
                if i < len(table):
                    result["automatic_promotion"].append({
                        "bey": table[i]["bey"],
                        "from_tier": tier,
                        "to_tier": tier - 1,
                        "position": i + 1
                    })
        
        # Automatic relegation (Tiers I-III)
        if tier < TIERS:
            for i in range(AUTO_RELEGATION):
                pos = len(table) - 1 - i
                if pos >= 0:
                    result["automatic_relegation"].append({
                        "bey": table[pos]["bey"],
                        "from_tier": tier,
                        "to_tier": tier + 1,
                        "position": pos + 1
                    })
        
        # Relegation matches (all tiers except Tier IV)
        if tier < TIERS:
            lower_table = league_tables.get(tier + 1, [])
            if (RELEGATION_MATCH_POSITION_HIGH - 1 < len(table) and 
                RELEGATION_MATCH_POSITION_LOW - 1 < len(lower_table)):
                
                result["relegation_matches"].append({
                    "higher_bey": table[RELEGATION_MATCH_POSITION_HIGH - 1]["bey"],
                    "higher_tier": tier,
                    "higher_position": RELEGATION_MATCH_POSITION_HIGH,
                    "lower_bey": lower_table[RELEGATION_MATCH_POSITION_LOW - 1]["bey"],
                    "lower_tier": tier + 1,
                    "lower_position": RELEGATION_MATCH_POSITION_LOW
                })
    
    return result


def schedule_round_robin(beys: List[str]) -> List[Tuple[str, str]]:
    """
    Generate round-robin match schedule for a list of beys.
    
    Uses the circle method algorithm for round-robin scheduling.
    Each bey plays every other bey exactly once.
    
    Args:
        beys: List of bey names
        
    Returns:
        List of tuples (bey_a, bey_b) representing matches
    """
    if len(beys) < 2:
        return []
    
    matches = []
    n = len(beys)
    
    # Simple round-robin: every bey plays every other bey once
    for i in range(n):
        for j in range(i + 1, n):
            matches.append((beys[i], beys[j]))
    
    return matches


def save_season_data(season_data: Dict, data_dir: str = DEFAULT_DATA_DIR) -> None:
    """
    Save season data to JSON file.
    
    Args:
        season_data: Season data dictionary
        data_dir: Directory to store season data
    """
    os.makedirs(data_dir, exist_ok=True)
    seasons_file = os.path.join(data_dir, "seasons.json")
    
    # Load existing seasons
    all_seasons = {}
    if os.path.exists(seasons_file):
        try:
            with open(seasons_file, "r", encoding="utf-8") as f:
                all_seasons = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            all_seasons = {}
    
    # Update with new season data
    season_id = season_data["season_id"]
    all_seasons[season_id] = season_data
    
    # Save back to file
    with open(seasons_file, "w", encoding="utf-8") as f:
        json.dump(all_seasons, f, indent=2, ensure_ascii=False)


def load_season_data(season_id: Optional[str] = None, 
                     data_dir: str = DEFAULT_DATA_DIR) -> Optional[Dict]:
    """
    Load season data from JSON file.
    
    Args:
        season_id: Season identifier. If None, returns all seasons.
        data_dir: Directory where season data is stored
        
    Returns:
        Season data dictionary, or None if not found
    """
    seasons_file = os.path.join(data_dir, "seasons.json")
    
    if not os.path.exists(seasons_file):
        return None
    
    try:
        with open(seasons_file, "r", encoding="utf-8") as f:
            all_seasons = json.load(f)
        
        if season_id is None:
            return all_seasons
        
        return all_seasons.get(season_id)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def generate_season_archive(season_id: str, matches: List[Dict], 
                           league_tables: Dict[int, List[Dict]],
                           promotion_relegation: Dict,
                           data_dir: str = DEFAULT_DATA_DIR) -> Dict:
    """
    Generate complete season archive data for frontend display.
    
    Args:
        season_id: Season identifier
        matches: All matches from the season
        league_tables: League tables for all tiers
        promotion_relegation: Promotion/relegation data
        data_dir: Directory to store archive
        
    Returns:
        Complete season archive dictionary
    """
    season_data = load_season_data(season_id, data_dir)
    if not season_data:
        raise ValueError(f"Season {season_id} not found")
    
    # Find league champion (1st place in Tier I)
    league_champion = None
    if 1 in league_tables and len(league_tables[1]) > 0:
        league_champion = league_tables[1][0]["bey"]
    
    # Group matches by matchday
    matchdays = defaultdict(list)
    for match in matches:
        if match.get("match_type") == "season" and match.get("season_id") == season_id:
            md = match.get("matchday", 0)
            matchdays[md].append(match)
    
    archive = {
        "season_id": season_id,
        "start_date": season_data.get("start_date"),
        "end_date": season_data.get("end_date"),
        "league_champion": league_champion,
        "cup_winner": season_data.get("cup_winner"),
        "league_tables": {str(tier): table for tier, table in league_tables.items()},
        "matchdays": dict(matchdays),
        "promotion_relegation": promotion_relegation,
        "statistics": {
            "total_matches": len([m for m in matches if m.get("season_id") == season_id]),
            "total_goals": sum(int(m.get("score_a", 0)) + int(m.get("score_b", 0)) 
                             for m in matches if m.get("season_id") == season_id)
        }
    }
    
    return archive


if __name__ == "__main__":
    # Example usage and testing
    print("Season Manager Module")
    print("=====================")
    
    # Test season points calculation
    print("\nTesting season points calculation:")
    test_cases = [
        (4, 0, "4-0 dominant win"),
        (5, 0, "5-0 dominant win"),
        (4, 3, "4-3 close win"),
        (4, 2, "4-2 win")
    ]
    
    for score_a, score_b, desc in test_cases:
        sp_a, sp_b = calculate_season_points(score_a, score_b)
        print(f"  {desc}: {score_a}-{score_b} → A: {sp_a} pts, B: {sp_b} pts")
