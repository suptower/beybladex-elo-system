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
    SPIN: { id: 'spin', label: 'Spin', points: 1, emoji: '🔄' },
    BURST: { id: 'burst', label: 'Burst', points: 2, emoji: '💥' },
    POCKET: { id: 'pocket', label: 'Pocket', points: 2, emoji: '🎯' },
    STADIUM_EXIT: { id: 'stadium_exit', label: 'Stadium Exit', points: 2, emoji: '🥏' },
    EXTREME: { id: 'extreme', label: 'Extreme', points: 3, emoji: '⚡' }
};

// Fallback image for missing bey images (SVG placeholder)
const BEY_IMAGE_FALLBACK = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23444'/%3E%3Ctext x='50' y='50' text-anchor='middle' dominant-baseline='middle' fill='white' font-size='40'%3E?%3C/text%3E%3C/svg%3E";

// ============================================
// ELO CALCULATION CONSTANTS
// ============================================
// Dynamic K-factor matching the Python engine (beyblade_elo.py)
const K_LEARNING    = 40; // < 6 matches played
const K_INTERMEDIATE = 24; // 6–14 matches played
const K_EXPERIENCED  = 12; // 15+ matches played
const DEFAULT_ELO = 1000; // Default ELO rating for new players
const DEFAULT_MATCH_TYPE = 'exhibition';

/**
 * Return the K-factor for a bey based on total matches played (including
 * the baseline matches already recorded in leaderboard.csv).
 */
function dynamicK(beyName) {
    const bey = state.beyblades.find(b => b.name === beyName);
    const totalMatches = bey ? bey.matches : 0;
    if (totalMatches < 6)  return K_LEARNING;
    if (totalMatches < 15) return K_INTERMEDIATE;
    return K_EXPERIENCED;
}

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
 * @param {string} [beyName] - Bey name used to look up the dynamic K-factor
 * @returns {number} ELO change (can be positive or negative)
 */
function calculateEloChange(elo, opponentElo, actualScore, beyName) {
    const expectedScore = calculateExpectedScore(elo, opponentElo);
    const k = beyName ? dynamicK(beyName) : K_EXPERIENCED;
    return Math.round(k * (actualScore - expectedScore));
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
    recommendedMatches: [], // Recommended match data
    focusedMatchIndex: -1,
    // Live ELO tracking
    liveMode: true,
    liveElos: {}, // Current ELO ratings during this tournament
    liveStats: {}, // Current stats (matches, wins, losses, etc.)
    liveLeaderboard: [], // Sorted leaderboard
    previousPositions: {}, // For tracking rank changes
    baselineElos: {}, // Starting ELOs at tournament start
    liveEloHistory: [], // Track all ELO changes in this session
    // Season Tier tracking
    seasonData: null, // Loaded season data (tier assignments)
    seasonTierStandings: {} // Live season standings by tier
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    await loadBeybladeData();
    await loadSeasonData();
    await loadRecommendedMatches();
    loadFromStorage();
    // Re-sync baseline ELOs from current leaderboard.csv, adjusting live ELOs
    // to preserve any in-tournament delta from a resumed session.
    state.beyblades.forEach(bey => {
        const oldBaseline = state.baselineElos[bey.name];
        state.baselineElos[bey.name] = bey.elo;
        if (oldBaseline !== undefined && state.liveElos[bey.name] !== undefined) {
            state.liveElos[bey.name] += (bey.elo - oldBaseline);
        }
    });
    // Always anchor previousPositions to the current baseline ranking so that
    // position deltas in the live leaderboard only reflect in-tournament movement,
    // not global (static) leaderboard position changes.
    const baselineLeaderboard = generateLeaderboard(state.baselineElos, {}, null);
    state.previousPositions = getPositionMap(baselineLeaderboard);
    initializeLiveElos();
    initializeUI();
    setupEventListeners();
    renderMatches();
    updateStatusBar();
    updateLiveLeaderboard();
    updateSeasonTierLeaderboard();
});

