# upset_analysis.py
"""
Upset Analysis Module for Beyblade ELO Rating System

This module analyzes match history to identify upsets (surprise wins) where a lower-rated
Beyblade defeats a higher-rated opponent. It calculates various metrics to identify
"Giant Killers" - Beyblades that consistently perform well against stronger opponents.

Key Metrics:
- Upset Win: A match won by the Beyblade that had lower pre-match ELO
- Upset Loss: A match lost by the Beyblade that had higher pre-match ELO
- Giant Killer Score: Composite score measuring a Bey's ability to defeat stronger opponents
- Upset Magnitude: The ELO difference between winner and loser when an upset occurs

Output Files:
- upset_analysis.csv: Per-bey upset statistics and Giant Killer scores
- upset_matches.csv: Individual upset matches with details
"""
import csv
import os
from collections import defaultdict

os.system("")

# Colors for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

HISTORY_FILE = "./data/elo_history.csv"
UPSET_ANALYSIS_FILE = "./data/upset_analysis.csv"
UPSET_MATCHES_FILE = "./data/upset_matches.csv"

# --- Giant Killer Score Weights ---
GIANT_KILLER_WEIGHTS = {
    "upset_winrate": 0.35,       # Percentage of wins that are upsets
    "upset_frequency": 0.25,     # How often they cause upsets
    "avg_magnitude": 0.25,       # Average ELO gap overcome in upsets
    "total_upsets": 0.15         # Raw count of upset wins
}


def calculate_giant_killer_score(
    upset_wins, total_wins, total_matches, avg_magnitude,
    max_upset_wins, max_magnitude
):
    """
    Calculate the Giant Killer Score for a Beyblade.

    The Giant Killer Score is a composite score (0-100) that measures a Bey's
    ability to defeat stronger opponents. Higher scores indicate Beys that
    frequently and convincingly beat higher-rated opponents.

    Components:
    - Upset Win Rate (35%): What percentage of wins are upsets
    - Upset Frequency (25%): How often upsets occur relative to total matches
    - Average Magnitude (25%): Average ELO difference overcome in upsets
    - Total Upsets (15%): Raw count of upset victories

    Args:
        upset_wins: Number of upset victories
        total_wins: Total number of wins
        total_matches: Total matches played
        avg_magnitude: Average ELO difference in upset wins
        max_upset_wins: Maximum upset wins in the dataset (for normalization)
        max_magnitude: Maximum average magnitude in the dataset (for normalization)

    Returns:
        float: Giant Killer Score from 0 to 100
    """
    # Calculate upset win rate (what % of wins are upsets)
    upset_winrate = upset_wins / total_wins if total_wins > 0 else 0

    # Calculate upset frequency (upsets per match)
    upset_frequency = upset_wins / total_matches if total_matches > 0 else 0

    # Normalize average magnitude (0-1 scale)
    normalized_magnitude = avg_magnitude / max_magnitude if max_magnitude > 0 else 0

    # Normalize total upsets
    normalized_upsets = upset_wins / max_upset_wins if max_upset_wins > 0 else 0

    # Calculate weighted score
    score = (
        GIANT_KILLER_WEIGHTS["upset_winrate"] * upset_winrate
        + GIANT_KILLER_WEIGHTS["upset_frequency"] * upset_frequency
        + GIANT_KILLER_WEIGHTS["avg_magnitude"] * normalized_magnitude
        + GIANT_KILLER_WEIGHTS["total_upsets"] * normalized_upsets
    )

    return round(score * 100, 1)


