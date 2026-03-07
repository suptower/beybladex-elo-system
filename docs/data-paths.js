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

    // -----------------------------------------------------------------------
    // Season
    // -----------------------------------------------------------------------
    SEASON_DATA_JSON:  'data/season/season_data.json',
    SEASON_STATS_JSON: 'data/season/season_statistics.json',

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
        return `data/leaderboard/leaderboard_${String(index).padStart(4, '0')}.csv`;
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
        return `data/season_meta_analytics_${seasonId}.json`;
    },

    /**
     * Table-snapshots CSV written by table_snapshots.py.
     * @param {string} seasonId - e.g. 'S3'
     * @param {number} tier
     * @returns {string}
     */
    tableSnapshots(seasonId, tier) {
        return `data/table_snapshots_${seasonId}_tier${tier}.csv`;
    },
});
