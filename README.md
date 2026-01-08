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
│   ├── build_manager.py        # Build management (stock + custom combos)
│   ├── build_elo.py            # Build-aware Elo calculation
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
│   │   ├── builds.json         # Build registry (stock + custom)
│   │   ├── matches.csv         # Match records
│   │   ├── leaderboard.csv     # Current rankings (blade level)
│   │   ├── build_leaderboard.csv # Build-level rankings
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

### Non-Stock Beyblade Combinations (Custom Builds)

The system now supports tracking **custom Beyblade builds** (non-stock Blade + Ratchet + Bit combinations) alongside stock configurations. This enables analysis of custom competitive builds while maintaining 100% backward compatibility.

#### Features

- **Build-Level Tracking**: Each unique combination (e.g., `DranDagger_5-80_Elevate`) has its own ELO rating and statistics
- **Blade Aggregation**: Blade-level stats aggregate all builds of that blade using weighted averages
- **Backward Compatible**: Stock-only workflows require no changes - BuildA/BuildB columns are optional
- **Auto-Registration**: Custom builds are automatically registered when first used in a match
- **Status Tracking**: Builds are marked as active (≥5 matches), provisional (<5), or retired (>90 days unused)

#### Usage

**Build Management:**
```bash
# Initialize stock builds from beys_data.json
python src/build_manager.py --init

# View all builds
python src/build_manager.py --list

# View builds for a specific blade
python src/build_manager.py --list --blade DranDagger

# Create a custom build
python src/build_manager.py --create DranDagger 5-80 Elevate

# Show statistics
python src/build_manager.py --stats
```

**Build-Aware ELO Calculation:**
```bash
# Run with build support (automatically uses builds.json)
python src/build_elo.py --mode official

# Specify custom paths
python src/build_elo.py --mode official \
    --matches ./docs/data/matches.csv \
    --leaderboard ./docs/data/leaderboard.csv \
    --build-leaderboard ./docs/data/build_leaderboard.csv
```

**Match CSV Format (Extended):**

Add optional `BuildA` and `BuildB` columns to `matches.csv`:

```csv
MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,BuildA,BuildB
M0001,2025-09-07,DranDagger,FoxBrush,4,2,,
M0002,2025-12-15,DranDagger,ImpactDrake,5,1,DranDagger_5-80_Elevate,
M0003,2025-12-16,PhoenixWing,DranDagger,3,4,PhoenixWing_9-60_Rush,DranDagger_5-80_Elevate
```

**Rules:**
- If `BuildA`/`BuildB` is empty → use stock build for that blade
- If specified → use the custom build (format: `{Blade}_{Ratchet}_{Bit}`)
- Blade name in build ID must match the `BeyA`/`BeyB` column

**Output Files:**
- `builds.json`: Registry of all builds (stock + custom)
- `build_leaderboard.csv`: Rankings at build level
- `leaderboard.csv`: Rankings at blade level (aggregated from builds)

#### Design Documentation

For detailed design decisions, ELO strategy, and migration plan, see:
- [Non-Stock Combos Design Document](docs/NON_STOCK_COMBOS_DESIGN.md)
- [Builds Schema](docs/schema/builds_schema.json)

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

