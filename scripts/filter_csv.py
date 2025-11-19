import pandas as pd

# ---- CONFIG ----
INPUT_CSV = "./csv/position_timeseries.csv"           # Originaldatei
OUTPUT_CSV = "debug_bey.csv"      # Ziel-Datei
BEY_NAME = "CerberusFlame"           # Der Bey, den du filtern willst
# -----------------


def main():
    # CSV laden
    df = pd.read_csv(INPUT_CSV)

    # Prüfen, ob Spalte "Bey" existiert
    if "Bey" not in df.columns:
        raise ValueError("Spalte 'Bey' wurde in der CSV nicht gefunden!")

    # Filtern
    df_filtered = df[df["Bey"] == BEY_NAME]

    # Neue Datei speichern
    df_filtered.to_csv(OUTPUT_CSV, index=False)

    print(f"Gefundene Zeilen: {len(df_filtered)}")
    print(f"Gespeichert in: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
