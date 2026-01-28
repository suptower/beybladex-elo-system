#!/usr/bin/env python3
"""
individual_interactive_position.py
Generates interactive Plotly position history charts for individual Beyblades.
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

from plot_styles import get_text_color, get_bg_color, get_grid_color  # noqa: E402

# Output directories
OUTPUT_DIR = "./docs/plots/positions/interactive"
OUTPUT_DIR_DARK = "./docs/plots/positions/interactive/dark"

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR_DARK, exist_ok=True)

# Data files
TIMESERIES_FILE = "./docs/data/position_timeseries.csv"
HISTORY_FILE = "./docs/data/elo_history.csv"
MATCHES_FILE = "./docs/data/matches.csv"


def load_data():
    """Load all necessary data files"""
    df_pos = pd.read_csv(TIMESERIES_FILE)
    df_hist = pd.read_csv(HISTORY_FILE)
    df_matches = pd.read_csv(MATCHES_FILE)

    # Clean and convert data types
    df_pos["Position"] = pd.to_numeric(df_pos["Position"], errors="coerce")
    df_pos["MatchIndex"] = df_pos["MatchIndex"].astype(int)
    df_pos = df_pos.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    return df_pos, df_hist, df_matches


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
    """Create an interactive Plotly chart for a single Beyblade's position history"""
    template = "plotly_dark" if dark_mode else "plotly_white"

    # Get colors based on theme
    text_color = get_text_color(dark_mode)
    bg_color = get_bg_color(dark_mode)
    grid_color = get_grid_color(dark_mode)

    # Calculate statistics
    avg_position = df_bey["Position"].mean()
    median_position = df_bey["Position"].median()
    best_position = df_bey["Position"].min()  # Best = lowest number (e.g., 1 is best)
    worst_position = df_bey["Position"].max()  # Worst = highest number (e.g., 36 is worst)
    best_idx = df_bey["Position"].idxmin()
    worst_idx = df_bey["Position"].idxmax()

    # Prepare hover text with match details
    hover_texts = []
    for idx, row in df_bey.iterrows():
        opponent, score, result = get_match_details(bey, row['Date'], df_hist, df_matches)

        # Calculate position change
        if idx > df_bey.index[0]:
            prev_position = df_bey.loc[df_bey.index[df_bey.index.get_loc(idx) - 1], "Position"]
            position_change = row["Position"] - prev_position
            # Note: negative change is good (moved up), positive is bad (moved down)
            if position_change < 0:
                position_change_str = f"↑{abs(int(position_change))}"
            elif position_change > 0:
                position_change_str = f"↓{int(position_change)}"
            else:
                position_change_str = "="
        else:
            position_change_str = "N/A"

        hover_text = (
            f"<b>{bey}</b><br>"
            f"Date: {row['Date']}<br>"
            f"Match: #{int(row['MatchIndex'])}<br>"
            f"Position: {int(row['Position'])} ({position_change_str})<br>"
            f"Opponent: {opponent}<br>"
            f"Score: {score}<br>"
            f"Result: {result}"
        )
        hover_texts.append(hover_text)

    # Create figure
    fig = go.Figure()

    # Main position line
    fig.add_trace(go.Scatter(
        x=df_bey["MatchIndex"],
        y=df_bey["Position"],
        mode='lines+markers',
        name='Position History',
        line=dict(color='#6366f1', width=2.5),
        marker=dict(size=6, color='#6366f1'),
        hovertext=hover_texts,
        hoverinfo='text',
        hovertemplate='%{hovertext}<extra></extra>'
    ))

    # Add average line
    fig.add_trace(go.Scatter(
        x=[df_bey["MatchIndex"].min(), df_bey["MatchIndex"].max()],
        y=[avg_position, avg_position],
        mode='lines',
        name=f'Average: {avg_position:.1f}',
        line=dict(color='blue', dash='dash', width=1.5),
        hovertemplate=f'Average Position: {avg_position:.1f}<extra></extra>'
    ))

    # Add median line
    fig.add_trace(go.Scatter(
        x=[df_bey["MatchIndex"].min(), df_bey["MatchIndex"].max()],
        y=[median_position, median_position],
        mode='lines',
        name=f'Median: {median_position:.1f}',
        line=dict(color='purple', dash='dot', width=1.5),
        hovertemplate=f'Median Position: {median_position:.1f}<extra></extra>'
    ))

    # Highlight best and worst positions (only if they differ)
    if best_position != worst_position:
        # Best position marker (lowest rank number)
        fig.add_trace(go.Scatter(
            x=[df_bey.loc[best_idx, "MatchIndex"]],
            y=[best_position],
            mode='markers',
            name=f'Best: {int(best_position)}',
            marker=dict(size=12, color='green', symbol='star', line=dict(color='darkgreen', width=2)),
            hovertemplate=f'Best Position: {int(best_position)}<extra></extra>'
        ))

        # Worst position marker (highest rank number)
        fig.add_trace(go.Scatter(
            x=[df_bey.loc[worst_idx, "MatchIndex"]],
            y=[worst_position],
            mode='markers',
            name=f'Worst: {int(worst_position)}',
            marker=dict(size=12, color='red', symbol='x', line=dict(color='darkred', width=2)),
            hovertemplate=f'Worst Position: {int(worst_position)}<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"Position History: {bey}",
            font=dict(size=20, color=text_color)
        ),
        xaxis=dict(
            title="Match Index",
            gridcolor=grid_color,
            color=text_color
        ),
        yaxis=dict(
            title="Position",
            gridcolor=grid_color,
            color=text_color,
            autorange="reversed"  # Invert y-axis so position 1 is at the top
        ),
        template=template,
        hovermode="closest",
        plot_bgcolor=bg_color,
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
                activecolor='#6366f1'
            )
        )

    return fig


def generate_all_individual_plots():
    """Generate interactive position plots for all Beyblades"""
    print("Loading data...")
    df_pos, df_hist, df_matches = load_data()

    # Filter to only include active matches (Played == 1)
    df_pos = df_pos[df_pos["Played"] == 1].copy()

    beyblades = df_pos['Bey'].unique()
    total = len(beyblades)

    print(f"Generating interactive position plots for {total} Beyblades...")

    for i, bey in enumerate(beyblades, 1):
        df_bey = df_pos[df_pos['Bey'] == bey].sort_values('MatchIndex')

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

    print("\n✓ Interactive position plots saved to:")
    print(f"  - {OUTPUT_DIR}")
    print(f"  - {OUTPUT_DIR_DARK}")


if __name__ == "__main__":
    generate_all_individual_plots()
