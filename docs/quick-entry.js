// ============================================
// QUICK ENTRY SYSTEM - Fast Round Entry for Tournaments
// ============================================

// ============================================
// UTILITY FUNCTIONS
// ============================================

// HTML escape function to prevent XSS
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Generate unique ID
let idCounter = 0;
function generateUniqueId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    // Fallback for older browsers
    return `${Date.now()}-${++idCounter}-${Math.random().toString(36).substr(2, 9)}`;
}

// Fisher-Yates shuffle for proper randomization
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

// ============================================
// FINISH TYPES (for round-level data)
// ============================================
const FINISH_TYPES = {
    SPIN: { id: 'spin', label: 'Spin', points: 1, emoji: '🌀' },
    BURST: { id: 'burst', label: 'Burst', points: 2, emoji: '💥' },
    POCKET: { id: 'pocket', label: 'Pocket', points: 2, emoji: '🎯' },
    EXTREME: { id: 'extreme', label: 'Extreme', points: 3, emoji: '⚡' }
};

// ============================================
// ELO CALCULATION CONSTANTS
// ============================================
const K_FACTOR = 32; // K-factor for ELO calculation (Swiss tournament standard)
const DEFAULT_ELO = 1000; // Default ELO rating for new players

// Score prediction thresholds
const SCORE_PREDICTION_THRESHOLDS = {
    STRONG_FAVORITE: 0.7,   // Win probability above 70%
    SLIGHT_FAVORITE: 0.55,  // Win probability above 55%
    EVEN_MATCH: 0.45,       // Win probability between 45-55%
    SLIGHT_UNDERDOG: 0.3    // Win probability above 30%
};

// ============================================
// STORAGE KEYS
// ============================================
const STORAGE_KEYS = {
    MATCHES: 'quickEntry_matches',
    TOURNAMENT: 'quickEntry_tournament',
    PARTICIPANTS: 'quickEntry_participants',
    SETTINGS: 'quickEntry_settings',
    LIVE_ELOS: 'quickEntry_liveElos',
    LIVE_STATS: 'quickEntry_liveStats',
    LIVE_MODE: 'quickEntry_liveMode',
    BASELINE_ELOS: 'quickEntry_baselineElos',
    PREVIOUS_POSITIONS: 'quickEntry_previousPositions'
};

// ============================================
// ELO CALCULATION FUNCTIONS
// ============================================

/**
 * Calculate expected score (win probability) using ELO formula
 * @param {number} eloA - ELO rating of player A
 * @param {number} eloB - ELO rating of player B
 * @returns {number} Expected score for player A (0.0 to 1.0)
 */
function calculateExpectedScore(eloA, eloB) {
    return 1.0 / (1.0 + Math.pow(10, (eloB - eloA) / 400.0));
}

/**
 * Calculate ELO change for a given outcome
 * @param {number} elo - Current ELO rating
 * @param {number} opponentElo - Opponent's ELO rating
 * @param {number} actualScore - Actual score (1 for win, 0 for loss, 0.5 for draw)
 * @returns {number} ELO change (can be positive or negative)
 */
function calculateEloChange(elo, opponentElo, actualScore) {
    const expectedScore = calculateExpectedScore(elo, opponentElo);
    return Math.round(K_FACTOR * (actualScore - expectedScore));
}

// ============================================
// STATE
// ============================================
let state = {
    matches: [],
    tournament: {
        name: '',
        round: 1,
        format: 'swiss'
    },
    participants: [],
    beyblades: [],
    matchHistory: [], // Historical match data
    roundsHistory: [], // Historical rounds data
    focusedMatchIndex: -1,
    // Live ELO tracking
    liveMode: true,
    liveElos: {}, // Current ELO ratings during this tournament
    liveStats: {}, // Current stats (matches, wins, losses, etc.)
    liveLeaderboard: [], // Sorted leaderboard
    previousPositions: {}, // For tracking rank changes
    baselineElos: {}, // Starting ELOs at tournament start
    liveEloHistory: [] // Track all ELO changes in this session
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    await loadBeybladeData();
    loadFromStorage();
    initializeLiveElos();
    initializeUI();
    setupEventListeners();
    renderMatches();
    updateStatusBar();
    updateLiveLeaderboard();
});

// Load beyblade data from CSV
async function loadBeybladeData() {
    try {
        const response = await fetch('data/leaderboard.csv');
        const text = await response.text();
        const lines = text.trim().split(/\r?\n/);
        
        state.beyblades = lines.slice(1).map(line => {
            const values = line.split(',');
            return {
                name: values[1],
                elo: parseInt(values[2]) || 1000,
                matches: parseInt(values[3]) || 0,
                wins: parseInt(values[4]) || 0
            };
        }).sort((a, b) => b.elo - a.elo);
        
        // Initialize baseline ELOs from loaded data
        state.beyblades.forEach(bey => {
            state.baselineElos[bey.name] = bey.elo;
        });
        
        // Load match history
        await loadMatchHistory();
        
        // Load rounds history
        await loadRoundsHistory();
    } catch (error) {
        console.error('Error loading beyblade data:', error);
        state.beyblades = [];
    }
}

// Load historical match data
async function loadMatchHistory() {
    try {
        const response = await fetch('data/matches.csv');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const text = await response.text();
        const lines = text.trim().split(/\r?\n/);
        
        state.matchHistory = lines.slice(1).map(line => {
            const values = line.split(',');
            return {
                matchId: values[0],
                date: values[1],
                beyA: values[2],
                beyB: values[3],
                scoreA: parseInt(values[4]) || 0,
                scoreB: parseInt(values[5]) || 0
            };
        });
    } catch (error) {
        console.error('Error loading match history:', error);
        state.matchHistory = [];
    }
}

// Load historical rounds data
async function loadRoundsHistory() {
    try {
        const response = await fetch('data/rounds.csv');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const text = await response.text();
        const lines = text.trim().split(/\r?\n/);
        
        state.roundsHistory = lines.slice(1).map(line => {
            const values = line.split(',');
            return {
                matchId: values[0],
                roundNumber: parseInt(values[1]) || 0,
                winner: values[2],
                finishType: values[3],
                points: parseInt(values[4]) || 0
            };
        });
    } catch (error) {
        console.error('Error loading rounds history:', error);
        state.roundsHistory = [];
    }
}

// Load state from localStorage
function loadFromStorage() {
    try {
        const matchesData = localStorage.getItem(STORAGE_KEYS.MATCHES);
        const tournamentData = localStorage.getItem(STORAGE_KEYS.TOURNAMENT);
        const participantsData = localStorage.getItem(STORAGE_KEYS.PARTICIPANTS);
        const liveElosData = localStorage.getItem(STORAGE_KEYS.LIVE_ELOS);
        const liveStatsData = localStorage.getItem(STORAGE_KEYS.LIVE_STATS);
        const liveModeData = localStorage.getItem(STORAGE_KEYS.LIVE_MODE);
        const baselineElosData = localStorage.getItem(STORAGE_KEYS.BASELINE_ELOS);
        const previousPositionsData = localStorage.getItem(STORAGE_KEYS.PREVIOUS_POSITIONS);
        
        if (matchesData) {
            const parsed = JSON.parse(matchesData);
            // Validate that parsed data is an array
            if (Array.isArray(parsed)) {
                state.matches = parsed;
            }
        }
        if (tournamentData) {
            const parsed = JSON.parse(tournamentData);
            // Validate tournament data structure
            if (parsed && typeof parsed === 'object') {
                state.tournament = {
                    name: String(parsed.name || ''),
                    round: parseInt(parsed.round) || 1,
                    format: String(parsed.format || 'swiss')
                };
            }
        }
        if (participantsData) {
            const parsed = JSON.parse(participantsData);
            // Validate that parsed data is an array of strings
            if (Array.isArray(parsed)) {
                state.participants = parsed.filter(p => typeof p === 'string');
            }
        }
        if (liveElosData) {
            const parsed = JSON.parse(liveElosData);
            if (parsed && typeof parsed === 'object') {
                state.liveElos = parsed;
            }
        }
        if (liveStatsData) {
            const parsed = JSON.parse(liveStatsData);
            if (parsed && typeof parsed === 'object') {
                state.liveStats = parsed;
            }
        }
        if (liveModeData !== null) {
            state.liveMode = liveModeData === 'true';
        }
        if (baselineElosData) {
            const parsed = JSON.parse(baselineElosData);
            if (parsed && typeof parsed === 'object') {
                state.baselineElos = parsed;
            }
        }
        if (previousPositionsData) {
            const parsed = JSON.parse(previousPositionsData);
            if (parsed && typeof parsed === 'object') {
                state.previousPositions = parsed;
            }
        }
    } catch (error) {
        console.error('Error loading from storage:', error);
    }
}

