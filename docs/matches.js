// matches.js - Extended Match History with filtering, sorting, and pagination
let allMatches = [];
let filteredMatches = [];
let beysData = [];
let roundsData = {}; // Mapping of match_id to rounds array
let currentSort = { column: 1, asc: false }; // Default: Date descending (Date is now column index 1)
let currentPage = 1;
let pageSize = 50;
let expandedMatches = new Set(); // Track which matches are expanded

// Column definitions for extended match history
const COLUMN_DEFINITIONS = [
    { key: 'matchId', label: 'Match ID', abbrev: 'ID', sortable: true },
    { key: 'date', label: 'Date', abbrev: 'Date', sortable: true },
    { key: 'beyA', label: 'Bey A', abbrev: 'Bey A', sortable: true },
    { key: 'preEloA', label: 'Pre ELO A', abbrev: 'Pre A', sortable: true },
    { key: 'scoreA', label: 'Score A', abbrev: 'Sc A', sortable: true },
    { key: 'scoreB', label: 'Score B', abbrev: 'Sc B', sortable: true },
    { key: 'preEloB', label: 'Pre ELO B', abbrev: 'Pre B', sortable: true },
    { key: 'beyB', label: 'Bey B', abbrev: 'Bey B', sortable: true },
    { key: 'winner', label: 'Winner', abbrev: 'Winner', sortable: true },
    { key: 'eloChangeA', label: 'Δ ELO A', abbrev: 'Δ A', sortable: true },
    { key: 'eloChangeB', label: 'Δ ELO B', abbrev: 'Δ B', sortable: true },
    { key: 'eloDiff', label: 'ELO Diff', abbrev: 'Diff', sortable: true }
];

// Column descriptions for legend
const COLUMN_DESCRIPTIONS = {
    'ID': { short: 'Match ID', long: 'Unique identifier for the match, used for referencing and debugging' },
    'Date': { short: 'Match Date', long: 'The date when the match was played' },
    'Bey A': { short: 'Beyblade A', long: 'Name of the first Beyblade in the match' },
    'Pre A': { short: 'Pre-Match ELO A', long: 'ELO rating of Bey A before the match' },
    'Sc A': { short: 'Score A', long: 'Points scored by Bey A in the match' },
    'Sc B': { short: 'Score B', long: 'Points scored by Bey B in the match' },
    'Pre B': { short: 'Pre-Match ELO B', long: 'ELO rating of Bey B before the match' },
    'Bey B': { short: 'Beyblade B', long: 'Name of the second Beyblade in the match' },
    'Winner': { short: 'Match Winner', long: 'The Beyblade that won the match' },
    'Δ A': { short: 'ELO Change A', long: 'ELO rating change for Bey A (positive = gained, negative = lost)' },
    'Δ B': { short: 'ELO Change B', long: 'ELO rating change for Bey B (positive = gained, negative = lost)' },
    'Diff': { short: 'ELO Difference', long: 'Absolute ELO difference between the two Beys before the match' }
};

// Load beys data for part filtering
async function loadBeysDataForFilters() {
    try {
        const response = await fetch('data/beys_data.json');
        beysData = await response.json();
    } catch (error) {
        console.error('Error loading beys data:', error);
        beysData = [];
    }
}

// Get bey info by name (blade name)
function getBeyInfo(bladeName) {
    return beysData.find(b => b.blade === bladeName) || null;
}

// Finish type styling configuration
const FINISH_TYPE_STYLES = {
    spin: { color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.15)', label: 'Spin', icon: '🔄', points: 1 },
    burst: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.15)', label: 'Burst', icon: '💥', points: 2 },
    pocket: { color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.15)', label: 'Pocket', icon: '🎯', points: 2 },
    extreme: { color: '#8b5cf6', bgColor: 'rgba(139, 92, 246, 0.15)', label: 'Extreme', icon: '⚡', points: 3 }
};

// Load rounds data from matches_with_rounds.json
async function loadRoundsData() {
    try {
        const response = await fetch('data/matches_with_rounds.json');
        const data = await response.json();
        
        // Create a mapping of match_id to rounds
        if (data.matches) {
            data.matches.forEach(match => {
                if (match.rounds && match.rounds.length > 0) {
                    roundsData[match.match_id] = match.rounds;
                }
            });
        }
        console.log(`Loaded rounds data for ${Object.keys(roundsData).length} matches`);
    } catch (error) {
        console.error('Error loading rounds data:', error);
        roundsData = {};
    }
}

