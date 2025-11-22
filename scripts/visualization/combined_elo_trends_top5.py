# combined_elo_trends_top5.py
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from plot_styles import configure_light_mode, configure_dark_mode

OUTPUT_DIR = "./plots/official"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)

# --- CSV einlesen ---
df_ts = pd.read_csv("./csv/elo_timeseries.csv")
df_adv = pd.read_csv("./csv/advanced_leaderboard.csv")

# --- Top 5 nach ELO ---
top5_beys = df_adv.sort_values(by='ELO', ascending=False).head(5)['Bey'].tolist()

# --- Farbcode nach Volatilität ---


def color_volatility(vol):
    if vol < 5:
        return 'green'
    elif vol < 10:
        return 'orange'
    else:
        return 'red'


bey_colors = {row['Bey']: color_volatility(row['Volatility']) for i, row in df_adv.iterrows()}


def plot_combined_elo_trends(df_ts, top5_beys, bey_colors, output_file, dark_mode=False):
    """Plot combined ELO trends with top 5 highlighted"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()
    
    plt.figure(figsize=(14, 8))

    for bey in df_ts['Bey'].unique():
        df_b = df_ts[df_ts['Bey'] == bey].sort_values(by='MatchIndex')
        matches_played = len(df_b)
        linestyle = '-' if matches_played > 1 else 'dashed'
        linewidth = 2.5 if bey in top5_beys else 0.8
        alpha = 0.9 if bey in top5_beys else 0.5
        color = bey_colors.get(bey, 'gray')

        plt.plot(df_b['MatchIndex'], df_b['ELO'], label=bey, color=color,
                 linestyle=linestyle, linewidth=linewidth, alpha=alpha)

        # Werte auf Linie (nur bei Top 5)
        if bey in top5_beys:
            for x, y in zip(df_b['MatchIndex'], df_b['ELO']):
                plt.text(x, y + 5, f"{int(y)}", fontsize=7, ha='center', va='bottom', alpha=0.8)

    plt.xlabel("Match Index")
    plt.ylabel("ELO")
    plt.title("Beyblade X - ELO Verläufe aller Beys (Top 5 hervorgehoben)")
    plt.grid(alpha=0.3)
    plt.legend(fontsize=7, ncol=3)
    plt.tight_layout()

    plt.savefig(output_file, dpi=300)
    plt.close()


# Generate light mode plot
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "elo_trends_all_top5.png")
plot_combined_elo_trends(df_ts, top5_beys, bey_colors, OUTPUT_FILE, dark_mode=False)
print(f"Kombiniertes ELO-Trend-Diagramm mit Top 5 hervorgehoben erstellt: {OUTPUT_FILE}")

# Generate dark mode plot
OUTPUT_FILE_DARK = os.path.join(OUTPUT_DIR, "dark", "elo_trends_all_top5_dark.png")
plot_combined_elo_trends(df_ts, top5_beys, bey_colors, OUTPUT_FILE_DARK, dark_mode=True)
print(f"Kombiniertes ELO-Trend-Diagramm (Dark Mode) mit Top 5 hervorgehoben erstellt: {OUTPUT_FILE_DARK}")
