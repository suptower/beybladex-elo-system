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


print(f"{BOLD}{GREEN}Starte Beyblade X Update Routine...{RESET}")

# Schritt 1: ELO berechnen
print(f"{YELLOW}Starte Skript zur ELO-Berechnung...{RESET}")
result = subprocess.run([sys.executable, "./scripts/beyblade_elo.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Schritt 2: Diagramme generieren
print(f"{YELLOW}Generiere ELO-Diagramme...{RESET}")
result = subprocess.run([sys.executable, "./scripts/generate_elo_charts.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Schritt 3: PDF-Rangliste erstellen
print(f"{YELLOW}Erstelle PDF-Rangliste...{RESET}")
result = subprocess.run([sys.executable, "./scripts/export_leaderboard_pdf.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Schritt 4: Bey-Counter aktualisieren
print(f"{YELLOW}Aktualisiere Bey-Counter...{RESET}")
result = subprocess.run([sys.executable, "./scripts/counter_checker.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

# Schritt 5: Ergebnisse hochladen
print(f"{YELLOW}Lade Daten nach Google Sheets...{RESET}")
result = subprocess.run([sys.executable, "./scripts/sheets_upload.py"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)

print(f"{GREEN}Alles erledigt! Leaderboard, History und Bey-Counters wurden aktualisiert.{RESET}")