// Load extended match history from elo_history.csv
async function loadMatches() {
    try {
        const response = await fetch('data/elo_history.csv');
        const text = await response.text();
        
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',');
        console.log(headers);
        
        allMatches = lines.slice(1).map((line, index) => {
            const values = line.split(',');
            const matchId = values[0]; // MatchID column
            const scoreA = parseInt(values[4]);
            const scoreB = parseInt(values[5]);
            const preA = parseFloat(values[6]);
            const preB = parseFloat(values[7]);
            const postA = parseFloat(values[8]);
            const postB = parseFloat(values[9]);
            
            return {
                id: index,
                matchId: matchId,
                date: values[1],
                dateFormatted: formatDate(values[1]),
                beyA: values[2],
                beyB: values[3],
                scoreA: scoreA,
                scoreB: scoreB,
                preEloA: Math.round(preA),
                preEloB: Math.round(preB),
                postEloA: Math.round(postA),
                postEloB: Math.round(postB),
                eloChangeA: Math.round(postA - preA),
                eloChangeB: Math.round(postB - preB),
                eloDiff: Math.round(Math.abs(preA - preB)),
                winner: scoreA > scoreB ? values[2] : values[3],
                rounds: roundsData[matchId] || [] // Attach rounds data
            };
        });
        
        // Sort by date descending by default (newest first)
        allMatches.sort((a, b) => new Date(b.date) - new Date(a.date));
        filteredMatches = [...allMatches];
        
        populateFilters();
        loadFiltersFromURL();
        updateLegend();
        applyFilters();
    } catch (error) {
        console.error('Error loading matches:', error);
        document.getElementById('matchesBody').innerHTML = 
            '<tr><td colspan="12">Error loading matches data</td></tr>';
    }
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

// Populate filter dropdowns
function populateFilters() {
    // Date filter
    const dates = [...new Set(allMatches.map(m => m.date))].sort().reverse();
    const dateSelect = document.getElementById('dateFilter');
    dates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = formatDate(date);
        dateSelect.appendChild(option);
    });
    
    // Bey filter
    const beys = [...new Set([...allMatches.map(m => m.beyA), ...allMatches.map(m => m.beyB)])].sort();
    const beySelect = document.getElementById('beyFilter');
    beys.forEach(bey => {
        const option = document.createElement('option');
        option.value = bey;
        option.textContent = bey;
        beySelect.appendChild(option);
    });
    
    // Part filters (Blade, Ratchet, Bit)
    const blades = [...new Set(beysData.map(b => b.blade).filter(Boolean))].sort();
    const ratchets = [...new Set(beysData.map(b => b.ratchet).filter(Boolean))].sort();
    const bits = [...new Set(beysData.map(b => b.bit).filter(Boolean))].sort();
    
    const bladeSelect = document.getElementById('bladeFilter');
    blades.forEach(blade => {
        const option = document.createElement('option');
        option.value = blade;
        option.textContent = blade;
        bladeSelect.appendChild(option);
    });
    
    const ratchetSelect = document.getElementById('ratchetFilter');
    ratchets.forEach(ratchet => {
        const option = document.createElement('option');
        option.value = ratchet;
        option.textContent = ratchet;
        ratchetSelect.appendChild(option);
    });
    
    const bitSelect = document.getElementById('bitFilter');
    bits.forEach(bit => {
        const option = document.createElement('option');
        option.value = bit;
        option.textContent = bit;
        bitSelect.appendChild(option);
    });
}

// Get current filter values
function getFilterValues() {
    return {
        search: document.getElementById('searchInput').value.toLowerCase(),
        date: document.getElementById('dateFilter').value,
        bey: document.getElementById('beyFilter').value,
        blade: document.getElementById('bladeFilter').value,
        ratchet: document.getElementById('ratchetFilter').value,
        bit: document.getElementById('bitFilter').value,
        minEloDiff: parseInt(document.getElementById('minEloDiff').value) || 0,
        maxEloDiff: parseInt(document.getElementById('maxEloDiff').value) || Infinity,
        eloChange: document.getElementById('eloChangeFilter').value
    };
}

