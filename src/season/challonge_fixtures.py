"""
Challonge Fixtures Integration

Converts Challonge API v2.1 JSON data into Quick-Entry compatible fixture
schedules and generates remaining match plans after each session.

The Challonge API JSON files are expected in:
    docs/data/season/api_jsons/{season_id_lower}/{season_id_lower}_t{tier}.json

e.g. docs/data/season/api_jsons/s2/s2_t1.json

Key Features:
- Parse full match schedule from Challonge API JSON (per season + tier)
- Convert to fixtures.csv format (FixtureID,Date,BeyA,BeyB,MatchType,SeasonID,Tier,Matchday)
- Compare Challonge schedule with played matches from matches.csv
- Generate a session-ready Quick-Entry CSV containing only remaining matches
- Deterministic FixtureID based on sorted bey names + season + tier
- Preview mode (--preview) showing summary counts
- Auto-detects the current season when --season is omitted

Remaining match ordering (per spec):
    Sorted by matchday ASC, then tier DESC (4 → 3 → 2 → 1) within each matchday.

Usage:
    # Auto-detect current season and generate remaining-matches plan
    python -m src.season.challonge_fixtures --generate-remaining

    # Update fixtures.csv with full schedule for season S2
    python -m src.season.challonge_fixtures --season S2 --update-fixtures

    # Generate remaining-matches plan for next session (all tiers)
    python -m src.season.challonge_fixtures --season S2 --generate-remaining

    # Single tier only
    python -m src.season.challonge_fixtures --season S2 --tier 1 --generate-remaining

    # Preview mode (no files written)
    python -m src.season.challonge_fixtures --season S2 --preview
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
import os as _os
_root = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)
del _os, _root

from src.config.paths import (  # noqa: E402
    FIXTURES_CSV,
    MATCHES_CSV,
    SEASON_API_JSONS_DIR,
    SEASON_DIR,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Roman numeral → integer mapping for tier parsing
_ROMAN_NUMERALS: Dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}

MATCH_TYPE = "season"
ARENA = "Xtreme"
SEASONS_JSON = os.path.join(SEASON_DIR, "seasons.json")


def _parse_season_start_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def detect_current_season(
    api_jsons_dir: str = SEASON_API_JSONS_DIR,
    seasons_json: str = SEASONS_JSON,
) -> str:
    """
    Determine the current season based on repository context.

    Priority order:
    1. Active seasons in seasons.json (latest start_date wins)
    2. Any season in seasons.json (latest start_date wins)
    3. Highest season number found in api_jsons directory

    Args:
        api_jsons_dir: Base directory containing season API JSON folders.
        seasons_json: Path to seasons.json metadata file.

    Returns:
        Uppercase season identifier string (e.g., "S2").
    """
    if os.path.exists(seasons_json):
        with open(seasons_json, "r", encoding="utf-8") as fh:
            seasons = json.load(fh)

        def _season_sort_key(item: Tuple[str, Dict]) -> Tuple[int, datetime, int]:
            season_id, info = item
            start_date = _parse_season_start_date(info.get("start_date"))
            match = re.search(r"\d+", season_id)
            season_num = int(match.group()) if match else 0
            if start_date:
                return (1, start_date, season_num)
            return (0, datetime.min, season_num)

        active = [
            (sid, info)
            for sid, info in seasons.items()
            if str(info.get("status", "")).lower() in ("active", "current", "ongoing")
        ]
        candidates = active or list(seasons.items())

        if os.path.isdir(api_jsons_dir):
            available = {
                d.lower()
                for d in os.listdir(api_jsons_dir)
                if os.path.isdir(os.path.join(api_jsons_dir, d))
            }
            filtered = [item for item in candidates if item[0].lower() in available]
            candidates = filtered or candidates

        if candidates:
            season_id = max(candidates, key=_season_sort_key)[0]
            return season_id.upper()

    if os.path.isdir(api_jsons_dir):
        available = [
            d for d in os.listdir(api_jsons_dir)
            if os.path.isdir(os.path.join(api_jsons_dir, d))
        ]
        if available:
            def _dir_sort_key(name: str) -> Tuple[int, int, str]:
                match = re.search(r"\d+", name)
                season_num = int(match.group()) if match else 0
                return (1 if match else 0, season_num, name)
            return max(available, key=_dir_sort_key).upper()

    raise FileNotFoundError(
        "Unable to determine current season. Check seasons.json for configured seasons "
        "or ensure at least one season directory exists in api_jsons/."
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def extract_season_tier(tournament_name: str) -> Tuple[str, int]:
    """
    Extract the season ID and tier number from a Challonge tournament name.

    Supports names like:
        "SEASON 2 TIER I"   → ("S2", 1)
        "SEASON 2 TIER II"  → ("S2", 2)
        "SEASON 2 TIER III" → ("S2", 3)
        "SEASON 2 TIER IV"  → ("S2", 4)

    Args:
        tournament_name: The ``name`` attribute from the Challonge API.

    Returns:
        A (season_id, tier) tuple, e.g. ("S2", 1).

    Raises:
        ValueError: If the name cannot be parsed.
    """
    name_upper = tournament_name.upper().strip()

    # Match "SEASON <number> TIER <roman>"
    pattern = r"SEASON\s+(\d+)\s+TIER\s+([IVXLCDM]+)"
    match = re.search(pattern, name_upper)
    if not match:
        raise ValueError(
            f"Cannot parse season/tier from tournament name: '{tournament_name}'"
        )

    season_num = int(match.group(1))
    tier_roman = match.group(2)

    if tier_roman not in _ROMAN_NUMERALS:
        raise ValueError(
            f"Unsupported tier roman numeral '{tier_roman}' in: '{tournament_name}'"
        )

    season_id = f"S{season_num}"
    tier = _ROMAN_NUMERALS[tier_roman]
    return season_id, tier


def make_fixture_id(bey_a: str, bey_b: str, season_id: str, tier: int) -> str:
    """
    Generate a deterministic, order-independent FixtureID.

    The two bey names are sorted alphabetically so that
    ``make_fixture_id("FoxBrush", "ImpactDrake", "S2", 1)`` produces the
    same result as
    ``make_fixture_id("ImpactDrake", "FoxBrush", "S2", 1)``.

    Format: ``{season_id}_T{tier}_{lower_bey}_{higher_bey}``
    Example: ``S2_T1_FoxBrush_ImpactDrake``

    Args:
        bey_a: First bey name.
        bey_b: Second bey name.
        season_id: Season identifier (e.g. "S2").
        tier: Tier number (1–4).

    Returns:
        A stable string identifier.
    """
    sorted_beys = sorted([bey_a, bey_b])
    return f"{season_id}_T{tier}_{sorted_beys[0]}_{sorted_beys[1]}"


def _match_pair_key(bey_a: str, bey_b: str) -> FrozenSet[str]:
    """Return a frozenset of two bey names for order-independent comparison."""
    return frozenset([bey_a, bey_b])


# ---------------------------------------------------------------------------
# Challonge API parsing
# ---------------------------------------------------------------------------

def parse_challonge_json(json_path: str) -> Dict:
    """
    Parse a Challonge API v2.1 JSON file.

    The JSON structure uses ``data`` for the tournament and ``included``
    for participants and matches.  Each match's ``points_by_participant``
    array holds participant IDs and their scores.

    Args:
        json_path: Absolute path to the ``*.json`` file.

    Returns:
        A dict with keys:
            - ``season_id`` (str)
            - ``tier`` (int)
            - ``tournament_name`` (str)
            - ``participants`` (dict mapping id → name)
            - ``matches`` (list of match dicts)

        Each match dict contains:
            - ``fixture_id`` (str)  – deterministic ID
            - ``challonge_match_id`` (str)
            - ``bey_a`` (str)
            - ``bey_b`` (str)
            - ``score_a`` (int)
            - ``score_b`` (int)
            - ``matchday`` (int)  – Challonge round number
            - ``state`` (str)  – "complete" | "open" | …
            - ``season_id`` (str)
            - ``tier`` (int)

    Raises:
        FileNotFoundError: If *json_path* does not exist.
        ValueError: If the tournament name cannot be parsed.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Challonge API JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    tournament_attrs = data["data"]["attributes"]
    tournament_name = tournament_attrs["name"]
    season_id, tier = extract_season_tier(tournament_name)

    # Build participant id → name lookup
    participants: Dict[str, str] = {}
    for item in data.get("included", []):
        if item["type"] == "participant":
            participants[item["id"]] = item["attributes"]["name"]

    # Parse matches
    matches: List[Dict] = []
    for item in data.get("included", []):
        if item["type"] != "match":
            continue

        attr = item["attributes"]
        pts_by_p = attr.get("points_by_participant", [])

        if len(pts_by_p) < 2:
            # Incomplete match data – skip
            continue

        p1_id = str(pts_by_p[0]["participant_id"])
        p2_id = str(pts_by_p[1]["participant_id"])
        bey_a = participants.get(p1_id, p1_id)
        bey_b = participants.get(p2_id, p2_id)

        scores_p1 = pts_by_p[0].get("scores", [0])
        scores_p2 = pts_by_p[1].get("scores", [0])
        score_a = scores_p1[0] if scores_p1 else 0
        score_b = scores_p2[0] if scores_p2 else 0

        matchday = int(attr.get("round", 0))
        state = attr.get("state", "unknown")

        fixture_id = make_fixture_id(bey_a, bey_b, season_id, tier)

        matches.append({
            "fixture_id": fixture_id,
            "challonge_match_id": str(item["id"]),
            "bey_a": bey_a,
            "bey_b": bey_b,
            "score_a": int(score_a),
            "score_b": int(score_b),
            "matchday": matchday,
            "state": state,
            "season_id": season_id,
            "tier": tier,
        })

    return {
        "season_id": season_id,
        "tier": tier,
        "tournament_name": tournament_name,
        "participants": participants,
        "matches": matches,
    }


