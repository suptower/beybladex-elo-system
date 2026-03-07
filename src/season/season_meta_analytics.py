"""
Season Meta Analytics Module

Implements four major analytical extensions for season-level evaluation,
meta understanding, and predictive modeling:

1. Archetype-Based Season Analytics
   - Performance table per season & tier (avg winrate, PPR, Elo change, finish distribution)
   - Archetype vs Archetype win-rate matrix (season matches only)
   - Archetype meta evolution (matchday × archetype win-share time-series)
   - Archetype stability index (std-dev of per-Bey winrates within archetype)

2. Extended Power Ranking (Form-Based)
   - Composite PowerScore with configurable weights
   - Power Ranking table + rank vs Elo-rank delta

3. Title Probability Model (Monte Carlo Simulation)
   - Elo-based win probability with optional recent-form adjustment
   - 10,000-run simulation of remaining season fixtures
   - Per-Bey title / promotion / relegation / top-3 / full position distribution

4. Tier Elo Distribution & Strength Tracking
   - Per-tier, per-matchday mean / median / max / min Elo
   - Tier Strength Index (mean Elo)
   - Tier Competitiveness Index (IQR)

⚠️  All season-specific metrics use only matches whose match_type == "season".
    Global Elo is used as-is from the leaderboard.
"""

import os
import random
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import DATA_DIR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum number of season matches a Bey must have played to be included in
# archetype-level aggregation.
MIN_SEASON_MATCHES = 3

# Default weights for the Extended Power Score (Feature 2).
# All values must be positive; they are normalised to sum to 1 at runtime.
DEFAULT_POWER_SCORE_WEIGHTS: Dict[str, float] = {
    "season_winrate": 0.35,
    "points_per_round": 0.25,
    "global_elo_percentile": 0.20,
    "round_diff_per_match": 0.10,
    "recent_form": 0.10,
}

# Number of recent season matches used to derive the "recent form" component.
RECENT_FORM_MATCHES = 3

# Monte Carlo defaults
DEFAULT_SIMULATIONS = 10_000
DEFAULT_SEED = 42

# Season point awards (mirror season_manager.py)
POINTS_WIN = 3
POINTS_DOMINANT_WIN = 4
DOMINANT_WIN_THRESHOLD = 4  # loser score must be 0


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _is_season_match(match: Dict) -> bool:
    """Return True when a match dict represents a regular-season match."""
    return str(match.get("match_type", match.get("MatchType", ""))).lower() == "season"


def _match_tier(match: Dict) -> Optional[int]:
    """Extract tier from a match dict, returning None if absent or invalid."""
    raw = match.get("tier", match.get("Tier"))
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _season_points(score_a: int, score_b: int) -> Tuple[int, int]:
    """Compute season league points for a match result."""
    if score_a == score_b:
        return (0, 0)
    w, loser_score = (score_a, score_b) if score_a > score_b else (score_b, score_a)
    # Dominant win: winner scores ≥ DOMINANT_WIN_THRESHOLD and loser scores 0 (shutout)
    pts = POINTS_DOMINANT_WIN if (loser_score == 0 and w >= DOMINANT_WIN_THRESHOLD) else POINTS_WIN
    return (pts, 0) if score_a > score_b else (0, pts)


def _normalise_to_unit(values: Dict[str, float]) -> Dict[str, float]:
    """Min-max normalise a mapping of {key: value} to [0, 1]."""
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    span = hi - lo
    if span == 0:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / span for k, v in values.items()}


