# BeybladeX Elo System

Lightweight tools for computing and publishing Elo ratings and charts for Beyblade tournaments.

**Purpose**
- Track match results, compute Elo ratings, generate charts, and export leaderboards.

**Quick Overview**
- Input data: CSV files in `csv/` (e.g. `matches.csv`, `beys.csv`).
- Main scripts:
  - `update.py` — runs the full update pipeline (compute Elo, update CSVs, produce artifacts).
  - `generate_elo_charts.py` — creates time-series and leaderboard charts in `elo_charts/` and `tournament-charts/`.
  - `export_leaderboard_pdf.py` — exports a printable leaderboard PDF from `csv/leaderboard.csv`.
  - `scripts/beyblade_elo.py` — helper functions and Elo logic.
  - `scripts/sheets_upload.py` — uploads CSV or leaderboard data to Google Sheets (uses `service_account.json`).
  - `scripts/simulation.py` — simulates tournaments using Elo-based match predictions.
  - `scripts/challonge_scraper.py` — scrapes tournament data from Challonge and appends to `matches.csv`.

**Repository Structure**
- `*.py` — top-level runner scripts for updates, charts and exports.
- `csv/` — source and generated CSV data (matches, leaderboard, elo history, timeseries).
- `elo_charts/`, `tournament-charts/` — generated charts and visual assets.
- `scripts/` — library-like helpers (Elo logic, Sheets upload).
- `service_account.json` — (optional) Google service account credentials for Sheets API.

**Usage examples**
- Run the full pipeline:

```powershell
python update.py
```

- Simulate a tournament:

```powershell
# Single elimination tournament with 8 random participants
python scripts/simulation.py -n 8 -f single-elimination

# Round-robin tournament with specific Beyblades
python scripts/simulation.py -f round-robin -b FoxBrush ImpactDrake DranSword

# Append simulated matches to matches.csv (then run update.py to recalculate Elo)
python scripts/simulation.py -n 16 -f single-elimination --append
```

- Import tournament data from Challonge:

```powershell
# Scrape a tournament and append matches to matches.csv
python scripts/challonge_scraper.py https://challonge.com/om3hx2e9

# Preview matches without writing (dry-run)
python scripts/challonge_scraper.py om3hx2e9 --dry-run

# Specify a custom date for the tournament
python scripts/challonge_scraper.py zjbg6ab3 --date 2025-09-15

# After scraping, run update.py to recalculate Elo ratings
python update.py
```



**CSV files**
- `csv/bey_counters.csv` - counter tables.
- `csv/beys.csv` — competitor names.
- `csv/elo_history.csv` — chronological Elo changes.
- `csv/leaderboard.csv` — latest calculated leaderboard (used by export and uploads).
- `csv/matches.csv` — recorded matches (winner, loser, timestamp, etc.).
- `csv/simulated_matches.csv` — output from simulation script (can be appended to matches.csv).

**Google Sheets**
- Place a service account JSON in the repository or secure path and update `scripts/sheets_upload.py` to point to it.
- Share the target Google Sheet with the service account email.


