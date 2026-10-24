"""
Challenge League Module for Season 4+

This module implements the Qualification Pool management, weighted selection,
group assignment, and match processing for the Challenge League.

Key Features:
- Qualification Pool construction (all Beys not in regular Tiers I-III)
- Weighted random sampling without replacement (reproducible with random seed)
- Configurable selection weights favoring less active/previously missed Beys
- Group assignment via ELO-based snake seeding (default) or random draw
- Phase 1: 4 Groups of 6 Beys playing 3 Swiss rounds (top 2 advance per group)
- Phase 2: Final Swiss Stage for 8 qualifiers starting from 0 points (top 5 qualify for Tier III)
- Promotion and return-to-pool resolution
"""

import math
import random
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Union

from src.season.season_manager import calculate_season_points


DEFAULT_CHALLENGE_LEAGUE_SIZE = 24
DEFAULT_GROUPS_COUNT = 4
DEFAULT_BEYS_PER_GROUP = 6
DEFAULT_GROUP_SWISS_ROUNDS = 3
DEFAULT_FINAL_QUALIFIERS = 8
DEFAULT_FINAL_SWISS_ROUNDS = 3
DEFAULT_PROMOTIONS_TO_TIER3 = 5


def get_relevant_participation_counts(
    matches: List[Dict],
    qualification_match_types: Optional[Set[str]] = None,
) -> Dict[str, int]:
    """
    Count relevant prior participations for Beys.

    Per Season 4 spec: uses relevant participation (Challenge League or
    prior qualification matches) rather than unrestricted all-time match count,
    so Beys that competed in regular tiers are not unfairly penalized.

    Args:
        matches: List of all match dictionaries from matches.csv.
        qualification_match_types: Set of MatchType strings to consider
            relevant (defaults to {"qualification", "challenge_group", "challenge_final"}).

    Returns:
        Dict mapping bey_name -> relevant match count.
    """
    if qualification_match_types is None:
        qualification_match_types = {
            "qualification",
            "challenge_group",
            "challenge_final",
            "challenge_league",
        }

    counts: Dict[str, int] = defaultdict(int)
    for match in matches:
        m_type = str(match.get("match_type") or match.get("MatchType", "")).lower()
        if m_type in qualification_match_types:
            bey_a = match.get("bey_a") or match.get("BeyA")
            bey_b = match.get("bey_b") or match.get("BeyB")
            if bey_a:
                counts[bey_a] += 1
            if bey_b:
                counts[bey_b] += 1

    return dict(counts)


def calculate_selection_weight(
    bey_name: str,
    relevant_matches: int = 0,
    missed_previous_challenge: bool = False,
    missed_seasons_count: int = 0,
    config: Optional[Dict] = None,
) -> float:
    """
    Calculate sampling weight for a Bey in the Qualification Pool.

    Baseline formula:
        weight = 1.0 / (1.0 + relevant_matches)

    Optional configurable multipliers:
        - missed_previous_challenge bonus (e.g. 1.5)
        - missed_seasons_count bonus (e.g. 1.0 + 0.2 * missed_seasons)

    Args:
        bey_name: Name of the Bey.
        relevant_matches: Relevant prior matches played.
        missed_previous_challenge: True if the Bey did not play in the prior Challenge League.
        missed_seasons_count: Number of consecutive seasons missed.
        config: Optional configuration dictionary.

    Returns:
        Calculated non-negative float weight.
    """
    cfg = config or {}
    prev_cl_mult = cfg.get("missed_previous_cl_multiplier", 1.5)
    season_missed_mult_step = cfg.get("missed_season_step_multiplier", 0.2)

    base_weight = 1.0 / (1.0 + max(0, relevant_matches))

    multiplier = 1.0
    if missed_previous_challenge:
        multiplier *= prev_cl_mult
    if missed_seasons_count > 0:
        multiplier *= (1.0 + missed_seasons_count * season_missed_mult_step)

    return max(0.0001, base_weight * multiplier)


