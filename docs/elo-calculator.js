/**
 * ELO Calculator - Beyblade X ELO Rating System
 * 
 * This module implements the same ELO calculation logic as the Python backend
 * (src/beyblade_elo.py) to enable client-side live updates.
 * 
 * Features:
 * - Dynamic K-factor based on match experience
 * - Dominance-based scoring (ELO Version 2)
 * - Expected score calculation
 * - Win probability calculation
 * 
 * K-Factor Rules:
 * - Learning (< 6 matches): K = 40
 * - Intermediate (6-14 matches): K = 24
 * - Experienced (15+ matches): K = 12
 * 
 * Dominance-Based Scoring:
 * - Winner gets: base_win_value (0.75) + dominance_bonus (0 to 0.25)
 * - Dominance scales with point differential
 * - Overkill bonus for scores beyond 4 points
 */

// ============================================
// CONSTANTS
// ============================================

const ELO_START = 1000;
const ELO_K_LEARNING = 40;
const ELO_K_INTERMEDIATE = 24;
const ELO_K_EXPERIENCED = 12;
const ELO_VERSION = 2; // Version 2: Dominance-based scoring

// Dominance calculation constants
const WIN_THRESHOLD = 4;
const MAX_POINT_DIFF = 6;
const OVERKILL_WEIGHT = 0.25;
const BASE_WIN = 0.75;

// ============================================
// K-FACTOR CALCULATION
// ============================================

/**
 * Calculate dynamic K-factor based on number of matches played
 * @param {number} matches - Number of matches played
 * @returns {number} K-factor (40, 24, or 12)
 */
function dynamicK(matches) {
    if (matches < 6) {
        return ELO_K_LEARNING;
    } else if (matches < 15) {
        return ELO_K_INTERMEDIATE;
    }
    return ELO_K_EXPERIENCED;
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
// DOMINANCE-BASED SCORING
// ============================================

/**
 * Calculate scores with dominance scaling (ELO Version 2)
 * 
 * Rewards dominant victories:
 * - 4-3 win: Winner gets ~0.83 (close match)
 * - 4-0 win: Winner gets ~0.83 + dominance (dominant)
 * - 6-0 win: Winner gets 1.00 (overwhelming)
 * 
 * @param {number} scoreA - Score for player A
 * @param {number} scoreB - Score for player B
 * @returns {Array<number>} [scoreA, scoreB] adjusted for dominance (sum = 1.0)
 */
function calculateScoreWithDominance(scoreA, scoreB) {
    // Draw case
    if (scoreA === scoreB) {
        return [0.5, 0.5];
    }
    
    const winnerScore = Math.max(scoreA, scoreB);
    const loserScore = Math.min(scoreA, scoreB);
    const diff = winnerScore - loserScore;
    
    // Dominance scaling up to 4-0
    let dominance;
    if (diff >= 4) {
        dominance = 1.0;
    } else {
        dominance = diff / 4.0; // 1 → 0.25, 2 → 0.5, 3 → 0.75
    }
    
    let scoreWinner = BASE_WIN + (1.0 - BASE_WIN) * dominance;
    
    // Overkill bonus (beyond 4 points)
    if (winnerScore > WIN_THRESHOLD) {
        const overkillPoints = winnerScore - WIN_THRESHOLD;
        const maxOverkill = MAX_POINT_DIFF - WIN_THRESHOLD; // 2
        scoreWinner += (overkillPoints / maxOverkill) * OVERKILL_WEIGHT;
    }
    
    const scoreLoser = 1.0 - scoreWinner;
    
    // Return in correct order
    if (scoreA > scoreB) {
        return [scoreWinner, scoreLoser];
    } else {
        return [scoreLoser, scoreWinner];
    }
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
 * @returns {Object} Updated ELO and stats information
 */
function updateElo(beyA, beyB, scoreA, scoreB, elos, stats) {
    // Initialize if not present
    if (!elos[beyA]) elos[beyA] = ELO_START;
    if (!elos[beyB]) elos[beyB] = ELO_START;
    
    if (!stats[beyA]) {
        stats[beyA] = { matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0 };
    }
    if (!stats[beyB]) {
        stats[beyB] = { matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0 };
    }
    
    const eloA = elos[beyA];
    const eloB = elos[beyB];
    
    // Calculate expected scores
    const expectedA = expected(eloA, eloB);
    const expectedB = expected(eloB, eloA);
    
    // Get K-factors based on experience
    const kA = dynamicK(stats[beyA].matches);
    const kB = dynamicK(stats[beyB].matches);
    
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
    
    // Calculate dominance-based scores
    const [actualA, actualB] = calculateScoreWithDominance(scoreA, scoreB);
    
    // Calculate new ELO ratings
    const newEloA = eloA + kA * (actualA - expectedA);
    const newEloB = eloB + kB * (actualB - expectedB);
    
    // Update ELO ratings
    elos[beyA] = newEloA;
    elos[beyB] = newEloB;
    
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
if (typeof module !== 'undefined' && module.exports) {
    // Node.js environment (for testing)
    module.exports = {
        ELO_START,
        ELO_K_LEARNING,
        ELO_K_INTERMEDIATE,
        ELO_K_EXPERIENCED,
        dynamicK,
        expected,
        calculateScoreWithDominance,
        updateElo,
        generateLeaderboard,
        calculateWinProbability,
        getPositionMap
    };
}
