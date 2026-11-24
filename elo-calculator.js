/**
 * ELO Calculator - Beyblade X ELO Rating System
 *
 * This module implements the same ELO calculation logic as the Python backend
 * (src/beyblade_elo.py) to enable client-side live updates.
 *
 * Features:
 * - Smooth dynamic K-factor (exponential decay, Version 3)
 * - Form-based K adjustment using rolling performance window
 * - Margin-based scoring using tanh function (Race-to-N compatible)
 * - Support for regular matches (Race to 4) and finals (Race to 7)
 * - Expected score calculation
 * - Win probability calculation
 *
 * K-Factor (Version 3, smooth exponential decay):
 *   K_base(N) = K_MIN + (K_MAX - K_MIN) * exp(-N / K_TAU)
 *   Parameters: K_MIN=12, K_MAX=40, K_TAU=15
 *
 * Margin-Based Scoring (ELO Version 3):
 *   Winner: S = 1 + MARGIN_A * tanh(MARGIN_B * (m - T) / T)
 *   Loser:  S = 0
 *   where m = point difference, T = target (4 for regular, 7 for finals)
 */

// ============================================
// CONSTANTS
// ============================================

const ELO_START = 1000;
const ELO_VERSION = 3; // Version 3: Smooth K-factor, form adjustment, tanh margin model

// Smooth exponential K-factor parameters
const K_MIN = 12;
const K_MAX = 40;
const K_TAU = 15;

// Form-based K adjustment parameters
const FORM_WINDOW = 14;  // Equivalent window size for EMA smoothing
const FORM_EMA_ALPHA = 2 / (FORM_WINDOW + 1);  // EMA smoothing factor ≈ 0.133
const FORM_ALPHA = 3.0;

// Margin model parameters (tanh-based)
const MARGIN_A = 0.18;
const MARGIN_B = 2.6;
const TARGET_POINTS = 4; // Default target for regular matches (Race to 4)

// ============================================
// K-FACTOR CALCULATION
// ============================================

/**
 * Calculate smooth K_base using exponential decay based on match count.
 * K_base(N) = K_MIN + (K_MAX - K_MIN) * exp(-N / K_TAU)
 *
 * @param {number} matches - Number of matches played
 * @returns {number} K-factor (float between K_MIN and K_MAX)
 */
function dynamicK(matches) {
    return K_MIN + (K_MAX - K_MIN) * Math.exp(-matches / K_TAU);
}

/**
 * Calculate effective K-factor with form-based EMA multiplier.
 * K_eff = K_base * (1 + FORM_ALPHA * |form_ema|)
 * where form_ema is the exponentially weighted mean of (S_i - E_i),
 * updated as: form_ema = FORM_EMA_ALPHA * delta + (1 - FORM_EMA_ALPHA) * form_ema
 *
 * @param {number} kBase - Base K-factor from dynamicK
 * @param {number|null} formEma - Current EMA of (actual_score - expected_score), or null if no history
 * @returns {number} Effective K-factor
 */
function kEffective(kBase, formEma) {
    if (formEma === null || formEma === undefined) {
        return kBase;
    }
    return kBase * (1 + FORM_ALPHA * Math.abs(formEma));
}

// ============================================
// EXPECTED SCORE CALCULATION
// ============================================

/**
 * Calculate expected score (win probability) for player A against player B
 * Uses the standard ELO formula: 1 / (1 + 10^((Rb - Ra) / 400))
 *
 * @param {number} eloA - ELO rating of player A
 * @param {number} eloB - ELO rating of player B
 * @returns {number} Expected score for player A (0.0 to 1.0)
 */
function expected(eloA, eloB) {
    return 1.0 / (1.0 + Math.pow(10, (eloB - eloA) / 400.0));
}

// ============================================
// MARGIN-BASED SCORING (tanh model, Version 3)
// ============================================

/**
 * Calculate winner score using tanh margin model (Version 3).
 *
 * For the winner: S = 1 + MARGIN_A * tanh(MARGIN_B * (m - T) / T)
 * For the loser:  S = 0
 * where m = point difference, T = target points.
 *
 * At the reference win (4-0 for Race to 4): m = T, tanh(0) = 0, S = 1.0.
 * Close wins (m < T) give S < 1.0; dominant wins (m > T) give S > 1.0.
 *
 * @param {number} scoreA - Score for player A
 * @param {number} scoreB - Score for player B
 * @param {number} target - Points needed to win (default TARGET_POINTS=4)
 * @returns {Array<number>} [scoreA_adjusted, scoreB_adjusted]
 */