def challonge_to_fixtures(json_path: str) -> List[Dict]:
    """
    Convert a Challonge API JSON file to a list of fixture dicts.

    This is a thin wrapper around :func:`parse_challonge_json` that returns
    only the list of match fixtures (all matches, both played and unplayed).

    Args:
        json_path: Path to the Challonge API JSON file.

    Returns:
        List of fixture dicts (see :func:`parse_challonge_json`).
    """
    result = parse_challonge_json(json_path)
    return result["matches"]


def load_season_api_jsons(season_id: str, tier: Optional[int] = None) -> List[str]:
    """
    Discover Challonge API JSON files for a given season.

    Files are expected at:
        ``{SEASON_API_JSONS_DIR}/{season_id_lower}/{season_id_lower}_t{tier}.json``

    Args:
        season_id: Season identifier, e.g. "S2".
        tier: Optional tier number (1–4).  When *None*, all tiers are returned.

    Returns:
        Sorted list of absolute paths that exist on disk.

    Raises:
        FileNotFoundError: If the season directory does not exist.
    """
    season_dir = os.path.join(SEASON_API_JSONS_DIR, season_id.lower())
    if not os.path.isdir(season_dir):
        raise FileNotFoundError(
            f"Season API JSON directory not found: {season_dir}"
        )

    paths = []
    if tier is not None:
        candidate = os.path.join(
            season_dir, f"{season_id.lower()}_t{tier}.json"
        )
        if os.path.exists(candidate):
            paths.append(candidate)
    else:
        for fname in sorted(os.listdir(season_dir)):
            if fname.endswith(".json"):
                paths.append(os.path.join(season_dir, fname))

    return paths