def analyze_upsets(history_file=HISTORY_FILE):
    """
    Analyze match history to identify upsets and calculate statistics.

    An upset occurs when a lower-rated Beyblade defeats a higher-rated opponent.
    This function processes all matches and extracts upset-related statistics.

    Args:
        history_file: Path to the ELO history CSV file

    Returns:
        tuple: (bey_stats dict, upset_matches list)
            - bey_stats: Dictionary with per-bey upset statistics
            - upset_matches: List of all upset match details
    """
    # Data structures for tracking
    bey_stats = defaultdict(lambda: {
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "upset_wins": 0,
        "upset_losses": 0,
        "upset_win_magnitudes": [],  # ELO differences in upset wins
        "upset_loss_magnitudes": [],  # ELO differences in upset losses
        "biggest_upset_win": 0,
        "biggest_upset_loss": 0,
        "last_elo": 1000
    })

    upset_matches = []

    # Read and process match history
    with open(history_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        matches = sorted(reader, key=lambda m: m["Date"])

        for row in matches:
            bey_a, bey_b = row["BeyA"], row["BeyB"]
            pre_a, pre_b = float(row["PreA"]), float(row["PreB"])
            post_a, post_b = float(row["PostA"]), float(row["PostB"])
            score_a, score_b = int(row["ScoreA"]), int(row["ScoreB"])
            date = row["Date"]

            if score_a + score_b == 0:
                continue

            # Update basic stats for both beys
            for bey, score_self, score_opp, pre_self, pre_opp, post_self in [
                (bey_a, score_a, score_b, pre_a, pre_b, post_a),
                (bey_b, score_b, score_a, pre_b, pre_a, post_b)
            ]:
                s = bey_stats[bey]
                s["matches"] += 1
                s["last_elo"] = post_self
                if score_self > score_opp:
                    s["wins"] += 1
                else:
                    s["losses"] += 1

            # Determine winner and check for upset
            if score_a > score_b:
                winner, loser = bey_a, bey_b
                winner_pre, loser_pre = pre_a, pre_b
            else:
                winner, loser = bey_b, bey_a
                winner_pre, loser_pre = pre_b, pre_a

            # An upset occurs when the lower-rated player wins
            elo_diff = loser_pre - winner_pre  # Positive if winner was underdog

            if elo_diff > 0:
                # This is an upset! Winner had lower ELO
                upset_matches.append({
                    "match_id": row.get("MatchID", ""),
                    "date": date,
                    "winner": winner,
                    "loser": loser,
                    "winner_pre_elo": winner_pre,
                    "loser_pre_elo": loser_pre,
                    "elo_difference": round(elo_diff, 2),
                    "score": f"{score_a}-{score_b}" if winner == bey_a else f"{score_b}-{score_a}"
                })

                # Update winner's upset stats
                bey_stats[winner]["upset_wins"] += 1
                bey_stats[winner]["upset_win_magnitudes"].append(elo_diff)
                if elo_diff > bey_stats[winner]["biggest_upset_win"]:
                    bey_stats[winner]["biggest_upset_win"] = elo_diff

                # Update loser's upset stats
                bey_stats[loser]["upset_losses"] += 1
                bey_stats[loser]["upset_loss_magnitudes"].append(elo_diff)
                if elo_diff > bey_stats[loser]["biggest_upset_loss"]:
                    bey_stats[loser]["biggest_upset_loss"] = elo_diff

    return bey_stats, upset_matches


def calculate_analysis_metrics(bey_stats):
    """
    Calculate derived metrics from raw upset statistics.

    Args:
        bey_stats: Dictionary with per-bey upset statistics

    Returns:
        list: List of dictionaries with calculated metrics for each bey
    """
    intermediate_data = []

    for bey, stats in bey_stats.items():
        upset_wins = stats["upset_wins"]
        upset_losses = stats["upset_losses"]
        total_wins = stats["wins"]
        total_matches = stats["matches"]

        # Calculate average upset magnitudes
        avg_upset_win_magnitude = (
            sum(stats["upset_win_magnitudes"]) / len(stats["upset_win_magnitudes"])
            if stats["upset_win_magnitudes"] else 0
        )
        avg_upset_loss_magnitude = (
            sum(stats["upset_loss_magnitudes"]) / len(stats["upset_loss_magnitudes"])
            if stats["upset_loss_magnitudes"] else 0
        )

        # Calculate upset rate (upsets per win opportunity)
        upset_rate = upset_wins / total_wins if total_wins > 0 else 0

        # Calculate vulnerability (upset losses per loss)
        vulnerability = upset_losses / (total_matches - total_wins) if (total_matches - total_wins) > 0 else 0

        intermediate_data.append({
            "bey": bey,
            "elo": stats["last_elo"],
            "matches": total_matches,
            "wins": total_wins,
            "losses": stats["losses"],
            "upset_wins": upset_wins,
            "upset_losses": upset_losses,
            "upset_rate": upset_rate,
            "vulnerability": vulnerability,
            "avg_upset_win_magnitude": avg_upset_win_magnitude,
            "avg_upset_loss_magnitude": avg_upset_loss_magnitude,
            "biggest_upset_win": stats["biggest_upset_win"],
            "biggest_upset_loss": stats["biggest_upset_loss"]
        })

    return intermediate_data


def calculate_giant_killer_scores(intermediate_data):
    """
    Calculate Giant Killer Scores for all beys using normalized metrics.

    Args:
        intermediate_data: List of dictionaries with calculated metrics

    Returns:
        list: List of dictionaries with Giant Killer Scores added
    """
    # Calculate normalization parameters
    max_upset_wins = max((d["upset_wins"] for d in intermediate_data), default=1)
    max_magnitude = max((d["avg_upset_win_magnitude"] for d in intermediate_data), default=1)

    # Calculate scores
    for d in intermediate_data:
        d["giant_killer_score"] = calculate_giant_killer_score(
            upset_wins=d["upset_wins"],
            total_wins=d["wins"],
            total_matches=d["matches"],
            avg_magnitude=d["avg_upset_win_magnitude"],
            max_upset_wins=max_upset_wins,
            max_magnitude=max_magnitude
        )

    return intermediate_data


def save_upset_analysis(analysis_data, upset_matches, output_file=UPSET_ANALYSIS_FILE,
                        matches_file=UPSET_MATCHES_FILE):
    """
    Save upset analysis results to CSV files.

    Args:
        analysis_data: List of dictionaries with per-bey analysis
        upset_matches: List of upset match details
        output_file: Path to save per-bey analysis
        matches_file: Path to save upset matches
    """
    # Sort by Giant Killer Score descending
    sorted_data = sorted(analysis_data, key=lambda x: -x["giant_killer_score"])

    # Save per-bey analysis
    header = [
        "Rank", "Bey", "ELO", "GiantKillerScore", "Matches", "Wins", "Losses",
        "UpsetWins", "UpsetLosses", "UpsetRate", "Vulnerability",
        "AvgUpsetWinMagnitude", "AvgUpsetLossMagnitude",
        "BiggestUpsetWin", "BiggestUpsetLoss"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for rank, d in enumerate(sorted_data, start=1):
            writer.writerow([
                rank,
                d["bey"],
                round(d["elo"]),
                d["giant_killer_score"],
                d["matches"],
                d["wins"],
                d["losses"],
                d["upset_wins"],
                d["upset_losses"],
                f"{d['upset_rate'] * 100:.1f}%",
                f"{d['vulnerability'] * 100:.1f}%",
                round(d["avg_upset_win_magnitude"], 1),
                round(d["avg_upset_loss_magnitude"], 1),
                round(d["biggest_upset_win"], 1),
                round(d["biggest_upset_loss"], 1)
            ])

    # Save individual upset matches (sorted by magnitude descending)
    sorted_upsets = sorted(upset_matches, key=lambda x: -x["elo_difference"])

    matches_header = [
        "Rank", "MatchID", "Date", "Winner", "Loser", "WinnerPreELO", "LoserPreELO",
        "ELODifference", "Score"
    ]

    with open(matches_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(matches_header)
        for rank, m in enumerate(sorted_upsets, start=1):
            writer.writerow([
                rank,
                m["match_id"],
                m["date"],
                m["winner"],
                m["loser"],
                round(m["winner_pre_elo"], 1),
                round(m["loser_pre_elo"], 1),
                m["elo_difference"],
                m["score"]
            ])

    # Copy to docs folder
    os.makedirs("./docs/data", exist_ok=True)

    with open(output_file, "r", encoding="utf-8") as src:
        with open("./docs/data/upset_analysis.csv", "w", encoding="utf-8") as dst:
            dst.write(src.read())

    with open(matches_file, "r", encoding="utf-8") as src:
        with open("./docs/data/upset_matches.csv", "w", encoding="utf-8") as dst:
            dst.write(src.read())


def print_summary(analysis_data, upset_matches):
    """
    Print a summary of the upset analysis to console.

    Args:
        analysis_data: List of dictionaries with per-bey analysis
        upset_matches: List of upset match details
    """
    print(f"\n{BOLD}{CYAN}=== Upset Analysis Summary ==={RESET}\n")

    # Total upsets
    total_upsets = len(upset_matches)
    print(f"{YELLOW}Total Upsets:{RESET} {total_upsets}")

    # Top Giant Killers
    sorted_by_score = sorted(analysis_data, key=lambda x: -x["giant_killer_score"])
    print(f"\n{BOLD}{GREEN}Top 5 Giant Killers:{RESET}")
    for i, d in enumerate(sorted_by_score[:5], start=1):
        print(f"  {i}. {d['bey']} - Score: {d['giant_killer_score']}, "
              f"Upsets: {d['upset_wins']}, Avg Magnitude: {d['avg_upset_win_magnitude']:.1f}")

    # Biggest Upsets
    sorted_upsets = sorted(upset_matches, key=lambda x: -x["elo_difference"])
    print(f"\n{BOLD}{GREEN}Top 5 Biggest Upsets:{RESET}")
    for i, m in enumerate(sorted_upsets[:5], start=1):
        print(f"  {i}. {m['winner']} beat {m['loser']} "
              f"(ELO diff: {m['elo_difference']:.1f}) on {m['date']}")

    # Most Vulnerable (high upset loss count)
    sorted_by_losses = sorted(analysis_data, key=lambda x: -x["upset_losses"])
    vulnerable = [d for d in sorted_by_losses if d["upset_losses"] > 0]
    if vulnerable:
        print(f"\n{BOLD}{YELLOW}Most Vulnerable (prone to upset losses):{RESET}")
        for i, d in enumerate(vulnerable[:5], start=1):
            print(f"  {i}. {d['bey']} - Upset Losses: {d['upset_losses']}, "
                  f"Vulnerability: {d['vulnerability'] * 100:.1f}%")


def run_upset_analysis():
    """
    Run the complete upset analysis pipeline.

    Returns:
        tuple: (analysis_data, upset_matches) for further processing if needed
    """
    print(f"{BOLD}{CYAN}Running Upset Analysis...{RESET}")

    # Analyze upsets from match history
    bey_stats, upset_matches = analyze_upsets()

    # Calculate metrics
    intermediate_data = calculate_analysis_metrics(bey_stats)

    # Calculate Giant Killer Scores
    analysis_data = calculate_giant_killer_scores(intermediate_data)

    # Save results
    save_upset_analysis(analysis_data, upset_matches)

    # Print summary
    print_summary(analysis_data, upset_matches)

    print(f"\n{GREEN}Upset Analysis saved to: {UPSET_ANALYSIS_FILE}{RESET}")
    print(f"{GREEN}Upset Matches saved to: {UPSET_MATCHES_FILE}{RESET}")

    return analysis_data, upset_matches


# --- Main ---
if __name__ == "__main__":
    run_upset_analysis()
