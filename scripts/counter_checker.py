import csv
from collections import defaultdict

matches_file = "csv/matches.csv"
output_file = "csv/bey_counters.csv"

results = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "score_for": 0, "score_against": 0}))
totals = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})

with open(matches_file, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        beyA = row["BeyA"]
        beyB = row["BeyB"]
        scoreA = int(row["ScoreA"])
        scoreB = int(row["ScoreB"])

        if scoreA == scoreB:
            continue

        if scoreA > scoreB:
            winner, loser = beyA, beyB
            score_winner, score_loser = scoreA, scoreB
        else:
            winner, loser = beyB, beyA
            score_winner, score_loser = scoreB, scoreA

        # Stats pro Gegner
        results[winner][loser]["wins"] += 1
        results[winner][loser]["score_for"] += score_winner
        results[winner][loser]["score_against"] += score_loser

        results[loser][winner]["losses"] += 1
        results[loser][winner]["score_for"] += score_loser
        results[loser][winner]["score_against"] += score_winner

        # Gesamtstatistik
        totals[winner]["wins"] += 1
        totals[loser]["losses"] += 1
        totals[winner]["games"] += 1
        totals[loser]["games"] += 1

# CSV schreiben
with open(output_file, "w", newline="") as f:
    fieldnames = [
        "Bey", "Top_Counter", "Games_vs_Counter", "Wins_vs_Counter", "Losses_vs_Counter",
        "Score_for_vs_Counter", "Score_against_vs_Counter", "Winrate_vs_Counter",
        "Total_Games", "Total_Wins", "Total_Losses", "Overall_Winrate"
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for bey, opponents in results.items():
        # Nur Gegner mit mindestens einer Niederlage
        losing_opponents = {o: s for o, s in opponents.items() if s["losses"] > 0}
        if not losing_opponents:
            continue

        # Top Counter nach Anzahl Niederlagen
        top_opponent, stats = max(losing_opponents.items(), key=lambda x: x[1]["losses"])

        games_vs = stats["wins"] + stats["losses"]
        winrate_vs = stats["wins"] / games_vs if games_vs > 0 else 0
        total_games = totals[bey]["games"]
        overall_winrate = totals[bey]["wins"] / total_games if total_games > 0 else 0

        writer.writerow({
            "Bey": bey,
            "Top_Counter": top_opponent,
            "Games_vs_Counter": games_vs,
            "Wins_vs_Counter": stats["wins"],
            "Losses_vs_Counter": stats["losses"],
            "Score_for_vs_Counter": stats["score_for"],
            "Score_against_vs_Counter": stats["score_against"],
            "Winrate_vs_Counter": round(winrate_vs, 2),
            "Total_Games": total_games,
            "Total_Wins": totals[bey]["wins"],
            "Total_Losses": totals[bey]["losses"],
            "Overall_Winrate": round(overall_winrate, 2)
        })

print(f"CSV mit stärksten Countern erstellt: {output_file}")