// Save state to localStorage
function saveToStorage() {
    try {
        localStorage.setItem(STORAGE_KEYS.MATCHES, JSON.stringify(state.matches));
        localStorage.setItem(STORAGE_KEYS.TOURNAMENT, JSON.stringify(state.tournament));
        localStorage.setItem(STORAGE_KEYS.PARTICIPANTS, JSON.stringify(state.participants));
        localStorage.setItem(STORAGE_KEYS.LIVE_ELOS, JSON.stringify(state.liveElos));
        localStorage.setItem(STORAGE_KEYS.LIVE_STATS, JSON.stringify(state.liveStats));
        localStorage.setItem(STORAGE_KEYS.LIVE_MODE, String(state.liveMode));
        localStorage.setItem(STORAGE_KEYS.BASELINE_ELOS, JSON.stringify(state.baselineElos));
        localStorage.setItem(STORAGE_KEYS.PREVIOUS_POSITIONS, JSON.stringify(state.previousPositions));
        showAutoSaveStatus();
    } catch (error) {
        console.error('Error saving to storage:', error);
    }
}

// Initialize UI with stored values
function initializeUI() {
    const tournamentNameInput = document.getElementById('tournamentName');
    const roundNumberInput = document.getElementById('roundNumber');
    const formatSelect = document.getElementById('formatSelect');
    const matchCountInput = document.getElementById('matchCount');
    const liveModeToggle = document.getElementById('liveModeToggle');
    
    if (tournamentNameInput) tournamentNameInput.value = state.tournament.name || '';
    if (roundNumberInput) roundNumberInput.value = state.tournament.round || 1;
    if (formatSelect) formatSelect.value = state.tournament.format || 'swiss';
    if (matchCountInput) matchCountInput.value = state.matches.length || 8;
    if (liveModeToggle) liveModeToggle.checked = state.liveMode;
    
    // Render selected participants
    renderSelectedParticipants();
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    // Tournament controls
    document.getElementById('tournamentName')?.addEventListener('input', handleTournamentChange);
    document.getElementById('roundNumber')?.addEventListener('input', handleTournamentChange);
    document.getElementById('formatSelect')?.addEventListener('change', handleTournamentChange);
    
    // Action buttons
    document.getElementById('generateMatchesBtn')?.addEventListener('click', generateMatches);
    document.getElementById('addMatchBtn')?.addEventListener('click', addMatch);
    document.getElementById('resetRoundBtn')?.addEventListener('click', resetRound);
    document.getElementById('clearAllBtn')?.addEventListener('click', clearAll);
    
    // Export/Import
    document.getElementById('exportJsonBtn')?.addEventListener('click', exportJSON);
    document.getElementById('exportCsvBtn')?.addEventListener('click', exportCSV);
    document.getElementById('exportRoundsCsvBtn')?.addEventListener('click', exportRoundsCSV);
    document.getElementById('importFile')?.addEventListener('change', handleImport);
    
    // Swiss pairing
    document.getElementById('participantSearch')?.addEventListener('input', handleParticipantSearch);
    document.getElementById('participantSearch')?.addEventListener('focus', handleParticipantSearch);
    document.getElementById('generatePairingsBtn')?.addEventListener('click', generateSwissPairings);
    document.getElementById('randomPairingsBtn')?.addEventListener('click', generateRandomPairings);
    
    // Shortcuts legend toggle
    document.getElementById('shortcutsHeader')?.addEventListener('click', toggleShortcutsLegend);
    
    // Live leaderboard controls
    document.getElementById('leaderboardHeader')?.addEventListener('click', toggleLiveLeaderboard);
    document.getElementById('leaderboardToggleBtn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleLiveLeaderboard();
    });
    document.getElementById('liveModeToggle')?.addEventListener('change', toggleLiveMode);
    
    // Global keyboard shortcuts
    document.addEventListener('keydown', handleGlobalKeydown);
    
    // Click outside to close dropdown
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('participantDropdown');
        const searchContainer = document.querySelector('.participant-search-container');
        if (dropdown && !searchContainer?.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });
}

function handleTournamentChange() {
    state.tournament.name = document.getElementById('tournamentName')?.value || '';
    state.tournament.round = parseInt(document.getElementById('roundNumber')?.value) || 1;
    state.tournament.format = document.getElementById('formatSelect')?.value || 'swiss';
    saveToStorage();
}

function handleGlobalKeydown(e) {
    // Ctrl+S to force save
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveToStorage();
        showToast('Data saved!', 'success');
    }
}

// ============================================
// MATCH MANAGEMENT
// ============================================

// Create an empty round object
function createEmptyRound(index) {
    return {
        roundIndex: index,
        winner: null, // 'A' or 'B'
        finishType: null // burst, ko, outspin, xtreme
    };
}

// Create an empty match with rounds support
function createEmptyMatch(index) {
    return {
        id: generateUniqueId(),
        matchNumber: index + 1,
        beyA: '',
        beyB: '',
        rounds: [], // Array of round objects
        scoreA: 0,  // Computed from rounds
        scoreB: 0,  // Computed from rounds
        winner: null,
        timestamp: null
    };
}

// Calculate scores from rounds
function calculateScoresFromRounds(match) {
    let scoreA = 0;
    let scoreB = 0;
    
    match.rounds.forEach(round => {
        if (round.winner === 'A') {
            const finishType = FINISH_TYPES[round.finishType?.toUpperCase()];
            scoreA += finishType ? finishType.points : 1;
        } else if (round.winner === 'B') {
            const finishType = FINISH_TYPES[round.finishType?.toUpperCase()];
            scoreB += finishType ? finishType.points : 1;
        }
    });
    
    return { scoreA, scoreB };
}

// Update match scores from rounds and determine winner
function updateMatchFromRounds(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const { scoreA, scoreB } = calculateScoresFromRounds(match);
    match.scoreA = scoreA;
    match.scoreB = scoreB;
    
    // Determine winner based on computed scores
    if (scoreA > scoreB && scoreA > 0) {
        match.winner = 'A';
    } else if (scoreB > scoreA && scoreB > 0) {
        match.winner = 'B';
    } else if (scoreA === scoreB && scoreA > 0) {
        match.winner = 'draw';
    } else {
        match.winner = null;
    }
    
    match.timestamp = new Date().toISOString();
    
    // Process for live ELO if match is complete
    if (state.liveMode && match.beyA && match.beyB && scoreA !== '' && scoreB !== '') {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
    }
}

// Add a round to a match
function addRound(matchIndex, winner, finishType) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const roundIndex = match.rounds.length;
    match.rounds.push({
        roundIndex: roundIndex,
        winner: winner, // 'A' or 'B'
        finishType: finishType || 'spin'
    });
    
    updateMatchFromRounds(matchIndex);
    saveToStorage();
    updateMatchRowOnly(matchIndex);
    updateStatusBar();
}

// Remove a round from a match
function removeRound(matchIndex, roundIndex) {
    const match = state.matches[matchIndex];
    if (!match || roundIndex < 0 || roundIndex >= match.rounds.length) return;
    
    match.rounds.splice(roundIndex, 1);
    // Re-index remaining rounds
    match.rounds.forEach((round, i) => {
        round.roundIndex = i;
    });
    
    updateMatchFromRounds(matchIndex);
    saveToStorage();
    updateMatchRowOnly(matchIndex);
    updateStatusBar();
}

// Update a round's winner or finish type
function updateRound(matchIndex, roundIndex, winner, finishType) {
    const match = state.matches[matchIndex];
    if (!match || roundIndex < 0 || roundIndex >= match.rounds.length) return;
    
    const round = match.rounds[roundIndex];
    if (winner !== undefined) round.winner = winner;
    if (finishType !== undefined) round.finishType = finishType;
    
    updateMatchFromRounds(matchIndex);
    saveToStorage();
    updateMatchRowOnly(matchIndex);
    updateStatusBar();
}