function calculateScoreWithMargin(scoreA, scoreB, target) {
    if (target === undefined) target = TARGET_POINTS;

    // Draw case
    if (scoreA === scoreB) {
        return [0.5, 0.5];
    }

    if (scoreA > scoreB) {
        const m = scoreA - scoreB;
        const sWinner = 1 + MARGIN_A * Math.tanh(MARGIN_B * (m - target) / target);
        return [sWinner, 1.0 - sWinner];
    } else {
        const m = scoreB - scoreA;
        const sWinner = 1 + MARGIN_A * Math.tanh(MARGIN_B * (m - target) / target);
        return [1.0 - sWinner, sWinner];
    }
}

/**
 * Backward-compatible alias for calculateScoreWithMargin with default target (TARGET_POINTS=4).
 * @param {number} scoreA - Score for player A
 * @param {number} scoreB - Score for player B
 * @returns {Array<number>} [scoreA_adjusted, scoreB_adjusted]
 */
function calculateScoreWithDominance(scoreA, scoreB) {
    return calculateScoreWithMargin(scoreA, scoreB);
}

// ============================================
// ELO UPDATE
// ============================================

/**
 * Calculate new ELO ratings after a match
 *
 * @param {string} beyA - Name of Bey A
 * @param {string} beyB - Name of Bey B
 * @param {number} scoreA - Points scored by Bey A
 * @param {number} scoreB - Points scored by Bey B
 * @param {Object} elos - Object mapping bey names to current ELO ratings
 * @param {Object} stats - Object mapping bey names to stats (matches, wins, losses, etc.)
 * @param {number} target - Points needed to win (default TARGET_POINTS=4)
 * @returns {Object} Updated ELO and stats information
 */
function updateElo(beyA, beyB, scoreA, scoreB, elos, stats, target) {
    if (target === undefined) target = TARGET_POINTS;

    // Initialize if not present
    if (!elos[beyA]) elos[beyA] = ELO_START;
    if (!elos[beyB]) elos[beyB] = ELO_START;

    if (!stats[beyA]) {
        stats[beyA] = { matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0, form_ema: null };
    }
    if (!stats[beyB]) {
        stats[beyB] = { matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0, form_ema: null };
    }
    // Lazy init form_ema
    if (stats[beyA].form_ema === undefined) stats[beyA].form_ema = null;
    if (stats[beyB].form_ema === undefined) stats[beyB].form_ema = null;

    const eloA = elos[beyA];
    const eloB = elos[beyB];

    // Calculate expected scores
    const expectedA = expected(eloA, eloB);
    const expectedB = expected(eloB, eloA);

    // Get effective K-factors (smooth base + form adjustment)
    const kBaseA = dynamicK(stats[beyA].matches);
    const kBaseB = dynamicK(stats[beyB].matches);
    const kA = kEffective(kBaseA, stats[beyA].form_ema);
    const kB = kEffective(kBaseB, stats[beyB].form_ema);

    // Handle edge case of 0-0 score
    const total = scoreA + scoreB;
    if (total === 0) {
        return {
            beyA: beyA,
            beyB: beyB,
            eloA: eloA,
            eloB: eloB,
            newEloA: eloA,
            newEloB: eloB,
            eloChangeA: 0,
            eloChangeB: 0,
            kA: kA,
            kB: kB
        };
    }

    // Calculate margin-based scores (Version 3)
    const [actualA, actualB] = calculateScoreWithMargin(scoreA, scoreB, target);

    // Calculate new ELO ratings
    const newEloA = eloA + kA * (actualA - expectedA);
    const newEloB = eloB + kB * (actualB - expectedB);

    // Update ELO ratings
    elos[beyA] = newEloA;
    elos[beyB] = newEloB;

    // Update form EMA: exponentially weighted mean of (S_i - E_i)
    const deltaA = actualA - expectedA;
    const deltaB = actualB - expectedB;
    stats[beyA].form_ema = stats[beyA].form_ema === null
        ? FORM_EMA_ALPHA * deltaA
        : FORM_EMA_ALPHA * deltaA + (1 - FORM_EMA_ALPHA) * stats[beyA].form_ema;
    stats[beyB].form_ema = stats[beyB].form_ema === null
        ? FORM_EMA_ALPHA * deltaB
        : FORM_EMA_ALPHA * deltaB + (1 - FORM_EMA_ALPHA) * stats[beyB].form_ema;

    // Update stats
    stats[beyA].for += scoreA;
    stats[beyA].against += scoreB;
    stats[beyB].for += scoreB;
    stats[beyB].against += scoreA;
    stats[beyA].matches += 1;
    stats[beyB].matches += 1;

    // Update wins/losses
    if (scoreA > scoreB) {
        stats[beyA].wins += 1;
        stats[beyB].losses += 1;
    } else if (scoreB > scoreA) {
        stats[beyB].wins += 1;
        stats[beyA].losses += 1;
    }

    // Update winrates
    stats[beyA].winrate = stats[beyA].matches > 0 ? stats[beyA].wins / stats[beyA].matches : 0.0;
    stats[beyB].winrate = stats[beyB].matches > 0 ? stats[beyB].wins / stats[beyB].matches : 0.0;

    // Return detailed information about the update
    return {
        beyA: beyA,
        beyB: beyB,
        eloA: eloA,
        eloB: eloB,
        newEloA: newEloA,
        newEloB: newEloB,
        eloChangeA: newEloA - eloA,
        eloChangeB: newEloB - eloB,
        kA: kA,
        kB: kB,
        expectedA: expectedA,
        expectedB: expectedB,
        actualA: actualA,
        actualB: actualB,
        winner: scoreA > scoreB ? beyA : (scoreB > scoreA ? beyB : null)
    };
}

