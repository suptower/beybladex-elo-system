"""
Season Manager Module for Tiered Seasonal League System

This module handles the creation, management, and processing of seasonal league data
including tier assignments, season points calculation, promotion/relegation, and
league table generation.

Key Features:
- Tier assignment based on ELO rankings at season start
- Season points calculation (3 pts for win, 4 pts for dominant win)
- League table ranking (Season Points → Point Diff → Total Points → H2H → ELO)
- Promotion/relegation logic per Season 2 rules (see get_promotion_relegation)
- Round-robin match scheduling within tiers
- Historical season archiving

Season Structure:
- 32 Beys divided into 4 Tiers of 8 Beys each
- Tier I (Top Tier), Tier II, Tier III, Tier IV (Challengers)
- Single round-robin within each tier (7 matches per Bey)
- Total: 112 league matches per season

Match Types:
- exhibition: Default, all existing matches and tournaments
- season: Regular league matches within a tier
- relegation: Decision matches between tiers (playoff matches)
- qualification: Tier IV entry tournament for unranked Beys
- season_cup: Post-season double-elimination tournament

Qualification System:
- Tier IV positions 5-8 drop into Qualification Pool
- New Beys and unranked Beys compete for Tier IV slots
- Top finishers earn Tier IV slots for next season

Season Points:
- Win: 3 points
- Dominant Win (4-0, 5-0, 6-0): 4 points
- Loss: 0 points

Promotion/Relegation Rules (Season 2+):
- Tier I:   Rank 8 auto-relegated to II; Rank 7 playoff vs II Rank 2
- Tier II:  Rank 1 auto-promoted to I; Ranks 7-8 auto-relegated to III;
            Rank 2 playoff vs I Rank 7; Rank 6 playoff vs III Rank 3
- Tier III: Ranks 1-2 auto-promoted to II; Ranks 7-8 auto-relegated to IV;
            Rank 3 playoff vs II Rank 6; Rank 6 playoff vs IV Rank 3
- Tier IV:  Ranks 1-2 auto-promoted to III; Rank 3 playoff vs III Rank 6;
            Ranks 5-8 drop to qualification pool

Functions:
    initialize_season(season_id, beys_with_elo): Create new season with tier assignments
    calculate_season_points(score_a, score_b): Calculate season points for a match
    get_league_table(season_id, tier, matches): Generate league table for a tier
    get_promotion_relegation(season_id): Determine promotion/relegation for next season
    schedule_round_robin(beys_in_tier): Generate round-robin match schedule
    save_season_data(season_id, data): Save season metadata to file
    load_season_data(season_id): Load season metadata from file
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import sys
import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root
from src.config.paths import SEASON_DIR, MATCHES_CSV  # noqa: E402

# Constants
# Per-season league format configuration.
# This allows legacy seasons (e.g., Season 1 with 3×10 structure) to coexist
# with Season 2+ (4×8) without being affected by global constant changes.
SEASON_FORMATS: Dict[str, Dict[str, int]] = {
    # Legacy Season 1: 3 tiers, 10 Beys per tier, no Tier IV.
    "S1": {
        "tiers": 3,
        "beys_per_tier": 10,
        "total_beys_in_league": 30,
        "rules_version": 1,  # Legacy ruleset
    },
    # Default / Season 2+ format: 4 tiers of 8 Beys each.
    "default": {
        "tiers": 4,
        "beys_per_tier": 8,
        "total_beys_in_league": 32,
        "rules_version": 2,  # Season 2+ ruleset
    },
}

# Backwards-compatible global constants derived from the default (Season 2+)
# format. Existing Season 2+ processing continues to use these values, while
# legacy seasons should query `get_season_format(season_id)` explicitly.
_DEFAULT_FORMAT = SEASON_FORMATS["default"]
TIERS = _DEFAULT_FORMAT["tiers"]
BEYS_PER_TIER = _DEFAULT_FORMAT["beys_per_tier"]
TOTAL_BEYS_IN_LEAGUE = _DEFAULT_FORMAT["total_beys_in_league"]  # Beys in active league (4 tiers)
TOTAL_BEYS = 40  # Total Beys in system (for backward compatibility)


def get_season_format(season_id: Optional[str]) -> Dict[str, int]:
    """
    Return the league format configuration for a given season.

    Args:
        season_id: The season identifier (e.g., "S1", "S2"). If None or
                   unrecognized, the Season 2+ default format is returned.

    Returns:
        A dict with at least:
            - "tiers": number of tiers in the league
            - "beys_per_tier": number of Beys per tier
            - "total_beys_in_league": total Beys participating in league
            - "rules_version": integer indicating ruleset version
    """
    if season_id is None:
        return SEASON_FORMATS["default"]
    return SEASON_FORMATS.get(season_id, SEASON_FORMATS["default"])


# Season points
POINTS_WIN = 3
POINTS_DOMINANT_WIN = 4
POINTS_LOSS = 0

# Dominant win threshold
DOMINANT_WIN_THRESHOLD = 4  # Shutout victory with 4+ points (4-0, 5-0, 6-0)

# Promotion/Relegation counts per tier (Season 2+ format)
# auto_promotions_per_tier: number of automatic promotions FROM each tier
AUTO_PROMOTIONS_PER_TIER = {2: 1, 3: 2, 4: 2}
# auto_relegations_per_tier: number of automatic relegations FROM each tier
AUTO_RELEGATIONS_PER_TIER = {1: 1, 2: 2, 3: 2}
# Playoff positions per tier boundary: (higher_tier_rank, lower_tier_rank)
RELEGATION_PLAYOFF_POSITIONS = {
    1: (7, 2),  # T1 rank 7 vs T2 rank 2
    2: (6, 3),  # T2 rank 6 vs T3 rank 3
    3: (6, 3),  # T3 rank 6 vs T4 rank 3
}
# Kept for backward compatibility
AUTO_PROMOTION = 2
AUTO_RELEGATION = 2
RELEGATION_MATCH_POSITION_HIGH = 7  # 7th place in higher tier (T1/T2 boundary)
RELEGATION_MATCH_POSITION_LOW = 2   # 2nd place in lower tier (T1/T2 boundary)

# Default paths
DEFAULT_DATA_DIR = SEASON_DIR
DEFAULT_SEASONS_FILE = os.path.join(DEFAULT_DATA_DIR, "seasons.json")
DEFAULT_MATCHES_FILE = MATCHES_CSV


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
    season_format = get_season_format(season_id)
    tiers = season_format["tiers"]
    beys_per_tier = season_format["beys_per_tier"]
    total_beys_in_league = season_format["total_beys_in_league"]

    # Sort beys by ELO (highest first)
    sorted_beys = sorted(beys_with_elo, key=lambda x: x[1], reverse=True)

    # Need at least total_beys_in_league beys for the league
    if len(sorted_beys) < total_beys_in_league:
        raise ValueError(f"Expected at least {total_beys_in_league} beys, got {len(sorted_beys)}")

    # Assign tiers
    tier_assignments = {}
    for tier in range(1, tiers + 1):
        start_idx = (tier - 1) * beys_per_tier
        end_idx = start_idx + beys_per_tier
        tier_beys = sorted_beys[start_idx:end_idx]

        for bey_name, elo in tier_beys:
            tier_assignments[bey_name] = {
                "tier": tier,
                "start_elo": elo
            }

    # Remaining beys (beyond league slots) are in qualification pool
    qualification_pool = []
    for bey_name, elo in sorted_beys[total_beys_in_league:]:
        qualification_pool.append({
            "bey": bey_name,
            "elo": elo
        })

    # Create season data structure
    season_data = {
        "season_id": season_id,
        "start_date": datetime.now().isoformat(),
        "status": "active",
        "tier_assignments": tier_assignments,
        "qualification_pool": qualification_pool,
        "league_champion": None,
        "cup_winner": None,
        "tiers": {}
    }

    # Initialize tier structures
    for tier in range(1, tiers + 1):
        tier_beys = [bey for bey, data in tier_assignments.items() if data["tier"] == tier]
        season_data["tiers"][str(tier)] = {
            "beys": tier_beys,
            "matches_played": 0,
            "matches_total": int(beys_per_tier * (beys_per_tier - 1) / 2)  # Round-robin count
        }

    return season_data


def get_league_table(
    matches: List[Dict],
    tier: int,
    season_id: str,
    rounds_data: Optional[Dict[str, List[Dict]]] = None,
) -> List[Dict]:
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
        tier: Tier number (1-3)
        season_id: Season identifier
        rounds_data: Optional mapping of match_id to list of round dicts, each
            with at least {"winner": str, "points_awarded": int}.  When
            provided, per-entry ``irw`` and ``irl`` counts are calculated.

    Returns:
        List of dictionaries with team standings, sorted by ranking criteria.
        Each entry includes irw, irl, ppr, and ppw in addition to existing
        fields (irw/irl are 0 when rounds_data is not supplied).
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
        "elo": 0,
        "irw": 0,
        "irl": 0,
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

        # Update individual round wins/losses from rounds_data
        if rounds_data is not None:
            match_id = match.get("match_id", "")
            for rnd in rounds_data.get(match_id, []):
                winner = rnd.get("winner", "")
                if winner == bey_a:
                    standings[bey_a]["irw"] += 1
                    standings[bey_b]["irl"] += 1
                elif winner == bey_b:
                    standings[bey_b]["irw"] += 1
                    standings[bey_a]["irl"] += 1

    # Calculate point differences and derived per-round/per-win stats
    for bey_data in standings.values():
        bey_data["point_diff"] = bey_data["points_for"] - bey_data["points_against"]
        m = bey_data["matches"]
        w = bey_data["wins"]
        bey_data["ppr"] = round(bey_data["season_points"] / m, 2) if m > 0 else 0.0
        bey_data["ppw"] = round(bey_data["season_points"] / w, 2) if w > 0 else 0.0

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
    Determine promotion, relegation, and relegation playoff matches for the next season.

    The ruleset is selected based on the season format (rules_version):

    Rules v1 (Season 1, 3 tiers of 10):
    - Tiers II-III: Top 2 auto-promoted one tier up
    - Tiers I-II:   Bottom 2 auto-relegated one tier down
    - Tiers I-II:   8th in higher tier playoff vs 3rd in lower tier
    - Tier III:     Positions 7-10 drop to qualification pool

    Rules v2 (Season 2+, 4 tiers of 8):
    - Tier I:   Rank 8 auto-relegated to II; Rank 7 playoff vs II Rank 2
    - Tier II:  Rank 1 auto-promoted to I; Ranks 7-8 auto-relegated to III;
                Rank 2 playoff vs I Rank 7; Rank 6 playoff vs III Rank 3
    - Tier III: Ranks 1-2 auto-promoted to II; Ranks 7-8 auto-relegated to IV;
                Rank 3 playoff vs II Rank 6; Rank 6 playoff vs IV Rank 3
    - Tier IV:  Ranks 1-2 auto-promoted to III; Rank 3 playoff vs III Rank 6;
                Ranks 5-8 drop to qualification pool

    Args:
        season_data: Current season data; if "season_id" is missing or None,
            the default season format is used.
        league_tables: Dictionary mapping tier number to league table

    Returns:
        Dictionary with promotion/relegation assignments
    """
    season_id = season_data.get("season_id")
    season_format = get_season_format(season_id)
    rules_version = season_format["rules_version"]
    tiers_count = season_format["tiers"]
    beys_per_tier = season_format["beys_per_tier"]

    result = {
        "automatic_promotion": [],
        "automatic_relegation": [],
        "relegation_matches": [],
        "qualification_candidates": []
    }

    if rules_version == 1:
        # Legacy Season 1 rules: 3 tiers of 10
        # Auto-promotion: top 2 from tiers 2 and 3
        v1_auto_promotions = {2: 2, 3: 2}
        # Auto-relegation: bottom 2 from tiers 1 and 2
        v1_auto_relegations = {1: 2, 2: 2}
        # Playoff: 8th in higher tier vs 3rd in lower tier
        v1_playoff_positions = {1: (8, 3), 2: (8, 3)}
        # Tier III: positions 7-10 → qualification pool
        # beys_per_tier - 4 = 10 - 4 = 6 (index of position 7 in a 10-bey tier)
        v1_qual_start = beys_per_tier - 4

        for tier in range(1, tiers_count + 1):
            table = league_tables.get(tier, [])
            if not table or len(table) < beys_per_tier:
                continue

            num_promotions = v1_auto_promotions.get(tier, 0)
            for i in range(num_promotions):
                if i < len(table):
                    result["automatic_promotion"].append({
                        "bey": table[i]["bey"],
                        "from_tier": tier,
                        "to_tier": tier - 1,
                        "position": i + 1
                    })

            if tier < tiers_count:
                num_relegations = v1_auto_relegations.get(tier, 0)
                for i in range(num_relegations):
                    pos = len(table) - 1 - i
                    if pos >= 0:
                        result["automatic_relegation"].append({
                            "bey": table[pos]["bey"],
                            "from_tier": tier,
                            "to_tier": tier + 1,
                            "position": pos + 1
                        })

            if tier in v1_playoff_positions and tier < tiers_count:
                higher_rank, lower_rank = v1_playoff_positions[tier]
                lower_table = league_tables.get(tier + 1, [])
                if (higher_rank - 1 < len(table) and
                        lower_rank - 1 < len(lower_table)):
                    result["relegation_matches"].append({
                        "higher_bey": table[higher_rank - 1]["bey"],
                        "higher_tier": tier,
                        "higher_position": higher_rank,
                        "lower_bey": lower_table[lower_rank - 1]["bey"],
                        "lower_tier": tier + 1,
                        "lower_position": lower_rank
                    })

            if tier == tiers_count:
                for i in range(v1_qual_start, len(table)):
                    result["qualification_candidates"].append({
                        "bey": table[i]["bey"],
                        "tier": tier,
                        "position": i + 1,
                        "reason": "tier3_bottom"
                    })

    else:
        # Season 2+ rules: 4 tiers of 8
        for tier in range(1, tiers_count + 1):
            table = league_tables.get(tier, [])
            if not table or len(table) < beys_per_tier:
                continue

            # Automatic promotion from this tier
            num_promotions = AUTO_PROMOTIONS_PER_TIER.get(tier, 0)
            for i in range(num_promotions):
                if i < len(table):
                    result["automatic_promotion"].append({
                        "bey": table[i]["bey"],
                        "from_tier": tier,
                        "to_tier": tier - 1,
                        "position": i + 1
                    })

            # Automatic relegation from this tier (not for Tier IV)
            if tier < tiers_count:
                num_relegations = AUTO_RELEGATIONS_PER_TIER.get(tier, 0)
                for i in range(num_relegations):
                    pos = len(table) - 1 - i
                    if pos >= 0:
                        result["automatic_relegation"].append({
                            "bey": table[pos]["bey"],
                            "from_tier": tier,
                            "to_tier": tier + 1,
                            "position": pos + 1
                        })

            # Relegation playoff matches
            if tier in RELEGATION_PLAYOFF_POSITIONS and tier < tiers_count:
                higher_rank, lower_rank = RELEGATION_PLAYOFF_POSITIONS[tier]
                lower_table = league_tables.get(tier + 1, [])
                if (higher_rank - 1 < len(table) and
                        lower_rank - 1 < len(lower_table)):
                    result["relegation_matches"].append({
                        "higher_bey": table[higher_rank - 1]["bey"],
                        "higher_tier": tier,
                        "higher_position": higher_rank,
                        "lower_bey": lower_table[lower_rank - 1]["bey"],
                        "lower_tier": tier + 1,
                        "lower_position": lower_rank
                    })

            # Bottom half of Tier IV (positions beys_per_tier//2+1 to beys_per_tier) enter Qualification Pool
            if tier == tiers_count:
                for i in range(beys_per_tier // 2, min(beys_per_tier, len(table))):
                    result["qualification_candidates"].append({
                        "bey": table[i]["bey"],
                        "tier": tier,
                        "position": i + 1,
                        "reason": "tier4_bottom"
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


def initialize_season_from_results(
        new_season_id: str,
        prev_tier_assignments: Dict[str, Dict],
        prev_qualification_pool: List[Dict],
        promotion_relegation: Dict,
        elo_lookup: Dict[str, float],
) -> Tuple[Dict, List[str]]:
    """
    Initialize a new season's tier assignments from a completed season's
    promotion/relegation results.

    Automatic promotions and relegations are applied directly.  Beys involved
    in relegation playoff matches are left in their current tier with a
    warning (the user must resolve those matches and adjust manually).
    Vacancies created in Tier IV by qualification candidates dropping to the
    qualification pool are filled in ELO order from the previous season's
    qualification pool only; current-season qualification candidates
    (``qual_out``) are not used to fill these vacancies — they enter the
    qualification tournament to compete for re-entry.

    Args:
        new_season_id: The new season identifier (e.g., "S3").
        prev_tier_assignments: ``tier_assignments`` dict from the previous
            season in ``seasons.json`` — maps bey name to
            ``{"tier": N, "start_elo": ...}``.
        prev_qualification_pool: ``qualification_pool`` list from the
            previous season in ``seasons.json`` — each entry is a dict with
            at least a ``"bey"`` key.
        promotion_relegation: Result dict produced by
            ``get_promotion_relegation()`` (stored in ``season_data.json``
            under ``seasons.<prev_id>.promotion_relegation``).
        elo_lookup: Dict mapping bey name to current ELO rating, used both
            to sort qualification-pool fill-ins and to set ``start_elo`` for
            each tier assignment.

    Returns:
        Tuple of (season_data dict, warnings list).  ``season_data`` has the
        same structure as the output of ``initialize_season()`` and is ready
        to be passed to ``save_season_data()``.  ``warnings`` is a list of
        human-readable strings describing unresolved situations (e.g., pending
        relegation playoffs, vacancies filled from the pool).
    """
    season_format = get_season_format(new_season_id)
    tiers = season_format["tiers"]
    beys_per_tier = season_format["beys_per_tier"]

    warnings: List[str] = []

    # Build mutable tier composition from the previous season.
    # Only include tiers that are valid for the new season format.
    tier_comp: Dict[int, List[str]] = {t: [] for t in range(1, tiers + 1)}
    for bey, data in prev_tier_assignments.items():
        t = data.get("tier", 0)
        if t in tier_comp:
            tier_comp[t].append(bey)

    # Collect relegation-playoff participants — they stay in their current
    # tier until the playoff is resolved manually.
    playoff_beys: set = set()
    for match in promotion_relegation.get("relegation_matches", []):
        playoff_beys.add(match["higher_bey"])
        playoff_beys.add(match["lower_bey"])
    if playoff_beys:
        warnings.append(
            "Relegation playoff participants kept in their current tier "
            "(resolve playoff matches and adjust manually): "
            + ", ".join(sorted(playoff_beys))
        )

    # Apply automatic promotions.
    for move in promotion_relegation.get("automatic_promotion", []):
        bey = move["bey"]
        from_tier = move["from_tier"]
        to_tier = move["to_tier"]
        if bey in tier_comp.get(from_tier, []) and to_tier in tier_comp:
            tier_comp[from_tier].remove(bey)
            tier_comp[to_tier].append(bey)

    # Apply automatic relegations.
    for move in promotion_relegation.get("automatic_relegation", []):
        bey = move["bey"]
        from_tier = move["from_tier"]
        to_tier = move["to_tier"]
        if bey in tier_comp.get(from_tier, []) and to_tier in tier_comp:
            tier_comp[from_tier].remove(bey)
            tier_comp[to_tier].append(bey)

    # Remove qualification candidates from Tier IV — they drop to the pool.
    # These beys will compete in the qualification tournament for re-entry;
    # they do NOT automatically fill their own vacancies.
    qual_out: List[str] = []
    for candidate in promotion_relegation.get("qualification_candidates", []):
        bey = candidate["bey"]
        t = candidate.get("tier", tiers)
        if t in tier_comp and bey in tier_comp[t]:
            tier_comp[t].remove(bey)
            qual_out.append(bey)

    # Build the fill-in pool from the PREVIOUS qualification pool only.
    # Qualification candidates (qual_out) go to the remaining pool to compete
    # in the qualification tournament; they are not auto-placed in any tier.
    in_league: set = {b for beys in tier_comp.values() for b in beys}
    fill_pool_beys: List[str] = []
    # Track ELO stored in the previous pool as a fallback for beys missing
    # from the current leaderboard (elo_lookup).
    fill_pool_elo_fallback: Dict[str, Optional[float]] = {}
    for entry in prev_qualification_pool:
        b = entry.get("bey") or entry.get("name", "")
        if b and b not in in_league and b not in fill_pool_beys:
            fill_pool_beys.append(b)
            fill_pool_elo_fallback[b] = entry.get("elo")

    # Sort fill pool by ELO descending.
    # Prefer the current leaderboard ELO; fall back to the previous pool's
    # stored ELO if the bey is missing from the leaderboard.
    fill_pool_list: List[Tuple[str, float]] = []
    for b in fill_pool_beys:
        elo = elo_lookup.get(b)
        if elo is None:
            fallback = fill_pool_elo_fallback.get(b)
            elo = float(fallback) if fallback is not None else 0.0
        fill_pool_list.append((b, elo))
    fill_pool: List[Tuple[str, float]] = sorted(fill_pool_list, key=lambda x: -x[1])

    # Fill vacancies in the bottom tier only from the qualification pool.
    # Upper tiers are expected to be size-stable via promotions/relegations;
    # placing qualification-pool beys into higher tiers is never correct.
    bottom_tier = tiers
    if bottom_tier in tier_comp:
        while len(tier_comp[bottom_tier]) < beys_per_tier and fill_pool:
            bey, elo = fill_pool.pop(0)
            tier_comp[bottom_tier].append(bey)
            warnings.append(
                f"Tier {bottom_tier} vacancy filled from qualification pool: "
                f"{bey} (ELO {elo:.0f})"
            )

    # Warn about any tiers still short (upper tiers require manual fixes;
    # Tier IV shortage means not enough pool beys were available).
    for t in range(1, tiers + 1):
        shortage = beys_per_tier - len(tier_comp[t])
        if shortage > 0:
            warnings.append(
                f"Tier {t} is still {shortage} bey(s) short — "
                "add qualification tournament results manually."
            )

    # Build tier_assignments with current ELO as start_elo.
    tier_assignments: Dict[str, Dict] = {}
    for t, beys in tier_comp.items():
        for bey in beys:
            tier_assignments[bey] = {
                "tier": t,
                "start_elo": elo_lookup.get(bey),
            }

    # Remaining qualification pool:
    # - fill_pool entries that were not placed in a tier (unused pool beys)
    # - qual_out beys (dropped from Tier IV; they enter the qual tournament)
    in_league_new: set = set(tier_assignments.keys())
    unused_pool = [
        {"bey": bey, "elo": elo}
        for bey, elo in fill_pool
        if bey not in in_league_new
    ]
    qual_out_entries = [
        {"bey": bey, "elo": elo_lookup.get(bey, 0.0)}
        for bey in qual_out
        if bey not in in_league_new
    ]
    remaining_qual_pool = qual_out_entries + unused_pool

    season_data = {
        "season_id": new_season_id,
        "start_date": datetime.now().isoformat(),
        "status": "active",
        "tier_assignments": tier_assignments,
        "qualification_pool": remaining_qual_pool,
        "league_champion": None,
        "cup_winner": None,
        "tiers": {},
    }

    for t in range(1, tiers + 1):
        tier_beys = [bey for bey, data in tier_assignments.items() if data["tier"] == t]
        season_data["tiers"][str(t)] = {
            "beys": tier_beys,
            "matches_played": 0,
            "matches_total": int(beys_per_tier * (beys_per_tier - 1) / 2),
        }

    return season_data, warnings


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

    # Find league champion (1st place in Tier I) — only when matches have been played
    season_matches_count = len([m for m in matches if m.get("season_id") == season_id])
    league_champion = None
    if season_matches_count > 0 and 1 in league_tables and len(league_tables[1]) > 0:
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
        "status": season_data.get("status", "active"),
        "league_champion": league_champion,
        "cup_winner": season_data.get("cup_winner"),
        "league_tables": {str(tier): table for tier, table in league_tables.items()},
        "matchdays": dict(matchdays),
        "promotion_relegation": promotion_relegation,
        "statistics": {
            "total_matches": season_matches_count,
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
