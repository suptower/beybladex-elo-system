# gen_plots.py — Version 3.0
# Renders all plots (heatmaps, trends, bars) for official or private ladder.
# Now with individual ELO charts, combined ELO chart, organized folders, and HTML gallery.

import argparse
import os, subprocess
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

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
# Ensure subfolders
# -------------------
def ensure_subdirs(base):
    subdirs = ["elo", "heatmaps", "bars"]
    paths = {}
    for s in subdirs:
        path = os.path.join(base, s)
        os.makedirs(path, exist_ok=True)
        paths[s] = path
    return paths

# -------------------
# ELO Charts
# -------------------
def plot_elo_combined(df_ts, outdir):
    df_ts["ELO"] = pd.to_numeric(df_ts["ELO"], errors="coerce")
    df_ts["MatchIndex"] = df_ts["MatchIndex"].astype(int)
    df_ts = df_ts.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    combined_file = os.path.join(outdir, "elo_combined.png")
    plt.figure(figsize=(10, 6))
    for bey, group in df_ts.groupby("Bey"):
        plt.plot(group["MatchIndex"], group["ELO"], label=bey, linewidth=1.3)
    plt.title("ELO-Verlauf aller Beys")
    plt.xlabel("Match")
    plt.ylabel("ELO")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7, ncol=3, loc="best")
    plt.tight_layout()
    plt.savefig(combined_file, dpi=300)
    plt.close()
    print(f"Kombiniertes ELO-Diagramm gespeichert als {combined_file}")

def plot_elo_single(df_ts, outdir):
    df_ts["ELO"] = pd.to_numeric(df_ts["ELO"], errors="coerce")
    df_ts["MatchIndex"] = df_ts["MatchIndex"].astype(int)
    df_ts = df_ts.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

    for bey, group in df_ts.groupby("Bey"):
        plt.figure(figsize=(6, 4))
        plt.plot(group["MatchIndex"], group["ELO"], marker="o", linewidth=1.8)
        plt.xticks(ticks=range(group["MatchIndex"].min(), group["MatchIndex"].max() + 1))
        plt.title(f"ELO-Verlauf: {bey}")
        plt.xlabel("Match")
        plt.ylabel("ELO")
        plt.grid(True, alpha=0.4)
        plt.tight_layout()

        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
        out_path = os.path.join(outdir, f"{safe_name}.png")
        plt.savefig(out_path, dpi=200)
        plt.close()
    print(f"Einzelne ELO-Diagramme gespeichert im Ordner: {outdir}")

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

    matches = win_counts + win_counts.T
    winrate = (win_counts / matches.replace(0, np.nan)).fillna(0)
    plt.figure(figsize=(18, 14))
    sns.heatmap(winrate, cmap="viridis")
    plt.title("Winrate Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "heatmap_winrate.png"))
    plt.close()

    plt.figure(figsize=(18, 14))
    sns.heatmap(point_diff, cmap="coolwarm", center=0)
    plt.title("Point Differential Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "heatmap_pointdiff.png"))
    plt.close()

# -------------------
# HTML Galerie mit Grid & Lightbox
# -------------------
def generate_html_gallery(base_dir):
    html_path = os.path.join(base_dir, "index.html")
    sections = {
        "ELO Charts": "elo",
        "Heatmaps": "heatmaps",
        "Barcharts": "bars"
    }
    html = [
        "<!DOCTYPE html>",
        "<html lang='de'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Beyblade X — Diagramme</title>",
        "<link href='https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/css/lightbox.min.css' rel='stylesheet'>",
        "<style>",
        "body { font-family: Arial; background:#111; color:#eee; padding:20px; }",
        "h1 { color:#6cf; }",
        "h2 { color:#fc6; margin-top:40px; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }",
        ".grid img { width: 100%; height: auto; border: 2px solid #555; border-radius:8px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Diagramm-Galerie</h1>"
    ]
    for title, folder in sections.items():
        html.append(f"<h2>{title}</h2>")
        html.append("<div class='grid'>")
        folder_path = os.path.join(base_dir, folder)
        images = [f for f in os.listdir(folder_path) if f.lower().endswith(".png")]
        for img in sorted(images):
            img_rel = f"{folder}/{img}"
            html.append(f"<a href='{img_rel}' data-lightbox='{folder}'><img src='{img_rel}' alt='{img}'></a>")
        html.append("</div>")
    html.append("<script src='https://cdnjs.cloudflare.com/ajax/libs/lightbox2/2.11.3/js/lightbox.min.js'></script>")
    html.append("</body></html>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"HTML-Galerie erzeugt: {html_path}")

# -------------------
# Master runner
# -------------------
def generate_all_plots(mode):
    files = load_files(mode)
    ensure_dir(files["outdir"])
    dirs = ensure_subdirs(files["outdir"])

    print(f"Loading data for mode: {mode}")

    df_lb = pd.read_csv(files["leaderboard"])
    df_hist = pd.read_csv(files["history"])
    df_ts = pd.read_csv(files["timeseries"])

    print("Rendering charts...")

    # ELO
    plot_elo_combined(df_ts, dirs["elo"])
    plot_elo_single(df_ts, dirs["elo"])

    # BAR CHARTS
    plot_leaderboard_bars(df_lb, dirs["bars"])
    plot_winrates(df_lb, dirs["bars"])

    # HEATMAPS
    plot_heatmaps(df_hist, dirs["heatmaps"])

    # HTML-Galerie
    generate_html_gallery(files["outdir"])

    # Advanced Visualizations
    result = subprocess.run(
        ["python", "scripts/visualization/advanced_visualizations.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running advanced_visualizations.py:")
        print(result.stderr)
    else:
        print("Advanced visualizations generated successfully.")

    # Combined ELO Trends Top 5
    result = subprocess.run(
        ["python", "scripts/visualization/combined_elo_trends_top5.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running combined_elo_trends_top5.py:")
        print(result.stderr)
    else:
        print("Combined ELO Trends Top 5 generated successfully.")

    # Heatmaps
    result = subprocess.run(
        ["python", "scripts/visualization/heatmaps.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running heatmaps.py:")
        print(result.stderr)
    else:
        print("Heatmaps generated successfully.")

    # Interactive ELO Trends
    result = subprocess.run(
        ["python", "scripts/visualization/interactive_elo_trends.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Error running interactive_elo_trends.py:")
        print(result.stderr)
    else:
        print("Interactive ELO Trends generated successfully.")

    print(f"All plots saved to: {files['outdir']}")

# -------------------
# Main CLI
# -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["official", "private"], default="official",
                        help="Select ladder mode: official or private")
    args = parser.parse_args()
    generate_all_plots(args.mode)
