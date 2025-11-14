# beyblade_elo.py
import csv, datetime
from collections import defaultdict
import os
import pandas as pd
import statistics

# Aktiviert ANSI-Farben in Windows-Terminals (macht nix auf anderen Systemen)
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

print(f"{BOLD}{CYAN}Starte Beyblade X ELO-Update...{RESET}")
print(f"{YELLOW}Berechne neue ELOs...{RESET}")



K = 32
START_ELO = 1000
INPUT_FILE = "./csv/matches.csv"
LEADERBOARD_FILE = "./csv/leaderboard.csv"
ADVANCED_LEADERBOARD_FILE = "./csv/advanced_leaderboard.csv"
HISTORY_FILE = "./csv/elo_history.csv"
TIMESERIES_FILE = "./csv/elo_timeseries.csv"

elos = defaultdict(lambda: START_ELO)
elo_deltas = defaultdict(list)
stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0, "winrate":0.0})

def expected(a,b):
    return 1 / (1 + 10 ** ((b - a) / 400))

def update_elo(a,b,sa,sb,date,writer):
    ra, rb = elos[a], elos[b]
    ea, eb = expected(ra, rb), expected(rb, ra)
    total = sa + sb
    if total == 0:
        return
    s_a, s_b = sa / total, sb / total
    new_a = ra + K * (s_a - ea)
    new_b = rb + K * (s_b - eb)
    elos[a], elos[b] = new_a, new_b

    # Save history
    writer.writerow([date,a,b,sa,sb,round(ra,2),round(rb,2),round(new_a,2),round(new_b,2)])

    # Stats
    elo_deltas[a].append(new_a - ra)
    elo_deltas[b].append(new_b - rb)

    stats[a]["for"] += sa
    stats[a]["against"] += sb
    stats[b]["for"] += sb
    stats[b]["against"] += sa
    stats[a]["matches"] += 1
    stats[b]["matches"] += 1
    if sa > sb:
        stats[a]["wins"] += 1
        stats[b]["losses"] += 1
    else:
        stats[b]["wins"] += 1
        stats[a]["losses"] += 1

# Calculate winrate
def calculate_winrates():
    for bey, s in stats.items():
        if s["matches"] > 0:
            s["winrate"] = s["wins"] / s["matches"]
        else:
            s["winrate"] = "0%"

# --- Main run ---
with open(INPUT_FILE, newline="", encoding="utf-8") as f_in, \
     open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f_hist:
    reader = csv.DictReader(f_in)
    writer = csv.writer(f_hist)
    writer.writerow(["Date","BeyA","BeyB","ScoreA","ScoreB","PreA","PreB","PostA","PostB"])
    matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))
    for m in matches:
        update_elo(m["BeyA"], m["BeyB"], int(m["ScoreA"]), int(m["ScoreB"]), m["Date"], writer)
    calculate_winrates()

# --- Save leaderboard ---
with open(LEADERBOARD_FILE, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["Platz","Name","ELO","Spiele","Siege","Niederlagen","Winrate","Gewonnene Punkte","Verlorene Punkte","Differenz"])
    
    sorted_beys = sorted(elos.items(), key=lambda x: x[1], reverse=True)
    
    for i, (bey, elo) in enumerate(sorted_beys, start=1):
        s = stats[bey]
        diff = s["for"] - s["against"]
        writer.writerow([
            i,
            bey,
            round(elo),
            s["matches"],
            s["wins"],
            s["losses"],
            f"{round(s['winrate'] * 100, 1)}%",
            s["for"],
            s["against"],
            diff
        ])

print(f"{GREEN}Leaderboard und Historie aktualisiert.{RESET}")

# --- Gestapelte History-Datei erzeugen ---
print(f"{CYAN}Erstelle gestackte ELO-History pro Bey...{RESET}")

# lese history (achte darauf, dass die Reihenfolge in der CSV der Spielreihenfolge entspricht)
df = pd.read_csv(HISTORY_FILE, parse_dates=["Date"])

# füge eine match_id hinzu, die der Zeilenreihenfolge entspricht (falls nicht schon vorhanden)
# falls df bereits in Match-Reihenfolge ist, ist dies die sichere Sequenz
df = df.reset_index(drop=True)
df["match_id"] = df.index + 1  # 1-basierter Match-Index in chronologischer Reihenfolge

# Erzeuge gestackte Tabelle: für jeden Match zwei Zeilen (Bey, ELO, match_id, Date)
df_a = pd.DataFrame({
    "Date": df["Date"],
    "Bey": df["BeyA"],
    "ELO": pd.to_numeric(df["PostA"], errors="coerce"),
    "match_id": df["match_id"]
})

df_b = pd.DataFrame({
    "Date": df["Date"],
    "Bey": df["BeyB"],
    "ELO": pd.to_numeric(df["PostB"], errors="coerce"),
    "match_id": df["match_id"]
})

stacked = pd.concat([df_a, df_b], ignore_index=True)

# Sortiere pro Bey nach match_id (wichtig: nicht nur nach Date)
stacked = stacked.sort_values(["Bey", "match_id"]).reset_index(drop=True)

# MatchIndex pro Bey (Anzahl der bisherigen Matches für diesen Bey)
stacked["MatchIndex"] = stacked.groupby("Bey").cumcount() + 1
stacked["MatchIndex"] = stacked["MatchIndex"].astype(int)

# Add initial entries (MatchIndex 0 with START_ELO) for each Bey
unique_beys = stacked["Bey"].unique()
initial_entries = []
for bey in unique_beys:
    # Get the earliest date for this Bey
    bey_data = stacked[stacked["Bey"] == bey]
    earliest_date = bey_data["Date"].min()
    initial_entries.append({
        "Date": earliest_date,
        "Bey": bey,
        "ELO": START_ELO,
        "match_id": 0,
        "MatchIndex": 0
    })

initial_df = pd.DataFrame(initial_entries)
stacked = pd.concat([initial_df, stacked], ignore_index=True)
stacked = stacked.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

# Optional: falls du eine exakte time-axis willst, kannst du auch:
# stacked["ExactTime"] = pd.to_datetime(stacked["Date"]) + pd.to_timedelta(stacked["match_id"], unit='s')

# Schreibe die Datei
stacked.to_csv(TIMESERIES_FILE, index=False, encoding="utf-8")

print(f"{GREEN}Erzeugt: {TIMESERIES_FILE} ({len(stacked)} Zeilen){RESET}")