# ---------------------------------------------------------------------------
# Played-match detection
# ---------------------------------------------------------------------------

def load_played_matches(
    matches_csv: str,
    season_id: str,
    tier: Optional[int] = None,
) -> Set[FrozenSet[str]]:
    """
    Load the set of (order-independent) bey pairs that have been played.

    A match is considered **played** when it exists in ``matches.csv`` with
    a non-zero score (ScoreA + ScoreB > 0), the correct SeasonID, and the
    correct MatchType of "season".

    Args:
        matches_csv: Path to ``matches.csv``.
        season_id: Season identifier to filter on (e.g. "S2").
        tier: Optional tier number.  When *None*, all tiers are included.

    Returns:
        Set of frozensets ``{bey_a, bey_b}`` for each played match.
    """
    played: Set[FrozenSet[str]] = set()
    if not os.path.exists(matches_csv):
        return played

    with open(matches_csv, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("MatchType", "").lower() != "season":
                continue
            if row.get("SeasonID", "") != season_id:
                continue
            if tier is not None:
                row_tier = row.get("Tier", "")
                if str(row_tier) != str(tier):
                    continue

            score_a = int(row.get("ScoreA", 0) or 0)
            score_b = int(row.get("ScoreB", 0) or 0)
            if score_a + score_b == 0:
                continue  # 0-0 is not considered played

            bey_a = row.get("BeyA", "")
            bey_b = row.get("BeyB", "")
            if bey_a and bey_b:
                played.add(_match_pair_key(bey_a, bey_b))

    return played


def compute_remaining_fixtures(
    fixtures: List[Dict],
    played_set: Set[FrozenSet[str]],
) -> List[Dict]:
    """
    Return fixtures that have not yet been played.

    A fixture is considered unplayed when its (bey_a, bey_b) pair—in either
    order—is not present in *played_set*.

    Args:
        fixtures: Full list of fixture dicts from :func:`challonge_to_fixtures`.
        played_set: Set of frozensets returned by :func:`load_played_matches`.

    Returns:
        Filtered list containing only unplayed fixtures, preserving order.
    """
    remaining = []
    for fix in fixtures:
        pair = _match_pair_key(fix["bey_a"], fix["bey_b"])
        if pair not in played_set:
            remaining.append(fix)
    return remaining


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_fixtures_csv(
    fixtures: List[Dict],
    output_path: str,
    append: bool = False,
) -> None:
    """
    Write fixtures to a CSV in ``fixtures.csv`` format.

    Columns: ``FixtureID,Date,BeyA,BeyB,MatchType,SeasonID,Tier,Matchday``

    Args:
        fixtures: List of fixture dicts.
        output_path: Destination file path.
        append: When *True*, append to an existing file instead of overwriting.
    """
    fieldnames = ["FixtureID", "Date", "BeyA", "BeyB",
                  "MatchType", "SeasonID", "Tier", "Matchday"]

    mode = "a" if append else "w"
    file_exists = os.path.exists(output_path)

    with open(output_path, mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)

        # Write header only when creating a new file (or overwriting)
        if not append or not file_exists:
            writer.writeheader()

        for fix in fixtures:
            writer.writerow({
                "FixtureID": fix.get("fixture_id", ""),
                "Date": fix.get("date", ""),
                "BeyA": fix["bey_a"],
                "BeyB": fix["bey_b"],
                "MatchType": MATCH_TYPE,
                "SeasonID": fix["season_id"],
                "Tier": fix["tier"],
                "Matchday": fix.get("matchday", ""),
            })


def write_remaining_plan_csv(
    fixtures: List[Dict],
    output_path: str,
) -> None:
    """
    Write remaining fixtures as a Quick-Entry session CSV.

    The format matches the session matches format used by ``update_matches.py``::

        MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,MatchType,SeasonID,Tier,Matchday,arena

    Match IDs are sequential starting from M0001 (local to this file).
    Date, ScoreA, and ScoreB are left blank so the operator can fill them in
    before importing.

    Args:
        fixtures: List of remaining fixture dicts.
        output_path: Destination file path.
    """
    fieldnames = ["MatchID", "Date", "BeyA", "BeyB",
                  "ScoreA", "ScoreB", "MatchType", "SeasonID", "Tier", "Matchday", "arena"]

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for idx, fix in enumerate(fixtures, start=1):
            writer.writerow({
                "MatchID": f"M{idx:04d}",
                "Date": "",
                "BeyA": fix["bey_a"],
                "BeyB": fix["bey_b"],
                "ScoreA": "",
                "ScoreB": "",
                "MatchType": MATCH_TYPE,
                "SeasonID": fix["season_id"],
                "Tier": fix["tier"],
                "Matchday": fix.get("matchday", ""),
                "arena": ARENA,
            })


def write_remaining_plan_json(
    fixtures: List[Dict],
    output_path: str,
) -> None:
    """
    Write remaining fixtures as a JSON file.

    Useful for consumption by web-based tools or further processing.

    Args:
        fixtures: List of remaining fixture dicts.
        output_path: Destination file path.
    """
    out = []
    for idx, fix in enumerate(fixtures, start=1):
        out.append({
            "match_id": f"M{idx:04d}",
            "fixture_id": fix.get("fixture_id", ""),
            "bey_a": fix["bey_a"],
            "bey_b": fix["bey_b"],
            "match_type": MATCH_TYPE,
            "season_id": fix["season_id"],
            "tier": fix["tier"],
            "matchday": fix.get("matchday", None),
            "arena": ARENA,
        })

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# High-level operations
# ---------------------------------------------------------------------------

def update_fixtures_for_season(
    season_id: str,
    tier: Optional[int] = None,
    matches_csv: str = MATCHES_CSV,
    fixtures_csv: str = FIXTURES_CSV,
    api_jsons_dir: str = SEASON_API_JSONS_DIR,
) -> Dict:
    """
    Rebuild ``fixtures.csv`` from the Challonge API JSONs for a season.

    Loads all API JSON files for *season_id* (optionally limited to *tier*),
    parses every match (complete or open), and overwrites ``fixtures.csv``
    with the full schedule.

    Args:
        season_id: Season identifier (e.g. "S2").
        tier: Optional single tier to process.
        matches_csv: Path to ``matches.csv`` (used for ordering only).
        fixtures_csv: Destination path for ``fixtures.csv``.
        api_jsons_dir: Base directory containing season API JSON files.

    Returns:
        Summary dict with keys ``total``, ``by_tier``, ``output_path``.
    """
    api_paths = load_season_api_jsons(season_id, tier)
    if not api_paths:
        raise FileNotFoundError(
            f"No API JSON files found for season '{season_id}'"
            + (f" tier {tier}" if tier else "")
        )

    all_fixtures: List[Dict] = []
    for path in api_paths:
        all_fixtures.extend(challonge_to_fixtures(path))

    # Sort by matchday then tier desc (4 → 3 → 2 → 1)
    all_fixtures.sort(
        key=lambda f: (
            f.get("matchday", 0),
            -int(f.get("tier", 0)) if f.get("tier") is not None else 0,
        )
    )

    write_fixtures_csv(all_fixtures, fixtures_csv, append=False)

    by_tier: Dict[int, int] = {}
    for fix in all_fixtures:
        by_tier[fix["tier"]] = by_tier.get(fix["tier"], 0) + 1

    return {
        "total": len(all_fixtures),
        "by_tier": by_tier,
        "output_path": fixtures_csv,
    }


def generate_remaining_plan(
    season_id: str,
    tier: Optional[int] = None,
    matches_csv: str = MATCHES_CSV,
    api_jsons_dir: str = SEASON_API_JSONS_DIR,
    output_dir: Optional[str] = None,
    output_format: str = "csv",
) -> Dict:
    """
    Generate a Quick-Entry plan containing only unplayed matches.

    For each tier (or the specified *tier*), compares the Challonge schedule
    with matches already in ``matches.csv`` and writes a session-ready CSV
    (and optionally JSON) with the remaining fixtures.

    Output files are written to *output_dir* (defaults to the same directory
    as ``fixtures.csv``).  The file is named:

        ``remaining_{season_id_lower}[_t{tier}].csv``

    Args:
        season_id: Season identifier (e.g. "S2").
        tier: Optional single tier to process.
        matches_csv: Path to ``matches.csv``.
        api_jsons_dir: Base directory containing season API JSON files.
        output_dir: Directory to write output files.  Defaults to the
            ``matches`` data directory.
        output_format: ``"csv"``, ``"json"``, or ``"both"``.

    Returns:
        Summary dict with keys:
            ``total_scheduled``, ``played``, ``remaining``,
            ``by_tier``, ``output_files``.
    """
    if output_dir is None:
        output_dir = os.path.dirname(FIXTURES_CSV)

    api_paths = load_season_api_jsons(season_id, tier)
    if not api_paths:
        raise FileNotFoundError(
            f"No API JSON files found for season '{season_id}'"
            + (f" tier {tier}" if tier else "")
        )

    all_fixtures: List[Dict] = []
    all_remaining: List[Dict] = []
    by_tier: Dict[int, Dict] = {}

    for path in api_paths:
        fixtures = challonge_to_fixtures(path)
        if not fixtures:
            continue

        t = fixtures[0]["tier"]
        played_set = load_played_matches(matches_csv, season_id, t)
        remaining = compute_remaining_fixtures(fixtures, played_set)

        all_fixtures.extend(fixtures)
        all_remaining.extend(remaining)

        by_tier[t] = {
            "total": len(fixtures),
            "played": len(fixtures) - len(remaining),
            "remaining": len(remaining),
        }

    # Sort by matchday then tier desc (4 → 3 → 2 → 1)
    all_remaining.sort(
        key=lambda f: (
            f.get("matchday", 0),
            -int(f.get("tier", 0)) if f.get("tier") is not None else 0,
        )
    )

    output_files = []
    suffix = f"_t{tier}" if tier is not None else ""

    if output_format in ("csv", "both"):
        csv_path = os.path.join(
            output_dir, f"remaining_{season_id.lower()}{suffix}.csv"
        )
        write_remaining_plan_csv(all_remaining, csv_path)
        output_files.append(csv_path)

    if output_format in ("json", "both"):
        json_path = os.path.join(
            output_dir, f"remaining_{season_id.lower()}{suffix}.json"
        )
        write_remaining_plan_json(all_remaining, json_path)
        output_files.append(json_path)

    return {
        "total_scheduled": len(all_fixtures),
        "played": len(all_fixtures) - len(all_remaining),
        "remaining": len(all_remaining),
        "by_tier": by_tier,
        "output_files": output_files,
    }


def preview_season(
    season_id: str,
    tier: Optional[int] = None,
    matches_csv: str = MATCHES_CSV,
) -> Dict:
    """
    Return a summary of the season schedule without writing any files.

    Args:
        season_id: Season identifier (e.g. "S2").
        tier: Optional single tier to inspect.
        matches_csv: Path to ``matches.csv``.

    Returns:
        Summary dict (same structure as :func:`generate_remaining_plan` but
        without ``output_files``).
    """
    api_paths = load_season_api_jsons(season_id, tier)

    all_total = 0
    all_played = 0
    by_tier: Dict[int, Dict] = {}

    for path in api_paths:
        fixtures = challonge_to_fixtures(path)
        if not fixtures:
            continue

        t = fixtures[0]["tier"]
        played_set = load_played_matches(matches_csv, season_id, t)
        remaining = compute_remaining_fixtures(fixtures, played_set)

        played_count = len(fixtures) - len(remaining)
        all_total += len(fixtures)
        all_played += played_count

        by_tier[t] = {
            "total": len(fixtures),
            "played": played_count,
            "remaining": len(remaining),
        }

    return {
        "total_scheduled": all_total,
        "played": all_played,
        "remaining": all_total - all_played,
        "by_tier": by_tier,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_summary(summary: Dict, season_id: str, verbose: bool = True) -> None:
    """Pretty-print the season summary to stdout."""
    print(f"\n=== Season {season_id} – Fixture Summary ===")
    print(f"  Total scheduled : {summary['total_scheduled']}")
    print(f"  Played          : {summary['played']}")
    print(f"  Remaining       : {summary['remaining']}")

    if verbose and summary.get("by_tier"):
        print("\n  By Tier:")
        for t in sorted(summary["by_tier"]):
            info = summary["by_tier"][t]
            print(
                f"    Tier {t}: {info['played']}/{info['total']} played, "
                f"{info['remaining']} remaining"
            )

    if summary.get("output_files"):
        print("\n  Output files:")
        for path in summary["output_files"]:
            print(f"    {path}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Challonge Fixtures Integration – generate match schedules "
                    "from Challonge API data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview season S2 schedule (no files written)
  python -m src.season.challonge_fixtures --season S2 --preview

  # Rebuild fixtures.csv from Challonge API (all tiers)
  python -m src.season.challonge_fixtures --season S2 --update-fixtures

  # Generate remaining-match plan (CSV) for next session
  python -m src.season.challonge_fixtures --season S2 --generate-remaining

  # Single tier, JSON output
  python -m src.season.challonge_fixtures --season S2 --tier 1 --generate-remaining --format json
        """,
    )

    parser.add_argument(
        "--season",
        default=None,
        help=(
            "Season identifier, e.g. S2. If omitted, auto-detects current season "
            "(active season in seasons.json, else newest api_jsons directory)."
        ),
    )
    parser.add_argument(
        "--tier",
        type=int,
        default=None,
        help="Restrict to a single tier (1–4). Default: all tiers.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print a summary without writing any files.",
    )
    parser.add_argument(
        "--update-fixtures",
        action="store_true",
        help="Rebuild fixtures.csv from the Challonge API data.",
    )
    parser.add_argument(
        "--generate-remaining",
        action="store_true",
        help="Generate a Quick-Entry CSV with only unplayed matches.",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="csv",
        dest="output_format",
        help="Output format for --generate-remaining (default: csv).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output files (default: same as fixtures.csv).",
    )
    parser.add_argument(
        "--matches-csv",
        default=MATCHES_CSV,
        help="Path to matches.csv (default: repo default).",
    )
    parser.add_argument(
        "--fixtures-csv",
        default=FIXTURES_CSV,
        help="Path to fixtures.csv (default: repo default).",
    )

    args = parser.parse_args()

    if not args.preview and not args.update_fixtures and not args.generate_remaining:
        parser.error(
            "Specify at least one action: --preview, --update-fixtures, "
            "or --generate-remaining"
        )

    season_id = args.season.upper() if args.season else detect_current_season()

    if args.preview:
        summary = preview_season(season_id, args.tier, args.matches_csv)
        _print_summary(summary, season_id, verbose=True)

    if args.update_fixtures:
        print(f"Rebuilding fixtures.csv for season {season_id}…")
        summary = update_fixtures_for_season(
            season_id,
            tier=args.tier,
            matches_csv=args.matches_csv,
            fixtures_csv=args.fixtures_csv,
        )
        print(
            f"  Written {summary['total']} fixtures to {summary['output_path']}"
        )
        for t, count in sorted(summary["by_tier"].items()):
            print(f"    Tier {t}: {count} fixtures")

    if args.generate_remaining:
        print(f"Generating remaining-match plan for season {season_id}…")
        summary = generate_remaining_plan(
            season_id,
            tier=args.tier,
            matches_csv=args.matches_csv,
            output_dir=args.output_dir,
            output_format=args.output_format,
        )
        _print_summary(summary, season_id, verbose=True)


if __name__ == "__main__":
    main()