def _win_probability(elo_a: float, elo_b: float) -> float:
    """Elo-based win probability for A against B."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


# ---------------------------------------------------------------------------
# Feature 1 – Archetype-Based Season Analytics
# ---------------------------------------------------------------------------

def calculate_archetype_season_performance(
    matches: List[Dict],
    rpg_stats: Dict,
    season_id: Optional[str] = None,
    tier: Optional[int] = None,
) -> Dict:
    """
    Aggregate season performance statistics at the archetype level.

    Only matches with match_type == "season" (optionally filtered by season_id
    and/or tier) are considered.

    Args:
        matches: Raw match dictionaries (from matches.csv / season_data).
        rpg_stats: Bey → archetype mapping (from rpg_stats.json).
        season_id: Optional season filter (e.g. "S1").
        tier: Optional tier filter (1, 2, or 3).

    Returns:
        Dict keyed by archetype_id with aggregated season metrics.
    """
    # Build Bey → archetype mapping (skip "unknown")
    bey_archetype: Dict[str, str] = {}
    archetype_meta: Dict[str, Dict] = {}
    for bey, data in rpg_stats.items():
        arch = data.get("archetype", {})
        arch_id = arch.get("id", "unknown")
        if arch_id != "unknown":
            bey_archetype[bey] = arch_id
            archetype_meta[arch_id] = arch

    # Filter to season matches
    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
        and (tier is None or _match_tier(m) == tier)
    ]

    # Per-Bey accumulators (season only)
    bey_wins: Dict[str, int] = defaultdict(int)
    bey_losses: Dict[str, int] = defaultdict(int)
    bey_rounds_won: Dict[str, int] = defaultdict(int)
    bey_rounds_total: Dict[str, int] = defaultdict(int)
    bey_season_pts: Dict[str, int] = defaultdict(int)

    for m in season_matches:
        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))
        score_a = int(m.get("score_a", m.get("ScoreA", 0)))
        score_b = int(m.get("score_b", m.get("ScoreB", 0)))

        sp_a, sp_b = _season_points(score_a, score_b)

        bey_season_pts[bey_a] += sp_a
        bey_season_pts[bey_b] += sp_b

        total_rounds = score_a + score_b
        bey_rounds_total[bey_a] += total_rounds
        bey_rounds_total[bey_b] += total_rounds
        bey_rounds_won[bey_a] += score_a
        bey_rounds_won[bey_b] += score_b

        if score_a > score_b:
            bey_wins[bey_a] += 1
            bey_losses[bey_b] += 1
        elif score_b > score_a:
            bey_wins[bey_b] += 1
            bey_losses[bey_a] += 1

    # Group Beys by archetype; filter by minimum match count
    archetype_beys: Dict[str, List[str]] = defaultdict(list)
    for bey, arch_id in bey_archetype.items():
        total_m = bey_wins[bey] + bey_losses[bey]
        if total_m >= MIN_SEASON_MATCHES:
            archetype_beys[arch_id].append(bey)

    # Compute archetype-level aggregates
    result: Dict[str, Dict] = {}
    for arch_id, beys in archetype_beys.items():
        winrates = []
        ppr_list = []
        total_wins = 0
        total_matches = 0
        total_rounds_won = 0
        total_rounds = 0
        total_pts = 0

        for bey in beys:
            w = bey_wins[bey]
            losses = bey_losses[bey]
            m_count = w + losses
            if m_count == 0:
                continue
            wr = w / m_count
            winrates.append(wr)
            rounds_total = bey_rounds_total[bey]
            pts = bey_season_pts[bey]
            ppr = pts / rounds_total if rounds_total > 0 else 0.0
            ppr_list.append(ppr)
            total_wins += w
            total_matches += m_count
            total_rounds_won += bey_rounds_won[bey]
            total_rounds += rounds_total
            total_pts += pts

        if not winrates:
            continue

        avg_winrate = total_wins / total_matches if total_matches else 0.0
        avg_ppr = total_pts / total_rounds if total_rounds else 0.0
        stability = statistics.stdev(winrates) if len(winrates) > 1 else 0.0

        result[arch_id] = {
            "id": arch_id,
            "name": archetype_meta.get(arch_id, {}).get("name", arch_id),
            "icon": archetype_meta.get(arch_id, {}).get("icon", ""),
            "color": archetype_meta.get(arch_id, {}).get("color", ""),
            "bey_count": len(beys),
            "beys": beys,
            "avg_winrate": round(avg_winrate, 4),
            "avg_points_per_round": round(avg_ppr, 4),
            "stability_index": round(stability, 4),
            "total_season_matches": total_matches,
            "total_rounds": total_rounds,
        }

    return result


def calculate_archetype_matchup_matrix_season(
    matches: List[Dict],
    rpg_stats: Dict,
    season_id: Optional[str] = None,
) -> Dict:
    """
    Build an archetype × archetype win-rate matrix using season matches only.

    Args:
        matches: Raw match dictionaries.
        rpg_stats: Bey → archetype mapping.
        season_id: Optional season filter.

    Returns:
        Nested dict: matrix[arch_a][arch_b] = {wins, losses, total, winrate}.
    """
    bey_archetype: Dict[str, str] = {}
    for bey, data in rpg_stats.items():
        arch_id = data.get("archetype", {}).get("id", "unknown")
        if arch_id != "unknown":
            bey_archetype[bey] = arch_id

    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
    ]

    wins: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for m in season_matches:
        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))
        score_a = int(m.get("score_a", m.get("ScoreA", 0)))
        score_b = int(m.get("score_b", m.get("ScoreB", 0)))

        arch_a = bey_archetype.get(bey_a)
        arch_b = bey_archetype.get(bey_b)

        if not arch_a or not arch_b:
            continue

        totals[arch_a][arch_b] += 1
        totals[arch_b][arch_a] += 1

        if score_a > score_b:
            wins[arch_a][arch_b] += 1
        elif score_b > score_a:
            wins[arch_b][arch_a] += 1

    matrix: Dict[str, Dict] = {}
    for arch_a in totals:
        matrix[arch_a] = {}
        for arch_b in totals[arch_a]:
            total = totals[arch_a][arch_b]
            w = wins[arch_a][arch_b]
            matrix[arch_a][arch_b] = {
                "wins": w,
                "losses": total - w,
                "total": total,
                "winrate": round(w / total, 4) if total else 0.0,
            }

    return matrix


def calculate_archetype_meta_evolution(
    matches: List[Dict],
    rpg_stats: Dict,
    season_id: Optional[str] = None,
) -> Dict:
    """
    Compute per-matchday archetype win-share (meta evolution time-series).

    Returns:
        Dict: {matchday: {arch_id: share_of_wins (0-1)}}
    """
    bey_archetype: Dict[str, str] = {}
    for bey, data in rpg_stats.items():
        arch_id = data.get("archetype", {}).get("id", "unknown")
        if arch_id != "unknown":
            bey_archetype[bey] = arch_id

    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
    ]

    # wins_by_day[matchday][arch_id] = count
    wins_by_day: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for m in season_matches:
        matchday = m.get("matchday", m.get("Matchday"))
        if matchday is None:
            continue
        matchday = int(matchday)

        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))
        score_a = int(m.get("score_a", m.get("ScoreA", 0)))
        score_b = int(m.get("score_b", m.get("ScoreB", 0)))

        if score_a > score_b:
            winner = bey_a
        elif score_b > score_a:
            winner = bey_b
        else:
            continue  # draw – no win to assign

        arch = bey_archetype.get(winner)
        if arch:
            wins_by_day[matchday][arch] += 1

    evolution: Dict[int, Dict[str, float]] = {}
    for matchday, arch_wins in wins_by_day.items():
        total_wins = sum(arch_wins.values())
        if total_wins == 0:
            continue
        evolution[matchday] = {
            arch: round(count / total_wins, 4)
            for arch, count in arch_wins.items()
        }

    return evolution


def calculate_archetype_stability_index(
    archetype_season_stats: Dict,
    matches: List[Dict],
    rpg_stats: Dict,
    season_id: Optional[str] = None,
) -> Dict:
    """
    Compute the Archetype Stability Index for each archetype.

    Stability = std-dev of season win-rates of individual Beys in the archetype.
    Low deviation → consistently strong archetype.
    High deviation → dependent on individual outliers.

    Returns:
        Dict: {arch_id: {"stability_index": float, "bey_winrates": {bey: wr}}}
    """
    bey_archetype: Dict[str, str] = {}
    for bey, data in rpg_stats.items():
        arch_id = data.get("archetype", {}).get("id", "unknown")
        if arch_id != "unknown":
            bey_archetype[bey] = arch_id

    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
    ]

    bey_wins: Dict[str, int] = defaultdict(int)
    bey_losses: Dict[str, int] = defaultdict(int)
    for m in season_matches:
        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))
        score_a = int(m.get("score_a", m.get("ScoreA", 0)))
        score_b = int(m.get("score_b", m.get("ScoreB", 0)))
        if score_a > score_b:
            bey_wins[bey_a] += 1
            bey_losses[bey_b] += 1
        elif score_b > score_a:
            bey_wins[bey_b] += 1
            bey_losses[bey_a] += 1

    # Group qualifying Beys by archetype
    arch_bey_winrates: Dict[str, Dict[str, float]] = defaultdict(dict)
    for bey, arch_id in bey_archetype.items():
        if arch_id not in archetype_season_stats:
            continue
        total = bey_wins[bey] + bey_losses[bey]
        if total < MIN_SEASON_MATCHES:
            continue
        arch_bey_winrates[arch_id][bey] = bey_wins[bey] / total

    result: Dict[str, Dict] = {}
    for arch_id, bey_wr in arch_bey_winrates.items():
        winrates = list(bey_wr.values())
        stability = statistics.stdev(winrates) if len(winrates) > 1 else 0.0
        result[arch_id] = {
            "stability_index": round(stability, 4),
            "bey_winrates": {b: round(wr, 4) for b, wr in bey_wr.items()},
        }

    return result


# ---------------------------------------------------------------------------
# Feature 2 – Extended Power Ranking (Form-Based)
# ---------------------------------------------------------------------------

def calculate_power_score(
    bey: str,
    season_wins: int,
    season_matches: int,
    total_points_scored: int,
    total_rounds: int,
    round_diff: int,
    global_elo: float,
    recent_results: List[bool],
    all_elos: List[float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute the Extended Power Score for a single Bey.

    All five components are normalised to [0, 1] before weighting; caller must
    provide pre-computed normalisation bounds via *all_elos*.

    Args:
        bey: Bey name (unused in computation; kept for caller clarity).
        season_wins: Season wins count.
        season_matches: Season matches count.
        total_points_scored: Total round-points scored in season matches.
        total_rounds: Total rounds played in season matches.
        round_diff: (rounds_won − rounds_lost) for this Bey in season matches.
        global_elo: Current global Elo rating.
        recent_results: Boolean list of last RECENT_FORM_MATCHES outcomes
                        (True = win), most recent last.
        all_elos: All global Elo ratings across the field (for percentile).
        weights: Custom weight dict (keys must match DEFAULT_POWER_SCORE_WEIGHTS).
                 Missing keys fall back to defaults; weights are re-normalised.

    Returns:
        float: Power Score in [0, 100].
    """
    w = dict(DEFAULT_POWER_SCORE_WEIGHTS)
    if weights:
        for key, val in weights.items():
            if key in w:
                w[key] = val
    # Normalise weights to sum = 1
    total_w = sum(w.values())
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    # 1. Season win-rate
    season_wr = season_wins / season_matches if season_matches > 0 else 0.0

    # 2. Points per round
    ppr = total_points_scored / total_rounds if total_rounds > 0 else 0.0
    # Normalise PPR: assume range [0, max_possible_ppr]; use 1.0 as practical max
    norm_ppr = min(ppr, 1.0)

    # 3. Global Elo percentile
    if all_elos:
        rank = sum(1 for e in all_elos if e <= global_elo)
        elo_percentile = rank / len(all_elos)
    else:
        elo_percentile = 0.5

    # 4. Round differential per match
    round_diff_per_match = round_diff / season_matches if season_matches > 0 else 0.0
    # Normalise assuming practical range [-5, +5]
    norm_rdipm = (round_diff_per_match + 5.0) / 10.0
    norm_rdipm = max(0.0, min(1.0, norm_rdipm))

    # 5. Recent form (last N matches)
    if recent_results:
        recent_form = sum(1 for r in recent_results[-RECENT_FORM_MATCHES:] if r) / min(
            RECENT_FORM_MATCHES, len(recent_results)
        )
    else:
        recent_form = 0.0

    score = (
        w["season_winrate"] * season_wr
        + w["points_per_round"] * norm_ppr
        + w["global_elo_percentile"] * elo_percentile
        + w["round_diff_per_match"] * norm_rdipm
        + w["recent_form"] * recent_form
    )

    return round(score * 100.0, 2)


