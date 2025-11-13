import pandas as pd
import matplotlib.pyplot as plt
import os

# === Einstellungen ===
INPUT_FILE = "./csv/elo_timeseries.csv"
OUTPUT_FOLDER = "elo_charts"
COMBINED_FILE = "elo_combined.png"

# === Ausgabeordner anlegen ===
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Daten laden ===
df = pd.read_csv(INPUT_FILE, parse_dates=["Date"])

# Falls ELO-Werte als Text gespeichert sind → konvertieren
df["ELO"] = pd.to_numeric(df["ELO"], errors="coerce")

# Nach Datum sortieren
df["MatchIndex"] = df["MatchIndex"].astype(int)
df = df.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)

# === 1️⃣ Kombiniertes Diagramm ===
plt.figure(figsize=(10, 6))
for bey, group in df.groupby("Bey"):
    plt.plot(group["MatchIndex"], group["ELO"], label=bey, linewidth=1.3)


plt.title("ELO-Verlauf aller Beys")
plt.xlabel("Match")
plt.ylabel("ELO")
plt.grid(True, alpha=0.3)
plt.legend(fontsize=7, ncol=3, loc="best")
plt.tight_layout()
plt.savefig(COMBINED_FILE, dpi=300)
plt.close()
print(f"Kombiniertes Diagramm gespeichert als {COMBINED_FILE}")

# === 2️⃣ Einzelne Diagramme pro Bey ===
for bey, group in df.groupby("Bey"):
    plt.figure(figsize=(6, 4))
    plt.plot(group["MatchIndex"], group["ELO"], marker="o", linewidth=1.8)
    plt.xticks(ticks=range(group["MatchIndex"].min(), group["MatchIndex"].max() + 1))
    plt.title(f"ELO-Verlauf: {bey}")
    plt.xlabel("Match")
    plt.ylabel("ELO")
    plt.grid(True, alpha=0.4)
    plt.tight_layout()

    # Dateinamen bereinigen
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in bey)
    out_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.png")

    plt.savefig(out_path, dpi=200)
    plt.close()

print(f"Einzelne Diagramme gespeichert im Ordner: {OUTPUT_FOLDER}")
