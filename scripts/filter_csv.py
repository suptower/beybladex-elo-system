import pandas as pd
import argparse

# ---- CONFIG ----
INPUT_CSV = "./csv/matches.csv"           # Originaldatei
OUTPUT_CSV = "debug_bey.csv"      # Ziel-Datei
BEY_NAME = "CerberusFlame"           # Der Bey, den du filtern willst
FILTER_DATE = None           # Das Datum, nach dem du filtern willst (Format: YYYY-MM-DD)
# -----------------


def main():
    # CSV laden
    df = pd.read_csv(INPUT_CSV)

    # Prüfen, ob Spalte "Bey" existiert
    if "Bey" not in df.columns:
        raise ValueError("Spalte 'Bey' wurde in der CSV nicht gefunden!")
    
    df_filtered = pd.DataFrame()

    # Filtern after date and bey
    if FILTER_DATE and BEY_NAME:
        df_filtered = df[(df["Bey"] == BEY_NAME) & (df["Date"] == FILTER_DATE)]
    elif BEY_NAME:
        df_filtered = df[df["Bey"] == BEY_NAME]
    elif FILTER_DATE:
        df_filtered = df[df["Date"] == FILTER_DATE]
    else:
        df_filtered = df

    # Neue Datei speichern
    df_filtered.to_csv(OUTPUT_CSV, index=False)

    print(f"Gefundene Zeilen: {len(df_filtered)}")
    print(f"Gespeichert in: {OUTPUT_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter CSV by Bey name")
    parser.add_argument("--input", type=str, default=INPUT_CSV, help="Input CSV file path")
    parser.add_argument("--output", type=str, default=OUTPUT_CSV, help="Output CSV file path")
    parser.add_argument("--bey", type=str, default=BEY_NAME, help="Bey name to filter by")
    parser.add_argument("--date", type=str, help="Date to filter by (format: YYYY-MM-DD)")
    args = parser.parse_args()

    INPUT_CSV = args.input
    OUTPUT_CSV = args.output
    BEY_NAME = args.bey

    main()
