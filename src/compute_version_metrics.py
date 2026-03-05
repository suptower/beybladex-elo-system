#!/usr/bin/env python3
"""
Compute ELO system metrics for archived V1 and V2 ELO systems.

Runs each historical ELO version in memory on the current match data (Xtreme arena only),
computes the same evaluation metrics as elo_metrics.py, and saves them to:
  - docs/data/elo_metrics_v1.json
  - docs/data/elo_metrics_v2.json

These are loaded by the frontend ELO System page to display per-version statistics
when the V1 or V2 tab is selected.

Usage:
    python src/compute_version_metrics.py
"""

import csv
import json
import math
import os
from collections import defaultdict

# Terminal colour helpers
if os.name == "nt":
    os.system("")
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# ── File paths ─────────────────────────────────────────────────────────────────
MATCHES_FILE = "./docs/data/matches.csv"
OUTPUT_V1 = "./docs/data/elo_metrics_v1.json"
OUTPUT_V2 = "./docs/data/elo_metrics_v2.json"

# ── Constants ──────────────────────────────────────────────────────────────────
START_ELO = 1000
ARENA_FILTER = "Xtreme"
EPSILON = 1e-15
N_CALIB_BINS = 10
SPEARMAN_MIN_MATCHES = 5

# ── V1 / V2 shared K-factor tiers ─────────────────────────────────────────────
K_LEARNING = 40
K_INTERMEDIATE = 24
K_EXPERIENCED = 12


def dynamic_k(n_matches: int) -> float:
    if n_matches < 6:
        return K_LEARNING
    elif n_matches < 15:
        return K_INTERMEDIATE
    return K_EXPERIENCED


def expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


# ── V1 scoring ─────────────────────────────────────────────────────────────────
def v1_score(sa: int, sb: int):
    """V1: proportional scoring — sa/(sa+sb)."""
    total = sa + sb
    if total == 0:
        return 0.5, 0.5
    return sa / total, sb / total


# ── V2 scoring ─────────────────────────────────────────────────────────────────
WIN_THRESHOLD = 4
MAX_POINT_DIFF = 6
OVERKILL_WEIGHT = 0.25
BASE_WIN = 0.75


def v2_score(sa: int, sb: int):
    """V2: dominance-based scoring."""
    if sa == sb:
        return 0.5, 0.5
    winner_score = max(sa, sb)
    loser_score = min(sa, sb)
    diff = winner_score - loser_score

    if diff >= 4:
        dominance = 1.0
    else:
        dominance = diff / 4.0

    score_winner = BASE_WIN + (1.0 - BASE_WIN) * dominance

    if winner_score > WIN_THRESHOLD:
        overkill_points = winner_score - WIN_THRESHOLD
        max_overkill = MAX_POINT_DIFF - WIN_THRESHOLD  # 2
        score_winner += (overkill_points / max_overkill) * OVERKILL_WEIGHT

    score_loser = 1.0 - score_winner

    if sa > sb:
        return score_winner, score_loser
    else:
        return score_loser, score_winner


# ── Match loading ─────────────────────────────────────────────────────────────
def load_xtreme_matches(filepath: str) -> list:
    """Load and sort Xtreme-only matches from matches.csv."""
    matches = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            arena = row.get("arena", "Xtreme")
            if arena != ARENA_FILTER:
                continue
            try:
                sa = int(row["ScoreA"])
                sb = int(row["ScoreB"])
            except (ValueError, KeyError):
                continue
            matches.append({
                "match_id": row.get("MatchID", ""),
                "date": row.get("Date", ""),
                "bey_a": row["BeyA"],
                "bey_b": row["BeyB"],
                "score_a": sa,
                "score_b": sb,
                "match_type": row.get("MatchType", "exhibition"),
            })
    matches.sort(key=lambda m: m["date"])
    return matches


