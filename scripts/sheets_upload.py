import gspread, csv
from oauth2client.service_account import ServiceAccountCredentials
import os

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
# Winrate-Spalte ist Spalte 9 (Index 9, J)
upload_csv_to_sheet("./csv/leaderboard.csv", "Leaderboard")
upload_csv_to_sheet("./csv/advanced_leaderboard.csv", "Advanced_Leaderboard")
upload_csv_to_sheet("./csv/elo_history.csv", "ELO_History")
upload_csv_to_sheet("./csv/elo_timeseries.csv", "ELO_Timeseries")
upload_csv_to_sheet("./csv/bey_counters.csv", "Bey_Counters")

print(f"{GREEN}Alle Daten erfolgreich zu Google Sheets hochgeladen!{RESET}")
