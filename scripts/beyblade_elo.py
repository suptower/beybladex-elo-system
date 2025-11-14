# beyblade_elo.py  — Version 2.4
# Supports official + private ladders with dynamic K-factors

import csv, datetime, argparse
from collections import defaultdict
import os
import pandas as pd

# Colors for Windows
os.system("")

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

START_ELO = 1000
K_LEARNING = 40
K_INTERMEDIATE = 24
K_EXPERIENCED = 12

# ------------ K-factor rules ------------
def dynamic_k(matches):
    if matches < 6:
        return K_LEARNING
    elif matches < 15:
        return K_INTERMEDIATE
    return K_EXPERIENCED

# ------------ Elo expected score ------------
def expected(a, b):
    return 1 / (1 + 10 ** ((b - a) / 400))


# ------------- Elo update for ONE MATCH -------------
def update_elo(a, b, sa, sb, date, writer, elos, stats):
    ra, rb = elos[a], elos[b]

    ea, eb = expected(ra, rb), expected(rb, ra)

    # Determine K for each player
    Ka = dynamic_k(stats[a]["matches"])
    Kb = dynamic_k(stats[b]["matches"])

    total = sa + sb
    if total == 0:
        return

    s_a, s_b = sa / total, sb / total

    new_a = ra + Ka * (s_a - ea)
    new_b = rb + Kb * (s_b - eb)

    elos[a], elos[b] = new_a, new_b

    # Save history
    writer.writerow([date, a, b, sa, sb, round(ra, 2), round(rb, 2), round(new_a, 2), round(new_b, 2)])

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


# ------------- Calculate winrates -------------
def calculate_winrates(stats):
    for bey, s in stats.items():
        if s["matches"] > 0:
            s["winrate"] = s["wins"] / s["matches"]
        else:
            s["winrate"] = 0.0


# ----------------- ELO PIPELINE -------------------
def run_elo_pipeline(config):
    mode = config["mode"]
    input_file = config["input_file"]
    leaderboard_file = config["leaderboard"]
    history_file = config["history"]
    timeseries_file = config["timeseries"]
    start_elos = config["start_elos"]

    print(f"{BOLD}{CYAN}Running ELO Pipeline — Mode: {mode}{RESET}")
    print(f"{YELLOW}Reading matches from {input_file}...{RESET}")

    # Initialize ELO + stats
    elos = defaultdict(lambda: START_ELO)
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "for": 0, "against": 0, "matches": 0})

    # Load start ratings for private ladder
    if start_elos is not None:
        print(f"{CYAN}Loading starting ELOs from official leaderboard...{RESET}")
        for bey, elo in start_elos.items():
            elos[bey] = elo

    # --- Run matches ---
    with open(input_file, newline="", encoding="utf-8") as f_in, \
         open(history_file, "w", newline="", encoding="utf-8") as f_hist:

        reader = csv.DictReader(f_in)
        writer = csv.writer(f_hist)
        writer.writerow(["Date", "BeyA", "BeyB", "ScoreA", "ScoreB",
                         "PreA", "PreB", "PostA", "PostB"])

        matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))

        for m in matches:
            update_elo(
                m["BeyA"],
                m["BeyB"],
                int(m["ScoreA"]),
                int(m["ScoreB"]),
                m["Date"],
                writer,
                elos,
                stats
            )

    # Winrates
    calculate_winrates(stats)

    # --- Save leaderboard ---
    print(f"{CYAN}Writing leaderboard to {leaderboard_file}...{RESET}")

    with open(leaderboard_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Platz", "Name", "ELO", "Spiele", "Siege",
                         "Niederlagen", "Winrate", "Gewonnene Punkte",
                         "Verlorene Punkte", "Differenz"])

        sorted_beys = sorted(elos.items(), key=lambda x: x[1], reverse=True)

        for i, (bey, elo) in enumerate(sorted_beys, start=1):
            s = stats[bey]
            diff = s["for"] - s["against"]
            writer.writerow([
                i, bey, round(elo), s["matches"], s["wins"], s["losses"],
                f"{round(s['winrate'] * 100, 1)}%",
                s["for"], s["against"], diff
            ])

    # --- Time series ---
    print(f"{CYAN}Generating timeseries file...{RESET}")

    df = pd.read_csv(history_file, parse_dates=["Date"])
    df = df.reset_index(drop=True)
    df["match_id"] = df.index + 1

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
    stacked = stacked.sort_values(["Bey", "match_id"]).reset_index(drop=True)
    stacked["MatchIndex"] = stacked.groupby("Bey").cumcount() + 1

    # Add initial line
    initial_entries = []
    for bey in stacked["Bey"].unique():
        earliest_date = stacked[stacked["Bey"] == bey]["Date"].min()
        initial_entries.append({
            "Date": earliest_date,
            "Bey": bey,
            "ELO": start_elos.get(bey, START_ELO) if start_elos else START_ELO,
            "match_id": 0,
            "MatchIndex": 0
        })

    initial_df = pd.DataFrame(initial_entries)
    stacked = pd.concat([initial_df, stacked], ignore_index=True)
    stacked = stacked.sort_values(["Bey", "MatchIndex"])

    stacked.to_csv(timeseries_file, index=False, encoding="utf-8")

    print(f"{GREEN}Finished {mode} ladder — {leaderboard_file}{RESET}")


# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()

    mode = args.mode

    if mode == "official":
        # Standard mode
        config = {
            "mode": "official",
            "input_file": "./csv/matches.csv",
            "leaderboard": "./csv/leaderboard.csv",
            "history": "./csv/elo_history.csv",
            "timeseries": "./csv/elo_timeseries.csv",
            "start_elos": None
        }

    else:  # private mode
        # Load official leaderboard as base
        df = pd.read_csv("./csv/leaderboard.csv")
        start_elos = dict(zip(df["Name"], df["ELO"]))

        config = {
            "mode": "private",
            "input_file": "./csv/private_matches.csv",
            "leaderboard": "./csv/private_leaderboard.csv",
            "history": "./csv/private_elo_history.csv",
            "timeseries": "./csv/private_elo_timeseries.csv",
            "start_elos": start_elos
        }

    run_elo_pipeline(config)
