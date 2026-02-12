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
│   ├── season_manager.py       # Season management and league tables
│   ├── season_cup.py           # Season Cup double-elimination system
│   ├── season_processing.py    # Season data processing pipeline
│   ├── simulation.py           # Tournament simulation
│   ├── elo_simulator.py        # Elo simulation tools
│   ├── gen_plots.py            # Plot generation orchestrator
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
| `seasons.json` | Season metadata and tier assignments |
| `season_data.json` | Complete season archives with league tables |
| `stadium_analytics.json` | **NEW:** Stadium-specific statistics and analytics |
| `leaderboards/` | Per-tournament leaderboard snapshots |
| `leaderboard_snapshots/` | **NEW:** Per-match historical leaderboard snapshots (leaderboard_0000.csv to leaderboard_NNNN.csv) |

**Note:** All scripts read from and write to `./docs/data/` only. No data is stored in the repository root.

## Historical Leaderboard Snapshots (Time Travel Mode)

The system now generates **historical leaderboard snapshots** after every single match, allowing you to view the complete evolution of rankings and statistics at any point in time.

### Features

- **Per-Match Snapshots**: A leaderboard snapshot is saved after each match (0 to N)
- **Complete Statistics**: Each snapshot includes all stats - rank, ELO, matches, wins, losses, winrate, points for/against, differentials, position delta, ELO delta
- **Interactive UI**: The leaderboard page includes a "Time Travel Mode" toggle with:
  - Smooth slider to scrub through match history
  - Prev/Next buttons for step-by-step navigation
  - Direct input field to jump to specific matches
  - "Latest" button to return to current leaderboard
  - Keyboard shortcuts (arrow keys) for navigation
- **Responsive Design**: Fully optimized for both desktop and mobile devices
- **Real-time Updates**: Leaderboard updates instantly when changing the match index

### File Format

Snapshots are stored as zero-padded CSV files:
- `leaderboard_0000.csv` - Initial state (before any matches)
- `leaderboard_0001.csv` - After match 1
- `leaderboard_0002.csv` - After match 2
- ...
- `leaderboard_0224.csv` - After match 224 (latest)

### Usage

1. Visit the leaderboard page on the website
2. Enable "Time Travel Mode" using the checkbox
3. Use the slider, buttons, or input field to navigate through match history
4. View how rankings and statistics evolved over time

### Technical Details

- Snapshots are generated during the ELO pipeline (`beyblade_elo.py`)
- Deltas (position and ELO changes) are calculated relative to the previous match
- The snapshot generation is deterministic and reproducible
- Compatible with existing data formats (no breaking changes)

## Stadium Statistics & Arena Analysis

The system now includes **comprehensive stadium-specific analytics** to analyze how different arenas affect performance, archetypes, finishes, and the competitive meta.

### Features

- **Stadium Overview**: General statistics per stadium including total matches, average scores, match distribution
- **Bey Performance per Stadium**: Win rates, ELO changes, point differentials for each Bey in each arena
- **Archetype Effectiveness**: Archetype win rates and matchup performance per stadium
- **Finish Type Statistics**: Distribution of spin/burst/pocket/extreme finishes per arena
- **ELO Behavior Analysis**: ELO volatility, upset frequency, dominant win frequency per stadium
- **Comparative Analysis**: Stadium-to-stadium comparison showing meta shifts

### Data Model

All matches include an `arena` column in `matches.csv`:
- Currently supported: `Xtreme` (Xtreme Stadium), `Drop Attack` (Drop Attack Beystadium)
- Default: `Xtreme` for backward compatibility with existing data

### Generated Data

Stadium analytics are generated automatically as part of the update pipeline:
- `docs/data/stadium_analytics.json` - Complete stadium-specific statistics

### Viewing Stadium Statistics

Visit the **Stadium Stats** page on the website to view:
- Interactive stadium selector
- Comprehensive statistics dashboards
- Visual charts for finish type distribution
- Top/worst performers per stadium
- Archetype effectiveness tables
- Comparative analysis between stadiums

The stadium statistics module runs automatically with:
```bash
python update.py
```

## Arena-Specific ELO Ratings

The system supports **arena-specific ELO ratings** to evaluate Bey performance independently per stadium. This feature allows tracking of how Beys perform in different competitive environments while maintaining the integrity of seasonal rankings.

### Overview

Each Bey maintains multiple parallel ELO ratings:
- **Global/Season ELO** (Xtreme Stadium) - Used for competitive season rankings
- **Arena-Specific ELOs** - Independent ratings per stadium type

### Key Features

- **Separate ELO per Arena**: Each Bey has independent ELO ratings for Xtreme Stadium and Drop Attack Beystadium
- **Season Match Integrity**: All season/competitive matches update Xtreme ELO only, regardless of arena played
- **Exhibition Match Flexibility**: Non-season matches update the arena-specific ELO where they were played
- **Backward Compatibility**: Existing matches without arena info are treated as Xtreme Stadium

### ELO Update Rules

#### Exhibition / Non-Season Matches
- Update **only the ELO of the arena used**
- Example: Match in Drop Attack → Update `elo_drop_attack` only
- Xtreme ELO remains unchanged

#### Season / Competitive Matches
- Always use and update **Xtreme ELO only**
- Even if the match was played in another arena
- Ensures season integrity, stable promotion/relegation logic, and historical consistency
- Applies to: `season`, `relegation`, and `season_cup` match types

