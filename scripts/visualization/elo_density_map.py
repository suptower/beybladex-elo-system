# elo_density_map.py
"""
ELO Density Map — Visualize ELO Distribution Over Time

This module creates visualizations to show how the distribution of ELO ratings
evolves over time. It helps reveal trends such as:
- Meta compression or spread
- Increasing skill gaps
- Rising or declining performance tiers
- Shifts caused by new parts, rule changes, or playstyle adaptations

Visualization types:
1. ELO Histogram (Single Time Slice) - Distribution at a specific point
2. KDE Evolution Plot - Multiple KDE curves shown chronologically
3. Density Heatmap (2D Timeline) - Matrix showing density over time
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

# Add scripts directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_light_mode, configure_dark_mode  # noqa: E402

# --- File paths ---
ELO_TIMESERIES_FILE = "./csv/elo_timeseries.csv"
LEADERBOARD_FILE = "./csv/leaderboard.csv"
OUTPUT_DIR = "./docs/plots"

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)

# --- Default parameters ---
DEFAULT_BINS = 20
DEFAULT_MIN_MATCHES = 0


# ============================================
# DATA PREPARATION
# ============================================

def load_elo_timeseries_data(min_matches: int = DEFAULT_MIN_MATCHES) -> pd.DataFrame:
    """
    Load and prepare ELO timeseries data for density analysis.

    Args:
        min_matches: Minimum number of matches required for inclusion.

    Returns:
        DataFrame with columns: Date, Bey, ELO, MatchIndex
    """
    try:
        df = pd.read_csv(ELO_TIMESERIES_FILE)
    except FileNotFoundError:
        print(f"Error: ELO timeseries file not found at {ELO_TIMESERIES_FILE}")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        print(f"Error: Could not parse CSV file {ELO_TIMESERIES_FILE}: {e}")
        return pd.DataFrame()

    # Ensure correct data types
    df["ELO"] = pd.to_numeric(df["ELO"], errors="coerce")
    df["MatchIndex"] = pd.to_numeric(df["MatchIndex"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Drop rows with NaN values in essential columns
    df = df.dropna(subset=["ELO", "MatchIndex"])
    df["MatchIndex"] = df["MatchIndex"].astype(int)

    # Filter by minimum matches if specified
    if min_matches > 0:
        max_matches = df.groupby("Bey")["MatchIndex"].max()
        valid_beys = max_matches[max_matches >= min_matches].index
        df = df[df["Bey"].isin(valid_beys)]

    return df.sort_values(["Date", "MatchIndex"]).reset_index(drop=True)


def compute_elo_snapshots(df: pd.DataFrame) -> list:
    """
    Compute ELO snapshots at each match index.

    For each unique MatchIndex, compute the distribution of ELO values
    across all Beys at that point in time.

    Args:
        df: DataFrame with ELO timeseries data.

    Returns:
        List of dictionaries with snapshot data:
        - match_index: The match index
        - elo_values: List of ELO values at that index
        - mean: Mean ELO
        - median: Median ELO
        - std: Standard deviation
        - min: Minimum ELO
        - max: Maximum ELO
        - count: Number of Beys
    """
    if df.empty:
        return []

    snapshots = []

    # Get all unique match indices
    match_indices = sorted(df["MatchIndex"].unique())

    for match_idx in match_indices:
        # Get the latest ELO for each Bey up to this match index
        df_at_idx = df[df["MatchIndex"] <= match_idx]
        latest_elos = df_at_idx.groupby("Bey")["ELO"].last()

        elo_values = latest_elos.values

        if len(elo_values) > 0:
            snapshots.append({
                "match_index": int(match_idx),
                "elo_values": [float(x) for x in elo_values],
                "mean": float(np.mean(elo_values)),
                "median": float(np.median(elo_values)),
                "std": float(np.std(elo_values)) if len(elo_values) > 1 else 0.0,
                "min": float(np.min(elo_values)),
                "max": float(np.max(elo_values)),
                "count": int(len(elo_values)),
            })

    return snapshots


def compute_histogram_data(
    elo_values: list,
    bins: int = DEFAULT_BINS,
    range_min: float = None,
    range_max: float = None
) -> dict:
    """
    Compute histogram bin data for a set of ELO values.

    Args:
        elo_values: List of ELO values.
        bins: Number of histogram bins.
        range_min: Minimum ELO range (optional).
        range_max: Maximum ELO range (optional).

    Returns:
        Dictionary with:
        - bin_edges: Array of bin edges
        - bin_centers: Array of bin centers
        - counts: Array of counts per bin
        - density: Array of density per bin (normalized)
    """
    if not elo_values:
        return {"bin_edges": [], "bin_centers": [], "counts": [], "density": []}

    elo_array = np.array(elo_values)

    if range_min is None:
        range_min = float(np.min(elo_array) - 10)
    if range_max is None:
        range_max = float(np.max(elo_array) + 10)

    counts, bin_edges = np.histogram(
        elo_array, bins=bins, range=(range_min, range_max)
    )
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Compute density (normalized)
    total = np.sum(counts)
    density = counts / total if total > 0 else counts

    return {
        "bin_edges": [float(x) for x in bin_edges],
        "bin_centers": [float(x) for x in bin_centers],
        "counts": [int(x) for x in counts],
        "density": [float(x) for x in density],
    }


def compute_kde(
    elo_values: list,
    x_range: tuple = None,
    bandwidth: float = None,
    num_points: int = 200
) -> dict:
    """
    Compute Kernel Density Estimation for ELO values.

    Uses a Gaussian kernel for density estimation.

    Args:
        elo_values: List of ELO values.
        x_range: Tuple of (min, max) for x-axis range.
        bandwidth: Kernel bandwidth (Scott's rule if None).
        num_points: Number of points for the KDE curve.

    Returns:
        Dictionary with:
        - x: Array of x values
        - density: Array of density values
        - bandwidth: The bandwidth used
    """
    if len(elo_values) < 2:
        return {"x": [], "density": [], "bandwidth": 0}

    elo_array = np.array(elo_values, dtype=float)

    # Use Scott's rule for bandwidth if not specified
    if bandwidth is None:
        bandwidth = 1.06 * np.std(elo_array) * (len(elo_array) ** (-1 / 5))
        bandwidth = max(bandwidth, 5.0)  # Minimum bandwidth of 5 ELO points

    # Determine x range
    if x_range is None:
        padding = 3 * bandwidth
        x_min = float(np.min(elo_array) - padding)
        x_max = float(np.max(elo_array) + padding)
    else:
        x_min, x_max = float(x_range[0]), float(x_range[1])

    x = np.linspace(x_min, x_max, num_points)

    # Compute Gaussian KDE
    density = np.zeros(num_points)
    for elo in elo_array:
        density += np.exp(-0.5 * ((x - elo) / bandwidth) ** 2)

    # Normalize
    density = density / (len(elo_array) * bandwidth * np.sqrt(2 * np.pi))

    return {
        "x": [float(val) for val in x],
        "density": [float(val) for val in density],
        "bandwidth": float(bandwidth),
    }


def compute_density_matrix(
    snapshots: list,
    bins: int = DEFAULT_BINS,
    global_range: tuple = None
) -> dict:
    """
    Compute a 2D density matrix for the heatmap visualization.

    Args:
        snapshots: List of snapshot dictionaries from compute_elo_snapshots.
        bins: Number of ELO bins.
        global_range: Tuple of (min_elo, max_elo) for consistent binning.

    Returns:
        Dictionary with:
        - matrix: 2D array [time_index, elo_bin]
        - match_indices: Array of match indices (time axis)
        - bin_edges: Array of ELO bin edges
        - bin_centers: Array of ELO bin centers
    """
    if not snapshots:
        return {
            "matrix": [],
            "match_indices": [],
            "bin_edges": [],
            "bin_centers": [],
        }

    # Determine global ELO range
    if global_range is None:
        all_elos = []
        for snap in snapshots:
            all_elos.extend(snap["elo_values"])
        if not all_elos:
            return {
                "matrix": [],
                "match_indices": [],
                "bin_edges": [],
                "bin_centers": [],
            }
        global_min = float(min(all_elos) - 10)
        global_max = float(max(all_elos) + 10)
    else:
        global_min, global_max = float(global_range[0]), float(global_range[1])

    # Create bin edges
    bin_edges = np.linspace(global_min, global_max, bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Build density matrix
    match_indices = [int(snap["match_index"]) for snap in snapshots]
    matrix = np.zeros((len(snapshots), bins))

    for i, snap in enumerate(snapshots):
        hist_data = compute_histogram_data(
            snap["elo_values"], bins=bins,
            range_min=global_min, range_max=global_max
        )
        matrix[i, :] = hist_data["density"]

    return {
        "matrix": [[float(val) for val in row] for row in matrix],
        "match_indices": match_indices,
        "bin_edges": [float(x) for x in bin_edges],
        "bin_centers": [float(x) for x in bin_centers],
    }


def compute_summary_statistics(snapshots: list) -> dict:
    """
    Compute summary statistics showing how the meta evolves over time.

    Args:
        snapshots: List of snapshot dictionaries.

    Returns:
        Dictionary with time-series statistics:
        - match_indices: List of match indices
        - means: List of mean ELO at each index
        - medians: List of median ELO at each index
        - stds: List of standard deviations
        - ranges: List of (max - min) ranges
        - skewness: List of skewness values (meta tilt)
    """
    if not snapshots:
        return {
            "match_indices": [],
            "means": [],
            "medians": [],
            "stds": [],
            "ranges": [],
            "skewness": [],
        }

    match_indices = []
    means = []
    medians = []
    stds = []
    ranges = []
    skewness = []

    for snap in snapshots:
        match_indices.append(snap["match_index"])
        means.append(snap["mean"])
        medians.append(snap["median"])
        stds.append(snap["std"])
        ranges.append(snap["max"] - snap["min"])

        # Compute skewness
        elo_values = np.array(snap["elo_values"])
        if len(elo_values) > 2 and snap["std"] > 0:
            skew = np.mean(((elo_values - snap["mean"]) / snap["std"]) ** 3)
        else:
            skew = 0.0
        skewness.append(float(skew))

    return {
        "match_indices": match_indices,
        "means": means,
        "medians": medians,
        "stds": stds,
        "ranges": ranges,
        "skewness": skewness,
    }


# ============================================
# STATIC MATPLOTLIB PLOTS
# ============================================

def plot_elo_histogram(
    elo_values: list,
    output_file: str,
    title: str = "ELO Distribution",
    show_kde: bool = True,
    dark_mode: bool = False
):
    """
    Create a histogram of ELO distribution for a single time slice.

    Args:
        elo_values: List of ELO values.
        output_file: Path to save the plot.
        title: Plot title.
        show_kde: Whether to overlay KDE curve.
        dark_mode: Whether to use dark mode styling.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    if not elo_values:
        print("Warning: No ELO values provided for histogram")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histogram
    counts, bins, patches = ax.hist(
        elo_values, bins=DEFAULT_BINS, density=True, alpha=0.7,
        color="#3b82f6" if dark_mode else "#2563eb",
        edgecolor="white" if dark_mode else "#1e40af",
        label="ELO Distribution"
    )

    # Overlay KDE if requested
    if show_kde and len(elo_values) >= 2:
        kde_data = compute_kde(elo_values)
        ax.plot(
            kde_data["x"], kde_data["density"],
            color="#ef4444" if dark_mode else "#dc2626",
            linewidth=2, label="KDE Curve"
        )

    # Add mean and median lines
    mean_elo = np.mean(elo_values)
    median_elo = np.median(elo_values)

    ax.axvline(
        mean_elo, color="#22c55e", linestyle="--", linewidth=2,
        label=f"Mean: {mean_elo:.0f}"
    )
    ax.axvline(
        median_elo, color="#f59e0b", linestyle=":", linewidth=2,
        label=f"Median: {median_elo:.0f}"
    )

    # Configure axes
    ax.set_xlabel("ELO Rating", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"ELO Histogram saved to: {output_file}")


def plot_kde_evolution(
    snapshots: list,
    output_file: str,
    title: str = "ELO Distribution Evolution",
    num_curves: int = 10,
    dark_mode: bool = False
):
    """
    Create a KDE evolution plot showing how distribution changes over time.

    Args:
        snapshots: List of snapshot dictionaries.
        output_file: Path to save the plot.
        title: Plot title.
        num_curves: Maximum number of KDE curves to show.
        dark_mode: Whether to use dark mode styling.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    if not snapshots:
        print("Warning: No snapshots provided for KDE evolution plot")
        return

    fig, ax = plt.subplots(figsize=(12, 7))

    # Select snapshots to display (evenly spaced)
    if len(snapshots) > num_curves:
        indices = np.linspace(0, len(snapshots) - 1, num_curves, dtype=int)
        selected_snapshots = [snapshots[i] for i in indices]
    else:
        selected_snapshots = snapshots

    # Determine global x range
    all_elos = []
    for snap in selected_snapshots:
        all_elos.extend(snap["elo_values"])

    if not all_elos:
        print("Warning: No ELO values in snapshots")
        return

    x_range = (min(all_elos) - 30, max(all_elos) + 30)

    # Create colormap from old (blue) to new (red)
    colors = plt.cm.coolwarm(np.linspace(0, 1, len(selected_snapshots)))

    # Plot each KDE curve
    for i, snap in enumerate(selected_snapshots):
        kde_data = compute_kde(snap["elo_values"], x_range=x_range)
        alpha = 0.3 + (0.7 * i / len(selected_snapshots))  # Fade from old to new

        ax.plot(
            kde_data["x"], kde_data["density"],
            color=colors[i], linewidth=1.5, alpha=alpha,
            label=f"Match {snap['match_index']}"
        )
        ax.fill_between(
            kde_data["x"], kde_data["density"],
            color=colors[i], alpha=0.1
        )

    # Configure axes
    ax.set_xlabel("ELO Rating", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold")

    # Add colorbar to show time progression
    sm = plt.cm.ScalarMappable(
        cmap=plt.cm.coolwarm,
        norm=mcolors.Normalize(
            vmin=selected_snapshots[0]["match_index"],
            vmax=selected_snapshots[-1]["match_index"]
        )
    )
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
    cbar.set_label("Match Index (Time)", fontsize=10)

    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"KDE Evolution plot saved to: {output_file}")


def plot_density_heatmap(
    snapshots: list,
    output_file: str,
    title: str = "ELO Density Heatmap",
    dark_mode: bool = False
):
    """
    Create a 2D density heatmap showing ELO distribution over time.

    Args:
        snapshots: List of snapshot dictionaries.
        output_file: Path to save the plot.
        title: Plot title.
        dark_mode: Whether to use dark mode styling.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    if not snapshots:
        print("Warning: No snapshots provided for density heatmap")
        return

    # Compute density matrix
    density_data = compute_density_matrix(snapshots, bins=25)

    if not density_data["matrix"]:
        print("Warning: Could not compute density matrix")
        return

    matrix = np.array(density_data["matrix"])

    fig, ax = plt.subplots(figsize=(14, 8))

    # Create heatmap
    im = ax.imshow(
        matrix.T,  # Transpose so ELO is on y-axis
        aspect="auto",
        origin="lower",
        cmap="viridis",
        interpolation="nearest"
    )

    # Configure axes
    n_time = len(density_data["match_indices"])
    n_bins = len(density_data["bin_centers"])

    # X-axis (time)
    x_ticks = np.linspace(0, n_time - 1, min(10, n_time), dtype=int)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([density_data["match_indices"][i] for i in x_ticks])
    ax.set_xlabel("Match Index (Time)", fontsize=11)

    # Y-axis (ELO bins)
    y_ticks = np.linspace(0, n_bins - 1, min(8, n_bins), dtype=int)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{density_data['bin_centers'][i]:.0f}" for i in y_ticks])
    ax.set_ylabel("ELO Rating", fontsize=11)

    ax.set_title(title, fontsize=14, fontweight="bold")

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8, aspect=30)
    cbar.set_label("Density (proportion of Beys)", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"ELO Density Heatmap saved to: {output_file}")