def generate_power_ranking(
    bey_season_data: Dict[str, Dict],
    global_leaderboard: Dict[str, Dict],
    matches: List[Dict],
    season_id: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    """
    Generate the Extended Power Ranking for all qualifying Beys.

    Args:
        bey_season_data: {bey: {wins, losses, points_scored, rounds, round_diff}}
                         (season-only statistics).
        global_leaderboard: {bey: {elo, …}} – global Elo ratings.
        matches: Raw match list (for recent form derivation).
        season_id: Optional filter.
        weights: Optional custom PowerScore weight overrides.

    Returns:
        List of dicts sorted by power_score descending, each containing:
            bey, power_score, power_rank, elo_rank, rank_delta.
    """
    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
    ]

    # Build recent match results per bey (chronological order preserved by list)
    recent_results_map: Dict[str, List[bool]] = defaultdict(list)
    for m in season_matches:
        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))
        score_a = int(m.get("score_a", m.get("ScoreA", 0)))
        score_b = int(m.get("score_b", m.get("ScoreB", 0)))
        recent_results_map[bey_a].append(score_a > score_b)
        recent_results_map[bey_b].append(score_b > score_a)

    all_elos = [v.get("elo", 1000) for v in global_leaderboard.values()]

    scores: Dict[str, float] = {}
    for bey, season_stats in bey_season_data.items():
        s_wins = season_stats.get("wins", 0)
        s_matches = season_stats.get("matches", 0)
        if s_matches < MIN_SEASON_MATCHES:
            continue
        pts_scored = season_stats.get("points_scored", 0)
        rounds_total = season_stats.get("rounds", 0)
        rd = season_stats.get("round_diff", 0)
        elo = global_leaderboard.get(bey, {}).get("elo", 1000)
        recent = recent_results_map.get(bey, [])

        scores[bey] = calculate_power_score(
            bey=bey,
            season_wins=s_wins,
            season_matches=s_matches,
            total_points_scored=pts_scored,
            total_rounds=rounds_total,
            round_diff=rd,
            global_elo=elo,
            recent_results=recent,
            all_elos=all_elos,
            weights=weights,
        )

    # Sort by PowerScore descending
    power_ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Elo ranking (global)
    elo_ranked = sorted(
        global_leaderboard.items(),
        key=lambda x: x[1].get("elo", 0),
        reverse=True,
    )
    elo_rank_map = {bey: rank for rank, (bey, _) in enumerate(elo_ranked, start=1)}

    result = []
    for power_rank, (bey, ps) in enumerate(power_ranked, start=1):
        elo_rank = elo_rank_map.get(bey, 0)
        result.append({
            "bey": bey,
            "power_score": ps,
            "power_rank": power_rank,
            "elo_rank": elo_rank,
            "rank_delta": elo_rank - power_rank,  # positive = power outranks elo
        })

    return result


