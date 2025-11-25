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

# --- Power Index Weights ---
POWER_INDEX_WEIGHTS = {
    "elo": 0.40,           # Base skill rating
    "winrate": 0.25,       # Consistent performance
    "trend": 0.15,         # Current form/momentum
    "activity": 0.10,      # Match engagement
    "consistency": 0.10    # Reliability (inverse of volatility)
}


def calculate_power_index(elo, winrate, trend, matches, volatility,
                          max_elo, min_elo, max_trend, min_trend,
                          max_matches, max_volatility):
    """
    Calculate the Power Index (Meta Score) for a Beyblade.

    The Power Index is a composite score (0-100) that combines multiple factors:
    - ELO rating (40%): Base skill level
    - Winrate (25%): Consistent performance percentage
    - ELO Trend (15%): Recent form/momentum
    - Activity (10%): Match engagement level
    - Consistency (10%): Performance reliability (inverse of volatility)

    Args:
        elo: Current ELO rating
        winrate: Win rate as decimal (0.0-1.0)
        trend: ELO trend (sum of all ELO changes)
        matches: Number of matches played
        volatility: Standard deviation of ELO changes
        max_elo: Maximum ELO in the dataset (for normalization)
        min_elo: Minimum ELO in the dataset (for normalization)
        max_trend: Maximum trend value in the dataset
        min_trend: Minimum trend value in the dataset
        max_matches: Maximum matches played by any Bey
        max_volatility: Maximum volatility in the dataset

    Returns:
        float: Power Index score from 0 to 100
    """
    # Normalize ELO (0-1 scale)
    elo_range = max_elo - min_elo if max_elo != min_elo else 1
    normalized_elo = (elo - min_elo) / elo_range

    # Winrate is already 0-1
    normalized_winrate = winrate

    # Normalize trend (handle negative values with a shift to 0-1 scale)
    trend_range = max_trend - min_trend if max_trend != min_trend else 1
    normalized_trend = (trend - min_trend) / trend_range

    # Normalize activity (matches played)
    normalized_activity = matches / max_matches if max_matches > 0 else 0

    # Normalize consistency (inverse of volatility - lower volatility = better)
    # Use 1 - (vol / max_vol) so lower volatility gives higher score
    normalized_consistency = 1 - (volatility / max_volatility) if max_volatility > 0 else 1

    # Calculate weighted Power Index
    power_index = (
        POWER_INDEX_WEIGHTS["elo"] * normalized_elo
        + POWER_INDEX_WEIGHTS["winrate"] * normalized_winrate
        + POWER_INDEX_WEIGHTS["trend"] * normalized_trend
        + POWER_INDEX_WEIGHTS["activity"] * normalized_activity
        + POWER_INDEX_WEIGHTS["consistency"] * normalized_consistency
    )

    # Scale to 0-100
    return round(power_index * 100, 1)


