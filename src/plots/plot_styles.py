# plot_styles.py
# Module for managing light and dark mode plot styles

import matplotlib.pyplot as plt
import seaborn as sns


def configure_light_mode():
    """Configure matplotlib for light mode plots."""
    plt.style.use('default')
    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["axes.edgecolor"] = "#e5e7eb"
    plt.rcParams["axes.labelcolor"] = "#1a1a1a"
    plt.rcParams["text.color"] = "#1a1a1a"
    plt.rcParams["xtick.color"] = "#1a1a1a"
    plt.rcParams["ytick.color"] = "#1a1a1a"
    plt.rcParams["grid.color"] = "#e5e7eb"
    plt.rcParams["grid.alpha"] = 0.5


def configure_dark_mode():
    """Configure matplotlib for dark mode plots."""
    plt.style.use('dark_background')
    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["figure.facecolor"] = "#0a0a0a"
    plt.rcParams["axes.facecolor"] = "#121212"
    plt.rcParams["axes.edgecolor"] = "#222222"
    plt.rcParams["axes.labelcolor"] = "#e2e2e2"
    plt.rcParams["text.color"] = "#e2e2e2"
    plt.rcParams["xtick.color"] = "#e2e2e2"
    plt.rcParams["ytick.color"] = "#e2e2e2"
    plt.rcParams["grid.color"] = "#222222"
    plt.rcParams["grid.alpha"] = 0.4
    # Apply Beyblade X green-accented color cycle
    sns.set_palette(get_color_palette(dark_mode=True))


def get_color_palette(dark_mode=False):
    """Get color palette appropriate for the mode."""
    if dark_mode:
        # Green-accented palette for the Beyblade X dark theme
        return sns.color_palette([
            "#7bc618", "#22c55e", "#3b82f6", "#f59e0b",
            "#ef4444", "#a78bfa", "#06b6d4", "#fb923c",
        ])
    else:
        # Standard colors for light mode
        return sns.color_palette("deep")


def get_text_color(dark_mode=False):
    """Get appropriate text color for the mode."""
    return '#e2e2e2' if dark_mode else 'black'


def get_heatmap_cmap(dark_mode=False):
    """Get appropriate heatmap colormap for the mode."""
    # viridis works well in both modes
    return "viridis"


def get_diverging_cmap(dark_mode=False):
    """Get appropriate diverging colormap for the mode."""
    # coolwarm works well in both modes
    return "coolwarm"


def get_bg_color(dark_mode=False):
    """Get appropriate background color for Plotly plots."""
    return '#0a0a0a' if dark_mode else 'white'


def get_plot_bg_color(dark_mode=False):
    """Get appropriate plot area background color for Plotly plots."""
    return '#121212' if dark_mode else 'white'


def get_grid_color(dark_mode=False):
    """Get appropriate grid color for Plotly plots."""
    return '#222222' if dark_mode else '#e5e7eb'


def get_accent_color(dark_mode=False):
    """Get appropriate accent/highlight color."""
    return '#7bc618' if dark_mode else '#3d6e00'


def generate_dynamic_yticks(min_pos, max_pos):
    """
    Generate dynamic yticks for position plots based on the actual data range.

    Args:
        min_pos: Minimum position value in the data
        max_pos: Maximum position value in the data

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


def calculate_dynamic_plot_dimensions(min_pos, max_pos):
    """
    Calculate appropriate plot height and y-axis limits based on actual data range.

    Args:
        min_pos: Minimum position value in the data
        max_pos: Maximum position value in the data

    Returns:
        Tuple of (height, ylim_max, ylim_min) where:
        - height: Figure height in inches
        - ylim_max: Upper limit for y-axis (lower position number, at top)
        - ylim_min: Lower limit for y-axis (higher position number, at bottom)
    """
    # Calculate the position range
    pos_range = max_pos - min_pos

    # Add some padding above and below the actual data
    # Use smaller padding for small ranges, more for larger ranges
    if pos_range <= 5:
        padding = 1.0
    elif pos_range <= 10:
        padding = 1.5
    elif pos_range <= 20:
        padding = 2.0
    else:
        padding = 2.5

    # Calculate figure height based on range (min 3.0, max 12.0 inches)
    height = max(3.0, min(12.0, 3.0 + pos_range * 0.22))

    # Calculate y-axis limits with padding
    # For position plots, lower numbers are better (at top), so ylim is (max, min)
    ylim_min = max_pos + padding  # Bottom of chart (worse position)
    ylim_max = max(0.5, min_pos - padding)  # Top of chart (better position)

    # Always show position 1 for reference if it's close to the range
    if min_pos <= 5:
        ylim_max = 0.5

    return height, ylim_max, ylim_min
