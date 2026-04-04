/**
 * Centralised data-path registry for the BeybladeX frontend.
 *
 * All paths are relative to the docs/ root (the site root served by GitHub
 * Pages), so they work from every HTML page regardless of nesting level.
 *
 * Keep this file in sync with src/config/paths.py whenever the output
 * directory layout changes.
 *
 * Usage (after loading this script):
 *   fetch(DATA_PATHS.MATCHES_CSV)
 *   fetch(DATA_PATHS.eloTimeseries('drop_attack'))
 *   fetch(DATA_PATHS.seasonStats('S3'))
 */

const DATA_PATHS = Object.freeze({
    // -----------------------------------------------------------------------
    // Matches
    // -----------------------------------------------------------------------
    MATCHES_CSV:              'data/matches/matches.csv',
    ROUNDS_CSV:               'data/matches/rounds.csv',
    MATCHES_WITH_ROUNDS_JSON: 'data/matches/matches_with_rounds.json',
    FIXTURES_CSV:             'data/matches/fixtures.csv',

    // -----------------------------------------------------------------------
    // Beys
    // -----------------------------------------------------------------------
    BEYS_CSV:       'data/beys/beys.csv',
    BEYS_DATA_JSON: 'data/beys/beys_data.json',

    // -----------------------------------------------------------------------
    // ELO
    // -----------------------------------------------------------------------
    ELO_HISTORY_CSV:     'data/elo/elo_history.csv',
    ELO_METRICS_JSON:    'data/elo/elo_metrics.json',
    ELO_METRICS_V1_JSON: 'data/elo/elo_metrics_v1.json',
    ELO_METRICS_V2_JSON: 'data/elo/elo_metrics_v2.json',

    // -----------------------------------------------------------------------
    // Leaderboard (static variants)
    // -----------------------------------------------------------------------
    LEADERBOARD_CSV:                      'data/leaderboard/leaderboard.csv',
    LEADERBOARD_V1_CSV:                   'data/leaderboard/leaderboard_v1.csv',
    LEADERBOARD_V2_CSV:                   'data/leaderboard/leaderboard_v2.csv',
    LEADERBOARD_XTREME_CSV:               'data/leaderboard/leaderboard_xtreme.csv',
    LEADERBOARD_DROP_ATTACK_CSV:          'data/leaderboard/leaderboard_drop_attack.csv',
    LEADERBOARD_COMBINED_CSV:             'data/leaderboard/leaderboard_combined.csv',
    LEADERBOARD_ALL_ARENAS_CSV:           'data/leaderboard/leaderboard_all_arenas.csv',
    ADVANCED_LEADERBOARD_CSV:             'data/leaderboard/advanced_leaderboard.csv',
    ADVANCED_LEADERBOARD_DROP_ATTACK_CSV: 'data/leaderboard/advanced_leaderboard_drop_attack.csv',
    ADVANCED_LEADERBOARD_COMBINED_CSV:    'data/leaderboard/advanced_leaderboard_combined.csv',

    // -----------------------------------------------------------------------
    // Analytics
    // -----------------------------------------------------------------------
    RPG_STATS_JSON:           'data/analytics/rpg_stats.json',
    RPG_STATS_CSV:            'data/analytics/rpg_stats.csv',
    STADIUM_ANALYTICS_JSON:   'data/analytics/stadium_analytics.json',
    UPSET_ANALYSIS_CSV:       'data/analytics/upset_analysis.csv',
    UPSET_MATCHES_CSV:        'data/analytics/upset_matches.csv',
    BEY_COUNTERS_CSV:         'data/analytics/bey_counters.csv',
    META_BALANCE_JSON:        'data/analytics/meta_balance.json',
    MATCHUP_MATRIX_JSON:      'data/analytics/matchup_matrix.json',
    ARCHETYPE_ANALYTICS_JSON: 'data/analytics/archetype_analytics.json',
    RECOMMENDED_MATCHES_JSON: 'data/analytics/recommended_matches.json',
    MILESTONES_JSON:          'data/analytics/milestones.json',
    XP_LEADERBOARD_JSON:      'data/analytics/xp_leaderboard.json',
    XP_HISTORY_JSON:          'data/analytics/xp_history.json',

    // -----------------------------------------------------------------------
    // Season
    // -----------------------------------------------------------------------
    SEASONS_JSON:      'data/season/seasons.json',
    SEASON_DATA_JSON:  'data/season/season_data.json',
    SEASON_STATS_JSON: 'data/season/season_statistics.json',

    // -----------------------------------------------------------------------
    // Plots (public, under docs/plots/)
    // -----------------------------------------------------------------------
    PLOTS_JSON:              'plots/plots.json',
    PLOTS_BARS_JSON:         'plots/bars/plots.json',
    PLOTS_ELO_JSON:          'plots/elo/plots.json',
    PLOTS_POSITIONS_JSON:    'plots/positions/plots.json',
    PLOTS_HEATMAPS_JSON:     'plots/heatmaps/plots.json',
    PLOTS_BASE:              'plots/',
    PLOTS_ELO_DIR:           'plots/elo/',
    PLOTS_ELO_DARK_DIR:      'plots/elo/dark/',
    PLOTS_POSITIONS_DIR:     'plots/positions/',
    PLOTS_POSITIONS_DARK_DIR:'plots/positions/dark/',
    PLOTS_KFACTOR_DIR:       'plots/kfactor/',
    PLOTS_KFACTOR_DARK_DIR:  'plots/kfactor/dark/',
    PLOTS_SEASON_DIR:        'plots/season/',

    // -----------------------------------------------------------------------
    // Tournaments
    // -----------------------------------------------------------------------
    TOURNAMENTS_JSON:         'data/tournaments/tournaments.json',
    TOURNAMENT_BRACKETS_JSON: 'data/tournaments/tournament_brackets.json',

    // -----------------------------------------------------------------------
    // Miscellaneous
    // -----------------------------------------------------------------------
    CHANGELOG_JSON: 'data/changelog.json',
    NEWSFEED_JSON:  'data/newsfeed.json',

    // -----------------------------------------------------------------------
    // Dynamic path helpers
    // -----------------------------------------------------------------------

    /**
     * Time-travel leaderboard snapshot CSV.
     * @param {number} index - snapshot index
     * @returns {string}
     */
    leaderboardSnapshot(index) {
        return `data/leaderboard_snapshots/leaderboard_${String(index).padStart(4, '0')}.csv`;
    },

    /**
     * ELO timeseries CSV for the given arena.
     * @param {string} arena - 'xtreme' | 'drop_attack' | 'combined' | …
     * @returns {string}
     */
    eloTimeseries(arena) {
        return arena === 'xtreme'
            ? 'data/elo/elo_timeseries.csv'
            : `data/elo/elo_timeseries_${arena}.csv`;
    },

    /**
     * Position timeseries CSV for the given arena.
     * @param {string} arena - 'xtreme' | 'drop_attack' | 'combined' | …
     * @returns {string}
     */
    positionTimeseries(arena) {
        return arena === 'xtreme'
            ? 'data/analytics/position_timeseries.csv'
            : `data/analytics/position_timeseries_${arena}.csv`;
    },

    /**
     * Standard leaderboard CSV for the given arena.
     * @param {string} arena - 'xtreme' | 'drop_attack' | 'combined' | …
     * @returns {string}
     */
    leaderboardForArena(arena) {
        if (arena === 'xtreme')       return 'data/leaderboard/leaderboard.csv';
        if (arena === 'combined')     return 'data/leaderboard/leaderboard_combined.csv';
        return `data/leaderboard/leaderboard_${arena}.csv`;
    },

    /**
     * Per-season statistics JSON (season-specific file written by season_statistics.py).
     * @param {string} seasonId - e.g. 'S3'
     * @returns {string}
     */
    seasonStats(seasonId) {
        return `data/season/season_statistics_${seasonId}.json`;
    },

    /**
     * Per-season meta-analytics JSON written by season_meta_analytics.py.
     * @param {string} seasonId - e.g. 'S3'
     * @returns {string}
     */
    seasonMetaAnalytics(seasonId) {
        return `data/season/season_meta_analytics_${seasonId}.json`;
    },

    /**
     * Table-snapshots CSV written by table_snapshots.py.
     * @param {string} seasonId - e.g. 'S3'
     * @param {number} tier
     * @returns {string}
     */
    tableSnapshots(seasonId, tier) {
        return `data/season/table_snapshots_${seasonId}_tier${tier}.csv`;
    },

    /**
     * Season plot manifest JSON.
     * @param {string} seasonId - e.g. 'S1'
     * @returns {string}
     */
    seasonPlotManifest(seasonId) {
        return `plots/season/${seasonId}/manifest.json`;
    },

    /**
     * Season plot directory for a tier or 'combined'.
     * @param {string} seasonId - e.g. 'S1'
     * @param {string|number} tier - tier number or 'combined'
     * @returns {string}
     */
    seasonPlotDir(seasonId, tier) {
        return tier === 'combined'
            ? `plots/season/${seasonId}/combined/`
            : `plots/season/${seasonId}/tier${tier}/`;
    },

    /**
     * Season comparison plot directory.
     * @returns {string}
     */
    seasonComparisonPlotDir() {
        return 'plots/season/comparison/';
    },

    /**
     * Season advanced meta-analytics plot directory.
     * @param {string} seasonId - e.g. 'S1'
     * @returns {string}
     */
    seasonAdvancedPlotDir(seasonId) {
        return `plots/season/${seasonId}/advanced/`;
    },

    /**
     * Interactive ELO plot HTML for a bey.
     * @param {string} safeName - filesystem-safe bey name
     * @param {boolean} dark - dark mode
     * @returns {string}
     */
    eloInteractivePlot(safeName, dark) {
        return dark
            ? `plots/elo/interactive/dark/${safeName}_dark.html`
            : `plots/elo/interactive/${safeName}.html`;
    },

    /**
     * Interactive positions plot HTML for a bey.
     * @param {string} safeName - filesystem-safe bey name
     * @param {boolean} dark - dark mode
     * @returns {string}
     */
    positionsInteractivePlot(safeName, dark) {
        return dark
            ? `plots/positions/interactive/dark/${safeName}_dark.html`
            : `plots/positions/interactive/${safeName}.html`;
    },
});
