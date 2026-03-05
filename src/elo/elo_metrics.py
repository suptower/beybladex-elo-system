#!/usr/bin/env python3
"""
ELO System Metrics Module for Beyblade ELO Rating System

Computes statistical metrics to evaluate the predictive quality of the ELO rating system
from elo_history.csv.  Only Xtreme arena matches are used (the arena where ELO rankings
are based).

Metrics calculated:
  - Prediction accuracy  – % of non-draw matches where the pre-match favourite won
  - Brier Score          – mean squared error of the predicted win probability
                           (0 = perfect, 0.25 = uninformed baseline, 1 = worst)
  - Log Loss             – mean cross-entropy of the predicted probability
                           (0 = perfect, ln(2) ≈ 0.693 = uninformed baseline)
  - Calibration          – actual win rate per predicted-probability decile
  - Total matches used   – size of the evaluation set
  - Spearman ρ           – rank correlation between final ELO and empirical win rate
                           (1 = perfect rank agreement, 0 = no relationship)

All metrics are computed from the pre-match expected probability (ExpA column) and the
binary win/loss outcome (ScoreA > ScoreB → outcome = 1).

Output Files:
  - docs/data/elo/elo_metrics.json
"""

import csv
import json
import math
import os
from collections import defaultdict

# Terminal colour helpers (graceful on systems without ANSI support)
if os.name == "nt":
    os.system("")
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# ── File paths ─────────────────────────────────────────────────────────────────
ELO_HISTORY_FILE = "./docs/data/elo/elo_history.csv"
OUTPUT_FILE = "./docs/data/elo/elo_metrics.json"

# ── Constants ──────────────────────────────────────────────────────────────────
ARENA_FILTER = "Xtreme"   # only the ranked arena
EPSILON = 1e-15      # clip probabilities away from 0/1 for log-loss
N_CALIB_BINS = 10         # decile calibration buckets
SPEARMAN_MIN_MATCHES = 5    # minimum matches per bey to include in Spearman calculation


def load_elo_history(filepath: str) -> list:
    rows = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def _rank_list(lst: list) -> list:
    """Return 1-based consecutive ranks for a list (no tie-handling; ties receive arbitrary ordering)."""
    sorted_idx = sorted(range(len(lst)), key=lambda i: lst[i])
    ranks = [0] * len(lst)
    for rank, idx in enumerate(sorted_idx):
        ranks[idx] = rank + 1
    return ranks


def compute_spearman(rows: list, arena: str = ARENA_FILTER) -> dict | None:
    """
    Compute Spearman rank correlation between each bey's final ELO and their
    empirical win rate, using only matches in *arena*.

    Returns a dict with keys: rho, n_beys, min_matches_filter
    Returns None if there are fewer than 3 qualifying beys.
    """
    # Collect per-bey stats: final ELO (last PostA/PostB in arena), wins, total
    bey_elo: dict = {}   # name → final ELO after their most recent arena match
    bey_wins: dict = defaultdict(int)
    bey_total: dict = defaultdict(int)

    for row in rows:
        if row.get("arena") != arena:
            continue
        bey_a = row.get("BeyA", "")
        bey_b = row.get("BeyB", "")
        try:
            score_a = int(row["ScoreA"])
            score_b = int(row["ScoreB"])
            post_a = float(row["PostA"])
            post_b = float(row["PostB"])
        except (ValueError, KeyError):
            continue

        bey_elo[bey_a] = post_a
        bey_elo[bey_b] = post_b
        bey_total[bey_a] += 1
        bey_total[bey_b] += 1
        if score_a > score_b:
            bey_wins[bey_a] += 1
        elif score_b > score_a:
            bey_wins[bey_b] += 1

    # Filter to beys with enough matches
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


