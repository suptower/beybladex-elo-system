# meta_landscape.py
"""
Meta Landscape Plot — 2D Offensive/Defensive Map with ELO + Winrate Overlay

This module creates a 2D scatter plot mapping all Beys by their:
- X-axis: Offense Score (derived from attack sub-metrics)
- Y-axis: Defense Score (derived from defense sub-metrics)

Additional encoding:
- Color: ELO rating (gradient from low to high)
- Size: Match count or Winrate

This provides a visual meta overview showing:
- Clusters of similar archetypes
- Outliers dominating offense or defense
- Balanced vs extreme picks
- Meta health and distribution
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import plotly.graph_objects as go

# Add scripts directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_light_mode, configure_dark_mode  # noqa: E402

# --- File paths ---
RPG_STATS_FILE = "./csv/rpg_stats.json"
ADVANCED_LEADERBOARD_FILE = "./csv/advanced_leaderboard.csv"
OUTPUT_DIR = "./docs/plots"

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)


# ============================================
# OFFENSE/DEFENSE SCORE CALCULATION
# ============================================

# Weights for Offense Score (derived from attack sub-metrics)
OFFENSE_WEIGHTS = {
    "burst_finish_rate": 0.30,
    "pocket_finish_rate": 0.15,
    "extreme_finish_rate": 0.20,
    "offensive_point_efficiency": 0.25,
    "opening_dominance": 0.10,
}

# Weights for Defense Score (derived from defense sub-metrics)
DEFENSE_WEIGHTS = {
    "burst_resistance": 0.35,
    "pocket_resistance": 0.25,
    "extreme_resistance": 0.25,
    "defensive_conversion": 0.15,
}


def calculate_offense_score(attack_metrics: dict) -> float:
    """
    Calculate the offense score from attack sub-metrics.

    The offense score represents aggressive, high-impact gameplay including:
    - Burst finishes
    - Pocket finishes
    - Extreme finishes
    - Point efficiency
    - Opening dominance

    Args:
        attack_metrics: Dictionary of attack sub-metrics

    Returns:
        float: Offense score between 0.0 and 5.0
    """
    score = 0.0
    for key, weight in OFFENSE_WEIGHTS.items():
        value = attack_metrics.get(key, 0.0)
        # Normalize point efficiency (typically 1.0-2.5 range)
        if key == "offensive_point_efficiency":
            value = min(value / 2.5, 1.0)
        score += value * weight

    # Scale to 0-5 range
    return min(score * 5.0, 5.0)


def calculate_defense_score(defense_metrics: dict) -> float:
    """
    Calculate the defense score from defense sub-metrics.

    The defense score represents resilience and stability including:
    - Burst resistance
    - Pocket resistance
    - Extreme resistance
    - Defensive conversion

    Args:
        defense_metrics: Dictionary of defense sub-metrics

    Returns:
        float: Defense score between 0.0 and 5.0
    """
    score = 0.0
    for key, weight in DEFENSE_WEIGHTS.items():
        value = defense_metrics.get(key, 0.0)
        score += value * weight

    # Scale to 0-5 range
    return min(score * 5.0, 5.0)


def load_meta_landscape_data() -> pd.DataFrame:
    """
    Load and prepare data for the Meta Landscape Plot.

    Returns:
        DataFrame with columns:
        - bey: Bey name
        - offense: Offense score (0-5)
        - defense: Defense score (0-5)
        - elo: ELO rating
        - winrate: Win rate percentage
        - matches: Match count
        - rank: Leaderboard rank
        - attack_raw: Raw attack stat from RPG stats
        - defense_raw: Raw defense stat from RPG stats
    """
    # Load RPG stats
    with open(RPG_STATS_FILE, "r", encoding="utf-8") as f:
        rpg_stats = json.load(f)

    # Load advanced leaderboard for additional context
    df_adv = pd.read_csv(ADVANCED_LEADERBOARD_FILE)
    winrate_map = {}
    for _, row in df_adv.iterrows():
        winrate_str = str(row["Winrate"]).rstrip("%")
        winrate_map[row["Bey"]] = float(winrate_str)

    # Build data
    data = []
    for bey, stats in rpg_stats.items():
        attack_metrics = stats.get("sub_metrics", {}).get("attack", {})
        defense_metrics = stats.get("sub_metrics", {}).get("defense", {})
        leaderboard = stats.get("leaderboard", {})

        offense = calculate_offense_score(attack_metrics)
        defense = calculate_defense_score(defense_metrics)

        data.append({
            "bey": bey,
            "offense": round(offense, 2),
            "defense": round(defense, 2),
            "elo": leaderboard.get("elo", 1000),
            "winrate": winrate_map.get(bey, 50.0),
            "matches": leaderboard.get("matches", 0),
            "rank": leaderboard.get("rank", 0),
            "attack_raw": stats.get("stats", {}).get("attack", 2.5),
            "defense_raw": stats.get("stats", {}).get("defense", 2.5),
        })

    return pd.DataFrame(data)


# ============================================
# STATIC MATPLOTLIB PLOTS
# ============================================

def plot_meta_landscape_static(df: pd.DataFrame, output_file: str, dark_mode: bool = False):
    """
    Create a static Meta Landscape Plot using matplotlib.

    Args:
        df: DataFrame with meta landscape data
        output_file: Path to save the plot
        dark_mode: Whether to use dark mode styling
    """
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    fig, ax = plt.subplots(figsize=(12, 10))

    # Normalize ELO for color mapping
    elo_min = df["elo"].min()
    elo_max = df["elo"].max()
    elo_normalized = (df["elo"] - elo_min) / (elo_max - elo_min + 1)

    # Color map: lower ELO = cooler colors, higher ELO = warmer colors
    cmap = plt.cm.RdYlGn  # Red-Yellow-Green gradient
    colors = [cmap(val) for val in elo_normalized]

    # Size based on match count (scaled)
    min_size = 50
    max_size = 500
    if df["matches"].max() > df["matches"].min():
        sizes = min_size + (df["matches"] - df["matches"].min()) / (
            df["matches"].max() - df["matches"].min()
        ) * (max_size - min_size)
    else:
        sizes = [200] * len(df)

    # Create scatter plot
    ax.scatter(
        df["offense"],
        df["defense"],
        c=colors,
        s=sizes,
        alpha=0.8,
        edgecolors="white" if dark_mode else "black",
        linewidths=0.5,
    )

    # Add labels for each point
    for idx, row in df.iterrows():
        ax.annotate(
            row["bey"],
            (row["offense"], row["defense"]),
            fontsize=7,
            ha="center",
            va="bottom",
            xytext=(0, 5),
            textcoords="offset points",
        )

    # Add quadrant labels
    ax.axhline(y=2.5, color="gray", linestyle="--", alpha=0.4, linewidth=1)
    ax.axvline(x=2.5, color="gray", linestyle="--", alpha=0.4, linewidth=1)

    text_color = "white" if dark_mode else "black"
    ax.text(4.5, 4.5, "Balanced\n(High Off/Def)", ha="center", va="center",
            fontsize=9, alpha=0.5, color=text_color)
    ax.text(0.5, 4.5, "Defensive\nSpecialist", ha="center", va="center",
            fontsize=9, alpha=0.5, color=text_color)
    ax.text(4.5, 0.5, "Offensive\nSpecialist", ha="center", va="center",
            fontsize=9, alpha=0.5, color=text_color)
    ax.text(0.5, 0.5, "Low Impact", ha="center", va="center",
            fontsize=9, alpha=0.5, color=text_color)

    # Configure axes
    ax.set_xlim(-0.2, 5.2)
    ax.set_ylim(-0.2, 5.2)
    ax.set_xlabel("Offense Score →", fontsize=11)
    ax.set_ylabel("Defense Score →", fontsize=11)
    ax.set_title("Meta Landscape: Offense vs Defense Map", fontsize=14, fontweight="bold")

    # Add colorbar for ELO
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=elo_min, vmax=elo_max))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
    cbar.set_label("ELO Rating", fontsize=10)

    # Add legend for size
    legend_sizes = [min_size, (min_size + max_size) / 2, max_size]
    legend_labels = ["Low Matches", "Medium Matches", "High Matches"]
    legend_elements = [
        plt.scatter([], [], s=s, c="gray", alpha=0.6, edgecolors="black", linewidths=0.5)
        for s in legend_sizes
    ]
    ax.legend(
        legend_elements, legend_labels,
        title="Match Count",
        loc="upper left",
        fontsize=8,
        title_fontsize=9,
        framealpha=0.8,
    )

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Meta Landscape (static) saved to: {output_file}")


# ============================================
# INTERACTIVE PLOTLY PLOT
# ============================================

def create_meta_landscape_interactive(df: pd.DataFrame, output_file: str, dark_mode: bool = False):
    """
    Create an interactive Meta Landscape Plot using Plotly.

    Features:
    - Hover tooltips with full Bey context
    - Color gradient by ELO
    - Size by match count
    - Zoom and pan capabilities

    Args:
        df: DataFrame with meta landscape data
        output_file: Path to save the HTML file
        dark_mode: Whether to use dark mode template
    """
    # Normalize sizes for better visualization
    min_marker_size = 10
    max_marker_size = 40
    if df["matches"].max() > df["matches"].min():
        marker_sizes = min_marker_size + (df["matches"] - df["matches"].min()) / (
            df["matches"].max() - df["matches"].min()
        ) * (max_marker_size - min_marker_size)
    else:
        marker_sizes = [25] * len(df)

    # Create hover text
    hover_text = [
        f"<b>{row['bey']}</b><br>"
        f"Rank: #{row['rank']}<br>"
        f"ELO: {row['elo']}<br>"
        f"Winrate: {row['winrate']:.1f}%<br>"
        f"Matches: {row['matches']}<br>"
        f"<br>"
        f"Offense: {row['offense']:.2f}<br>"
        f"Defense: {row['defense']:.2f}<br>"
        f"<br>"
        f"<i>Click for Bey profile</i>"
        for _, row in df.iterrows()
    ]

    # Create links for click-through
    bey_links = [
        f"bey.html?name={row['bey']}"
        for _, row in df.iterrows()
    ]

    # Choose template
    template = "plotly_dark" if dark_mode else "plotly_white"

    # Create figure
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["offense"],
        y=df["defense"],
        mode="markers+text",
        text=df["bey"],
        textposition="top center",
        textfont=dict(size=9, color="white" if dark_mode else "black"),
        marker=dict(
            size=marker_sizes,
            color=df["elo"],
            colorscale="RdYlGn",
            colorbar=dict(
                title="ELO",
                thickness=15,
                len=0.7,
            ),
            showscale=True,
            line=dict(width=1, color="white" if dark_mode else "black"),
        ),
        hovertext=hover_text,
        hoverinfo="text",
        customdata=bey_links,
    ))

    # Add quadrant dividers
    fig.add_hline(y=2.5, line_dash="dash", line_color="gray", opacity=0.4)
    fig.add_vline(x=2.5, line_dash="dash", line_color="gray", opacity=0.4)

    # Add quadrant annotations
    annotation_color = "rgba(255,255,255,0.4)" if dark_mode else "rgba(0,0,0,0.3)"
    annotations = [
        dict(x=4.5, y=4.5, text="Balanced<br>(High Off/Def)", showarrow=False,
             font=dict(size=10, color=annotation_color)),
        dict(x=0.5, y=4.5, text="Defensive<br>Specialist", showarrow=False,
             font=dict(size=10, color=annotation_color)),
        dict(x=4.5, y=0.5, text="Offensive<br>Specialist", showarrow=False,
             font=dict(size=10, color=annotation_color)),
        dict(x=0.5, y=0.5, text="Low Impact", showarrow=False,
             font=dict(size=10, color=annotation_color)),
    ]

    fig.update_layout(
        title=dict(
            text="Meta Landscape: Offense vs Defense Map",
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Offense Score →",
            range=[-0.2, 5.2],
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis=dict(
            title="Defense Score →",
            range=[-0.2, 5.2],
            gridcolor="rgba(128,128,128,0.2)",
        ),
        template=template,
        hovermode="closest",
        width=1000,
        height=800,
        annotations=annotations,
    )

    # Add JavaScript for click-through to bey profile
    fig.write_html(
        output_file,
        include_plotlyjs="cdn",
        full_html=True,
        config={
            "displayModeBar": True,
            "modeBarButtonsToAdd": ["pan2d", "zoomIn2d", "zoomOut2d", "resetScale2d"],
        },
    )

    print(f"Meta Landscape (interactive) saved to: {output_file}")


def generate_meta_landscape_plots():
    """Generate all Meta Landscape plots (static and interactive, light and dark modes)."""
    print("Generating Meta Landscape plots...")

    # Load data
    df = load_meta_landscape_data()

    if df.empty:
        print("Warning: No data available for Meta Landscape plot")
        return

    # Generate static plots
    plot_meta_landscape_static(
        df,
        os.path.join(OUTPUT_DIR, "meta_landscape.png"),
        dark_mode=False
    )
    plot_meta_landscape_static(
        df,
        os.path.join(OUTPUT_DIR, "dark", "meta_landscape_dark.png"),
        dark_mode=True
    )

    # Generate interactive plots
    create_meta_landscape_interactive(
        df,
        os.path.join(OUTPUT_DIR, "meta_landscape_interactive.html"),
        dark_mode=False
    )
    create_meta_landscape_interactive(
        df,
        os.path.join(OUTPUT_DIR, "dark", "meta_landscape_interactive_dark.html"),
        dark_mode=True
    )

    print("Meta Landscape plots generated successfully!")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    generate_meta_landscape_plots()
