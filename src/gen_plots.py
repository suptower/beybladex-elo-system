# gen_plots.py — Version 3.1
# Renders all plots (heatmaps, trends, bars) for official or private ladder.
# Now with individual ELO charts, combined ELO chart, organized folders, and HTML gallery.
# Supports light and dark mode plot generation.

import argparse
import json
import os
import subprocess
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from plot_styles import configure_light_mode, configure_dark_mode
from plot_styles import generate_dynamic_yticks, calculate_dynamic_plot_dimensions
# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["axes.grid"] = True

# -------------------
# Statistical reference line styling
# -------------------

# Consistent styling for average and median lines across all plots
AVERAGE_LINE_STYLE = {
    'color': '#3b82f6',
    'linestyle': '--',
    'linewidth': 1.5,
    'alpha': 0.7,
    'zorder': 4
}

MEDIAN_LINE_STYLE = {
    'color': '#a78bfa',
    'linestyle': ':',
    'linewidth': 1.5,
    'alpha': 0.7,
    'zorder': 4
}


# -------------------
# File selection
# -------------------


def load_files(mode):
    if mode == "official":
        return {
            "leaderboard": "./docs/data/leaderboard.csv",
            "history": "./docs/data/elo_history.csv",
            "timeseries": "./docs/data/elo_timeseries.csv",
            "positions": "./docs/data/position_timeseries.csv",
            "outdir": "./docs/plots/"
        }
    else:
        return {
            "leaderboard": "./docs/data/private_leaderboard.csv",
            "history": "./docs/data/private_elo_history.csv",
            "timeseries": "./docs/data/private_elo_timeseries.csv",
            "positions": "./docs/data/private_position_timeseries.csv",
            "outdir": "./plots/private/"
        }

# -------------------
# Ensure output dir
# -------------------


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# -------------------
# Ensure subfolders
# -------------------


def ensure_subdirs(base):
    subdirs = ["elo", "heatmaps", "bars", "positions"]
    paths = {}
    for s in subdirs:
        path = os.path.join(base, s)
        os.makedirs(path, exist_ok=True)
        paths[s] = path
        # Always create dark mode subdirectories for plot generation
        dark_path = os.path.join(path, "dark")
        os.makedirs(dark_path, exist_ok=True)
    # Create dark mode root directory
    dark_root = os.path.join(base, "dark")
    os.makedirs(dark_root, exist_ok=True)
    return paths

# -------------------
# ELO Charts
# -------------------


def plot_elo_combined(df_ts, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_ts["ELO"] = pd.to_numeric(df_ts["ELO"], errors="coerce")
    df_ts["MatchIndex"] = df_ts["MatchIndex"].astype(int)
    df_ts = df_ts.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    suffix = "_dark" if dark_mode else ""
    subdir = "dark" if dark_mode else ""
    filename = f"elo_combined{suffix}.png"
    if dark_mode:
        combined_file = os.path.join(outdir, subdir, filename)
    else:
        combined_file = os.path.join(outdir, filename)

    plt.figure(figsize=(10, 6))
    for bey, group in df_ts.groupby("Bey"):
        plt.plot(group["MatchIndex"], group["ELO"], label=bey, linewidth=1.3)
    plt.title("ELO-Verlauf aller Beys")
    plt.xlabel("Match")
    plt.ylabel("ELO")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7, ncol=3, loc="best")
    plt.tight_layout()
    plt.savefig(combined_file, dpi=300)
    plt.close()
    print(f"Kombiniertes ELO-Diagramm gespeichert als {combined_file}")