# ---------------------------------------------------------------------------
# Feature 3 – Title Probability Model (Monte Carlo)
# ---------------------------------------------------------------------------

def calculate_win_probability(
    elo_a: float,
    elo_b: float,
    recent_form_a: float = 0.0,
    recent_form_b: float = 0.0,
    use_form_adjustment: bool = True,
) -> float:
    """
    Estimate A's win probability against B.

    Formula (with form adjustment enabled):
        P_elo = 1 / (1 + 10^((elo_b - elo_a) / 400))
        form_modifier = clip(recent_form_a - recent_form_b, -0.15, 0.15)
        P_adj = 0.85 × P_elo + 0.15 × (0.5 + form_modifier)

    Args:
        elo_a, elo_b: Elo ratings of contestants.
        recent_form_a, recent_form_b: Season win-rates in recent matches [0, 1].
        use_form_adjustment: Whether to apply form modifier (default True).

    Returns:
        float: Probability in (0, 1).
    """
    p_elo = _win_probability(elo_a, elo_b)

    if not use_form_adjustment:
        return p_elo

    form_modifier = max(-0.15, min(0.15, recent_form_a - recent_form_b))
    p_adj = 0.85 * p_elo + 0.15 * (0.5 + form_modifier)
    return max(0.01, min(0.99, p_adj))


