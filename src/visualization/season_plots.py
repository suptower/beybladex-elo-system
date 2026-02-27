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
               label=ft.capitalize(), color=FINISH_COLORS[ft], alpha=0.85)
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

        for tier in tiers:
            tier_int = int(tier)
            outdir = os.path.join(BASE_OUTPUT_DIR, season_id, f"tier{tier_int}")
            ensure_dirs(outdir)

            tier_beys = sorted(
                set(s_matches[s_matches["Tier"] == tier]["BeyA"])
                | set(s_matches[s_matches["Tier"] == tier]["BeyB"])
            )

            for dark_mode in [False, True]:
                plot_bump_chart(s_matches, tier, outdir, season_id, dark_mode)
                plot_cumulative_points(s_matches, tier, outdir, season_id, dark_mode)
                plot_finish_distribution(s_matches, s_rounds, tier, outdir, season_id, dark_mode)
                plot_h2h_matrix(s_matches, tier, outdir, season_id, dark_mode)
                plot_points_per_match(s_matches, tier, outdir, season_id, dark_mode)
                plot_radar_chart(season_stats_s, tier_beys, tier_int, outdir, season_id, dark_mode)

            print(f"  Season {season_id} – Tier {tier_int}: plots saved to {outdir}")

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
                    ],
                    "dark_plots": [
                        f"dark/bump_chart_tier{int(t)}_dark.png",
                        f"dark/cumulative_points_tier{int(t)}_dark.png",
                        f"dark/finish_distribution_tier{int(t)}_dark.png",
                        f"dark/h2h_matrix_tier{int(t)}_dark.png",
                        f"dark/points_per_match_tier{int(t)}_dark.png",
                        f"dark/radar_chart_tier{int(t)}_dark.png",
                    ],
                }
                for t in sorted(s_matches["Tier"].dropna().unique())
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
