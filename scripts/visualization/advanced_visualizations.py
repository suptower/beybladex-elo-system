# advanced_visualizations.py
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Add scripts directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from plot_styles import configure_light_mode, configure_dark_mode  # noqa: E402

# --- Dateien und Verzeichnisse ---
LEADERBOARD_FILE = "./csv/leaderboard.csv"
ADVANCED_FILE = "./csv/advanced_leaderboard.csv"
OUTPUT_DIR = "./docs/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)

# --- CSV einlesen ---
df_adv = pd.read_csv(ADVANCED_FILE)

# --- Hilfsfunktion für Farben nach Wert ---


def color_winrate(winrate):
    if winrate >= 70:
        return 'green'
    elif winrate >= 50:
        return 'orange'
    else:
        return 'red'


def color_volatility(vol):
    if vol < 5:
        return 'green'
    elif vol < 10:
        return 'orange'
    else:
        return 'red'


def plot_winrate_bar(df_adv, output_file, dark_mode=False):
    """Plot winrate bar chart"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_sorted = df_adv.sort_values(by='WinrateInt', ascending=False)

    plt.figure(figsize=(12, 6))
    bars = plt.bar(df_sorted['Bey'], df_sorted['WinrateInt'], color=df_sorted['WinrateInt'].apply(color_winrate))
    for bar, value in zip(bars, df_sorted['WinrateInt']):
        size = bar.get_x() + bar.get_width() / 2
        plt.text(size, bar.get_height() + 1, f"{value}%", ha='center', va='bottom', fontsize=8)
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Winrate (%)")
    plt.title("Beyblade X - Winrate Übersicht")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def plot_volatility_bar(df_adv, output_file, dark_mode=False):
    """Plot volatility bar chart"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_sorted_vol = df_adv.sort_values(by='Volatility', ascending=False)

    plt.figure(figsize=(12, 6))
    bars = plt.bar(df_sorted_vol['Bey'], df_sorted_vol['Volatility'],
                   color=df_sorted_vol['Volatility'].apply(color_volatility))
    for bar, value in zip(bars, df_sorted_vol['Volatility']):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height()
                 + 0.1, f"{value}", ha='center', va='bottom', fontsize=8)
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Volatilität (Std. Abw. ΔELO)")
    plt.title("Beyblade X - ELO Volatilität")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def plot_upset_bar(df_adv, output_file, dark_mode=False):
    """Plot upset wins/losses bar chart"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    df_sorted_upset = df_adv.sort_values(by='UpsetWins', ascending=False)

    plt.figure(figsize=(12, 6))
    plt.bar(df_sorted_upset['Bey'], df_sorted_upset['UpsetWins'], color='blue', label='Upset Wins')
    plt.bar(df_sorted_upset['Bey'], df_sorted_upset['UpsetLosses'], color='red',
            label='Upset Losses', bottom=df_sorted_upset['UpsetWins'])
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Anzahl Upsets")
    plt.title("Beyblade X - Upset Wins / Losses")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def plot_winrate_vs_pointdiff(df_adv, output_file, dark_mode=False):
    """Plot winrate vs point difference scatter"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    plt.figure(figsize=(10, 6))
    plt.scatter(df_adv['AvgPointDiff'], df_adv['WinrateFloat'], s=df_adv['Matches'] * 5, c='skyblue', alpha=0.7)
    for i, row in df_adv.iterrows():
        plt.text(row['AvgPointDiff'], row['WinrateFloat'] + 0.5, row['Bey'], fontsize=8, rotation=45)
    plt.xlabel("Durchschnittliche Punktedifferenz pro Match")
    plt.ylabel("Winrate (%)")
    plt.title("Beyblade X - Winrate vs. Punktedifferenz")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


def plot_elo_trends_top5(output_file, dark_mode=False):
    """Plot ELO trends for top 5"""
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()

    # ELO Verlauf aus timeseries CSV
    df_ts = pd.read_csv("./csv/elo_timeseries.csv")
    df_adv = pd.read_csv("./csv/advanced_leaderboard.csv")
    df_trend = df_adv.sort_values(by='ELO', ascending=False).head(5)

    plt.figure(figsize=(12, 6))
    for bey in df_trend['Bey']:
        df_bey = df_ts[(df_ts['Bey'] == bey)].sort_values(by='MatchIndex')
        plt.plot(df_bey['MatchIndex'], df_bey['ELO'], label=bey)
    plt.xlabel("Match Index")
    plt.ylabel("ELO")
    plt.title("Beyblade X - Top 5 ELO Verläufe")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


# --- 1. Winrate Balkendiagramm ---
df_adv['WinrateInt'] = (df_adv['Winrate'].str.rstrip('%').astype(float)).round().astype(int)
df_adv['WinrateFloat'] = df_adv['Winrate'].str.rstrip('%').astype(float)

# Generate light mode plots
plot_winrate_bar(df_adv, os.path.join(OUTPUT_DIR, "winrate_bar.png"), dark_mode=False)
plot_volatility_bar(df_adv, os.path.join(OUTPUT_DIR, "volatility_bar.png"), dark_mode=False)
plot_upset_bar(df_adv, os.path.join(OUTPUT_DIR, "upset_bar.png"), dark_mode=False)
plot_winrate_vs_pointdiff(df_adv, os.path.join(OUTPUT_DIR, "winrate_vs_pointdiff.png"), dark_mode=False)
plot_elo_trends_top5(os.path.join(OUTPUT_DIR, "elo_trends_top5.png"), dark_mode=False)

# Generate dark mode plots
plot_winrate_bar(df_adv, os.path.join(OUTPUT_DIR, "dark", "winrate_bar_dark.png"), dark_mode=True)
plot_volatility_bar(df_adv, os.path.join(OUTPUT_DIR, "dark", "volatility_bar_dark.png"), dark_mode=True)
plot_upset_bar(df_adv, os.path.join(OUTPUT_DIR, "dark", "upset_bar_dark.png"), dark_mode=True)
plot_winrate_vs_pointdiff(df_adv, os.path.join(OUTPUT_DIR, "dark", "winrate_vs_pointdiff_dark.png"), dark_mode=True)
plot_elo_trends_top5(os.path.join(OUTPUT_DIR, "dark", "elo_trends_top5_dark.png"), dark_mode=True)

print(f" Alle Advanced-Diagramme erstellt in: {OUTPUT_DIR}")