def simulate_season_completion(
    standings: Dict[str, Dict],
    remaining_fixtures: List[Tuple[str, str]],
    elos: Dict[str, float],
    recent_form: Optional[Dict[str, float]] = None,
    n_simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
) -> Dict[str, List[int]]:
    """
    Monte Carlo simulation of remaining season fixtures.

    Args:
        standings: Current standings {bey: {season_points, point_diff, points_for}}.
        remaining_fixtures: List of (bey_a, bey_b) pairs yet to be played.
        elos: Global Elo ratings {bey: elo}.
        recent_form: Optional {bey: win_rate_last_n_matches} for form adjustment.
        n_simulations: Number of Monte Carlo iterations.
        seed: RNG seed for reproducibility.

    Returns:
        Dict: {bey: [final_position_count_per_position]}.
            position_distributions[bey][pos-1] = number of simulations
            where bey finished in position pos (1-indexed).
    """
    rng = random.Random(seed)
    all_beys = list(standings.keys())
    n_beys = len(all_beys)
    if n_beys == 0:
        return {}

    # Pre-compute win probabilities for each remaining fixture
    fixture_probs: List[Tuple[str, str, float]] = []
    for bey_a, bey_b in remaining_fixtures:
        elo_a = elos.get(bey_a, 1000.0)
        elo_b = elos.get(bey_b, 1000.0)
        form_a = (recent_form or {}).get(bey_a, 0.5)
        form_b = (recent_form or {}).get(bey_b, 0.5)
        p = calculate_win_probability(elo_a, elo_b, form_a, form_b,
                                      use_form_adjustment=recent_form is not None)
        fixture_probs.append((bey_a, bey_b, p))

    # position_counts[bey][position-1] += 1
    position_counts: Dict[str, List[int]] = {bey: [0] * n_beys for bey in all_beys}

    for _ in range(n_simulations):
        # Copy current standings
        sim: Dict[str, Dict] = {
            bey: {
                "season_points": int(data.get("season_points", 0)),
                "point_diff": int(data.get("point_diff", 0)),
                "points_for": int(data.get("points_for", 0)),
            }
            for bey, data in standings.items()
        }

        # Simulate each remaining fixture
        for bey_a, bey_b, p_a in fixture_probs:
            if rng.random() < p_a:
                winner, loser_name = bey_a, bey_b
                # Approximate: regular win = score 4-2 (2-point diff)
                sim[winner]["season_points"] += POINTS_WIN
                sim[winner]["point_diff"] += 2
                sim[winner]["points_for"] += 4
                sim[loser_name]["point_diff"] -= 2
                sim[loser_name]["points_for"] += 2
            else:
                winner, loser_name = bey_b, bey_a
                sim[winner]["season_points"] += POINTS_WIN
                sim[winner]["point_diff"] += 2
                sim[winner]["points_for"] += 4
                sim[loser_name]["point_diff"] -= 2
                sim[loser_name]["points_for"] += 2

        # Rank beys by season tiebreaker: season_points → point_diff → points_for → elo
        ranked = sorted(
            sim.items(),
            key=lambda x: (
                -x[1]["season_points"],
                -x[1]["point_diff"],
                -x[1]["points_for"],
                -elos.get(x[0], 1000),
            ),
        )

        for pos, (bey, _) in enumerate(ranked):
            position_counts[bey][pos] += 1

    return position_counts