# ── ELO simulation ─────────────────────────────────────────────────────────────
def simulate_elo(matches: list, score_fn) -> list:
    """
    Simulate ELO for a list of Xtreme-only matches using the given score function.

    Returns a list of dicts with the fields needed by compute_metrics():
        arena, BeyA, BeyB, ScoreA, ScoreB, ExpA, ActA, PostA, PostB
    """
    elos: dict = defaultdict(lambda: START_ELO)
    n_matches: dict = defaultdict(int)
    rows = []

    for m in matches:
        a, b = m["bey_a"], m["bey_b"]
        sa, sb = m["score_a"], m["score_b"]

        pre_a, pre_b = elos[a], elos[b]
        exp_a = expected(pre_a, pre_b)

        ka = dynamic_k(n_matches[a])
        kb = dynamic_k(n_matches[b])

        act_a, act_b = score_fn(sa, sb)

        new_a = pre_a + ka * (act_a - exp_a)
        new_b = pre_b + kb * (act_b - (1.0 - exp_a))

        elos[a] = new_a
        elos[b] = new_b
        n_matches[a] += 1
        n_matches[b] += 1

        rows.append({
            "arena": ARENA_FILTER,
            "BeyA": a,
            "BeyB": b,
            "ScoreA": sa,
            "ScoreB": sb,
            "ExpA": str(exp_a),
            "ActA": str(act_a),
            "PostA": str(new_a),
            "PostB": str(new_b),
        })

    return rows


# ── Metrics (mirrors elo_metrics.compute_metrics) ─────────────────────────────
def _rank_list(lst: list) -> list:
    sorted_idx = sorted(range(len(lst)), key=lambda i: lst[i])
    ranks = [0] * len(lst)
    for rank, idx in enumerate(sorted_idx):
        ranks[idx] = rank + 1
    return ranks


def compute_spearman(rows: list) -> dict | None:
    bey_elo: dict = {}
    bey_wins: dict = defaultdict(int)
    bey_total: dict = defaultdict(int)

    for row in rows:
        bey_a = row["BeyA"]
        bey_b = row["BeyB"]
        sa = int(row["ScoreA"])
        sb = int(row["ScoreB"])
        post_a = float(row["PostA"])
        post_b = float(row["PostB"])

        bey_elo[bey_a] = post_a
        bey_elo[bey_b] = post_b
        bey_total[bey_a] += 1
        bey_total[bey_b] += 1
        if sa > sb:
            bey_wins[bey_a] += 1
        elif sb > sa:
            bey_wins[bey_b] += 1

    beys = [
        (name, bey_elo[name], bey_wins[name] / bey_total[name])
        for name in bey_elo
        if bey_total[name] >= SPEARMAN_MIN_MATCHES
    ]

    n = len(beys)
    if n < 3:
        return None

    elos = [b[1] for b in beys]
    winrates = [b[2] for b in beys]
    elo_ranks = _rank_list(elos)
    wr_ranks = _rank_list(winrates)
    d2 = sum((er - wr) ** 2 for er, wr in zip(elo_ranks, wr_ranks))
    rho = 1 - 6 * d2 / (n * (n ** 2 - 1))

    return {
        "rho": round(rho, 4),
        "n_beys": n,
        "min_matches_filter": SPEARMAN_MIN_MATCHES,
    }


