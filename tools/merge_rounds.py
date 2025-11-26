#!/usr/bin/env python3
"""
Merge Rounds Tool

Merges Challonge export data (CSV or JSON) with a rounds CSV file to create
match data with per-round finish type tracking.

Usage:
    python tools/merge_rounds.py --challonge challonge.csv --rounds rounds.csv --output matches.json
    python tools/merge_rounds.py --validate matches.json
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Valid finish types
VALID_FINISH_TYPES = {"spin", "ring_out", "pocket", "burst", "extreme"}
DEFAULT_FINISH_TYPE = "spin"

# Default weights path
DEFAULT_WEIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "finish_weights.json"
)


def load_finish_weights(weights_path: Optional[str] = None) -> dict:
    """Load finish type weights from config file."""
    path = weights_path or DEFAULT_WEIGHTS_PATH
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("weights", {})
    # Default weights if config not found
    return {
        "spin": 1,
        "ring_out": 2,
        "pocket": 2,
        "burst": 2,
        "extreme": 3
    }


def load_challonge_csv(filepath: str) -> list[dict]:
    """
    Load Challonge export CSV file.

    Supports both Challonge export format and internal CSV format:
    - Challonge: Various column names for players and scores
    - Internal: Date,BeyA,BeyB,ScoreA,ScoreB
    """
    matches = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Detect format based on headers
        is_internal_format = "BeyA" in headers and "BeyB" in headers

        for row in reader:
            if is_internal_format:
                match = {
                    "date": row.get("Date", ""),
                    "bey_a": row.get("BeyA", ""),
                    "bey_b": row.get("BeyB", ""),
                    "score_a": int(row.get("ScoreA", 0)),
                    "score_b": int(row.get("ScoreB", 0)),
                    "match_id": row.get("match_id", ""),
                }
            else:
                # Challonge format - adapt as needed
                match = {
                    "date": row.get("Date", row.get("date", "")),
                    "bey_a": row.get("Player 1", row.get("player1", row.get("BeyA", ""))),
                    "bey_b": row.get("Player 2", row.get("player2", row.get("BeyB", ""))),
                    "score_a": int(row.get("Player 1 Score", row.get("score1", row.get("ScoreA", 0))) or 0),
                    "score_b": int(row.get("Player 2 Score", row.get("score2", row.get("ScoreB", 0))) or 0),
                    "match_id": row.get("Match ID", row.get("match_id", row.get("id", ""))),
                }

            # Generate match_id if not present
            if not match["match_id"]:
                match["match_id"] = f"{match['bey_a']}_vs_{match['bey_b']}_{match['date']}"

            matches.append(match)

    return matches


def load_challonge_json(filepath: str) -> list[dict]:
    """Load Challonge export JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    matches = []
    # Handle various JSON structures
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "matches" in data:
        items = data["matches"]
    else:
        items = [data]

    for item in items:
        # Handle nested match objects
        if "match" in item:
            item = item["match"]

        # Parse scores - handle Challonge scores_csv format
        scores_csv = item.get("scores_csv")
        if isinstance(scores_csv, str) and "-" in scores_csv:
            score_a = int(scores_csv.split("-")[0])
            score_b = int(scores_csv.split("-")[1])
        else:
            score_a = item.get("score_a", item.get("ScoreA", 0))
            score_b = item.get("score_b", item.get("ScoreB", 0))

        match = {
            "date": item.get("date", item.get("Date", "")),
            "bey_a": item.get("player1_id", item.get("bey_a", item.get("BeyA", ""))),
            "bey_b": item.get("player2_id", item.get("bey_b", item.get("BeyB", ""))),
            "score_a": int(score_a) if score_a else 0,
            "score_b": int(score_b) if score_b else 0,
            "match_id": str(item.get("id", item.get("match_id", ""))),
        }

        if not match["match_id"]:
            match["match_id"] = f"{match['bey_a']}_vs_{match['bey_b']}_{match['date']}"

        matches.append(match)

    return matches


def load_rounds_csv(filepath: str) -> dict[str, list[dict]]:
    """
    Load rounds CSV file.

    Returns dict mapping match_id to list of rounds.
    """
    rounds_by_match = defaultdict(list)

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            match_id = row.get("match_id", "")
            if not match_id:
                continue

            round_data = {
                "round_number": int(row.get("round_number", 0)) if row.get("round_number") else None,
                "winner": row.get("winner", ""),
                "finish_type": row.get("finish_type", "").lower().strip() or DEFAULT_FINISH_TYPE,
                "points_awarded": int(row.get("points_awarded", 1)) if row.get("points_awarded") else 1,
                "notes": row.get("notes", ""),
            }

            # Validate and default finish_type
            if round_data["finish_type"] not in VALID_FINISH_TYPES:
                ft = round_data["finish_type"]
                print(f"Warning: Invalid finish_type '{ft}' in match {match_id}, defaulting to 'spin'")
                round_data["finish_type"] = DEFAULT_FINISH_TYPE

            rounds_by_match[match_id].append(round_data)

    # Sort rounds by round_number within each match
    for match_id in rounds_by_match:
        rounds_by_match[match_id].sort(key=lambda r: r["round_number"] or 0)
        # Assign round numbers if missing
        for i, r in enumerate(rounds_by_match[match_id], 1):
            if r["round_number"] is None:
                r["round_number"] = i

    return dict(rounds_by_match)


