#!/usr/bin/env python3
"""
Standalone position plotting script
Generates clean position plots without overlaps or backward lines
"""

import pandas as pd
import matplotlib.pyplot as plt
import os


def plot_position_timeseries_clean(csv_path="./csv/position_timeseries.csv", output_dir="./docs/plots/positions"):
    """
    Plot position timeseries with a clean, simple approach:
    - Only plot entries when bey actually played (active position changes)
    - Use MatchIndex as x-axis (bey's own match number)
    - No fractional coordinates, no oscillations
    """

    # Read data
    df = pd.read_csv(csv_path)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get all unique beys
    beys = df["Bey"].unique()
    max_rank = len(beys)

    print(f"Plotting positions for {len(beys)} beys...")

    for bey in beys:
        # Get data for this bey, sorted by MatchIndex
        bey_data = df[df["Bey"] == bey].sort_values("MatchIndex").reset_index(drop=True)

        if len(bey_data) == 0:
            continue

        # Create plot
        height = max_rank * 0.15
        plt.figure(figsize=(6, height))

        # Plot: x-axis = MatchIndex, y-axis = Position
        plt.plot(bey_data["MatchIndex"], bey_data["Position"],
                 marker="o", linewidth=1.8, markersize=6)

        # Invert y-axis (position 1 at top)
        plt.gca().invert_yaxis()

        # Set x-axis ticks to match indices
        if len(bey_data["MatchIndex"].unique()) > 0:
            plt.xticks(ticks=bey_data["MatchIndex"].unique())

        # Labels and title
        plt.title(f"Positionsverlauf: {bey}")
        plt.xlabel("Match Index")
        plt.ylabel("Position")

        # Y-axis limits and ticks
        plt.ylim(max_rank + 0.5, 0.5)
        plt.yticks([1, 5, 10, 15, 20, 25, 30, 36])

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
