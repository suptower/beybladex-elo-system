import gspread
import csv
import os
from oauth2client.service_account import ServiceAccountCredentials

from src.config.paths import (
    LEADERBOARD_CSV,
    ADVANCED_LEADERBOARD_CSV,
    ELO_HISTORY_CSV,
    ELO_TIMESERIES_CSV,
    BEY_COUNTERS_CSV,
    LEADERBOARD_DIR,
)

# Aktiviert ANSI-Farben in Windows-Terminals
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"

SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "service_account.json"
SHEET_ID = "1taZJq9c1H2KfvhH5GMnIQ-c701IZqLXvMnBSENrxNVw"


def upload_csv_to_sheet(csv_file, sheet_name, percent_cols=[]):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)

    try:
        ws = sheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=sheet_name, rows="500", cols="20")

    ws.clear()
    with open(csv_file, encoding="utf-8") as f:
        data = list(csv.reader(f))
    ws.update(values=data, range_name="A1")
    print(f"{GREEN}{csv_file} -> {sheet_name}{RESET}")


# --- Tabellen hochladen ---
print(f"{BOLD}Lade Leaderboards zu Google Sheets hoch...{RESET}", flush=True)
upload_csv_to_sheet(LEADERBOARD_CSV, "Leaderboard")
print(f"{GREEN}Haupt-Rangliste hochgeladen.{RESET}")
print(f"{BOLD}Lade erweiterte Daten zu Google Sheets hoch...{RESET}", flush=True)
upload_csv_to_sheet(ADVANCED_LEADERBOARD_CSV, "Advanced_Leaderboard")
print(f"{GREEN}Erweiterte Daten hochgeladen.{RESET}", flush=True)
upload_csv_to_sheet(ELO_HISTORY_CSV, "ELO_History")
print(f"{GREEN}ELO-Verlauf hochgeladen.{RESET}", flush=True)
upload_csv_to_sheet(ELO_TIMESERIES_CSV, "ELO_Timeseries")
print(f"{GREEN}ELO-Zeitreihe hochgeladen.{RESET}", flush=True)
upload_csv_to_sheet(BEY_COUNTERS_CSV, "Bey_Counters")
print(f"{GREEN}Bey-Counter-Daten hochgeladen.{RESET}", flush=True)

# Alle leaderboard csvs hochladen
print(f"{BOLD}Lade einzelne Turnier-Ranglisten zu Google Sheets hoch...{RESET}", flush=True)
for file in os.listdir(LEADERBOARD_DIR):
    if file.startswith("leaderboard_") and file.endswith(".csv"):
        print(f"{GREEN}Lade {file} hoch...{RESET}", flush=True)
        t_idx = file[len("leaderboard_"):-len(".csv")]
        upload_csv_to_sheet(os.path.join(LEADERBOARD_DIR, file), f"Single_Leaderboard_{t_idx}")


print(f"{GREEN}Alle Daten erfolgreich zu Google Sheets hochgeladen!{RESET}")
