// ============================================
// QUICK ENTRY SYSTEM - Fast Round Entry for Tournaments
// ============================================

// ============================================
// STORAGE KEYS
// ============================================
const STORAGE_KEYS = {
    MATCHES: 'quickEntry_matches',
    TOURNAMENT: 'quickEntry_tournament',
    PARTICIPANTS: 'quickEntry_participants',
    SETTINGS: 'quickEntry_settings'
};

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
    focusedMatchIndex: -1
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    await loadBeybladeData();
    loadFromStorage();
    initializeUI();
    setupEventListeners();
    renderMatches();
    updateStatusBar();
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
    } catch (error) {
        console.error('Error loading beyblade data:', error);
        state.beyblades = [];
    }
}

// Load state from localStorage
function loadFromStorage() {
    try {
        const matchesData = localStorage.getItem(STORAGE_KEYS.MATCHES);
        const tournamentData = localStorage.getItem(STORAGE_KEYS.TOURNAMENT);
        const participantsData = localStorage.getItem(STORAGE_KEYS.PARTICIPANTS);
        
        if (matchesData) {
            state.matches = JSON.parse(matchesData);
        }
        if (tournamentData) {
            state.tournament = JSON.parse(tournamentData);
        }
        if (participantsData) {
            state.participants = JSON.parse(participantsData);
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
    
    if (tournamentNameInput) tournamentNameInput.value = state.tournament.name || '';
    if (roundNumberInput) roundNumberInput.value = state.tournament.round || 1;
    if (formatSelect) formatSelect.value = state.tournament.format || 'swiss';
    if (matchCountInput) matchCountInput.value = state.matches.length || 8;
    
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
    document.getElementById('importFile')?.addEventListener('change', handleImport);
    
    // Swiss pairing
    document.getElementById('participantSearch')?.addEventListener('input', handleParticipantSearch);
    document.getElementById('participantSearch')?.addEventListener('focus', handleParticipantSearch);
    document.getElementById('generatePairingsBtn')?.addEventListener('click', generateSwissPairings);
    document.getElementById('randomPairingsBtn')?.addEventListener('click', generateRandomPairings);
    
    // Shortcuts legend toggle
    document.getElementById('shortcutsHeader')?.addEventListener('click', toggleShortcutsLegend);
    
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
function createEmptyMatch(index) {
    return {
        id: Date.now() + index,
        matchNumber: index + 1,
        beyA: '',
        beyB: '',
        scoreA: 0,
        scoreB: 0,
        winner: null,
        timestamp: null
    };
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
        match.scoreA = 0;
        match.scoreB = 0;
        match.winner = null;
        match.timestamp = null;
    });
    
    saveToStorage();
    renderMatches();
    updateStatusBar();
    showToast('Round reset', 'warning');
}

function clearAll() {
    if (!confirm('Clear all match data? This cannot be undone.')) {
        return;
    }
    
    state.matches = [];
    state.participants = [];
    
    saveToStorage();
    renderMatches();
    renderSelectedParticipants();
    updateStatusBar();
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
}

// ============================================
// RENDERING
// ============================================
function renderMatches() {
    renderMatchTable();
    renderMatchCards();
}

function renderMatchTable() {
    const tbody = document.getElementById('matchEntryBody');
    if (!tbody) return;
    
    tbody.innerHTML = state.matches.map((match, index) => {
        const isComplete = match.winner && match.beyA && match.beyB;
        const isIncomplete = !isComplete && (match.scoreA > 0 || match.scoreB > 0 || match.beyA || match.beyB);
        const rowClass = isComplete ? 'complete' : (isIncomplete ? 'incomplete' : '');
        
        return `
            <tr class="match-row ${rowClass}" data-index="${index}">
                <td class="col-match">
                    <span class="match-number">${match.matchNumber}</span>
                </td>
                <td class="col-bey-a">
                    ${renderBeySelect(match.beyA, index, 'A')}
                </td>
                <td class="col-score-a">
                    <div class="score-control">
                        <button class="score-btn score-btn-minus" onclick="updateScore(${index}, 'A', -1)" aria-label="Decrease score A">−</button>
                        <span class="score-display" id="scoreA_${index}">${match.scoreA}</span>
                        <button class="score-btn score-btn-plus" onclick="updateScore(${index}, 'A', 1)" aria-label="Increase score A">+</button>
                    </div>
                </td>
                <td class="col-vs">
                    <span class="vs-text">VS</span>
                </td>
                <td class="col-score-b">
                    <div class="score-control">
                        <button class="score-btn score-btn-minus" onclick="updateScore(${index}, 'B', -1)" aria-label="Decrease score B">−</button>
                        <span class="score-display" id="scoreB_${index}">${match.scoreB}</span>
                        <button class="score-btn score-btn-plus" onclick="updateScore(${index}, 'B', 1)" aria-label="Increase score B">+</button>
                    </div>
                </td>
                <td class="col-bey-b">
                    ${renderBeySelect(match.beyB, index, 'B')}
                </td>
                <td class="col-winner">
                    ${renderWinnerIndicator(match)}
                </td>
                <td class="col-actions">
                    <div class="row-actions">
                        <button class="row-action-btn delete-btn" onclick="deleteMatch(${index})" aria-label="Delete match" title="Delete">🗑️</button>
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
        
        return `
            <div class="match-card ${cardClass}" data-index="${index}">
                <div class="match-card-header">
                    <span class="match-card-number">Match ${match.matchNumber}</span>
                    <span class="match-card-winner">${renderWinnerIndicator(match)}</span>
                </div>
                <div class="match-card-content">
                    <div class="match-card-player player-a">
                        ${renderBeySelect(match.beyA, index, 'A')}
                        <div class="score-control">
                            <button class="score-btn score-btn-minus" onclick="updateScore(${index}, 'A', -1)">−</button>
                            <span class="score-display">${match.scoreA}</span>
                            <button class="score-btn score-btn-plus" onclick="updateScore(${index}, 'A', 1)">+</button>
                        </div>
                    </div>
                    <div class="match-card-vs">VS</div>
                    <div class="match-card-player player-b">
                        ${renderBeySelect(match.beyB, index, 'B')}
                        <div class="score-control">
                            <button class="score-btn score-btn-minus" onclick="updateScore(${index}, 'B', -1)">−</button>
                            <span class="score-display">${match.scoreB}</span>
                            <button class="score-btn score-btn-plus" onclick="updateScore(${index}, 'B', 1)">+</button>
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

function renderBeySelect(selectedBey, matchIndex, player) {
    const options = state.beyblades.map(bey => 
        `<option value="${bey.name}" ${bey.name === selectedBey ? 'selected' : ''}>${bey.name}</option>`
    ).join('');
    
    return `
        <select class="bey-select ${selectedBey ? 'has-value' : ''}" 
                onchange="updateBey(${matchIndex}, '${player}', this.value)"
                data-match="${matchIndex}" 
                data-player="${player}">
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
    
    return `<span class="winner-indicator ${winnerClass}" title="${winnerName}">${displayName}</span>`;
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
        dropdown.innerHTML = filtered.map(bey => `
            <div class="participant-option" onclick="addParticipant('${bey.name}')">
                <span>${bey.name}</span>
                <span class="elo-badge">${bey.elo} ELO</span>
            </div>
        `).join('');
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
    
    container.innerHTML = state.participants.map(name => `
        <div class="participant-chip">
            <span>${name}</span>
            <button class="remove-participant" onclick="removeParticipant('${name}')" aria-label="Remove ${name}">×</button>
        </div>
    `).join('');
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
            id: Date.now() + i,
            matchNumber: state.matches.length + 1,
            beyA: sortedParticipants[i],
            beyB: sortedParticipants[i + 1],
            scoreA: 0,
            scoreB: 0,
            winner: null,
            timestamp: null
        });
    }
    
    // Handle odd participant (bye)
    if (sortedParticipants.length % 2 === 1) {
        showToast(`${sortedParticipants[sortedParticipants.length - 1]} gets a bye`, 'warning');
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
    
    // Shuffle participants
    const shuffled = [...state.participants].sort(() => Math.random() - 0.5);
    
    // Create pairings
    state.matches = [];
    for (let i = 0; i < shuffled.length - 1; i += 2) {
        state.matches.push({
            id: Date.now() + i,
            matchNumber: state.matches.length + 1,
            beyA: shuffled[i],
            beyB: shuffled[i + 1],
            scoreA: 0,
            scoreB: 0,
            winner: null,
            timestamp: null
        });
    }
    
    if (shuffled.length % 2 === 1) {
        showToast(`${shuffled[shuffled.length - 1]} gets a bye`, 'warning');
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
        version: '1.0'
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const filename = `${state.tournament.name || 'tournament'}_round${state.tournament.round}_${new Date().toISOString().split('T')[0]}.json`;
    downloadFile(url, filename);
    
    showToast('Exported as JSON', 'success');
}

function exportCSV() {
    const headers = ['MatchID', 'Date', 'BeyA', 'BeyB', 'ScoreA', 'ScoreB'];
    const rows = state.matches.map((match, i) => {
        const date = match.timestamp ? new Date(match.timestamp).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
        return [
            `M${String(i + 1).padStart(4, '0')}`,
            date,
            match.beyA || '',
            match.beyB || '',
            match.scoreA,
            match.scoreB
        ];
    });
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const filename = `${state.tournament.name || 'tournament'}_round${state.tournament.round}_${new Date().toISOString().split('T')[0]}.csv`;
    downloadFile(url, filename);
    
    showToast('Exported as CSV', 'success');
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
        state.matches = data.matches.map((match, i) => ({
            id: match.id || Date.now() + i,
            matchNumber: match.matchNumber || i + 1,
            beyA: match.beyA || '',
            beyB: match.beyB || '',
            scoreA: match.scoreA || 0,
            scoreB: match.scoreB || 0,
            winner: match.winner || null,
            timestamp: match.timestamp || null
        }));
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
    
    state.matches = lines.slice(1).map((line, i) => {
        const values = line.split(',').map(v => v.trim());
        const scoreA = scoreAIndex !== -1 ? parseInt(values[scoreAIndex]) || 0 : 0;
        const scoreB = scoreBIndex !== -1 ? parseInt(values[scoreBIndex]) || 0 : 0;
        
        let winner = null;
        if (scoreA > scoreB && scoreA > 0) winner = 'A';
        else if (scoreB > scoreA && scoreB > 0) winner = 'B';
        else if (scoreA === scoreB && scoreA > 0) winner = 'draw';
        
        return {
            id: Date.now() + i,
            matchNumber: i + 1,
            beyA: values[beyAIndex] || '',
            beyB: values[beyBIndex] || '',
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