// Apply all filters
function applyFilters() {
    const filters = getFilterValues();
    
    filteredMatches = allMatches.filter(match => {
        // Search filter
        if (filters.search) {
            const searchMatch = 
                match.beyA.toLowerCase().includes(filters.search) ||
                match.beyB.toLowerCase().includes(filters.search) ||
                match.dateFormatted.includes(filters.search) ||
                match.date.includes(filters.search);
            if (!searchMatch) return false;
        }
        
        // Date filter
        if (filters.date !== 'all' && match.date !== filters.date) {
            return false;
        }
        
        // Bey filter
        if (filters.bey !== 'all' && match.beyA !== filters.bey && match.beyB !== filters.bey) {
            return false;
        }
        
        // Part filters (Blade, Ratchet, Bit)
        if (filters.blade !== 'all' || filters.ratchet !== 'all' || filters.bit !== 'all') {
            const beyAInfo = getBeyInfo(match.beyA);
            const beyBInfo = getBeyInfo(match.beyB);
            
            let matchesPart = false;
            
            if (beyAInfo) {
                let aMatches = true;
                if (filters.blade !== 'all' && beyAInfo.blade !== filters.blade) aMatches = false;
                if (filters.ratchet !== 'all' && beyAInfo.ratchet !== filters.ratchet) aMatches = false;
                if (filters.bit !== 'all' && beyAInfo.bit !== filters.bit) aMatches = false;
                if (aMatches) matchesPart = true;
            }
            
            if (beyBInfo && !matchesPart) {
                let bMatches = true;
                if (filters.blade !== 'all' && beyBInfo.blade !== filters.blade) bMatches = false;
                if (filters.ratchet !== 'all' && beyBInfo.ratchet !== filters.ratchet) bMatches = false;
                if (filters.bit !== 'all' && beyBInfo.bit !== filters.bit) bMatches = false;
                if (bMatches) matchesPart = true;
            }
            
            if (!matchesPart) return false;
        }
        
        // ELO difference filter
        if (match.eloDiff < filters.minEloDiff || match.eloDiff > filters.maxEloDiff) {
            return false;
        }
        
        // ELO change filter
        if (filters.eloChange !== 'all') {
            if (filters.bey !== 'all') {
                // Filter based on specific bey's ELO change
                const eloChange = match.beyA === filters.bey ? match.eloChangeA : match.eloChangeB;
                if (filters.eloChange === 'gain' && eloChange <= 0) return false;
                if (filters.eloChange === 'loss' && eloChange >= 0) return false;
            } else {
                // If no specific bey selected, show matches where either had gain/loss
                if (filters.eloChange === 'gain') {
                    if (match.eloChangeA <= 0 && match.eloChangeB <= 0) return false;
                }
                if (filters.eloChange === 'loss') {
                    if (match.eloChangeA >= 0 && match.eloChangeB >= 0) return false;
                }
            }
        }
        
        return true;
    });
    
    // Apply current sort
    sortMatches();
    
    // Reset to page 1
    currentPage = 1;
    
    // Save filters to URL
    saveFiltersToURL();
    
    // Update active filters count
    updateActiveFiltersCount();
    
    // Update display
    updateMatchCount();
    updatePagination();
    displayMatches();
}