def compute_metrics(rows: list) -> dict:
    """Return a dict with all evaluation metrics."""

    # ── Filter to Xtreme arena with valid prediction data ────────────────────
    filtered = []
    for row in rows:
        if row.get("arena") != ARENA_FILTER:
            continue
        try:
            exp_a = float(row["ExpA"])
            score_a = int(row["ScoreA"])
            score_b = int(row["ScoreB"])
        except (ValueError, KeyError):
            continue
        if score_a == score_b:       # skip draws (shouldn't occur but guard anyway)
            continue
        act_a_raw = row.get("ActA", "")
        try:
            act_a = float(act_a_raw) if act_a_raw != "" else None
        except ValueError:
            act_a = None
        filtered.append((exp_a, 1 if score_a > score_b else 0, act_a))

    n = len(filtered)
    if n == 0:
        return {"error": "No valid matches found"}

    # ── Core metrics ─────────────────────────────────────────────────────────
    brier_sum = 0.0
    log_loss_sum = 0.0
    correct = 0
    skipped_acc = 0  # matches where ELO had no preference (ExpA ≈ 0.5)
    margin_mse_sum = 0.0
    margin_mse_count = 0

    # Calibration: bucket by predicted-probability decile
    calib_buckets: dict = defaultdict(lambda: {"predicted_sum": 0.0, "wins": 0, "count": 0})

    for exp_a, outcome, act_a in filtered:
        # Brier score uses binary outcome: did the predicted favourite win?
        brier_sum += (exp_a - outcome) ** 2

        # Log-loss (binary outcome)
        p = max(min(exp_a, 1 - EPSILON), EPSILON)
        log_loss_sum += -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))

        # Accuracy (only when there was a clear pre-match favourite)
        if abs(exp_a - 0.5) > 1e-9:
            predicted_winner = 1 if exp_a > 0.5 else 0
            if predicted_winner == outcome:
                correct += 1
        else:
            skipped_acc += 1

        # Calibration bucket (decile 0–9)
        bucket = min(int(exp_a * N_CALIB_BINS), N_CALIB_BINS - 1)
        calib_buckets[bucket]["predicted_sum"] += exp_a
        calib_buckets[bucket]["wins"] += outcome
        calib_buckets[bucket]["count"] += 1

        # Margin MSE: MSE of E (win probability) vs S (continuous margin score).
        # Unlike binary Brier Score, this includes punishment for margin magnitude.
        # S can exceed [0, 1] for dominant results (>4-0 wins / <0-4 losses).
        if act_a is not None:
            margin_mse_sum += (exp_a - act_a) ** 2
            margin_mse_count += 1

    n_acc = n - skipped_acc
    accuracy = (correct / n_acc) if n_acc else None
    brier_score = brier_sum / n
    log_loss = log_loss_sum / n
    margin_mse = (margin_mse_sum / margin_mse_count) if margin_mse_count else None

    # Baseline Brier / log-loss for an uninformed model that always predicts 0.5
    baseline_brier = 0.25
    baseline_log_loss = math.log(2)

    # ── Calibration table ────────────────────────────────────────────────────
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

    # ── Spearman rank correlation: ELO rank vs empirical win-rate rank ────────
    spearman = compute_spearman(rows)

    return {
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
    print(f"{CYAN}  ELO System Metrics{RESET}")
    print(f"{CYAN}{'─' * 50}{RESET}\n")

    print(f"{YELLOW}Loading ELO history …{RESET}")
    rows = load_elo_history(ELO_HISTORY_FILE)
    print(f"  Total rows in file : {len(rows)}")

    print(f"{YELLOW}Computing metrics (arena = {ARENA_FILTER}) …{RESET}")
    metrics = compute_metrics(rows)

    if "error" in metrics:
        print(f"  ⚠  {metrics['error']}")
        return

    # Pretty-print summary
    print(f"\n  Matches evaluated  : {metrics['n_matches']}")
    print(f"  Accuracy           : {metrics['accuracy']:.1%}  "
          f"({metrics['n_accuracy_matches']} decisive matches)")
    print(f"  Brier Score        : {metrics['brier_score']:.4f}  "
          f"(baseline {metrics['brier_baseline']:.2f}  |  "
          f"skill {metrics['brier_skill']:+.2%})")
    print(f"  Log Loss           : {metrics['log_loss']:.4f}  "
          f"(baseline {metrics['log_loss_baseline']:.4f})")
    if metrics.get("margin_rmse") is not None:
        print(f"  Margin RMSE        : {metrics['margin_rmse']:.4f}  "
              f"(RMSE of E vs actual margin score S)")
    if metrics.get("spearman") is not None:
        sp = metrics["spearman"]
        print(f"  Spearman ρ (ELO vs win rate) : {sp['rho']:.4f}  "
              f"(n={sp['n_beys']} beys, min {sp['min_matches_filter']} matches)")

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump({"version": "V3", **metrics}, fh, indent=2)
    print(f"\n{GREEN}✔  Metrics written to {OUTPUT_FILE}{RESET}\n")


if __name__ == "__main__":
    main()
