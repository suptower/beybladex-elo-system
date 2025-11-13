# upload_to_sheets.py
import gspread, csv
from oauth2client.service_account import ServiceAccountCredentials
import os

# Aktiviert ANSI-Farben in Windows-Terminals (macht nix auf anderen Systemen)
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "service_account.json"
SHEET_ID = "1taZJq9c1H2KfvhH5GMnIQ-c701IZqLXvMnBSENrxNVw"   # z.B. aus URL: https://docs.google.com/spreadsheets/d/<ID>/edit

def upload_csv_to_sheet(csv_file, sheet_name):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)

    try: ws = sheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=sheet_name, rows="500", cols="10")

    ws.clear()
    with open(csv_file, encoding="utf-8") as f:
        data = list(csv.reader(f))
    ws.update(values=data, range_name="A1")
    print(f"{csv_file} -> {sheet_name}")

# --- beide Tabellen hochladen ---
upload_csv_to_sheet("./csv/leaderboard.csv","Leaderboard")
upload_csv_to_sheet("./csv/elo_history.csv","ELO_History")
upload_csv_to_sheet("./csv/elo_timeseries.csv","ELO_Timeseries")
upload_csv_to_sheet("./csv/bey_counters.csv","Bey_Counters")
print(f"{GREEN}Alle Daten erfolgreich zu Google Sheets hochgeladen!{RESET}")