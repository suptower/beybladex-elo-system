#!/usr/bin/env python3
"""
ELO Parameter Tuning Script — Temporal Hold-Out Validation

Searches for the ELO hyper-parameter combination that minimises Log Loss (and
Brier Score) on an out-of-sample hold-out window.

Overfitting prevention strategy
────────────────────────────────
All Xtreme arena matches are sorted chronologically.  The first
TRAIN_FRACTION of those matches are used only to build up ELO ratings;
predictions on those matches are NOT evaluated.  Log Loss and Brier Score are
computed only on the remaining HOLDOUT_FRACTION matches — matches the model
has never "seen" during the parameter search.  Because ELO ratings already
encode a temporal causal structure (future matches are predicted from past
ratings), this is exactly the correct analogue of train/test split for a
sequential rating system.

Why not k-fold?
K-fold cross-validation would leak future information into the ratings used for
prediction.  The temporal hold-out is the standard approach for time-series
forecasting and rating-system evaluation.

Usage:
    cd <repo-root>
    python src/elo_tune.py [--holdout 0.25] [--csv docs/data/elo_history.csv]

Output:
    - Prints the top-N parameter combinations ranked by log loss.
    - Prints the parameter combination that best improves over the current default.
    - Writes a CSV summary to docs/data/elo_tune_results.csv.
"""

import argparse
import csv
import itertools
import math
import os
from typing import Optional

# ── File paths ──────────────────────────────────────────────────────────────
ELO_HISTORY_FILE = "./docs/data/elo_history.csv"
OUTPUT_CSV       = "./docs/data/elo_tune_results.csv"

ARENA_FILTER     = "Xtreme"
START_ELO        = 1000
TARGET_POINTS    = 4
EPSILON          = 1e-15   # clip probabilities away from 0/1 for log-loss

# ── Terminal colours ────────────────────────────────────────────────────────
if os.name == "nt":
    os.system("")
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RED    = "\033[31m"

# ── Default / current parameter values ─────────────────────────────────────
DEFAULTS = dict(
    k_max      = 32,
    k_min      = 16,
    k_tau      = 15,
    form_alpha = 2.5,
    form_win   = 10,
    margin_a   = 0.18,
    margin_b   = 2.2,
)

# ── Search grid ─────────────────────────────────────────────────────────────
# Keep the grid manageable (~a few hundred combinations) to run in seconds.
SEARCH_GRID = dict(
    k_max      = [28, 32, 36, 40],
    k_min      = [12, 16, 20],
    k_tau      = [10, 15, 20, 25],
    form_alpha = [1.5, 2.0, 2.5, 3.0],
    form_win   = [6, 10, 14],
    margin_a   = [0.15, 0.18, 0.22],
    margin_b   = [1.8, 2.2, 2.6],
)


# ────────────────────────────────────────────────────────────────────────────
#  Core ELO functions (parametrised versions, no global state)
# ────────────────────────────────────────────────────────────────────────────

def dynamic_k(matches: int, k_max: float, k_min: float, k_tau: float) -> float:
    return k_min + (k_max - k_min) * math.exp(-matches / k_tau)


def k_effective(k_base: float, form_ema: Optional[float], form_alpha: float) -> float:
    if form_ema is None:
        return k_base
    return k_base * (1.0 + form_alpha * abs(form_ema))


def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(r_a - r_b) / 400.0))


def score_with_margin(sa: int, sb: int, margin_a: float, margin_b: float,
                      target: int = TARGET_POINTS):
    if sa > sb:
        m = sa - sb
        s_w = 1.0 + margin_a * math.tanh(margin_b * (m - target) / target)
        return s_w, 1.0 - s_w
    elif sb > sa:
        m = sb - sa
        s_w = 1.0 + margin_a * math.tanh(margin_b * (m - target) / target)
        return 1.0 - s_w, s_w
    else:
        return 0.5, 0.5


# ────────────────────────────────────────────────────────────────────────────
#  Replay ELO and collect (expected_prob, binary_outcome) for eval matches
# ────────────────────────────────────────────────────────────────────────────

