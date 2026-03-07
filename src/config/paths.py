"""
Centralised path registry for the BeybladeX ELO system.

All canonical input and output paths are defined here, anchored relative to
the repository root via ``__file__``.  Every source module should import the
constants it needs from this module instead of hard-coding path strings.

Usage example::

    from src.config.paths import MATCHES_CSV, ELO_HISTORY_CSV, LEADERBOARD_DIR
"""

import os

# ---------------------------------------------------------------------------
# Repository root – resolved once from this file's location so it works
# regardless of the current working directory.
#   src/config/paths.py  →  src/config/  →  src/  →  repo root
# ---------------------------------------------------------------------------
_HERE = os.path.abspath(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))

# ---------------------------------------------------------------------------
# Top-level directories
# ---------------------------------------------------------------------------
DOCS_DIR   = os.path.join(REPO_ROOT, "docs")
DATA_DIR   = os.path.join(DOCS_DIR,  "data")
PLOTS_DIR  = os.path.join(DOCS_DIR,  "plots")
CONFIG_DIR = os.path.join(REPO_ROOT, "config")

# ---------------------------------------------------------------------------
# Data sub-directories
# ---------------------------------------------------------------------------
MATCHES_DIR               = os.path.join(DATA_DIR, "matches")
BEYS_DIR                  = os.path.join(DATA_DIR, "beys")
ELO_DIR                   = os.path.join(DATA_DIR, "elo")
LEADERBOARD_DIR           = os.path.join(DATA_DIR, "leaderboard")
LEADERBOARD_SNAPSHOTS_DIR = os.path.join(DATA_DIR, "leaderboard_snapshots")
ANALYTICS_DIR             = os.path.join(DATA_DIR, "analytics")
SEASON_DIR                = os.path.join(DATA_DIR, "season")
TOURNAMENTS_DIR           = os.path.join(DATA_DIR, "tournaments")

# ---------------------------------------------------------------------------
# Plot sub-directories
# ---------------------------------------------------------------------------
PLOTS_ELO_DIR                      = os.path.join(PLOTS_DIR, "elo")
PLOTS_ELO_INTERACTIVE_DIR          = os.path.join(PLOTS_ELO_DIR, "interactive")
PLOTS_ELO_INTERACTIVE_DARK_DIR     = os.path.join(PLOTS_ELO_INTERACTIVE_DIR, "dark")
PLOTS_POSITIONS_DIR                = os.path.join(PLOTS_DIR, "positions")
PLOTS_POSITIONS_INTERACTIVE_DIR    = os.path.join(PLOTS_POSITIONS_DIR, "interactive")
PLOTS_POSITIONS_INTERACTIVE_DARK_DIR = os.path.join(PLOTS_POSITIONS_INTERACTIVE_DIR, "dark")
PLOTS_SEASON_DIR                   = os.path.join(PLOTS_DIR, "season")
PLOTS_SEASON_ADVANCED_DIR          = os.path.join(PLOTS_SEASON_DIR, "advanced")
PLOTS_SEASON_COMPARISON_DIR        = os.path.join(PLOTS_SEASON_DIR, "comparison")

# Private-mode plots live outside docs/ so they are never published to GitHub Pages
PLOTS_PRIVATE_DIR = os.path.join(REPO_ROOT, "plots", "private")

# ---------------------------------------------------------------------------
# Config files
# ---------------------------------------------------------------------------
FINISH_WEIGHTS_JSON = os.path.join(CONFIG_DIR, "finish_weights.json")

# ---------------------------------------------------------------------------
# Matches files
# ---------------------------------------------------------------------------
MATCHES_CSV              = os.path.join(MATCHES_DIR, "matches.csv")
ROUNDS_CSV               = os.path.join(MATCHES_DIR, "rounds.csv")
MATCHES_WITH_ROUNDS_JSON = os.path.join(MATCHES_DIR, "matches_with_rounds.json")
PRIVATE_MATCHES_CSV      = os.path.join(MATCHES_DIR, "private_matches.csv")
FIXTURES_CSV             = os.path.join(MATCHES_DIR, "fixtures.csv")

# ---------------------------------------------------------------------------
# Beys files
# ---------------------------------------------------------------------------
BEYS_CSV       = os.path.join(BEYS_DIR, "beys.csv")
BEYS_DATA_JSON = os.path.join(BEYS_DIR, "beys_data.json")