// Sort matches by column
function sortMatches() {
    const colDef = COLUMN_DEFINITIONS[currentSort.column];
    const key = colDef.key;
    
    filteredMatches.sort((a, b) => {
        let valA = a[key];
        let valB = b[key];
        
        // Handle date sorting - convert to Date objects for comparison
        if (key === 'date') {
            valA = new Date(valA);
            valB = new Date(valB);
            return currentSort.asc ? valA - valB : valB - valA;
        }
        
        // Handle numeric sorting
        if (typeof valA === 'number' && typeof valB === 'number') {
            return currentSort.asc ? valA - valB : valB - valA;
        }
        
        // Handle string sorting
        if (typeof valA === 'string' && typeof valB === 'string') {
            return currentSort.asc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        
        return 0;
    });
}

// Sort by column click
function sortByColumn(colIndex) {
    if (currentSort.column === colIndex) {
        currentSort.asc = !currentSort.asc;
    } else {
        currentSort.column = colIndex;
        currentSort.asc = true;
    }
    
    sortMatches();
    currentPage = 1;
    updatePagination();
    displayMatches();
    updateCurrentSortLabel();
}

// Update match count display
function updateMatchCount() {
    const countEl = document.getElementById('matchCount');
    if (countEl) {
        countEl.textContent = `Showing ${filteredMatches.length} of ${allMatches.length} matches`;
    }
}

// Update pagination controls
function updatePagination() {
    const pageSizeVal = document.getElementById('pageSize').value;
    pageSize = pageSizeVal === 'all' ? filteredMatches.length : parseInt(pageSizeVal);
    
    const totalPages = Math.ceil(filteredMatches.length / pageSize) || 1;
    
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;
}

// Get current page of matches
function getCurrentPageMatches() {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredMatches.slice(start, end);
}

// Display matches in table and cards
function displayMatches() {
    const isMobile = window.innerWidth < 900;
    const tbody = document.getElementById('matchesBody');
    const headRow = document.getElementById('matchesHeadRow');
    const cardsContainer = document.getElementById('matchesCards');
    const tableWrapper = document.querySelector('.table-wrapper');
    const mobileSortControls = document.getElementById('mobileSortControls');
    const pagination = document.getElementById('pagination');
    
    // Clear existing content
    tbody.innerHTML = '';
    headRow.innerHTML = '';
    cardsContainer.innerHTML = '';
    
    const matchesToShow = getCurrentPageMatches();
    
    if (filteredMatches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12">No matches found</td></tr>';
        cardsContainer.innerHTML = '<div class="no-results">No matches found</div>';
        return;
    }
    
    // Show/hide based on screen size
    if (isMobile) {
        tableWrapper.style.display = 'none';
        cardsContainer.style.display = 'grid';
        if (mobileSortControls) mobileSortControls.style.display = 'block';
        pagination.style.display = 'none';
    } else {
        tableWrapper.style.display = 'block';
        cardsContainer.style.display = 'none';
        if (mobileSortControls) mobileSortControls.style.display = 'none';
        pagination.style.display = 'flex';
    }
    
    // Build table headers
    COLUMN_DEFINITIONS.forEach((col, index) => {
        const th = document.createElement('th');
        th.textContent = col.abbrev;
        if (col.sortable) {
            th.classList.add('sortable');
            th.onclick = () => sortByColumn(index);
            if (currentSort.column === index) {
                th.classList.add(currentSort.asc ? 'sorted-asc' : 'sorted-desc');
            }
        }
        headRow.appendChild(th);
    });
    
    // Add Rounds column header
    const thRounds = document.createElement('th');
    thRounds.textContent = 'Rounds';
    thRounds.classList.add('rounds-header');
    headRow.appendChild(thRounds);
    
    // Display table rows (desktop)
    matchesToShow.forEach(match => {
        const row = document.createElement('tr');
        row.dataset.matchId = match.matchId;
        
        // Match ID
        const tdMatchId = document.createElement('td');
        tdMatchId.className = 'match-id-cell';
        const matchIdSpan = document.createElement('span');
        matchIdSpan.className = 'match-id';
        matchIdSpan.textContent = match.matchId;
        matchIdSpan.title = 'Click to copy';
        matchIdSpan.onclick = (e) => {
            e.stopPropagation();
            copyMatchId(match.matchId);
        };
        tdMatchId.appendChild(matchIdSpan);
        row.appendChild(tdMatchId);
        
        // Date
        const tdDate = document.createElement('td');
        tdDate.textContent = match.dateFormatted;
        row.appendChild(tdDate);
        
        // Bey A
        const tdBeyA = document.createElement('td');
        tdBeyA.className = match.winner === match.beyA ? 'winner' : '';
        const linkA = document.createElement('a');
        linkA.href = `bey.html?name=${encodeURIComponent(match.beyA)}`;
        linkA.className = 'bey-link';
        linkA.textContent = match.beyA;
        tdBeyA.appendChild(linkA);
        row.appendChild(tdBeyA);
        
        // Pre ELO A
        const tdPreA = document.createElement('td');
        tdPreA.textContent = match.preEloA;
        row.appendChild(tdPreA);
        
        // Score A
        const tdScoreA = document.createElement('td');
        tdScoreA.textContent = match.scoreA;
        tdScoreA.className = match.winner === match.beyA ? 'score-winner' : '';
        row.appendChild(tdScoreA);
        
        // Score B
        const tdScoreB = document.createElement('td');
        tdScoreB.textContent = match.scoreB;
        tdScoreB.className = match.winner === match.beyB ? 'score-winner' : '';
        row.appendChild(tdScoreB);
        
        // Pre ELO B
        const tdPreB = document.createElement('td');
        tdPreB.textContent = match.preEloB;
        row.appendChild(tdPreB);
        
        // Bey B
        const tdBeyB = document.createElement('td');
        tdBeyB.className = match.winner === match.beyB ? 'winner' : '';
        const linkB = document.createElement('a');
        linkB.href = `bey.html?name=${encodeURIComponent(match.beyB)}`;
        linkB.className = 'bey-link';
        linkB.textContent = match.beyB;
        tdBeyB.appendChild(linkB);
        row.appendChild(tdBeyB);
        
        // Winner
        const tdWinner = document.createElement('td');
        tdWinner.className = 'match-winner';
        const linkWinner = document.createElement('a');
        linkWinner.href = `bey.html?name=${encodeURIComponent(match.winner)}`;
        linkWinner.className = 'bey-link';
        linkWinner.textContent = match.winner;
        tdWinner.appendChild(linkWinner);
        row.appendChild(tdWinner);
        
        // ELO Change A
        const tdChangeA = document.createElement('td');
        tdChangeA.textContent = (match.eloChangeA >= 0 ? '+' : '') + match.eloChangeA;
        tdChangeA.className = match.eloChangeA >= 0 ? 'delta-elo-up' : 'delta-elo-down';
        row.appendChild(tdChangeA);
        
        // ELO Change B
        const tdChangeB = document.createElement('td');
        tdChangeB.textContent = (match.eloChangeB >= 0 ? '+' : '') + match.eloChangeB;
        tdChangeB.className = match.eloChangeB >= 0 ? 'delta-elo-up' : 'delta-elo-down';
        row.appendChild(tdChangeB);
        
        // ELO Difference
        const tdDiff = document.createElement('td');
        tdDiff.textContent = match.eloDiff;
        row.appendChild(tdDiff);
        
        // Rounds expand button
        const tdRounds = document.createElement('td');
        tdRounds.className = 'rounds-cell';
        if (match.rounds && match.rounds.length > 0) {
            const expandBtn = document.createElement('button');
            expandBtn.className = 'rounds-expand-btn';
            expandBtn.dataset.matchId = match.matchId;
            expandBtn.title = `Show ${match.rounds.length} rounds`;
            const isExpanded = expandedMatches.has(match.matchId);
            expandBtn.innerHTML = isExpanded ? '▲' : '▼';
            expandBtn.setAttribute('aria-expanded', isExpanded);
            expandBtn.onclick = (e) => {
                e.stopPropagation();
                toggleRoundsRow(match.matchId);
            };
            tdRounds.appendChild(expandBtn);
        } else {
            tdRounds.textContent = '—';
            tdRounds.classList.add('no-rounds');
        }
        row.appendChild(tdRounds);
        
        tbody.appendChild(row);
        
        // Add rounds detail row if expanded
        if (match.rounds && match.rounds.length > 0 && expandedMatches.has(match.matchId)) {
            const roundsRow = createRoundsDetailRow(match);
            tbody.appendChild(roundsRow);
        }
    });
    
    // Display cards (mobile) - show all filtered matches for scrolling
    const mobileMatches = isMobile ? filteredMatches : matchesToShow;
    mobileMatches.forEach(match => {
        const card = document.createElement('div');
        card.className = 'card matches-card';
        card.dataset.matchId = match.matchId;
        
        const hasRounds = match.rounds && match.rounds.length > 0;
        const roundsHtml = hasRounds ? createMobileRoundsHtml(match) : '';
        const isExpanded = expandedMatches.has(match.matchId);
        
        card.innerHTML = `
            <div class="card-header">
                <span class="card-match-id match-id" title="Click to copy" onclick="copyMatchId('${match.matchId}')">${match.matchId}</span>
                <span class="card-date">${match.dateFormatted}</span>
                <span class="match-elo-diff" title="ELO Difference">Δ${match.eloDiff} ELO</span>
            </div>
            <div class="card-match">
                <div class="card-bey ${match.winner === match.beyA ? 'winner' : ''}">
                    <div class="bey-name"><a href="bey.html?name=${encodeURIComponent(match.beyA)}" class="bey-link">${match.beyA}</a></div>
                    <div class="bey-elo"><span class="stat-label">Pre-ELO:</span> ${match.preEloA}</div>
                    <div class="bey-score ${match.winner === match.beyA ? 'score-winner' : ''}"><span class="stat-label">Score:</span> ${match.scoreA}</div>
                    <div class="bey-elo-change ${match.eloChangeA >= 0 ? 'delta-elo-up' : 'delta-elo-down'}"><span class="stat-label">ELO Δ:</span> ${match.eloChangeA >= 0 ? '+' : ''}${match.eloChangeA}</div>
                </div>
                <div class="card-vs">VS</div>
                <div class="card-bey ${match.winner === match.beyB ? 'winner' : ''}">
                    <div class="bey-name"><a href="bey.html?name=${encodeURIComponent(match.beyB)}" class="bey-link">${match.beyB}</a></div>
                    <div class="bey-elo"><span class="stat-label">Pre-ELO:</span> ${match.preEloB}</div>
                    <div class="bey-score ${match.winner === match.beyB ? 'score-winner' : ''}"><span class="stat-label">Score:</span> ${match.scoreB}</div>
                    <div class="bey-elo-change ${match.eloChangeB >= 0 ? 'delta-elo-up' : 'delta-elo-down'}"><span class="stat-label">ELO Δ:</span> ${match.eloChangeB >= 0 ? '+' : ''}${match.eloChangeB}</div>
                </div>
            </div>
            <div class="card-footer">
                Winner: <strong><a href="bey.html?name=${encodeURIComponent(match.winner)}" class="bey-link">${match.winner}</a></strong>
            </div>
            ${hasRounds ? `
            <div class="card-rounds-section">
                <button class="card-rounds-toggle ${isExpanded ? 'expanded' : ''}" onclick="toggleMobileRounds('${match.matchId}')">
                    <span class="toggle-icon">${isExpanded ? '▲' : '▼'}</span>
                    Show Rounds (${match.rounds.length})
                </button>
                <div class="card-rounds-content ${isExpanded ? 'expanded' : ''}" id="mobile-rounds-${match.matchId}">
                    ${roundsHtml}
                </div>
            </div>
            ` : ''}
        `;
        
        cardsContainer.appendChild(card);
    });
}

// Save filters to URL
function saveFiltersToURL() {
    const params = new URLSearchParams();
    const filters = getFilterValues();
    
    if (filters.search) params.set('search', filters.search);
    if (filters.date !== 'all') params.set('date', filters.date);
    if (filters.bey !== 'all') params.set('bey', filters.bey);
    if (filters.blade !== 'all') params.set('blade', filters.blade);
    if (filters.ratchet !== 'all') params.set('ratchet', filters.ratchet);
    if (filters.bit !== 'all') params.set('bit', filters.bit);
    if (filters.minEloDiff > 0) params.set('minEloDiff', filters.minEloDiff);
    if (filters.maxEloDiff < Infinity && document.getElementById('maxEloDiff').value) {
        params.set('maxEloDiff', filters.maxEloDiff);
    }
    if (filters.eloChange !== 'all') params.set('eloChange', filters.eloChange);
    
    const newURL = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, '', newURL);
}

