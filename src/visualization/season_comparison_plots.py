"""
season_comparison_plots.py
Generates Season vs Global Performance Comparison visualisations.

Plots produced (light + dark variants)
---------------------------------------
1. Global vs Season Percentile Scatter (with 45° reference line)
2. PDI Bar Chart (sorted by PDI)
3. Expected vs Actual Wins Scatter (with reference diagonal)
4. Tier Strength Overview (grouped bar chart)

Source data: docs/data/season_comparison.json
Output dir : docs/plots/season/comparison/
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Add parent directory to path for plot_styles import
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_dark_mode, configure_light_mode  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
COMPARISON_FILE = "./docs/data/season_comparison.json"
BASE_OUTPUT_DIR = "./docs/plots/season/comparison"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "dark"), exist_ok=True)


def save_fig(fig, light_path: str, dark_path: str, dark_mode: bool) -> None:
    """Save figure to the appropriate path and close it."""
    path = dark_path if dark_mode else light_path
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _suffix(dark_mode: bool) -> str:
    return "_dark" if dark_mode else ""


# ---------------------------------------------------------------------------
# Plot 1 – Global vs Season Percentile Scatter
# ---------------------------------------------------------------------------

def plot_percentile_scatter(
    bey_stats: list,
    out_dir: str,
    season_id: str,
    tier: int,
    dark_mode: bool = False,
) -> None:
    """
    Scatter plot: x = Global Percentile, y = Season Percentile.
    A 45° reference line separates over- from underperformers.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    valid = [b for b in bey_stats if b.get("global_percentile") is not None]
    if not valid:
        return

    xs = [b["global_percentile"] * 100 for b in valid]
    ys = [b["season_percentile"] * 100 for b in valid]
    labels = [b["bey"] for b in valid]

    fig, ax = plt.subplots(figsize=(8, 7))

    # 45° reference line
    ax.plot([0, 100], [0, 100], color="gray", linestyle="--", linewidth=1.2,
            alpha=0.6, label="Expected (45°)")

    # Colour by PDI sign
    for x, y, label in zip(xs, ys, labels):
        color = "#22c55e" if y > x else "#ef4444"
        ax.scatter(x, y, color=color, s=60, zorder=3)
        ax.annotate(label, (x, y), textcoords="offset points",
                    xytext=(5, 3), fontsize=7, alpha=0.85)

    ax.set_xlabel("Global Percentile (%)")
    ax.set_ylabel("Season Percentile (%)")
    ax.set_title(f"Global vs Season Percentile — {season_id} Tier {tier}")
    ax.set_xlim(-2, 105)
    ax.set_ylim(-2, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))

    # Legend for colour coding
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#22c55e',
               markersize=8, label='Overperformer'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ef4444',
               markersize=8, label='Underperformer'),
        Line2D([0], [0], linestyle='--', color='gray', label='Expected (45°)'),
    ]
    ax.legend(handles=legend_elements, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    sfx = _suffix(dark_mode)
    fname = f"percentile_scatter_s{season_id}_t{tier}{sfx}.png"
    light_path = os.path.join(out_dir, fname)
    dark_path = os.path.join(out_dir, "dark", fname)
    save_fig(fig, light_path, dark_path, dark_mode)


# ---------------------------------------------------------------------------
# Plot 2 – PDI Bar Chart
# ---------------------------------------------------------------------------

def plot_pdi_bar(
    bey_stats: list,
    out_dir: str,
    season_id: str,
    tier: int,
    dark_mode: bool = False,
) -> None:
    """
    Horizontal bar chart sorted by PDI.
    Positive bars (overperformers) are green, negative are red.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    valid = [b for b in bey_stats if b.get("pdi") is not None]
    if not valid:
        return

    valid_sorted = sorted(valid, key=lambda b: b["pdi"])
    beys = [b["bey"] for b in valid_sorted]
    pdis = [b["pdi"] * 100 for b in valid_sorted]  # convert to percentage points
    colors = ["#22c55e" if p >= 0 else "#ef4444" for p in pdis]

    fig, ax = plt.subplots(figsize=(8, max(4, len(beys) * 0.45)))
    bars = ax.barh(beys, pdis, color=colors, edgecolor="none", height=0.6)

    ax.axvline(0, color="gray", linewidth=1.0, linestyle="-")
    ax.set_xlabel("PDI (Season Percentile − Global Percentile, pp)")
    ax.set_title(f"Performance Delta Index — {season_id} Tier {tier}")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f"))
    ax.grid(True, axis="x", alpha=0.3)

    # Value labels
    for bar, pdi_val in zip(bars, pdis):
        offset = 0.3 if pdi_val >= 0 else -0.3
        ha = "left" if pdi_val >= 0 else "right"
        ax.text(
            pdi_val + offset,
            bar.get_y() + bar.get_height() / 2,
            f"{pdi_val:+.1f}",
            va="center", ha=ha, fontsize=7,
        )

    fig.tight_layout()

    sfx = _suffix(dark_mode)
    fname = f"pdi_bar_s{season_id}_t{tier}{sfx}.png"
    light_path = os.path.join(out_dir, fname)
    dark_path = os.path.join(out_dir, "dark", fname)
    save_fig(fig, light_path, dark_path, dark_mode)


# ---------------------------------------------------------------------------
# Plot 3 – Expected vs Actual Wins Scatter
# ---------------------------------------------------------------------------

def plot_expected_vs_actual_wins(
    bey_stats: list,
    out_dir: str,
    season_id: str,
    tier: int,
    dark_mode: bool = False,
) -> None:
    """
    Scatter plot: x = Expected Wins (Elo model), y = Actual Wins.
    Reference diagonal separates lucky from sustained performance.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    if not bey_stats:
        return

    xs = [b["expected_wins"] for b in bey_stats]
    ys = [b["actual_wins"] for b in bey_stats]
    labels = [b["bey"] for b in bey_stats]

    if not xs:
        return

    max_val = max(max(xs), max(ys)) + 1
    ref = np.linspace(0, max_val, 100)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(ref, ref, color="gray", linestyle="--", linewidth=1.2,
            alpha=0.6, label="Expected = Actual")

    for x, y, label in zip(xs, ys, labels):
        color = "#22c55e" if y > x else "#ef4444" if y < x else "steelblue"
        ax.scatter(x, y, color=color, s=60, zorder=3)
        ax.annotate(label, (x, y), textcoords="offset points",
                    xytext=(5, 3), fontsize=7, alpha=0.85)

    ax.set_xlabel("Expected Wins (Elo model)")
    ax.set_ylabel("Actual Wins")
    ax.set_title(f"Expected vs Actual Wins — {season_id} Tier {tier}")

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#22c55e',
               markersize=8, label='Outperforming Elo'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ef4444',
               markersize=8, label='Underperforming Elo'),
        Line2D([0], [0], linestyle='--', color='gray', label='Expected = Actual'),
    ]
    ax.legend(handles=legend_elements, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    sfx = _suffix(dark_mode)
    fname = f"exp_vs_actual_wins_s{season_id}_t{tier}{sfx}.png"
    light_path = os.path.join(out_dir, fname)
    dark_path = os.path.join(out_dir, "dark", fname)
    save_fig(fig, light_path, dark_path, dark_mode)


# ---------------------------------------------------------------------------
# Plot 4 – Tier Strength Overview
# ---------------------------------------------------------------------------

def plot_tier_strength(
    tier_data: dict,
    out_dir: str,
    season_id: str,
    dark_mode: bool = False,
) -> None:
    """
    Grouped bar chart showing per-tier:
    - Average Global Percentile
    - Average PDI (offset to positive range for display)
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    tiers = sorted(tier_data.keys(), key=lambda t: int(t))
    if not tiers:
        return

    avg_global_pcts = [tier_data[t]["tier_strength"]["avg_global_percentile"] * 100 for t in tiers]
    avg_elos = [tier_data[t]["tier_strength"]["avg_elo"] for t in tiers]
    avg_pdis = [tier_data[t]["tier_strength"]["avg_pdi"] * 100 for t in tiers]

    tier_labels = [f"Tier {t}" for t in tiers]
    x = np.arange(len(tiers))
    width = 0.28

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()

    bars1 = ax1.bar(x - width, avg_global_pcts, width, label="Avg Global Percentile (%)",
                    color="#3b82f6", alpha=0.85)
    bars2 = ax1.bar(x, avg_pdis, width, label="Avg PDI (pp)",
                    color="#f59e0b", alpha=0.85)
    bars3 = ax2.bar(x + width, avg_elos, width, label="Avg Elo",
                    color="#a78bfa", alpha=0.85)

    ax1.set_ylabel("Percentile / PDI (%)")
    ax2.set_ylabel("Average Elo")
    ax1.set_xticks(x)
    ax1.set_xticklabels(tier_labels)
    ax1.set_title(f"Tier Strength Overview — {season_id}")
    ax1.axhline(0, color="gray", linewidth=0.8, linestyle="-")
    ax1.grid(True, axis="y", alpha=0.3)

    # Combined legend
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, fontsize=8, loc="upper right")

    fig.tight_layout()

    sfx = _suffix(dark_mode)
    fname = f"tier_strength_s{season_id}{sfx}.png"
    light_path = os.path.join(out_dir, fname)
    dark_path = os.path.join(out_dir, "dark", fname)
    save_fig(fig, light_path, dark_path, dark_mode)


# ---------------------------------------------------------------------------
# Manifest helper
# ---------------------------------------------------------------------------

def write_manifest(out_dir: str, plots: list) -> None:
    """Write a plots.json manifest listing generated PNG files."""
    manifest_path = os.path.join(out_dir, "plots.json")
    existing = []
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    combined = list(dict.fromkeys(existing + plots))  # deduplicate while preserving insertion order
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def generate_comparison_plots(
    comparison_file: str = COMPARISON_FILE,
    out_dir: str = BASE_OUTPUT_DIR,
) -> None:
    """Load season_comparison.json and generate all comparison plots."""
    if not os.path.exists(comparison_file):
        print(f"season_comparison.json not found at {comparison_file} — skipping.")
        return

    with open(comparison_file, encoding="utf-8") as f:
        data = json.load(f)

    seasons = data.get("seasons", {})
    if not seasons:
        print("No season data found in season_comparison.json — skipping.")
        return

    ensure_dirs(out_dir)
    generated: list = []

    for season_id, season_data in seasons.items():
        tier_data = season_data.get("tiers", {})

        for dark_mode in (False, True):
            sfx = _suffix(dark_mode)

            for tier_str, tier_info in tier_data.items():
                tier = int(tier_str)
                bey_stats = tier_info.get("beys", [])
                if not bey_stats:
                    continue

                # Plot 1 – Percentile Scatter
                plot_percentile_scatter(bey_stats, out_dir, season_id, tier, dark_mode)
                generated.append(f"percentile_scatter_s{season_id}_t{tier}{sfx}.png")

                # Plot 2 – PDI Bar
                plot_pdi_bar(bey_stats, out_dir, season_id, tier, dark_mode)
                generated.append(f"pdi_bar_s{season_id}_t{tier}{sfx}.png")

                # Plot 3 – Expected vs Actual Wins
                plot_expected_vs_actual_wins(bey_stats, out_dir, season_id, tier, dark_mode)
                generated.append(f"exp_vs_actual_wins_s{season_id}_t{tier}{sfx}.png")

            # Plot 4 – Tier Strength (once per season)
            if tier_data:
                plot_tier_strength(tier_data, out_dir, season_id, dark_mode)
                generated.append(f"tier_strength_s{season_id}{sfx}.png")

    write_manifest(out_dir, [p for p in generated if not p.endswith("_dark.png")])
    print(f"Season comparison plots saved to: {out_dir}")


if __name__ == "__main__":
    generate_comparison_plots()
