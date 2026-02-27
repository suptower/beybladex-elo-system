"""
season_plots.py
Generates comprehensive season analytics plots for each tier.
Only matches with match_type = season are used.

Generates per season and tier:
  - Bump chart (position progression across matchdays)
  - Cumulative season points over time
  - Finish type distribution (stacked bar per bey)
  - Head-to-head win rate matrix (heatmap)
  - Points per match boxplot
  - Radar chart (per bey season profile)
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_dark_mode, configure_light_mode  # noqa: E402

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
MATCHES_FILE = "./docs/data/matches.csv"
ROUNDS_FILE = "./docs/data/rounds.csv"
SEASON_DATA_FILE = "./docs/data/season_data.json"
SEASON_STATS_FILE = "./docs/data/season_statistics.json"
BASE_OUTPUT_DIR = "./docs/plots/season"

# Finish type colours (consistent across all plots)
FINISH_COLORS = {
    "burst": "#ef4444",
    "extreme": "#f59e0b",
    "pocket": "#3b82f6",
    "spin": "#22c55e",
    "stadium_exit": "#a78bfa",
}

# Human-readable finish type labels
FINISH_LABELS = {
    "burst": "Burst",
    "extreme": "Extreme",
    "pocket": "Pocket",
    "spin": "Spin",
    "stadium_exit": "Stadium Exit",
}


def finish_label(ft: str) -> str:
    """Return a human-readable label for a finish type key."""
    return FINISH_LABELS.get(ft, ft.replace("_", " ").title())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "dark"), exist_ok=True)


def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s)


def save_fig(fig, light_path: str, dark_path: str, dark_mode: bool) -> None:
    """Save figure to the correct path."""
    path = dark_path if dark_mode else light_path
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    """Load and return season-only matches, rounds, season data JSON and stats."""
    df_matches = pd.read_csv(MATCHES_FILE)
    df_rounds = pd.read_csv(ROUNDS_FILE)

    # Keep only season matches
    season_matches = df_matches[df_matches["MatchType"] == "season"].copy()

    # Merge rounds with season match ids
    season_round_ids = set(season_matches["MatchID"])
    season_rounds = df_rounds[df_rounds["match_id"].isin(season_round_ids)].copy()

    with open(SEASON_DATA_FILE, encoding="utf-8") as f:
        season_data = json.load(f)

    # Try to load per-bey season statistics
    try:
        with open(SEASON_STATS_FILE, encoding="utf-8") as f:
            season_stats = json.load(f)
    except FileNotFoundError:
        season_stats = {}

    return season_matches, season_rounds, season_data, season_stats


# ---------------------------------------------------------------------------
# 1. Bump Chart – position progression across matchdays
# ---------------------------------------------------------------------------

def build_position_table(season_matches, tier):
    """
    Reconstruct per-matchday standings for *tier*.

    Returns a dict: {matchday: {bey: position}}
    Only season points (win = 3, draw = 1) are used to rank.
    """
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()

    # Accumulate season points incrementally per matchday
    bey_points: dict = {}
    bey_wins: dict = {}   # tie-break 1
    bey_diff: dict = {}   # tie-break 2

    standings_over_time: dict = {}

    for md in sorted(tier_matches["Matchday"].unique()):
        md_matches = tier_matches[tier_matches["Matchday"] <= md]

        for _, row in md_matches.iterrows():
            a, b = row["BeyA"], row["BeyB"]
            sa, sb = row["ScoreA"], row["ScoreB"]
            for bey in (a, b):
                if bey not in bey_points:
                    bey_points[bey] = 0
                    bey_wins[bey] = 0
                    bey_diff[bey] = 0

        # Reset and recompute to avoid double-counting
        pts: dict = {}
        wins: dict = {}
        diff: dict = {}

        for _, row in md_matches.iterrows():
            a, b = row["BeyA"], row["BeyB"]
            sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
            for bey in (a, b):
                if bey not in pts:
                    pts[bey] = 0
                    wins[bey] = 0
                    diff[bey] = 0

            if sa > sb:
                pts[a] = pts.get(a, 0) + 3
                wins[a] = wins.get(a, 0) + 1
            elif sb > sa:
                pts[b] = pts.get(b, 0) + 3
                wins[b] = wins.get(b, 0) + 1
            else:
                # Draw: 1 point each
                pts[a] = pts.get(a, 0) + 1
                pts[b] = pts.get(b, 0) + 1

            diff[a] = diff.get(a, 0) + (sa - sb)
            diff[b] = diff.get(b, 0) + (sb - sa)

        # Rank beys
        all_beys = sorted(pts.keys())
        ranked = sorted(
            all_beys,
            key=lambda x: (-pts.get(x, 0), -wins.get(x, 0), -diff.get(x, 0))
        )
        standings_over_time[int(md)] = {bey: rank + 1 for rank, bey in enumerate(ranked)}

    return standings_over_time


def plot_bump_chart(season_matches, tier, outdir, season_id, dark_mode=False):
    """Bump chart: position progression per matchday for a tier."""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    standings = build_position_table(season_matches, tier)
    if not standings:
        return

    matchdays = sorted(standings.keys())
    all_beys = sorted({b for md_dict in standings.values() for b in md_dict})
    n = len(all_beys)

    palette = sns.color_palette("tab20", n)

    fig, ax = plt.subplots(figsize=(10, max(5, n * 0.55)))

    for i, bey in enumerate(all_beys):
        positions = [standings[md].get(bey, np.nan) for md in matchdays]
        ax.plot(matchdays, positions, marker="o", linewidth=2, markersize=5,
                color=palette[i], label=bey, alpha=0.85)
        # label at the right end
        last_val = next((p for p in reversed(positions) if not np.isnan(p)), None)
        if last_val is not None:
            ax.text(matchdays[-1] + 0.15, last_val, bey,
                    fontsize=7, va="center", color=palette[i])

    ax.invert_yaxis()
    ax.set_yticks(range(1, n + 1))
    ax.set_xticks(matchdays)
    ax.set_xlabel("Matchday")
    ax.set_ylabel("Position")
    ax.set_title(f"{season_id} – Tier {tier_int} – Position Progression")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=6, ncol=2)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"bump_chart_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"bump_chart_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 2. Cumulative Season Points Over Time
# ---------------------------------------------------------------------------

def plot_cumulative_points(season_matches, tier, outdir, season_id, dark_mode=False):
    """Cumulative season points per matchday for each bey in a tier."""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    matchdays = sorted(tier_matches["Matchday"].unique())
    beys = sorted(set(tier_matches["BeyA"]) | set(tier_matches["BeyB"]))

    # Cumulative points per bey per matchday
    cum_points: dict = {bey: [] for bey in beys}

    for md in matchdays:
        md_matches = tier_matches[tier_matches["Matchday"] <= md]
        for bey in beys:
            pts = 0
            for _, row in md_matches.iterrows():
                a, b = row["BeyA"], row["BeyB"]
                sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
                if sa == sb:
                    # Draw: 1 point each
                    if bey in (a, b):
                        pts += 1
                elif bey == a and sa > sb:
                    pts += 3
                elif bey == b and sb > sa:
                    pts += 3
            cum_points[bey].append(pts)

    palette = sns.color_palette("tab20", len(beys))

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, bey in enumerate(beys):
        ax.plot(matchdays, cum_points[bey], marker="o", linewidth=2,
                markersize=4, label=bey, color=palette[i])

    ax.set_xlabel("Matchday")
    ax.set_ylabel("Cumulative Season Points")
    ax.set_title(f"{season_id} – Tier {tier_int} – Cumulative Points")
    ax.set_xticks(matchdays)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"cumulative_points_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"cumulative_points_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 3. Finish Type Distribution per Bey (stacked bar)
# ---------------------------------------------------------------------------

def plot_finish_distribution(season_matches, season_rounds, tier, outdir, season_id, dark_mode=False):
    """
    Stacked bar chart: finish-type wins per bey for a given tier.
    Only beys in the tier are shown. Only season rounds are used.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_match_ids = set(season_matches[season_matches["Tier"] == tier]["MatchID"])
    tier_rounds = season_rounds[season_rounds["match_id"].isin(tier_match_ids)].copy()
    if tier_rounds.empty:
        return

    finish_types = list(FINISH_COLORS.keys())
    beys = sorted(
        set(season_matches[season_matches["Tier"] == tier]["BeyA"])
        | set(season_matches[season_matches["Tier"] == tier]["BeyB"])
    )

    data: dict = {ft: [] for ft in finish_types}
    for bey in beys:
        bey_wins = tier_rounds[tier_rounds["winner"] == bey]
        for ft in finish_types:
            data[ft].append(len(bey_wins[bey_wins["finish_type"] == ft]))

    fig, ax = plt.subplots(figsize=(max(8, len(beys) * 0.8), 6))

    bottom = np.zeros(len(beys))
    for ft in finish_types:
        values = np.array(data[ft])
        ax.bar(beys, values, bottom=bottom,
               label=finish_label(ft), color=FINISH_COLORS[ft], alpha=0.85)
        bottom += values

    ax.set_xlabel("Bey")
    ax.set_ylabel("Round Wins")
    ax.set_title(f"{season_id} – Tier {tier_int} – Finish Type Distribution")
    ax.set_xticks(range(len(beys)))
    ax.set_xticklabels(beys, rotation=40, ha="right", fontsize=8)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"finish_distribution_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"finish_distribution_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 4. Head-to-Head Win Rate Matrix (heatmap)