def plot_elo_single(df_ts, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_ts["ELO"] = pd.to_numeric(df_ts["ELO"], errors="coerce")
    df_ts["MatchIndex"] = df_ts["MatchIndex"].astype(int)
    df_ts = df_ts.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    subdir = os.path.join(outdir, "dark") if dark_mode else outdir
    suffix = "_dark" if dark_mode else ""

    for bey, group in df_ts.groupby("Bey"):
        plt.figure(figsize=(6, 4))
        plt.plot(group["MatchIndex"], group["ELO"], marker="o", linewidth=1.8, label="ELO History")

        # Calculate and plot median and average
        if len(group) > 0:
            avg_elo = group["ELO"].mean()
            median_elo = group["ELO"].median()

            ax = plt.gca()
            xlim = ax.get_xlim()

            # Plot average line (dashed)
            plt.axhline(avg_elo, label=f'Average: {int(round(avg_elo))}',
                        **AVERAGE_LINE_STYLE)

            # Plot median line (dotted)
            plt.axhline(median_elo, label=f'Median: {int(round(median_elo))}',
                        **MEDIAN_LINE_STYLE)

            # Highlight max and min ELO values
            max_idx = group["ELO"].idxmax()
            min_idx = group["ELO"].idxmin()
            max_elo = group.loc[max_idx, "ELO"]
            min_elo = group.loc[min_idx, "ELO"]
            max_match = group.loc[max_idx, "MatchIndex"]
            min_match = group.loc[min_idx, "MatchIndex"]

            # Only highlight if max != min (not a flat curve)
            if max_elo != min_elo:
                # Highlight maximum ELO (peak) with green dot
                plt.scatter(max_match, max_elo, color='green', s=36, marker='o',
                            zorder=5, edgecolors='darkgreen', linewidths=1.5,
                            label=f'Peak: {int(max_elo)}')

                # Highlight minimum ELO (low point) with red dot
                plt.scatter(min_match, min_elo, color='red', s=36, marker='o',
                            zorder=5, edgecolors='darkred', linewidths=1.5,
                            label=f'Low: {int(min_elo)}')

                # Draw subtle horizontal lines to y-axis
                plt.hlines(max_elo, xlim[0], max_match, colors='green',
                           linestyles='dashed', linewidths=1, alpha=0.4, zorder=3)
                plt.hlines(min_elo, xlim[0], min_match, colors='red',
                           linestyles='dashed', linewidths=1, alpha=0.4, zorder=3)

            plt.legend(loc='best', fontsize=8)

        plt.xticks(ticks=range(group["MatchIndex"].min(), group["MatchIndex"].max() + 1))
        plt.title(f"ELO-Verlauf: {bey}")
        plt.xlabel("Match")
        plt.ylabel("ELO")
        plt.grid(True, alpha=0.4)
        plt.tight_layout()

        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
        out_path = os.path.join(subdir, f"{safe_name}{suffix}.png")
        plt.savefig(out_path, dpi=200)
        plt.close()
    print(f"Einzelne ELO-Diagramme gespeichert im Ordner: {subdir}")

# -------------------
# ELO Bar Chart
# -------------------


def plot_leaderboard_bars(df, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    sorted_df = df.sort_values("ELO", ascending=False)

    suffix = "_dark" if dark_mode else ""
    subdir = os.path.join(outdir, "dark") if dark_mode else outdir

    plt.figure(figsize=(12, 8))
    sns.barplot(data=sorted_df, x="ELO", y="Name")
    plt.title("ELO Leaderboard")
    plt.xlabel("ELO")
    plt.ylabel("Bey")
    plt.tight_layout()
    plt.savefig(os.path.join(subdir, f"elo_bar_chart{suffix}.png"))
    plt.close()

# -------------------
# Position Time Series
# -------------------


def plot_position_timeseries(df_pos, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_pos["Position"] = pd.to_numeric(df_pos["Position"], errors="coerce")
    df_pos["Event"] = df_pos["Event"].astype(int)
    df_pos["MatchIndex"] = df_pos["MatchIndex"].astype(int)
    df_pos = df_pos.sort_values(["Bey", "Event"]).reset_index(drop=True)
    max_rank = len(df_pos["Bey"].unique())

    subdir = os.path.join(outdir, "dark") if dark_mode else outdir
    suffix = "_dark" if dark_mode else ""

    for bey, group in df_pos.groupby("Bey"):
        # Filter to keep only first and last entry per MatchIndex to avoid oscillations
        # filtered_rows = []
        # for mi in group["MatchIndex"].unique():
        #     mi_group = group[group["MatchIndex"] == mi]
        #     if len(mi_group) == 1:
        #         filtered_rows.append(mi_group.iloc[0])
        #     else:
        #         # Keep first and last entry
        #         filtered_rows.append(mi_group.iloc[0])
        #         if len(mi_group) > 1:
        #             filtered_rows.append(mi_group.iloc[-1])

        # group_filtered = pd.DataFrame(filtered_rows).reset_index(drop=True)

        # Calculate dynamic plot dimensions based on actual position range
        min_pos = group["Position"].min()
        max_pos = group["Position"].max()
        height = max_rank * 0.15
        ylim_max, ylim_min = calculate_dynamic_plot_dimensions(min_pos, max_pos)

        plt.figure(figsize=(6, height))
        plt.plot(group["PlotX"], group["Position"], marker="o", linewidth=1.2, label="Position History")

        # Calculate and plot median and average positions
        if len(group) > 0:
            avg_pos = group["Position"].mean()
            median_pos = group["Position"].median()

            ax = plt.gca()
            xlim = ax.get_xlim()

            ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))  # Ensure x-axis shows integer match indices

            # Plot average line (dashed)
            plt.axhline(avg_pos, label=f'Average: #{int(round(avg_pos))}',
                        **AVERAGE_LINE_STYLE)

            # Plot median line (dotted)
            plt.axhline(median_pos, label=f'Median: #{int(round(median_pos))}',
                        **MEDIAN_LINE_STYLE)

            # Highlight best and worst positions
            # Best position = minimum rank number (e.g., 1 is better than 10)
            best_idx = group["Position"].idxmin()
            # Worst position = maximum rank number (e.g., 30 is worse than 10)
            worst_idx = group["Position"].idxmax()
            best_pos = group.loc[best_idx, "Position"]
            worst_pos = group.loc[worst_idx, "Position"]
            best_plotx = group.loc[best_idx, "PlotX"]
            worst_plotx = group.loc[worst_idx, "PlotX"]

            # Only highlight if best != worst (not a flat curve)
            if best_pos != worst_pos:
                # Highlight best position (lowest rank) with green dot
                plt.scatter(best_plotx, best_pos, color='green', s=36, marker='o',
                            zorder=5, edgecolors='darkgreen', linewidths=1.5,
                            label=f'Best: #{int(best_pos)}')

                # Highlight worst position (highest rank) with red dot
                plt.scatter(worst_plotx, worst_pos, color='red', s=36, marker='o',
                            zorder=5, edgecolors='darkred', linewidths=1.5,
                            label=f'Worst: #{int(worst_pos)}')

                # Draw subtle horizontal lines to y-axis
                plt.hlines(best_pos, xlim[0], best_plotx, colors='green',
                           linestyles='dashed', linewidths=1, alpha=0.4, zorder=3)
                plt.hlines(worst_pos, xlim[0], worst_plotx, colors='red',
                           linestyles='dashed', linewidths=1, alpha=0.4, zorder=3)

            plt.legend(loc='best', fontsize=8)

        plt.gca().invert_yaxis()  # Higher positions (1st) should be at the top
        # Let matplotlib automatically determine x-axis ticks for fractional positioning
        # (removed: plt.xticks(ticks=group["MatchIndex"].unique()))
        plt.title(f"Positionsverlauf: {bey}")
        plt.xlabel("Match Index")
        plt.ylabel("Position")
        plt.ylim(ylim_min, ylim_max)

        # Generate dynamic yticks based on actual position range
        yticks = generate_dynamic_yticks(min_pos, max_pos)
        plt.yticks(yticks)
        plt.grid(True, which="major", axis="y", alpha=0.2, linestyle="--")

        # label_x_offset = -0.03
        # label_y_offset = 1.5

        # # --- Position als Text direkt neben jedem Punkt ---
        # for i, row in group_filtered.iterrows():
        #     plt.text(
        #         row["PlotX"] + label_x_offset,
        #         row["Position"] + label_y_offset,
        #         str(int(row["Position"])),
        #         fontsize=9,
        #         ha="left",
        #         va="center",
        #     )

        plt.grid(True, alpha=0.4)
        plt.tight_layout()

        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
        out_path = os.path.join(subdir, f"{safe_name}_position{suffix}.png")
        plt.savefig(out_path, dpi=200)
        plt.close()
    print(f"Positions-Diagramme gespeichert im Ordner: {subdir}")


def plot_combined_positions(df_pos, out_path, dark_mode=False):
    import matplotlib.pyplot as plt

    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_pos["Position"] = pd.to_numeric(df_pos["Position"], errors="coerce")
    df_pos["PlotX"] = pd.to_numeric(df_pos["PlotX"], errors="coerce")

    # Sortieren für hübsche Linien
    df_pos = df_pos.sort_values(["Bey", "PlotX"])

    # Anzahl der Ränge = max Position
    max_rank = df_pos["Position"].max()

    plt.figure(figsize=(12, 8))

    # Jede Linie plotten
    for bey, group in df_pos.groupby("Bey"):
        plt.plot(
            group["PlotX"],
            group["Position"],
            linewidth=1.8,
            alpha=0.7,
            label=bey
        )

    # Invertierte Y-Achse (1 = oben)
    plt.gca().invert_yaxis()
    plt.ylim(max_rank + 0.5, 0.5)
    plt.yticks(range(1, max_rank + 1))

    plt.xlabel("Match Index")
    plt.ylabel("Position")
    plt.title("Positionsverläufe aller Beys")

    plt.grid(True, alpha=0.35)

    plt.legend(bbox_to_anchor=(1.05, 1), loc="best", fontsize=7)

    # Wenn es zu viele Beys sind: Legende optional
    # if len(df_pos["Bey"].unique()) <= 25:
    #     plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    # else:
    #     print("Legende deaktiviert (zu viele Beys).")

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()

    print(f"Kombiniertes Positionsdiagramm gespeichert unter: {out_path}")


def create_fractional_positions(df_pos):
    df = df_pos.copy()
    df["PlotX"] = 0.0

    for bey, group in df.groupby("Bey"):
        group = group.sort_values("Event")

        prev_mi = None
        buffer = []  # (mi, event_idx)

        def flush_buffer(mi):
            n = len(buffer)
            if n == 0:
                return
            # gleichmäßig zwischen mi und mi+1 verteilen
            step = 1.0 / (n + 1)
            for i, (base_mi, idx) in enumerate(buffer, start=1):
                df.loc[idx, "PlotX"] = base_mi + i * step

        for idx, row in group.iterrows():
            mi = row["MatchIndex"]
            if prev_mi is None:
                # erster Punkt → direkt setzen
                df.loc[idx, "PlotX"] = mi
                prev_mi = mi
                continue

            if mi == prev_mi:
                # passives Event → puffern
                buffer.append((mi, idx))
            else:
                # MI-Wechsel → Buffer flushen
                flush_buffer(prev_mi)
                buffer = []
                df.loc[idx, "PlotX"] = mi
                prev_mi = mi

        # letzten Buffer flushen
        flush_buffer(prev_mi)

    df = df.sort_values(["Bey", "PlotX"]).reset_index(drop=True)
    return df


# -------------------
# Winrate Bar Chart
# -------------------
def plot_winrates(df, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df["WR"] = df["Winrate"].str.replace("%", "").astype(float)
    sorted_df = df.sort_values("WR", ascending=False)

    suffix = "_dark" if dark_mode else ""
    subdir = os.path.join(outdir, "dark") if dark_mode else outdir

    plt.figure(figsize=(12, 8))
    sns.barplot(data=sorted_df, x="WR", y="Name")
    plt.title("Winrates")
    plt.xlabel("Winrate (%)")
    plt.ylabel("Bey")
    plt.tight_layout()
    plt.savefig(os.path.join(subdir, f"winrate_bar_chart{suffix}.png"))
    plt.close()

# -------------------
# Heatmaps: win/loss + point diff
# -------------------


def plot_heatmaps(df_hist, outdir, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    beys = sorted(set(df_hist["BeyA"]) | set(df_hist["BeyB"]))
    win_counts = pd.DataFrame(0, index=beys, columns=beys)
    point_diff = pd.DataFrame(0, index=beys, columns=beys)

    for _, m in df_hist.iterrows():
        a, b = m["BeyA"], m["BeyB"]
        sa, sb = m["ScoreA"], m["ScoreB"]
        if sa > sb:
            win_counts.loc[a, b] += 1
        else:
            win_counts.loc[b, a] += 1
        point_diff.loc[a, b] += sa - sb
        point_diff.loc[b, a] += sb - sa

    matches = win_counts + win_counts.T
    winrate = (win_counts / matches.replace(0, np.nan)).fillna(0)

    suffix = "_dark" if dark_mode else ""
    subdir = os.path.join(outdir, "dark") if dark_mode else outdir

    plt.figure(figsize=(18, 14))
    sns.heatmap(winrate, cmap="viridis")
    plt.title("Winrate Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(subdir, f"heatmap_winrate{suffix}.png"))
    plt.close()

    plt.figure(figsize=(18, 14))
    sns.heatmap(point_diff, cmap="coolwarm", center=0)
    plt.title("Point Differential Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(subdir, f"heatmap_pointdiff{suffix}.png"))
    plt.close()

# -------------------
# HTML Galerie mit Grid & Lightbox
# -------------------


def generate_html_gallery(base_dir):
    html_path = os.path.join(base_dir, "index.html")
    sections = {
        "ELO Charts": "elo",
        "Position Charts": "positions",
        "Heatmaps": "heatmaps",
        "Barcharts": "bars"
    }
    html = [
        "<!DOCTYPE html>",
        "<html lang='de'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Beyblade X — Diagramme</title>",
        "<link href='https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/css/lightbox.min.css' rel='stylesheet'>",
        "<style>",
        "body { font-family: Arial; background:#111; color:#eee; padding:20px; }",
        "h1 { color:#6cf; }",
        "h2 { color:#fc6; margin-top:40px; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }",
        ".grid img { width: 100%; height: auto; border: 2px solid #555; border-radius:8px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Diagramm-Galerie</h1>"
    ]
    for title, folder in sections.items():
        html.append(f"<h2>{title}</h2>")
        html.append("<div class='grid'>")
        folder_path = os.path.join(base_dir, folder)
        images = [f for f in os.listdir(folder_path) if f.lower().endswith(".png")]
        for img in sorted(images):
            img_rel = f"{folder}/{img}"
            html.append(f"<a href='{img_rel}' data-lightbox='{folder}'><img src='{img_rel}' alt='{img}'></a>")
        html.append("</div>")
    html.append("<script src='https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/js/lightbox.min.js'></script>")
    html.append("</body></html>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"HTML-Galerie erzeugt: {html_path}")

# -------------------
# Master runner
# -------------------


def generate_all_plots(mode):
    files = load_files(mode)
    ensure_dir(files["outdir"])
    dirs = ensure_subdirs(files["outdir"])

    print(f"Loading data for mode: {mode}")

    df_lb = pd.read_csv(files["leaderboard"])
    df_hist = pd.read_csv(files["history"])
    df_ts = pd.read_csv(files["timeseries"])
    df_pos = pd.read_csv(files["positions"])

    print("Rendering charts...")

    # Generate both light and dark mode plots
    for dark_mode in [False, True]:
        mode_label = "dark mode" if dark_mode else "light mode"
        print(f"\nGenerating {mode_label} plots...")

        # ELO
        plot_elo_combined(df_ts, files["outdir"], dark_mode=dark_mode)
        plot_elo_single(df_ts, dirs["elo"], dark_mode=dark_mode)

        df_pos_frac = create_fractional_positions(df_pos)
        plot_position_timeseries(df_pos_frac, dirs["positions"], dark_mode=dark_mode)

        # Combined positions with proper path handling for dark mode
        if dark_mode:
            combined_pos_path = os.path.join(files["outdir"], "dark", "combined_positions_dark.png")
        else:
            combined_pos_path = os.path.join(files["outdir"], "combined_positions.png")
        plot_combined_positions(df_pos_frac, combined_pos_path, dark_mode=dark_mode)

        # BAR CHARTS
        plot_leaderboard_bars(df_lb, dirs["bars"], dark_mode=dark_mode)
        plot_winrates(df_lb, dirs["bars"], dark_mode=dark_mode)

        # HEATMAPS
        plot_heatmaps(df_hist, dirs["heatmaps"], dark_mode=dark_mode)

    # HTML-Galerie
    generate_html_gallery(files["outdir"])

    # Advanced Visualizations
    result = subprocess.run(
        ["python", "src/visualization/advanced_visualizations.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running advanced_visualizations.py:")
        print(result.stderr)
    else:
        print("Advanced visualizations generated successfully.")

    # Combined ELO Trends Top 5
    result = subprocess.run(
        ["python", "src/visualization/combined_elo_trends_top5.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running combined_elo_trends_top5.py:")
        print(result.stderr)
    else:
        print("Combined ELO Trends Top 5 generated successfully.")

    # Heatmaps
    result = subprocess.run(
        ["python", "src/visualization/heatmaps.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running heatmaps.py:")
        print(result.stderr)
    else:
        print("Heatmaps generated successfully.")

    # Interactive ELO Trends
    result = subprocess.run(
        ["python", "src/visualization/interactive_elo_trends.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running interactive_elo_trends.py:")
        print(result.stderr)
    else:
        print("Interactive ELO Trends generated successfully.")

    # Meta Landscape Plot
    result = subprocess.run(
        ["python", "src/visualization/meta_landscape.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running meta_landscape.py:")
        print(result.stderr)
    else:
        print("Meta Landscape plots generated successfully.")

    # ELO Density Map
    result = subprocess.run(
        ["python", "src/visualization/elo_density_map.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running elo_density_map.py:")
        print(result.stderr)
    else:
        print("ELO Density Map plots generated successfully.")

    # Tier Flow Diagram
    result = subprocess.run(
        ["python", "src/visualization/tier_flow.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running tier_flow.py:")
        print(result.stderr)
    else:
        print("Tier Flow Diagram plots generated successfully.")

    # Individual Interactive ELO Plots
    result = subprocess.run(
        ["python", "src/visualization/individual_interactive_elo.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running individual_interactive_elo.py:")
        print(result.stderr)
    else:
        print("Individual interactive ELO plots generated successfully.")

    # Individual Interactive Position Plots
    result = subprocess.run(
        ["python", "src/visualization/individual_interactive_position.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running individual_interactive_position.py:")
        print(result.stderr)
    else:
        print("Individual interactive position plots generated successfully.")

    # Season Analytics Plots (tier-based, only match_type=season)
    result = subprocess.run(
        ["python", "src/visualization/season_plots.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running season_plots.py:")
        print(result.stderr)
    else:
        print("Season analytics plots generated successfully.")

    print(f"All plots saved to: {files['outdir']}")


def generate_plot_jsons():
    base = "docs/plots"
    subfolders = ["bars", "elo", "heatmaps", "positions"]

    for folder in subfolders:
        path = os.path.join(base, folder)
        files = [f for f in os.listdir(path) if f.lower().endswith(".png")]
        with open(os.path.join(path, "plots.json"), "w") as f:
            json.dump(files, f)

    root_files = [
        f for f in os.listdir(base)
        if f.lower().endswith(".png")
    ]

    with open(os.path.join(base, "plots.json"), "w") as f:
        json.dump(root_files, f)


# -------------------
# Main CLI
# -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()
    generate_all_plots(args.mode)
    generate_plot_jsons()
