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
│   ├── rpg_stats.py            # RPG-style stats and archetypes
│   ├── archetype_analytics.py  # Archetype effectiveness analysis
│   ├── parts_stats.py          # Individual part statistics
│   ├── upset_analysis.py       # Upset detection and analysis
│   ├── meta_balance.py         # Meta analysis tools
│   ├── synergy_heatmaps.py     # Part synergy analysis
│   ├── matchup_matrix.py       # Matchup matrix generation
│   ├── matchup_predictor.py    # Match prediction tools
│   ├── counter_checker.py      # Counter matchup analysis
│   ├── combo_explorer.py       # Combination explorer data
│   ├── milestones.py           # Statistical records and achievements
│   ├── recommended_matches.py  # Match recommendation engine
│   ├── simulation.py           # Tournament simulation
│   ├── elo_simulator.py        # Elo simulation tools
│   ├── gen_plots.py            # Plot generation orchestrator
│   ├── plot_positions.py       # Position plot generation
│   ├── plot_styles.py          # Plot styling utilities
│   ├── generate_version.py     # Git-based version generation
│   ├── sheets_upload.py        # Google Sheets integration
│   ├── export_leaderboard_pdf.py # PDF export
│   ├── filter_csv.py           # CSV filtering utility
│   ├── merge_rounds.py         # Round data merging
│   ├── offset_matchid.py       # Match ID offset utility
│   ├── simulation_cl_format.py # Simulation CLI formatting
│   └── visualization/          # Visualization modules
│       ├── elo_density_map.py
│       ├── meta_landscape.py
│       ├── tier_flow.py
│       ├── heatmaps.py
│       ├── advanced_visualizations.py
│       ├── combined_elo_trends_top5.py
│       └── interactive_elo_trends.py
├── docs/                       # GitHub Pages frontend
│   ├── index.html              # Main page
│   ├── styles.css              # Stylesheet
│   ├── *.js                    # JavaScript modules
│   ├── data/                   # All generated data (CSV/JSON)
│   │   ├── beys.csv            # Beyblade registry
│   │   ├── matches.csv         # Match records
│   │   ├── leaderboard.csv     # Current rankings
│   │   ├── elo_history.csv     # Historical Elo changes
│   │   ├── leaderboards/       # Tournament snapshots
│   │   └── *.json              # Various data files
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
└── README.md                   # This file
```

**Note:** All data files are now stored in `./docs/data/` to avoid duplication. All scripts read from and write to this single location.

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Run the Full Pipeline

```bash
python update.py
```

This will:
1. Generate version information from Git (commit count + hash)
2. Calculate ELO ratings and advanced statistics
3. Generate analysis modules (RPG stats, archetypes, upsets, meta balance, synergy, counters, combo explorer, milestones, recommended matches, matchup matrix)
4. Create visualizations and plots

### Command Line Options

```bash
python update.py                    # Run full pipeline (stats + analysis + plots)
python update.py --skip-plots       # Skip plot generation (faster updates)
python update.py --stats-only       # Only run core statistics (ELO + Advanced Stats)
python update.py --plots-only       # Only generate visualizations
python update.py --pdf              # Include PDF leaderboard generation
python update.py --upload           # Include Google Sheets upload
python update.py --verbose          # Show detailed output from each script
python update.py --all              # Explicitly run complete pipeline (same as default)
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

**All data files are stored in `./docs/data/` to serve the GitHub Pages site.**

### Input Data (docs/data/)

| File | Description |
|------|-------------|
| `beys.csv` | Registry of all Beyblades |
| `matches.csv` | Match records (winner, loser, scores, timestamp) |
| `rounds.csv` | Round-level match data |

### Generated Data (docs/data/)

| File | Description |
|------|-------------|
| `leaderboard.csv` | Current rankings with stats |
| `advanced_leaderboard.csv` | Extended metrics |
| `elo_history.csv` | Chronological Elo changes |
| `elo_timeseries.csv` | Elo over time per Beyblade |
| `position_timeseries.csv` | Position rankings over time |
| `bey_counters.csv` | Counter matchup data |
| `rpg_stats.csv` | RPG-style stats (CSV format) |
| `rpg_stats.json` | RPG-style stats and archetypes |
| `archetype_analytics.json` | Archetype effectiveness metrics |
| `synergy_data.json` | Part synergy heatmap data |
| `meta_balance.json` | Meta health analysis |
| `matchup_matrix.json` | Head-to-head matchup matrix |
| `combo_data.json` | Combination explorer data |
| `parts_stats.json` | Individual part statistics |
| `tournaments.json` | Tournament metadata |
| `milestones.json` | Statistical records and achievements |
| `recommended_matches.json` | Match recommendations |
| `upset_analysis.csv` | Upset match analysis |
| `upset_matches.csv` | Individual upset records |
| `matches_with_rounds.json` | Matches with round-level data |
| `beys_data.json` | Beyblade data in JSON format |
| `leaderboards/` | Per-tournament leaderboard snapshots |

**Note:** All scripts read from and write to `./docs/data/` only. No data is stored in the repository root.

## Automatic Site Versioning

The website displays an automatic version number in the footer of every page, based on Git commit history. The version is automatically updated on every commit without manual intervention.

### How It Works

1. **Version Generation**: The `src/generate_version.py` script extracts:
   - Total commit count (used as version number)
   - Short commit hash (7 characters)
   - Full commit hash and timestamp

2. **JavaScript Integration**: Version info is written to `docs/version.js` and automatically displayed in all page footers via `docs/version-display.js`

3. **Format**: Version strings appear as: `Version [count] · [hash]`
   - Example: `Version 142 · a3f92c1`

4. **Pipeline Integration**: Version generation runs automatically as the first step in `update.py`

### Manual Version Generation

To regenerate the version file manually:

```bash
python src/generate_version.py
```

This creates/updates `docs/version.js` with current Git state.

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

Contributions are welcome! Please ensure that:
- Code follows existing style conventions
- Tests pass before submitting changes
- Documentation is updated for new features