# ---------------------------------------------------------------------------

def plot_h2h_matrix(season_matches, tier, outdir, season_id, dark_mode=False):
    """Heatmap showing head-to-head win rates between beys in a tier."""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    beys = sorted(set(tier_matches["BeyA"]) | set(tier_matches["BeyB"]))
    n = len(beys)

    wins_matrix = pd.DataFrame(0, index=beys, columns=beys, dtype=float)
    matches_matrix = pd.DataFrame(0, index=beys, columns=beys, dtype=int)

    for _, row in tier_matches.iterrows():
        a, b = row["BeyA"], row["BeyB"]
        sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
        matches_matrix.loc[a, b] += 1
        matches_matrix.loc[b, a] += 1
        if sa > sb:
            wins_matrix.loc[a, b] += 1
        else:
            wins_matrix.loc[b, a] += 1

    wr_matrix = (wins_matrix / matches_matrix.replace(0, np.nan)).fillna(np.nan)

    cell_size = max(0.6, 8 / n)
    fig_size = max(6, n * cell_size)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    cmap = "RdYlGn"
    mask = wr_matrix.isna()
    sns.heatmap(
        wr_matrix,
        ax=ax,
        cmap=cmap,
        vmin=0, vmax=1,
        annot=True, fmt=".0%",
        linewidths=0.5,
        mask=mask,
        cbar_kws={"label": "Win Rate"},
    )
    ax.set_title(f"{season_id} – Tier {tier_int} – Head-to-Head Win Rate")
    ax.set_xlabel("Opponent")
    ax.set_ylabel("Bey")
    plt.tight_layout()

    light_p = os.path.join(outdir, f"h2h_matrix_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"h2h_matrix_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 5. Points Per Match Boxplot
# ---------------------------------------------------------------------------

def plot_points_per_match(season_matches, tier, outdir, season_id, dark_mode=False):
    """Boxplot: distribution of points scored per match for each bey in a tier."""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    beys = sorted(set(tier_matches["BeyA"]) | set(tier_matches["BeyB"]))
    records = []
    for _, row in tier_matches.iterrows():
        records.append({"bey": row["BeyA"], "points": int(row["ScoreA"])})
        records.append({"bey": row["BeyB"], "points": int(row["ScoreB"])})

    df = pd.DataFrame(records)

    # Order beys by median points descending
    order = df.groupby("bey")["points"].median().sort_values(ascending=False).index.tolist()

    fig, ax = plt.subplots(figsize=(max(8, len(beys) * 0.9), 6))
    sns.boxplot(data=df, x="bey", y="points", order=order, hue="bey",
                legend=False, ax=ax, palette="Set2", linewidth=1.2)
    plt.xticks(rotation=40, ha="right")
    ax.set_xlabel("Bey")
    ax.set_ylabel("Points Per Match")
    ax.set_title(f"{season_id} – Tier {tier_int} – Points Per Match Distribution")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"points_per_match_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"points_per_match_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 6. Radar Chart – per bey season profile
# ---------------------------------------------------------------------------

def plot_radar_chart(season_stats_json, tier_beys, tier, outdir, season_id, dark_mode=False):
    """
    Radar chart for each bey in the tier, showing 5 key metrics normalised to [0, 1].
    Metrics: Match Win Rate, PPR, Burst %, Defensive Stability, Clutch Win Rate
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    stats_dict = season_stats_json.get("statistics", {})
    if not stats_dict:
        return

    # Filter to beys in this tier that have stats
    beys = [b for b in tier_beys if b in stats_dict]
    if not beys:
        return

    metrics = [
        ("match_win_rate", "Win Rate", 100.0),
        ("points_per_round", "PPR", None),
        ("burst_win_rate", "Burst %", 100.0),
        ("defensive_stability_index", "Defense", 1.0),
        ("clutch_win_rate", "Clutch", 100.0),
    ]

    # Normalise across all beys in tier
    raw: dict = {key: [] for key, _, _ in metrics}
    for bey in beys:
        s = stats_dict[bey]
        for key, _, _ in metrics:
            raw[key].append(float(s.get(key, 0)))

    def normalise(values, max_val):
        if max_val is not None:
            return [v / max_val for v in values]
        m = max(values) if values and max(values) > 0 else 1
        return [v / m for v in values]

    normalised: dict = {}
    for i, (key, _, max_val) in enumerate(metrics):
        normalised[key] = normalise(raw[key], max_val)

    num_metrics = len(metrics)
    angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    label_angles = angles[:-1]

    palette = sns.color_palette("tab10", len(beys))

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    for i, bey in enumerate(beys):
        values = [normalised[key][i] for key, _, _ in metrics]
        values += values[:1]
        ax.plot(angles, values, linewidth=1.5, label=bey, color=palette[i])
        ax.fill(angles, values, alpha=0.08, color=palette[i])

    ax.set_xticks(label_angles)
    ax.set_xticklabels([label for _, label, _ in metrics], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=7)
    ax.set_title(f"{season_id} – Tier {tier} – Bey Profile (Radar)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=7, ncol=1)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"radar_chart_tier{tier}.png")
    dark_p = os.path.join(outdir, "dark", f"radar_chart_tier{tier}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# Combined (all-tiers) plots
# ---------------------------------------------------------------------------

def plot_combined_finish_distribution(season_matches, season_rounds, tiers, outdir, season_id, dark_mode=False):
    """
    Stacked bar chart of finish-type wins for every bey across all tiers.
    Beys are grouped by tier with vertical dividers.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    finish_types = list(FINISH_COLORS.keys())

    all_beys = []
    tier_boundaries = []  # x-index where each tier starts
    bey_tier_labels = []

    for tier in sorted(tiers):
        tier_int = int(tier)
        t_beys = sorted(
            set(season_matches[season_matches["Tier"] == tier]["BeyA"])
            | set(season_matches[season_matches["Tier"] == tier]["BeyB"])
        )
        tier_boundaries.append((len(all_beys), tier_int, len(t_beys)))
        all_beys.extend(t_beys)
        bey_tier_labels.extend([tier_int] * len(t_beys))

    if not all_beys:
        return

    all_match_ids = set(season_matches["MatchID"])
    all_rounds = season_rounds[season_rounds["match_id"].isin(all_match_ids)].copy()

    data: dict = {ft: [] for ft in finish_types}
    for bey in all_beys:
        bey_wins = all_rounds[all_rounds["winner"] == bey]
        for ft in finish_types:
            data[ft].append(len(bey_wins[bey_wins["finish_type"] == ft]))

    fig, ax = plt.subplots(figsize=(max(10, len(all_beys) * 0.75), 6))

    bottom = np.zeros(len(all_beys))
    x = np.arange(len(all_beys))
    for ft in finish_types:
        values = np.array(data[ft])
        ax.bar(x, values, bottom=bottom, label=finish_label(ft),
               color=FINISH_COLORS[ft], alpha=0.85)
        bottom += values

    # Tier dividers and labels
    for start_idx, tier_int, size in tier_boundaries:
        if start_idx > 0:
            ax.axvline(start_idx - 0.5, color="gray", linewidth=1.2, linestyle="--", alpha=0.6)
        mid = start_idx + size / 2 - 0.5
        ax.text(mid, ax.get_ylim()[1] * 0.97, f"Tier {tier_int}",
                ha="center", va="top", fontsize=9, fontweight="bold", alpha=0.7)

    ax.set_xlabel("Bey")
    ax.set_ylabel("Round Wins")
    ax.set_title(f"{season_id} – All Tiers – Finish Type Distribution")
    ax.set_xticks(x)
    ax.set_xticklabels(all_beys, rotation=40, ha="right", fontsize=7)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, "finish_distribution_all_tiers.png")
    dark_p = os.path.join(outdir, "dark", "finish_distribution_all_tiers_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


def plot_combined_points_per_match(season_matches, tiers, outdir, season_id, dark_mode=False):
    """
    Boxplot of points-per-match for every bey across all tiers, colored by tier.
    Beys are ordered by tier then by median points descending within each tier.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    records = []
    for tier in sorted(tiers):
        tier_int = int(tier)
        tier_matches = season_matches[season_matches["Tier"] == tier]
        for _, row in tier_matches.iterrows():
            records.append({"bey": row["BeyA"], "points": int(row["ScoreA"]), "tier": f"Tier {tier_int}"})
            records.append({"bey": row["BeyB"], "points": int(row["ScoreB"]), "tier": f"Tier {tier_int}"})

    if not records:
        return

    df = pd.DataFrame(records)

    # Order: by tier, then by median descending within tier
    order = []
    tier_boundaries = []
    for tier in sorted(tiers):
        tier_int = int(tier)
        label = f"Tier {tier_int}"
        tier_df = df[df["tier"] == label]
        tier_order = tier_df.groupby("bey")["points"].median().sort_values(ascending=False).index.tolist()
        tier_boundaries.append((len(order), tier_int, len(tier_order)))
        order.extend(tier_order)

    palette = sns.color_palette("Set2", len(tiers))
    tier_colors = {f"Tier {int(t)}": palette[i] for i, t in enumerate(sorted(tiers))}
    # Build a bey→tier-label lookup to avoid repeated DataFrame filtering
    bey_to_tier_label = {r["bey"]: r["tier"] for r in records}
    bey_colors = [tier_colors[bey_to_tier_label[b]] for b in order]

    fig, ax = plt.subplots(figsize=(max(10, len(order) * 0.85), 6))
    sns.boxplot(data=df, x="bey", y="points", order=order, hue="bey",
                legend=False, ax=ax, palette=bey_colors, linewidth=1.2)

    # Tier dividers and labels
    for start_idx, tier_int, size in tier_boundaries:
        if start_idx > 0:
            ax.axvline(start_idx - 0.5, color="gray", linewidth=1.2, linestyle="--", alpha=0.6)
        mid = start_idx + size / 2 - 0.5
        ax.text(mid, ax.get_ylim()[1] * 0.97, f"Tier {tier_int}",
                ha="center", va="top", fontsize=9, fontweight="bold", alpha=0.7)

    plt.xticks(rotation=40, ha="right", fontsize=7)
    ax.set_xlabel("Bey")
    ax.set_ylabel("Points Per Match")
    ax.set_title(f"{season_id} – All Tiers – Points Per Match Distribution")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, "points_per_match_all_tiers.png")
    dark_p = os.path.join(outdir, "dark", "points_per_match_all_tiers_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


def plot_combined_radar_chart(season_stats_json, all_beys_by_tier, outdir, season_id, dark_mode=False):
    """
    Radar chart showing all beys across all tiers on a single chart.
    Each tier's beys are drawn with the same hue family to aid readability.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    stats_dict = season_stats_json.get("statistics", {})
    if not stats_dict:
        return

    metrics = [
        ("match_win_rate", "Win Rate", 100.0),
        ("points_per_round", "PPR", None),
        ("burst_win_rate", "Burst %", 100.0),
        ("defensive_stability_index", "Defense", 1.0),
        ("clutch_win_rate", "Clutch", 100.0),
    ]

    # Flatten all beys from all tiers that have stats
    flat_beys = []
    bey_tier_map = {}
    for tier, beys in sorted(all_beys_by_tier.items()):
        for b in beys:
            if b in stats_dict:
                flat_beys.append(b)
                bey_tier_map[b] = int(tier)

    if not flat_beys:
        return

    # Collect raw values across all beys for normalisation
    raw: dict = {key: [] for key, _, _ in metrics}
    for bey in flat_beys:
        s = stats_dict[bey]
        for key, _, _ in metrics:
            raw[key].append(float(s.get(key, 0)))

    def normalise(values, max_val):
        if max_val is not None:
            return [v / max_val for v in values]
        m = max(values) if values and max(values) > 0 else 1
        return [v / m for v in values]

    normalised: dict = {}
    for key, _, max_val in metrics:
        normalised[key] = normalise(raw[key], max_val)

    num_metrics = len(metrics)
    angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()
    angles += angles[:1]

    # Distinct tier colour palettes (one palette name per tier, cycling through options)
    _palette_names = ["tab10", "Set1", "Dark2", "tab20"]
    unique_tiers = sorted(set(bey_tier_map.values()))
    tier_palettes = {
        t: sns.color_palette(_palette_names[i % len(_palette_names)], 10)
        for i, t in enumerate(unique_tiers)
    }
    tier_counts: dict = {t: 0 for t in unique_tiers}

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))

    for i, bey in enumerate(flat_beys):
        t = bey_tier_map[bey]
        color = tier_palettes[t][tier_counts[t] % 10]
        tier_counts[t] += 1
        values = [normalised[key][i] for key, _, _ in metrics]
        values += values[:1]
        ax.plot(angles, values, linewidth=1.5, label=f"{bey} (T{t})", color=color)
        ax.fill(angles, values, alpha=0.05, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([label for _, label, _ in metrics], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=7)
    ax.set_title(f"{season_id} – All Tiers – Bey Profile (Radar)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.5, 1.2), fontsize=6, ncol=2)
    plt.tight_layout()

    light_p = os.path.join(outdir, "radar_chart_all_tiers.png")
    dark_p = os.path.join(outdir, "dark", "radar_chart_all_tiers_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 7. Round Differential Over Time (per tier)
# ---------------------------------------------------------------------------

def plot_round_differential(season_matches, tier, outdir, season_id, dark_mode=False):
    """Cumulative round differential (rounds won minus rounds lost) per matchday."""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    matchdays = sorted(tier_matches["Matchday"].unique())
    beys = sorted(set(tier_matches["BeyA"]) | set(tier_matches["BeyB"]))

    cum_diff: dict = {bey: [] for bey in beys}
    for md in matchdays:
        md_matches = tier_matches[tier_matches["Matchday"] <= md]
        for bey in beys:
            diff = 0
            for _, row in md_matches.iterrows():
                sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
                if row["BeyA"] == bey:
                    diff += sa - sb
                elif row["BeyB"] == bey:
                    diff += sb - sa
            cum_diff[bey].append(diff)

    palette = sns.color_palette("tab20", len(beys))
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, bey in enumerate(beys):
        ax.plot(matchdays, cum_diff[bey], marker="o", linewidth=2,
                markersize=4, label=bey, color=palette[i])
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("Matchday")
    ax.set_ylabel("Cumulative Round Differential")
    ax.set_title(f"{season_id} – Tier {tier_int} – Round Differential Over Time")
    ax.set_xticks(matchdays)
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"round_differential_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"round_differential_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 8. Finish Type Evolution (stacked area per matchday, per tier)
# ---------------------------------------------------------------------------

def plot_finish_type_evolution(season_matches, season_rounds, tier, outdir, season_id, dark_mode=False):
    """
    Stacked area chart showing cumulative finish type counts per matchday for a tier.
    Shows how the meta of finish types evolves over the season.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_match_ids = set(season_matches[season_matches["Tier"] == tier]["MatchID"])
    tier_rounds = season_rounds[season_rounds["match_id"].isin(tier_match_ids)].copy()
    if tier_rounds.empty:
        return

    # Merge matchday onto rounds
    md_map = season_matches.set_index("MatchID")["Matchday"].to_dict()
    tier_rounds["matchday"] = tier_rounds["match_id"].map(md_map)

    matchdays = sorted(tier_rounds["matchday"].dropna().unique())
    finish_types = list(FINISH_COLORS.keys())

    # Cumulative counts per finish type per matchday
    cum_counts: dict = {ft: [] for ft in finish_types}
    for md in matchdays:
        md_rounds = tier_rounds[tier_rounds["matchday"] <= md]
        for ft in finish_types:
            cum_counts[ft].append(len(md_rounds[md_rounds["finish_type"] == ft]))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.stackplot(
        matchdays,
        [cum_counts[ft] for ft in finish_types],
        labels=[finish_label(ft) for ft in finish_types],
        colors=[FINISH_COLORS[ft] for ft in finish_types],
        alpha=0.75,
    )
    ax.set_xlabel("Matchday")
    ax.set_ylabel("Cumulative Round Wins")
    ax.set_title(f"{season_id} – Tier {tier_int} – Finish Type Evolution")
    ax.set_xticks(matchdays)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.2)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"finish_type_evolution_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"finish_type_evolution_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 9. Rolling Volatility Plot (per tier)
# ---------------------------------------------------------------------------

def plot_rolling_volatility(season_matches, tier, outdir, season_id, dark_mode=False,
                            window: int = 3):
    """
    Rolling standard deviation of season points scored per match (default window = 3 matchdays).
    High values indicate inconsistent performance.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    matchdays = sorted(tier_matches["Matchday"].unique())
    if len(matchdays) < window:
        return

    beys = sorted(set(tier_matches["BeyA"]) | set(tier_matches["BeyB"]))

    # Collect per-matchday points for each bey
    md_points: dict = {bey: [] for bey in beys}
    for md in matchdays:
        md_matches = tier_matches[tier_matches["Matchday"] == md]
        for bey in beys:
            pts = 0
            count = 0
            for _, row in md_matches.iterrows():
                sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
                if row["BeyA"] == bey:
                    pts += 3 if sa > sb else (1 if sa == sb else 0)
                    count += 1
                elif row["BeyB"] == bey:
                    pts += 3 if sb > sa else (1 if sa == sb else 0)
                    count += 1
            # Use NaN when bey has no matches on this matchday to show a gap in the plot
            md_points[bey].append(pts / count if count else np.nan)

    palette = sns.color_palette("tab20", len(beys))
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, bey in enumerate(beys):
        series = pd.Series(md_points[bey])
        rolling_vol = series.rolling(window=window, min_periods=2).std()
        valid = [md for j, md in enumerate(matchdays) if not np.isnan(rolling_vol.iloc[j])]
        vals = rolling_vol.dropna().tolist()
        if valid:
            ax.plot(valid, vals, marker="o", linewidth=2, markersize=4,
                    label=bey, color=palette[i], alpha=0.85)

    ax.set_xlabel("Matchday")
    ax.set_ylabel(f"Rolling Volatility (σ, window={window})")
    ax.set_title(f"{season_id} – Tier {tier_int} – Rolling Volatility (window={window})")
    ax.set_xticks(matchdays)
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"rolling_volatility_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"rolling_volatility_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 10. Efficiency vs Win Rate Scatter (per tier)
# ---------------------------------------------------------------------------

def plot_efficiency_vs_winrate(season_stats_json, tier_beys, tier, outdir, season_id,
                               dark_mode=False):
    """
    Scatter plot: X = Points Per Round (PPR), Y = Match Win Rate.
    Identifies over- and under-performers relative to the tier average.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    stats_dict = season_stats_json.get("statistics", {})
    beys = [b for b in tier_beys if b in stats_dict]
    if len(beys) < 2:
        return

    pprs = [float(stats_dict[b].get("points_per_round", 0)) for b in beys]
    wrs = [float(stats_dict[b].get("match_win_rate", 0)) for b in beys]

    palette = sns.color_palette("tab10", len(beys))
    fig, ax = plt.subplots(figsize=(8, 6))

    for i, (bey, ppr, wr) in enumerate(zip(beys, pprs, wrs)):
        ax.scatter(ppr, wr, color=palette[i], s=80, zorder=3)
        ax.annotate(bey, (ppr, wr), textcoords="offset points",
                    xytext=(6, 3), fontsize=7, color=palette[i])

    # Average lines
    ax.axvline(np.mean(pprs), color="gray", linewidth=0.9, linestyle="--", alpha=0.6,
               label="Avg PPR")
    ax.axhline(np.mean(wrs), color="gray", linewidth=0.9, linestyle=":", alpha=0.6,
               label="Avg Win Rate")

    ax.set_xlabel("Points Per Round (PPR)")
    ax.set_ylabel("Match Win Rate (%)")
    ax.set_title(f"{season_id} – Tier {tier} – Efficiency vs Win Rate")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"efficiency_vs_winrate_tier{tier}.png")
    dark_p = os.path.join(outdir, "dark", f"efficiency_vs_winrate_tier{tier}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 11. Expected vs Actual Wins (per tier)
# ---------------------------------------------------------------------------

def plot_expected_vs_actual(season_matches, season_stats_json, tier_beys, tier,
                            outdir, season_id, dark_mode=False):
    """
    Bar chart comparing expected wins (based on opponent difficulty) vs actual wins.
    Expected wins = Σ (opponent_final_rank / n_beys) for each match played.
    Positive difference = overperformer, negative = underperformer.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    stats_dict = season_stats_json.get("statistics", {})
    tier_matches = season_matches[season_matches["Tier"] == tier].copy()
    if tier_matches.empty:
        return

    beys = [b for b in tier_beys if b in stats_dict]
    if not beys:
        return

    # Compute final win-rate as proxy for strength
    win_rates = {b: float(stats_dict[b].get("match_win_rate", 50)) / 100.0 for b in beys}

    # For each bey, sum opponent win-rates as "expected opponents strength" → expected wins
    actual_wins: dict = {}
    expected_wins: dict = {}
    for bey in beys:
        actual = 0
        expected = 0.0
        for _, row in tier_matches.iterrows():
            a, b_opp = row["BeyA"], row["BeyB"]
            sa, sb = int(row["ScoreA"]), int(row["ScoreB"])
            if bey == a:
                opponent = b_opp
                won = 1 if sa > sb else 0
            elif bey == b_opp:
                opponent = a
                won = 1 if sb > sa else 0
            else:
                continue
            actual += won
            opp_wr = win_rates.get(opponent, 0.5)
            expected += 1 - opp_wr  # probability of winning against that opponent
        actual_wins[bey] = actual
        expected_wins[bey] = expected

    # Sort beys by difference (overperformers first)
    diffs = {b: actual_wins[b] - expected_wins[b] for b in beys}
    sorted_beys = sorted(beys, key=lambda b: diffs[b], reverse=True)

    x = np.arange(len(sorted_beys))
    width = 0.35
    actuals = [actual_wins[b] for b in sorted_beys]
    expecteds = [expected_wins[b] for b in sorted_beys]
    diff_vals = [diffs[b] for b in sorted_beys]
    colors = ["#22c55e" if d >= 0 else "#ef4444" for d in diff_vals]

    fig, ax = plt.subplots(figsize=(max(8, len(sorted_beys) * 0.9), 6))
    ax.bar(x - width / 2, actuals, width, label="Actual Wins", color="#3b82f6", alpha=0.85)
    ax.bar(x + width / 2, expecteds, width, label="Expected Wins", color="#f59e0b", alpha=0.85)
    y_range = max(max(actuals, default=1), max(expecteds, default=1))
    offset = y_range * 0.03
    for xi, d in zip(x, diff_vals):
        ax.annotate(f"{d:+.1f}", (xi, max(actuals[xi], expecteds[xi]) + offset),
                    ha="center", fontsize=7, color=colors[xi])

    ax.set_xlabel("Bey")
    ax.set_ylabel("Wins")
    ax.set_title(f"{season_id} – Tier {tier_int} – Expected vs Actual Wins")
    ax.set_xticks(x)
    ax.set_xticklabels(sorted_beys, rotation=40, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"expected_vs_actual_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"expected_vs_actual_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 12. Cutline Pressure Plot (per tier)
# ---------------------------------------------------------------------------

def plot_cutline_pressure(season_matches, tier, outdir, season_id, dark_mode=False,
                          promotion_spots: int = 2, relegation_spots: int = 2):
    """
    Distance to promotion / relegation cutlines over matchdays.
    Positive = distance above cutline (safe), negative = distance below (danger).
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    standings = build_position_table(season_matches, tier)
    if not standings:
        return

    matchdays = sorted(standings.keys())
    all_beys = sorted({b for md_dict in standings.values() for b in md_dict})
    n = len(all_beys)
    # Skip if there aren't enough beys to have distinct promotion and relegation zones
    if n <= promotion_spots + relegation_spots:
        return

    promotion_cutline = promotion_spots          # rank ≤ this → promoted
    relegation_cutline = n - relegation_spots + 1  # rank ≥ this → relegated

    palette = sns.color_palette("tab20", n)
    fig, ax = plt.subplots(figsize=(10, max(5, n * 0.55)))

    for i, bey in enumerate(all_beys):
        positions = [standings[md].get(bey, np.nan) for md in matchdays]
        # Distance from promotion cutline (positive = above safe, negative = in danger)
        prom_dist = [promotion_cutline - p if not np.isnan(p) else np.nan for p in positions]
        ax.plot(matchdays, prom_dist, marker="o", linewidth=1.5, markersize=4,
                color=palette[i], label=bey, alpha=0.85)

    ax.axhline(0, color="#22c55e", linewidth=1.5, linestyle="--", alpha=0.8,
               label=f"Promotion cutline (top {promotion_spots})")
    ax.axhline(-(relegation_cutline - promotion_cutline - 1), color="#ef4444",
               linewidth=1.5, linestyle="--", alpha=0.8,
               label=f"Relegation danger (bottom {relegation_spots})")

    ax.set_xlabel("Matchday")
    ax.set_ylabel("Distance from Promotion Cutline (ranks)")
    ax.set_title(f"{season_id} – Tier {tier_int} – Cutline Pressure")
    ax.set_xticks(matchdays)
    ax.legend(fontsize=6, ncol=2, loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    light_p = os.path.join(outdir, f"cutline_pressure_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"cutline_pressure_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 13. Dominance Timeline (per tier)
# ---------------------------------------------------------------------------

def plot_dominance_timeline(season_matches, tier, outdir, season_id, dark_mode=False):
    """
    Strip chart showing which bey held rank 1 at each matchday.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tier_int = int(tier)
    standings = build_position_table(season_matches, tier)
    if not standings:
        return

    matchdays = sorted(standings.keys())
    leaders = [min(standings[md], key=lambda b: standings[md][b]) for md in matchdays]

    all_beys = sorted({b for md_dict in standings.values() for b in md_dict})
    palette = {b: c for b, c in zip(all_beys, sns.color_palette("tab20", len(all_beys)))}

    fig, ax = plt.subplots(figsize=(max(8, len(matchdays) * 0.7), 3))

    for md, leader in zip(matchdays, leaders):
        ax.bar(md, 1, color=palette[leader], width=0.6, alpha=0.85)
        ax.text(md, 0.5, leader, ha="center", va="center", fontsize=6.5,
                rotation=90, color="white", fontweight="bold")

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=palette[b], label=b) for b in all_beys
                       if b in leaders]
    ax.legend(handles=legend_elements, fontsize=7, loc="upper right",
              bbox_to_anchor=(1.25, 1.0), ncol=1)

    ax.set_xlim(min(matchdays) - 0.5, max(matchdays) + 0.5)
    ax.set_xticks(matchdays)
    ax.set_xlabel("Matchday")
    ax.set_yticks([])
    ax.set_title(f"{season_id} – Tier {tier_int} – Dominance Timeline (Rank 1 holder)")
    plt.tight_layout()

    light_p = os.path.join(outdir, f"dominance_timeline_tier{tier_int}.png")
    dark_p = os.path.join(outdir, "dark", f"dominance_timeline_tier{tier_int}_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# 14. Tier Comparison Plots (combined – compares tiers against each other)
# ---------------------------------------------------------------------------

def plot_tier_comparison(season_matches, season_rounds, season_stats_json,
                         all_beys_by_tier, outdir, season_id, dark_mode=False):
    """
    4-panel figure comparing key metrics across tiers:
    - Average PPR per tier
    - Win rate spread (box plot) per tier
    - Finish distribution per tier (stacked bar)
    - Average volatility index per tier
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    stats_dict = season_stats_json.get("statistics", {})
    tiers = sorted(all_beys_by_tier.keys(), key=lambda t: int(t))
    if not tiers:
        return

    tier_labels = [f"Tier {int(t)}" for t in tiers]
    palette = sns.color_palette("Set2", len(tiers))

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{season_id} – Tier Comparison", fontsize=13, fontweight="bold")

    # --- Panel 1: Average PPR per tier ---
    avg_pprs = []
    for t in tiers:
        pprs = [float(stats_dict[b].get("points_per_round", 0))
                for b in all_beys_by_tier[t] if b in stats_dict]
        avg_pprs.append(np.mean(pprs) if pprs else 0)

    ax1 = axes[0, 0]
    bars = ax1.bar(tier_labels, avg_pprs, color=palette, alpha=0.85)
    for bar, val in zip(bars, avg_pprs):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=8)
    ax1.set_ylabel("Average PPR")
    ax1.set_title("Average Points Per Round")
    ax1.grid(True, axis="y", alpha=0.3)

    # --- Panel 2: Win Rate spread (boxplot) per tier ---
    ax2 = axes[0, 1]
    wr_data = []
    for t in tiers:
        wrs = [float(stats_dict[b].get("match_win_rate", 0))
               for b in all_beys_by_tier[t] if b in stats_dict]
        wr_data.append(wrs)
    ax2.boxplot(wr_data, tick_labels=tier_labels, patch_artist=True,
                boxprops=dict(facecolor="lightblue", alpha=0.7),
                medianprops=dict(color="navy", linewidth=2))
    ax2.set_ylabel("Match Win Rate (%)")
    ax2.set_title("Win Rate Spread")
    ax2.grid(True, axis="y", alpha=0.3)

    # --- Panel 3: Finish type distribution per tier (stacked bar) ---
    ax3 = axes[1, 0]
    finish_types = list(FINISH_COLORS.keys())
    ft_counts: dict = {ft: [] for ft in finish_types}
    for t in tiers:
        t_match_ids = set(season_matches[season_matches["Tier"] == t]["MatchID"])
        t_rounds = season_rounds[season_rounds["match_id"].isin(t_match_ids)]
        total = len(t_rounds) if len(t_rounds) > 0 else 1
        for ft in finish_types:
            ft_counts[ft].append(len(t_rounds[t_rounds["finish_type"] == ft]) / total * 100)

    x_pos = np.arange(len(tiers))
    bottom = np.zeros(len(tiers))
    for ft in finish_types:
        vals = np.array(ft_counts[ft])
        ax3.bar(x_pos, vals, bottom=bottom, label=finish_label(ft),
                color=FINISH_COLORS[ft], alpha=0.85)
        bottom += vals
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(tier_labels)
    ax3.set_ylabel("% of Rounds")
    ax3.set_title("Finish Distribution (%)")
    ax3.legend(fontsize=7, loc="upper right")
    ax3.grid(True, axis="y", alpha=0.3)

    # --- Panel 4: Average volatility index per tier ---
    ax4 = axes[1, 1]
    avg_vols = []
    for t in tiers:
        vols = [float(stats_dict[b].get("volatility_index", 0))
                for b in all_beys_by_tier[t] if b in stats_dict]
        avg_vols.append(np.mean(vols) if vols else 0)

    bars4 = ax4.bar(tier_labels, avg_vols, color=palette, alpha=0.85)
    for bar, val in zip(bars4, avg_vols):
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                 f"{val:.3f}", ha="center", va="bottom", fontsize=8)
    ax4.set_ylabel("Average Volatility Index")
    ax4.set_title("Performance Volatility")
    ax4.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()

    light_p = os.path.join(outdir, "tier_comparison.png")
    dark_p = os.path.join(outdir, "dark", "tier_comparison_dark.png")
    save_fig(fig, light_p, dark_p, dark_mode)


# ---------------------------------------------------------------------------
# Master runner
# ---------------------------------------------------------------------------

def generate_season_plots():
    """Generate all season analytics plots for every season and tier."""
    season_matches, season_rounds, season_data, season_stats = load_data()

    seasons = season_data.get("seasons", {})
    if not seasons:
        print("No season data found – skipping season plots.")
        return

    for season_id, s_data in seasons.items():
        # Load per-season statistics file if it exists
        season_stats_path = f"./docs/data/season_statistics_{season_id}.json"
        if os.path.exists(season_stats_path):
            with open(season_stats_path, encoding="utf-8") as f:
                season_stats_s = json.load(f)
        else:
            season_stats_s = season_stats

        s_matches = season_matches[season_matches["SeasonID"] == season_id]
        s_rounds = season_rounds[season_rounds["match_id"].isin(set(s_matches["MatchID"]))]

        tiers = sorted(s_matches["Tier"].dropna().unique())

        # Per-tier beys mapping used later for combined radar chart
        all_beys_by_tier: dict = {}

        for tier in tiers:
            tier_int = int(tier)
            outdir = os.path.join(BASE_OUTPUT_DIR, season_id, f"tier{tier_int}")
            ensure_dirs(outdir)

            tier_beys = sorted(
                set(s_matches[s_matches["Tier"] == tier]["BeyA"])
                | set(s_matches[s_matches["Tier"] == tier]["BeyB"])
            )
            all_beys_by_tier[tier] = tier_beys

            for dark_mode in [False, True]:
                plot_bump_chart(s_matches, tier, outdir, season_id, dark_mode)
                plot_cumulative_points(s_matches, tier, outdir, season_id, dark_mode)
                plot_finish_distribution(s_matches, s_rounds, tier, outdir, season_id, dark_mode)
                plot_h2h_matrix(s_matches, tier, outdir, season_id, dark_mode)
                plot_points_per_match(s_matches, tier, outdir, season_id, dark_mode)
                plot_radar_chart(season_stats_s, tier_beys, tier_int, outdir, season_id, dark_mode)
                plot_round_differential(s_matches, tier, outdir, season_id, dark_mode)
                plot_finish_type_evolution(s_matches, s_rounds, tier, outdir, season_id, dark_mode)
                plot_rolling_volatility(s_matches, tier, outdir, season_id, dark_mode)
                plot_efficiency_vs_winrate(season_stats_s, tier_beys, tier_int, outdir, season_id, dark_mode)
                plot_expected_vs_actual(s_matches, season_stats_s, tier_beys, tier, outdir, season_id, dark_mode)
                plot_cutline_pressure(s_matches, tier, outdir, season_id, dark_mode)
                plot_dominance_timeline(s_matches, tier, outdir, season_id, dark_mode)

            print(f"  Season {season_id} – Tier {tier_int}: plots saved to {outdir}")

        # Combined (all-tiers) plots
        combined_outdir = os.path.join(BASE_OUTPUT_DIR, season_id, "combined")
        ensure_dirs(combined_outdir)
        for dark_mode in [False, True]:
            plot_combined_finish_distribution(s_matches, s_rounds, tiers, combined_outdir, season_id, dark_mode)
            plot_combined_points_per_match(s_matches, tiers, combined_outdir, season_id, dark_mode)
            plot_combined_radar_chart(season_stats_s, all_beys_by_tier, combined_outdir, season_id, dark_mode)
            plot_tier_comparison(s_matches, s_rounds, season_stats_s, all_beys_by_tier,
                                 combined_outdir, season_id, dark_mode)
        print(f"  Season {season_id} – Combined (all tiers): plots saved to {combined_outdir}")

        # Write a JSON manifest so the frontend knows which plots are available
        manifest = {
            "season_id": season_id,
            "tiers": {
                str(int(t)): {
                    "plots": [
                        f"bump_chart_tier{int(t)}.png",
                        f"cumulative_points_tier{int(t)}.png",
                        f"finish_distribution_tier{int(t)}.png",
                        f"h2h_matrix_tier{int(t)}.png",
                        f"points_per_match_tier{int(t)}.png",
                        f"radar_chart_tier{int(t)}.png",
                        f"round_differential_tier{int(t)}.png",
                        f"finish_type_evolution_tier{int(t)}.png",
                        f"rolling_volatility_tier{int(t)}.png",
                        f"efficiency_vs_winrate_tier{int(t)}.png",
                        f"expected_vs_actual_tier{int(t)}.png",
                        f"cutline_pressure_tier{int(t)}.png",
                        f"dominance_timeline_tier{int(t)}.png",
                    ],
                    "dark_plots": [
                        f"dark/bump_chart_tier{int(t)}_dark.png",
                        f"dark/cumulative_points_tier{int(t)}_dark.png",
                        f"dark/finish_distribution_tier{int(t)}_dark.png",
                        f"dark/h2h_matrix_tier{int(t)}_dark.png",
                        f"dark/points_per_match_tier{int(t)}_dark.png",
                        f"dark/radar_chart_tier{int(t)}_dark.png",
                        f"dark/round_differential_tier{int(t)}_dark.png",
                        f"dark/finish_type_evolution_tier{int(t)}_dark.png",
                        f"dark/rolling_volatility_tier{int(t)}_dark.png",
                        f"dark/efficiency_vs_winrate_tier{int(t)}_dark.png",
                        f"dark/expected_vs_actual_tier{int(t)}_dark.png",
                        f"dark/cutline_pressure_tier{int(t)}_dark.png",
                        f"dark/dominance_timeline_tier{int(t)}_dark.png",
                    ],
                }
                for t in sorted(s_matches["Tier"].dropna().unique())
            },
            "combined": {
                "plots": [
                    "finish_distribution_all_tiers.png",
                    "points_per_match_all_tiers.png",
                    "radar_chart_all_tiers.png",
                    "tier_comparison.png",
                ],
                "dark_plots": [
                    "dark/finish_distribution_all_tiers_dark.png",
                    "dark/points_per_match_all_tiers_dark.png",
                    "dark/radar_chart_all_tiers_dark.png",
                    "dark/tier_comparison_dark.png",
                ],
            },
        }
        manifest_dir = os.path.join(BASE_OUTPUT_DIR, season_id)
        os.makedirs(manifest_dir, exist_ok=True)
        manifest_path = os.path.join(manifest_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)

        print(f"Season {season_id}: manifest written to {manifest_path}")

    print("Season plots generation complete.")


if __name__ == "__main__":
    generate_season_plots()