// Update only a specific match row and its rounds panel (keeps panel open)
function updateMatchRowOnly(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    // Update table row score display
    const row = document.querySelector(`.match-row[data-index="${matchIndex}"]`);
    if (row) {
        const scoreADisplay = row.querySelector('.col-score-a .score-display-large');
        const scoreBDisplay = row.querySelector('.col-score-b .score-display-large');
        const winnerCell = row.querySelector('.col-winner');
        const roundsBtn = row.querySelector('.rounds-btn');
        
        if (scoreADisplay) {
            scoreADisplay.textContent = match.scoreA;
            scoreADisplay.classList.toggle('score-winner', match.winner === 'A');
        }
        if (scoreBDisplay) {
            scoreBDisplay.textContent = match.scoreB;
            scoreBDisplay.classList.toggle('score-winner', match.winner === 'B');
        }
        if (winnerCell) {
            winnerCell.innerHTML = renderWinnerIndicator(match);
        }
        if (roundsBtn) {
            const hasRounds = match.rounds && match.rounds.length > 0;
            roundsBtn.classList.toggle('has-rounds', hasRounds);
            roundsBtn.querySelector('.rounds-count').textContent = `⚔️${match.rounds?.length || 0}`;
        }
        
        // Update row class
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        row.classList.remove('complete', 'incomplete');
        if (isComplete) row.classList.add('complete');
        else if (isIncomplete) row.classList.add('incomplete');
    }
    
    // Update rounds panel content (without closing it)
    const panel = document.getElementById(`roundsPanel_${matchIndex}`);
    if (panel) {
        const roundsList = panel.querySelector('.rounds-list');
        if (roundsList) {
            roundsList.innerHTML = renderRoundsList(match, matchIndex);
        }
    }
    
    // Update card view too (mobile)
    const card = document.querySelector(`.match-card[data-index="${matchIndex}"]`);
    if (card) {
        const cardScoreA = card.querySelector('.match-card-scores .score-a');
        const cardScoreB = card.querySelector('.match-card-scores .score-b');
        const cardWinner = card.querySelector('.match-card-winner');
        const roundsToggle = card.querySelector('.rounds-toggle');
        
        if (cardScoreA) {
            cardScoreA.textContent = match.scoreA;
            cardScoreA.classList.toggle('score-winner', match.winner === 'A');
        }
        if (cardScoreB) {
            cardScoreB.textContent = match.scoreB;
            cardScoreB.classList.toggle('score-winner', match.winner === 'B');
        }
        if (cardWinner) {
            cardWinner.innerHTML = renderWinnerIndicator(match);
        }
        if (roundsToggle) {
            roundsToggle.innerHTML = `⚔️ Rounds (${match.rounds?.length || 0}) <span class="toggle-arrow">▼</span>`;
        }
        
        // Update card completion state
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        card.classList.remove('complete', 'incomplete');
        if (isComplete) card.classList.add('complete');
        else if (isIncomplete) card.classList.add('incomplete');
        
        const cardRoundsPanel = document.getElementById(`cardRoundsPanel_${matchIndex}`);
        if (cardRoundsPanel) {
            const cardRoundsList = cardRoundsPanel.querySelector('.rounds-list');
            if (cardRoundsList) {
                cardRoundsList.innerHTML = renderRoundsList(match, matchIndex);
            }
        }
    }
}

function generateMatches() {
    const count = parseInt(document.getElementById('matchCount')?.value) || 8;
    state.matches = [];
    
    for (let i = 0; i < count; i++) {
        state.matches.push(createEmptyMatch(i));
    }
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast(`Generated ${count} matches`, 'success');
}

function addMatch() {
    const newIndex = state.matches.length;
    state.matches.push(createEmptyMatch(newIndex));
    saveToStorage();
    renderMatches();
    updateStatusBar();
}

function deleteMatch(index) {
    state.matches.splice(index, 1);
    // Renumber matches
    state.matches.forEach((match, i) => {
        match.matchNumber = i + 1;
    });
    saveToStorage();
    renderMatches();
    updateStatusBar();
}

function resetRound() {
    if (!confirm('Reset all scores for this round? Bey selections will be preserved.')) {
        return;
    }
    
    state.matches.forEach(match => {
        match.rounds = []; // Clear all rounds
        match.scoreA = 0;
        match.scoreB = 0;
        match.winner = null;
        match.timestamp = null;
    });
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    
    // Recalculate live leaderboard after reset
    if (state.liveMode) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
    }
    
    showToast('Round reset', 'warning');
}

function clearAll() {
    if (!confirm('Clear all match data? This cannot be undone.')) {
        return;
    }
    
    state.matches = [];
    state.participants = [];
    
    // Also reset live tournament state
    initializeLiveElos();
    
    saveToStorage();
    renderMatches();
    renderSelectedParticipants();
    updateStatusBar();
    updateLiveLeaderboard();
    showToast('All data cleared', 'warning');
}

// ============================================
// SCORE HANDLING
// ============================================
function updateScore(matchIndex, player, delta) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    if (player === 'A') {
        match.scoreA = Math.max(0, match.scoreA + delta);
    } else {
        match.scoreB = Math.max(0, match.scoreB + delta);
    }
    
    // Auto-detect winner
    updateWinner(matchIndex);
    
    // Mark timestamp
    match.timestamp = new Date().toISOString();
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
}

function setScore(matchIndex, player, value) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const score = Math.max(0, parseInt(value) || 0);
    
    if (player === 'A') {
        match.scoreA = score;
    } else {
        match.scoreB = score;
    }
    
    updateWinner(matchIndex);
    match.timestamp = new Date().toISOString();
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
}

/**
 * Get head-to-head record between two beys
 * @param {string} beyA - Name of first bey
 * @param {string} beyB - Name of second bey
 * @returns {object} Object with winsA, winsB, and matches array
 */
function getHeadToHead(beyA, beyB) {
    const h2h = {
        winsA: 0,
        winsB: 0,
        matches: []
    };
    
    state.matchHistory.forEach(match => {
        const isAinMatch = match.beyA === beyA || match.beyB === beyA;
        const isBinMatch = match.beyA === beyB || match.beyB === beyB;
        
        if (isAinMatch && isBinMatch) {
            h2h.matches.push(match);
            
            // Determine winner
            const aIsFirst = match.beyA === beyA;
            const aWon = aIsFirst ? (match.scoreA > match.scoreB) : (match.scoreB > match.scoreA);
            
            if (aWon) {
                h2h.winsA++;
            } else if (match.scoreA !== match.scoreB) {
                h2h.winsB++;
            }
        }
    });
    
    return h2h;
}

/**
 * Calculate predicted score based on win probability
 * Assumes matches typically go to 4 points (first to 4 wins)
 * @param {number} winProb - Win probability (0-1) for player A
 * @returns {object} Object with scoreA and scoreB
 */
function calculatePredictedScore(winProb) {
    // Deterministic score prediction based on win probability
    // Winner gets 4 points, loser gets points based on probability difference
    
    if (winProb > SCORE_PREDICTION_THRESHOLDS.STRONG_FAVORITE) {
        // Strong favorite A: likely 4-1
        return { scoreA: 4, scoreB: 1 };
    } else if (winProb > SCORE_PREDICTION_THRESHOLDS.SLIGHT_FAVORITE) {
        // Slight favorite A: likely 4-2
        return { scoreA: 4, scoreB: 2 };
    } else if (winProb >= SCORE_PREDICTION_THRESHOLDS.EVEN_MATCH) {
        // Even match: could go either way, likely 4-3
        return { scoreA: 4, scoreB: 3 };
    } else if (winProb >= SCORE_PREDICTION_THRESHOLDS.SLIGHT_UNDERDOG) {
        // Slight underdog A (B is favorite): likely 2-4
        return { scoreA: 2, scoreB: 4 };
    } else {
        // Strong underdog A (B is strong favorite): likely 1-4
        return { scoreA: 1, scoreB: 4 };
    }
}

/**
 * Get finish type statistics for a bey
 * @param {string} beyName - Name of the bey
 * @returns {object} Object with finish type counts
 */
function getFinishTypeStats(beyName) {
    const stats = {
        spin: 0,
        burst: 0,
        pocket: 0,
        extreme: 0,
        total: 0
    };
    
    // Get all matches involving this bey
    const beyMatches = state.matchHistory.filter(m => m.beyA === beyName || m.beyB === beyName);
    const matchIdsSet = new Set(beyMatches.map(m => m.matchId));
    
    // Get rounds for these matches where the bey won
    state.roundsHistory.forEach(round => {
        if (matchIdsSet.has(round.matchId) && round.winner === beyName) {
            const finishType = round.finishType?.toLowerCase();
            if (finishType && stats[finishType] !== undefined) {
                stats[finishType]++;
                stats.total++;
            }
        }
    });
    
    return stats;
}

/**
 * Get most likely finish type for a bey
 * @param {string} beyName - Name of the bey
 * @returns {string} Most common finish type
 */
function getMostLikelyFinish(beyName) {
    const stats = getFinishTypeStats(beyName);
    
    if (stats.total === 0) {
        return 'spin'; // Default if no data
    }
    
    let maxCount = 0;
    let mostLikely = 'spin';
    
    ['spin', 'burst', 'pocket', 'extreme'].forEach(type => {
        if (stats[type] > maxCount) {
            maxCount = stats[type];
            mostLikely = type;
        }
    });
    
    return mostLikely;
}