// Load filters from URL
function loadFiltersFromURL() {
    const params = new URLSearchParams(window.location.search);
    
    if (params.has('search')) {
        document.getElementById('searchInput').value = params.get('search');
    }
    if (params.has('date')) {
        document.getElementById('dateFilter').value = params.get('date');
    }
    if (params.has('bey')) {
        document.getElementById('beyFilter').value = params.get('bey');
    }
    if (params.has('blade')) {
        document.getElementById('bladeFilter').value = params.get('blade');
    }
    if (params.has('ratchet')) {
        document.getElementById('ratchetFilter').value = params.get('ratchet');
    }
    if (params.has('bit')) {
        document.getElementById('bitFilter').value = params.get('bit');
    }
    if (params.has('minEloDiff')) {
        document.getElementById('minEloDiff').value = params.get('minEloDiff');
    }
    if (params.has('maxEloDiff')) {
        document.getElementById('maxEloDiff').value = params.get('maxEloDiff');
    }
    if (params.has('eloChange')) {
        document.getElementById('eloChangeFilter').value = params.get('eloChange');
    }
}

// Clear all filters
function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('dateFilter').value = 'all';
    document.getElementById('beyFilter').value = 'all';
    document.getElementById('bladeFilter').value = 'all';
    document.getElementById('ratchetFilter').value = 'all';
    document.getElementById('bitFilter').value = 'all';
    document.getElementById('minEloDiff').value = '';
    document.getElementById('maxEloDiff').value = '';
    document.getElementById('eloChangeFilter').value = 'all';
    
    applyFilters();
}