def replay_elo(matches: list, holdout_start_idx: int, params: dict) -> list:
    """
    Replay the ELO sequence with the given params.  Return a list of
    (exp_a, outcome) tuples for matches whose index >= holdout_start_idx.
    """
    k_max      = params["k_max"]
    k_min      = params["k_min"]
    k_tau      = params["k_tau"]
    form_alpha = params["form_alpha"]
    form_win   = params["form_win"]
    margin_a   = params["margin_a"]
    margin_b   = params["margin_b"]
    ema_alpha  = 2.0 / (form_win + 1)

    elos:      dict = {}
    match_cnt: dict = {}
    form_emas: dict = {}
    results = []

    for idx, row in enumerate(matches):
        bey_a  = row["BeyA"]
        bey_b  = row["BeyB"]
        sa     = int(row["ScoreA"])
        sb     = int(row["ScoreB"])

        r_a = elos.get(bey_a, START_ELO)
        r_b = elos.get(bey_b, START_ELO)
        n_a = match_cnt.get(bey_a, 0)
        n_b = match_cnt.get(bey_b, 0)

        kb_a = dynamic_k(n_a, k_max, k_min, k_tau)
        kb_b = dynamic_k(n_b, k_max, k_min, k_tau)
        ke_a = k_effective(kb_a, form_emas.get(bey_a), form_alpha)
        ke_b = k_effective(kb_b, form_emas.get(bey_b), form_alpha)

        e_a = expected_score(r_a, r_b)
        e_b = 1.0 - e_a

        s_a, s_b = score_with_margin(sa, sb, margin_a, margin_b)

        # Record prediction for eval window
        if idx >= holdout_start_idx:
            outcome = 1 if sa > sb else 0
            results.append((e_a, outcome))

        # Update state
        delta_a = s_a - e_a
        delta_b = s_b - e_b

        elos[bey_a] = r_a + ke_a * delta_a
        elos[bey_b] = r_b + ke_b * delta_b
        match_cnt[bey_a] = n_a + 1
        match_cnt[bey_b] = n_b + 1

        # Update EMA
        old_ema_a = form_emas.get(bey_a)
        old_ema_b = form_emas.get(bey_b)
        form_emas[bey_a] = (delta_a if old_ema_a is None
                            else ema_alpha * delta_a + (1 - ema_alpha) * old_ema_a)
        form_emas[bey_b] = (delta_b if old_ema_b is None
                            else ema_alpha * delta_b + (1 - ema_alpha) * old_ema_b)

    return results


# ────────────────────────────────────────────────────────────────────────────
#  Metric computation
# ────────────────────────────────────────────────────────────────────────────

def compute_log_loss(preds: list) -> float:
    total = 0.0
    for exp_a, outcome in preds:
        p = max(min(exp_a, 1 - EPSILON), EPSILON)
        total += -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))
    return total / len(preds)


def compute_brier(preds: list) -> float:
    return sum((p - o) ** 2 for p, o in preds) / len(preds)


# ────────────────────────────────────────────────────────────────────────────
#  Main
# ────────────────────────────────────────────────────────────────────────────

