"""
advanced_season_plots.py
Generates visualisation plots for the four advanced season meta analytics features:

  1. Archetype-Based Season Analytics
     - Archetype performance table (bar charts)
     - Archetype vs Archetype win-rate heatmap
     - Archetype meta evolution line chart (matchday × win-share)
     - Archetype stability index bar chart

  2. Extended Power Ranking
     - Power Score ranking bar chart
     - Power Rank vs Elo Rank delta bar chart

  3. Title Probability Model
     - Title probability bar chart
     - Position probability heatmap

  4. Tier Elo Distribution & Strength Tracking
     - Per-tier Elo time-series (mean / median / max / min lines)
     - Tier Strength & Competitiveness Index bar charts

All season-specific data is expected to have already been filtered to
match_type == "season" before being passed to these functions.
Accessible via "View advanced statistics & plots".
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

# Ensure parent src directory is on path for plot_styles import
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_dark_mode, configure_light_mode  # noqa: E402
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import PLOTS_SEASON_ADVANCED_DIR, PLOTS_SEASON_DIR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_OUTPUT_DIR = PLOTS_SEASON_ADVANCED_DIR
# Season manifest directory (season-specific sub-folder)
SEASON_BASE_DIR = PLOTS_SEASON_DIR

TIER_COLORS = {1: "#ef4444", 2: "#f59e0b", 3: "#3b82f6"}

# The manifest key used for the advanced meta analytics plots block
MANIFEST_KEY = "advanced_meta"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "dark"), exist_ok=True)


def _save(fig, outdir: str, filename: str, dark_mode: bool) -> None:
    """Save figure to light or dark subfolder and close it.

    For dark mode the filename automatically gets a ``_dark`` suffix before the
    extension, so callers always pass the base (light) filename.
    """
    if dark_mode:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_dark{ext}"
        path = os.path.join(outdir, "dark", filename)
    else:
        path = os.path.join(outdir, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _write_manifest_entry(season_id: str, tier_keys: list) -> None:
    """Merge the advanced_meta block into the season's manifest.json.

    The manifest entry declares the fixed set of plot files and their dark
    counterparts, grouped into four feature sections that the frontend uses
    to label and render each group.

    Args:
        season_id: Season identifier, e.g. "S1".
        tier_keys: List of tier integers available (e.g. [1, 2, 3]).
    """
    manifest_dir = os.path.join(SEASON_BASE_DIR, season_id)
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "manifest.json")

    # Feature 4 Tier Elo time-series: one plot per tier
    tier_ts_plots = [f"advanced/tier{t}_elo_timeseries.png" for t in sorted(tier_keys)]
    tier_ts_dark = [f"advanced/dark/tier{t}_elo_timeseries_dark.png" for t in sorted(tier_keys)]

    advanced_meta_entry = {
        # Web-relative path used by the browser (docs/ root is the site root)
        "base_path": f"plots/season/{season_id}/advanced/",
        "features": [
            {
                "id": "archetype_analytics",
                "label": "🎭 Archetype-Based Season Analytics",
                "plots": [
                    "archetype_performance.png",
                    "archetype_matchup_matrix.png",
                    "archetype_meta_evolution.png",
                    "archetype_stability.png",
                ],
                "dark_plots": [
                    "dark/archetype_performance_dark.png",
                    "dark/archetype_matchup_matrix_dark.png",
                    "dark/archetype_meta_evolution_dark.png",
                    "dark/archetype_stability_dark.png",
                ],
            },
            {
                "id": "power_ranking",
                "label": "⚡ Extended Power Ranking",
                "plots": [
                    "power_ranking.png",
                    "power_vs_elo_rank_delta.png",
                ],
                "dark_plots": [
                    "dark/power_ranking_dark.png",
                    "dark/power_vs_elo_rank_delta_dark.png",
                ],
            },
            {
                "id": "title_probability",
                "label": "🏆 Title Probability Model",
                "plots": [
                    "title_probability.png",
                    "position_probability_heatmap.png",
                ],
                "dark_plots": [
                    "dark/title_probability_dark.png",
                    "dark/position_probability_heatmap_dark.png",
                ],
            },
            {
                "id": "tier_elo",
                "label": "📊 Tier Elo Distribution & Strength",
                "plots": tier_ts_plots + ["tier_strength_competitiveness.png"],
                "dark_plots": tier_ts_dark + ["dark/tier_strength_competitiveness_dark.png"],
            },
        ],
    }

    # Read existing manifest and merge
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    manifest[MANIFEST_KEY] = advanced_meta_entry

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Advanced meta manifest entry written to {manifest_path}")


def _apply_mode(dark_mode: bool) -> None:
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()


# ---------------------------------------------------------------------------
# Feature 1 – Archetype-Based Season Analytics plots
# ---------------------------------------------------------------------------

def plot_archetype_performance(
    archetype_season_stats: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Bar chart of average win-rate and points-per-round per archetype.
    """
    if not archetype_season_stats:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    archetypes = list(archetype_season_stats.keys())
    winrates = [archetype_season_stats[a]["avg_winrate"] * 100 for a in archetypes]
    pprs = [archetype_season_stats[a]["avg_points_per_round"] for a in archetypes]
    colors = [archetype_season_stats[a].get("color", "#6b7280") for a in archetypes]
    labels = [archetype_season_stats[a].get("name", a) for a in archetypes]

    x = np.arange(len(archetypes))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    title_prefix = f"{season_id} – " if season_id else ""

    # Win-rate chart
    axes[0].bar(x, winrates, color=colors, alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[0].set_ylabel("Avg Win Rate (%)")
    axes[0].set_title(f"{title_prefix}Archetype Season Win Rate")
    axes[0].set_ylim(0, 100)
    axes[0].grid(axis="y", alpha=0.3)

    # PPR chart
    axes[1].bar(x, pprs, color=colors, alpha=0.85)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("Avg Points per Round")
    axes[1].set_title(f"{title_prefix}Archetype Points per Round")
    axes[1].grid(axis="y", alpha=0.3)

    plt.tight_layout()
    _save(fig, outdir, "archetype_performance.png", dark_mode)


def plot_archetype_matchup_matrix(
    matchup_matrix: dict,
    rpg_stats: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Heatmap of archetype-vs-archetype win rates (season matches only).
    """
    if not matchup_matrix:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    archetypes = sorted(matchup_matrix.keys())
    if not archetypes:
        return

    # Build display names
    arch_names: dict = {}
    for bey_data in rpg_stats.values():
        arch = bey_data.get("archetype", {})
        aid = arch.get("id", "")
        if aid and aid not in arch_names:
            arch_names[aid] = arch.get("name", aid)

    labels = [arch_names.get(a, a) for a in archetypes]
    n = len(archetypes)
    matrix = np.full((n, n), np.nan)

    for i, arch_a in enumerate(archetypes):
        for j, arch_b in enumerate(archetypes):
            if arch_b in matchup_matrix.get(arch_a, {}):
                matrix[i][j] = matchup_matrix[arch_a][arch_b]["winrate"]

    fig, ax = plt.subplots(figsize=(max(6, n), max(5, n - 1)))
    title_prefix = f"{season_id} – " if season_id else ""
    mask = np.isnan(matrix)
    sns.heatmap(
        matrix,
        mask=mask,
        annot=True,
        fmt=".0%",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
        linewidths=0.5,
    )
    ax.set_title(f"{title_prefix}Archetype vs Archetype Win Rate (Season)")
    ax.set_xlabel("Defending Archetype (Loser)")
    ax.set_ylabel("Attacking Archetype (Winner)")
    plt.xticks(rotation=30, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()

    _save(fig, outdir, "archetype_matchup_matrix.png", dark_mode)


def plot_archetype_meta_evolution(
    meta_evolution: dict,
    rpg_stats: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Line chart: per-matchday archetype win-share (meta evolution).
    """
    if not meta_evolution:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    matchdays = sorted(meta_evolution.keys())
    # Collect all archetype ids across all matchdays
    all_archs = sorted({a for md_data in meta_evolution.values() for a in md_data})

    arch_names: dict = {}
    for bey_data in rpg_stats.values():
        arch = bey_data.get("archetype", {})
        aid = arch.get("id", "")
        if aid and aid not in arch_names:
            arch_names[aid] = arch.get("name", aid)

    palette = sns.color_palette("tab20", len(all_archs))

    fig, ax = plt.subplots(figsize=(max(8, len(matchdays) * 0.8), 5))
    title_prefix = f"{season_id} – " if season_id else ""

    for i, arch in enumerate(all_archs):
        shares = [meta_evolution[md].get(arch, 0) * 100 for md in matchdays]
        ax.plot(
            matchdays, shares,
            marker="o", linewidth=2, markersize=5,
            color=palette[i],
            label=arch_names.get(arch, arch),
        )

    ax.set_xlabel("Matchday")
    ax.set_ylabel("Share of Wins (%)")
    ax.set_title(f"{title_prefix}Archetype Meta Evolution")
    ax.set_xticks(matchdays)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(fontsize=7, ncol=2, loc="best")
    ax.grid(alpha=0.3)
    plt.tight_layout()

    _save(fig, outdir, "archetype_meta_evolution.png", dark_mode)


def plot_archetype_stability(
    stability_data: dict,
    rpg_stats: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Bar chart of Archetype Stability Index (std-dev of per-Bey win-rates).
    """
    if not stability_data:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    arch_names: dict = {}
    for bey_data in rpg_stats.values():
        arch = bey_data.get("archetype", {})
        aid = arch.get("id", "")
        if aid and aid not in arch_names:
            arch_names[aid] = arch.get("name", aid)

    archetypes = sorted(stability_data.keys())
    labels = [arch_names.get(a, a) for a in archetypes]
    stabilities = [stability_data[a]["stability_index"] for a in archetypes]

    fig, ax = plt.subplots(figsize=(max(7, len(archetypes)), 5))
    title_prefix = f"{season_id} – " if season_id else ""

    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(archetypes)))
    ax.bar(labels, stabilities, color=colors, alpha=0.85)
    ax.set_xlabel("Archetype")
    ax.set_ylabel("Stability Index (σ of win-rates)")
    ax.set_title(f"{title_prefix}Archetype Stability Index")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.3)
    ax.annotate(
        "Lower = more consistent across all Beys in archetype",
        xy=(0.5, 0.96), xycoords="axes fraction",
        ha="center", fontsize=8, style="italic",
    )
    plt.tight_layout()

    _save(fig, outdir, "archetype_stability.png", dark_mode)


# ---------------------------------------------------------------------------
# Feature 2 – Extended Power Ranking plots
# ---------------------------------------------------------------------------

def plot_power_ranking(
    power_ranking: list,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Horizontal bar chart of Extended Power Scores.
    """
    if not power_ranking:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    beys = [r["bey"] for r in power_ranking]
    scores = [r["power_score"] for r in power_ranking]

    palette = sns.color_palette("viridis_r", len(beys))

    fig, ax = plt.subplots(figsize=(9, max(4, len(beys) * 0.45)))
    y = np.arange(len(beys))
    ax.barh(y, scores, color=palette, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(beys, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Power Score (0 – 100)")
    title_prefix = f"{season_id} – " if season_id else ""
    ax.set_title(f"{title_prefix}Extended Power Ranking")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    _save(fig, outdir, "power_ranking.png", dark_mode)


def plot_power_vs_elo_rank_delta(
    power_ranking: list,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Bar chart of Power Rank vs Elo Rank delta (positive = power outranks Elo).
    """
    if not power_ranking:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    beys = [r["bey"] for r in power_ranking]
    deltas = [r["rank_delta"] for r in power_ranking]

    colors = ["#22c55e" if d > 0 else "#ef4444" if d < 0 else "#94a3b8" for d in deltas]

    fig, ax = plt.subplots(figsize=(9, max(4, len(beys) * 0.45)))
    y = np.arange(len(beys))
    ax.barh(y, deltas, color=colors, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels(beys, fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color="gray", linewidth=1, linestyle="--")
    ax.set_xlabel("Power Rank − Elo Rank (positive = form outperforms Elo)")
    title_prefix = f"{season_id} – " if season_id else ""
    ax.set_title(f"{title_prefix}Power Rank vs Elo Rank Delta")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    _save(fig, outdir, "power_vs_elo_rank_delta.png", dark_mode)


# ---------------------------------------------------------------------------
# Feature 3 – Title Probability Model plots
# ---------------------------------------------------------------------------

def plot_title_probabilities(
    title_probabilities: list,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Bar chart of simulated title probabilities per Bey.
    """
    if not title_probabilities:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    beys = [r["bey"] for r in title_probabilities]
    probs = [r["title_prob"] for r in title_probabilities]

    fig, ax = plt.subplots(figsize=(max(8, len(beys) * 0.5), 5))
    colors = sns.color_palette("YlOrRd", len(beys))[::-1]
    ax.bar(beys, probs, color=colors, alpha=0.85)
    ax.set_ylabel("Title Probability (%)")
    title_prefix = f"{season_id} – " if season_id else ""
    ax.set_title(f"{title_prefix}Simulated Title Probability")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    _save(fig, outdir, "title_probability.png", dark_mode)


def plot_position_probability_heatmap(
    title_probabilities: list,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Heatmap of finishing-position probability distribution for each Bey.
    """
    if not title_probabilities:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    # Only include Beys with non-trivial distributions
    beys = [r["bey"] for r in title_probabilities]
    n_positions = max(
        len(r.get("position_distribution", [])) for r in title_probabilities
    )
    if n_positions == 0:
        return

    matrix = np.zeros((len(beys), n_positions))
    for i, r in enumerate(title_probabilities):
        dist = r.get("position_distribution", [])
        for j, p in enumerate(dist[:n_positions]):
            matrix[i][j] = p

    pos_labels = [str(p + 1) for p in range(n_positions)]

    fig, ax = plt.subplots(figsize=(max(8, n_positions * 0.6), max(5, len(beys) * 0.45)))
    title_prefix = f"{season_id} – " if season_id else ""
    sns.heatmap(
        matrix,
        annot=(n_positions <= 12),
        fmt=".1f",
        cmap="Blues",
        xticklabels=pos_labels,
        yticklabels=beys,
        ax=ax,
        linewidths=0.3,
        cbar_kws={"label": "Probability (%)"},
    )
    ax.set_title(f"{title_prefix}Position Probability Heatmap")
    ax.set_xlabel("Final Position")
    ax.set_ylabel("Bey")
    plt.tight_layout()

    _save(fig, outdir, "position_probability_heatmap.png", dark_mode)


# ---------------------------------------------------------------------------
# Feature 4 – Tier Elo Distribution & Strength Tracking plots
# ---------------------------------------------------------------------------

def plot_tier_elo_timeseries(
    tier_elo_timeseries: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Per-tier line plots showing mean, median, max, and min Elo per matchday.
    Shaded band for min–max range.
    """
    if not tier_elo_timeseries:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    for tier_val, md_data in sorted(tier_elo_timeseries.items()):
        if not md_data:
            continue

        matchdays = sorted(md_data.keys())
        means = [md_data[md]["mean"] for md in matchdays]
        medians = [md_data[md]["median"] for md in matchdays]
        maxes = [md_data[md]["max"] for md in matchdays]
        mins = [md_data[md]["min"] for md in matchdays]

        fig, ax = plt.subplots(figsize=(max(7, len(matchdays) * 0.9), 5))
        title_prefix = f"{season_id} – " if season_id else ""
        tier_color = TIER_COLORS.get(tier_val, "#6b7280")

        ax.fill_between(matchdays, mins, maxes, alpha=0.15, color=tier_color,
                        label="Min–Max range")
        ax.plot(matchdays, means, marker="o", linewidth=2.5, color=tier_color,
                label="Mean Elo")
        ax.plot(matchdays, medians, marker="s", linewidth=1.8, linestyle="--",
                color=tier_color, alpha=0.7, label="Median Elo")
        ax.plot(matchdays, maxes, marker="^", linewidth=1.2, linestyle=":",
                color=tier_color, alpha=0.6, label="Max Elo")
        ax.plot(matchdays, mins, marker="v", linewidth=1.2, linestyle=":",
                color=tier_color, alpha=0.6, label="Min Elo")

        ax.set_xticks(matchdays)
        ax.set_xlabel("Matchday")
        ax.set_ylabel("Elo")
        ax.set_title(f"{title_prefix}Tier {tier_val} – Elo Distribution over Time")
        ax.legend(fontsize=8, loc="best")
        ax.grid(alpha=0.3)
        plt.tight_layout()

        _save(fig, outdir, f"tier{tier_val}_elo_timeseries.png", dark_mode)


def plot_tier_strength_competitiveness(
    strength_index: dict,
    competitiveness_index: dict,
    outdir: str = BASE_OUTPUT_DIR,
    season_id: str = "",
    dark_mode: bool = False,
) -> None:
    """
    Side-by-side bar charts for Tier Strength Index and Tier Competitiveness Index.
    """
    if not strength_index and not competitiveness_index:
        return

    _apply_mode(dark_mode)
    _ensure_dirs(outdir)

    tiers = sorted(set(list(strength_index.keys()) + list(competitiveness_index.keys())))
    tier_labels = [f"Tier {t}" for t in tiers]
    strengths = [strength_index.get(t, 0) for t in tiers]
    comp = [competitiveness_index.get(t, 0) for t in tiers]
    tier_colors = [TIER_COLORS.get(t, "#6b7280") for t in tiers]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    title_prefix = f"{season_id} – " if season_id else ""

    axes[0].bar(tier_labels, strengths, color=tier_colors, alpha=0.85)
    axes[0].set_ylabel("Tier Strength Index (Mean Elo)")
    axes[0].set_title(f"{title_prefix}Tier Strength Index")
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].bar(tier_labels, comp, color=tier_colors, alpha=0.85)
    axes[1].set_ylabel("Tier Competitiveness Index (Mean IQR)")
    axes[1].set_title(f"{title_prefix}Tier Competitiveness Index")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].annotate(
        "Lower IQR = more competitive",
        xy=(0.5, 0.96), xycoords="axes fraction",
        ha="center", fontsize=8, style="italic",
    )

    plt.tight_layout()
    _save(fig, outdir, "tier_strength_competitiveness.png", dark_mode)


# ---------------------------------------------------------------------------
# High-level entry point (called from gen_plots.py or update.py pipeline)
# ---------------------------------------------------------------------------

def generate_all_advanced_season_plots(
    archetype_season_stats: dict,
    archetype_matchup_matrix: dict,
    archetype_meta_evolution: dict,
    archetype_stability: dict,
    power_ranking: list,
    title_probabilities: list,
    tier_elo_timeseries: dict,
    tier_strength_index: dict,
    tier_competitiveness_index: dict,
    rpg_stats: dict,
    season_id: str = "",
    outdir: str = "",
    dark_mode: bool = False,
    write_manifest: bool = True,
) -> None:
    """
    Generate all advanced season analytics plots.

    When *season_id* is provided the plots are saved under
    ``docs/plots/season/{season_id}/advanced/`` and the season's
    ``manifest.json`` is updated with an ``advanced_meta`` block so the
    frontend can discover and render the new plots automatically.

    Intended to be called from gen_plots.py after the underlying data has been
    computed via season_meta_analytics.py.

    Args:
        archetype_season_stats: Feature 1 – archetype performance dict.
        archetype_matchup_matrix: Feature 1 – season matchup matrix.
        archetype_meta_evolution: Feature 1 – meta evolution dict.
        archetype_stability: Feature 1 – stability index dict.
        power_ranking: Feature 2 – sorted power ranking list.
        title_probabilities: Feature 3 – simulation output list.
        tier_elo_timeseries: Feature 4 – per-tier Elo time-series.
        tier_strength_index: Feature 4 – tier strength index dict.
        tier_competitiveness_index: Feature 4 – tier competitiveness index dict.
        rpg_stats: Bey → archetype mapping (for label resolution).
        season_id: Season identifier string (for plot titles and output path).
        outdir: Override output directory.  When empty and *season_id* is set,
                defaults to ``docs/plots/season/{season_id}/advanced/``.
        dark_mode: Whether to render in dark mode.
        write_manifest: When True (default), update manifest.json for the season.
    """
    # Resolve output directory: season-scoped by default
    if not outdir:
        if season_id:
            outdir = os.path.join(SEASON_BASE_DIR, season_id, "advanced")
        else:
            outdir = BASE_OUTPUT_DIR

    _ensure_dirs(outdir)

    # --- Feature 1 ---
    plot_archetype_performance(
        archetype_season_stats, outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_archetype_matchup_matrix(
        archetype_matchup_matrix, rpg_stats=rpg_stats,
        outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_archetype_meta_evolution(
        archetype_meta_evolution, rpg_stats=rpg_stats,
        outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_archetype_stability(
        archetype_stability, rpg_stats=rpg_stats,
        outdir=outdir, season_id=season_id, dark_mode=dark_mode)

    # --- Feature 2 ---
    plot_power_ranking(
        power_ranking, outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_power_vs_elo_rank_delta(
        power_ranking, outdir=outdir, season_id=season_id, dark_mode=dark_mode)

    # --- Feature 3 ---
    plot_title_probabilities(
        title_probabilities, outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_position_probability_heatmap(
        title_probabilities, outdir=outdir, season_id=season_id, dark_mode=dark_mode)

    # --- Feature 4 ---
    plot_tier_elo_timeseries(
        tier_elo_timeseries, outdir=outdir, season_id=season_id, dark_mode=dark_mode)
    plot_tier_strength_competitiveness(
        tier_strength_index, competitiveness_index=tier_competitiveness_index,
        outdir=outdir, season_id=season_id, dark_mode=dark_mode)

    # Write manifest entry (light-mode pass only, to avoid duplicate writes)
    if write_manifest and season_id and not dark_mode:
        tier_keys = list(tier_elo_timeseries.keys()) if tier_elo_timeseries else []
        _write_manifest_entry(season_id, tier_keys)