// Update legend
function updateLegend() {
    const legendContent = document.getElementById('legendContent');
    if (!legendContent) return;
    
    const legendEntries = COLUMN_DEFINITIONS.map(col => {
        const desc = COLUMN_DESCRIPTIONS[col.abbrev] || { short: col.label, long: '' };
        return `
            <div class="legend-item">
                <div class="legend-abbr">${col.abbrev}</div>
                <div class="legend-desc">
                    <div class="legend-short">${desc.short}</div>
                    <div class="legend-long">${desc.long}</div>
                </div>
            </div>
        `;
    }).join('');
    
    legendContent.innerHTML = legendEntries;
}

// Setup legend toggle
function setupLegend() {
    const legendToggle = document.getElementById('legendToggle');
    const legendContent = document.getElementById('legendContent');
    const legendHeader = document.querySelector('.legend-header');
    
    if (legendToggle && legendContent && legendHeader) {
        legendContent.classList.add('collapsed');
        
        legendHeader.addEventListener('click', () => {
            const isExpanded = legendContent.classList.contains('expanded');
            
            if (isExpanded) {
                legendContent.classList.remove('expanded');
                legendContent.classList.add('collapsed');
                legendToggle.textContent = '▼';
            } else {
                legendContent.classList.remove('collapsed');
                legendContent.classList.add('expanded');
                legendToggle.textContent = '▲';
            }
        });
    }
}

// Setup collapsible filters panel
function setupFiltersPanel() {
    const filtersHeader = document.getElementById('filtersHeader');
    const filtersContent = document.getElementById('filtersContent');
    const filtersToggle = document.getElementById('filtersToggle');
    
    if (filtersHeader && filtersContent && filtersToggle) {
        // Start collapsed
        filtersContent.classList.add('collapsed');
        
        filtersHeader.addEventListener('click', () => {
            const isExpanded = filtersContent.classList.contains('expanded');
            
            if (isExpanded) {
                filtersContent.classList.remove('expanded');
                filtersContent.classList.add('collapsed');
                filtersToggle.textContent = '▼';
            } else {
                filtersContent.classList.remove('collapsed');
                filtersContent.classList.add('expanded');
                filtersToggle.textContent = '▲';
            }
        });
    }
}

// Update active filters count badge
function updateActiveFiltersCount() {
    const filters = getFilterValues();
    let activeCount = 0;
    
    if (filters.date !== 'all') activeCount++;
    if (filters.bey !== 'all') activeCount++;
    if (filters.blade !== 'all') activeCount++;
    if (filters.ratchet !== 'all') activeCount++;
    if (filters.bit !== 'all') activeCount++;
    if (filters.minEloDiff > 0) activeCount++;
    if (filters.maxEloDiff < Infinity && document.getElementById('maxEloDiff').value) activeCount++;
    if (filters.eloChange !== 'all') activeCount++;
    
    const countBadge = document.getElementById('activeFiltersCount');
    if (countBadge) {
        if (activeCount > 0) {
            countBadge.textContent = activeCount;
            countBadge.classList.add('visible');
        } else {
            countBadge.classList.remove('visible');
        }
    }
}

// Mobile sorting
function setupMobileSorting() {
    const sortButton = document.getElementById('mobileSortButton');
    const sortModal = document.getElementById('sortModal');
    const sortModalClose = document.getElementById('sortModalClose');
    
    if (!sortButton || !sortModal || !sortModalClose) return;
    
    sortButton.addEventListener('click', openSortModal);
    sortModalClose.addEventListener('click', closeSortModal);
    sortModal.addEventListener('click', (e) => {
        if (e.target === sortModal) closeSortModal();
    });
}