// Load beyblade data from CSV
async function loadBeybladeData() {
    try {
        const response = await fetch(DATA_PATHS.LEADERBOARD_CSV);
        const text = await response.text();
        const lines = text.trim().split(/\r?\n/);
        
        state.beyblades = lines.slice(1).map(line => {
            const values = line.split(',');
            return {
                rank: parseInt(values[0]) || null,
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
        const response = await fetch(DATA_PATHS.MATCHES_CSV);
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
                scoreB: parseInt(values[5]) || 0,
                // Arena is at index 10 (11th column): MatchID,Date,BeyA,BeyB,ScoreA,ScoreB,MatchType,SeasonID,Tier,Matchday,arena
                arena: values[10] || 'Xtreme'
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
        const response = await fetch(DATA_PATHS.ROUNDS_CSV);
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

// Load recommended matches data
async function loadRecommendedMatches() {
    try {
        const response = await fetch(DATA_PATHS.RECOMMENDED_MATCHES_JSON);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Collect all recommendations from all categories
        const allRecommendations = [];
        if (data.by_category) {
            for (const category of Object.keys(data.by_category)) {
                allRecommendations.push(...data.by_category[category]);
            }
        }
        
        // Sort all recommendations by information value (descending)
        allRecommendations.sort((a, b) => (b.info_value || 0) - (a.info_value || 0));
        
        // Store all sorted recommendations
        state.recommendedMatches = allRecommendations;
        
        console.log(`Loaded ${state.recommendedMatches.length} recommended matches`);
    } catch (error) {
        console.error('Error loading recommended matches:', error);
        state.recommendedMatches = [];
    }
}

// Load season data (tier assignments)
async function loadSeasonData() {
    try {
        const response = await fetch(DATA_PATHS.SEASON_DATA_JSON);
        if (!response.ok) {
            console.log('No season data found, season tier leaderboard will be disabled');
            return;
        }
        const data = await response.json();
        state.seasonData = data;
        console.log('Loaded season data:', data);
    } catch (error) {
        console.error('Error loading season data:', error);
        state.seasonData = null;
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
    const arenaSelect = document.getElementById('arenaSelect');
    
    if (tournamentNameInput) tournamentNameInput.value = state.tournament.name || '';
    if (roundNumberInput) roundNumberInput.value = state.tournament.round || 1;
    if (formatSelect) formatSelect.value = state.tournament.format || 'swiss';
    if (matchCountInput) matchCountInput.value = state.matches.length || 8;
    if (liveModeToggle) liveModeToggle.checked = state.liveMode;
    if (arenaSelect) arenaSelect.value = state.tournament.arena || 'Xtreme';
    
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
    document.getElementById('arenaSelect')?.addEventListener('change', handleTournamentChange);
    
    // Action buttons
    document.getElementById('generateMatchesBtn')?.addEventListener('click', generateMatches);
    document.getElementById('addMatchBtn')?.addEventListener('click', addMatch);
    document.getElementById('addMatchBtnBottom')?.addEventListener('click', addMatch);
    document.getElementById('addMatchBtnBottomMobile')?.addEventListener('click', addMatch);
    document.getElementById('resetRoundBtn')?.addEventListener('click', resetRound);
    document.getElementById('deleteEmptyBtn')?.addEventListener('click', deleteEmptyMatches);
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
    document.getElementById('recommendedPairingsBtn')?.addEventListener('click', generateRecommendedPairings);
    
    // Shortcuts legend toggle
    document.getElementById('shortcutsHeader')?.addEventListener('click', toggleShortcutsLegend);
    
    // Live leaderboard controls
    document.getElementById('leaderboardHeader')?.addEventListener('click', toggleLiveLeaderboard);
    document.getElementById('leaderboardToggleBtn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleLiveLeaderboard();
    });
    document.getElementById('liveModeToggle')?.addEventListener('change', toggleLiveMode);
    
    // Season tier leaderboard controls
    document.getElementById('seasonLeaderboardHeader')?.addEventListener('click', toggleSeasonTierLeaderboard);
    document.getElementById('seasonLeaderboardToggleBtn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleSeasonTierLeaderboard();
    });
    
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
    state.tournament.arena = document.getElementById('arenaSelect')?.value || 'Xtreme';
    
    // Update arena for all existing matches when it changes
    const selectedArena = state.tournament.arena;
    state.matches.forEach(match => {
        match.arena = selectedArena;
    });
    
    saveToStorage();
    renderMatches(); // Re-render to show updated arena info
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
    // Get settings from the tournament or most recent match (if any)
    let matchType = DEFAULT_MATCH_TYPE;
    let seasonId = '';
    let tier = '';
    let matchday = '';
    let arena = state.tournament.arena || 'Xtreme';
    
    if (state.matches.length > 0) {
        const lastMatch = state.matches[state.matches.length - 1];
        matchType = lastMatch.matchType || DEFAULT_MATCH_TYPE;
        seasonId = lastMatch.seasonId || '';
        tier = lastMatch.tier || '';
        matchday = lastMatch.matchday || '';
        // Only use lastMatch arena if tournament arena is not set
        if (!state.tournament.arena) {
            arena = lastMatch.arena || 'Xtreme';
        }
    }
    
    return {
        id: generateUniqueId(),
        matchNumber: index + 1,
        beyA: '',
        beyB: '',
        rounds: [], // Array of round objects
        scoreA: 0,  // Computed from rounds
        scoreB: 0,  // Computed from rounds
        winner: null,
        timestamp: null,
        // Season fields (copied from most recent match)
        matchType: matchType,
        seasonId: seasonId,
        tier: tier,
        matchday: matchday,
        arena: arena
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

function determineWinner(scoreA, scoreB) {
    const a = parseInt(scoreA) || 0;
    const b = parseInt(scoreB) || 0;
    if (a > b && a > 0) return 'A';
    if (b > a && b > 0) return 'B';
    if (a === b && a > 0) return 'draw';
    return null;
}

// Update match scores from rounds and determine winner
function updateMatchFromRounds(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const { scoreA, scoreB } = calculateScoresFromRounds(match);
    match.scoreA = scoreA;
    match.scoreB = scoreB;
    
    match.winner = determineWinner(scoreA, scoreB);
    
    match.timestamp = new Date().toISOString();
    
    // Process for live ELO if match is complete
    if (state.liveMode && match.beyA && match.beyB && scoreA !== '' && scoreB !== '') {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
        updateSeasonTierLeaderboard();
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
    
    // DO NOT update previousPositions here - it should always reference the baseline positions from tournament start
    // Position deltas will show change from tournament start, not from previous match
    
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
    
    // Recalculate live ELOs after match deletion
    if (state.liveMode) {
        recalculateAllLiveElos();
        updateLiveLeaderboard(); // Don't update baseline positions - maintain comparison to tournament start
        updateSeasonTierLeaderboard();
    }
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
        // Recalculate from baseline (will reset previousPositions to baseline)
        recalculateAllLiveElos();
        
        // Generate baseline leaderboard to reset position tracking
        const baselineLeaderboard = generateLeaderboard(
            state.liveElos,
            state.liveStats,
            null
        );
        state.previousPositions = getPositionMap(baselineLeaderboard);
        
        // Don't pass savePositions=true since we just set previousPositions above
        updateLiveLeaderboard();
        updateSeasonTierLeaderboard();
    }
    
    showToast('Round reset', 'warning');
}

function deleteEmptyMatches() {
    const isEmptyMatch = (match) => {
        const scoreA = parseInt(match.scoreA) || 0;
        const scoreB = parseInt(match.scoreB) || 0;
        const roundsEmpty = !Array.isArray(match.rounds) || match.rounds.length === 0;
        return roundsEmpty && scoreA === 0 && scoreB === 0;
    };

    const emptyCount = state.matches.filter(isEmptyMatch).length;
    if (emptyCount === 0) {
        showToast('No empty matches to delete', 'warning');
        return;
    }

    if (!confirm(`Delete ${emptyCount} empty match${emptyCount === 1 ? '' : 'es'}?`)) {
        return;
    }

    state.matches = state.matches.filter(match => !isEmptyMatch(match));
    state.matches.forEach((match, i) => {
        match.matchNumber = i + 1;
    });

    saveToStorage();
    renderMatches();
    updateStatusBar();

    if (state.liveMode) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
        updateSeasonTierLeaderboard();
    }

    showToast(`Deleted ${emptyCount} empty match${emptyCount === 1 ? '' : 'es'}`, 'warning');
}

function clearAll() {
    if (!confirm('Clear all match data? This cannot be undone.')) {
        return;
    }
    
    state.matches = [];
    state.participants = [];
    
    // Also reset live tournament state (force reset)
    // initializeLiveElos() will set previousPositions to baseline
    initializeLiveElos(true);
    
    saveToStorage();
    renderMatches();
    renderSelectedParticipants();
    updateStatusBar();
    // Don't pass savePositions=true since initializeLiveElos() already set previousPositions
    updateLiveLeaderboard();
    updateSeasonTierLeaderboard();
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
    
    // Update live ELOs if both beys are selected and live mode is enabled
    if (state.liveMode && match.beyA && match.beyB) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
        updateSeasonTierLeaderboard();
    }
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
    
    // Update live ELOs if both beys are selected and live mode is enabled
    if (state.liveMode && match.beyA && match.beyB) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
        updateSeasonTierLeaderboard();
    }
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
        stadium_exit: 0,
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
    
    ['spin', 'burst', 'pocket', 'stadium_exit', 'extreme'].forEach(type => {
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
    
    // Recalculate live ELOs if match has scores and live mode is enabled
    if (state.liveMode && match.beyA && match.beyB && 
        (match.scoreA > 0 || match.scoreB > 0)) {
        recalculateAllLiveElos();
        updateLiveLeaderboard();
    }
}

function updateArena(matchIndex, arena) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    match.arena = arena;
    saveToStorage();
    renderMatches();
    refreshFullscreenIfActive(matchIndex);
}

// Season field update functions
function updateMatchType(matchIndex, matchType) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    match.matchType = matchType;
    
    // Clear fields that don't apply to this match type
    if (matchType === 'exhibition') {
        match.seasonId = '';
        match.tier = '';
        match.matchday = '';
    } else if (matchType === 'relegation' || matchType === 'season_cup') {
        match.tier = '';
        match.matchday = '';
    }
    
    saveToStorage();
    renderMatches();
    updateSeasonTierLeaderboard();
    refreshFullscreenIfActive(matchIndex);
}

function updateSeasonId(matchIndex, seasonId) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    match.seasonId = seasonId;
    saveToStorage();
    renderMatches();
    refreshFullscreenIfActive(matchIndex);
}

function updateTier(matchIndex, tier) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    match.tier = tier;
    saveToStorage();
    renderMatches();
    updateSeasonTierLeaderboard();
    refreshFullscreenIfActive(matchIndex);
}

function updateMatchday(matchIndex, matchday) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    match.matchday = matchday ? parseInt(matchday) : '';
    saveToStorage();
    renderMatches();
    refreshFullscreenIfActive(matchIndex);
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
 * Find recommendation info for a matchup
 * @param {string} beyA - Name of first bey
 * @param {string} beyB - Name of second bey
 * @returns {object|null} Recommendation object or null if not found
 */
function findRecommendation(beyA, beyB) {
    if (!beyA || !beyB) return null;
    
    return state.recommendedMatches.find(rec => 
        (rec.bey_a === beyA && rec.bey_b === beyB) ||
        (rec.bey_a === beyB && rec.bey_b === beyA)
    ) || null;
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
    
    // Check if this match is a recommended match
    const recommendationInfo = match.recommendation || findRecommendation(match.beyA, match.beyB);
    
    // Use live ELOs if available and live mode is enabled, otherwise use static data
    let eloA, eloB, livePositionA, livePositionB, offlinePositionA, offlinePositionB;
    
    // Always get offline positions from CSV
    offlinePositionA = beyAData.rank || null;
    offlinePositionB = beyBData.rank || null;
    
    if (state.liveMode && state.liveElos[match.beyA] && state.liveElos[match.beyB]) {
        eloA = state.liveElos[match.beyA];
        eloB = state.liveElos[match.beyB];
        
        // Get current positions from live leaderboard
        if (state.liveLeaderboard && state.liveLeaderboard.length > 0) {
            const entryA = state.liveLeaderboard.find(entry => entry.bey === match.beyA);
            const entryB = state.liveLeaderboard.find(entry => entry.bey === match.beyB);
            livePositionA = entryA ? entryA.position : null;
            livePositionB = entryB ? entryB.position : null;
        }
    } else {
        eloA = beyAData.elo || DEFAULT_ELO;
        eloB = beyBData.elo || DEFAULT_ELO;
        livePositionA = null;
        livePositionB = null;
    }
    const eloDiff = eloA - eloB;
    
    // Calculate win probabilities
    const probA = calculateExpectedScore(eloA, eloB);
    const probB = 1 - probA;
    
    // Calculate expected ELO changes
    const eloChangeAWin = calculateEloChange(eloA, eloB, 1, match.beyA);
    const eloChangeALoss = calculateEloChange(eloA, eloB, 0, match.beyA);
    const eloChangeBWin = calculateEloChange(eloB, eloA, 1, match.beyB);
    const eloChangeBLoss = calculateEloChange(eloB, eloA, 0, match.beyB);
    
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
        spin: '🔄',
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
    
    // Build recommendation display if this match is recommended
    let recommendationDisplay = '';
    if (recommendationInfo) {
        const categoryIcons = {
            'meta_balance': '⚖️',
            'high_uncertainty': '🎲',
            'elo_clarity': '🔍',
            'low_data_exploration': '📊',
            'upset_testing': '⚡'
        };
        const categoryLabels = {
            'meta_balance': 'Meta Balance',
            'high_uncertainty': 'High Uncertainty',
            'elo_clarity': 'ELO Clarity',
            'low_data_exploration': 'Low Data Exploration',
            'upset_testing': 'Upset Testing'
        };
        
        const categoryIcon = categoryIcons[recommendationInfo.category] || '🎯';
        const categoryLabel = categoryLabels[recommendationInfo.category] || recommendationInfo.category;
        const infoValue = recommendationInfo.info_value || recommendationInfo.infoValue || 0;
        
        recommendationDisplay = `
            <div class="analysis-section recommendation-info">
                <div class="recommendation-badge">
                    ${categoryIcon} <strong>Recommended Match</strong>
                </div>
                <div class="recommendation-details">
                    <div class="recommendation-category">
                        <span class="recommendation-label">Category:</span>
                        <span class="recommendation-value">${categoryLabel}</span>
                    </div>
                    <div class="recommendation-score">
                        <span class="recommendation-label">Info Value:</span>
                        <span class="recommendation-value">${infoValue.toFixed(1)}</span>
                    </div>
                </div>
                <div class="recommendation-explanation">
                    ${escapeHtml(recommendationInfo.explanation)}
                </div>
            </div>
        `;
    }
    
    // Determine which tabs to show
    const showRecommendationTab = recommendationInfo !== null;
    const showHistoryTab = (h2hDisplay !== '' || finishDisplay !== '');
    
    return `
        <div class="match-analysis-panel collapsed" id="${idPrefix}_${matchIndex}">
            <div class="analysis-toggle" onclick="toggleAnalysisPanel('${idPrefix}_${matchIndex}')">
                <span class="analysis-toggle-icon">▶</span>
                <span class="analysis-toggle-text">📊 Pre-Match Analysis</span>
                ${favoredText}
            </div>
            
            <div class="analysis-content" style="display: none;">
                <div class="analysis-tabs">
                    <button class="analysis-tab active" onclick="switchAnalysisTab(event, '${idPrefix}_${matchIndex}', 'overview')">
                        📊 Overview
                    </button>
                    ${showHistoryTab ? `
                        <button class="analysis-tab" onclick="switchAnalysisTab(event, '${idPrefix}_${matchIndex}', 'history')">
                            📜 History
                        </button>
                    ` : ''}
                    <button class="analysis-tab" onclick="switchAnalysisTab(event, '${idPrefix}_${matchIndex}', 'whatif')">
                        🔮 What-If
                    </button>
                    ${showRecommendationTab ? `
                        <button class="analysis-tab" onclick="switchAnalysisTab(event, '${idPrefix}_${matchIndex}', 'recommendation')">
                            🎯 Recommended
                        </button>
                    ` : ''}
                </div>
                
                <div class="analysis-tab-content active" id="${idPrefix}_${matchIndex}_overview">
                    <div class="analysis-section elo-ratings">
                        <div class="elo-rating-item elo-a">
                            <span class="elo-bey-name">${escapeHtml(match.beyA)}</span>
                            ${livePositionA && offlinePositionA ? `<span class="elo-position">#${offlinePositionA} → #${livePositionA}</span>` : 
                              livePositionA ? `<span class="elo-position">#${livePositionA}</span>` :
                              offlinePositionA ? `<span class="elo-position">#${offlinePositionA}</span>` : ''}
                            <span class="elo-value">${Math.round(eloA)}</span>
                        </div>
                        <div class="elo-diff">
                            <span class="elo-diff-label">ΔELO</span>
                            <span class="elo-diff-value ${eloDiff >= 0 ? 'positive' : 'negative'}">${eloDiff >= 0 ? '+' : ''}${Math.round(eloDiff)}</span>
                        </div>
                        <div class="elo-rating-item elo-b">
                            <span class="elo-bey-name">${escapeHtml(match.beyB)}</span>
                            ${livePositionB && offlinePositionB ? `<span class="elo-position">#${offlinePositionB} → #${livePositionB}</span>` : 
                              livePositionB ? `<span class="elo-position">#${livePositionB}</span>` :
                              offlinePositionB ? `<span class="elo-position">#${offlinePositionB}</span>` : ''}
                            <span class="elo-value">${Math.round(eloB)}</span>
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
                </div>
                
                ${showHistoryTab ? `
                    <div class="analysis-tab-content" id="${idPrefix}_${matchIndex}_history" style="display: none;">
                        ${h2hDisplay}
                        ${finishDisplay}
                    </div>
                ` : ''}
                
                <div class="analysis-tab-content" id="${idPrefix}_${matchIndex}_whatif" style="display: none;">
                    <div class="analysis-section elo-changes">
                        <div class="elo-change-label">Expected ELO Changes</div>
                        <div class="elo-change-outcomes">
                            <div class="elo-outcome">
                                <span class="outcome-label">If ${escapeHtml(match.beyA)} wins:</span>
                                <span class="outcome-values">
                                    <span class="elo-change ${eloChangeAWin >= 0 ? 'positive' : 'negative'}">${eloChangeAWin >= 0 ? '+' : ''}${Math.round(eloChangeAWin)}</span>
                                    <span class="outcome-separator">/</span>
                                    <span class="elo-change ${eloChangeBLoss >= 0 ? 'positive' : 'negative'}">${eloChangeBLoss >= 0 ? '+' : ''}${Math.round(eloChangeBLoss)}</span>
                                </span>
                            </div>
                            <div class="elo-outcome">
                                <span class="outcome-label">If ${escapeHtml(match.beyB)} wins:</span>
                                <span class="outcome-values">
                                    <span class="elo-change ${eloChangeALoss >= 0 ? 'positive' : 'negative'}">${eloChangeALoss >= 0 ? '+' : ''}${Math.round(eloChangeALoss)}</span>
                                    <span class="outcome-separator">/</span>
                                    <span class="elo-change ${eloChangeBWin >= 0 ? 'positive' : 'negative'}">${eloChangeBWin >= 0 ? '+' : ''}${Math.round(eloChangeBWin)}</span>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                
                ${showRecommendationTab ? `
                    <div class="analysis-tab-content" id="${idPrefix}_${matchIndex}_recommendation" style="display: none;">
                        ${recommendationDisplay}
                    </div>
                ` : ''}
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
                <button class="quick-add-btn spin-a" onclick="addRound(${matchIndex}, 'A', 'spin')" title="Spin Finish (+1)">🔄</button>
                <button class="quick-add-btn burst-a" onclick="addRound(${matchIndex}, 'A', 'burst')" title="Burst Finish (+2)">💥</button>
                <button class="quick-add-btn pocket-a" onclick="addRound(${matchIndex}, 'A', 'pocket')" title="Pocket Finish (+2)">🎯</button>
                <button class="quick-add-btn stadium-exit-a" onclick="addRound(${matchIndex}, 'A', 'stadium_exit')" title="Stadium Exit (+2)">🥏</button>
                <button class="quick-add-btn extreme-a" onclick="addRound(${matchIndex}, 'A', 'extreme')" title="Extreme Finish (+3)">⚡</button>
            </div>
            <div class="quick-add-group">
                <span class="quick-add-label">${beyBName} wins:</span>
                <button class="quick-add-btn spin-b" onclick="addRound(${matchIndex}, 'B', 'spin')" title="Spin Finish (+1)">🔄</button>
                <button class="quick-add-btn burst-b" onclick="addRound(${matchIndex}, 'B', 'burst')" title="Burst Finish (+2)">💥</button>
                <button class="quick-add-btn pocket-b" onclick="addRound(${matchIndex}, 'B', 'pocket')" title="Pocket Finish (+2)">🎯</button>
                <button class="quick-add-btn stadium-exit-b" onclick="addRound(${matchIndex}, 'B', 'stadium_exit')" title="Stadium Exit (+2)">🥏</button>
                <button class="quick-add-btn extreme-b" onclick="addRound(${matchIndex}, 'B', 'extreme')" title="Extreme Finish (+3)">⚡</button>
            </div>
        </div>
    `;
}

// Render season fields for a match
function renderSeasonFields(matchIndex, match) {
    const matchType = match.matchType || 'exhibition';
    const seasonId = match.seasonId || '';
    const tier = match.tier || '';
    const matchday = match.matchday || '';
    const arena = match.arena || 'Xtreme';
    
    const isSeasonMatch = matchType === 'season';
    const needsSeasonId = matchType !== 'exhibition';
    
    // Build season ID options from loaded season data or a sensible default list
    let seasonKeys = (state.seasonData && state.seasonData.seasons)
        ? Object.keys(state.seasonData.seasons)
        : ['S1', 'S2', 'S3'];
    // Ensure the currently saved seasonId is always present in the list
    if (seasonId && !seasonKeys.includes(seasonId)) {
        seasonKeys = [...seasonKeys, seasonId];
    }
    const seasonOptions = ['', ...seasonKeys].map(key => {
        const label = key ? escapeHtml(key) : '—';
        return `<option value="${escapeHtml(key)}" ${seasonId === key ? 'selected' : ''}>${label}</option>`;
    }).join('');

    // Build tier options from the selected season's league_tables, defaulting to 3 tiers
    let tierCount = 3;
    if (state.seasonData && seasonId && state.seasonData.seasons[seasonId]) {
        const tables = state.seasonData.seasons[seasonId].league_tables || {};
        const tierNums = Object.keys(tables).map(key => parseInt(key)).filter(n => !isNaN(n));
        if (tierNums.length > 0) tierCount = Math.max(...tierNums);
    }
    const tierOptions = ['', ...Array.from({length: tierCount}, (_, i) => String(i + 1))].map(tierKey =>
        `<option value="${tierKey}" ${tier === tierKey ? 'selected' : ''}>${tierKey ? `Tier ${tierKey}` : '—'}</option>`
    ).join('');

    // Build matchday options from the selected season's matchdays, defaulting to 9
    let maxMatchday = 9;
    if (state.seasonData && seasonId && state.seasonData.seasons[seasonId]) {
        // calculate matchdays by checking how many participants are in tier 1
        // assumption: all tier sizes will stay the same as tier I, so we can use that to calculate the number of matchdays (rounds) in the season
        const mds = Math.max(((state.seasonData.seasons[seasonId].league_tables?.['1']?.length) - 1), 0);
        if (Number.isFinite(mds)) {
            maxMatchday = mds;
        }
    }
    const matchdayOptions = ['', ...Array.from({length: maxMatchday}, (_, i) => i + 1)].map(mdKey =>
        `<option value="${mdKey}" ${String(matchday) === String(mdKey) ? 'selected' : ''}>${mdKey === '' ? '—' : mdKey}</option>`
    ).join('');

    return `
        <div class="match-season-fields">
            <div class="season-field-group">
                <label class="season-field-label">🏆 Match Type</label>
                <select class="season-field-select" onchange="updateMatchType(${matchIndex}, this.value)" data-match="${matchIndex}">
                    <option value="exhibition" ${matchType === 'exhibition' ? 'selected' : ''}>Exhibition</option>
                    <option value="season" ${matchType === 'season' ? 'selected' : ''}>Season League</option>
                    <option value="relegation" ${matchType === 'relegation' ? 'selected' : ''}>Relegation Match</option>
                    <option value="qualification" ${matchType === 'qualification' ? 'selected' : ''}>Qualification Tournament</option>
                    <option value="season_cup" ${matchType === 'season_cup' ? 'selected' : ''}>Season Cup</option>
                </select>
            </div>
            <div class="season-field-group">
                <label class="season-field-label">🏟️ Arena</label>
                <select class="season-field-select" onchange="updateArena(${matchIndex}, this.value)" data-match="${matchIndex}">
                    <option value="Xtreme" ${arena === 'Xtreme' ? 'selected' : ''}>⚡ Xtreme Stadium</option>
                    <option value="DropAttack" ${arena === 'DropAttack' ? 'selected' : ''}>🎯 Drop Attack Beystadium</option>
                    <option value="DoubleXtreme" ${arena === 'DoubleXtreme' ? 'selected' : ''}>💢 Double Xtreme Stadium</option>
                </select>
            </div>
            <div class="season-field-group ${needsSeasonId ? '' : 'field-disabled'}">
                <label class="season-field-label">📅 Season ID</label>
                <select class="season-field-select" onchange="updateSeasonId(${matchIndex}, this.value)" ${needsSeasonId ? '' : 'disabled'}>
                    ${seasonOptions}
                </select>
            </div>
            <div class="season-field-group ${isSeasonMatch ? '' : 'field-disabled'}">
                <label class="season-field-label">🎯 Tier</label>
                <select class="season-field-select season-field-small" onchange="updateTier(${matchIndex}, this.value)" ${isSeasonMatch ? '' : 'disabled'}>
                    ${tierOptions}
                </select>
            </div>
            <div class="season-field-group ${isSeasonMatch ? '' : 'field-disabled'}">
                <label class="season-field-label">📆 Matchday</label>
                <select class="season-field-select season-field-small" onchange="updateMatchday(${matchIndex}, this.value)" ${isSeasonMatch ? '' : 'disabled'}>
                    ${matchdayOptions}
                </select>
            </div>
        </div>
    `;
}

function renderMatchTable() {
    const tbody = document.getElementById('matchEntryBody');
    if (!tbody) return;
    
    // Preserve open rounds panel state before re-rendering
    const openRoundsPanels = new Set();
    state.matches.forEach((_, index) => {
        const panel = document.getElementById(`roundsPanel_${index}`);
        if (panel && panel.style.display !== 'none') {
            openRoundsPanels.add(index);
        }
    });
    
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
                        <button class="row-action-btn fullscreen-btn" onclick="enterFullscreenMatch(${index})" aria-label="Fullscreen mode" title="Fullscreen">⛶</button>
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
                                <span>🔄 Spin (+1)</span>
                                <span>💥 Burst (+2)</span>
                                <span>🎯 Pocket (+2)</span>
                                <span>🥏 Stadium Exit (+2)</span>
                                <span>⚡ Extreme (+3)</span>
                            </div>
                        </div>
                        ${renderSeasonFields(index, match)}
                        ${renderQuickAddButtons(index, match)}
                        <div class="rounds-list">
                            ${renderRoundsList(match, index)}
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    // Restore open rounds panel state after re-rendering
    openRoundsPanels.forEach(index => {
        const panel = document.getElementById(`roundsPanel_${index}`);
        if (panel) panel.style.display = 'table-row';
    });
}

function renderMatchCards() {
    const container = document.getElementById('matchCardsContainer');
    if (!container) return;
    
    // Preserve open card rounds panel state before re-rendering
    const openCardPanels = new Set();
    state.matches.forEach((_, index) => {
        const panel = document.getElementById(`cardRoundsPanel_${index}`);
        if (panel && panel.style.display !== 'none') {
            openCardPanels.add(index);
        }
    });
    
    container.innerHTML = state.matches.map((match, index) => {
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        const cardClass = isComplete ? 'complete' : (isIncomplete ? 'incomplete' : '');
        const hasRounds = match.rounds && match.rounds.length > 0;
        
        return `
            <div class="match-card ${cardClass}" data-index="${index}">
                <div class="match-card-header">
                    <span class="match-card-number">Match ${match.matchNumber}</span>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button class="match-card-fullscreen-btn" onclick="enterFullscreenMatch(${index})" title="Open in fullscreen">
                            ⛶ Fullscreen
                        </button>
                        <span class="match-card-winner">${renderWinnerIndicator(match)}</span>
                    </div>
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
                        ${renderSeasonFields(index, match)}
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
    
    // Restore open card rounds panel state after re-rendering
    openCardPanels.forEach(index => {
        const panel = document.getElementById(`cardRoundsPanel_${index}`);
        if (panel) panel.style.display = 'block';
    });
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
            content.style.display = 'block';
            icon.textContent = '▼';
        } else {
            // Collapse
            panel.classList.add('collapsed');
            content.style.display = 'none';
            icon.textContent = '▶';
        }
    }
}

