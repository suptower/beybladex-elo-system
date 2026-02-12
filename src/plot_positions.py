#!/usr/bin/env python3
"""
Standalone position plotting script
Generates clean position plots without overlaps or backward lines
"""

import pandas as pd
import matplotlib.pyplot as plt
import os


def generate_dynamic_yticks(min_pos, max_pos, max_rank):
    """
    Generate dynamic yticks for position plots based on the actual data range.
    
    Args:
        min_pos: Minimum position value in the data
        max_pos: Maximum position value in the data
        max_rank: Maximum possible rank (total number of beys)
    
    Returns:
        List of ytick positions
    """
    # Always start with position 1 (best possible position)
    ticks = [1]
    
    # Calculate the range of positions
    pos_range = max_pos - min_pos
    
    # Determine appropriate step size based on range
    # We want about 5-8 ticks for good readability
    if pos_range <= 5:
        # Small range: use every position
        step = 1
    elif pos_range <= 10:
        # Medium-small range: use step of 2
        step = 2
    elif pos_range <= 20:
        # Medium range: use step of 5
        step = 5
    elif pos_range <= 40:
        # Large range: use step of 10
        step = 10
    else:
        # Very large range: use step of 15
        step = 15
    
    # Add intermediate ticks at regular intervals
    # Start from the first multiple of step that's >= min_pos
    if min_pos <= 1:
        # If min_pos is 1, start from the next step
        current = step
    else:
        # Otherwise start from the first step >= min_pos
        current = ((min_pos - 1) // step + 1) * step
    
    # Add ticks up to max_pos
    while current <= max_pos:
        if current not in ticks:
            ticks.append(current)
        current += step
    
    # Always include the actual min and max from the data
    if min_pos not in ticks and min_pos > 1:
        ticks.append(min_pos)
    if max_pos not in ticks:
        ticks.append(max_pos)
    
    # Sort and return
    ticks = sorted(set(ticks))
    return ticks


def plot_position_timeseries_clean(csv_path="./docs/data/position_timeseries.csv", output_dir="./docs/plots/positions"):
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
        
        # Generate dynamic yticks based on actual position range
        min_pos = bey_data["Position"].min()
        max_pos = bey_data["Position"].max()
        yticks = generate_dynamic_yticks(min_pos, max_pos, max_rank)
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
