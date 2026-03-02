"""
Season Cup Module - Double Elimination Tournament System

This module handles the Season Cup post-season tournament, including:
- Qualification logic based on tier performance
- Double-elimination bracket generation
- Match tracking and bracket progression
- Cup winner determination

Season Cup Structure:
- 8 qualified beys total:
  * Top 4 from Tier I
  * Top 2 from Tier II
  * Top 1 from Tier III
  * Top 1 from Tier IV
- Double-elimination format
- All matches tagged as match_type='season_cup'

Functions:
    get_qualified_beys(league_tables): Determine Season Cup qualifiers
    generate_double_elimination_bracket(qualified_beys): Create bracket structure
    update_bracket(bracket, match_result): Update bracket after match
    get_cup_winner(bracket): Determine tournament winner
    export_bracket_for_display(bracket): Format bracket for frontend visualization
"""

import json
import os
from typing import Dict, List, Optional

# Qualification slots per tier
TIER_QUALIFICATION = {
    1: 4,  # Tier I: Top 4
    2: 2,  # Tier II: Top 2
    3: 1,  # Tier III: Top 1
    4: 1   # Tier IV: Top 1
}

# Default paths
DEFAULT_DATA_DIR = "./docs/data"


def get_qualified_beys(league_tables: Dict[int, List[Dict]]) -> List[Dict]:
    """
    Determine which beys qualify for the Season Cup based on league standings.

    Qualification:
    - Tier I: Top 4
    - Tier II: Top 3
    - Tier III: Top 1

    Args:
        league_tables: Dictionary mapping tier number to league table

    Returns:
        List of qualified bey dictionaries with tier and position info
    """
    qualified = []

    for tier, slots in TIER_QUALIFICATION.items():
        table = league_tables.get(tier, [])

        # Take top N from this tier
        for i in range(min(slots, len(table))):
            qualified.append({
                "bey": table[i]["bey"],
                "tier": tier,
                "position": i + 1,
                "seed": len(qualified) + 1,
                "elo": table[i].get("elo", 0)
            })

    return qualified