def select_challenge_league_beys(
    qualification_pool: List[Union[Dict, str]],
    count: int = DEFAULT_CHALLENGE_LEAGUE_SIZE,
    seed: Optional[int] = None,
    participation_counts: Optional[Dict[str, int]] = None,
    config: Optional[Dict] = None,
) -> List[Dict]:
    """
    Select distinct Beys from the Qualification Pool using weighted random
    sampling without replacement.

    Requirements:
    - Exactly `count` distinct Beys must be selected (or all if pool < count).
    - A Bey must not be selected more than once.
    - Reproducible when an explicit random seed is supplied.

    Args:
        qualification_pool: List of Bey dicts (with 'bey' and 'elo') or list of strings.
        count: Number of Beys to select (default 24).
        seed: Optional random seed for deterministic reproduction.
        participation_counts: Mapping of bey -> relevant match count.
        config: Optional weights and bonus configuration.

    Returns:
        List of selected Bey dictionaries, with keys:
            - 'bey': Bey name
            - 'elo': ELO rating
            - 'weight': Computed selection weight
            - 'selection_order': 1-based order drawn
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    p_counts = participation_counts or {}

    # Normalize pool entries to dicts: {"bey": str, "elo": float}
    pool_entries: List[Dict] = []
    seen = set()
    for item in qualification_pool:
        if isinstance(item, dict):
            name = item.get("bey") or item.get("name") or ""
            elo = float(item.get("elo", 1000.0) or 1000.0)
            missed_prev = bool(item.get("missed_previous_challenge", False))
            missed_seasons = int(item.get("missed_seasons_count", 0))
        else:
            name = str(item)
            elo = 1000.0
            missed_prev = False
            missed_seasons = 0

        if name and name not in seen:
            seen.add(name)
            rel_m = p_counts.get(name, 0)
            w = calculate_selection_weight(
                name,
                relevant_matches=rel_m,
                missed_previous_challenge=missed_prev,
                missed_seasons_count=missed_seasons,
                config=config,
            )
            pool_entries.append({
                "bey": name,
                "elo": elo,
                "relevant_matches": rel_m,
                "weight": w,
            })

    target_count = min(count, len(pool_entries))
    selected: List[Dict] = []
    candidates = list(pool_entries)

    for step in range(1, target_count + 1):
        total_w = sum(c["weight"] for c in candidates)
        if total_w <= 0:
            # Fallback to uniform if all weights zero
            pick_idx = rng.randrange(len(candidates))
        else:
            r = rng.uniform(0, total_w)
            cumulative = 0.0
            pick_idx = 0
            for idx, cand in enumerate(candidates):
                cumulative += cand["weight"]
                if cumulative >= r:
                    pick_idx = idx
                    break

        chosen = candidates.pop(pick_idx)
        chosen["selection_order"] = step
        selected.append(chosen)

    return selected


def assign_challenge_groups(
    selected_beys: List[Union[Dict, str]],
    method: str = "snake_elo",
    elo_lookup: Optional[Dict[str, float]] = None,
    seed: Optional[int] = None,
) -> Dict[str, List[Dict]]:
    """
    Assign the selected Challenge League Beys into 4 groups of 6.

    Supported methods:
    - 'snake_elo' (Default): Sorts Beys by ELO descending, then applies snake draft
      across Groups A, B, C, D to balance group strength:
        Round 1: A, B, C, D
        Round 2: D, C, B, A
        Round 3: A, B, C, D
        Round 4: D, C, B, A
        Round 5: A, B, C, D
        Round 6: D, C, B, A
    - 'random': Uniform random distribution into 4 groups.

    Args:
        selected_beys: List of 24 selected Bey dicts or names.
        method: 'snake_elo' or 'random'.
        elo_lookup: Optional dict of bey_name -> ELO rating.
        seed: Optional random seed for reproducible random assignment.

    Returns:
        Dict mapping group name ("A", "B", "C", "D") to list of Bey dicts.
    """
    elos = elo_lookup or {}

    # Normalize to dicts
    entries: List[Dict] = []
    for item in selected_beys:
        if isinstance(item, dict):
            name = item.get("bey") or item.get("name") or ""
            elo = float(item.get("elo") if item.get("elo") is not None else elos.get(name, 1000.0))
            d = dict(item)
            d["bey"] = name
            d["elo"] = elo
            entries.append(d)
        else:
            name = str(item)
            elo = float(elos.get(name, 1000.0))
            entries.append({"bey": name, "elo": elo})

    group_names = ["A", "B", "C", "D"]
    groups: Dict[str, List[Dict]] = {g: [] for g in group_names}

    if method == "random":
        rng = random.Random(seed) if seed is not None else random.Random()
        shuffled = list(entries)
        rng.shuffle(shuffled)
        for i, entry in enumerate(shuffled):
            g = group_names[i % len(group_names)]
            groups[g].append(entry)
    else:
        # Default: ELO-based snake seeding
        sorted_entries = sorted(entries, key=lambda x: x["elo"], reverse=True)
        num_groups = len(group_names)

        for i, entry in enumerate(sorted_entries):
            round_idx = i // num_groups
            pos_in_round = i % num_groups
            if round_idx % 2 == 0:
                # Forward: A, B, C, D
                group_key = group_names[pos_in_round]
            else:
                # Reverse (snake): D, C, B, A
                group_key = group_names[num_groups - 1 - pos_in_round]

            groups[group_key].append(entry)

    return groups


def calculate_league_table(
    matches: List[Dict],
    expected_beys: Optional[List[str]] = None,
    rounds_data: Optional[Dict[str, List[Dict]]] = None,
) -> List[Dict]:
    """
    Calculate standings table for a list of matches (Group or Swiss).

    Scoring:
    - Win: 3 points
    - Dominant win (opponent scored 0, e.g. 4-0, 5-0): 4 points
    - Loss: 0 points

    Ranking order:
    1. Season Points (desc)
    2. Point Difference (desc)
    3. Points For (desc)
    4. ELO (desc)

    Args:
        matches: List of match dictionaries with score_a, score_b, bey_a, bey_b.
        expected_beys: Optional list of Beys that should be in the table even with 0 matches.
        rounds_data: Optional mapping of match_id -> round dicts for rw/rl.

    Returns:
        List of standings dicts sorted by ranking criteria, with 1-based position.
    """
    standings: Dict[str, Dict] = defaultdict(lambda: {
        "bey": "",
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "season_points": 0,
        "points_for": 0,
        "points_against": 0,
        "point_diff": 0,
        "elo": 1000.0,
        "rw": 0,
        "rl": 0,
    })

    if expected_beys:
        for b in expected_beys:
            standings[b]["bey"] = b

    for match in matches:
        bey_a = match.get("bey_a") or match.get("BeyA") or ""
        bey_b = match.get("bey_b") or match.get("BeyB") or ""
        if not bey_a or not bey_b:
            continue

        score_a = int(match.get("score_a") or match.get("ScoreA") or 0)
        score_b = int(match.get("score_b") or match.get("ScoreB") or 0)

        # Skip unplayed matches (0-0)
        if score_a == 0 and score_b == 0:
            continue

        sp_a, sp_b = calculate_season_points(score_a, score_b)

        elo_a = float(match.get("elo_a") or 1000.0)
        elo_b = float(match.get("elo_b") or 1000.0)

        for bey, score, opp_score, sp, elo in [
            (bey_a, score_a, score_b, sp_a, elo_a),
            (bey_b, score_b, score_a, sp_b, elo_b),
        ]:
            st = standings[bey]
            st["bey"] = bey
            st["matches"] += 1
            st["season_points"] += sp
            st["points_for"] += score
            st["points_against"] += opp_score
            st["elo"] = elo
            if score > opp_score:
                st["wins"] += 1
            elif opp_score > score:
                st["losses"] += 1

        if rounds_data:
            match_id = match.get("match_id") or match.get("MatchID") or ""
            for rnd in rounds_data.get(match_id, []):
                winner = rnd.get("winner")
                if winner == bey_a:
                    standings[bey_a]["rw"] += 1
                    standings[bey_b]["rl"] += 1
                elif winner == bey_b:
                    standings[bey_b]["rw"] += 1
                    standings[bey_a]["rl"] += 1

    table = list(standings.values())
    for entry in table:
        entry["point_diff"] = entry["points_for"] - entry["points_against"]
        total_r = entry["rw"] + entry["rl"]
        entry["ppr"] = round(entry["points_for"] / total_r, 2) if total_r > 0 else 0.0
        entry["ppw"] = round(entry["points_for"] / entry["wins"], 2) if entry["wins"] > 0 else 0.0

    table.sort(key=lambda x: (
        -x["season_points"],
        -x["point_diff"],
        -x["points_for"],
        -x["elo"],
    ))

    for idx, entry in enumerate(table, 1):
        entry["position"] = idx

    return table


def process_challenge_league(
    matches: List[Dict],
    season_id: str,
    groups: Optional[Dict[str, List[Dict]]] = None,
    rounds_data: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """
    Process Challenge League matches and compute group stage + final Swiss standings.

    Specification:
    - Phase 1: 4 Groups of 6 Beys. Top 2 advance from each group (8 qualifiers).
    - Phase 2: Final Swiss stage of 8 Beys. Points RESET to zero.
    - Final Outcome:
      - Top 5: Promoted to Tier III next season.
      - Positions 6-8: Returned to Qualification Pool next season.

    Args:
        matches: List of all matches.
        season_id: Season identifier (e.g. "S4").
        groups: Optional dict of group_name -> list of Bey dicts.
        rounds_data: Optional rounds data mapping.

    Returns:
        Dict containing:
            - 'groups': Dict mapping group_id -> standings list
            - 'group_qualifiers': List of 8 Bey names advancing to Phase 2
            - 'final_swiss': Standings list of 8 qualifiers
            - 'promoted_to_tier3': List of top 5 Bey names
            - 'returned_to_pool': List of Bey names returning to Qualification Pool
    """
    # Filter Challenge League matches
    cl_matches = [
        m for m in matches
        if str(m.get("season_id") or m.get("SeasonID", "")).upper() == season_id.upper()
        and str(m.get("match_type") or m.get("MatchType", "")).lower() in (
            "challenge_group",
            "challenge_final",
            "challenge_league",
        )
    ]

    # Process Group Stage (Phase 1)
    group_tables: Dict[str, List[Dict]] = {}
    group_qualifiers: List[str] = []
    group_eliminated: List[str] = []

    group_keys = ["A", "B", "C", "D"]
    for g_id in group_keys:
        expected = [b["bey"] for b in groups.get(g_id, [])] if groups and g_id in groups else None

        # Filter matches for this group:
        # Check tier field or match_type
        g_matches = [
            m for m in cl_matches
            if str(m.get("match_type") or m.get("MatchType", "")).lower() == "challenge_group"
            and str(m.get("tier") or m.get("Tier", "")).upper() == g_id
        ]
        # Also include generic challenge matches between Beys of this group if tier wasn't tagged
        if not g_matches and expected:
            exp_set = set(expected)
            g_matches = [
                m for m in cl_matches
                if (m.get("bey_a") in exp_set and m.get("bey_b") in exp_set)
                and str(m.get("match_type") or m.get("MatchType", "")).lower() != "challenge_final"
            ]

        table = calculate_league_table(g_matches, expected_beys=expected, rounds_data=rounds_data)
        group_tables[g_id] = table

        # Top 2 advance
        for entry in table[:2]:
            group_qualifiers.append(entry["bey"])
        for entry in table[2:]:
            group_eliminated.append(entry["bey"])

    # Process Final Swiss Stage (Phase 2)
    # Filter final swiss matches
    final_matches = [
        m for m in cl_matches
        if str(m.get("match_type") or m.get("MatchType", "")).lower() == "challenge_final"
    ]
    if not final_matches and group_qualifiers:
        qual_set = set(group_qualifiers)
        final_matches = [
            m for m in cl_matches
            if (m.get("bey_a") in qual_set and m.get("bey_b") in qual_set)
            and str(m.get("match_type") or m.get("MatchType", "")).lower() not in ("challenge_group", "season")
        ]

    # Standings in Phase 2 start strictly with ZERO points (matches only from final_matches)
    final_swiss_table = calculate_league_table(
        final_matches,
        expected_beys=group_qualifiers if group_qualifiers else None,
        rounds_data=rounds_data,
    )

    promoted_to_tier3 = [entry["bey"] for entry in final_swiss_table[:DEFAULT_PROMOTIONS_TO_TIER3]]
    final_eliminated = [entry["bey"] for entry in final_swiss_table[DEFAULT_PROMOTIONS_TO_TIER3:]]

    returned_to_pool = final_eliminated + group_eliminated

    return {
        "groups": group_tables,
        "group_qualifiers": group_qualifiers,
        "final_swiss": final_swiss_table,
        "promoted_to_tier3": promoted_to_tier3,
        "final_eliminated": final_eliminated,
        "group_eliminated": group_eliminated,
        "returned_to_pool": returned_to_pool,
    }