function updateWinner(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    // Determine winner based on score
    if (match.scoreA > match.scoreB && match.scoreA > 0) {
        match.winner = 'A';
    } else if (match.scoreB > match.scoreA && match.scoreB > 0) {
        match.winner = 'B';
    } else if (match.scoreA === match.scoreB && match.scoreA > 0) {
        // Tie - highlight as warning but valid in some formats
        match.winner = 'draw';
    } else {
        match.winner = null;
    }
}

function updateBey(matchIndex, player, beyName) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    if (player === 'A') {
        match.beyA = beyName;
    } else {
        match.beyB = beyName;
    }
    
    saveToStorage();
    renderMatches();
    
    // Update analysis panel when both Beys are selected
    updateAnalysisPanel(matchIndex);
}

// ============================================
// PRE-MATCH ANALYSIS PANEL
// ============================================

/**
 * Get Bey data including ELO from state
 * @param {string} beyName - Name of the Bey
 * @returns {object|null} Bey data or null if not found
 */
function getBeyData(beyName) {
    if (!beyName) return null;
    return state.beyblades.find(bey => bey.name === beyName) || null;
}

/**
 * Render pre-match analysis panel for a match
 * @param {number} matchIndex - Index of the match
 * @param {string} idPrefix - ID prefix for the panel (default: 'analysisPanel')
 * @returns {string} HTML string for the analysis panel
 */