// Switch between analysis tabs
function switchAnalysisTab(event, panelId, tabName) {
    event.stopPropagation();
    
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // Remove active class from all tabs in this panel
    const tabs = panel.querySelectorAll('.analysis-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Hide all tab contents in this panel
    const tabContents = panel.querySelectorAll('.analysis-tab-content');
    tabContents.forEach(content => {
        content.style.display = 'none';
        content.classList.remove('active');
    });
    
    // Activate the clicked tab
    event.target.classList.add('active');
    
    // Show the corresponding tab content
    const targetContent = document.getElementById(`${panelId}_${tabName}`);
    if (targetContent) {
        targetContent.style.display = 'block';
        targetContent.classList.add('active');
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

function renderArenaSelect(selectedArena, matchIndex) {
    return `
        <select class="arena-select has-value" 
                onchange="updateArena(${matchIndex}, this.value)"
                data-match="${matchIndex}">
            <option value="Xtreme" ${selectedArena === 'Xtreme' ? 'selected' : ''}>⚡ Xtreme</option>
            <option value="DropAttack" ${selectedArena === 'DropAttack' ? 'selected' : ''}>🎯 Drop Attack</option>
            <option value="DoubleXtreme" ${selectedArena === 'DoubleXtreme' ? 'selected' : ''}>⚡⚡ Double Xtreme</option>
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

function generateRecommendedPairings() {
    if (state.recommendedMatches.length === 0) {
        showToast('No recommended matches available', 'error');
        return;
    }
    
    // Get the top N recommended matches that haven't been played yet
    const count = parseInt(document.getElementById('matchCount')?.value) || 8;
    
    // Warn if fewer recommendations than requested
    if (state.recommendedMatches.length < count) {
        showToast(`Only ${state.recommendedMatches.length} recommendations available (requested ${count})`, 'warning');
    }
    
    const topRecommendations = state.recommendedMatches.slice(0, count);
    
    // Create matches from recommendations
    state.matches = [];
    topRecommendations.forEach((rec, i) => {
        state.matches.push({
            id: generateUniqueId(),
            matchNumber: i + 1,
            beyA: rec.bey_a,
            beyB: rec.bey_b,
            rounds: [],
            scoreA: 0,
            scoreB: 0,
            winner: null,
            timestamp: null,
            recommendation: {
                category: rec.category,
                infoValue: rec.info_value,
                explanation: rec.explanation
            }
        });
    });
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast(`Generated ${state.matches.length} recommended pairings`, 'success');
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
    
    // filename should be: ddmmyy_session.json
    const todayDate = new Date();
    const filename = `${String(todayDate.getDate()).padStart(2, '0')}${String(todayDate.getMonth() + 1).padStart(2, '0')}${String(todayDate.getFullYear()).slice(-2)}_session.json`;
    downloadFile(url, filename);
    
    showToast('Exported as JSON', 'success');
}

function exportCSV() {
    // Export match-level CSV with season fields from each match
    const headers = ['MatchID', 'Date', 'BeyA', 'BeyB', 'ScoreA', 'ScoreB', 'MatchType', 'SeasonID', 'Tier', 'Matchday', 'arena'];
    const rows = state.matches.map((match, i) => {
        const date = match.timestamp ? new Date(match.timestamp).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
        return [
            `M${String(i + 1).padStart(4, '0')}`,
            date,
            match.beyA || '',
            match.beyB || '',
            match.scoreA,
            match.scoreB,
            match.matchType || 'exhibition',
            match.seasonId || '',
            match.tier || '',
            match.matchday || '',
            match.arena || 'Xtreme'
        ];
    });
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    // filename should be: ddmmyy_session_matches.csv
    const todayDate = new Date();
    const filename = `${String(todayDate.getDate()).padStart(2, '0')}${String(todayDate.getMonth() + 1).padStart(2, '0')}${String(todayDate.getFullYear()).slice(-2)}_session_matches.csv`;
    downloadFile(url, filename);
    
    showToast('Exported as CSV', 'success');
}

// Export detailed rounds CSV
function exportRoundsCSV() {
    // Format compatible with ./data/matches/rounds.csv
    const headers = ['MatchID', 'round_number', 'winner', 'finish_type', 'points_awarded', 'notes'];
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
    
    // filename should be: ddmmyy_session_rounds.csv
    const todayDate = new Date();
    const filename = `${String(todayDate.getDate()).padStart(2, '0')}${String(todayDate.getMonth() + 1).padStart(2, '0')}${String(todayDate.getFullYear()).slice(-2)}_session_rounds.csv`;
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

    const mapImportedMatch = (match, i) => {
        const rounds = Array.isArray(match.rounds) ? match.rounds : [];
        const scoreA = parseInt(match.scoreA ?? match.score_a) || 0;
        const scoreB = parseInt(match.scoreB ?? match.score_b) || 0;
        const matchdayRaw = match.matchday ?? match.match_day ?? '';
        const parsedMatchday = parseInt(matchdayRaw);
        const matchday = Number.isFinite(parsedMatchday) ? parsedMatchday : '';

        const normalizedMatchType = String(match.matchType || match.match_type || DEFAULT_MATCH_TYPE).toLowerCase();
        const imported = {
            id: match.id || match.match_id || generateUniqueId(),
            matchNumber: match.matchNumber || match.match_number || i + 1,
            beyA: match.beyA || match.bey_a || '',
            beyB: match.beyB || match.bey_b || '',
            rounds,
            scoreA,
            scoreB,
            winner: match.winner || null,
            timestamp: match.timestamp || null,
            matchType: normalizedMatchType,
            seasonId: match.seasonId || match.season_id || '',
            tier: match.tier ?? '',
            matchday,
            arena: match.arena || 'Xtreme'
        };
        
        // If rounds exist, recalculate scores from rounds
        if (imported.rounds.length > 0) {
            const { scoreA: roundScoreA, scoreB: roundScoreB } = calculateScoresFromRounds(imported);
            imported.scoreA = roundScoreA;
            imported.scoreB = roundScoreB;
        }
        imported.winner = determineWinner(imported.scoreA, imported.scoreB);
        
        return imported;
    };
    
    if (data.tournament) {
        state.tournament = data.tournament;
        document.getElementById('tournamentName').value = state.tournament.name || '';
        document.getElementById('roundNumber').value = state.tournament.round || 1;
        document.getElementById('formatSelect').value = state.tournament.format || 'swiss';
    }
    
    if (Array.isArray(data)) {
        state.matches = data.map(mapImportedMatch);
    } else if (data.matches && Array.isArray(data.matches)) {
        state.matches = data.matches.map(mapImportedMatch);
    }
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast('Imported JSON data', 'success');
}

function importCSV(content) {
    const lines = content.trim().split(/\r?\n/);
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    const compactHeaders = headers.map(h => h.replace(/[\s_]+/g, ''));
    
    // Find column indices
    const beyAIndex = compactHeaders.findIndex(h => h === 'beya');
    const beyBIndex = compactHeaders.findIndex(h => h === 'beyb');
    const scoreAIndex = compactHeaders.findIndex(h => h === 'scorea');
    const scoreBIndex = compactHeaders.findIndex(h => h === 'scoreb');
    const matchTypeIndex = compactHeaders.findIndex(h => h === 'matchtype');
    const seasonIdIndex = compactHeaders.findIndex(h => h === 'seasonid');
    const tierIndex = compactHeaders.findIndex(h => h === 'tier');
    const matchdayIndex = compactHeaders.findIndex(h => h === 'matchday');
    const arenaIndex = compactHeaders.findIndex(h => h === 'arena');
    
    if (beyAIndex === -1 || beyBIndex === -1) {
        showToast('CSV must have BeyA and BeyB columns', 'error');
        return;
    }
    
    state.matches = lines.slice(1).filter(line => line.trim()).map((line, i) => {
        // Simple CSV parsing - handles basic cases
        const values = line.split(',').map(v => v.trim());
        const scoreA = scoreAIndex !== -1 ? parseInt(values[scoreAIndex]) || 0 : 0;
        const scoreB = scoreBIndex !== -1 ? parseInt(values[scoreBIndex]) || 0 : 0;
        const matchTypeRaw = matchTypeIndex !== -1 && values[matchTypeIndex] ? values[matchTypeIndex] : '';
        const matchType = matchTypeRaw ? matchTypeRaw.toLowerCase() : DEFAULT_MATCH_TYPE;
        const seasonId = seasonIdIndex !== -1 && values[seasonIdIndex] ? values[seasonIdIndex] : '';
        const tier = tierIndex !== -1 && values[tierIndex] ? values[tierIndex] : '';
        const parsedMatchday = matchdayIndex !== -1 ? parseInt(values[matchdayIndex]) : NaN;
        const matchday = Number.isFinite(parsedMatchday) ? parsedMatchday : '';
        const arena = arenaIndex !== -1 && values[arenaIndex] ? values[arenaIndex] : 'Xtreme';
        
        const winner = determineWinner(scoreA, scoreB);
        
        return {
            id: generateUniqueId(),
            matchNumber: i + 1,
            beyA: values[beyAIndex] || '',
            beyB: values[beyBIndex] || '',
            rounds: [], // Start with empty rounds for CSV imports
            scoreA,
            scoreB,
            winner,
            timestamp: new Date().toISOString(),
            matchType,
            seasonId,
            tier,
            matchday,
            arena
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
 * @param {boolean} forceReset - Force reset even if live ELOs exist
 */
function initializeLiveElos(forceReset = false) {
    // If we have saved live ELOs and they're not empty, we're resuming (unless forced reset)
    if (!forceReset && Object.keys(state.liveElos).length > 0) {
        console.log('Resuming live tournament with existing ELOs');
        return;
    }
    
    // Otherwise, initialize from baseline
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
    
    // Generate baseline leaderboard to capture initial positions
    const baselineLeaderboard = generateLeaderboard(
        state.liveElos,
        state.liveStats,
        null  // No previous positions for baseline
    );
    
    // Set previousPositions to baseline positions so first match shows deltas
    state.previousPositions = getPositionMap(baselineLeaderboard);
    
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
    
    // Generate baseline leaderboard to capture initial positions
    const baselineLeaderboard = generateLeaderboard(
        state.liveElos,
        state.liveStats,
        null  // No previous positions for baseline
    );
    
    // Set previousPositions to baseline positions so first match shows deltas
    state.previousPositions = getPositionMap(baselineLeaderboard);
    
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
 * @param {boolean} savePositions - Whether to save current positions as the new baseline for future delta calculations.
 *                                   Set to true for match-level operations (add/delete/reset) but false for incremental round additions.
 */
function updateLiveLeaderboard(savePositions = false) {
    if (!state.liveMode) {
        document.getElementById('liveLeaderboardPanel')?.classList.add('collapsed');
        return;
    }
    
    // Capture current positions BEFORE generating new leaderboard
    // This ensures we can show position deltas from the previous state
    const oldPositions = state.previousPositions || {};
    
    // Generate NEW leaderboard with OLD positions for delta calculation
    state.liveLeaderboard = generateLeaderboard(
        state.liveElos,
        state.liveStats,
        oldPositions
    );
    
    // Only update previous positions when explicitly requested
    // This prevents position deltas from being reset during incremental round additions
    if (savePositions) {
        state.previousPositions = getPositionMap(state.liveLeaderboard);
    }
    
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
                <td colspan="7">No beys loaded. Please check if leaderboard.csv is available.</td>
            </tr>
        `;
        return;
    }
    
    // Always show all beys in the leaderboard
    tbody.innerHTML = leaderboard.map(entry => {
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
        const roundedEloDelta = Math.round(eloDelta);
        if (roundedEloDelta > 0) {
            eloChangeDisplay = `<span class="elo-change positive">+${roundedEloDelta}</span>`;
        } else if (roundedEloDelta < 0) {
            eloChangeDisplay = `<span class="elo-change negative">${roundedEloDelta}</span>`;
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
                <td class="col-elo">${Math.round(entry.elo)}</td>
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
        updateSeasonTierLeaderboard();
        showToast('Live mode enabled', 'success');
    } else {
        showToast('Live mode disabled', 'info');
    }
}

// ============================================
// SEASON TIER LEADERBOARD FUNCTIONS
// ============================================

/**
 * Calculate season tier standings from current matches
 */
function calculateSeasonTierStandings() {
    if (!state.seasonData) {
        return {};
    }
    
    // Get the current season (use the latest season by ID)
    const seasonKeys = Object.keys(state.seasonData.seasons || {});
    if (seasonKeys.length === 0) return {};
    
    // Sort season keys numerically by their numeric suffix and pick the last one (e.g. "S10" > "S2" > "S1")
    seasonKeys.sort((a, b) => {
        const numA = parseInt(String(a).replace(/^\D+/, ''), 10);
        const numB = parseInt(String(b).replace(/^\D+/, ''), 10);
        
        // If both have valid numeric parts and differ, sort by those numbers
        if (!Number.isNaN(numA) && !Number.isNaN(numB) && numA !== numB) {
            return numA - numB;
        }
        
        // Fallback to lexical comparison to keep ordering stable for non-standard IDs
        return String(a).localeCompare(String(b));
    });
    const currentSeasonId = seasonKeys[seasonKeys.length - 1];
    const currentSeason = state.seasonData.seasons[currentSeasonId];
    
    // Initialize tier standings from season data
    const tierStandings = {};
    
    // Build initial standings from league_tables
    for (const tierNum in currentSeason.league_tables) {
        const tier = parseInt(tierNum);
        tierStandings[tier] = {};
        
        // Initialize each bey in the tier from existing season standings
        currentSeason.league_tables[tierNum].forEach(entry => {
            tierStandings[tier][entry.bey] = {
                bey: entry.bey,
                tier: tier,
                matches: entry.matches || 0,
                wins: entry.wins || 0,
                losses: entry.losses || 0,
                seasonPoints: entry.season_points || 0,
                pointsFor: entry.points_for || 0,
                pointsAgainst: entry.points_against || 0,
                pointDiff: entry.point_diff || 0,
                elo: entry.elo || state.baselineElos[entry.bey] || 1000
            };
        });
    }
    
    // Process all season matches
    const seasonMatches = state.matches.filter(m => 
        m.matchType === 'season' && 
        m.beyA && m.beyB && 
        m.scoreA !== '' && m.scoreB !== ''
    );
    
    seasonMatches.forEach(match => {
        const scoreA = parseInt(match.scoreA) || 0;
        const scoreB = parseInt(match.scoreB) || 0;
        
        // Determine which tier this match belongs to
        // Try to find the tier from the match, or infer from bey assignments
        let matchTier = null;
        if (match.tier) {
            matchTier = parseInt(match.tier);
        } else {
            // Try to infer tier from bey assignments
            for (const tier in tierStandings) {
                if (tierStandings[tier][match.beyA] || tierStandings[tier][match.beyB]) {
                    matchTier = parseInt(tier);
                    break;
                }
            }
        }
        
        if (!matchTier || !tierStandings[matchTier]) return;
        
        // Make sure both beys are in this tier
        if (!tierStandings[matchTier][match.beyA]) {
            tierStandings[matchTier][match.beyA] = {
                bey: match.beyA,
                tier: matchTier,
                matches: 0,
                wins: 0,
                losses: 0,
                seasonPoints: 0,
                pointsFor: 0,
                pointsAgainst: 0,
                pointDiff: 0,
                elo: state.baselineElos[match.beyA] || 1000
            };
        }
        if (!tierStandings[matchTier][match.beyB]) {
            tierStandings[matchTier][match.beyB] = {
                bey: match.beyB,
                tier: matchTier,
                matches: 0,
                wins: 0,
                losses: 0,
                seasonPoints: 0,
                pointsFor: 0,
                pointsAgainst: 0,
                pointDiff: 0,
                elo: state.baselineElos[match.beyB] || 1000
            };
        }
        
        const statA = tierStandings[matchTier][match.beyA];
        const statB = tierStandings[matchTier][match.beyB];
        
        // Update match counts
        statA.matches++;
        statB.matches++;
        
        // Update points for/against
        statA.pointsFor += scoreA;
        statA.pointsAgainst += scoreB;
        statB.pointsFor += scoreB;
        statB.pointsAgainst += scoreA;
        
        // Update point difference
        statA.pointDiff = statA.pointsFor - statA.pointsAgainst;
        statB.pointDiff = statB.pointsFor - statB.pointsAgainst;
        
        // Determine winner and award season points
        if (scoreA > scoreB) {
            statA.wins++;
            statB.losses++;
            // Win = 3 points, Dominant win (4-0) = 4 points
            if (scoreA >= 4 && scoreB === 0) {
                statA.seasonPoints += 4;
            } else {
                statA.seasonPoints += 3;
            }
        } else if (scoreB > scoreA) {
            statB.wins++;
            statA.losses++;
            // Win = 3 points, Dominant win (4-0) = 4 points
            if (scoreB >= 4 && scoreA === 0) {
                statB.seasonPoints += 4;
            } else {
                statB.seasonPoints += 3;
            }
        } else {
            // Draw - no points awarded in this simplified system
            // (could be extended to award 1 point each)
        }
    });
    
    return tierStandings;
}

/**
 * Sort tier standings according to season rules
 */
function sortTierStandings(standings) {
    return Object.values(standings).sort((a, b) => {
        // 1. Season points (descending)
        if (a.seasonPoints !== b.seasonPoints) {
            return b.seasonPoints - a.seasonPoints;
        }
        // 2. Point difference (descending)
        if (a.pointDiff !== b.pointDiff) {
            return b.pointDiff - a.pointDiff;
        }
        // 3. Points scored (descending)
        if (a.pointsFor !== b.pointsFor) {
            return b.pointsFor - a.pointsFor;
        }
        // 4. Current ELO (descending, fallback)
        return b.elo - a.elo;
    });
}

/**
 * Update the season tier leaderboard display
 */
function updateSeasonTierLeaderboard() {
    const panel = document.getElementById('seasonTierLeaderboardPanel');
    if (!panel) return;
    
    if (!state.seasonData) {
        panel.style.display = 'none';
        return;
    }
    
    panel.style.display = 'block';
    
    // Calculate standings
    state.seasonTierStandings = calculateSeasonTierStandings();
    
    // Render
    renderSeasonTierLeaderboard();
}

/**
 * Render the season tier leaderboard
 */
function renderSeasonTierLeaderboard() {
    const container = document.getElementById('seasonTiersContainer');
    if (!container) return;
    
    const tierStandings = state.seasonTierStandings;
    const tiers = Object.keys(tierStandings).sort((a, b) => a - b);
    
    if (tiers.length === 0) {
        container.innerHTML = '<div class="empty-state-message">Enter season matches to see live tier standings!</div>';
        return;
    }
    
    // Generate HTML for each tier
    container.innerHTML = tiers.map(tier => {
        const standings = sortTierStandings(tierStandings[tier]);
        
        // Filter out beys with no matches
        // const activeStandings = standings.filter(s => s.matches > 0);
        const activeStandings = standings; // Show all beys in the tier, even if they haven't played yet
        
        if (activeStandings.length === 0) {
            return `
                <div class="tier-section collapsed" data-tier="${tier}">
                    <div class="tier-header" onclick="toggleTierSection(${tier})">
                        <span class="tier-title">Tier ${tier}</span>
                        <span class="tier-subtitle">No matches played yet</span>
                        <button class="tier-toggle">▼</button>
                    </div>
                </div>
            `;
        }

        const matchCount = Math.round(activeStandings.reduce((sum, s) => sum + s.matches, 0) / 2); // Each match counts for both beys
        const matchesString = matchCount === 1 ? '1 match' : `${matchCount} matches`;
        
        return `
            <div class="tier-section" data-tier="${tier}">
                <div class="tier-header" onclick="toggleTierSection(${tier})">
                    <span class="tier-title">Tier ${tier}</span>
                    <span class="tier-subtitle">${activeStandings.length} beys • ${matchesString}</span>
                    <button class="tier-toggle">▼</button>
                </div>
                <div class="tier-content">
                    <div class="tier-table-wrapper">
                        <table class="season-tier-table">
                            <thead>
                                <tr>
                                    <th class="col-pos">Pos</th>
                                    <th class="col-bey">Bey</th>
                                    <th class="col-played">P</th>
                                    <th class="col-wins">W</th>
                                    <th class="col-losses">L</th>
                                    <th class="col-points">Pts</th>
                                    <th class="col-for">PF</th>
                                    <th class="col-against">PA</th>
                                    <th class="col-diff">+/-</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${activeStandings.map((stat, index) => {
                                    const position = index + 1;
                                    const tierNum = parseInt(tier);
                                    let rowClass = '';
                                    
                                    // Highlight promotion/playoff/relegation zones per tier (Season 2 rules)
                                    if (tierNum === 1) {
                                        // T1: Rank 7 = playoff, Rank 8 = relegated
                                        if (position === 7) rowClass = 'playoff-zone';
                                        else if (position === 8) rowClass = 'relegation-zone';
                                    } else if (tierNum === 2) {
                                        // T2: Rank 1 = promoted, Rank 2 = playoff, Rank 6 = playoff, Ranks 7-8 = relegated
                                        if (position === 1) rowClass = 'promotion-zone';
                                        else if (position === 2 || position === 6) rowClass = 'playoff-zone';
                                        else if (position >= 7) rowClass = 'relegation-zone';
                                    } else if (tierNum === 3) {
                                        // T3: Ranks 1-2 = promoted, Rank 3 = playoff, Rank 6 = playoff, Ranks 7-8 = relegated
                                        if (position <= 2) rowClass = 'promotion-zone';
                                        else if (position === 3 || position === 6) rowClass = 'playoff-zone';
                                        else if (position >= 7) rowClass = 'relegation-zone';
                                    } else if (tierNum === 4) {
                                        // T4: Ranks 1-2 = promoted, Rank 3 = playoff, Ranks 5-8 = qualification pool
                                        if (position <= 2) rowClass = 'promotion-zone';
                                        else if (position === 3) rowClass = 'playoff-zone';
                                        else if (position >= 5) rowClass = 'relegation-zone';
                                    }
                                    
                                    return `
                                        <tr class="season-row ${rowClass}" data-bey="${escapeHtml(stat.bey)}">
                                            <td class="col-pos">${position}</td>
                                            <td class="col-bey">${escapeHtml(stat.bey)}</td>
                                            <td class="col-played">${stat.matches}</td>
                                            <td class="col-wins">${stat.wins}</td>
                                            <td class="col-losses">${stat.losses}</td>
                                            <td class="col-points"><strong>${stat.seasonPoints}</strong></td>
                                            <td class="col-for">${stat.pointsFor}</td>
                                            <td class="col-against">${stat.pointsAgainst}</td>
                                            <td class="col-diff ${stat.pointDiff >= 0 ? 'positive' : 'negative'}">${stat.pointDiff >= 0 ? '+' : ''}${stat.pointDiff}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div class="tier-legend">
                        ${// Show promotion only for tiers that have promotion spots
                            parseInt(tier) === 1 ? '' : `<span class="legend-item"><span class="legend-color promotion-color"></span>Promotion</span>`
                        }
                        <span class="legend-item"><span class="legend-color playoff-color"></span>Playoff</span>
                        <span class="legend-item"><span class="legend-color relegation-color"></span>Relegation / Drop</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Toggle a tier section
 */
function toggleTierSection(tier) {
    const section = document.querySelector(`.tier-section[data-tier="${tier}"]`);
    if (section) {
        section.classList.toggle('collapsed');
    }
}

/**
 * Toggle season tier leaderboard panel
 */
function toggleSeasonTierLeaderboard() {
    const panel = document.getElementById('seasonTierLeaderboardPanel');
    if (panel) {
        panel.classList.toggle('collapsed');
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

// ============================================
// FULLSCREEN MODE FOR MOBILE
// ============================================

/**
 * Enter fullscreen mode for a specific match
 * Provides larger touch-friendly interface for mobile devices
 */
function enterFullscreenMatch(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const overlay = document.getElementById('fullscreenMatchOverlay');
    if (!overlay) return;
    
    const isComplete = match.winner && match.beyA && match.beyB;
    const hasRounds = match.rounds && match.rounds.length > 0;
    
    // Get sorted beyblade names
    const sortedBeyNames = [...state.beyblades].sort((a, b) => a.name.localeCompare(b.name)).map(bey => bey.name);
    
    // Build fullscreen content
    overlay.innerHTML = `
        <div class="fullscreen-header">
            <span class="fullscreen-title">Match ${match.matchNumber}</span>
            <button class="fullscreen-close-btn" onclick="exitFullscreenMatch()">
                ✕ Exit
            </button>
        </div>
        
        <div class="fullscreen-match-content">
            <!-- Bey A Selection -->
            <div class="fullscreen-bey-section">
                <label class="fullscreen-bey-label">Player A</label>
                <button class="fullscreen-bey-picker-btn" onclick="openBeyPicker(${matchIndex}, 'A')">
                    ${match.beyA ? `
                        <img src="./data/beys/${match.beyA}.png" 
                             alt="${escapeHtml(match.beyA)}" 
                             class="fullscreen-bey-picker-img"
                             onerror="this.style.display='none'">
                        <span class="fullscreen-bey-picker-name">${escapeHtml(match.beyA)}</span>
                    ` : `
                        <span class="fullscreen-bey-picker-placeholder">📸 Tap to Select Bey</span>
                    `}
                </button>
            </div>
            
            <!-- Scores Display -->
            <div class="fullscreen-scores-section">
                <div class="fullscreen-scores-display">
                    <div class="fullscreen-score-value score-a ${match.winner === 'A' ? 'score-winner' : ''}">${match.scoreA}</div>
                    <span class="fullscreen-score-separator">:</span>
                    <div class="fullscreen-score-value score-b ${match.winner === 'B' ? 'score-winner' : ''}">${match.scoreB}</div>
                </div>
                ${isComplete ? `<div class="fullscreen-winner-display">🏆 Winner: ${match.winner === 'A' ? match.beyA : match.beyB}</div>` : ''}
            </div>
            
            <!-- Bey B Selection -->
            <div class="fullscreen-bey-section">
                <label class="fullscreen-bey-label">Player B</label>
                <button class="fullscreen-bey-picker-btn" onclick="openBeyPicker(${matchIndex}, 'B')">
                    ${match.beyB ? `
                        <img src="./data/beys/${match.beyB}.png" 
                             alt="${escapeHtml(match.beyB)}" 
                             class="fullscreen-bey-picker-img"
                             onerror="this.style.display='none'">
                        <span class="fullscreen-bey-picker-name">${escapeHtml(match.beyB)}</span>
                    ` : `
                        <span class="fullscreen-bey-picker-placeholder">📸 Tap to Select Bey</span>
                    `}
                </button>
            </div>
            
            <!-- Match Data Section -->
            ${renderSeasonFields(matchIndex, match)}
            
            <!-- Rounds Section -->
            <div class="fullscreen-rounds-section">
                <div class="fullscreen-rounds-header">
                    ⚔️ Rounds (${match.rounds?.length || 0})
                </div>
                
                ${match.beyA && match.beyB ? renderFullscreenQuickAddButtons(matchIndex, match) : '<div style="padding: 1rem; text-align: center; color: var(--text-light);">Select both Beys to add rounds</div>'}
                
                ${hasRounds ? `
                    <div class="fullscreen-rounds-list">
                        ${renderFullscreenRoundsList(match, matchIndex)}
                    </div>
                ` : ''}
            </div>
            
            <!-- Actions -->
            <div class="fullscreen-actions">
                <button class="fullscreen-action-btn btn-delete" onclick="deleteMatch(${matchIndex}); exitFullscreenMatch();">
                    🗑️ Delete Match
                </button>
            </div>
        </div>
    `;
    
    // Close hamburger menu if open to ensure clean state before entering fullscreen
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    if (hamburger && navMenu && hamburger.classList.contains('active')) {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
    }
    
    // Show overlay
    overlay.classList.add('active');
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
}

/**
 * Exit fullscreen mode and return to normal view
 */
function exitFullscreenMatch() {
    const overlay = document.getElementById('fullscreenMatchOverlay');
    if (!overlay) return;
    
    overlay.classList.remove('active');
    document.body.style.overflow = '';
    
    // Re-render matches to update any changes
    renderMatches();
}

/**
 * Re-render the fullscreen overlay if it is currently active
 */
function refreshFullscreenIfActive(matchIndex) {
    const overlay = document.getElementById('fullscreenMatchOverlay');
    if (overlay && overlay.classList.contains('active')) {
        enterFullscreenMatch(matchIndex);
    }
}

/**
 * Render quick add buttons for fullscreen mode
 */
function renderFullscreenQuickAddButtons(matchIndex, match) {
    const MAX_BEY_NAME_LENGTH_FULLSCREEN = 10; // Maximum characters to display for Bey names in fullscreen buttons
    const beyAName = match.beyA ? escapeHtml(match.beyA.substring(0, MAX_BEY_NAME_LENGTH_FULLSCREEN)) : 'A';
    const beyBName = match.beyB ? escapeHtml(match.beyB.substring(0, MAX_BEY_NAME_LENGTH_FULLSCREEN)) : 'B';
    
    return `
        <div class="fullscreen-quick-add">
            ${Object.values(FINISH_TYPES).map(finish => `
                <button class="fullscreen-quick-add-btn" onclick="handleFullscreenRoundClick(this, ${matchIndex}, 'A', '${finish.id}');">
                    <span class="btn-player">${beyAName}</span>
                    <span class="btn-finish">${finish.emoji} ${finish.label}</span>
                </button>
                <button class="fullscreen-quick-add-btn" onclick="handleFullscreenRoundClick(this, ${matchIndex}, 'B', '${finish.id}');">
                    <span class="btn-player">${beyBName}</span>
                    <span class="btn-finish">${finish.emoji} ${finish.label}</span>
                </button>
            `).join('')}
        </div>
    `;
}

/**
 * Handle fullscreen round button click with visual feedback
 */
function handleFullscreenRoundClick(button, matchIndex, winner, finishType) {
    // Add success class for visual feedback
    button.classList.add('btn-success');
    
    // Add the round
    addRound(matchIndex, winner, finishType);
    
    // Remove success class after animation completes
    setTimeout(() => {
        button.classList.remove('btn-success');
    }, 400);
    
    // Update fullscreen view after a brief delay to show the feedback
    setTimeout(() => {
        updateFullscreenRounds(matchIndex);
    }, 100);
}

/**
 * Render rounds list for fullscreen mode
 */
function renderFullscreenRoundsList(match, matchIndex) {
    if (!match.rounds || match.rounds.length === 0) {
        return '<div style="padding: 1rem; text-align: center; color: var(--text-light);">No rounds recorded</div>';
    }
    
    return match.rounds.map((round, roundIndex) => {
        const winnerLabel = round.winner === 'A' ? (match.beyA || 'A') : (match.beyB || 'B');
        const finishType = FINISH_TYPES[round.finishType?.toUpperCase()] || { label: round.finishType || 'Win' };
        
        return `
            <div class="fullscreen-round-item">
                <span class="round-number">R${roundIndex + 1}</span>
                <span class="round-winner">${escapeHtml(winnerLabel)}</span>
                <span class="round-finish">${escapeHtml(finishType.label)}</span>
                <button class="round-remove-btn" onclick="removeRound(${matchIndex}, ${roundIndex}); updateFullscreenRounds(${matchIndex});">×</button>
            </div>
        `;
    }).join('');
}

/**
 * Update the rounds section in fullscreen mode after changes
 */
function updateFullscreenRounds(matchIndex) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    // Re-render the entire fullscreen view to reflect changes
    enterFullscreenMatch(matchIndex);
}

// ============================================
// BEY PICKER MODAL (for touch-friendly selection)
// ============================================

/**
 * Open the bey picker modal for selecting a bey
 * @param {number} matchIndex - Index of the match
 * @param {string} player - 'A' or 'B' to indicate which player's bey is being selected
 */
function openBeyPicker(matchIndex, player) {
    const match = state.matches[matchIndex];
    if (!match) return;
    
    const currentSelection = player === 'A' ? match.beyA : match.beyB;
    
    // Get bey data with images
    const sortedBeys = [...state.beyblades].sort((a, b) => a.name.localeCompare(b.name));
    
    // Create modal HTML
    const modalHTML = `
        <div class="bey-picker-backdrop" onclick="closeBeyPicker()"></div>
        <div class="bey-picker-modal">
            <div class="bey-picker-header">
                <h3 class="bey-picker-title">Select Bey for Player ${player}</h3>
                <button class="bey-picker-close" onclick="closeBeyPicker()">✕</button>
            </div>
            <div class="bey-picker-search">
                <input 
                    type="text" 
                    id="beyPickerSearch" 
                    class="bey-picker-search-input" 
                    placeholder="Search beys..." 
                    oninput="filterBeyPicker(this.value)"
                />
            </div>
            <div class="bey-picker-grid" id="beyPickerGrid">
                ${sortedBeys.map(bey => {
                    const imagePath = `./data/beys/${bey.name}.png`;
                    const isSelected = currentSelection === bey.name;
                    const escapedName = escapeHtml(bey.name);
                    return `
                        <div class="bey-picker-item ${isSelected ? 'selected' : ''}" 
                             onclick="selectBeyFromPicker(${matchIndex}, '${player}', '${bey.name}')"
                             data-bey-name="${escapedName.toLowerCase()}">
                            <div class="bey-picker-item-image">
                                <img src="${imagePath}" alt="${escapedName}" onerror="this.src='${BEY_IMAGE_FALLBACK}'">
                            </div>
                            <div class="bey-picker-item-name">${escapedName}</div>
                            ${isSelected ? '<div class="bey-picker-item-check">✓</div>' : ''}
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="bey-picker-footer">
                <button class="bey-picker-cancel" onclick="closeBeyPicker()">Cancel</button>
            </div>
        </div>
    `;
    
    // Create or get the picker container
    let pickerContainer = document.getElementById('beyPickerContainer');
    if (!pickerContainer) {
        pickerContainer = document.createElement('div');
        pickerContainer.id = 'beyPickerContainer';
        pickerContainer.className = 'bey-picker-container';
        document.body.appendChild(pickerContainer);
    }
    
    pickerContainer.innerHTML = modalHTML;
    pickerContainer.classList.add('active');
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    
    // Do not auto-focus the search input — on mobile this would immediately
    // pop up the on-screen keyboard before the user requests it.
}

/**
 * Close the bey picker modal
 */
function closeBeyPicker() {
    const pickerContainer = document.getElementById('beyPickerContainer');
    if (pickerContainer) {
        pickerContainer.classList.remove('active');
        // Restore body scroll if fullscreen is still active, otherwise let exitFullscreenMatch handle it
        const overlay = document.getElementById('fullscreenMatchOverlay');
        if (overlay && overlay.classList.contains('active')) {
            document.body.style.overflow = 'hidden'; // Keep scroll disabled while fullscreen is active
        } else {
            document.body.style.overflow = '';
        }
    }
}

/**
 * Select a bey from the picker and update the match
 * @param {number} matchIndex - Index of the match
 * @param {string} player - 'A' or 'B'
 * @param {string} beyName - Name of the selected bey
 */
function selectBeyFromPicker(matchIndex, player, beyName) {
    updateBey(matchIndex, player, beyName);
    closeBeyPicker();
    // Refresh the fullscreen view to show the updated selection
    enterFullscreenMatch(matchIndex);
}

/**
 * Filter bey picker grid based on search input
 * @param {string} searchTerm - The search term entered by user
 */
function filterBeyPicker(searchTerm) {
    const grid = document.getElementById('beyPickerGrid');
    if (!grid) return;
    
    const items = grid.querySelectorAll('.bey-picker-item');
    const lowerSearch = searchTerm.toLowerCase().trim();
    
    items.forEach(item => {
        const beyName = item.getAttribute('data-bey-name');
        if (beyName && beyName.includes(lowerSearch)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}