def plot_summary_statistics(
    stats: dict,
    output_file: str,
    title: str = "Meta Evolution Statistics",
    dark_mode: bool = False
):
    """
    Create a multi-panel plot showing meta evolution statistics.

    Args:
        stats: Dictionary from compute_summary_statistics.
        output_file: Path to save the plot.
        title: Overall plot title.
        dark_mode: Whether to use dark mode styling.
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    if not stats["match_indices"]:
        print("Warning: No statistics data provided")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")

    match_idx = stats["match_indices"]

    # Plot 1: Mean and Median ELO
    ax1 = axes[0, 0]
    ax1.plot(match_idx, stats["means"], label="Mean ELO", color="#3b82f6", linewidth=2)
    ax1.plot(match_idx, stats["medians"], label="Median ELO", color="#22c55e",
             linewidth=2, linestyle="--")
    ax1.axhline(1000, color="gray", linestyle=":", alpha=0.5, label="Starting ELO")
    ax1.set_xlabel("Match Index")
    ax1.set_ylabel("ELO")
    ax1.set_title("Mean & Median ELO Over Time")
    ax1.legend(loc="best", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Standard Deviation (spread)
    ax2 = axes[0, 1]
    ax2.plot(match_idx, stats["stds"], color="#8b5cf6", linewidth=2)
    ax2.fill_between(match_idx, stats["stds"], alpha=0.2, color="#8b5cf6")
    ax2.set_xlabel("Match Index")
    ax2.set_ylabel("Standard Deviation")
    ax2.set_title("ELO Spread (Meta Compression/Expansion)")
    ax2.grid(True, alpha=0.3)

    # Plot 3: ELO Range (max - min)
    ax3 = axes[1, 0]
    ax3.plot(match_idx, stats["ranges"], color="#f59e0b", linewidth=2)
    ax3.fill_between(match_idx, stats["ranges"], alpha=0.2, color="#f59e0b")
    ax3.set_xlabel("Match Index")
    ax3.set_ylabel("ELO Range")
    ax3.set_title("ELO Range (Gap Between Best & Worst)")
    ax3.grid(True, alpha=0.3)

    # Plot 4: Skewness (meta tilt)
    ax4 = axes[1, 1]
    ax4.plot(match_idx, stats["skewness"], color="#ef4444", linewidth=2)
    ax4.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax4.fill_between(match_idx, stats["skewness"], alpha=0.2, color="#ef4444")
    ax4.set_xlabel("Match Index")
    ax4.set_ylabel("Skewness")
    ax4.set_title("Distribution Skewness (Meta Balance)")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Meta Statistics plot saved to: {output_file}")


# ============================================
# INTERACTIVE PLOTLY PLOTS
# ============================================

def create_elo_density_interactive(
    df: pd.DataFrame,
    snapshots: list,
    output_file: str
):
    """
    Create an interactive ELO Density Map using Plotly with theme toggle.

    Features:
    - Switchable views: Histogram, KDE Evolution, Density Heatmap
    - Time slider for histogram/KDE view
    - Dark/light mode toggle
    - Hover tooltips with statistics

    Args:
        df: DataFrame with ELO timeseries data.
        snapshots: List of snapshot dictionaries.
        output_file: Path to save the HTML file.
    """
    if df.empty or not snapshots:
        print("Warning: No data available for interactive plot")
        return

    # Prepare data for JavaScript
    snapshot_data = []
    for snap in snapshots:
        hist_data = compute_histogram_data(snap["elo_values"])
        kde_data = compute_kde(snap["elo_values"])
        snapshot_data.append({
            "match_index": snap["match_index"],
            "elo_values": snap["elo_values"],
            "mean": round(snap["mean"], 2),
            "median": round(snap["median"], 2),
            "std": round(snap["std"], 2),
            "min": round(snap["min"], 2),
            "max": round(snap["max"], 2),
            "count": snap["count"],
            "histogram": {
                "bin_centers": hist_data["bin_centers"],
                "counts": hist_data["counts"],
                "density": hist_data["density"],
            },
            "kde": {
                "x": kde_data["x"],
                "density": kde_data["density"],
            },
        })

    # Compute density matrix for heatmap
    density_data = compute_density_matrix(snapshots, bins=25)

    # Compute summary statistics
    summary_stats = compute_summary_statistics(snapshots)

    # Create HTML with embedded JavaScript
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ELO Density Map - Beyblade X</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light {{
            background-color: #ffffff;
            color: #1a1a1a;
        }}
        body.dark {{
            background-color: #0f172a;
            color: #f1f5f9;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.5em;
        }}
        .controls {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .theme-toggle {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .theme-toggle label {{
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            transition: background-color 0.3s;
        }}
        body.light .theme-toggle label {{
            background-color: #e5e7eb;
        }}
        body.dark .theme-toggle label {{
            background-color: #334155;
        }}
        .theme-toggle input {{
            display: none;
        }}
        .view-selector {{
            display: flex;
            gap: 5px;
        }}
        .view-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        body.light .view-btn {{
            background-color: #e5e7eb;
            color: #1a1a1a;
        }}
        body.dark .view-btn {{
            background-color: #334155;
            color: #f1f5f9;
        }}
        .view-btn.active {{
            background-color: #3b82f6;
            color: white;
        }}
        .back-link {{
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: background-color 0.3s;
        }}
        body.light .back-link {{
            color: #1a1a1a;
            background-color: #e5e7eb;
        }}
        body.dark .back-link {{
            color: #f1f5f9;
            background-color: #334155;
        }}
        #plotDiv {{
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .slider-container {{
            max-width: 1200px;
            margin: 10px auto;
            padding: 10px;
        }}
        .slider-container label {{
            display: block;
            margin-bottom: 5px;
        }}
        .slider-container input[type="range"] {{
            width: 100%;
        }}
        .stats-panel {{
            max-width: 1200px;
            margin: 10px auto;
            padding: 15px;
            border-radius: 8px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        body.light .stats-panel {{
            background-color: #f3f4f6;
        }}
        body.dark .stats-panel {{
            background-color: #1e293b;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #3b82f6;
        }}
        .stat-label {{
            font-size: 0.85em;
            opacity: 0.8;
        }}
        .info-panel {{
            max-width: 1200px;
            margin: 15px auto;
            padding: 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        body.light .info-panel {{
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
        }}
        body.dark .info-panel {{
            background-color: #1e3a5f;
            border: 1px solid #0ea5e9;
        }}
    </style>
</head>
<body class="light">
    <div class="header">
        <a href="../plots.html" class="back-link">← Back to Plots</a>
        <h1>📊 ELO Density Map</h1>
        <div class="controls">
            <div class="view-selector">
                <button class="view-btn active" data-view="histogram">Histogram</button>
                <button class="view-btn" data-view="kde">KDE Evolution</button>
                <button class="view-btn" data-view="heatmap">Density Heatmap</button>
                <button class="view-btn" data-view="stats">Statistics</button>
            </div>
            <div class="theme-toggle">
                <label>
                    <input type="checkbox" id="themeToggle">
                    <span id="themeIcon">🌙</span>
                    <span id="themeLabel">Dark Mode</span>
                </label>
            </div>
        </div>
    </div>

    <div class="info-panel">
        <strong>What is the ELO Density Map?</strong><br>
        This visualization shows how ELO ratings are distributed across all Beys
        and how that distribution changes over time.
        <ul style="margin: 5px 0; padding-left: 20px;">
            <li><strong>Histogram:</strong> See how many Beys fall into each ELO range.</li>
            <li><strong>KDE Evolution:</strong> Watch the distribution curve evolve over time.</li>
            <li><strong>Density Heatmap:</strong> A 2D view showing density across ELO and time.</li>
            <li><strong>Statistics:</strong> Track meta-level metrics like spread and skewness.</li>
        </ul>
    </div>

    <div class="slider-container" id="sliderContainer">
        <label>Match Index: <span id="sliderValue">{snapshots[-1]["match_index"] if snapshots else 0}</span></label>
        <input type="range" id="timeSlider" min="0" max="{len(snapshots) - 1}" value="{len(snapshots) - 1}">
    </div>

    <div class="stats-panel" id="statsPanel">
        <div class="stat-item">
            <div class="stat-value" id="statMean">-</div>
            <div class="stat-label">Mean ELO</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statMedian">-</div>
            <div class="stat-label">Median ELO</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statStd">-</div>
            <div class="stat-label">Std Dev</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statRange">-</div>
            <div class="stat-label">ELO Range</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statCount">-</div>
            <div class="stat-label">Bey Count</div>
        </div>
    </div>

    <div id="plotDiv"></div>

    <script>
        // Data
        const snapshotData = {json.dumps(snapshot_data)};
        const densityMatrix = {json.dumps(density_data)};
        const summaryStats = {json.dumps(summary_stats)};

        let currentView = 'histogram';
        let currentSnapshotIdx = snapshotData.length - 1;
        let isDarkMode = localStorage.getItem('theme') === 'dark';

        // DOM elements
        const toggle = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        const themeLabel = document.getElementById('themeLabel');
        const sliderContainer = document.getElementById('sliderContainer');
        const timeSlider = document.getElementById('timeSlider');
        const sliderValue = document.getElementById('sliderValue');
        const viewBtns = document.querySelectorAll('.view-btn');

        // Config
        const config = {{
            displayModeBar: true,
            modeBarButtonsToAdd: ['pan2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'],
            responsive: true
        }};

        // Update statistics panel
        function updateStatsPanel(snap) {{
            document.getElementById('statMean').textContent = snap.mean.toFixed(1);
            document.getElementById('statMedian').textContent = snap.median.toFixed(1);
            document.getElementById('statStd').textContent = snap.std.toFixed(1);
            document.getElementById('statRange').textContent = (snap.max - snap.min).toFixed(0);
            document.getElementById('statCount').textContent = snap.count;
        }}

        // Plot histogram view
        function plotHistogram(snapIdx) {{
            const snap = snapshotData[snapIdx];
            const isDark = document.body.classList.contains('dark');

            const trace1 = {{
                x: snap.histogram.bin_centers,
                y: snap.histogram.density,
                type: 'bar',
                name: 'Distribution',
                marker: {{
                    color: '#3b82f6',
                    opacity: 0.7
                }}
            }};

            const trace2 = {{
                x: snap.kde.x,
                y: snap.kde.density,
                type: 'scatter',
                mode: 'lines',
                name: 'KDE Curve',
                line: {{
                    color: '#ef4444',
                    width: 2
                }}
            }};

            const layout = {{
                title: `ELO Distribution at Match ${{snap.match_index}}`,
                xaxis: {{
                    title: 'ELO Rating',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                yaxis: {{
                    title: 'Density',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                paper_bgcolor: isDark ? '#0f172a' : '#ffffff',
                plot_bgcolor: isDark ? '#1e293b' : '#ffffff',
                font: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }},
                showlegend: true,
                legend: {{ x: 0.8, y: 0.95 }},
                shapes: [
                    {{
                        type: 'line',
                        x0: snap.mean, x1: snap.mean,
                        y0: 0, y1: Math.max(...snap.kde.density) * 1.1,
                        line: {{ color: '#22c55e', dash: 'dash', width: 2 }}
                    }},
                    {{
                        type: 'line',
                        x0: snap.median, x1: snap.median,
                        y0: 0, y1: Math.max(...snap.kde.density) * 1.1,
                        line: {{ color: '#f59e0b', dash: 'dot', width: 2 }}
                    }}
                ],
                annotations: [
                    {{
                        x: snap.mean, y: Math.max(...snap.kde.density) * 1.05,
                        text: `Mean: ${{snap.mean.toFixed(0)}}`,
                        showarrow: false,
                        font: {{ size: 10, color: '#22c55e' }}
                    }},
                    {{
                        x: snap.median, y: Math.max(...snap.kde.density) * 0.95,
                        text: `Median: ${{snap.median.toFixed(0)}}`,
                        showarrow: false,
                        font: {{ size: 10, color: '#f59e0b' }}
                    }}
                ]
            }};

            Plotly.react('plotDiv', [trace1, trace2], layout, config);
            updateStatsPanel(snap);
        }}

        // Plot KDE evolution view
        function plotKDEEvolution() {{
            const isDark = document.body.classList.contains('dark');
            const traces = [];

            // Select evenly spaced snapshots (max 10)
            const numCurves = Math.min(10, snapshotData.length);
            const step = Math.floor(snapshotData.length / numCurves);
            const indices = [];
            for (let i = 0; i < numCurves; i++) {{
                indices.push(Math.min(i * step, snapshotData.length - 1));
            }}
            if (indices[indices.length - 1] !== snapshotData.length - 1) {{
                indices.push(snapshotData.length - 1);
            }}

            // Colorscale from blue (old) to red (new)
            const colorscale = indices.map((_, i) => {{
                const t = i / (indices.length - 1);
                const r = Math.round(59 + t * (239 - 59));
                const g = Math.round(130 + t * (68 - 130));
                const b = Math.round(246 + t * (68 - 246));
                return `rgb(${{r}},${{g}},${{b}})`;
            }});

            indices.forEach((idx, i) => {{
                const snap = snapshotData[idx];
                traces.push({{
                    x: snap.kde.x,
                    y: snap.kde.density,
                    type: 'scatter',
                    mode: 'lines',
                    name: `Match ${{snap.match_index}}`,
                    line: {{
                        color: colorscale[i],
                        width: 1.5
                    }},
                    fill: 'tozeroy',
                    fillcolor: colorscale[i].replace('rgb', 'rgba').replace(')', ',0.1)')
                }});
            }});

            const layout = {{
                title: 'ELO Distribution Evolution Over Time',
                xaxis: {{
                    title: 'ELO Rating',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                yaxis: {{
                    title: 'Density',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                paper_bgcolor: isDark ? '#0f172a' : '#ffffff',
                plot_bgcolor: isDark ? '#1e293b' : '#ffffff',
                font: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }},
                showlegend: true,
                legend: {{ x: 1.02, y: 1 }}
            }};

            Plotly.react('plotDiv', traces, layout, config);
        }}

        // Plot density heatmap view
        function plotDensityHeatmap() {{
            const isDark = document.body.classList.contains('dark');

            const trace = {{
                z: densityMatrix.matrix,
                x: densityMatrix.match_indices,
                y: densityMatrix.bin_centers,
                type: 'heatmap',
                colorscale: 'Viridis',
                colorbar: {{
                    title: 'Density',
                    tickfont: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }},
                    titlefont: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }}
                }}
            }};

            const layout = {{
                title: 'ELO Density Heatmap Over Time',
                xaxis: {{
                    title: 'Match Index (Time)',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                yaxis: {{
                    title: 'ELO Rating',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                paper_bgcolor: isDark ? '#0f172a' : '#ffffff',
                plot_bgcolor: isDark ? '#1e293b' : '#ffffff',
                font: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }}
            }};

            Plotly.react('plotDiv', [trace], layout, config);
        }}

        // Plot statistics view
        function plotStatistics() {{
            const isDark = document.body.classList.contains('dark');

            const trace1 = {{
                x: summaryStats.match_indices,
                y: summaryStats.means,
                type: 'scatter',
                mode: 'lines',
                name: 'Mean ELO',
                line: {{ color: '#3b82f6', width: 2 }}
            }};

            const trace2 = {{
                x: summaryStats.match_indices,
                y: summaryStats.medians,
                type: 'scatter',
                mode: 'lines',
                name: 'Median ELO',
                line: {{ color: '#22c55e', width: 2, dash: 'dash' }}
            }};

            const trace3 = {{
                x: summaryStats.match_indices,
                y: summaryStats.stds,
                type: 'scatter',
                mode: 'lines',
                name: 'Std Dev (Spread)',
                line: {{ color: '#8b5cf6', width: 2 }},
                yaxis: 'y2'
            }};

            const layout = {{
                title: 'Meta Evolution Statistics',
                xaxis: {{
                    title: 'Match Index',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                yaxis: {{
                    title: 'ELO',
                    color: isDark ? '#f1f5f9' : '#1a1a1a',
                    gridcolor: 'rgba(128,128,128,0.2)'
                }},
                yaxis2: {{
                    title: 'Standard Deviation',
                    overlaying: 'y',
                    side: 'right',
                    color: '#8b5cf6',
                    gridcolor: 'rgba(128,128,128,0.1)'
                }},
                paper_bgcolor: isDark ? '#0f172a' : '#ffffff',
                plot_bgcolor: isDark ? '#1e293b' : '#ffffff',
                font: {{ color: isDark ? '#f1f5f9' : '#1a1a1a' }},
                showlegend: true,
                legend: {{ x: 0.02, y: 0.98 }},
                shapes: [{{
                    type: 'line',
                    x0: summaryStats.match_indices[0],
                    x1: summaryStats.match_indices[summaryStats.match_indices.length - 1],
                    y0: 1000, y1: 1000,
                    line: {{ color: 'gray', dash: 'dot', width: 1 }}
                }}]
            }};

            Plotly.react('plotDiv', [trace1, trace2, trace3], layout, config);
        }}

        // Update plot based on current view
        function updatePlot() {{
            sliderContainer.style.display = (currentView === 'histogram') ? 'block' : 'none';
            document.getElementById('statsPanel').style.display =
                (currentView === 'histogram') ? 'grid' : 'none';

            switch (currentView) {{
                case 'histogram':
                    plotHistogram(currentSnapshotIdx);
                    break;
                case 'kde':
                    plotKDEEvolution();
                    break;
                case 'heatmap':
                    plotDensityHeatmap();
                    break;
                case 'stats':
                    plotStatistics();
                    break;
            }}
        }}

        // Theme toggle
        function updateTheme(isDark) {{
            document.body.className = isDark ? 'dark' : 'light';
            themeIcon.textContent = isDark ? '☀️' : '🌙';
            themeLabel.textContent = isDark ? 'Light Mode' : 'Dark Mode';
            toggle.checked = isDark;
            updatePlot();
        }}

        // Initialize
        updateTheme(isDarkMode);

        // Event listeners
        toggle.addEventListener('change', function() {{
            isDarkMode = this.checked;
            localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
            updateTheme(isDarkMode);
        }});

        viewBtns.forEach(btn => {{
            btn.addEventListener('click', function() {{
                viewBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentView = this.dataset.view;
                updatePlot();
            }});
        }});

        timeSlider.addEventListener('input', function() {{
            currentSnapshotIdx = parseInt(this.value);
            sliderValue.textContent = snapshotData[currentSnapshotIdx].match_index;
            plotHistogram(currentSnapshotIdx);
        }});

        // Listen for theme changes from other pages
        window.addEventListener('storage', function(e) {{
            if (e.key === 'theme') {{
                isDarkMode = e.newValue === 'dark';
                updateTheme(isDarkMode);
            }}
        }});
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"ELO Density Map (interactive) saved to: {output_file}")


# ============================================
# MAIN GENERATION FUNCTIONS
# ============================================

def generate_elo_density_plots(min_matches: int = DEFAULT_MIN_MATCHES):
    """
    Generate all ELO Density Map plots (static and interactive).

    Args:
        min_matches: Minimum match count for inclusion.
    """
    print("Generating ELO Density Map plots...")

    # Load data
    df = load_elo_timeseries_data(min_matches=min_matches)

    if df.empty:
        print("Warning: No data available for ELO Density Map")
        return

    # Compute snapshots
    snapshots = compute_elo_snapshots(df)

    if not snapshots:
        print("Warning: Could not compute ELO snapshots")
        return

    # Get current (latest) ELO values for histogram
    current_elos = snapshots[-1]["elo_values"]

    # Compute summary statistics
    summary_stats = compute_summary_statistics(snapshots)

    # Generate static plots - light mode
    plot_elo_histogram(
        current_elos,
        os.path.join(OUTPUT_DIR, "elo_density_histogram.png"),
        title="Current ELO Distribution",
        show_kde=True,
        dark_mode=False
    )

    plot_kde_evolution(
        snapshots,
        os.path.join(OUTPUT_DIR, "elo_kde_evolution.png"),
        title="ELO Distribution Evolution",
        dark_mode=False
    )

    plot_density_heatmap(
        snapshots,
        os.path.join(OUTPUT_DIR, "elo_density_heatmap.png"),
        title="ELO Density Heatmap Over Time",
        dark_mode=False
    )

    plot_summary_statistics(
        summary_stats,
        os.path.join(OUTPUT_DIR, "elo_meta_statistics.png"),
        title="Meta Evolution Statistics",
        dark_mode=False
    )

    # Generate static plots - dark mode
    plot_elo_histogram(
        current_elos,
        os.path.join(OUTPUT_DIR, "dark", "elo_density_histogram_dark.png"),
        title="Current ELO Distribution",
        show_kde=True,
        dark_mode=True
    )

    plot_kde_evolution(
        snapshots,
        os.path.join(OUTPUT_DIR, "dark", "elo_kde_evolution_dark.png"),
        title="ELO Distribution Evolution",
        dark_mode=True
    )

    plot_density_heatmap(
        snapshots,
        os.path.join(OUTPUT_DIR, "dark", "elo_density_heatmap_dark.png"),
        title="ELO Density Heatmap Over Time",
        dark_mode=True
    )

    plot_summary_statistics(
        summary_stats,
        os.path.join(OUTPUT_DIR, "dark", "elo_meta_statistics_dark.png"),
        title="Meta Evolution Statistics",
        dark_mode=True
    )

    # Generate interactive plot with theme toggle
    create_elo_density_interactive(
        df,
        snapshots,
        os.path.join(OUTPUT_DIR, "elo_density_interactive.html")
    )

    print("ELO Density Map plots generated successfully!")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    generate_elo_density_plots()
