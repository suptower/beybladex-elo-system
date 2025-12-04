# Update Pipeline Documentation

This document describes the unified update pipeline for the Beyblade X ELO System.

## Overview

The `update.py` script serves as the **single entry point** to regenerate all dependent data in the system. It orchestrates the execution of all processing scripts in the correct dependency order.

## Quick Start

```bash
# Run the full pipeline (stats + analysis + plots)
python update.py

# Fast update (skip plots)
python update.py --skip-plots

# Only regenerate plots
python update.py --plots-only
```

## Pipeline Stages

The pipeline is organized into four main stages that run in order:

### Stage 1: Core Statistics

| Script | Description | Output Files |
|--------|-------------|--------------|
| `beyblade_elo.py` | ELO calculations for all matches | `leaderboard.csv`, `elo_history.csv`, `elo_timeseries.csv`, `position_timeseries.csv` |
| `advanced_stats.py` | Power Index and extended statistics | `advanced_leaderboard.csv` |

### Stage 2: Analysis Modules

| Script | Description | Output Files |
|--------|-------------|--------------|
| `rpg_stats.py` | RPG-style stats (Attack, Defense, Stamina, Control, Meta Impact) and archetype detection | `rpg_stats.json`, `rpg_stats.csv` |
| `upset_analysis.py` | Upset analysis and Giant Killer scores | `upset_analysis.csv`, `upset_matches.csv` |
| `meta_balance.py` | Meta health analysis and balance metrics | `meta_balance.json` |
| `synergy_heatmaps.py` | Part synergy calculations | `synergy_data.json` |
| `counter_checker.py` | Bey counter matchup data | `bey_counters.csv` |
| `combo_explorer.py` | Combo exploration data | `combo_data.json` |

### Stage 3: Visualizations (runs by default)

| Script | Description | Output Files |
|--------|-------------|--------------|
| `gen_plots.py` | ELO trends, heatmaps, bar charts | `docs/plots/` directory |
| `plot_positions.py` | Position timeline plots | `docs/plots/positions/` directory |

### Stage 4: Exports (Optional)

| Script | Description | Output Files |
|--------|-------------|--------------|
| `export_leaderboard_pdf.py` | PDF leaderboard export | `leaderboard.pdf` |
| `sheets_upload.py` | Google Sheets synchronization | (external) |

## Command Line Options

| Flag | Short | Description |
|------|-------|-------------|
| `--all` | `-a` | Run complete pipeline (same as default, for clarity) |
| `--stats-only` | | Only run core statistics (ELO + Advanced Stats) |
| `--plots-only` | | Only run visualization/plot generation |
| `--skip-plots` | `-s` | Skip plot generation (faster updates) |
| `--upload` | `-u` | Upload data to Google Sheets after processing |
| `--pdf` | `-p` | Generate PDF leaderboard after processing |
| `--verbose` | `-v` | Show detailed output from each script |

## Usage Examples

### Standard Update (Recommended)

Run the full pipeline including plots:

```bash
python update.py
```

This runs all core statistics, analysis modules, and plot generation.

### Fast Update (Skip Plots)

When you don't need fresh plots and want a faster update:

```bash
python update.py --skip-plots
```

### Quick Stats Only

For quick testing or when you only need updated ELO ratings:

```bash
python update.py --stats-only
```

### Regenerate Plots Only

If you've made style changes and need to regenerate plots:

```bash
python update.py --plots-only
```

### Full Release Pipeline

For a complete release with PDF and Google Sheets sync:

```bash
python update.py --all --pdf --upload
```

## Dependency Graph

The scripts have the following dependency relationships:

```
matches.csv, rounds.csv
        │
        ▼
┌──────────────────┐
│  beyblade_elo.py │  ───► leaderboard.csv, elo_history.csv, elo_timeseries.csv
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ advanced_stats.py│  ───► advanced_leaderboard.csv
└────────┬─────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
rpg_stats  upset_analysis  meta_balance  synergy_heatmaps
    │         │            │            │
    └────┬────┴────────────┴────────────┘
         │
         ▼
┌──────────────────┐
│  combo_explorer  │  ───► combo_data.json
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    gen_plots     │  ───► docs/plots/
│  plot_positions  │
└──────────────────┘
```

## Adding New Scripts

To add a new analysis script to the pipeline:

1. Create your script in the `src/` directory
2. Add the script path constant at the top of `update.py`:
   ```python
   SCRIPT_YOUR_MODULE = "./src/your_module.py"
   ```
3. Add the script execution to the appropriate function:
   - `run_core_stats()` - for fundamental data generation
   - `run_analysis_modules()` - for derived analysis
   - `run_visualizations()` - for plot generation
   - `run_exports()` - for external exports

4. Use the `run_script()` helper:
   ```python
   success, duration = run_script(
       SCRIPT_YOUR_MODULE,
       "Your Module Description",
       verbose=verbose
   )
   results.append(("Your Module", success, duration))
   ```

## Error Handling

The pipeline tracks success/failure for each step and provides a summary at the end:

- ✓ indicates successful completion
- ✗ indicates a failure

Failed steps will show error output, and the pipeline continues with remaining steps to allow partial updates.

## Performance Notes

Typical execution times:

| Mode | Duration |
|------|----------|
| `--stats-only` | ~0.5s |
| Default (no plots) | ~1s |
| `--all` (with plots) | ~60s |

Plot generation is the most time-consuming step due to creating individual charts for each Beyblade.

## Troubleshooting

### Script Not Found

If you see "script not found" errors, verify:
- You're running from the repository root directory
- The script path in `update.py` is correct

### Import Errors

If scripts fail with import errors:
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check that the `src/` directory is accessible

### Data Consistency

If you notice inconsistent data:
1. Run the full pipeline: `python update.py --all`
2. Check input files in `data/` directory
3. Verify `matches.csv` and `rounds.csv` are properly formatted
