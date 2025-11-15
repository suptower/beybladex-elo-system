# update_beyblade.py
import subprocess
import sys, os
import argparse

SCRIPT_ADVANCED_STATS = "./scripts/advanced_stats.py"
SCRIPT_BLADE_ELO = "./scripts/beyblade_elo.py"
SCRIPT_COUNTER_CHECKER = "./scripts/counter_checker.py"
SCRIPT_SHEETS_UPLOAD = "./scripts/sheets_upload.py"
SCRIPT_EXPORT_PDF = "./scripts/export_leaderboard_pdf.py"
SCRIPT_GEN_PLOTS = "./scripts/gen_plots.py"

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
result = subprocess.run([sys.executable, SCRIPT_BLADE_ELO], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Advanced Stats berechnen
print(f"{YELLOW}Starte Skript zur Berechnung erweiterter Statistiken...{RESET}")
result = subprocess.run([sys.executable, SCRIPT_ADVANCED_STATS], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# --- 2. Optional Diagramme erstellen ---
if args.create_diagrams:
    print(f"{YELLOW}Generiere Diagramme...{RESET}")
    process = subprocess.Popen([sys.executable, "-u", SCRIPT_GEN_PLOTS], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()
else:
    print(f"{YELLOW}Diagramme übersprungen (mit --create-diagrams aktivieren){RESET}")



# PDF-Rangliste erstellen
print(f"{YELLOW}Erstelle PDF-Rangliste...{RESET}")
result = subprocess.run([sys.executable, SCRIPT_EXPORT_PDF], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Bey-Counter aktualisieren
print(f"{YELLOW}Aktualisiere Bey-Counter...{RESET}")
result = subprocess.run([sys.executable, SCRIPT_COUNTER_CHECKER], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Daten hochladen
if args.skip_upload:
    print(f"{YELLOW}Upload zu Google Sheets übersprungen (mit --skip-upload deaktivieren){RESET}")
else:
    print(f"{YELLOW}Lade Daten nach Google Sheets...{RESET}")
    process = subprocess.Popen([sys.executable, "-u", SCRIPT_SHEETS_UPLOAD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()

print(f"{GREEN}Alles erledigt! Leaderboard, History und Bey-Counters wurden aktualisiert.{RESET}")