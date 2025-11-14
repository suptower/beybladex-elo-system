# advanced_visualizations.py
import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Dateien und Verzeichnisse ---
LEADERBOARD_FILE = "./csv/leaderboard.csv"
ADVANCED_FILE = "./csv/advanced_leaderboard.csv"
OUTPUT_DIR = "./plots/official"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

# --- 1. Winrate Balkendiagramm ---
df_adv['WinrateInt'] = (df_adv['Winrate'].str.rstrip('%').astype(float)).round().astype(int)
df_sorted = df_adv.sort_values(by='WinrateInt', ascending=False)

plt.figure(figsize=(12,6))
bars = plt.bar(df_sorted['Bey'], df_sorted['WinrateInt'], color=df_sorted['WinrateInt'].apply(color_winrate))
for bar, value in zip(bars, df_sorted['WinrateInt']):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f"{value}%", ha='center', va='bottom', fontsize=8)
plt.xticks(rotation=45, ha='right')
plt.ylabel("Winrate (%)")
plt.title("Beyblade X - Winrate Übersicht")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "winrate_bar.png"), dpi=300)
plt.close()

# --- 2. Volatilität Balken ---
df_sorted_vol = df_adv.sort_values(by='Volatility', ascending=False)
plt.figure(figsize=(12,6))
bars = plt.bar(df_sorted_vol['Bey'], df_sorted_vol['Volatility'], color=df_sorted_vol['Volatility'].apply(color_volatility))
for bar, value in zip(bars, df_sorted_vol['Volatility']):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f"{value}", ha='center', va='bottom', fontsize=8)
plt.xticks(rotation=45, ha='right')
plt.ylabel("Volatilität (Std. Abw. ΔELO)")
plt.title("Beyblade X - ELO Volatilität")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "volatility_bar.png"), dpi=300)
plt.close()

# --- 3. Upset Wins / Losses Balken ---
df_sorted_upset = df_adv.sort_values(by='UpsetWins', ascending=False)
plt.figure(figsize=(12,6))
plt.bar(df_sorted_upset['Bey'], df_sorted_upset['UpsetWins'], color='blue', label='Upset Wins')
plt.bar(df_sorted_upset['Bey'], df_sorted_upset['UpsetLosses'], color='red', label='Upset Losses', bottom=df_sorted_upset['UpsetWins'])
plt.xticks(rotation=45, ha='right')
plt.ylabel("Anzahl Upsets")
plt.title("Beyblade X - Upset Wins / Losses")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "upset_bar.png"), dpi=300)
plt.close()

# --- 4. Punktedifferenz vs Winrate Scatterplot ---
df_adv['WinrateFloat'] = df_adv['Winrate'].str.rstrip('%').astype(float)
plt.figure(figsize=(10,6))
plt.scatter(df_adv['AvgPointDiff'], df_adv['WinrateFloat'], s=df_adv['Matches']*5, c='skyblue', alpha=0.7)
for i, row in df_adv.iterrows():
    plt.text(row['AvgPointDiff'], row['WinrateFloat']+0.5, row['Bey'], fontsize=8, rotation=45)
plt.xlabel("Durchschnittliche Punktedifferenz pro Match")
plt.ylabel("Winrate (%)")
plt.title("Beyblade X - Winrate vs. Punktedifferenz")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "winrate_vs_pointdiff.png"), dpi=300)
plt.close()

# --- 5. Optional: ELO-Trend Linienchart ---
# Für Übersichtlichkeit nur Top 5 nach ELO
df_trend = df_adv.sort_values(by='ELO', ascending=False).head(5)
plt.figure(figsize=(12,6))
for bey in df_trend['Bey']:
    # ELO Verlauf aus timeseries CSV
    df_ts = pd.read_csv("./csv/elo_timeseries.csv")
    df_bey = df_ts[(df_ts['Bey']==bey)].sort_values(by='MatchIndex')  # MatchIndex oder fortlaufende Nummer
    plt.plot(df_bey['MatchIndex'], df_bey['ELO'], label=bey)
plt.xlabel("Match Index")
plt.ylabel("ELO")
plt.title("Beyblade X - Top 5 ELO Verläufe")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "elo_trends_top5.png"), dpi=300)
plt.close()

print(f" Alle Advanced-Diagramme erstellt in: {OUTPUT_DIR}")