### Data Files

The system generates separate leaderboards:
- `leaderboard.csv` - Default (Xtreme Stadium / Season ELO)
- `leaderboard_xtreme.csv` - Xtreme Stadium specific rankings
- `leaderboard_drop_attack.csv` - Drop Attack Beystadium specific rankings
- `leaderboard_all_arenas.csv` - Combined view with all arena ELOs

### UI Integration

**Leaderboard Page:**
- Arena selector dropdown to switch between stadiums
- Default view shows Xtreme Stadium (Season/Global ELO)
- Combined view shows ELO and stats for all arenas side-by-side

**Quick Entry:**
- Mandatory arena selector when creating new matches
- Automatically applies arena setting to all matches in a tournament
- Defaults to Xtreme Stadium for backward compatibility

### Match Data Format

The `arena` field in `matches.csv`:
```csv
MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,MatchType,SeasonID,Tier,Matchday,arena
M0001,2025-01-30,BeyA,BeyB,4,2,exhibition,,,,Xtreme
M0002,2025-01-30,BeyC,BeyD,4,1,season,S1,1,1,Xtreme
M0003,2025-01-30,BeyE,BeyF,3,4,exhibition,,,,Drop Attack
```

### Implementation Details

Arena-specific ELO tracking is implemented in `src/beyblade_elo.py`:
- `normalize_arena_name()` - Ensures consistent arena naming
- `update_elo()` - Handles arena-specific and match-type-based ELO updates
- Independent stats tracking per arena (wins, losses, matches, points)

### Testing

Comprehensive unit tests in `tests/test_beyblade_elo.py`:
- Arena name normalization
- Exhibition match updates correct arena ELO
- Season matches always update Xtreme ELO
- Independent ratings across arenas
- Relegation and season cup match handling

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

## Tiered Seasonal League System

The system supports a tiered seasonal league format designed to prioritize statistical reliability, fair ranking, and long-term progression.

### Overview

- **4 Tiers** of 10 Beyblades each (40 total)
- **Single round-robin** within each tier (9 matches per Beyblade per season)
- **180 total league matches** per season
- **Promotion/relegation** between tiers
- **Post-season cup** tournament (double-elimination)

### Season Structure

**Tier Assignment:**
- At season start, Beyblades are assigned to tiers based on current ELO rankings
- Tier I: Top 10 (highest ELO)
- Tier II: Places 11-20
- Tier III: Places 21-30
- Tier IV: Places 31-40 (lowest ELO)

**League Matches:**
- Each Beyblade plays every other Beyblade in its tier once
- Tagged with `match_type=season` in matches.csv

**Season Points:**
- Win: 3 points
- Dominant Win (4-0, 5-0, 6-0): 4 points
- Loss: 0 points

**League Table Ranking:**
1. Season Points
2. Point Difference (points for - points against)
3. Total Points Scored
4. Head-to-Head Result
5. ELO Rating

### Promotion & Relegation

**Automatic:**
- Top 2 from Tiers II-IV: Promoted to tier above
- Bottom 2 from Tiers I-III: Relegated to tier below

**Relegation Matches:**
- 8th place (higher tier) vs 3rd place (lower tier)
- Winner plays in higher tier next season
- Tagged with `match_type=relegation`

### Season Cup

**Qualification:**
- Tier I: Top 4
- Tier II: Top 2
- Tier III: Top 1
- Tier IV: Top 1
- Total: 8 qualified Beyblades

**Format:**
- Double-elimination tournament
- Tagged with `match_type=season_cup`

**Titles:**
- **Season League Champion**: 1st place in Tier I (consistency-based)
- **Season Cup Winner**: Tournament winner (peak performance)

### Match Type Field

The `matches.csv` file now supports an optional `MatchType` column:

- `exhibition` (default): All existing matches and tournaments
- `season`: League matches within a tier
- `relegation`: Promotion/relegation decision matches
- `season_cup`: Post-season cup tournament matches

If `MatchType` is missing, matches are treated as `exhibition` for full backwards compatibility.

### Initializing a New Season

Use the `init_season.py` utility to initialize a new season from the current leaderboard:

```bash
# Initialize a season (creates tier assignments)
python src/init_season.py S1

# Initialize and generate match schedule templates
python src/init_season.py S1 --generate-schedule

# Specify custom paths
python src/init_season.py S2 --leaderboard ./custom/leaderboard.csv --data-dir ./data
```

The utility will:
1. Read current ELO rankings from `leaderboard.csv`
2. Assign all 40 Beys to 4 tiers based on ELO
3. Save tier assignments to `seasons.json`
4. Optionally generate match schedule CSV templates for each tier

**Generated Schedule Format:**
- Ready-to-use CSV templates with all matchups
- Pre-filled with MatchType, SeasonID, Tier, and Matchday
- Simply add dates and results, then import to `matches.csv`

### Season Data Processing

Process season data after adding season matches:

```bash
# Process all seasons
python src/season_processing.py

# Process specific season
python src/season_processing.py --season S1
```

Season data is automatically processed as part of the main pipeline:

```bash
python update.py  # Includes season processing
```

### Season Pages

Visit the Seasons section on the website to view:
- Season archive and history
- League tables for all tiers
- Promotion/relegation results
- Relegation match outcomes
- Season Cup brackets
- Matchday schedules

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