function renderAnalysisPanel(matchIndex, idPrefix = 'analysisPanel') {
    const match = state.matches[matchIndex];
    if (!match || !match.beyA || !match.beyB) {
        return `
            <div class="match-analysis-panel collapsed" id="${idPrefix}_${matchIndex}">
                <div class="analysis-toggle" onclick="toggleAnalysisPanel('${idPrefix}_${matchIndex}')">
                    <span class="analysis-toggle-icon">▶</span>
                    <span class="analysis-toggle-text">📊 Pre-Match Analysis</span>
                    <span class="analysis-toggle-hint">Select both Beys to see predictions</span>
                </div>
            </div>
        `;
    }
    
    const beyAData = getBeyData(match.beyA);
    const beyBData = getBeyData(match.beyB);
    
    if (!beyAData || !beyBData) {
        return `
            <div class="match-analysis-panel collapsed" id="${idPrefix}_${matchIndex}">
                <div class="analysis-toggle" onclick="toggleAnalysisPanel('${idPrefix}_${matchIndex}')">
                    <span class="analysis-toggle-icon">▶</span>
                    <span class="analysis-toggle-text">📊 Pre-Match Analysis</span>
                    <span class="analysis-toggle-hint">ELO data not available</span>
                </div>
            </div>
        `;
    }
    
    // Use live ELOs if available and live mode is enabled, otherwise use static data
    let eloA, eloB;
    if (state.liveMode && state.liveElos[match.beyA] && state.liveElos[match.beyB]) {
        eloA = state.liveElos[match.beyA];
        eloB = state.liveElos[match.beyB];
    } else {
        eloA = beyAData.elo || DEFAULT_ELO;
        eloB = beyBData.elo || DEFAULT_ELO;
    }
    const eloDiff = eloA - eloB;
    
    // Calculate win probabilities
    const probA = calculateExpectedScore(eloA, eloB);
    const probB = 1 - probA;
    
    // Calculate expected ELO changes
    const eloChangeAWin = calculateEloChange(eloA, eloB, 1);
    const eloChangeALoss = calculateEloChange(eloA, eloB, 0);
    const eloChangeBWin = calculateEloChange(eloB, eloA, 1);
    const eloChangeBLoss = calculateEloChange(eloB, eloA, 0);
    
    // Get head-to-head record
    const h2h = getHeadToHead(match.beyA, match.beyB);
    
    // Get predicted score
    const predictedScore = calculatePredictedScore(probA);
    
    // Get likely finish types
    const finishA = getMostLikelyFinish(match.beyA);
    const finishB = getMostLikelyFinish(match.beyB);
    const finishStatsA = getFinishTypeStats(match.beyA);
    const finishStatsB = getFinishTypeStats(match.beyB);
    
    // Determine favored status
    let favoredText = '';
    if (Math.abs(eloDiff) < 50) {
        favoredText = '<span class="favored-even">Even Match</span>';
    } else if (eloDiff > 0) {
        favoredText = `<span class="favored-a">${escapeHtml(match.beyA)} Favored</span>`;
    } else {
        favoredText = `<span class="favored-b">${escapeHtml(match.beyB)} Favored</span>`;
    }
    
    // Build head-to-head display
    let h2hDisplay = '';
    if (h2h.matches.length > 0) {
        h2hDisplay = `
            <div class="analysis-section head-to-head">
                <div class="h2h-label">Head-to-Head Record</div>
                <div class="h2h-record">
                    <span class="h2h-stat">
                        <span class="h2h-bey">${escapeHtml(match.beyA)}</span>
                        <span class="h2h-wins">${h2h.winsA}W</span>
                    </span>
                    <span class="h2h-separator">-</span>
                    <span class="h2h-stat">
                        <span class="h2h-wins">${h2h.winsB}W</span>
                        <span class="h2h-bey">${escapeHtml(match.beyB)}</span>
                    </span>
                </div>
                <div class="h2h-total">${h2h.matches.length} previous ${h2h.matches.length === 1 ? 'match' : 'matches'}</div>
            </div>
        `;
    }
    
    // Build finish type predictions
    const finishIcons = {
        spin: '🌀',
        burst: '💥',
        pocket: '🎯',
        extreme: '⚡'
    };
    
    let finishDisplay = '';
    if (finishStatsA.total > 0 || finishStatsB.total > 0) {
        finishDisplay = `
            <div class="analysis-section finish-predictions">
                <div class="finish-label">Most Likely Finish Types</div>
                <div class="finish-types">
                    ${finishStatsA.total > 0 ? `
                        <div class="finish-type-item">
                            <span class="finish-bey">${escapeHtml(match.beyA)}</span>
                            <span class="finish-icon">${finishIcons[finishA]} ${finishA.charAt(0).toUpperCase() + finishA.slice(1)}</span>
                            <span class="finish-percent">${((finishStatsA[finishA] / finishStatsA.total) * 100).toFixed(0)}%</span>
                        </div>
                    ` : ''}
                    ${finishStatsB.total > 0 ? `
                        <div class="finish-type-item">
                            <span class="finish-bey">${escapeHtml(match.beyB)}</span>
                            <span class="finish-icon">${finishIcons[finishB]} ${finishB.charAt(0).toUpperCase() + finishB.slice(1)}</span>
                            <span class="finish-percent">${((finishStatsB[finishB] / finishStatsB.total) * 100).toFixed(0)}%</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    return `
        <div class="match-analysis-panel collapsed" id="${idPrefix}_${matchIndex}">
            <div class="analysis-toggle" onclick="toggleAnalysisPanel('${idPrefix}_${matchIndex}')">
                <span class="analysis-toggle-icon">▶</span>
                <span class="analysis-toggle-text">📊 Pre-Match Analysis</span>
                ${favoredText}
            </div>
            
            <div class="analysis-content" style="display: none;">
                <div class="analysis-section elo-ratings">
                    <div class="elo-rating-item elo-a">
                        <span class="elo-bey-name">${escapeHtml(match.beyA)}</span>
                        <span class="elo-value">${eloA}</span>
                    </div>
                    <div class="elo-diff">
                        <span class="elo-diff-label">ΔELO</span>
                        <span class="elo-diff-value ${eloDiff >= 0 ? 'positive' : 'negative'}">${eloDiff >= 0 ? '+' : ''}${eloDiff}</span>
                    </div>
                    <div class="elo-rating-item elo-b">
                        <span class="elo-bey-name">${escapeHtml(match.beyB)}</span>
                        <span class="elo-value">${eloB}</span>
                    </div>
                </div>
                
                <div class="analysis-section win-probability">
                    <div class="probability-label">Win Probability</div>
                    <div class="probability-bars">
                        <div class="probability-bar-container">
                            <div class="probability-bar prob-a" style="width: ${probA * 100}%">
                                <span class="probability-text">${(probA * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                        <div class="probability-bar-container">
                            <div class="probability-bar prob-b" style="width: ${probB * 100}%">
                                <span class="probability-text">${(probB * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="analysis-section predicted-score">
                    <div class="predicted-score-label">Predicted Score</div>
                    <div class="predicted-score-value">
                        <span class="score-team score-a">${predictedScore.scoreA}</span>
                        <span class="score-separator">-</span>
                        <span class="score-team score-b">${predictedScore.scoreB}</span>
                    </div>
                    <div class="predicted-score-hint">Based on ${(probA * 100).toFixed(0)}% win probability</div>
                </div>
                
                ${h2hDisplay}
                
                ${finishDisplay}
                
                <div class="analysis-section elo-changes">
                    <div class="elo-change-label">Expected ELO Changes</div>
                    <div class="elo-change-outcomes">
                        <div class="elo-outcome">
                            <span class="outcome-label">If ${escapeHtml(match.beyA)} wins:</span>
                            <span class="outcome-values">
                                <span class="elo-change ${eloChangeAWin >= 0 ? 'positive' : 'negative'}">${eloChangeAWin >= 0 ? '+' : ''}${eloChangeAWin}</span>
                                <span class="outcome-separator">/</span>
                                <span class="elo-change ${eloChangeBLoss >= 0 ? 'positive' : 'negative'}">${eloChangeBLoss >= 0 ? '+' : ''}${eloChangeBLoss}</span>
                            </span>
                        </div>
                        <div class="elo-outcome">
                            <span class="outcome-label">If ${escapeHtml(match.beyB)} wins:</span>
                            <span class="outcome-values">
                                <span class="elo-change ${eloChangeALoss >= 0 ? 'positive' : 'negative'}">${eloChangeALoss >= 0 ? '+' : ''}${eloChangeALoss}</span>
                                <span class="outcome-separator">/</span>
                                <span class="elo-change ${eloChangeBWin >= 0 ? 'positive' : 'negative'}">${eloChangeBWin >= 0 ? '+' : ''}${eloChangeBWin}</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Update analysis panel for a specific match
 * @param {number} matchIndex - Index of the match to update
 */
function updateAnalysisPanel(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    // Update table row analysis panel
    const panel = document.getElementById(`analysisPanel_${matchIndex}`);
    if (panel) {
        panel.outerHTML = renderAnalysisPanel(matchIndex);
    }
    
    // Update card view analysis panel
    const cardPanel = document.getElementById(`cardAnalysisPanel_${matchIndex}`);
    if (cardPanel) {
        cardPanel.outerHTML = renderAnalysisPanel(matchIndex, 'cardAnalysisPanel');
    }
}

// ============================================
// RENDERING
// ============================================
function renderMatches() {
    renderMatchTable();
    renderMatchCards();
}

// Render rounds list for a match
function renderRoundsList(match, matchIndex) {
    if (!match.rounds || match.rounds.length === 0) {
        return '<div class="rounds-empty">No rounds recorded</div>';
    }
    
    return match.rounds.map((round, roundIndex) => {
        const winnerLabel = round.winner === 'A' ? (match.beyA || 'A') : (match.beyB || 'B');
        const finishType = FINISH_TYPES[round.finishType?.toUpperCase()] || { label: round.finishType || 'Win' };
        
        return `
            <div class="round-item round-winner-${round.winner?.toLowerCase() || 'none'}">
                <span class="round-number">R${round.roundIndex + 1}</span>
                <span class="round-winner">${escapeHtml(winnerLabel)}</span>
                <span class="round-finish">${escapeHtml(finishType.label)}</span>
                <button class="round-remove-btn" onclick="removeRound(${matchIndex}, ${roundIndex})" title="Remove round">×</button>
            </div>
        `;
    }).join('');
}

// Render quick add buttons for rounds
function renderQuickAddButtons(matchIndex, match) {
    const beyAName = match.beyA ? escapeHtml(match.beyA.substring(0, 8)) : 'A';
    const beyBName = match.beyB ? escapeHtml(match.beyB.substring(0, 8)) : 'B';
    
    return `
        <div class="quick-add-rounds">
            <div class="quick-add-group">
                <span class="quick-add-label">${beyAName} wins:</span>
                <button class="quick-add-btn spin-a" onclick="addRound(${matchIndex}, 'A', 'spin')" title="Spin Finish (+1)">🌀</button>
                <button class="quick-add-btn burst-a" onclick="addRound(${matchIndex}, 'A', 'burst')" title="Burst Finish (+2)">💥</button>
                <button class="quick-add-btn pocket-a" onclick="addRound(${matchIndex}, 'A', 'pocket')" title="Pocket Finish (+2)">🎯</button>
                <button class="quick-add-btn extreme-a" onclick="addRound(${matchIndex}, 'A', 'extreme')" title="Extreme Finish (+3)">⚡</button>
            </div>
            <div class="quick-add-group">
                <span class="quick-add-label">${beyBName} wins:</span>
                <button class="quick-add-btn spin-b" onclick="addRound(${matchIndex}, 'B', 'spin')" title="Spin Finish (+1)">🌀</button>
                <button class="quick-add-btn burst-b" onclick="addRound(${matchIndex}, 'B', 'burst')" title="Burst Finish (+2)">💥</button>
                <button class="quick-add-btn pocket-b" onclick="addRound(${matchIndex}, 'B', 'pocket')" title="Pocket Finish (+2)">🎯</button>
                <button class="quick-add-btn extreme-b" onclick="addRound(${matchIndex}, 'B', 'extreme')" title="Extreme Finish (+3)">⚡</button>
            </div>
        </div>
    `;
}

function renderMatchTable() {
    const tbody = document.getElementById('matchEntryBody');
    if (!tbody) return;
    
    tbody.innerHTML = state.matches.map((match, index) => {
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        const rowClass = isComplete ? 'complete' : (isIncomplete ? 'incomplete' : '');
        const hasRounds = match.rounds && match.rounds.length > 0;
        
        return `
            <tr class="match-row ${rowClass}" data-index="${index}">
                <td class="col-match">
                    <span class="match-number">${match.matchNumber}</span>
                </td>
                <td class="col-bey-a">
                    ${renderBeySelect(match.beyA, index, 'A')}
                </td>
                <td class="col-score-a">
                    <div class="score-display-large ${match.winner === 'A' ? 'score-winner' : ''}">${match.scoreA}</div>
                </td>
                <td class="col-vs">
                    <span class="vs-text">VS</span>
                </td>
                <td class="col-score-b">
                    <div class="score-display-large ${match.winner === 'B' ? 'score-winner' : ''}">${match.scoreB}</div>
                </td>
                <td class="col-bey-b">
                    ${renderBeySelect(match.beyB, index, 'B')}
                </td>
                <td class="col-winner">
                    ${renderWinnerIndicator(match)}
                </td>
                <td class="col-actions">
                    <div class="row-actions">
                        <button class="row-action-btn rounds-btn ${hasRounds ? 'has-rounds' : ''}" onclick="toggleRoundsPanel(${index})" title="Rounds (${match.rounds?.length || 0})">
                            <span class="rounds-count">⚔️${match.rounds?.length || 0}</span>
                        </button>
                        <button class="row-action-btn delete-btn" onclick="deleteMatch(${index})" aria-label="Delete match" title="Delete">🗑️</button>
                    </div>
                </td>
            </tr>
            <tr class="analysis-panel-row" id="analysisPanelRow_${index}">
                <td colspan="8">
                    ${renderAnalysisPanel(index)}
                </td>
            </tr>
            <tr class="rounds-panel-row" id="roundsPanel_${index}" style="display: none;">
                <td colspan="8">
                    <div class="rounds-panel">
                        <div class="rounds-panel-header">
                            <h4>Rounds for Match ${match.matchNumber}</h4>
                            <div class="finish-legend">
                                <span>🌀 Spin (+1)</span>
                                <span>💥 Burst (+2)</span>
                                <span>🎯 Pocket (+2)</span>
                                <span>⚡ Extreme (+3)</span>
                            </div>
                        </div>
                        ${renderQuickAddButtons(index, match)}
                        <div class="rounds-list">
                            ${renderRoundsList(match, index)}
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderMatchCards() {
    const container = document.getElementById('matchCardsContainer');
    if (!container) return;
    
    container.innerHTML = state.matches.map((match, index) => {
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        const cardClass = isComplete ? 'complete' : (isIncomplete ? 'incomplete' : '');
        const hasRounds = match.rounds && match.rounds.length > 0;
        
        return `
            <div class="match-card ${cardClass}" data-index="${index}">
                <div class="match-card-header">
                    <span class="match-card-number">Match ${match.matchNumber}</span>
                    <span class="match-card-winner">${renderWinnerIndicator(match)}</span>
                </div>
                <div class="match-card-content">
                    <div class="match-card-names">
                        ${renderBeySelect(match.beyA, index, 'A')}
                        <span class="vs-text">VS</span>
                        ${renderBeySelect(match.beyB, index, 'B')}
                    </div>
                    <div class="match-card-scores">
                        <div class="score-display-large score-a ${match.winner === 'A' ? 'score-winner' : ''}">${match.scoreA}</div>
                        <span class="score-separator">:</span>
                        <div class="score-display-large score-b ${match.winner === 'B' ? 'score-winner' : ''}">${match.scoreB}</div>
                    </div>
                </div>
                ${renderAnalysisPanel(index, 'cardAnalysisPanel')}
                <div class="match-card-rounds">
                    <div class="rounds-toggle" onclick="toggleCardRounds(${index})">
                        ⚔️ Rounds (${match.rounds?.length || 0}) <span class="toggle-arrow">▼</span>
                    </div>
                    <div class="card-rounds-panel" id="cardRoundsPanel_${index}" style="display: none;">
                        ${renderQuickAddButtons(index, match)}
                        <div class="rounds-list">
                            ${renderRoundsList(match, index)}
                        </div>
                    </div>
                </div>
                <div class="match-card-actions">
                    <button class="row-action-btn delete-btn" onclick="deleteMatch(${index})">🗑️ Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

// Toggle rounds panel visibility (table view)
function toggleRoundsPanel(matchIndex) {
    const panel = document.getElementById(`roundsPanel_${matchIndex}`);
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'table-row' : 'none';
    }
}

// Toggle rounds panel visibility (card view)
function toggleCardRounds(matchIndex) {
    const panel = document.getElementById(`cardRoundsPanel_${matchIndex}`);
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

// Toggle analysis panel visibility
function toggleAnalysisPanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    const content = panel.querySelector('.analysis-content');
    const icon = panel.querySelector('.analysis-toggle-icon');
    
    if (content && icon) {
        const isCollapsed = panel.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Expand
            panel.classList.remove('collapsed');
            content.style.display = 'flex';
            icon.textContent = '▼';
        } else {
            // Collapse
            panel.classList.add('collapsed');
            content.style.display = 'none';
            icon.textContent = '▶';
        }
    }
}

function renderBeySelect(selectedBey, matchIndex, player) {
    const escapedSelectedBey = escapeHtml(selectedBey);
    // Sort beyblades alphabetically for quick entry
    const sortedBeyblades = [...state.beyblades].sort((a, b) => a.name.localeCompare(b.name));
    const options = sortedBeyblades.map(bey => {
        const escapedName = escapeHtml(bey.name);
        return `<option value="${escapedName}" ${bey.name === selectedBey ? 'selected' : ''}>${escapedName}</option>`;
    }).join('');
    
    return `
        <select class="bey-select ${selectedBey ? 'has-value' : ''}" 
                onchange="updateBey(${matchIndex}, '${escapeHtml(player)}', this.value)"
                data-match="${matchIndex}" 
                data-player="${escapeHtml(player)}">
            <option value="">Select Bey...</option>
            ${options}
        </select>
    `;
}

function renderWinnerIndicator(match) {
    if (!match.winner) {
        return '<span class="winner-indicator winner-none">—</span>';
    }
    
    if (match.winner === 'draw') {
        return '<span class="winner-indicator winner-draw">Draw</span>';
    }
    
    const winnerName = match.winner === 'A' ? (match.beyA || 'A') : (match.beyB || 'B');
    const winnerClass = match.winner === 'A' ? 'winner-a' : 'winner-b';
    
    // Truncate long names
    const displayName = winnerName.length > 12 ? winnerName.substring(0, 10) + '…' : winnerName;
    
    return `<span class="winner-indicator ${winnerClass}" title="${escapeHtml(winnerName)}">${escapeHtml(displayName)}</span>`;
}

// ============================================
// STATUS BAR
// ============================================
function updateStatusBar() {
    const total = state.matches.length;
    const completed = state.matches.filter(m => m.winner && m.beyA && m.beyB).length;
    const incomplete = total - completed;
    
    document.getElementById('totalMatchesCount').textContent = total;
    document.getElementById('completedMatchesCount').textContent = completed;
    document.getElementById('incompleteMatchesCount').textContent = incomplete;
}

function showAutoSaveStatus() {
    const icon = document.getElementById('autoSaveIcon');
    const text = document.getElementById('autoSaveStatus');
    
    if (icon) icon.textContent = '✓';
    if (text) text.textContent = 'Saved';
    
    setTimeout(() => {
        if (icon) icon.textContent = '💾';
        if (text) text.textContent = 'Auto-saved';
    }, 1500);
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================
function toggleShortcutsLegend() {
    const legend = document.getElementById('shortcutsLegend');
    if (legend) {
        legend.classList.toggle('collapsed');
    }
}

// ============================================
// SWISS PAIRING
// ============================================
function handleParticipantSearch(e) {
    const query = e.target.value.toLowerCase();
    const dropdown = document.getElementById('participantDropdown');
    if (!dropdown) return;
    
    if (query.length === 0 && e.type !== 'focus') {
        dropdown.classList.remove('active');
        return;
    }
    
    const filtered = state.beyblades.filter(bey => 
        bey.name.toLowerCase().includes(query) &&
        !state.participants.includes(bey.name)
    ).slice(0, 10);
    
    if (filtered.length === 0) {
        dropdown.innerHTML = '<div class="participant-option" style="color: var(--text-light)">No matches found</div>';
    } else {
        dropdown.innerHTML = filtered.map(bey => {
            const escapedName = escapeHtml(bey.name);
            return `
            <div class="participant-option" onclick="addParticipant('${escapedName}')">
                <span>${escapedName}</span>
                <span class="elo-badge">${bey.elo} ELO</span>
            </div>
        `}).join('');
    }
    
    dropdown.classList.add('active');
}

function addParticipant(name) {
    if (!state.participants.includes(name)) {
        state.participants.push(name);
        saveToStorage();
        renderSelectedParticipants();
    }
    
    const search = document.getElementById('participantSearch');
    const dropdown = document.getElementById('participantDropdown');
    if (search) search.value = '';
    if (dropdown) dropdown.classList.remove('active');
}

function removeParticipant(name) {
    state.participants = state.participants.filter(p => p !== name);
    saveToStorage();
    renderSelectedParticipants();
}

function renderSelectedParticipants() {
    const container = document.getElementById('selectedParticipants');
    if (!container) return;
    
    if (state.participants.length === 0) {
        container.innerHTML = '<span style="color: var(--text-light); font-size: 0.875rem;">No participants selected</span>';
        return;
    }
    
    container.innerHTML = state.participants.map(name => {
        const escapedName = escapeHtml(name);
        return `
        <div class="participant-chip">
            <span>${escapedName}</span>
            <button class="remove-participant" onclick="removeParticipant('${escapedName}')" aria-label="Remove ${escapedName}">×</button>
        </div>
    `}).join('');
}

function generateSwissPairings() {
    if (state.participants.length < 2) {
        showToast('Need at least 2 participants', 'error');
        return;
    }
    
    // Sort participants by ELO
    const sortedParticipants = [...state.participants].sort((a, b) => {
        const beyA = state.beyblades.find(bey => bey.name === a);
        const beyB = state.beyblades.find(bey => bey.name === b);
        return (beyB?.elo || 1000) - (beyA?.elo || 1000);
    });
    
    // Swiss pairing: pair adjacent players
    state.matches = [];
    for (let i = 0; i < sortedParticipants.length - 1; i += 2) {
        state.matches.push({
            id: generateUniqueId(),
            matchNumber: state.matches.length + 1,
            beyA: sortedParticipants[i],
            beyB: sortedParticipants[i + 1],
            rounds: [],
            scoreA: 0,
            scoreB: 0,
            winner: null,
            timestamp: null
        });
    }
    
    // Handle odd participant (bye)
    if (sortedParticipants.length % 2 === 1) {
        showToast(`${escapeHtml(sortedParticipants[sortedParticipants.length - 1])} gets a bye`, 'warning');
    }
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast(`Generated ${state.matches.length} Swiss pairings`, 'success');
}

function generateRandomPairings() {
    if (state.participants.length < 2) {
        showToast('Need at least 2 participants', 'error');
        return;
    }
    
    // Shuffle participants using Fisher-Yates algorithm
    const shuffled = shuffleArray(state.participants);
    
    // Create pairings
    state.matches = [];
    for (let i = 0; i < shuffled.length - 1; i += 2) {
        state.matches.push({
            id: generateUniqueId(),
            matchNumber: state.matches.length + 1,
            beyA: shuffled[i],
            beyB: shuffled[i + 1],
            rounds: [],
            scoreA: 0,
            scoreB: 0,
            winner: null,
            timestamp: null
        });
    }
    
    if (shuffled.length % 2 === 1) {
        showToast(`${escapeHtml(shuffled[shuffled.length - 1])} gets a bye`, 'warning');
    }
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast(`Generated ${state.matches.length} random pairings`, 'success');
}

// ============================================
// EXPORT/IMPORT
// ============================================
function exportJSON() {
    const data = {
        tournament: state.tournament,
        matches: state.matches,
        exportDate: new Date().toISOString(),
        version: '2.0' // Updated version for rounds support
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const filename = `${state.tournament.name || 'tournament'}_round${state.tournament.round}_${new Date().toISOString().split('T')[0]}.json`;
    downloadFile(url, filename);
    
    showToast('Exported as JSON', 'success');
}

function exportCSV() {
    // Export match-level CSV (summary)
    const headers = ['MatchID', 'Date', 'BeyA', 'BeyB', 'ScoreA', 'ScoreB', 'RoundsCount'];
    const rows = state.matches.map((match, i) => {
        const date = match.timestamp ? new Date(match.timestamp).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
        return [
            `M${String(i + 1).padStart(4, '0')}`,
            date,
            match.beyA || '',
            match.beyB || '',
            match.scoreA,
            match.scoreB,
            match.rounds?.length || 0
        ];
    });
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const filename = `${state.tournament.name || 'tournament'}_round${state.tournament.round}_${new Date().toISOString().split('T')[0]}.csv`;
    downloadFile(url, filename);
    
    showToast('Exported as CSV', 'success');
}

// Export detailed rounds CSV
function exportRoundsCSV() {
    // Format compatible with ./data/rounds.csv
    const headers = ['match_id', 'round_number', 'winner', 'finish_type', 'points_awarded', 'notes'];
    const rows = [];
    
    state.matches.forEach((match, i) => {
        const matchId = `M${String(i + 1).padStart(4, '0')}`;
        if (match.rounds && match.rounds.length > 0) {
            match.rounds.forEach(round => {
                const winnerName = round.winner === 'A' ? match.beyA : match.beyB;
                const finishType = round.finishType || '';
                // Get points for the finish type
                const finishTypeObj = Object.values(FINISH_TYPES).find(ft => ft.id === finishType);
                const points = finishTypeObj ? finishTypeObj.points : '';
                rows.push([
                    matchId,
                    round.roundIndex + 1,
                    winnerName || round.winner,
                    finishType,
                    points,
                    '' // notes column (empty by default)
                ]);
            });
        }
    });
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const filename = `${state.tournament.name || 'tournament'}_rounds_${new Date().toISOString().split('T')[0]}.csv`;
    downloadFile(url, filename);
    
    showToast('Exported rounds as CSV', 'success');
}

function downloadFile(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function handleImport(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    
    reader.onload = (event) => {
        try {
            const content = event.target.result;
            
            if (file.name.endsWith('.json')) {
                importJSON(content);
            } else if (file.name.endsWith('.csv')) {
                importCSV(content);
            } else {
                showToast('Unsupported file format', 'error');
            }
        } catch (error) {
            console.error('Import error:', error);
            showToast('Error importing file', 'error');
        }
    };
    
    reader.readAsText(file);
    e.target.value = ''; // Reset file input
}

function importJSON(content) {
    const data = JSON.parse(content);
    
    if (data.tournament) {
        state.tournament = data.tournament;
        document.getElementById('tournamentName').value = state.tournament.name || '';
        document.getElementById('roundNumber').value = state.tournament.round || 1;
        document.getElementById('formatSelect').value = state.tournament.format || 'swiss';
    }
    
    if (data.matches && Array.isArray(data.matches)) {
        state.matches = data.matches.map((match, i) => {
            const imported = {
                id: match.id || generateUniqueId(),
                matchNumber: match.matchNumber || i + 1,
                beyA: match.beyA || '',
                beyB: match.beyB || '',
                rounds: Array.isArray(match.rounds) ? match.rounds : [],
                scoreA: match.scoreA || 0,
                scoreB: match.scoreB || 0,
                winner: match.winner || null,
                timestamp: match.timestamp || null
            };
            
            // If rounds exist, recalculate scores from rounds
            if (imported.rounds.length > 0) {
                const { scoreA, scoreB } = calculateScoresFromRounds(imported);
                imported.scoreA = scoreA;
                imported.scoreB = scoreB;
                
                // Recalculate winner
                if (scoreA > scoreB && scoreA > 0) {
                    imported.winner = 'A';
                } else if (scoreB > scoreA && scoreB > 0) {
                    imported.winner = 'B';
                } else if (scoreA === scoreB && scoreA > 0) {
                    imported.winner = 'draw';
                } else {
                    imported.winner = null;
                }
            }
            
            return imported;
        });
    }
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast('Imported JSON data', 'success');
}

function importCSV(content) {
    const lines = content.trim().split(/\r?\n/);
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    
    // Find column indices
    const beyAIndex = headers.findIndex(h => h.includes('beya') || h === 'bey a');
    const beyBIndex = headers.findIndex(h => h.includes('beyb') || h === 'bey b');
    const scoreAIndex = headers.findIndex(h => h.includes('scorea') || h === 'score a');
    const scoreBIndex = headers.findIndex(h => h.includes('scoreb') || h === 'score b');
    
    if (beyAIndex === -1 || beyBIndex === -1) {
        showToast('CSV must have BeyA and BeyB columns', 'error');
        return;
    }
    
    state.matches = lines.slice(1).filter(line => line.trim()).map((line, i) => {
        // Simple CSV parsing - handles basic cases
        const values = line.split(',').map(v => v.trim());
        const scoreA = scoreAIndex !== -1 ? parseInt(values[scoreAIndex]) || 0 : 0;
        const scoreB = scoreBIndex !== -1 ? parseInt(values[scoreBIndex]) || 0 : 0;
        
        let winner = null;
        if (scoreA > scoreB && scoreA > 0) winner = 'A';
        else if (scoreB > scoreA && scoreB > 0) winner = 'B';
        else if (scoreA === scoreB && scoreA > 0) winner = 'draw';
        
        return {
            id: generateUniqueId(),
            matchNumber: i + 1,
            beyA: values[beyAIndex] || '',
            beyB: values[beyBIndex] || '',
            rounds: [], // Start with empty rounds for CSV imports
            scoreA,
            scoreB,
            winner,
            timestamp: new Date().toISOString()
        };
    });
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast(`Imported ${state.matches.length} matches from CSV`, 'success');
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// VALIDATION
// ============================================
function validateMatches() {
    const warnings = [];
    
    state.matches.forEach((match, index) => {
        // Check for ties
        if (match.scoreA === match.scoreB && match.scoreA > 0) {
            warnings.push(`Match ${match.matchNumber}: Tie detected (${match.scoreA}-${match.scoreB})`);
        }
        
        // Check for 0-0
        if (match.scoreA === 0 && match.scoreB === 0 && (match.beyA || match.beyB)) {
            warnings.push(`Match ${match.matchNumber}: No scores entered`);
        }
        
        // Check for missing beys
        if ((match.scoreA > 0 || match.scoreB > 0) && (!match.beyA || !match.beyB)) {
            warnings.push(`Match ${match.matchNumber}: Missing Bey selection`);
        }
        
        // Check for unusual scores (e.g., 10-0)
        if (Math.abs(match.scoreA - match.scoreB) >= 10 && (match.scoreA >= 10 || match.scoreB >= 10)) {
            warnings.push(`Match ${match.matchNumber}: Unusual score (${match.scoreA}-${match.scoreB})`);
        }
    });
    
    if (warnings.length > 0) {
        console.warn('Match validation warnings:', warnings);
    }
    
    return warnings;
}

// ============================================
// LIVE ELO TRACKING
// ============================================

/**
 * Initialize live ELO ratings from baseline
 */
function initializeLiveElos() {
    // If we have saved live ELOs and they're not empty, we're resuming
    if (Object.keys(state.liveElos).length > 0) {
        console.log('Resuming live tournament with existing ELOs');
        return;
    }
    
    // Otherwise, initialize from baseline
    state.liveElos = { ...state.baselineElos };
    state.liveStats = {};
    state.previousPositions = {};
    
    // Initialize stats for all beyblades
    for (const beyName in state.baselineElos) {
        state.liveStats[beyName] = {
            matches: 0,
            wins: 0,
            losses: 0,
            for: 0,
            against: 0,
            winrate: 0.0
        };
    }
    
    console.log('Initialized live ELO tracking with baseline values');
}

/**
 * Reset live tournament to baseline
 */
function resetLiveTournament() {
    const confirmed = confirm('Reset live tournament? This will clear all live ELO changes and match results.');
    if (!confirmed) return;
    
    state.liveElos = { ...state.baselineElos };
    state.liveStats = {};
    state.previousPositions = {};
    state.liveLeaderboard = [];
    state.liveEloHistory = [];
    
    // Initialize stats
    for (const beyName in state.baselineElos) {
        state.liveStats[beyName] = {
            matches: 0,
            wins: 0,
            losses: 0,
            for: 0,
            against: 0,
            winrate: 0.0
        };
    }
    
    // Clear matches
    state.matches = [];
    
    saveToStorage();
    updateLiveLeaderboard();
    renderMatches();
    updateStatusBar();
    
    showToast('Live tournament reset successfully', 'success');
}

/**
 * Process a match and update live ELO ratings
 */
function processMatchForLiveElo(match) {
    if (!state.liveMode) return;
    if (!match.beyA || !match.beyB) return;
    if (match.scoreA === '' || match.scoreB === '') return;
    
    const scoreA = parseInt(match.scoreA) || 0;
    const scoreB = parseInt(match.scoreB) || 0;
    
    // Ensure both beys have ELO ratings
    if (!state.liveElos[match.beyA]) {
        state.liveElos[match.beyA] = state.baselineElos[match.beyA] || ELO_START;
    }
    if (!state.liveElos[match.beyB]) {
        state.liveElos[match.beyB] = state.baselineElos[match.beyB] || ELO_START;
    }
    
    // Ensure both beys have stats
    if (!state.liveStats[match.beyA]) {
        state.liveStats[match.beyA] = {
            matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0
        };
    }
    if (!state.liveStats[match.beyB]) {
        state.liveStats[match.beyB] = {
            matches: 0, wins: 0, losses: 0, for: 0, against: 0, winrate: 0.0
        };
    }
    
    // Use the elo-calculator.js functions
    const result = updateElo(
        match.beyA,
        match.beyB,
        scoreA,
        scoreB,
        state.liveElos,
        state.liveStats
    );
    
    // Store in history
    state.liveEloHistory.push({
        matchId: match.id,
        timestamp: Date.now(),
        ...result
    });
    
    return result;
}

/**
 * Recalculate all live ELOs from scratch
 */
function recalculateAllLiveElos() {
    // Reset to baseline
    state.liveElos = { ...state.baselineElos };
    state.liveStats = {};
    state.liveEloHistory = [];
    
    // Initialize stats for all beyblades
    for (const beyName in state.baselineElos) {
        state.liveStats[beyName] = {
            matches: 0,
            wins: 0,
            losses: 0,
            for: 0,
            against: 0,
            winrate: 0.0
        };
    }
    
    // Process all completed matches in order
    const completedMatches = state.matches.filter(m => 
        m.beyA && m.beyB && m.scoreA !== '' && m.scoreB !== ''
    );
    
    completedMatches.forEach(match => {
        processMatchForLiveElo(match);
    });
    
    console.log('Recalculated all live ELOs:', state.liveElos);
}

/**
 * Update the live leaderboard display
 */
function updateLiveLeaderboard() {
    if (!state.liveMode) {
        document.getElementById('liveLeaderboardPanel')?.classList.add('collapsed');
        return;
    }
    
    // Generate leaderboard
    state.liveLeaderboard = generateLeaderboard(
        state.liveElos,
        state.liveStats,
        state.previousPositions
    );
    
    // Update previous positions for next time
    state.previousPositions = getPositionMap(state.liveLeaderboard);
    
    // Render the leaderboard
    renderLiveLeaderboard();
    
    // Save state
    saveToStorage();
}

/**
 * Render the live leaderboard table
 */
function renderLiveLeaderboard() {
    const tbody = document.getElementById('liveLeaderboardBody');
    if (!tbody) return;
    
    const leaderboard = state.liveLeaderboard;
    
    if (leaderboard.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-state">
                <td colspan="7">No matches entered yet. Start entering matches to see live rankings!</td>
            </tr>
        `;
        return;
    }
    
    // Show only beys with at least one match
    const activeLeaderboard = leaderboard.filter(entry => entry.matches > 0);
    
    if (activeLeaderboard.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-state">
                <td colspan="7">No matches entered yet. Start entering matches to see live rankings!</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = activeLeaderboard.map(entry => {
        const baselineElo = state.baselineElos[entry.bey] || ELO_START;
        const eloDelta = entry.elo - baselineElo;
        
        // Rank badge for top 3
        let rankDisplay;
        if (entry.position <= 3) {
            rankDisplay = `<span class="rank-badge rank-${entry.position}">${entry.position}</span>`;
        } else {
            rankDisplay = entry.position;
        }
        
        // Position delta
        let positionDeltaDisplay = '';
        if (entry.positionDelta > 0) {
            positionDeltaDisplay = `<span class="position-delta up">
                <span class="position-delta-icon">↑</span>${entry.positionDelta}
            </span>`;
        } else if (entry.positionDelta < 0) {
            positionDeltaDisplay = `<span class="position-delta down">
                <span class="position-delta-icon">↓</span>${Math.abs(entry.positionDelta)}
            </span>`;
        } else {
            positionDeltaDisplay = `<span class="position-delta neutral">—</span>`;
        }
        
        // ELO change
        let eloChangeDisplay;
        if (eloDelta > 0) {
            eloChangeDisplay = `<span class="elo-change positive">+${eloDelta}</span>`;
        } else if (eloDelta < 0) {
            eloChangeDisplay = `<span class="elo-change negative">${eloDelta}</span>`;
        } else {
            eloChangeDisplay = `<span class="elo-change neutral">—</span>`;
        }
        
        // Record
        const recordDisplay = `<span class="record-display">
            <span class="record-wins">${entry.wins}</span>-<span class="record-losses">${entry.losses}</span>
        </span>`;
        
        // Winrate
        const winratePercent = (entry.winrate * 100).toFixed(0);
        let winrateClass = 'winrate-medium';
        if (entry.winrate >= 0.6) winrateClass = 'winrate-high';
        else if (entry.winrate < 0.4) winrateClass = 'winrate-low';
        
        const winrateDisplay = `<span class="winrate-display ${winrateClass}">${winratePercent}%</span>`;
        
        return `
            <tr class="leaderboard-row" data-bey="${escapeHtml(entry.bey)}">
                <td class="col-rank">${rankDisplay}</td>
                <td class="col-delta">${positionDeltaDisplay}</td>
                <td class="col-bey">${escapeHtml(entry.bey)}</td>
                <td class="col-elo">${entry.elo}</td>
                <td class="col-elo-change">${eloChangeDisplay}</td>
                <td class="col-record">${recordDisplay}</td>
                <td class="col-winrate">${winrateDisplay}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Toggle live leaderboard panel
 */
function toggleLiveLeaderboard() {
    const panel = document.getElementById('liveLeaderboardPanel');
    if (panel) {
        panel.classList.toggle('collapsed');
    }
}

/**
 * Toggle live mode on/off
 */
function toggleLiveMode() {
    state.liveMode = !state.liveMode;
    saveToStorage();
    
    if (state.liveMode) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
        showToast('Live mode enabled', 'success');
    } else {
        showToast('Live mode disabled', 'info');
    }
}

/**
 * Show a post-match summary modal with ELO changes
 */
function showPostMatchSummary(eloResult) {
    if (!eloResult) return;
    
    const summary = `
        <div class="post-match-summary">
            <h3>Match Complete!</h3>
            <div class="summary-row">
                <span class="summary-label">${escapeHtml(eloResult.beyA)}</span>
                <span class="summary-value">${Math.round(eloResult.eloA)} → ${Math.round(eloResult.newEloA)}</span>
                <span class="summary-delta ${eloResult.eloChangeA >= 0 ? 'positive' : 'negative'}">
                    ${eloResult.eloChangeA >= 0 ? '+' : ''}${Math.round(eloResult.eloChangeA)}
                </span>
            </div>
            <div class="summary-row">
                <span class="summary-label">${escapeHtml(eloResult.beyB)}</span>
                <span class="summary-value">${Math.round(eloResult.eloB)} → ${Math.round(eloResult.newEloB)}</span>
                <span class="summary-delta ${eloResult.eloChangeB >= 0 ? 'positive' : 'negative'}">
                    ${eloResult.eloChangeB >= 0 ? '+' : ''}${Math.round(eloResult.eloChangeB)}
                </span>
            </div>
        </div>
    `;
    
    // You could show this in a toast or modal
    // For now, we'll just log it
    console.log('Post-match summary:', eloResult);
}

