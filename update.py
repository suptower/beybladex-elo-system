# update_beyblade.py
import subprocess
import sys, os
import argparse

# --- Argumente parsen ---
parser = argparse.ArgumentParser(description="Beyblade X Update Script")
parser.add_argument(
    "--create-diagrams", "-d",
    action="store_true",
    help="Optional: ELO-Diagramme erstellen"
)
parser.add_argument(
    "--skip-upload", "-s",
    action="store_true",
    help="Optional: Upload zu Google Sheets überspringen"
)
args = parser.parse_args()

# Aktiviert ANSI-Farben in Windows-Terminals (macht nix auf anderen Systemen)
os.system("")

# Farben
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


print(f"{BOLD}{GREEN}Starte Beyblade X Update Routine...{RESET}")

# ELO berechnen
print(f"{YELLOW}Starte Skript zur ELO-Berechnung...{RESET}")
result = subprocess.run([sys.executable, "./scripts/beyblade_elo.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Advanced Stats berechnen
print(f"{YELLOW}Starte Skript zur Berechnung erweiterter Statistiken...{RESET}")
result = subprocess.run([sys.executable, "./scripts/advanced_stats.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# --- 2. Optional Diagramme erstellen ---
if args.create_diagrams:
    print(f"{YELLOW}Generiere ELO-Diagramme...{RESET}")
    result = subprocess.run([sys.executable, "./scripts/generate_elo_charts.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"{YELLOW}Generiere erweiterte Diagramme...{RESET}")
    result = subprocess.run([sys.executable, "./scripts/advanced_visualizations.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
else:
    print(f"{YELLOW}Diagramme übersprungen (mit --create-diagrams aktivieren){RESET}")



# PDF-Rangliste erstellen
print(f"{YELLOW}Erstelle PDF-Rangliste...{RESET}")
result = subprocess.run([sys.executable, "./scripts/export_leaderboard_pdf.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Bey-Counter aktualisieren
print(f"{YELLOW}Aktualisiere Bey-Counter...{RESET}")
result = subprocess.run([sys.executable, "./scripts/counter_checker.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Daten hochladen
if args.skip_upload:
    print(f"{YELLOW}Upload zu Google Sheets übersprungen (mit --skip-upload deaktivieren){RESET}")
else:
    print(f"{YELLOW}Lade Daten nach Google Sheets...{RESET}")
    result = subprocess.run([sys.executable, "./scripts/sheets_upload.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

print(f"{GREEN}Alles erledigt! Leaderboard, History und Bey-Counters wurden aktualisiert.{RESET}")