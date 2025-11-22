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
    plt.rcParams["figure.facecolor"] = "#0f172a"
    plt.rcParams["axes.facecolor"] = "#1e293b"
    plt.rcParams["axes.edgecolor"] = "#334155"
    plt.rcParams["axes.labelcolor"] = "#f1f5f9"
    plt.rcParams["text.color"] = "#f1f5f9"
    plt.rcParams["xtick.color"] = "#f1f5f9"
    plt.rcParams["ytick.color"] = "#f1f5f9"
    plt.rcParams["grid.color"] = "#334155"
    plt.rcParams["grid.alpha"] = 0.3


def get_color_palette(dark_mode=False):
    """Get color palette appropriate for the mode."""
    if dark_mode:
        # Brighter, more vibrant colors for dark mode
        return sns.color_palette("bright")
    else:
        # Standard colors for light mode
        return sns.color_palette("deep")


def get_text_color(dark_mode=False):
    """Get appropriate text color for the mode."""
    return 'white' if dark_mode else 'black'


def get_heatmap_cmap(dark_mode=False):
    """Get appropriate heatmap colormap for the mode."""
    # viridis works well in both modes
    return "viridis"


def get_diverging_cmap(dark_mode=False):
    """Get appropriate diverging colormap for the mode."""
    # coolwarm works well in both modes
    return "coolwarm"