def compute_scores_from_rounds(rounds: list[dict], bey_a: str, bey_b: str) -> tuple[int, int]:
    """Compute total scores from round data."""
    score_a = 0
    score_b = 0

    for r in rounds:
        winner = r["winner"]
        points = r["points_awarded"]

        if winner == bey_a:
            score_a += points
        elif winner == bey_b:
            score_b += points
        else:
            print(f"Warning: Round winner '{winner}' doesn't match '{bey_a}' or '{bey_b}'")

    return score_a, score_b


def create_player_key(bey_a: str, bey_b: str, date: str = "") -> str:
    """Create a key for matching by player names."""
    players = sorted([bey_a.lower(), bey_b.lower()])
    return f"{players[0]}_{players[1]}_{date}" if date else f"{players[0]}_{players[1]}"


def merge_matches_and_rounds(
    matches: list[dict],
    rounds_by_match: dict[str, list[dict]],
    match_by_players: bool = False
) -> tuple[list[dict], dict]:
    """
    Merge match data with round data.

    Returns:
        - List of merged match objects
        - Statistics dictionary
    """
    merged = []
    stats = {
        "total_matches": len(matches),
        "total_rounds": sum(len(r) for r in rounds_by_match.values()),
        "merged": 0,
        "unmerged": 0,
        "score_mismatches": 0,
        "defaults_applied": 0,
        "warnings": []
    }

    used_round_keys = set()

    for match in matches:
        match_id = match["match_id"]
        bey_a = match["bey_a"]
        bey_b = match["bey_b"]

        # Try to find rounds for this match
        rounds = None

        # First try match_id
        if match_id in rounds_by_match:
            rounds = rounds_by_match[match_id]
            used_round_keys.add(match_id)
        elif match_by_players:
            # Try matching by player names
            for rm_id, rm_rounds in rounds_by_match.items():
                if rm_id in used_round_keys:
                    continue
                # Check if round winners match the players
                round_players = set()
                for r in rm_rounds:
                    round_players.add(r["winner"].lower())
                if bey_a.lower() in round_players or bey_b.lower() in round_players:
                    rounds = rm_rounds
                    used_round_keys.add(rm_id)
                    stats["warnings"].append(
                        f"Match '{bey_a}' vs '{bey_b}': matched by players (original id: {rm_id})"
                    )
                    break

        merged_match = {
            "match_id": match_id,
            "date": match["date"],
            "bey_a": bey_a,
            "bey_b": bey_b,
            "score_a": match["score_a"],
            "score_b": match["score_b"],
        }

        if rounds:
            merged_match["rounds"] = rounds
            stats["merged"] += 1

            # Compute scores from rounds and validate
            computed_a, computed_b = compute_scores_from_rounds(rounds, bey_a, bey_b)

            if (computed_a, computed_b) != (match["score_a"], match["score_b"]):
                stats["score_mismatches"] += 1
                warning = (
                    f"Match {match_id}: Score mismatch - "
                    f"Challonge: {match['score_a']}-{match['score_b']}, "
                    f"Rounds: {computed_a}-{computed_b}"
                )
                stats["warnings"].append(warning)
                # Prefer rounds data
                merged_match["score_a"] = computed_a
                merged_match["score_b"] = computed_b
                merged_match["original_scores"] = {
                    "score_a": match["score_a"],
                    "score_b": match["score_b"]
                }

            # Count defaults applied
            for r in rounds:
                if r["finish_type"] == DEFAULT_FINISH_TYPE:
                    # Only count if it wasn't explicitly set (approximation)
                    stats["defaults_applied"] += 1
        else:
            stats["unmerged"] += 1
            stats["warnings"].append(f"Match {match_id} ({bey_a} vs {bey_b}): No rounds data found")

        merged.append(merged_match)

    return merged, stats