def generate_double_elimination_bracket(qualified_beys: List[Dict]) -> Dict:
    """
    Generate a double-elimination bracket structure for 8 participants.

    Double elimination means:
    - Winners bracket: Winners continue here
    - Losers bracket: First-time losers drop here (second loss eliminates)
    - Grand final: Winner of each bracket meets

    Seeding is based on tier performance:
    1-4: Tier I (1st, 2nd, 3rd, 4th)
    5-7: Tier II (1st, 2nd, 3rd)
    8: Tier III (1st)

    Args:
        qualified_beys: List of 8 qualified beys with seed info

    Returns:
        Bracket structure dictionary
    """
    if len(qualified_beys) != 8:
        raise ValueError(f"Expected 8 qualified beys, got {len(qualified_beys)}")

    # Sort by seed
    qualified_beys.sort(key=lambda x: x["seed"])

    # Standard 8-player double elimination seeding
    # Winners Bracket Round 1 (Quarterfinals)
    winners_r1_matchups = [
        (qualified_beys[0], qualified_beys[7]),  # 1 vs 8
        (qualified_beys[3], qualified_beys[4]),  # 4 vs 5
        (qualified_beys[1], qualified_beys[6]),  # 2 vs 7
        (qualified_beys[2], qualified_beys[5])   # 3 vs 6
    ]

    bracket = {
        "format": "double_elimination",
        "participants": qualified_beys,
        "winners_bracket": {
            "round_1": [
                {
                    "match_id": "WB-R1-M1",
                    "bey_a": winners_r1_matchups[0][0]["bey"],
                    "bey_b": winners_r1_matchups[0][1]["bey"],
                    "seed_a": winners_r1_matchups[0][0]["seed"],
                    "seed_b": winners_r1_matchups[0][1]["seed"],
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "WB-R1-M2",
                    "bey_a": winners_r1_matchups[1][0]["bey"],
                    "bey_b": winners_r1_matchups[1][1]["bey"],
                    "seed_a": winners_r1_matchups[1][0]["seed"],
                    "seed_b": winners_r1_matchups[1][1]["seed"],
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "WB-R1-M3",
                    "bey_a": winners_r1_matchups[2][0]["bey"],
                    "bey_b": winners_r1_matchups[2][1]["bey"],
                    "seed_a": winners_r1_matchups[2][0]["seed"],
                    "seed_b": winners_r1_matchups[2][1]["seed"],
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "WB-R1-M4",
                    "bey_a": winners_r1_matchups[3][0]["bey"],
                    "bey_b": winners_r1_matchups[3][1]["bey"],
                    "seed_a": winners_r1_matchups[3][0]["seed"],
                    "seed_b": winners_r1_matchups[3][1]["seed"],
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                }
            ],
            "round_2": [
                {
                    "match_id": "WB-R2-M1",
                    "bey_a": None,  # Winner of WB-R1-M1
                    "bey_b": None,  # Winner of WB-R1-M2
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "WB-R2-M2",
                    "bey_a": None,  # Winner of WB-R1-M3
                    "bey_b": None,  # Winner of WB-R1-M4
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                }
            ],
            "finals": {
                "match_id": "WB-FINAL",
                "bey_a": None,  # Winner of WB-R2-M1
                "bey_b": None,  # Winner of WB-R2-M2
                "winner": None,
                "score_a": None,
                "score_b": None
            }
        },
        "losers_bracket": {
            "round_1": [
                {
                    "match_id": "LB-R1-M1",
                    "bey_a": None,  # Loser of WB-R1-M1
                    "bey_b": None,  # Loser of WB-R1-M2
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "LB-R1-M2",
                    "bey_a": None,  # Loser of WB-R1-M3
                    "bey_b": None,  # Loser of WB-R1-M4
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                }
            ],
            "round_2": [
                {
                    "match_id": "LB-R2-M1",
                    "bey_a": None,  # Winner of LB-R1-M1
                    "bey_b": None,  # Loser of WB-R2-M1
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                },
                {
                    "match_id": "LB-R2-M2",
                    "bey_a": None,  # Winner of LB-R1-M2
                    "bey_b": None,  # Loser of WB-R2-M2
                    "winner": None,
                    "score_a": None,
                    "score_b": None
                }
            ],
            "round_3": {
                "match_id": "LB-R3",
                "bey_a": None,  # Winner of LB-R2-M1
                "bey_b": None,  # Winner of LB-R2-M2
                "winner": None,
                "score_a": None,
                "score_b": None
            },
            "finals": {
                "match_id": "LB-FINAL",
                "bey_a": None,  # Winner of LB-R3
                "bey_b": None,  # Loser of WB-FINAL
                "winner": None,
                "score_a": None,
                "score_b": None
            }
        },
        "grand_final": {
            "match_id": "GRAND-FINAL",
            "bey_a": None,  # Winner of WB-FINAL
            "bey_b": None,  # Winner of LB-FINAL
            "winner": None,
            "score_a": None,
            "score_b": None,
            "note": "Winner of Winners Bracket has advantage (may need only 1 match to win)"
        },
        "cup_winner": None
    }

    return bracket


def update_bracket_with_match(bracket: Dict, match_id: str,
                              winner: str, score_a: int, score_b: int,
                              bey_a: str, bey_b: str) -> Dict:
    """
    Update bracket structure with a match result.

    Args:
        bracket: Bracket structure
        match_id: Identifier for the match (e.g., "WB-R1-M1")
        winner: Name of winning bey
        score_a: Score for bey_a
        score_b: Score for bey_b
        bey_a: Name of first participant
        bey_b: Name of second participant

    Returns:
        Updated bracket structure
    """
    # Find and update the match in the bracket
    def update_match_recursive(section):
        if isinstance(section, dict):
            if section.get("match_id") == match_id:
                section["bey_a"] = bey_a
                section["bey_b"] = bey_b
                section["winner"] = winner
                section["score_a"] = score_a
                section["score_b"] = score_b
                return True
            for value in section.values():
                if update_match_recursive(value):
                    return True
        elif isinstance(section, list):
            for item in section:
                if update_match_recursive(item):
                    return True
        return False

    update_match_recursive(bracket)

    # Update downstream matches based on bracket logic
    # This is a simplified version - full implementation would handle all bracket flows

    return bracket


