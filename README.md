# BeybladeX Elo System

[![Python Tests](https://github.com/suptower/beybladex-elo-system/actions/workflows/test.yml/badge.svg)](https://github.com/suptower/beybladex-elo-system/actions/workflows/test.yml)
[![Python Linting](https://github.com/suptower/beybladex-elo-system/actions/workflows/lint.yml/badge.svg)](https://github.com/suptower/beybladex-elo-system/actions/workflows/lint.yml)
[![Copilot code review](https://github.com/suptower/beybladex-elo-system/actions/workflows/copilot-pull-request-reviewer/copilot-pull-request-reviewer/badge.svg)](https://github.com/suptower/beybladex-elo-system/actions/workflows/copilot-pull-request-reviewer/copilot-pull-request-reviewer)
[![pages-build-deployment](https://github.com/suptower/beybladex-elo-system/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/suptower/beybladex-elo-system/actions/workflows/pages/pages-build-deployment)

Lightweight tools for computing and publishing Elo ratings and charts for Beyblade tournaments.

## Purpose

Track match results, compute Elo ratings, generate charts, and export leaderboards.

## Repository Structure

```
beybladex-elo-system/
├── src/                    # Core Python modules
│   ├── beyblade_elo.py         # Elo calculation logic
│   ├── advanced_stats.py       # Power index and advanced metrics
│   ├── simulation.py           # Tournament simulation
│   ├── matchup_predictor.py    # Match prediction tools
│   ├── meta_balance.py         # Meta analysis tools
│   ├── synergy_heatmaps.py     # Part synergy analysis
│   ├── upset_analysis.py       # Upset detection and analysis
│   ├── gen_plots.py            # Plot generation orchestrator
│   ├── sheets_upload.py        # Google Sheets integration
│   ├── export_leaderboard_pdf.py # PDF export
│   └── visualization/          # Visualization modules
│       ├── elo_density_map.py
│       ├── meta_landscape.py
│       ├── tier_flow.py
│       └── heatmaps.py
├── data/                       # Source data and generated CSVs
│   ├── beys.csv                # Beyblade registry
│   ├── matches.csv             # Match records
│   ├── leaderboard.csv         # Current rankings
│   ├── elo_history.csv         # Historical Elo changes
│   └── leaderboards/           # Tournament snapshots
├── docs/                       # GitHub Pages frontend
│   ├── index.html              # Main page
│   ├── styles.css              # Stylesheet
│   ├── *.js                    # JavaScript modules
│   ├── data/                   # Frontend data (CSV/JSON)
│   ├── plots/                  # Generated visualizations
│   ├── schema/                 # Data schemas
│   └── tournament-charts/      # Tournament standings
├── tests/                      # Pytest test suite
├── config/                     # Configuration files
├── templates/                  # CSV templates
├── archive/                    # Archived/backup data
├── .github/workflows/          # CI/CD workflows
├── update.py                   # Main update pipeline
├── requirements.txt            # Python dependencies
├── roadmap.md                  # Project roadmap
└── README.md                   # This file
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run the Full Pipeline

```bash
python update.py
```

### Command Line Options

```bash
python update.py                    # Run full pipeline (Elo, stats, plots)
python update.py --skip-diagrams    # Skip plot generation
python update.py --pdf              # Generate PDF leaderboard
python update.py --upload           # Upload to Google Sheets
```

### Simulate Tournaments

```bash
# Single elimination tournament with 8 random participants
python src/simulation.py -n 8 -f single-elimination

# Round-robin tournament with specific Beyblades
python src/simulation.py -f round-robin -b FoxBrush ImpactDrake DranSword

# Append simulated matches to matches.csv
python src/simulation.py -n 16 -f single-elimination --append
```

## Data Files

### Input Data (data/)

| File | Description |
|------|-------------|
| `beys.csv` | Registry of all Beyblades |
| `matches.csv` | Match records (winner, loser, scores, timestamp) |
| `rounds.csv` | Round-level match data |

### Generated Data (data/)

| File | Description |
|------|-------------|
| `leaderboard.csv` | Current rankings with stats |
| `advanced_leaderboard.csv` | Extended metrics |
| `elo_history.csv` | Chronological Elo changes |
| `elo_timeseries.csv` | Elo over time per Beyblade |
| `bey_counters.csv` | Counter matchup data |

## Google Sheets Integration

1. Create a service account in Google Cloud Console
2. Save credentials as `service_account.json` in the repository root
3. Share the target Google Sheet with the service account email
4. Run `python update.py --upload`

## Development

### Running Tests

```bash
python -m pytest tests/ -v
```

### Linting

```bash
python -m flake8 .
```

## Contributing

See [roadmap.md](roadmap.md) for planned features and improvements.