function openSortModal() {
    const sortModal = document.getElementById('sortModal');
    const sortModalBody = document.getElementById('sortModalBody');
    
    if (!sortModal || !sortModalBody) return;
    
    sortModalBody.innerHTML = '';
    
    COLUMN_DEFINITIONS.forEach((col, index) => {
        if (!col.sortable) return;
        
        const option = document.createElement('div');
        option.className = 'sort-option';
        if (currentSort.column === index) option.classList.add('active');
        
        const label = document.createElement('div');
        label.className = 'sort-option-label';
        label.textContent = col.abbrev;
        
        const directionContainer = document.createElement('div');
        directionContainer.className = 'sort-option-direction';
        
        const ascBtn = document.createElement('button');
        ascBtn.className = 'direction-btn';
        ascBtn.textContent = '↑';
        if (currentSort.column === index && currentSort.asc) ascBtn.classList.add('active');
        ascBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, true);
            closeSortModal();
        };
        
        const descBtn = document.createElement('button');
        descBtn.className = 'direction-btn';
        descBtn.textContent = '↓';
        if (currentSort.column === index && !currentSort.asc) descBtn.classList.add('active');
        descBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, false);
            closeSortModal();
        };
        
        directionContainer.appendChild(ascBtn);
        directionContainer.appendChild(descBtn);
        
        option.appendChild(label);
        option.appendChild(directionContainer);
        
        option.addEventListener('click', () => {
            const newAsc = currentSort.column === index ? !currentSort.asc : true;
            sortByColumnMobile(index, newAsc);
            closeSortModal();
        });
        
        sortModalBody.appendChild(option);
    });
    
    sortModal.classList.add('active');
}

function closeSortModal() {
    const sortModal = document.getElementById('sortModal');
    if (sortModal) sortModal.classList.remove('active');
}

function sortByColumnMobile(colIndex, asc) {
    currentSort = { column: colIndex, asc };
    sortMatches();
    displayMatches();
    updateCurrentSortLabel();
}

function updateCurrentSortLabel() {
    const currentSortLabel = document.getElementById('currentSortLabel');
    if (!currentSortLabel) return;
    
    const col = COLUMN_DEFINITIONS[currentSort.column];
    const direction = currentSort.asc ? '↑' : '↓';
    currentSortLabel.textContent = `${col.abbrev} ${direction}`;
}

// Pagination event handlers
function setupPagination() {
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            updatePagination();
            displayMatches();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredMatches.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            updatePagination();
            displayMatches();
        }
    });
    
    document.getElementById('pageSize').addEventListener('change', () => {
        currentPage = 1;
        updatePagination();
        displayMatches();
    });
}

// Main initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Load beys data first for part filtering
    await loadBeysDataForFilters();
    
    // Load rounds data before loading matches
    await loadRoundsData();
    
    // Load matches
    await loadMatches();
    
    // Setup event listeners for filters
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('dateFilter').addEventListener('change', applyFilters);
    document.getElementById('beyFilter').addEventListener('change', applyFilters);
    document.getElementById('bladeFilter').addEventListener('change', applyFilters);
    document.getElementById('ratchetFilter').addEventListener('change', applyFilters);
    document.getElementById('bitFilter').addEventListener('change', applyFilters);
    document.getElementById('minEloDiff').addEventListener('input', applyFilters);
    document.getElementById('maxEloDiff').addEventListener('input', applyFilters);
    document.getElementById('eloChangeFilter').addEventListener('change', applyFilters);
    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    
    // Setup other features
    setupFiltersPanel();
    setupLegend();
    setupMobileSorting();
    setupPagination();
    updateCurrentSortLabel();
    updateActiveFiltersCount();
    
    // Handle resize
    window.addEventListener('resize', displayMatches);
});

// ============================================
// ROUNDS DISPLAY FUNCTIONS
// ============================================