def calculate_title_probabilities(
    position_counts: Dict[str, List[int]],
    n_simulations: int = DEFAULT_SIMULATIONS,
    promotion_spots: int = 2,
    relegation_start: int = 9,
) -> List[Dict]:
    """
    Convert raw simulation position counts into probability percentages.

    Args:
        position_counts: Output of simulate_season_completion().
        n_simulations: Total simulations run (for denominator).
        promotion_spots: How many top positions count as "promoted".
        relegation_start: First position (1-indexed) that triggers relegation.

    Returns:
        List of dicts sorted by title_probability descending, each with:
            bey, title_prob, promotion_prob, relegation_prob, top3_prob,
            position_distribution (list of % per final position).
    """
    result = []
    for bey, counts in position_counts.items():
        n = n_simulations or 1
        pos_dist = [round(c / n * 100, 2) for c in counts]
        title_prob = pos_dist[0] if pos_dist else 0.0
        promo_prob = round(sum(pos_dist[:promotion_spots]), 2) if pos_dist else 0.0
        top3_prob = round(sum(pos_dist[:3]), 2) if len(pos_dist) >= 3 else promo_prob
        relg_prob = round(sum(pos_dist[relegation_start - 1:]), 2) if len(pos_dist) >= relegation_start else 0.0

        result.append({
            "bey": bey,
            "title_prob": title_prob,
            "promotion_prob": promo_prob,
            "top3_prob": top3_prob,
            "relegation_prob": relg_prob,
            "position_distribution": pos_dist,
        })

    result.sort(key=lambda x: x["title_prob"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Feature 4 – Tier Elo Distribution & Strength Tracking
# ---------------------------------------------------------------------------

def calculate_tier_elo_timeseries(
    matches: List[Dict],
    elo_history: Dict[str, Dict],
    season_id: Optional[str] = None,
) -> Dict:
    """
    Compute per-tier, per-matchday Elo distribution statistics.

    Args:
        matches: Raw match dictionaries (must include tier and matchday fields).
        elo_history: Pre-match Elo snapshots keyed by match_id.
                     {match_id: {bey: pre_elo}}.
        season_id: Optional season filter.

    Returns:
        Dict: {tier: {matchday: {mean, median, max, min, q1, q3, iqr}}}
    """
    season_matches = [
        m for m in matches
        if _is_season_match(m)
        and (season_id is None or m.get("season_id", m.get("SeasonID")) == season_id)
    ]

    # tier → matchday → list of pre-match Elo values
    tier_md_elos: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))

    for m in season_matches:
        tier_raw = m.get("tier", m.get("Tier"))
        matchday_raw = m.get("matchday", m.get("Matchday"))
        match_id = m.get("match_id", m.get("MatchID", ""))

        if tier_raw is None or matchday_raw is None:
            continue

        try:
            tier_val = int(tier_raw)
            md_val = int(matchday_raw)
        except (ValueError, TypeError):
            continue

        elo_snap = elo_history.get(match_id, {})
        bey_a = m.get("bey_a", m.get("BeyA", ""))
        bey_b = m.get("bey_b", m.get("BeyB", ""))

        for bey in (bey_a, bey_b):
            if bey in elo_snap:
                tier_md_elos[tier_val][md_val].append(float(elo_snap[bey]))

    result: Dict[int, Dict[int, Dict]] = {}
    for tier_val, md_data in tier_md_elos.items():
        result[tier_val] = {}
        for md, elos in sorted(md_data.items()):
            if not elos:
                continue
            sorted_elos = sorted(elos)
            q1_idx = len(sorted_elos) // 4
            q3_idx = (3 * len(sorted_elos)) // 4
            q1 = sorted_elos[q1_idx]
            q3 = sorted_elos[min(q3_idx, len(sorted_elos) - 1)]
            result[tier_val][md] = {
                "mean": round(statistics.mean(elos), 2),
                "median": round(statistics.median(elos), 2),
                "max": round(max(elos), 2),
                "min": round(min(elos), 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(q3 - q1, 2),
            }

    return result


def calculate_tier_strength_index(tier_elo_timeseries: Dict) -> Dict[int, float]:
    """
    Tier Strength Index = mean of all matchday-mean Elo values for a tier.

    Args:
        tier_elo_timeseries: Output of calculate_tier_elo_timeseries().

    Returns:
        Dict: {tier: strength_index}
    """
    result: Dict[int, float] = {}
    for tier_val, md_data in tier_elo_timeseries.items():
        means = [stats["mean"] for stats in md_data.values() if stats]
        if means:
            result[tier_val] = round(statistics.mean(means), 2)
    return result


def calculate_tier_competitiveness_index(tier_elo_timeseries: Dict) -> Dict[int, float]:
    """
    Tier Competitiveness Index = mean of all matchday-IQR values for a tier.

    Low IQR → highly competitive (Beys clustered together).
    High IQR → stratified tier (large spread).

    Args:
        tier_elo_timeseries: Output of calculate_tier_elo_timeseries().

    Returns:
        Dict: {tier: competitiveness_index}
    """
    result: Dict[int, float] = {}
    for tier_val, md_data in tier_elo_timeseries.items():
        iqrs = [stats["iqr"] for stats in md_data.values() if stats]
        if iqrs:
            result[tier_val] = round(statistics.mean(iqrs), 2)
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _load_matches_csv(matches_file: str) -> List[Dict]:
    """Load all matches from CSV into a list of normalised dicts."""
    import csv
    rows: List[Dict] = []
    if not os.path.exists(matches_file):
        return rows
    with open(matches_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "match_id": row.get("MatchID", ""),
                "bey_a": row.get("BeyA", ""),
                "bey_b": row.get("BeyB", ""),
                "score_a": int(row.get("ScoreA", 0) or 0),
                "score_b": int(row.get("ScoreB", 0) or 0),
                "match_type": row.get("MatchType", ""),
                "season_id": row.get("SeasonID", ""),
                "tier": int(row["Tier"]) if row.get("Tier") else None,
                "matchday": int(row["Matchday"]) if row.get("Matchday") else None,
            })
    return rows


