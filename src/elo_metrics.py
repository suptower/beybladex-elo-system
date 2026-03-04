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

All metrics are computed from the pre-match expected probability (ExpA column) and the
binary win/loss outcome (ScoreA > ScoreB → outcome = 1).

Output Files:
  - docs/data/elo_metrics.json
"""

import csv
import json
import math
import os
from collections import defaultdict

# Terminal colour helpers (graceful on systems without ANSI support)
if os.name == "nt":
    os.system("")
RESET  = "\033[0m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"

# ── File paths ─────────────────────────────────────────────────────────────────
ELO_HISTORY_FILE = "./docs/data/elo_history.csv"
OUTPUT_FILE      = "./docs/data/elo_metrics.json"

# ── Constants ──────────────────────────────────────────────────────────────────
ARENA_FILTER   = "Xtreme"   # only the ranked arena
EPSILON        = 1e-15      # clip probabilities away from 0/1 for log-loss
N_CALIB_BINS   = 10         # decile calibration buckets


def load_elo_history(filepath: str) -> list:
    rows = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


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
        filtered.append((exp_a, 1 if score_a > score_b else 0))

    n = len(filtered)
    if n == 0:
        return {"error": "No valid matches found"}

    # ── Core metrics ─────────────────────────────────────────────────────────
    brier_sum    = 0.0
    log_loss_sum = 0.0
    correct      = 0
    skipped_acc  = 0  # matches where ELO had no preference (ExpA ≈ 0.5)

    # Calibration: bucket by predicted-probability decile
    calib_buckets: dict = defaultdict(lambda: {"predicted_sum": 0.0, "wins": 0, "count": 0})

    for exp_a, outcome in filtered:
        # Brier score (both teams contribute, but by symmetry using A is sufficient)
        brier_sum += (exp_a - outcome) ** 2

        # Log-loss
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
        calib_buckets[bucket]["wins"]          += outcome
        calib_buckets[bucket]["count"]         += 1

    n_acc = n - skipped_acc
    accuracy   = (correct / n_acc) if n_acc else None
    brier_score = brier_sum / n
    log_loss    = log_loss_sum / n

    # Baseline Brier / log-loss for an uninformed model that always predicts 0.5
    baseline_brier    = 0.25
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

    return {
        "n_matches":          n,
        "n_accuracy_matches": n_acc,
        "accuracy":           round(accuracy, 4) if accuracy is not None else None,
        "brier_score":        round(brier_score, 4),
        "brier_baseline":     round(baseline_brier, 4),
        "brier_skill":        round(1 - brier_score / baseline_brier, 4),
        "log_loss":           round(log_loss, 4),
        "log_loss_baseline":  round(baseline_log_loss, 4),
        "calibration":        calibration,
        "arena_filter":       ARENA_FILTER,
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

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"\n{GREEN}✔  Metrics written to {OUTPUT_FILE}{RESET}\n")


if __name__ == "__main__":
    main()
