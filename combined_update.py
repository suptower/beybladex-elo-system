# update_beyblade.py
import subprocess
import sys, os

# Aktiviert ANSI-Farben in Windows-Terminals (macht nix auf anderen Systemen)
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


print(f"{BOLD}{CYAN}Starte Beyblade X ELO-Update...{RESET}")

# Schritt 1: ELO berechnen
print(f"{YELLOW}Berechne neue ELOs...{RESET}")
result = subprocess.run([sys.executable, "./scripts/beyblade_elo.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Schritt 2: Ergebnisse hochladen
print(f"{YELLOW}Lade Daten nach Google Sheets...{RESET}")
result = subprocess.run([sys.executable, "./scripts/sheets_upload.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

print(f"{GREEN}Alles erledigt! Leaderboard und History wurden aktualisiert.{RESET}")