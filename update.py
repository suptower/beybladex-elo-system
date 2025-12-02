# update_beyblade.py
import subprocess
import sys
import os
import argparse

SCRIPT_ADVANCED_STATS = "./src/advanced_stats.py"
SCRIPT_BLADE_ELO = "./src/beyblade_elo.py"
SCRIPT_COUNTER_CHECKER = "./src/counter_checker.py"
SCRIPT_SHEETS_UPLOAD = "./src/sheets_upload.py"
SCRIPT_EXPORT_PDF = "./src/export_leaderboard_pdf.py"
SCRIPT_GEN_PLOTS = "./src/gen_plots.py"
SCRIPT_SYNERGY_HEATMAPS = "./src/synergy_heatmaps.py"

# --- Argumente parsen ---
parser = argparse.ArgumentParser(description="Beyblade X Update Script")
parser.add_argument(
    "--skip-diagrams", "-s",
    action="store_true",
    help="Optional: ELO-Diagramme nicht erstellen"
)
parser.add_argument(
    "--upload", "-u",
    action="store_true",
    help="Optional: Upload zu Google Sheets"
)
parser.add_argument(
    "--pdf", "-p",
    action="store_true",
    help="Optional: PDF-Rangliste erstellen"
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

# Synergy Heatmaps generieren
print(f"{YELLOW}Generiere Synergy Heatmap Daten...{RESET}")
result = subprocess.run([sys.executable, SCRIPT_SYNERGY_HEATMAPS], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# --- 2. Optional Diagramme erstellen ---
if not args.skip_diagrams:
    print(f"{YELLOW}Generiere Diagramme...{RESET}")
    process = subprocess.Popen(
        [sys.executable, "-u", SCRIPT_GEN_PLOTS],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
else:
    print(f"{YELLOW}Diagramme übersprungen (mit --create-diagrams aktivieren){RESET}")


# PDF-Rangliste erstellen
if not args.pdf:
    print(f"{YELLOW}PDF-Rangliste übersprungen (mit --pdf aktivieren){RESET}")
else:
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
if not args.upload:
    print(f"{YELLOW}Upload zu Google Sheets übersprungen (mit --upload aktivieren){RESET}")
else:
    print(f"{YELLOW}Lade Daten nach Google Sheets...{RESET}")
    process = subprocess.Popen(
        [sys.executable, "-u", SCRIPT_SHEETS_UPLOAD],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()

print(f"{GREEN}Alles erledigt! Leaderboard, History und Bey-Counters wurden aktualisiert.{RESET}")
