# beyblade_elo.py  — Version 2.5
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
def update_elo(a, b, sa, sb, date, elos, stats, writer=None):
    ra, rb = elos[a], elos[b]
    ea, eb = expected(ra, rb), expected(rb, ra)

    Ka = dynamic_k(stats[a]["matches"])
    Kb = dynamic_k(stats[b]["matches"])

    total = sa + sb
    if total == 0:
        return

    s_a, s_b = sa / total, sb / total
    new_a = ra + Ka * (s_a - ea)
    new_b = rb + Kb * (s_b - eb)
    elos[a], elos[b] = new_a, new_b

    # Nur schreiben, wenn writer vorhanden
    if writer is not None:
        writer.writerow([date, a, b, sa, sb, round(ra,2), round(rb,2), round(new_a,2), round(new_b,2)])

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
        s["winrate"] = s["wins"]/s["matches"] if s["matches"] > 0 else 0.0

# ----------------- ELO PIPELINE -------------------
def run_elo_pipeline(config):
    mode = config["mode"]
    input_file = config["input_file"]
    leaderboard_file = config["leaderboard"]
    history_file = config["history"]
    timeseries_file = config["timeseries"]
    position_file = config["positions"]
    start_elos = config["start_elos"]

    print(f"{BOLD}{CYAN}Running ELO Pipeline — Mode: {mode}{RESET}")
    print(f"{YELLOW}Reading matches from {input_file}...{RESET}")

    # Initialize ELO + stats
    elos = defaultdict(lambda: START_ELO)
    stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0,"winrate":0.0})

    # Load start ratings for private ladder
    if start_elos is not None:
        print(f"{CYAN}Loading starting ELOs from official leaderboard...{RESET}")
        for bey, elo in start_elos.items():
            elos[bey] = elo

    # --- Full history CSV ---
    with open(input_file,newline="",encoding="utf-8") as f_in, \
         open(history_file,"w",newline="",encoding="utf-8") as f_hist:

        reader = csv.DictReader(f_in)
        writer = csv.writer(f_hist)
        writer.writerow(["Date","BeyA","BeyB","ScoreA","ScoreB","PreA","PreB","PostA","PostB"])

        matches = sorted(reader, key=lambda m: datetime.date.fromisoformat(m["Date"]))
        for m in matches:
            update_elo(
                m["BeyA"], m["BeyB"],
                int(m["ScoreA"]), int(m["ScoreB"]),
                m["Date"], elos, stats, writer
            )

        calculate_winrates(stats)

    # --- Turnier-basierte Leaderboards mit Positionsdelta ---
    print(f"{CYAN}Computing tournament deltas and saving per-turnier CSVs...{RESET}")

    matches_df = pd.read_csv(input_file, parse_dates=["Date"])
    tournament_dates = matches_df["Date"].drop_duplicates().sort_values().tolist()

    # Ausgangswerte für Turnier 1
    prev_positions = {}
    prev_elos = start_elos.copy() if start_elos else {}
    prev_stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0,"winrate":0.0})

    for t_idx, t_date in enumerate(tournament_dates, start=1):
        tour_matches = matches_df[matches_df["Date"]==t_date].sort_values(["Date"])

        # Stats und Elos für dieses Turnier initialisieren mit Werten vom vorherigen Turnier
        temp_elos = defaultdict(lambda: START_ELO)
        temp_stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0,"winrate":0.0})

        # Übernehmen der ELOs & Stats vom vorherigen Turnier
        for bey, elo in prev_elos.items():
            temp_elos[bey] = elo
        for bey, s in prev_stats.items():
            temp_stats[bey] = s.copy()  # deepcopy, damit Änderungen temp_stats nicht prev_stats beeinflussen

        # Matches für dieses Turnier durchlaufen
        for _, m in tour_matches.iterrows():
            update_elo(
                m["BeyA"], m["BeyB"],
                int(m["ScoreA"]), int(m["ScoreB"]),
                m["Date"], temp_elos, temp_stats
            )

        calculate_winrates(temp_stats)

        # Sortiere nach ELO absteigend und erstelle Leaderboard
        sorted_beys = sorted(temp_elos.items(), key=lambda x: x[1], reverse=True)
        tour_rows = []

        for pos, (bey, elo) in enumerate(sorted_beys, start=1):
            s = temp_stats[bey]
            delta = prev_positions.get(bey,pos) - pos if prev_positions else 0
            prev_positions[bey] = pos
            prev_elo = prev_elos.get(bey, START_ELO) if prev_elos else START_ELO
            elo_delta = round(elo - prev_elo)

            if elo_delta > 0:
                elo_delta_str = f"+{elo_delta}"
            elif elo_delta < 0:
                elo_delta_str = f"{elo_delta}"  # Minus schon drin
            else:
                elo_delta_str = "0"


            if delta > 0:
                delta_str = f"▲ {delta}"
            elif delta < 0:
                delta_str = f"▼ {abs(delta)}"
            else:
                delta_str = "→ 0"


            tour_rows.append({
                "Platz": pos,
                "Name": bey,
                "ELO": round(elo),
                "Spiele": s["matches"],
                "Siege": s["wins"],
                "Niederlagen": s["losses"],
                # convert to percentage string with 1 decimal
                "Winrate": f"{round(s['winrate']*100,1)}%",
                "Gewonnene Punkte": s["for"],
                "Verlorene Punkte": s["against"],
                "Differenz": s["for"]-s["against"],
                "Positionsdelta": delta_str,
                "ELOdelta": elo_delta_str
            })

        out_file = f"./csv/leaderboards/leaderboard_{t_idx}.csv"
        pd.DataFrame(tour_rows).to_csv(out_file,index=False)

        # Update für nächstes Turnier
        prev_elos = temp_elos.copy()
        prev_stats = temp_stats.copy()


    # --- Aktuelles Turnier zusätzlich als leaderboard.csv ---
    tour_rows_df = pd.DataFrame(tour_rows)
    tour_rows_df.to_csv(leaderboard_file,index=False)
    print(f"{GREEN}Aktuelles Leaderboard geschrieben: {leaderboard_file}{RESET}")

    # --- Time series ---
    df_hist = pd.read_csv(history_file,parse_dates=["Date"]).reset_index(drop=True)
    df_hist["match_id"] = df_hist.index+1
    df_a = pd.DataFrame({"Date":df_hist["Date"],"Bey":df_hist["BeyA"],"ELO":pd.to_numeric(df_hist["PostA"],errors="coerce"),"match_id":df_hist["match_id"]})
    df_b = pd.DataFrame({"Date":df_hist["Date"],"Bey":df_hist["BeyB"],"ELO":pd.to_numeric(df_hist["PostB"],errors="coerce"),"match_id":df_hist["match_id"]})
    stacked = pd.concat([df_a, df_b],ignore_index=True).sort_values(["Bey","match_id"]).reset_index(drop=True)
    stacked["MatchIndex"] = stacked.groupby("Bey").cumcount()+1

    initial_entries = []
    for bey in stacked["Bey"].unique():
        earliest_date = stacked[stacked["Bey"]==bey]["Date"].min()
        initial_entries.append({"Date":earliest_date,"Bey":bey,"ELO":start_elos.get(bey,START_ELO) if start_elos else START_ELO,"match_id":0,"MatchIndex":0})

    stacked = pd.concat([pd.DataFrame(initial_entries),stacked],ignore_index=True)
    stacked = stacked.sort_values(["Bey","MatchIndex"])
    stacked.to_csv(timeseries_file,index=False,encoding="utf-8")

    print(f"{GREEN}Fertig — Zeitreihen gespeichert: {timeseries_file}{RESET}")

    # --- Position Time Series ---
    print(f"{CYAN}Generating position time series...{RESET}")
    
    # Read the history to track positions after each match
    df_hist = pd.read_csv(history_file, parse_dates=["Date"])
    
    # Initialize tracking structures
    current_elos = defaultdict(lambda: START_ELO)
    current_stats = defaultdict(lambda: {"wins":0,"losses":0,"for":0,"against":0,"matches":0,"winrate":0.0})
    
    # Load start ratings for private ladder
    if start_elos is not None:
        for bey, elo in start_elos.items():
            current_elos[bey] = elo
    
    # Calculate initial positions (before any matches)
    sorted_beys = sorted(current_elos.items(), key=lambda x: x[1], reverse=True)
    previous_positions = {bey: pos for pos, (bey, elo) in enumerate(sorted_beys, start=1)}
    
    position_rows = []
    match_counters = defaultdict(int)
    
    # Process each match in chronological order
    for match_idx, match in df_hist.iterrows():
        date = match["Date"]
        bey_a = match["BeyA"]
        bey_b = match["BeyB"]
        
        # Update ELOs from match
        current_elos[bey_a] = match["PostA"]
        current_elos[bey_b] = match["PostB"]
        
        # Update stats
        score_a = match["ScoreA"]
        score_b = match["ScoreB"]
        
        for bey, score_self, score_opp in [(bey_a, score_a, score_b), (bey_b, score_b, score_a)]:
            current_stats[bey]["matches"] += 1
            current_stats[bey]["for"] += score_self
            current_stats[bey]["against"] += score_opp
            if score_self > score_opp:
                current_stats[bey]["wins"] += 1
            else:
                current_stats[bey]["losses"] += 1
            if current_stats[bey]["matches"] > 0:
                current_stats[bey]["winrate"] = current_stats[bey]["wins"] / current_stats[bey]["matches"]
        
        # Increment match counter for participating beys
        match_counters[bey_a] += 1
        match_counters[bey_b] += 1
        
        # Calculate current leaderboard positions for ALL beys
        sorted_beys = sorted(current_elos.items(), key=lambda x: x[1], reverse=True)
        current_positions = {bey: pos for pos, (bey, elo) in enumerate(sorted_beys, start=1)}
        
        # Event number is match index + 1 (1-based)
        event_num = match_idx + 1
        
        # Only record position changes for the beys that played in this match
        # This prevents recording passive position changes that cause backward lines
        for bey in [bey_a, bey_b]:
            old_pos = previous_positions.get(bey)
            new_pos = current_positions[bey]
            
            # Only add entry if position changed
            if old_pos != new_pos:
                s = current_stats[bey]
                elo = current_elos[bey]
                position_rows.append({
                    "Event": event_num,
                    "MatchIndex": match_counters[bey],
                    "Date": date,
                    "Bey": bey,
                    "ELO": round(elo),
                    "Position": new_pos,
                    "Spiele": s["matches"],
                    "Siege": s["wins"],
                    "Niederlagen": s["losses"],
                    "Winrate": s["winrate"]
                })
        
        # Update previous positions for next iteration
        previous_positions = current_positions.copy()
    
    # Save position timeseries
    position_df = pd.DataFrame(position_rows)
    position_df.to_csv(position_file, index=False, encoding="utf-8")
    print(f"{GREEN}Position time series gespeichert: {position_file}{RESET}")

# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official","private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()

    mode = args.mode

    if mode=="official":
        config = {
            "mode":"official",
            "input_file":"./csv/matches.csv",
            "leaderboard":"./csv/leaderboard.csv",
            "history":"./csv/elo_history.csv",
            "timeseries":"./csv/elo_timeseries.csv",
            "positions":"./csv/position_timeseries.csv",
            "start_elos":None
        }
    else:
        df = pd.read_csv("./csv/leaderboard.csv")
        start_elos = dict(zip(df["Name"],df["ELO"]))
        config = {
            "mode":"private",
            "input_file":"./csv/private_matches.csv",
            "leaderboard":"./csv/private_leaderboard.csv",
            "history":"./csv/private_elo_history.csv",
            "timeseries":"./csv/private_elo_timeseries.csv",
            "positions":"./csv/private_position_timeseries.csv",
            "start_elos":start_elos
        }

    run_elo_pipeline(config)
