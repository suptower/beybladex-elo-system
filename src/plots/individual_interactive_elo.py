#!/usr/bin/env python3
"""
individual_interactive_elo.py
Generates interactive Plotly ELO history charts for individual Beyblades.
These replace the static PNG plots with interactive HTML versions.
"""

import os
import sys
import pandas as pd
import plotly.graph_objects as go

# Add parent directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import get_text_color, get_bg_color, get_grid_color, get_plot_bg_color, get_accent_color  # noqa: E402
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))); del _sys, _os
from src.config.paths import (
    PLOTS_ELO_INTERACTIVE_DIR,
    PLOTS_ELO_INTERACTIVE_DARK_DIR,
    ELO_TIMESERIES_CSV,
    ELO_HISTORY_CSV,
    MATCHES_CSV,
)

# Output directories
OUTPUT_DIR = PLOTS_ELO_INTERACTIVE_DIR
OUTPUT_DIR_DARK = PLOTS_ELO_INTERACTIVE_DARK_DIR

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR_DARK, exist_ok=True)

# Data files
TIMESERIES_FILE = ELO_TIMESERIES_CSV
HISTORY_FILE = ELO_HISTORY_CSV
MATCHES_FILE = MATCHES_CSV


def load_data():
    """Load all necessary data files"""
    df_ts = pd.read_csv(TIMESERIES_FILE)
    df_hist = pd.read_csv(HISTORY_FILE)
    df_matches = pd.read_csv(MATCHES_FILE)

    # Clean and convert data types
    df_ts["ELO"] = pd.to_numeric(df_ts["ELO"], errors="coerce")
    df_ts["MatchIndex"] = df_ts["MatchIndex"].astype(int)
    df_ts = df_ts.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    return df_ts, df_hist, df_matches


def get_match_details(bey, date, df_hist, df_matches):
    """Get opponent and match result for a specific bey on a specific date"""
    # Find match in history
    hist_day = df_hist[
        (df_hist['Date'] == date) &
        ((df_hist['BeyA'] == bey) | (df_hist['BeyB'] == bey))
    ]

    if len(hist_day) == 0:
        return "Unknown", "N/A", "N/A"

    match = hist_day.iloc[0]
    is_bey_a = match['BeyA'] == bey
    opponent = match['BeyB'] if is_bey_a else match['BeyA']

    # Find match in matches.csv to get score
    match_day = df_matches[
        (df_matches['Date'] == date) &
        (((df_matches['BeyA'] == bey) & (df_matches['BeyB'] == opponent)) |
         ((df_matches['BeyB'] == bey) & (df_matches['BeyA'] == opponent)))
    ]

    if len(match_day) > 0:
        m = match_day.iloc[0]
        if m['BeyA'] == bey:
            my_score = m['ScoreA']
            opp_score = m['ScoreB']
            result = "Win" if m['ScoreA'] > m['ScoreB'] else "Loss"
        else:
            my_score = m['ScoreB']
            opp_score = m['ScoreA']
            result = "Win" if m['ScoreB'] > m['ScoreA'] else "Loss"
        score = f"{my_score}-{opp_score}"
    else:
        score = "N/A"
        result = "N/A"

    return opponent, score, result


