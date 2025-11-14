# visualize.py — Version 2.4.1
# Renders all plots (heatmaps, trends, bars) for official or private ladder.

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["axes.grid"] = True


# -------------------
# File selection
# -------------------
def load_files(mode):
    if mode == "official":
        return {
            "leaderboard": "./csv/leaderboard.csv",
            "history": "./csv/elo_history.csv",
            "timeseries": "./csv/elo_timeseries.csv",
            "outdir": "./plots/official/"
        }
    else:
        return {
            "leaderboard": "./csv/private_leaderboard.csv",
            "history": "./csv/private_elo_history.csv",
            "timeseries": "./csv/private_elo_timeseries.csv",
            "outdir": "./plots/private/"
        }


# -------------------
# Ensure output dir
# -------------------
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


# -------------------
# Elo Line Chart
# -------------------
def plot_elo_trends(df_ts, outdir):
    for bey in df_ts["Bey"].unique():
        sub = df_ts[df_ts["Bey"] == bey]

        plt.figure()
        plt.plot(sub["MatchIndex"], sub["ELO"])
        plt.title(f"ELO-Verlauf — {bey}")
        plt.xlabel("Match Index")
        plt.ylabel("ELO")

        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"elo_trend_{bey}.png"))
        plt.close()


# -------------------
# ELO Bar Chart
# -------------------
def plot_leaderboard_bars(df, outdir):
    sorted_df = df.sort_values("ELO", ascending=False)

    plt.figure(figsize=(12, 8))
    sns.barplot(data=sorted_df, x="ELO", y="Name")
    plt.title("ELO Leaderboard")
    plt.xlabel("ELO")
    plt.ylabel("Bey")

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "elo_bar_chart.png"))
    plt.close()


# -------------------
# Winrate Bar Chart
# -------------------
def plot_winrates(df, outdir):
    df["WR"] = df["Winrate"].str.replace("%", "").astype(float)

    sorted_df = df.sort_values("WR", ascending=False)

    plt.figure(figsize=(12, 8))
    sns.barplot(data=sorted_df, x="WR", y="Name")
    plt.title("Winrates")
    plt.xlabel("Winrate (%)")
    plt.ylabel("Bey")

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "winrate_bar_chart.png"))
    plt.close()


# -------------------
# Heatmaps: win/loss + point diff
# -------------------
def plot_heatmaps(df_hist, outdir):
    beys = sorted(set(df_hist["BeyA"]) | set(df_hist["BeyB"]))

    win_counts = pd.DataFrame(0, index=beys, columns=beys)
    point_diff = pd.DataFrame(0, index=beys, columns=beys)

    for _, m in df_hist.iterrows():
        a, b = m["BeyA"], m["BeyB"]
        sa, sb = m["ScoreA"], m["ScoreB"]

        if sa > sb:
            win_counts.loc[a, b] += 1
        else:
            win_counts.loc[b, a] += 1

        point_diff.loc[a, b] += sa - sb
        point_diff.loc[b, a] += sb - sa

    # Winrate matrix
    matches = win_counts + win_counts.T
    winrate = (win_counts / matches.replace(0, pd.NA)).fillna(0)

    plt.figure(figsize=(18, 14))
    sns.heatmap(winrate, cmap="viridis")
    plt.title("Winrate Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "heatmap_winrate.png"))
    plt.close()

    # Point differential
    plt.figure(figsize=(18, 14))
    sns.heatmap(point_diff, cmap="coolwarm", center=0)
    plt.title("Point Differential Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "heatmap_pointdiff.png"))
    plt.close()


# -------------------
# Master runner
# -------------------
def generate_all_plots(mode):
    files = load_files(mode)
    ensure_dir(files["outdir"])

    print(f"Loading data for mode: {mode}")

    df_lb = pd.read_csv(files["leaderboard"])
    df_hist = pd.read_csv(files["history"])
    df_ts = pd.read_csv(files["timeseries"])

    outdir = files["outdir"]

    print("Rendering charts...")

    plot_leaderboard_bars(df_lb, outdir)
    plot_winrates(df_lb, outdir)
    plot_elo_trends(df_ts, outdir)
    plot_heatmaps(df_hist, outdir)

    print(f"All plots saved to: {outdir}")


# -------------------
# Main CLI
# -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()

    generate_all_plots(args.mode)
