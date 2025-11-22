# head_to_head_heatmaps_full.py
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np
import sys

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from plot_styles import configure_light_mode, configure_dark_mode

# --- Ordner für Diagramme ---
OUTPUT_DIR = "./plots/official"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)

# --- CSV einlesen ---
df_hist = pd.read_csv("./csv/elo_history.csv")  # Date,BeyA,BeyB,ScoreA,ScoreB,...

df_adv = pd.read_csv("./csv/advanced_leaderboard.csv")  # enthält ELO

# --- Gewinner-Spalte ---
df_hist['winner'] = df_hist.apply(lambda r: r['BeyA'] if r['ScoreA'] > r['ScoreB'] else r['BeyB'], axis=1)

# --- Listen aller Beys ---
beys = sorted(set(df_hist['BeyA']).union(df_hist['BeyB']))

# --- DataFrames initialisieren ---
winrate_matrix = pd.DataFrame(0, index=beys, columns=beys, dtype=float)
pointdiff_matrix = pd.DataFrame(0, index=beys, columns=beys, dtype=float)
match_counts = pd.DataFrame(0, index=beys, columns=beys, dtype=int)

# --- Daten füllen ---
for _, row in df_hist.iterrows():
    a, b = row['BeyA'], row['BeyB']
    winner = row['winner']
    score_a, score_b = row['ScoreA'], row['ScoreB']

    match_counts.loc[a, b] += 1
    match_counts.loc[b, a] += 1

    # Winrate
    if winner == a:
        winrate_matrix.loc[a, b] += 1
    else:
        winrate_matrix.loc[b, a] += 1

    # Durchschnittliche Punktdifferenz (Bey - Gegner)
    pointdiff_matrix.loc[a, b] += score_a - score_b
    pointdiff_matrix.loc[b, a] += score_b - score_a

# Winrate in Prozent umwandeln & float erzwingen
winrate_matrix = winrate_matrix / match_counts.replace(0, np.nan)
winrate_matrix = winrate_matrix.fillna(0).astype(float)

# Punktedifferenz mitteln & float erzwingen
pointdiff_matrix = pointdiff_matrix / match_counts.replace(0, np.nan)
pointdiff_matrix = pointdiff_matrix.fillna(0).astype(float)


# --- Funktionen für Heatmaps ---
def plot_heatmap(matrix, title, output_file, annot=False, cmap='YlOrRd', center=None, dark_mode=False):
    if dark_mode:
        configure_dark_mode()
    else:
        configure_light_mode()
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(matrix, annot=annot, fmt=".2f" if annot else "", cmap=cmap, center=center,
                cbar_kws={'label': title.split('-')[-1].strip()})
    plt.title(title)
    plt.ylabel("Bey")
    plt.xlabel("Gegner")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()


# --- Heatmaps für alle Beys ---
plot_heatmap(winrate_matrix, "Beyblade X - Head-to-Head Winrate (All Beys)",
             os.path.join(OUTPUT_DIR, "heatmap_winrate_all.png"), annot=False)

plot_heatmap(pointdiff_matrix, "Beyblade X - Head-to-Head Avg Point Diff (All Beys)",
             os.path.join(OUTPUT_DIR, "heatmap_pointdiff_all.png"), annot=False, cmap='RdBu_r', center=0)

# Dark mode versions
plot_heatmap(winrate_matrix, "Beyblade X - Head-to-Head Winrate (All Beys)",
             os.path.join(OUTPUT_DIR, "dark", "heatmap_winrate_all_dark.png"), annot=False, dark_mode=True)

plot_heatmap(pointdiff_matrix, "Beyblade X - Head-to-Head Avg Point Diff (All Beys)",
             os.path.join(OUTPUT_DIR, "dark", "heatmap_pointdiff_all_dark.png"), annot=False, cmap='RdBu_r', center=0, dark_mode=True)

# --- Top 10 nach ELO ---
top10_beys = df_adv.sort_values('ELO', ascending=False)['Bey'].head(10).tolist()
winrate_top10 = winrate_matrix.loc[top10_beys, top10_beys]
pointdiff_top10 = pointdiff_matrix.loc[top10_beys, top10_beys]

plot_heatmap(winrate_top10, "Beyblade X - Head-to-Head Winrate (Top 10)",
             os.path.join(OUTPUT_DIR, "heatmap_winrate_top10.png"), annot=True)

plot_heatmap(pointdiff_top10, "Beyblade X - Head-to-Head Avg Point Diff (Top 10)",
             os.path.join(OUTPUT_DIR, "heatmap_pointdiff_top10.png"), annot=True, cmap='RdBu_r', center=0)

# Dark mode versions
plot_heatmap(winrate_top10, "Beyblade X - Head-to-Head Winrate (Top 10)",
             os.path.join(OUTPUT_DIR, "dark", "heatmap_winrate_top10_dark.png"), annot=True, dark_mode=True)

plot_heatmap(pointdiff_top10, "Beyblade X - Head-to-Head Avg Point Diff (Top 10)",
             os.path.join(OUTPUT_DIR, "dark", "heatmap_pointdiff_top10_dark.png"), annot=True, cmap='RdBu_r', center=0, dark_mode=True)

print("Heatmaps erstellt:")
print(f"   {os.path.join(OUTPUT_DIR, 'heatmap_winrate_all.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'heatmap_pointdiff_all.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'heatmap_winrate_top10.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'heatmap_pointdiff_top10.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'dark', 'heatmap_winrate_all_dark.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'dark', 'heatmap_pointdiff_all_dark.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'dark', 'heatmap_winrate_top10_dark.png')}")
print(f"   {os.path.join(OUTPUT_DIR, 'dark', 'heatmap_pointdiff_top10_dark.png')}")