def create_interactive_plot(bey, df_bey, df_hist, df_matches, dark_mode=False):
    """Create an interactive Plotly chart for a single Beyblade"""
    template = "plotly_dark" if dark_mode else "plotly_white"

    # Get colors based on theme
    text_color = get_text_color(dark_mode)
    bg_color = get_bg_color(dark_mode)
    plot_bg_color = get_plot_bg_color(dark_mode)
    grid_color = get_grid_color(dark_mode)
    accent_color = get_accent_color(dark_mode)

    # Calculate statistics
    avg_elo = df_bey["ELO"].mean()
    median_elo = df_bey["ELO"].median()
    max_elo = df_bey["ELO"].max()
    min_elo = df_bey["ELO"].min()
    max_idx = df_bey["ELO"].idxmax()
    min_idx = df_bey["ELO"].idxmin()

    # Prepare hover text with match details
    hover_texts = []
    for idx, row in df_bey.iterrows():
        opponent, score, result = get_match_details(bey, row['Date'], df_hist, df_matches)

        # Calculate ELO change
        if idx > df_bey.index[0]:
            prev_elo = df_bey.loc[df_bey.index[df_bey.index.get_loc(idx) - 1], "ELO"]
            elo_change = row["ELO"] - prev_elo
            elo_change_str = f"+{elo_change:.1f}" if elo_change >= 0 else f"{elo_change:.1f}"
        else:
            elo_change_str = "N/A"

        hover_text = (
            f"<b>{bey}</b><br>"
            f"Date: {row['Date']}<br>"
            f"Match: #{int(row['MatchIndex'])}<br>"
            f"ELO: {row['ELO']:.1f} ({elo_change_str})<br>"
            f"Opponent: {opponent}<br>"
            f"Score: {score}<br>"
            f"Result: {result}"
        )
        hover_texts.append(hover_text)

    # Create figure
    fig = go.Figure()

    # Main ELO line
    fig.add_trace(go.Scatter(
        x=df_bey["MatchIndex"],
        y=df_bey["ELO"],
        mode='lines+markers',
        name='ELO History',
        line=dict(color=accent_color, width=2.5),
        marker=dict(size=6, color=accent_color),
        hovertext=hover_texts,
        hoverinfo='text',
        hovertemplate='%{hovertext}<extra></extra>'
    ))

    # Add average line
    fig.add_trace(go.Scatter(
        x=[df_bey["MatchIndex"].min(), df_bey["MatchIndex"].max()],
        y=[avg_elo, avg_elo],
        mode='lines',
        name=f'Average: {avg_elo:.0f}',
        line=dict(color='#3b82f6', dash='dash', width=1.5),
        hovertemplate=f'Average ELO: {avg_elo:.1f}<extra></extra>'
    ))

    # Add median line
    fig.add_trace(go.Scatter(
        x=[df_bey["MatchIndex"].min(), df_bey["MatchIndex"].max()],
        y=[median_elo, median_elo],
        mode='lines',
        name=f'Median: {median_elo:.0f}',
        line=dict(color='#a78bfa', dash='dot', width=1.5),
        hovertemplate=f'Median ELO: {median_elo:.1f}<extra></extra>'
    ))

    # Highlight peak and low (only if they differ)
    if max_elo != min_elo:
        # Peak marker
        fig.add_trace(go.Scatter(
            x=[df_bey.loc[max_idx, "MatchIndex"]],
            y=[max_elo],
            mode='markers',
            name=f'Peak: {max_elo:.0f}',
            marker=dict(size=12, color='green', symbol='star', line=dict(color='darkgreen', width=2)),
            hovertemplate=f'Peak ELO: {max_elo:.1f}<extra></extra>'
        ))

        # Low marker
        fig.add_trace(go.Scatter(
            x=[df_bey.loc[min_idx, "MatchIndex"]],
            y=[min_elo],
            mode='markers',
            name=f'Low: {min_elo:.0f}',
            marker=dict(size=12, color='red', symbol='x', line=dict(color='darkred', width=2)),
            hovertemplate=f'Low ELO: {min_elo:.1f}<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"ELO History: {bey}",
            font=dict(size=20, color=text_color)
        ),
        xaxis=dict(
            title="Match Index",
            gridcolor=grid_color,
            color=text_color
        ),
        yaxis=dict(
            title="ELO Rating",
            gridcolor=grid_color,
            color=text_color
        ),
        template=template,
        hovermode="closest",
        plot_bgcolor=plot_bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color=text_color)
        ),
        height=500,
        margin=dict(l=60, r=30, t=80, b=100)
    )

    # Add range selector if there are enough data points
    if len(df_bey) > 10:
        fig.update_xaxes(
            rangeslider=dict(visible=False),
            rangeselector=dict(
                buttons=list([
                    dict(count=5, label="Last 5", step="all", stepmode="backward"),
                    dict(count=10, label="Last 10", step="all", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                font=dict(color=text_color),
                bgcolor=bg_color,
                activecolor=accent_color
            )
        )

    return fig


def generate_all_individual_plots():
    """Generate interactive plots for all Beyblades"""
    print("Loading data...")
    df_ts, df_hist, df_matches = load_data()

    beyblades = df_ts['Bey'].unique()
    total = len(beyblades)

    print(f"Generating interactive ELO plots for {total} Beyblades...")

    for i, bey in enumerate(beyblades, 1):
        df_bey = df_ts[df_ts['Bey'] == bey].sort_values('MatchIndex')

        if len(df_bey) < 2:
            print(f"  [{i}/{total}] Skipping {bey} (insufficient data)")
            continue

        # Generate light mode plot
        fig_light = create_interactive_plot(bey, df_bey, df_hist, df_matches, dark_mode=False)
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
        output_file = os.path.join(OUTPUT_DIR, f"{safe_name}.html")
        fig_light.write_html(output_file, config={'displayModeBar': True, 'responsive': True})

        # Generate dark mode plot
        fig_dark = create_interactive_plot(bey, df_bey, df_hist, df_matches, dark_mode=True)
        output_file_dark = os.path.join(OUTPUT_DIR_DARK, f"{safe_name}_dark.html")
        fig_dark.write_html(output_file_dark, config={'displayModeBar': True, 'responsive': True})

        print(f"  [{i}/{total}] Generated: {bey}")

    print("\n✓ Interactive ELO plots saved to:")
    print(f"  - {OUTPUT_DIR}")
    print(f"  - {OUTPUT_DIR_DARK}")


if __name__ == "__main__":
    generate_all_individual_plots()
