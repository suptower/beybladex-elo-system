#!/usr/bin/env python3
"""
Standalone position plotting script
Generates clean position plots with fractional positioning
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from plot_styles import generate_dynamic_yticks, calculate_dynamic_plot_dimensions


def create_fractional_positions(df_pos):
    """
    Create fractional x-axis positions for events within the same MatchIndex.
    This allows visualizing multiple position changes that occur at the same match.
    """
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
            # Distribute evenly between mi and mi+1
            step = 1.0 / (n + 1)
            for i, (base_mi, idx) in enumerate(buffer, start=1):
                df.loc[idx, "PlotX"] = base_mi + i * step

        for idx, row in group.iterrows():
            mi = row["MatchIndex"]
            if prev_mi is None:
                # First point → set directly
                df.loc[idx, "PlotX"] = mi
                prev_mi = mi
                continue

            if mi == prev_mi:
                # Passive event → buffer
                buffer.append((mi, idx))
            else:
                # MI change → flush buffer
                flush_buffer(prev_mi)
                buffer = []
                df.loc[idx, "PlotX"] = mi
                prev_mi = mi

        # Flush last buffer
        flush_buffer(prev_mi)

    df = df.sort_values(["Bey", "PlotX"]).reset_index(drop=True)
    return df


def plot_position_timeseries_clean(csv_path="./docs/data/position_timeseries.csv", output_dir="./docs/plots/positions"):
    """
    Plot position timeseries with fractional positioning:
    - Uses PlotX for x-axis to show fractional positioning
    - Visualizes passive changes within the same match
    """

    # Read data
    df = pd.read_csv(csv_path)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get all unique beys
    beys = df["Bey"].unique()
    max_rank = len(beys)

    print(f"Plotting positions for {len(beys)} beys...")

    # Create fractional positions
    df_frac = create_fractional_positions(df)

    for bey in beys:
        # Get data for this bey, sorted by PlotX
        bey_data = df_frac[df_frac["Bey"] == bey].sort_values("PlotX").reset_index(drop=True)

        if len(bey_data) == 0:
            continue

        # Calculate dynamic plot dimensions based on actual position range
        min_pos = bey_data["Position"].min()
        max_pos = bey_data["Position"].max()
        height = max_rank * 0.15
        ylim_max, ylim_min = calculate_dynamic_plot_dimensions(min_pos, max_pos)

        # Create plot
        plt.figure(figsize=(6, height))

        # Plot: x-axis = PlotX (fractional), y-axis = Position
        plt.plot(bey_data["PlotX"], bey_data["Position"],
                 marker="o", linewidth=1.8, markersize=6)

        # Invert y-axis (position 1 at top)
        plt.gca().invert_yaxis()

        # Let matplotlib automatically determine x-axis ticks for fractional positioning
        # (removed hardcoded xticks to allow fractional values to be displayed)

        # Labels and title
        plt.title(f"Positionsverlauf: {bey}")
        plt.xlabel("Match Index")
        plt.ylabel("Position")

        # Y-axis limits and ticks
        plt.ylim(ylim_min, ylim_max)

        # Generate dynamic yticks based on actual position range
        yticks = generate_dynamic_yticks(min_pos, max_pos)
        plt.yticks(yticks)

        # Grid
        plt.grid(True, alpha=0.4)
        plt.tight_layout()

        # Save
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
        out_path = os.path.join(output_dir, f"{safe_name}_position.png")
        plt.savefig(out_path, dpi=200)
        plt.close()

    print(f"Position plots saved to: {output_dir}")


if __name__ == "__main__":
    plot_position_timeseries_clean()