# ---------------------------------------------------------------------------
# ELO files
# ---------------------------------------------------------------------------
ELO_HISTORY_CSV            = os.path.join(ELO_DIR, "elo_history.csv")
ELO_TIMESERIES_CSV         = os.path.join(ELO_DIR, "elo_timeseries.csv")
ELO_METRICS_JSON           = os.path.join(ELO_DIR, "elo_metrics.json")
ELO_TUNE_RESULTS_CSV       = os.path.join(ELO_DIR, "elo_tune_results.csv")
ELO_METRICS_V1_JSON        = os.path.join(ELO_DIR, "elo_metrics_v1.json")
ELO_METRICS_V2_JSON        = os.path.join(ELO_DIR, "elo_metrics_v2.json")
PRIVATE_ELO_HISTORY_CSV    = os.path.join(ELO_DIR, "private_elo_history.csv")
PRIVATE_ELO_TIMESERIES_CSV = os.path.join(ELO_DIR, "private_elo_timeseries.csv")

# ---------------------------------------------------------------------------
# Leaderboard files
# ---------------------------------------------------------------------------
LEADERBOARD_CSV                    = os.path.join(LEADERBOARD_DIR, "leaderboard.csv")
ADVANCED_LEADERBOARD_CSV           = os.path.join(LEADERBOARD_DIR, "advanced_leaderboard.csv")
ADVANCED_LEADERBOARD_DROP_ATTACK_CSV = os.path.join(LEADERBOARD_DIR, "advanced_leaderboard_drop_attack.csv")
ADVANCED_LEADERBOARD_COMBINED_CSV  = os.path.join(LEADERBOARD_DIR, "advanced_leaderboard_combined.csv")
LEADERBOARD_ALL_ARENAS_CSV         = os.path.join(LEADERBOARD_DIR, "leaderboard_all_arenas.csv")
PRIVATE_LEADERBOARD_CSV            = os.path.join(LEADERBOARD_DIR, "private_leaderboard.csv")

# ---------------------------------------------------------------------------
# Analytics files
# ---------------------------------------------------------------------------
RPG_STATS_JSON           = os.path.join(ANALYTICS_DIR, "rpg_stats.json")
RPG_STATS_CSV            = os.path.join(ANALYTICS_DIR, "rpg_stats.csv")
STADIUM_ANALYTICS_JSON   = os.path.join(ANALYTICS_DIR, "stadium_analytics.json")
UPSET_ANALYSIS_CSV       = os.path.join(ANALYTICS_DIR, "upset_analysis.csv")
UPSET_MATCHES_CSV        = os.path.join(ANALYTICS_DIR, "upset_matches.csv")
BEY_COUNTERS_CSV         = os.path.join(ANALYTICS_DIR, "bey_counters.csv")
META_BALANCE_JSON        = os.path.join(ANALYTICS_DIR, "meta_balance.json")
MATCHUP_MATRIX_JSON      = os.path.join(ANALYTICS_DIR, "matchup_matrix.json")
ARCHETYPE_ANALYTICS_JSON = os.path.join(ANALYTICS_DIR, "archetype_analytics.json")
RECOMMENDED_MATCHES_JSON = os.path.join(ANALYTICS_DIR, "recommended_matches.json")
MILESTONES_JSON          = os.path.join(ANALYTICS_DIR, "milestones.json")
POSITION_TIMESERIES_CSV         = os.path.join(ANALYTICS_DIR, "position_timeseries.csv")
PRIVATE_POSITION_TIMESERIES_CSV = os.path.join(ANALYTICS_DIR, "private_position_timeseries.csv")

# ---------------------------------------------------------------------------
# Season files
# ---------------------------------------------------------------------------
SEASON_DATA_JSON       = os.path.join(SEASON_DIR, "season_data.json")
SEASON_STATS_JSON      = os.path.join(SEASON_DIR, "season_statistics.json")
SEASON_COMPARISON_JSON = os.path.join(SEASON_DIR, "season_comparison.json")

# ---------------------------------------------------------------------------
# Tournament files
# ---------------------------------------------------------------------------
TOURNAMENTS_JSON         = os.path.join(TOURNAMENTS_DIR, "tournaments.json")
TOURNAMENT_BRACKETS_JSON = os.path.join(TOURNAMENTS_DIR, "tournament_brackets.json")

# ---------------------------------------------------------------------------
# Miscellaneous data files
# ---------------------------------------------------------------------------
CHANGELOG_JSON = os.path.join(DATA_DIR, "changelog.json")
VERSION_JS     = os.path.join(DOCS_DIR,  "version.js")