// Create a detailed rounds row for the table
function createRoundsDetailRow(match) {
    const row = document.createElement('tr');
    row.className = 'rounds-detail-row';
    row.dataset.matchId = match.matchId;
    
    const cell = document.createElement('td');
    cell.colSpan = 13; // All columns + rounds column (including Match ID column)
    cell.className = 'rounds-detail-cell';
    
    // Build rounds table HTML
    let html = `
        <div class="rounds-detail-container" id="rounds-${match.matchId}">
            <div class="rounds-header-info">
                <span class="rounds-title">Round-by-Round Details</span>
                <span class="rounds-count">${match.rounds.length} rounds</span>
            </div>
            <table class="rounds-table">
                <thead>
                    <tr>
                        <th>Round</th>
                        <th>Winner</th>
                        <th>Finish Type</th>
                        <th>Points</th>
                        <th>Running Score</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    let runningScoreA = 0;
    let runningScoreB = 0;
    
    match.rounds.forEach((round, index) => {
        const finishStyle = FINISH_TYPE_STYLES[round.finish_type] || FINISH_TYPE_STYLES.spin;
        
        // Update running score
        if (round.winner === match.beyA) {
            runningScoreA += round.points_awarded;
        } else if (round.winner === match.beyB) {
            runningScoreB += round.points_awarded;
        }
        
        html += `
            <tr class="round-row">
                <td class="round-number">${round.round_number || index + 1}</td>
                <td class="round-winner ${round.winner === match.winner ? 'match-winner-round' : ''}">${round.winner}</td>
                <td class="round-finish">
                    <span class="finish-badge" style="background: ${finishStyle.bgColor}; color: ${finishStyle.color};">
                        <span class="finish-icon">${finishStyle.icon}</span>
                        ${finishStyle.label}
                    </span>
                </td>
                <td class="round-points">+${round.points_awarded}</td>
                <td class="round-score">${runningScoreA} - ${runningScoreB}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
            <div class="rounds-summary">
                <div class="finish-summary">
                    ${createFinishTypeSummary(match.rounds)}
                </div>
            </div>
        </div>
    `;
    
    cell.innerHTML = html;
    row.appendChild(cell);
    
    return row;
}

// Create finish type summary badges
function createFinishTypeSummary(rounds) {
    const counts = {};
    rounds.forEach(round => {
        const type = round.finish_type || 'spin';
        counts[type] = (counts[type] || 0) + 1;
    });
    
    return Object.entries(counts).map(([type, count]) => {
        const style = FINISH_TYPE_STYLES[type] || FINISH_TYPE_STYLES.spin;
        return `
            <span class="finish-summary-badge" style="background: ${style.bgColor}; color: ${style.color};">
                ${style.icon} ${style.label}: ${count}
            </span>
        `;
    }).join('');
}

// Create mobile rounds HTML
function createMobileRoundsHtml(match) {
    let html = '<div class="mobile-rounds-list">';
    
    let runningScoreA = 0;
    let runningScoreB = 0;
    
    match.rounds.forEach((round, index) => {
        const finishStyle = FINISH_TYPE_STYLES[round.finish_type] || FINISH_TYPE_STYLES.spin;
        
        // Update running score
        if (round.winner === match.beyA) {
            runningScoreA += round.points_awarded;
        } else if (round.winner === match.beyB) {
            runningScoreB += round.points_awarded;
        }
        
        html += `
            <div class="mobile-round-item">
                <div class="mobile-round-header">
                    <span class="mobile-round-number">R${round.round_number || index + 1}</span>
                    <span class="finish-badge" style="background: ${finishStyle.bgColor}; color: ${finishStyle.color};">
                        ${finishStyle.icon} ${finishStyle.label}
                    </span>
                    <span class="mobile-round-points">+${round.points_awarded}</span>
                </div>
                <div class="mobile-round-details">
                    <span class="mobile-round-winner">${round.winner}</span>
                    <span class="mobile-round-score">${runningScoreA} - ${runningScoreB}</span>
                </div>
            </div>
        `;
    });
    
    html += `
        <div class="mobile-rounds-summary">
            ${createFinishTypeSummary(match.rounds)}
        </div>
    </div>`;
    
    return html;
}

// Toggle rounds row visibility (desktop)
function toggleRoundsRow(matchId) {
    const btn = document.querySelector(`button[data-match-id="${matchId}"]`);
    const existingRoundsRow = document.querySelector(`tr.rounds-detail-row[data-match-id="${matchId}"]`);
    
    if (expandedMatches.has(matchId)) {
        // Collapse
        expandedMatches.delete(matchId);
        if (existingRoundsRow) {
            existingRoundsRow.remove();
        }
        if (btn) {
            btn.innerHTML = '▼';
            btn.setAttribute('aria-expanded', 'false');
        }
    } else {
        // Expand
        expandedMatches.add(matchId);
        
        // Find the match data
        const match = filteredMatches.find(m => m.matchId === matchId);
        if (match && match.rounds && match.rounds.length > 0) {
            // Find the main row and insert rounds row after it
            const mainRow = document.querySelector(`tr[data-match-id="${matchId}"]:not(.rounds-detail-row)`);
            if (mainRow) {
                const roundsRow = createRoundsDetailRow(match);
                mainRow.after(roundsRow);
            }
        }
        
        if (btn) {
            btn.innerHTML = '▲';
            btn.setAttribute('aria-expanded', 'true');
        }
    }
}

// Toggle mobile rounds visibility
function toggleMobileRounds(matchId) {
    const content = document.getElementById(`mobile-rounds-${matchId}`);
    const toggle = document.querySelector(`.matches-card[data-match-id="${matchId}"] .card-rounds-toggle`);
    
    if (expandedMatches.has(matchId)) {
        expandedMatches.delete(matchId);
        if (content) content.classList.remove('expanded');
        if (toggle) {
            toggle.classList.remove('expanded');
            toggle.querySelector('.toggle-icon').textContent = '▼';
        }
    } else {
        expandedMatches.add(matchId);
        if (content) content.classList.add('expanded');
        if (toggle) {
            toggle.classList.add('expanded');
            toggle.querySelector('.toggle-icon').textContent = '▲';
        }
    }
}

// Copy match ID to clipboard
function copyMatchId(matchId) {
    navigator.clipboard.writeText(matchId).then(() => {
        // Show brief visual feedback
        const elements = document.querySelectorAll(`.match-id`);
        elements.forEach(el => {
            if (el.textContent === matchId) {
                el.classList.add('copied');
                setTimeout(() => el.classList.remove('copied'), 1000);
            }
        });
    }).catch(err => {
        console.error('Failed to copy match ID:', err);
    });
}
