# BeybladeX Elo System

Lightweight tools for computing and publishing Elo ratings and charts for Beyblade tournaments.

**Purpose**
- Track match results, compute Elo ratings, generate charts, and export leaderboards.

**Quick Overview**
- Input data: CSV files in `csv/` (e.g. `matches.csv`, `beys.csv`).
- Main scripts:
  - `combined_update.py` — runs the full update pipeline (compute Elo, update CSVs, produce artifacts).
  - `generate_elo_charts.py` — creates time-series and leaderboard charts in `elo_charts/` and `tournament-charts/`.
  - `export_leaderboard_pdf.py` — exports a printable leaderboard PDF from `csv/leaderboard.csv`.
  - `scripts/beyblade_elo.py` — helper functions and Elo logic.
  - `scripts/sheets_upload.py` — uploads CSV or leaderboard data to Google Sheets (uses `service_account.json`).

**Repository Structure**
- `*.py` — top-level runner scripts for updates, charts and exports.
- `csv/` — source and generated CSV data (matches, leaderboard, elo history, timeseries).
- `elo_charts/`, `tournament-charts/` — generated charts and visual assets.
- `scripts/` — library-like helpers (Elo logic, Sheets upload).
- `service_account.json` — (optional) Google service account credentials for Sheets API.

**Requirements** (suggested)
- Python 3.8+
- Typical libraries used: `pandas`, `matplotlib`, `reportlab` (or `fpdf`), `google-api-python-client`, `google-auth`, `google-auth-httplib2`, `google-auth-oauthlib`.

Install quick environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pandas matplotlib reportlab google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib
```

(If your project has a `requirements.txt` later, replace the last install with `pip install -r requirements.txt`.)

**Usage examples**
- Run the full pipeline (if `combined_update.py` is implemented to run all steps):

```powershell
python combined_update.py
```

- Generate only charts:

```powershell
python generate_elo_charts.py
```

- Export leaderboard to PDF:

```powershell
python export_leaderboard_pdf.py
```

- Upload to Google Sheets (ensure `service_account.json` has correct scopes and path):

```powershell
python scripts\sheets_upload.py
```

**CSV files**
- `csv/matches.csv` — recorded matches (winner, loser, timestamp, etc.).
- `csv/beys.csv` — competitor metadata.
- `csv/elo_history.csv` — chronological Elo changes.
- `csv/leaderboard.csv` — latest calculated leaderboard (used by export and uploads).

**Google Sheets**
- Place a service account JSON in the repository or secure path and update `scripts/sheets_upload.py` to point to it.
- Share the target Google Sheet with the service account email.