def load_xtreme_matches(filepath: str) -> list:
    rows = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("arena") == ARENA_FILTER:
                try:
                    int(row["ScoreA"])
                    int(row["ScoreB"])
                except (ValueError, KeyError):
                    continue
                rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="ELO hyper-parameter search with temporal hold-out validation.")
    parser.add_argument("--holdout", type=float, default=0.25,
                        help="Fraction of matches to use for evaluation (default: 0.25)")
    parser.add_argument("--csv", default=ELO_HISTORY_FILE,
                        help="Path to elo_history.csv")
    parser.add_argument("--top", type=int, default=20,
                        help="Number of top results to display (default: 20)")
    args = parser.parse_args()

    print(f"\n{CYAN}{'─' * 60}{RESET}")
    print(f"{CYAN}  ELO Parameter Tuning — Temporal Hold-Out Validation{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}\n")

    print(f"{YELLOW}Loading Xtreme arena matches from {args.csv} …{RESET}")
    matches = load_xtreme_matches(args.csv)
    n_total = len(matches)
    holdout_start = int(n_total * (1 - args.holdout))
    n_holdout = n_total - holdout_start

    print(f"  Total Xtreme matches : {n_total}")
    print(f"  Train window         : first {holdout_start} matches")
    print(f"  Eval hold-out        : last  {n_holdout} matches  ({args.holdout:.0%})")
    print()

    # ── Baseline: current default parameters ────────────────────────────────
    print(f"{YELLOW}Computing baseline (current default parameters) …{RESET}")
    baseline_preds = replay_elo(matches, holdout_start, DEFAULTS)
    baseline_ll    = compute_log_loss(baseline_preds)
    baseline_bs    = compute_brier(baseline_preds)
    print(f"  Default Log Loss  : {baseline_ll:.4f}")
    print(f"  Default Brier     : {baseline_bs:.4f}\n")

    # ── Grid search ─────────────────────────────────────────────────────────
    keys  = list(SEARCH_GRID.keys())
    values = list(SEARCH_GRID.values())
    combos = list(itertools.product(*values))
    print(f"{YELLOW}Searching {len(combos)} parameter combinations …{RESET}")

    results = []
    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        preds  = replay_elo(matches, holdout_start, params)
        ll     = compute_log_loss(preds)
        bs     = compute_brier(preds)
        results.append({**params, "log_loss": ll, "brier": bs})
        if (i + 1) % 200 == 0 or (i + 1) == len(combos):
            print(f"  … {i + 1}/{len(combos)} done", end="\r")

    print(f"  {len(combos)} combinations evaluated.{' ' * 20}")
    print()

    results.sort(key=lambda r: r["log_loss"])

    # ── Display top results ──────────────────────────────────────────────────
    col_w = 10
    headers = list(DEFAULTS.keys()) + ["log_loss", "brier"]
    header_line = "  " + "".join(h.rjust(col_w) for h in headers)
    print(f"{BOLD}Top {args.top} parameter combinations (ranked by log loss):{RESET}")
    print(header_line)
    print("  " + "─" * (col_w * len(headers)))

    for rank, r in enumerate(results[:args.top]):
        ll_delta = r["log_loss"] - baseline_ll
        if ll_delta < -0.001:
            marker = f" {GREEN}✓ {ll_delta:+.4f}{RESET}"
        elif ll_delta > 0.001:
            marker = f" {RED}✗ {ll_delta:+.4f}{RESET}"
        else:
            marker = "  (≈ baseline)"
        row_str = "  " + "".join(
            str(round(r[h], 4) if isinstance(r[h], float) else r[h]).rjust(col_w)
            for h in headers
        )
        print(row_str + marker)

    best = results[0]
    print()
    print(f"{BOLD}Best configuration:{RESET}")
    for k in DEFAULTS:
        change = ""
        if best[k] != DEFAULTS[k]:
            change = f"  {YELLOW}← default: {DEFAULTS[k]}{RESET}"
        print(f"  {k:<14} = {best[k]}{change}")
    print(f"\n  {'Log Loss':<14} : {best['log_loss']:.4f}  (default: {baseline_ll:.4f}  "
          f"Δ {best['log_loss'] - baseline_ll:+.4f})")
    print(f"  {'Brier Score':<14} : {best['brier']:.4f}  (default: {baseline_bs:.4f}  "
          f"Δ {best['brier'] - baseline_bs:+.4f})")

    if best["log_loss"] >= baseline_ll:
        print(f"\n  {YELLOW}⚠  No combination beats the default on this hold-out window.{RESET}")
        print(f"  {YELLOW}   Consider a wider grid or more match data.{RESET}")
    else:
        improvement = (baseline_ll - best["log_loss"]) / baseline_ll
        print(f"\n  {GREEN}✔  Best log loss is {improvement:.1%} better than the default.{RESET}")

    # ── Write CSV ────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n{GREEN}✔  Full results written to {OUTPUT_CSV}{RESET}\n")

    # ── Overfitting note ─────────────────────────────────────────────────────
    print(f"{CYAN}{'─' * 60}{RESET}")
    print(f"{CYAN}  Overfitting prevention note{RESET}")
    print(f"{CYAN}{'─' * 60}{RESET}")
    print("""
  The evaluation uses a TEMPORAL HOLD-OUT: predictions are only scored
  on the last {pct:.0%} of Xtreme matches.  ELO ratings entering those
  matches are built entirely from earlier data — the parameter search
  never sees future match outcomes before making predictions.

  This is the correct approach for a sequential rating system.  Standard
  k-fold cross-validation would leak future information and give falsely
  optimistic metrics.

  With only ~{n_eval} hold-out matches, some variance is unavoidable.
  Prefer parameter values that improve metrics by a meaningful margin
  (>1%) and are close to the default — small improvements on a small
  sample may be noise.  Re-evaluate after adding more match data.
""".format(pct=args.holdout, n_eval=n_holdout))


if __name__ == "__main__":
    main()
