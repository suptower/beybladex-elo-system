# advanced_stats.py
import csv
import statistics
from collections import defaultdict
import os
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


HISTORY_FILE = "./csv/elo_history.csv"
ADVANCED_FILE = "./csv/advanced_leaderboard.csv"

# --- Datenstrukturen ---
stats = defaultdict(lambda: {
    "matches": 0,
    "wins": 0,
    "losses": 0,
    "points_for": 0,
    "points_against": 0,
    "elo_deltas": [],
    "last_elo": 1000,  # letzter PostELO
    "upset_wins": 0,
    "upset_losses": 0
})

# --- CSV einlesen und Stats sammeln ---
with open(HISTORY_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    matches = sorted(reader, key=lambda m: m["Date"])
    for row in matches:
        a, b = row["BeyA"], row["BeyB"]
        pre_a, pre_b = float(row["PreA"]), float(row["PreB"])
        post_a, post_b = float(row["PostA"]), float(row["PostB"])
        score_a, score_b = int(row["ScoreA"]), int(row["ScoreB"])
        total = score_a + score_b
        if total == 0:
            continue

        # Statistiken updaten
        for bey, pre, post, score_self, score_opp, opponent_pre in [
            (a, pre_a, post_a, score_a, score_b, pre_b),
            (b, pre_b, post_b, score_b, score_a, pre_a)
        ]:
            s = stats[bey]
            s["matches"] += 1
            s["points_for"] += score_self
            s["points_against"] += score_opp
            delta = post - pre
            s["elo_deltas"].append(delta)
            s["last_elo"] = post

            # Win / Loss
            if score_self > score_opp:
                s["wins"] += 1
            else:
                s["losses"] += 1

            # Upset-Win / Upset-Loss
            if score_self > score_opp and pre < opponent_pre:
                s["upset_wins"] += 1
            if score_self < score_opp and pre > opponent_pre:
                s["upset_losses"] += 1

# --- Advanced Stats berechnen ---
advanced_data = []
for bey, s in stats.items():
    matches = s["matches"]
    wins = s["wins"]
    losses = s["losses"]
    points_for = s["points_for"]
    points_against = s["points_against"]
    delta_sum = sum(s["elo_deltas"])
    last_elo = round(s["last_elo"])
    # Volatilität
    volatility = round(statistics.stdev(s["elo_deltas"]), 2) if len(s["elo_deltas"]) > 1 else 0.0
    # Avg ΔELO
    avg_delta = round(sum(abs(d) for d in s["elo_deltas"]) / matches, 2) if matches > 0 else 0.0
    # Max/Min ΔELO
    max_delta = round(max(s["elo_deltas"]), 2) if s["elo_deltas"] else 0.0
    min_delta = round(min(s["elo_deltas"]), 2) if s["elo_deltas"] else 0.0
    # Winrate
    winrate = round(wins / matches, 3) if matches > 0 else 0.0
    # Average Punktedifferenz
    avg_point_diff = round((points_for - points_against) / matches, 2) if matches > 0 else 0.0
    # ELO-Trend
    elo_trend = round(delta_sum, 2)

    advanced_data.append([
        bey, last_elo, matches, wins, losses, f"{winrate*100:.1f}%",
        points_for, points_against, avg_point_diff, volatility, avg_delta, max_delta, min_delta,
        s["upset_wins"], s["upset_losses"], elo_trend
    ])

# --- CSV speichern (nach ELO sortiert) ---
header = [
    "Bey", "ELO", "Matches", "Wins", "Losses", "Winrate",
    "PointsFor", "PointsAgainst", "AvgPointDiff", "Volatility",
    "AvgΔELO", "MaxΔELO", "MinΔELO", "UpsetWins", "UpsetLosses", "ELOTrend"
]

with open(ADVANCED_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for row in sorted(advanced_data, key=lambda x: -x[1]):  # sortiert nach ELO absteigend
        writer.writerow(row)

print(f"{GREEN} Advanced Leaderboard erstellt: {ADVANCED_FILE}")

# | Spalte            | Beschreibung                                                                                                                        |
# | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
# | **Bey**           | Name des Beyblades.                                                                                                                 |
# | **ELO**           | Aktuelle ELO nach allen bisherigen Matches (letzter PostELO-Wert). Zeigt die Gesamtstärke des Bey im Turnierverlauf.                |
# | **Matches**       | Anzahl der gespielten Matches.                                                                                                      |
# | **Wins**          | Anzahl der gewonnenen Matches.                                                                                                      |
# | **Losses**        | Anzahl der verlorenen Matches.                                                                                                      |
# | **Winrate**       | Prozentsatz der gewonnenen Matches (`Wins / Matches`). Zeigt die allgemeine Erfolgsquote.                                           |
# | **PointsFor**     | Summe aller Punkte, die der Bey über alle Matches erzielt hat.                                                                      |
# | **PointsAgainst** | Summe aller Punkte, die der Bey gegen sich kassiert hat.                                                                            |
# | **AvgPointDiff**  | Durchschnittliche Punktedifferenz pro Match (`PointsFor − PointsAgainst / Matches`). Zeigt, wie klar ein Bey gewinnt oder verliert. |
# | **Volatility**    | Standardabweichung der ELO-Änderungen pro Match. Misst, wie stark die Leistung von Match zu Match schwankt.                         |
# | **AvgΔELO**       | Durchschnittlicher Betrag der ELO-Änderung pro Match. Zeigt, wie stark ein Match typischerweise die Bewertung verändert.            |
# | **MaxΔELO**       | Größte einzelne ELO-Zunahme in einem Match. Zeigt den stärksten Match-Erfolg.                                                       |
# | **MinΔELO**       | Größte einzelne ELO-Abnahme in einem Match. Zeigt die größte Niederlage.                                                            |
# | **UpsetWins**     | Anzahl der Siege gegen Gegner, die vor dem Match eine höhere ELO hatten. Zeigt „Überraschungssiege“.                                |
# | **UpsetLosses**   | Anzahl der Niederlagen gegen Gegner, die vor dem Match eine niedrigere ELO hatten. Zeigt unerwartete Niederlagen.                   |
# | **ELOTrend**      | Gesamte ELO-Änderung über alle Matches (`sum(PostELO-PreELO)`). Zeigt, ob der Bey insgesamt stärker oder schwächer geworden ist.    |
