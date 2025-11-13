# beyblade_elo.py
import csv, datetime
from collections import defaultdict
import os

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
HISTORY_FILE = "./csv/elo_history.csv"

elos = defaultdict(lambda: START_ELO)
stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0})

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

# --- Main run ---
with open(INPUT_FILE, newline="", encoding="utf-8") as f_in, \
     open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f_hist:
    reader = csv.DictReader(f_in)
    writer = csv.writer(f_hist)
    writer.writerow(["Date","BeyA","BeyB","ScoreA","ScoreB","PreA","PreB","PostA","PostB"])
    matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))
    for m in matches:
        update_elo(m["BeyA"], m["BeyB"], int(m["ScoreA"]), int(m["ScoreB"]), m["Date"], writer)

# --- Save leaderboard ---
with open(LEADERBOARD_FILE, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["Platz","Name","ELO","Spiele","Siege","Niederlagen","Gewonnene Punkte","Verlorene Punkte","Differenz"])
    
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
            s["for"],
            s["against"],
            diff
        ])

print(f"{GREEN}Leaderboard und Historie aktualisiert.{RESET}")
