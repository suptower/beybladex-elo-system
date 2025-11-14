# beyblade_elo.py — Version 2.3.3
import csv, datetime
from collections import defaultdict
import os
import pandas as pd

os.system("")  # enable ANSI colors on Windows

# Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

# K Factors
K_NEWBIE = 40
K_INTERMEDIATE = 24
K_VETERAN = 12

print(f"{BOLD}{CYAN}Starte Beyblade X ELO-Update...{RESET}")
print(f"{YELLOW}Berechne neue ELOs...{RESET}")

# ---------- CONFIG ----------
START_ELO = 1000
INPUT_FILE = "./csv/matches.csv"
LEADERBOARD_FILE = "./csv/leaderboard.csv"
ADVANCED_LEADERBOARD_FILE = "./csv/advanced_leaderboard.csv"
HISTORY_FILE = "./csv/elo_history.csv"
TIMESERIES_FILE = "./csv/elo_timeseries.csv"
# ----------------------------

# Elo + Stats
elos = defaultdict(lambda: START_ELO)
elo_deltas = defaultdict(list)
stats = defaultdict(lambda: {
    "wins":0, "losses":0, "for":0, "against":0,
    "matches":0, "winrate":0.0
})

# ---------- K-FAKTOR STAFFELUNG ----------
def get_k_factor(matches: int) -> int:
    if matches < 10:
        return K_NEWBIE
    elif matches < 50:
        return K_INTERMEDIATE
    return K_VETERAN
# -----------------------------------------

def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))

def update_elo(a, b, sa, sb, date, writer):
    # Current values
    ra, rb = elos[a], elos[b]

    # Dynamic K-factors
    k_a = get_k_factor(stats[a]["matches"])
    k_b = get_k_factor(stats[b]["matches"])

    ea, eb = expected(ra, rb), expected(rb, ra)

    total = sa + sb
    if total == 0:
        return

    # actual scores
    s_a, s_b = sa / total, sb / total

    # new ratings
    new_a = ra + k_a * (s_a - ea)
    new_b = rb + k_b * (s_b - eb)

    elos[a], elos[b] = new_a, new_b

    # Write history
    writer.writerow([date, a, b, sa, sb, round(ra,2), round(rb,2),
                     round(new_a,2), round(new_b,2), k_a, k_b])

    # Stats update
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

def calculate_winrates():
    for bey, s in stats.items():
        if s["matches"] > 0:
            s["winrate"] = s["wins"] / s["matches"]
        else:
            s["winrate"] = 0

# ---------- MAIN RUN ----------
with open(INPUT_FILE, newline="", encoding="utf-8") as f_in, \
     open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f_hist:

    reader = csv.DictReader(f_in)
    writer = csv.writer(f_hist)
    writer.writerow([
        "Date","BeyA","BeyB","ScoreA","ScoreB",
        "PreA","PreB","PostA","PostB","K_A","K_B"
    ])

    matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))
    for m in matches:
        update_elo(
            m["BeyA"], m["BeyB"],
            int(m["ScoreA"]), int(m["ScoreB"]),
            m["Date"], writer
        )
    calculate_winrates()

# ---------- Write leaderboard.csv ----------
with open(LEADERBOARD_FILE, "w", newline="", encoding="utf-8") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(["Platz","Name","ELO","Spiele","Siege","Niederlagen",
                     "Winrate","Gewonnene Punkte","Verlorene Punkte","Differenz"])

    sorted_beys = sorted(elos.items(), key=lambda x: x[1], reverse=True)

    for i, (bey, elo) in enumerate(sorted_beys, start=1):
        s = stats[bey]
        diff = s["for"] - s["against"]
        writer.writerow([
            i, bey, round(elo),
            s["matches"], s["wins"], s["losses"],
            f"{round(s['winrate'] * 100, 1)}%",
            s["for"], s["against"], diff
        ])

print(f"{GREEN}Leaderboard und Historie aktualisiert.{RESET}")

# ---------- Build ELO time series (elo_timeseries.csv) ----------
print(f"{CYAN}Erstelle gestackte ELO-History pro Bey...{RESET}")

df = pd.read_csv(HISTORY_FILE, parse_dates=["Date"])
df = df.reset_index(drop=True)
df["match_id"] = df.index + 1

df_a = pd.DataFrame({
    "Date": df["Date"],
    "Bey": df["BeyA"],
    "ELO": pd.to_numeric(df["PostA"]),
    "match_id": df["match_id"]
})

df_b = pd.DataFrame({
    "Date": df["Date"],
    "Bey": df["BeyB"],
    "ELO": pd.to_numeric(df["PostB"]),
    "match_id": df["match_id"]
})

stacked = pd.concat([df_a, df_b], ignore_index=True)
stacked = stacked.sort_values(["Bey","match_id"]).reset_index(drop=True)
stacked["MatchIndex"] = stacked.groupby("Bey").cumcount()

# Add initial ELO entries (MatchIndex 0)
initial = []
for bey in stacked["Bey"].unique():
    earliest = stacked[stacked["Bey"] == bey]["Date"].min()
    initial.append({
        "Date": earliest,
        "Bey": bey,
        "ELO": START_ELO,
        "match_id": 0,
        "MatchIndex": 0
    })

stacked = pd.concat([pd.DataFrame(initial), stacked], ignore_index=True)
stacked = stacked.sort_values(["Bey","MatchIndex"]).reset_index(drop=True)
stacked.to_csv(TIMESERIES_FILE, index=False, encoding="utf-8")

print(f"{GREEN}Erzeugt: {TIMESERIES_FILE}{RESET}")