def compute_metrics(rows: list, version_label: str) -> dict:
    filtered = []
    for row in rows:
        try:
            exp_a = float(row["ExpA"])
            sa = int(row["ScoreA"])
            sb = int(row["ScoreB"])
        except (ValueError, KeyError):
            continue
        if sa == sb:
            continue
        act_a_raw = row.get("ActA", "")
        try:
            act_a = float(act_a_raw) if act_a_raw != "" else None
        except ValueError:
            act_a = None
        filtered.append((exp_a, 1 if sa > sb else 0, act_a))

    n = len(filtered)
    if n == 0:
        return {"error": "No valid matches found"}

    brier_sum = 0.0
    log_loss_sum = 0.0
    correct = 0
    skipped_acc = 0
    margin_mse_sum = 0.0
    margin_mse_count = 0
    calib_buckets: dict = defaultdict(lambda: {"predicted_sum": 0.0, "wins": 0, "count": 0})

    for exp_a, outcome, act_a in filtered:
        brier_sum += (exp_a - outcome) ** 2
        p = max(min(exp_a, 1 - EPSILON), EPSILON)
        log_loss_sum += -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))

        if abs(exp_a - 0.5) > 1e-9:
            if (1 if exp_a > 0.5 else 0) == outcome:
                correct += 1
        else:
            skipped_acc += 1

        bucket = min(int(exp_a * N_CALIB_BINS), N_CALIB_BINS - 1)
        calib_buckets[bucket]["predicted_sum"] += exp_a
        calib_buckets[bucket]["wins"] += outcome
        calib_buckets[bucket]["count"] += 1

        if act_a is not None:
            margin_mse_sum += (exp_a - act_a) ** 2
            margin_mse_count += 1

    n_acc = n - skipped_acc
    accuracy = (correct / n_acc) if n_acc else None
    brier_score = brier_sum / n
    log_loss = log_loss_sum / n
    margin_mse = (margin_mse_sum / margin_mse_count) if margin_mse_count else None

    baseline_brier = 0.25
    baseline_log_loss = math.log(2)

    calibration = []
    for bucket in sorted(calib_buckets.keys()):
        b = calib_buckets[bucket]
        cnt = b["count"]
        mean_pred = b["predicted_sum"] / cnt if cnt else 0.0
        actual_rate = b["wins"] / cnt if cnt else 0.0
        calibration.append({
            "bucket": bucket,
            "label": f"{int(bucket * 10)}-{int(bucket * 10 + 10)}%",
            "mean_predicted": round(mean_pred, 4),
            "actual_win_rate": round(actual_rate, 4),
            "count": cnt,
        })

    spearman = compute_spearman(rows)

    return {
        "version": version_label,
        "n_matches": n,
        "n_accuracy_matches": n_acc,
        "accuracy": round(accuracy, 4) if accuracy is not None else None,
        "brier_score": round(brier_score, 4),
        "brier_baseline": round(baseline_brier, 4),
        "brier_skill": round(1 - brier_score / baseline_brier, 4),
        "log_loss": round(log_loss, 4),
        "log_loss_baseline": round(baseline_log_loss, 4),
        "margin_mse": round(margin_mse, 4) if margin_mse is not None else None,
        "margin_rmse": round(margin_mse ** 0.5, 4) if margin_mse is not None else None,
        "spearman": spearman,
        "calibration": calibration,
        "arena_filter": ARENA_FILTER,
    }


def main() -> None:
    print(f"\n{CYAN}{'─' * 50}{RESET}")
    print(f"{CYAN}  Historical ELO Version Metrics{RESET}")
    print(f"{CYAN}{'─' * 50}{RESET}\n")

    print(f"{YELLOW}Loading Xtreme matches from {MATCHES_FILE} …{RESET}")
    matches = load_xtreme_matches(MATCHES_FILE)
    print(f"  Xtreme matches loaded : {len(matches)}")

    for version, score_fn, output_file in [
        ("V1", v1_score, OUTPUT_V1),
        ("V2", v2_score, OUTPUT_V2),
    ]:
        print(f"\n{YELLOW}Simulating {version} ELO and computing metrics …{RESET}")
        rows = simulate_elo(matches, score_fn)
        metrics = compute_metrics(rows, version)

        if "error" in metrics:
            print(f"  ⚠  {metrics['error']}")
            continue

        print(f"  Matches : {metrics['n_matches']}")
        print(f"  Accuracy: {metrics['accuracy']:.1%}  ({metrics['n_accuracy_matches']} decisive matches)")
        print(f"  Brier   : {metrics['brier_score']:.4f}  (skill {metrics['brier_skill']:+.2%})")
        print(f"  Log Loss: {metrics['log_loss']:.4f}")
        if metrics.get("spearman"):
            sp = metrics["spearman"]
            print(f"  Spearman ρ: {sp['rho']:.4f}  (n={sp['n_beys']} beys)")

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, indent=2)
        print(f"{GREEN}✔  {version} metrics written to {output_file}{RESET}")

    print()


if __name__ == "__main__":
    main()