# --- Datenstrukturen ---
stats = defaultdict(lambda: {
    "rank": 0,
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

# --- Advanced Stats berechnen (Phase 1: Compute intermediate values) ---
intermediate_data = []
sorted_stats = sorted(stats.items(), key=lambda x: -x[1]["last_elo"])
for bey, s in sorted_stats:
    match_count = s["matches"]
    wins = s["wins"]
    losses = s["losses"]
    points_for = s["points_for"]
    points_against = s["points_against"]
    delta_sum = sum(s["elo_deltas"])
    last_elo = s["last_elo"]
    # Volatilität
    volatility = statistics.stdev(s["elo_deltas"]) if len(s["elo_deltas"]) > 1 else 0.0
    # Avg ΔELO
    avg_delta = sum(abs(d) for d in s["elo_deltas"]) / match_count if match_count > 0 else 0.0
    # Max/Min ΔELO
    max_delta = max(s["elo_deltas"]) if s["elo_deltas"] else 0.0
    min_delta = min(s["elo_deltas"]) if s["elo_deltas"] else 0.0
    # Winrate
    winrate = wins / match_count if match_count > 0 else 0.0
    # Average Punktedifferenz
    avg_point_diff = (points_for - points_against) / match_count if match_count > 0 else 0.0
    # ELO-Trend
    elo_trend = delta_sum

    intermediate_data.append({
        "bey": bey,
        "elo": last_elo,
        "matches": match_count,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "points_for": points_for,
        "points_against": points_against,
        "avg_point_diff": avg_point_diff,
        "volatility": volatility,
        "avg_delta": avg_delta,
        "max_delta": max_delta,
        "min_delta": min_delta,
        "upset_wins": s["upset_wins"],
        "upset_losses": s["upset_losses"],
        "elo_trend": elo_trend
    })

# --- Phase 2: Calculate normalization parameters for Power Index ---
all_elos = [d["elo"] for d in intermediate_data]
all_trends = [d["elo_trend"] for d in intermediate_data]
all_matches = [d["matches"] for d in intermediate_data]
all_volatilities = [d["volatility"] for d in intermediate_data]

max_elo = max(all_elos) if all_elos else 1000
min_elo = min(all_elos) if all_elos else 1000
max_trend = max(all_trends) if all_trends else 0
min_trend = min(all_trends) if all_trends else 0
max_matches = max(all_matches) if all_matches else 1
max_volatility = max(all_volatilities) if all_volatilities else 1

# --- Phase 3: Calculate Power Index and build final data ---
advanced_data = []
for d in intermediate_data:
    power_index = calculate_power_index(
        elo=d["elo"],
        winrate=d["winrate"],
        trend=d["elo_trend"],
        matches=d["matches"],
        volatility=d["volatility"],
        max_elo=max_elo,
        min_elo=min_elo,
        max_trend=max_trend,
        min_trend=min_trend,
        max_matches=max_matches,
        max_volatility=max_volatility
    )

    advanced_data.append({
        "bey": d["bey"],
        "elo": round(d["elo"]),
        "matches": d["matches"],
        "wins": d["wins"],
        "losses": d["losses"],
        "winrate": f"{d['winrate'] * 100:.1f}%",
        "points_for": d["points_for"],
        "points_against": d["points_against"],
        "avg_point_diff": round(d["avg_point_diff"], 2),
        "volatility": round(d["volatility"], 2),
        "avg_delta": round(d["avg_delta"], 2),
        "max_delta": round(d["max_delta"], 2),
        "min_delta": round(d["min_delta"], 2),
        "upset_wins": d["upset_wins"],
        "upset_losses": d["upset_losses"],
        "elo_trend": round(d["elo_trend"], 2),
        "power_index": power_index
    })

# --- Phase 4: Sort by ELO and assign ranks ---
advanced_data_sorted = sorted(advanced_data, key=lambda x: -x["elo"])
for rank, d in enumerate(advanced_data_sorted, start=1):
    d["rank"] = rank

# --- CSV speichern (nach Power Index sortiert) ---
header = [
    "Platz", "Bey", "ELO", "PowerIndex", "Matches", "Wins", "Losses", "Winrate",
    "PointsFor", "PointsAgainst", "AvgPointDiff", "Volatility",
    "AvgΔELO", "MaxΔELO", "MinΔELO", "UpsetWins", "UpsetLosses", "ELOTrend"
]

with open(ADVANCED_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for d in advanced_data_sorted:
        writer.writerow([
            d["rank"], d["bey"], d["elo"], d["power_index"], d["matches"],
            d["wins"], d["losses"], d["winrate"], d["points_for"],
            d["points_against"], d["avg_point_diff"], d["volatility"],
            d["avg_delta"], d["max_delta"], d["min_delta"],
            d["upset_wins"], d["upset_losses"], d["elo_trend"]
        ])

# copy to docs folder
with open(ADVANCED_FILE, "r", encoding="utf-8") as src, open("./docs/data/advanced_leaderboard.csv", "w", encoding="utf-8") as dst:
    dst.write(src.read())

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
# | **PowerIndex**    | Composite score (0-100) combining ELO (40%), Winrate (25%), Trend (15%), Activity (10%), and Consistency (10%).                     |