def validate_merged_data(filepath: str) -> bool:
    """Validate a merged JSON file."""
    print(f"Validating: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "matches" in data:
        matches = data["matches"]
    elif isinstance(data, list):
        matches = data
    else:
        print("Error: Invalid data format")
        return False

    errors = []
    warnings = []

    for i, match in enumerate(matches):
        match_id = match.get("match_id", f"index-{i}")

        # Check required fields
        for field in ["bey_a", "bey_b"]:
            if not match.get(field):
                errors.append(f"Match {match_id}: Missing required field '{field}'")

        # Validate rounds if present
        rounds = match.get("rounds", [])
        if rounds:
            bey_a = match.get("bey_a", "")
            bey_b = match.get("bey_b", "")
            computed_a, computed_b = compute_scores_from_rounds(rounds, bey_a, bey_b)

            # Check score consistency
            if match.get("score_a") is not None and match.get("score_b") is not None:
                if (computed_a, computed_b) != (match["score_a"], match["score_b"]):
                    warnings.append(
                        f"Match {match_id}: Stored scores ({match['score_a']}-{match['score_b']}) "
                        f"don't match computed ({computed_a}-{computed_b})"
                    )

            for j, r in enumerate(rounds):
                # Check winner
                winner = r.get("winner", "")
                if winner and winner not in [bey_a, bey_b]:
                    errors.append(
                        f"Match {match_id}, Round {j + 1}: Winner '{winner}' not in players"
                    )

                # Check finish_type
                finish_type = r.get("finish_type", "")
                if finish_type and finish_type not in VALID_FINISH_TYPES:
                    errors.append(
                        f"Match {match_id}, Round {j + 1}: Invalid finish_type '{finish_type}'"
                    )

                # Check points_awarded
                points = r.get("points_awarded")
                if points is not None and points < 1:
                    errors.append(
                        f"Match {match_id}, Round {j + 1}: Invalid points_awarded '{points}'"
                    )

    # Print results
    print("\n=== Validation Results ===")
    print(f"Total matches: {len(matches)}")
    print(f"Matches with rounds: {sum(1 for m in matches if m.get('rounds'))}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if errors:
        print("\nErrors:")
        for e in errors[:20]:  # Limit output
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    if warnings:
        print("\nWarnings:")
        for w in warnings[:20]:
            print(f"  - {w}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more")

    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Merge Challonge export with rounds data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge Challonge CSV with rounds CSV
  python merge_rounds.py --challonge challonge.csv --rounds rounds.csv --output merged.json

  # Merge using player name matching (no match IDs)
  python merge_rounds.py --challonge challonge.csv --rounds rounds.csv --output merged.json --match-by-players

  # Validate a merged file
  python merge_rounds.py --validate merged.json
        """
    )

    parser.add_argument(
        "--challonge",
        help="Path to Challonge export file (CSV or JSON)"
    )
    parser.add_argument(
        "--rounds",
        help="Path to rounds CSV file"
    )
    parser.add_argument(
        "--output",
        help="Path for output JSON file"
    )
    parser.add_argument(
        "--validate",
        help="Path to JSON file to validate (standalone validation mode)"
    )
    parser.add_argument(
        "--match-by-players",
        action="store_true",
        help="Match rounds to matches by player names instead of match_id"
    )
    parser.add_argument(
        "--weights-config",
        help="Path to finish weights config file"
    )

    args = parser.parse_args()

    # Validation mode
    if args.validate:
        success = validate_merged_data(args.validate)
        sys.exit(0 if success else 1)

    # Merge mode
    if not args.challonge or not args.rounds or not args.output:
        parser.error("--challonge, --rounds, and --output are required for merge mode")

    # Load Challonge data
    print(f"Loading Challonge data from: {args.challonge}")
    if args.challonge.endswith(".json"):
        matches = load_challonge_json(args.challonge)
    else:
        matches = load_challonge_csv(args.challonge)
    print(f"  Loaded {len(matches)} matches")

    # Load rounds data
    print(f"Loading rounds data from: {args.rounds}")
    rounds_by_match = load_rounds_csv(args.rounds)
    total_rounds = sum(len(r) for r in rounds_by_match.values())
    print(f"  Loaded {total_rounds} rounds for {len(rounds_by_match)} matches")

    # Merge
    print("Merging data...")
    merged, stats = merge_matches_and_rounds(matches, rounds_by_match, args.match_by_players)

    # Write output
    output_data = {
        "matches": merged,
        "metadata": {
            "source_challonge": args.challonge,
            "source_rounds": args.rounds,
            "merge_stats": stats
        }
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Output written to: {args.output}")

    # Print summary
    print("\n=== Merge Summary ===")
    print(f"Total matches in Challonge: {stats['total_matches']}")
    print(f"Total rounds in rounds file: {stats['total_rounds']}")
    print(f"Matches merged: {stats['merged']}")
    print(f"Matches without rounds: {stats['unmerged']}")
    print(f"Score mismatches: {stats['score_mismatches']}")
    print(f"Defaults applied: {stats['defaults_applied']}")

    if stats["warnings"]:
        print(f"\nWarnings ({len(stats['warnings'])}):")
        for w in stats["warnings"][:10]:
            print(f"  - {w}")
        if len(stats["warnings"]) > 10:
            print(f"  ... and {len(stats['warnings']) - 10} more")


if __name__ == "__main__":
    main()