def _load_elo_history(elo_history_file: str) -> Dict[str, Dict[str, float]]:
    """Build {match_id: {bey: pre_elo}} from elo_history.csv."""
    import csv
    result: Dict[str, Dict[str, float]] = {}
    if not os.path.exists(elo_history_file):
        return result
    with open(elo_history_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row.get("MatchID", "")
            bey_a = row.get("BeyA", "")
            bey_b = row.get("BeyB", "")
            try:
                pre_a = float(row.get("PreA", 1000))
                pre_b = float(row.get("PreB", 1000))
            except (ValueError, TypeError):
                pre_a = pre_b = 1000.0
            if mid:
                result[mid] = {bey_a: pre_a, bey_b: pre_b}
    return result


def _load_leaderboard(leaderboard_file: str) -> Dict[str, Dict]:
    """Build {bey: {elo, wins, losses, matches}} from leaderboard.csv."""
    import csv
    result: Dict[str, Dict] = {}
    if not os.path.exists(leaderboard_file):
        return result
    with open(leaderboard_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("Name", "")
            if not name:
                continue
            try:
                elo = float(str(row.get("ELO", 1000)).replace(",", "."))
            except (ValueError, TypeError):
                elo = 1000.0
            result[name] = {"elo": elo}
    return result


def _load_table_snapshots(data_dir: str, season_id: str) -> Dict[int, Dict[str, Dict]]:
    """
    Load the latest standings per tier from table_snapshots_{season_id}_tier{n}.csv.

    Returns:
        {tier: {bey: {season_points, point_diff, points_for, wins, losses, matches}}}
    """
    import csv
    result: Dict[int, Dict[str, Dict]] = {}
    for tier in (1, 2, 3):
        fname = os.path.join(data_dir, f"table_snapshots_{season_id}_tier{tier}.csv")
        if not os.path.exists(fname):
            continue
        rows_by_md: Dict[int, List[Dict]] = {}
        with open(fname, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                md_raw = row.get("matchday", "")
                if not md_raw:
                    continue
                md = int(md_raw)
                rows_by_md.setdefault(md, []).append(row)
        if not rows_by_md:
            continue
        latest = rows_by_md[max(rows_by_md)]
        tier_standings: Dict[str, Dict] = {}
        for row in latest:
            bey = row.get("bey", "")
            if not bey:
                continue
            points_for = int(row.get("points_for", 0) or 0)
            points_against = int(row.get("points_against", 0) or 0)
            point_diff = int(row.get("point_diff", 0) or 0)
            tier_standings[bey] = {
                "season_points": int(row.get("season_points", 0) or 0),
                "point_diff": point_diff,
                "points_for": points_for,
                "wins": int(row.get("wins", 0) or 0),
                "losses": int(row.get("losses", 0) or 0),
                "matches": int(row.get("matches", 0) or 0),
                # Aliases used by generate_power_ranking()
                "points_scored": points_for,
                "rounds": points_for + points_against,
                "round_diff": point_diff,
            }
        result[tier] = tier_standings
    return result


def _build_remaining_fixtures(
    matches: List[Dict],
    tier_standings: Dict[str, Dict],
    season_id: str,
    tier: int,
    total_matchdays: int,
) -> List[Tuple[str, str]]:
    """
    Infer remaining (unplayed) fixtures from the round-robin schedule.

    Every pair (bey_a, bey_b) in the tier plays once; already-played pairs
    are excluded.
    """
    played: set = set()
    for m in matches:
        if (
            m.get("match_type", "").lower() == "season"
            and m.get("season_id", "") == season_id
            and m.get("tier") == tier
        ):
            a = m["bey_a"]
            b = m["bey_b"]
            played.add((min(a, b), max(a, b)))

    beys = list(tier_standings.keys())
    remaining = []
    for i in range(len(beys)):
        for j in range(i + 1, len(beys)):
            pair = (min(beys[i], beys[j]), max(beys[i], beys[j]))
            if pair not in played:
                remaining.append((beys[i], beys[j]))
    return remaining


def main() -> None:
    """CLI entry point: compute and export season meta analytics to JSON."""
    import argparse
    import json as json_mod

    parser = argparse.ArgumentParser(
        description="Advanced Season Meta Analytics – compute & export JSON"
    )
    parser.add_argument("--data-dir", default=DATA_DIR,
                        help="Directory containing input CSV/JSON files")
    parser.add_argument("--output-dir", default=DATA_DIR,
                        help="Directory to write output JSON files")
    parser.add_argument("--season", default=None,
                        help="Season ID to process (default: all active seasons)")
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS,
                        help="Number of Monte Carlo simulations")
    args = parser.parse_args()

    data_dir = args.data_dir
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # --- Load shared data -------------------------------------------------
    matches = _load_matches_csv(os.path.join(data_dir, "matches.csv"))
    elo_history = _load_elo_history(os.path.join(data_dir, "elo_history.csv"))
    leaderboard = _load_leaderboard(os.path.join(data_dir, "leaderboard.csv"))
    rpg_stats_path = os.path.join(data_dir, "rpg_stats.json")
    rpg_stats: Dict = {}
    if os.path.exists(rpg_stats_path):
        with open(rpg_stats_path, encoding="utf-8") as f:
            rpg_stats = json_mod.load(f)

    # Determine which seasons to process
    seasons_path = os.path.join(data_dir, "seasons.json")
    all_season_ids: List[str] = []
    if args.season:
        all_season_ids = [args.season]
    elif os.path.exists(seasons_path):
        with open(seasons_path, encoding="utf-8") as f:
            seasons_cfg = json_mod.load(f)
        all_season_ids = list(seasons_cfg.keys())
    else:
        # Fallback: derive from matches
        all_season_ids = sorted({
            m["season_id"] for m in matches
            if m.get("match_type", "").lower() == "season" and m.get("season_id")
        })

    for season_id in all_season_ids:
        print(f"Processing season {season_id}…")
        season_matches = [
            m for m in matches
            if m.get("match_type", "").lower() == "season"
            and m.get("season_id") == season_id
        ]
        if not season_matches:
            print(f"  No season matches found for {season_id}, skipping.")
            continue

        # ----- Feature 1: Archetype analytics --------------------------------
        archetype_perf = calculate_archetype_season_performance(
            matches, rpg_stats, season_id=season_id
        )
        archetype_matrix = calculate_archetype_matchup_matrix_season(
            matches, rpg_stats, season_id=season_id
        )
        archetype_evolution = calculate_archetype_meta_evolution(
            matches, rpg_stats, season_id=season_id
        )
        archetype_stability = calculate_archetype_stability_index(
            archetype_perf, matches, rpg_stats, season_id=season_id
        )

        # ----- Feature 2: Power Ranking --------------------------------------
        # Aggregate per-bey season stats across all tiers for power ranking
        bey_season_data: Dict[str, Dict] = {}
        for tier in (1, 2, 3):
            tier_standings = _load_table_snapshots(data_dir, season_id).get(tier, {})
            for bey, stats in tier_standings.items():
                if bey not in bey_season_data:
                    bey_season_data[bey] = stats
                else:
                    # Merge across tiers (unusual but safe)
                    for k in ("wins", "losses", "matches", "points_scored", "rounds"):
                        bey_season_data[bey][k] = bey_season_data[bey].get(k, 0) + stats.get(k, 0)

        power_ranking = generate_power_ranking(
            bey_season_data, leaderboard, matches, season_id=season_id
        )

        # ----- Feature 3: Title Probability per tier -------------------------
        tier_standings_all = _load_table_snapshots(data_dir, season_id)
        title_probs_per_tier: Dict[int, List[Dict]] = {}
        for tier, tier_standings in tier_standings_all.items():
            if not tier_standings:
                continue
            elos_tier = {b: leaderboard.get(b, {}).get("elo", 1000.0) for b in tier_standings}
            remaining = _build_remaining_fixtures(
                matches, tier_standings, season_id, tier, total_matchdays=9
            )
            position_counts = simulate_season_completion(
                tier_standings, remaining, elos_tier,
                n_simulations=args.simulations, seed=DEFAULT_SEED,
            )
            title_probs = calculate_title_probabilities(
                position_counts, n_simulations=args.simulations
            )
            title_probs_per_tier[tier] = title_probs

        # ----- Feature 4: Tier Elo timeseries --------------------------------
        tier_elo_ts = calculate_tier_elo_timeseries(matches, elo_history, season_id=season_id)
        tier_strength = calculate_tier_strength_index(tier_elo_ts)
        tier_comp = calculate_tier_competitiveness_index(tier_elo_ts)

        # ----- Assemble output -----------------------------------------------
        output = {
            "season_id": season_id,
            "n_simulations": args.simulations,
            "archetype_analytics": {
                "performance": archetype_perf,
                "matchup_matrix": archetype_matrix,
                "meta_evolution": {
                    str(md): shares
                    for md, shares in archetype_evolution.items()
                },
                "stability": archetype_stability,
            },
            "power_ranking": power_ranking,
            "title_probabilities": {
                str(tier): probs
                for tier, probs in title_probs_per_tier.items()
            },
            "tier_elo": {
                "timeseries": {
                    str(tier): {
                        str(md): stats
                        for md, stats in md_data.items()
                    }
                    for tier, md_data in tier_elo_ts.items()
                },
                "strength_index": {str(k): v for k, v in tier_strength.items()},
                "competitiveness_index": {str(k): v for k, v in tier_comp.items()},
            },
        }

        out_file = os.path.join(output_dir, f"season_meta_analytics_{season_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json_mod.dump(output, f, indent=2, ensure_ascii=False)
        print(f"  Exported → {out_file}")

    print("Season meta analytics complete.")


if __name__ == "__main__":
    main()