def get_cup_winner(bracket: Dict) -> Optional[str]:
    """
    Determine the cup winner from a completed bracket.

    Args:
        bracket: Bracket structure

    Returns:
        Name of cup winner, or None if tournament not complete
    """
    grand_final = bracket.get("grand_final", {})
    winner = grand_final.get("winner")

    if winner:
        bracket["cup_winner"] = winner
        return winner

    return None


def export_bracket_for_display(bracket: Dict) -> Dict:
    """
    Format bracket data for frontend visualization.

    Args:
        bracket: Bracket structure

    Returns:
        Simplified bracket structure for display
    """
    def simplify_match(match):
        if match is None:
            return None
        return {
            "id": match.get("match_id"),
            "participants": [
                {
                    "name": match.get("bey_a"),
                    "score": match.get("score_a"),
                    "seed": match.get("seed_a")
                },
                {
                    "name": match.get("bey_b"),
                    "score": match.get("score_b"),
                    "seed": match.get("seed_b")
                }
            ],
            "winner": match.get("winner")
        }

    display_bracket = {
        "format": bracket.get("format"),
        "cup_winner": bracket.get("cup_winner"),
        "winners_bracket": {},
        "losers_bracket": {},
        "grand_final": simplify_match(bracket.get("grand_final"))
    }

    # Simplify winners bracket
    wb = bracket.get("winners_bracket", {})
    for round_name, matches in wb.items():
        if isinstance(matches, list):
            display_bracket["winners_bracket"][round_name] = [
                simplify_match(m) for m in matches
            ]
        elif isinstance(matches, dict):
            display_bracket["winners_bracket"][round_name] = simplify_match(matches)

    # Simplify losers bracket
    lb = bracket.get("losers_bracket", {})
    for round_name, matches in lb.items():
        if isinstance(matches, list):
            display_bracket["losers_bracket"][round_name] = [
                simplify_match(m) for m in matches
            ]
        elif isinstance(matches, dict):
            display_bracket["losers_bracket"][round_name] = simplify_match(matches)

    return display_bracket


def save_season_cup_data(season_id: str, bracket: Dict,
                         data_dir: str = DEFAULT_DATA_DIR) -> None:
    """
    Save Season Cup bracket data to file.

    Args:
        season_id: Season identifier
        bracket: Bracket structure
        data_dir: Directory to store data
    """
    os.makedirs(data_dir, exist_ok=True)
    filename = os.path.join(data_dir, f"season_{season_id}_cup.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(bracket, f, indent=2, ensure_ascii=False)


def load_season_cup_data(season_id: str,
                         data_dir: str = DEFAULT_DATA_DIR) -> Optional[Dict]:
    """
    Load Season Cup bracket data from file.

    Args:
        season_id: Season identifier
        data_dir: Directory where data is stored

    Returns:
        Bracket structure, or None if not found
    """
    filename = os.path.join(data_dir, f"season_{season_id}_cup.json")

    if not os.path.exists(filename):
        return None

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


if __name__ == "__main__":
    # Example usage and testing
    print("Season Cup Module")
    print("=================")

    # Test qualification
    print("\nTesting qualification logic:")
    test_tables = {
        1: [{"bey": f"T1-{i}", "elo": 1500 - i * 10} for i in range(1, 11)],
        2: [{"bey": f"T2-{i}", "elo": 1400 - i * 10} for i in range(1, 11)],
        3: [{"bey": f"T3-{i}", "elo": 1300 - i * 10} for i in range(1, 11)]
    }

    qualified = get_qualified_beys(test_tables)
    print(f"  Qualified beys: {len(qualified)}")
    for q in qualified:
        print(f"    Seed {q['seed']}: {q['bey']} (Tier {q['tier']}, Position {q['position']})")

    # Test bracket generation
    print("\nGenerating double-elimination bracket:")
    bracket = generate_double_elimination_bracket(qualified)
    print(f"  Winners Bracket R1: {len(bracket['winners_bracket']['round_1'])} matches")
    print(f"  Losers Bracket R1: {len(bracket['losers_bracket']['round_1'])} matches")