// ============================================
// LEADERBOARD GENERATION
// ============================================

/**
 * Generate a sorted leaderboard from current ELO ratings and stats
 * 
 * @param {Object} elos - Object mapping bey names to ELO ratings
 * @param {Object} stats - Object mapping bey names to stats
 * @param {Object} previousPositions - Optional previous positions for delta calculation
 * @returns {Array<Object>} Sorted leaderboard array
 */
function generateLeaderboard(elos, stats, previousPositions = null) {
    const leaderboard = [];
    
    for (const [bey, elo] of Object.entries(elos)) {
        const beyStats = stats[bey] || { matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0 };
        
        leaderboard.push({
            bey: bey,
            elo: Math.round(elo),
            matches: beyStats.matches,
            wins: beyStats.wins,
            losses: beyStats.losses,
            pointsFor: beyStats.for,
            pointsAgainst: beyStats.against,
            pointDifferential: beyStats.for - beyStats.against,
            winrate: beyStats.winrate
        });
    }
    
    // Sort by ELO descending
    leaderboard.sort((a, b) => b.elo - a.elo);
    
    // Add positions and deltas
    leaderboard.forEach((entry, index) => {
        entry.position = index + 1;
        
        if (previousPositions && previousPositions[entry.bey] !== undefined) {
            entry.positionDelta = previousPositions[entry.bey] - entry.position;
        } else {
            entry.positionDelta = 0;
        }
    });
    
    return leaderboard;
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Calculate win probability for Bey A vs Bey B
 * (Alias for expected() for API clarity)
 * 
 * @param {number} eloA - ELO rating of Bey A
 * @param {number} eloB - ELO rating of Bey B
 * @returns {number} Win probability for Bey A (0.0 to 1.0)
 */
function calculateWinProbability(eloA, eloB) {
    return expected(eloA, eloB);
}

/**
 * Get position map from leaderboard for delta tracking
 * 
 * @param {Array<Object>} leaderboard - Current leaderboard
 * @returns {Object} Map of bey name to position
 */
function getPositionMap(leaderboard) {
    const positions = {};
    leaderboard.forEach(entry => {
        positions[entry.bey] = entry.position;
    });
    return positions;
}

// ============================================
// EXPORTS
// ============================================

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports !== undefined) {
    // Node.js environment (for testing)
    module.exports = {
        ELO_START,
        ELO_VERSION,
        K_MIN,
        K_MAX,
        K_TAU,
        FORM_WINDOW,
        FORM_EMA_ALPHA,
        FORM_ALPHA,
        MARGIN_A,
        MARGIN_B,
        TARGET_POINTS,
        dynamicK,
        kEffective,
        expected,
        calculateScoreWithMargin,
        calculateScoreWithDominance,
        updateElo,
        generateLeaderboard,
        calculateWinProbability,
        getPositionMap
    };
}
