/**
 * season.js
 * Loads and displays individual season details including tier tables,
 * promotion/relegation, matchdays, and Season Cup bracket.
 */

let currentSeason = null;
let roundsData = {}; // Mapping of match_id to rounds array
let expandedMatches = new Set(); // Track which matches are expanded
let xtremeEloData = {}; // Mapping of bey name to Xtreme ELO
let collapsedSections = new Set(['qualification-pool']); // Track which sections are collapsed (qualification pool collapsed by default)
let selectedMatchdays = {}; // Track selected matchday for each tier (tier -> matchday number)
let selectedTableSnapshots = {}; // Track selected table snapshot matchday for each tier (tier -> matchday number)
let tableSnapshotsData = {}; // Store loaded snapshot data (tier -> array of snapshots)
let tierFullSizes = {}; // Store the full (final) tier size for each tier to drive zone highlighting
let tableSortStates = {}; // Track sort column/direction per tier: {tier: {col, dir}} dir = 'asc'|'desc'|null
let fixtureMatchdays = []; // Track available matchdays for upcoming fixtures
let selectedFixtureMatchday = null; // Track selected matchday for upcoming fixtures
let fixturesByMatchday = {}; // Store fixtures grouped by matchday
let fixturesById = {}; // Map fixture_id -> fixture data
let simulatedFixtureResults = {}; // Map fixture_id -> simulated result data

// Default sort applied to all tier tables on initial render
const TABLE_DEFAULT_SORT_COL = 'season_points';
const TABLE_DEFAULT_SORT_DIR = 'desc';

/**
 * Add soft hyphens before capital letters in compound Bey names for better line breaking
 * E.g., "CobaltDragoon" becomes "Cobalt&shy;Dragoon"
 */
function addSoftHyphens(name) {
    // Add soft hyphen before every capital letter that follows a lowercase letter
    return name.replace(/([a-z])([A-Z])/g, '$1&shy;$2');
}

// Finish type styling configuration
const FINISH_TYPE_STYLES = {
    spin: { color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.15)', label: 'Spin', icon: '🔄', points: 1 },
    burst: { color: '#ef4444', bgColor: 'rgba(239, 68, 68, 0.15)', label: 'Burst', icon: '💥', points: 2 },
    pocket: { color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.15)', label: 'Pocket', icon: '🎯', points: 2 },
    stadium_exit: { color: '#06b6d4', bgColor: 'rgba(6, 182, 212, 0.15)', label: 'Stadium Exit', icon: '🥏', points: 2 },
    extreme: { color: '#8b5cf6', bgColor: 'rgba(139, 92, 246, 0.15)', label: 'Extreme', icon: '⚡', points: 3 }
};

// Load season data on page load
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const seasonId = urlParams.get('id');
    
    if (seasonId) {
        // Load both rounds data and Xtreme ELO data before loading season
        Promise.all([loadRoundsData(), loadXtremeEloData()]).then(() => {
            loadSeason(seasonId);
        });
    } else {
        showError('No season ID provided');
    }
});

/**
 * Load rounds data from matches_with_rounds.json
 */
async function loadRoundsData() {
    try {
        const response = await fetch(DATA_PATHS.MATCHES_WITH_ROUNDS_JSON);
        const data = await response.json();
        
        // Create a mapping of match_id to rounds and ELO values
        if (data.matches) {
            data.matches.forEach(match => {
                if (match.rounds && match.rounds.length > 0) {
                    roundsData[match.match_id] = {
                        rounds: match.rounds,
                        bey_a: match.bey_a ?? match.BeyA ?? '',
                        bey_b: match.bey_b ?? match.BeyB ?? '',
                        score_a: match.score_a ?? match.ScoreA ?? 0,
                        score_b: match.score_b ?? match.ScoreB ?? 0,
                        elo_a: match.elo_a,
                        elo_b: match.elo_b,
                        post_elo_a: match.post_elo_a,
                        post_elo_b: match.post_elo_b
                    };
                }
            });
        }
        
        console.log(`Loaded rounds data for ${Object.keys(roundsData).length} matches`);
    } catch (error) {
        console.error('Error loading rounds data:', error);
        roundsData = {};
    }
}

/**
 * Load Xtreme stadium ELO data from leaderboard
 */
async function loadXtremeEloData() {
    try {
        const response = await fetch(DATA_PATHS.LEADERBOARD_XTREME_CSV);
        if (!response.ok) {
            throw new Error('Failed to load Xtreme leaderboard');
        }
        
        const csvText = await response.text();
        const lines = csvText.trim().split('\n');
        
        // Skip header row
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i];
            if (!line.trim()) continue;
            
            const values = line.split(',');
            if (values.length >= 3) {
                const beyName = values[1]; // Name is in second column
                const elo = parseFloat(values[2]); // ELO is in third column
                
                if (beyName && !isNaN(elo)) {
                    xtremeEloData[beyName] = elo;
                }
            }
        }
        
        console.log(`Loaded Xtreme ELO data for ${Object.keys(xtremeEloData).length} Beys`);
    } catch (error) {
        console.error('Error loading Xtreme ELO data:', error);
        xtremeEloData = {};
    }
}

/**
 * Load table snapshots CSV data for a specific tier
 */
async function loadTableSnapshots(seasonId, tier) {
    try {
        const response = await fetch(DATA_PATHS.tableSnapshots(seasonId, tier));
        if (!response.ok) {
            console.log(`No table snapshots found for ${seasonId} Tier ${tier}`);
            return [];
        }
        
        const csvText = await response.text();
        const lines = csvText.trim().split('\n');
        
        const snapshots = {};
        
        // Skip header row
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            
            const values = line.split(',');
            if (values.length >= 12) {
                const matchday = parseInt(values[0]);
                const position = parseInt(values[1]);
                const bey = values[2];
                const matches = parseInt(values[3]);
                const wins = parseInt(values[4]);
                const losses = parseInt(values[5]);
                const seasonPoints = parseInt(values[6]);
                const pointsFor = parseInt(values[7]);
                const pointsAgainst = parseInt(values[8]);
                const pointDiff = parseInt(values[9]);
                const elo = parseFloat(values[10]);
                const positionDelta = parseInt(values[11]);
                // New stats (columns 12-15, present in updated CSVs; fall back to 0)
                const rw = values.length > 12 ? parseInt(values[12]) || 0 : 0;
                const rl = values.length > 13 ? parseInt(values[13]) || 0 : 0;
                const ppr = values.length > 14 ? parseFloat(values[14]) || 0 : 0;
                const ppw = values.length > 15 ? parseFloat(values[15]) || 0 : 0;
                
                if (!snapshots[matchday]) {
                    snapshots[matchday] = [];
                }
                
                snapshots[matchday].push({
                    position,
                    bey,
                    matches,
                    wins,
                    losses,
                    season_points: seasonPoints,
                    points_for: pointsFor,
                    points_against: pointsAgainst,
                    point_diff: pointDiff,
                    elo,
                    position_delta: positionDelta,
                    rw,
                    rl,
                    ppr,
                    ppw,
                });
            }
        }
        
        console.log(`Loaded table snapshots for ${seasonId} Tier ${tier}: ${Object.keys(snapshots).length} matchdays`);
        return snapshots;
    } catch (error) {
        console.error(`Error loading table snapshots for ${seasonId} Tier ${tier}:`, error);
        return [];
    }
}

/**
 * Load specific season data
 */
async function loadSeason(seasonId) {
    try {
        const response = await fetch(DATA_PATHS.SEASON_DATA_JSON);
        if (!response.ok) {
            throw new Error('Failed to load season data');
        }
        
        const data = await response.json();
        const season = data.seasons?.[seasonId];
        
        if (!season) {
            showError(`Season ${seasonId} not found`);
            return;
        }
        
        currentSeason = season;
        displaySeason(seasonId, season);
    } catch (error) {
        console.error('Error loading season:', error);
        showError('Failed to load season data');
    }
}

/**
 * Initialize selected matchdays for each tier
 */
function initializeSelectedMatchdays(matchdays) {
    selectedMatchdays = {}; // Reset
    
    for (let tier = 1; tier <= 4; tier++) {
        const tierMatchdays = getTierMatchdays(matchdays, tier);
        if (tierMatchdays.length > 0) {
            selectedMatchdays[tier] = tierMatchdays[0]; // Start with first matchday
        }
    }
}

/**
 * Load table snapshots for all tiers
 */
async function loadAllTableSnapshots(seasonId) {
    tableSnapshotsData = {};
    selectedTableSnapshots = {};
    
    for (let tier = 1; tier <= 4; tier++) {
        const snapshots = await loadTableSnapshots(seasonId, tier);
        if (snapshots && Object.keys(snapshots).length > 0) {
            tableSnapshotsData[tier] = snapshots;
            // Initialize to last matchday (final standings) by default
            const matchdays = Object.keys(snapshots).map(Number).sort((a, b) => b - a);
            selectedTableSnapshots[tier] = matchdays[0]; // Start with final standings
        }
    }
}

/**
 * Display season overview and all components
 */
async function displaySeason(seasonId, season) {
    // Update title
    document.getElementById('season-title').textContent = seasonId;
    document.getElementById('season-subtitle').textContent = 
        `${season.start_date ? new Date(season.start_date).toLocaleDateString() : ''} - ${season.end_date ? new Date(season.end_date).toLocaleDateString() : 'Ongoing'}`;
    
    // Initialize matchday selections
    initializeSelectedMatchdays(season.matchdays || {});
    
    // Load table snapshots for all tiers
    await loadAllTableSnapshots(seasonId);
    
    // Display overview
    displayOverview(season, seasonId);
    
    // Display tier tables
    displayTierTables(season.league_tables || {});
    
    // Display fixtures if available
    if (season.fixtures && season.fixtures.upcoming_matches && season.fixtures.upcoming_matches.length > 0) {
        displayFixtures(season.fixtures);
    }
    
    // Display promotion/relegation
    if (season.promotion_relegation) {
        displayPromotionRelegation(season.promotion_relegation);
    }
    
    // Display Qualification Pool
    if (season.qualification_pool) {
        displayQualificationPool(season.qualification_pool);
    }
    
    // Display Season Cup
    if (season.season_cup) {
        displaySeasonCup(season.season_cup);
    }
    
    // Hide matchdays section - matches are now displayed per tier
    document.getElementById('matchdays-container').style.display = 'none';
}

/**
 * Display season overview stats
 */
function displayOverview(season, seasonId) {
    const container = document.getElementById('season-overview');
    
    const stats = season.statistics || {};
    const champion = season.league_champion || 'TBD';
    const cupWinner = season.cup_winner || 'TBD';
    
    // Calculate additional statistics from match data
    const matchdays = season.matchdays || {};
    const allMatches = [];
    Object.values(matchdays).forEach(matches => {
        if (Array.isArray(matches)) {
            allMatches.push(...matches);
        }
    });
    
    // Calculate comprehensive statistics
    let totalPoints = 0;
    let highestScore = 0;
    let lowestScore = Infinity;
    let totalPointDiff = 0;
    let blowouts = 0; // 3+ point difference
    
    allMatches.forEach(match => {
        const scoreA = match.score_a || 0;
        const scoreB = match.score_b || 0;
        const pointDiff = Math.abs(scoreA - scoreB);
        
        totalPoints += scoreA + scoreB;
        highestScore = Math.max(highestScore, scoreA, scoreB);
        if (scoreA > 0) lowestScore = Math.min(lowestScore, scoreA);
        if (scoreB > 0) lowestScore = Math.min(lowestScore, scoreB);
        totalPointDiff += pointDiff;
        
        if (pointDiff >= 3) {
            blowouts++;
        }
    });
    
    const avgPointsPerMatch = allMatches.length > 0 ? (totalPoints / allMatches.length).toFixed(1) : 0;
    const avgPointDiff = allMatches.length > 0 ? (totalPointDiff / allMatches.length).toFixed(1) : 0;
    
    if (lowestScore === Infinity) lowestScore = 0;
    
    // Create champion link if not TBD
    const championHtml = champion !== 'TBD' 
        ? `<a href="bey.html?name=${encodeURIComponent(champion)}" class="bey-link">${addSoftHyphens(champion)}</a>`
        : champion;
    const cupWinnerHtml = cupWinner !== 'TBD'
        ? `<a href="bey.html?name=${encodeURIComponent(cupWinner)}" class="bey-link">${addSoftHyphens(cupWinner)}</a>`
        : cupWinner;
    
    container.innerHTML = `
        <div class="season-overview-grid">
            <div class="overview-card champion-card">
                <h3>🏆 League Champion</h3>
                <p class="champion-name">${championHtml}</p>
                <p class="champion-note">Most consistent performer of the season</p>
            </div>
            <div class="overview-card cup-card">
                <h3>🏅 Season Cup Winner</h3>
                <p class="champion-name">${cupWinnerHtml}</p>
                <p class="champion-note">Post-season tournament champion</p>
            </div>
            <div class="overview-card stats-card">
                <h3>📊 Match Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Total Matches</span>
                        <span class="stat-value">${allMatches.length}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Total Points</span>
                        <span class="stat-value">${totalPoints}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Avg Points/Match</span>
                        <span class="stat-value">${avgPointsPerMatch}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Highest Score</span>
                        <span class="stat-value">${highestScore}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Blowouts</span>
                        <span class="stat-value">${blowouts}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Avg Point Diff</span>
                        <span class="stat-value">${avgPointDiff}</span>
                    </div>
                </div>
                <a href="season-stats.html?season=${seasonId}" class="view-stats-button">
                    <span class="button-icon">📈</span> View Advanced Statistics
                </a>
            </div>
        </div>
    `;
}

/**
 * Display tier tables with integrated matchday view
 */
function displayTierTables(leagueTables) {
    const container = document.getElementById('tier-tables');
    
    if (Object.keys(leagueTables).length === 0) {
        container.innerHTML = '<p class="no-data">No league tables available</p>';
        return;
    }
    
    // Get matchdays data from current season
    const matchdays = currentSeason?.matchdays || {};
    
    let html = '';
    
    // Display each tier
    for (let tier = 1; tier <= 4; tier++) {
        const table = leagueTables[tier.toString()];
        if (!table || table.length === 0) continue;
        
        // Record the full (final) tier size so snapshots use the right zone rules
        tierFullSizes[tier] = table.length;
        
        const tierNames = ['I', 'II', 'III', 'IV'];
        const sectionId = `tier-${tier}-content`;
        
        // Get all matchdays for this tier
        const tierMatchdays = getTierMatchdays(matchdays, tier);
        const currentMatchday = selectedMatchdays[tier] || tierMatchdays[0] || 1;
        
        // Get table snapshot data if available
        const hasSnapshots = tableSnapshotsData[tier] && Object.keys(tableSnapshotsData[tier]).length > 0;
        const snapshotMatchdays = hasSnapshots ? Object.keys(tableSnapshotsData[tier]).map(Number).sort((a, b) => a - b) : [];
        const currentSnapshotMatchday = selectedTableSnapshots[tier] || snapshotMatchdays[snapshotMatchdays.length - 1] || null;
        const displayTable = hasSnapshots && currentSnapshotMatchday ? tableSnapshotsData[tier][currentSnapshotMatchday] : table;
        
        const tierStats = getTierTableStats(displayTable);

        html += `
            <div class="tier-section-new">
                <h3 class="collapsible-header" onclick="toggleSection('${sectionId}')" data-section-id="${sectionId}">
                    <span class="section-toggle-icon">▼</span>
                    <span>🏆 Tier ${tierNames[tier-1]}</span>
                </h3>
                <div id="${sectionId}" class="collapsible-content">
                    <div class="tier-content-grid">
                        <div class="tier-table-column">
                            <div class="table-header-with-nav">
                                <h4 class="tier-subsection-header">📊 Table</h4>
                                ${hasSnapshots ? `
                                    <div class="table-snapshot-navigator">
                                        <button class="snapshot-nav-btn" onclick="changeTableSnapshot(${tier}, -1)" ${currentSnapshotMatchday <= snapshotMatchdays[0] ? 'disabled' : ''}>
                                            <span class="nav-arrow">◀</span>
                                        </button>
                                        <span class="snapshot-matchday-label">MD ${currentSnapshotMatchday}</span>
                                        <button class="snapshot-nav-btn" onclick="changeTableSnapshot(${tier}, 1)" ${currentSnapshotMatchday >= snapshotMatchdays[snapshotMatchdays.length - 1] ? 'disabled' : ''}>
                                            <span class="nav-arrow">▶</span>
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                            <div class="table-responsive">
                                <table class="league-table">
                                    <thead>
                                        <tr>
                                            <th>Pos</th>
                                            ${hasSnapshots ? '<th style="width:1.75rem;min-width:0;">Δ</th>' : ''}
                                            <th class="bey-name-header">Bey</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'matches' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'matches')" title="Matches played">M</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'wins' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'wins')" title="Wins">W</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'losses' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'losses')" title="Losses">L</th>
                                            <th class="sortable${(tableSortStates[tier]?.col ?? TABLE_DEFAULT_SORT_COL) === 'season_points' ? (' ' + ((tableSortStates[tier]?.dir ?? TABLE_DEFAULT_SORT_DIR) === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'season_points')" title="Season Points">SP</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'points_for' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'points_for')" title="Round Points Won">RPW</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'points_against' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'points_against')" title="Round Points Lost">RPL</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'point_diff' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'point_diff')" title="Round Points Difference">RPD</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'rw' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'rw')" title="Rounds Won">RW</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'rl' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'rl')" title="Rounds Lost">RL</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'ppr' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'ppr')" title="Round Points per Round Played">PPR</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'ppw' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'ppw')" title="Round Points per Round Won">PPW</th>
                                            <th class="sortable${tableSortStates[tier]?.col === 'elo' ? (' ' + (tableSortStates[tier].dir === 'asc' ? 'sorted-asc' : 'sorted-desc')) : ''}" onclick="sortTierTable(${tier}, 'elo')" title="ELO Rating">ELO</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                         ${displayTable.map((entry, idx) => createTableRow(entry, idx, tier, hasSnapshots, table.length, tierStats)).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="table-legend">
                                <span><strong>M</strong>=Matches, <strong>W</strong>=Wins, <strong>L</strong>=Losses, <strong>SP</strong>=Season Points</span>
                                <span><strong>RW</strong>=Rounds Won, <strong>RL</strong>=Rounds Lost</span>
                                <span><strong>PPR</strong>=Round Points per Round Played (RPW ÷ (RW+RL)), <strong>PPW</strong>=Round Points per Round Won (RPW ÷ RW)</span>
                                <span><strong>RPW</strong>=Round Points Won, <strong>RPL</strong>=Round Points Lost, <strong>RPD</strong>=Round Points Difference</span>
                            </div>
                            ${getPositionLegend(tier, table.length)}
                        </div>
                        <div class="tier-matches-column">
                            ${tierMatchdays.length > 0 ? `
                                <div class="matchday-navigator">
                                    <button class="matchday-nav-btn" onclick="changeMatchday(${tier}, -1)" ${currentMatchday <= tierMatchdays[0] ? 'disabled' : ''}>
                                        <span class="nav-arrow">◀</span>
                                    </button>
                                    <h4 class="matchday-title">Matchday ${currentMatchday}</h4>
                                    <button class="matchday-nav-btn" onclick="changeMatchday(${tier}, 1)" ${currentMatchday >= tierMatchdays[tierMatchdays.length - 1] ? 'disabled' : ''}>
                                        <span class="nav-arrow">▶</span>
                                    </button>
                                </div>
                                <div class="tier-matches-container" id="tier-${tier}-matches">
                                    ${displayTierMatches(matchdays, tier, currentMatchday)}
                                </div>
                            ` : '<p class="no-data">No match data available</p>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

/**
 * Get all matchdays available for a specific tier
 */
function getTierMatchdays(matchdays, tier) {
    const tierMatchdays = new Set();
    
    Object.keys(matchdays).forEach(md => {
        const matches = matchdays[md];
        if (Array.isArray(matches)) {
            matches.forEach(match => {
                if (match.tier === tier) {
                    tierMatchdays.add(parseInt(md));
                }
            });
        }
    });
    
    return Array.from(tierMatchdays).sort((a, b) => a - b);
}

/**
 * Display matches for a specific tier and matchday
 */
function displayTierMatches(matchdays, tier, matchday) {
    const matches = matchdays[matchday.toString()] || [];
    const tierMatches = matches.filter(match => match.tier === tier);
    
    if (tierMatches.length === 0) {
        return '<p class="no-data">No matches for this matchday</p>';
    }
    
    let html = '<div class="matches-grid">';
    
    tierMatches.forEach(match => {
        html += createMatchCard(match, matchday);
    });
    
    html += '</div>';
    return html;
}

/**
 * Create a compact match card with horizontal layout
 */
function createMatchCard(match, md) {
    const beyALink = `<a href="bey.html?name=${encodeURIComponent(match.bey_a)}" class="bey-link">${addSoftHyphens(match.bey_a)}</a>`;
    const beyBLink = `<a href="bey.html?name=${encodeURIComponent(match.bey_b)}" class="bey-link">${addSoftHyphens(match.bey_b)}</a>`;
    
    // Determine winner, loser, or tie
    const isAWinner = match.score_a > match.score_b;
    const isBWinner = match.score_b > match.score_a;
    const isTie = match.score_a === match.score_b;
    
    const winner = isTie ? 'Tie' : (isAWinner ? match.bey_a : match.bey_b);
    
    // Get bey classes based on result
    const beyAClass = isTie ? '' : (isAWinner ? 'winner' : '');
    const beyBClass = isTie ? '' : (isBWinner ? 'winner' : '');
    
    // Get season and arena info
    const seasonId = match.season_id || currentSeason?.season_id || 'S?';
    const tierNum = match.tier || '?';
    const arena = match.arena || 'Xtreme';
    const date = match.date || '';
    
    // Get rounds data and ELO values
    const matchData = roundsData[match.match_id];
    const hasRounds = matchData && matchData.rounds && matchData.rounds.length > 0;
    const isExpanded = expandedMatches.has(match.match_id);
    
    // Use ELO from roundsData if available, otherwise fallback to Xtreme ELO
    const eloA = matchData?.elo_a || 
                (match.elo_a && match.elo_a !== 1000 ? match.elo_a : null) || 
                xtremeEloData[match.bey_a] || 1000;
    const eloB = matchData?.elo_b || 
                (match.elo_b && match.elo_b !== 1000 ? match.elo_b : null) || 
                xtremeEloData[match.bey_b] || 1000;
    const postEloA = matchData?.post_elo_a;
    const postEloB = matchData?.post_elo_b;
    
    // Calculate ELO changes and difference
    const eloChangeA = postEloA ? Math.round(postEloA - eloA) : null;
    const eloChangeB = postEloB ? Math.round(postEloB - eloB) : null;
    const eloDiff = Math.abs(Math.round(eloA) - Math.round(eloB));
    
    // Create ELO delta badges
    const deltaBadgeA = eloChangeA !== null ? `<span class="elo-delta-badge ${eloChangeA >= 0 ? 'delta-elo-up' : 'delta-elo-down'}">${eloChangeA >= 0 ? '+' : ''}${eloChangeA}</span>` : '';
    const deltaBadgeB = eloChangeB !== null ? `<span class="elo-delta-badge ${eloChangeB >= 0 ? 'delta-elo-up' : 'delta-elo-down'}">${eloChangeB >= 0 ? '+' : ''}${eloChangeB}</span>` : '';
    
    // Arena badge
    const arenaBadge = arena === 'Xtreme' ? '⚡X' : '🎯DA';
    const arenaTitle = arena === 'Xtreme' ? 'Xtreme Stadium' : 'Drop Attack Beystadium';
    
    // Only generate rounds HTML if expanded (optimization)
    const roundsHtml = (hasRounds && isExpanded) ? createRoundsHtml(match, matchData.rounds) : '';
    
    return `
        <div class="season-match-card" data-match-id="${match.match_id}">
            <div class="season-card-header">
                <span class="card-match-id match-id" title="Click to copy" onclick="copyMatchId('${match.match_id}')">${match.match_id}</span>
                <span class="card-date">${date}</span>
                <span class="arena-badge arena-${arena.toLowerCase().replace(/\s+/g, '-')}" title="${arenaTitle}">${arenaBadge}</span>
                <span class="match-elo-diff" title="ELO Difference">Δ${eloDiff}</span>
            </div>
            <div class="season-card-match-compact">
                <div class="season-compact-bey season-compact-bey-left ${beyAClass}">
                    <span class="compact-bey-name">${beyALink}</span>
                    <span class="compact-bey-elo-change">${deltaBadgeA}</span>
                    <span class="compact-bey-score">${match.score_a}</span>
                </div>
                <span class="compact-vs">vs.</span>
                <div class="season-compact-bey season-compact-bey-right ${beyBClass}">
                    <span class="compact-bey-name">${beyBLink}</span>
                    <span class="compact-bey-elo-change">${deltaBadgeB}</span>
                    <span class="compact-bey-score">${match.score_b}</span>
                </div>
            </div>
            ${hasRounds ? `
            <div class="card-rounds-section">
                <button class="card-rounds-toggle ${isExpanded ? 'expanded' : ''}" onclick="toggleMatchRounds('${match.match_id}', ${matchData.rounds.length})">
                    <span class="toggle-icon">${isExpanded ? '▲' : '▼'}</span>
                    Show Rounds (${matchData.rounds.length})
                </button>
                <div class="card-rounds-content ${isExpanded ? 'expanded' : ''}" id="rounds-${match.match_id}">
                    ${roundsHtml}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

/**
 * Update matches and navigator for a specific tier
 */
function updateTierMatches(tier) {
    const matchdays = currentSeason?.matchdays || {};
    const tierMatchdays = getTierMatchdays(matchdays, tier);
    const currentMatchday = selectedMatchdays[tier] || tierMatchdays[0] || 1;
    
    // Update matchday title
    const titleElement = document.querySelector(`#tier-${tier}-content .matchday-title`);
    if (titleElement) {
        titleElement.textContent = `Matchday ${currentMatchday}`;
    }
    
    // Update navigation buttons
    const prevBtn = document.querySelector(`#tier-${tier}-content .matchday-nav-btn:first-of-type`);
    const nextBtn = document.querySelector(`#tier-${tier}-content .matchday-nav-btn:last-of-type`);
    
    if (prevBtn) {
        prevBtn.disabled = currentMatchday <= tierMatchdays[0];
    }
    if (nextBtn) {
        nextBtn.disabled = currentMatchday >= tierMatchdays[tierMatchdays.length - 1];
    }
    
    // Update matches
    const matchesContainer = document.getElementById(`tier-${tier}-matches`);
    if (matchesContainer) {
        matchesContainer.innerHTML = displayTierMatches(matchdays, tier, currentMatchday);
    }
}

/**
 * Change matchday for a specific tier
 */
function changeMatchday(tier, direction) {
    const matchdays = currentSeason?.matchdays || {};
    const tierMatchdays = getTierMatchdays(matchdays, tier);
    
    if (tierMatchdays.length === 0) return;
    
    const currentIdx = tierMatchdays.indexOf(selectedMatchdays[tier]);
    const newIdx = currentIdx + direction;
    
    if (newIdx >= 0 && newIdx < tierMatchdays.length) {
        selectedMatchdays[tier] = tierMatchdays[newIdx];
        
        // Update only this tier's matches
        updateTierMatches(tier);
    }
}

/**
 * Change table snapshot matchday for a tier
 */
function changeTableSnapshot(tier, direction) {
    const snapshots = tableSnapshotsData[tier];
    if (!snapshots) return;
    
    const snapshotMatchdays = Object.keys(snapshots).map(Number).sort((a, b) => a - b);
    const currentIdx = snapshotMatchdays.indexOf(selectedTableSnapshots[tier]);
    const newIdx = currentIdx + direction;
    
    if (newIdx >= 0 && newIdx < snapshotMatchdays.length) {
        selectedTableSnapshots[tier] = snapshotMatchdays[newIdx];
        
        // Update only this tier's table
        updateTierTable(tier);
    }
}

/**
 * Update only the table for a specific tier
 */
function updateTierTable(tier) {
    const hasSnapshots = tableSnapshotsData[tier] && Object.keys(tableSnapshotsData[tier]).length > 0;
    const displayTable = getDisplayTableForTier(tier);
    if (!displayTable) return;
    const tierStats = getTierTableStats(displayTable);
    const snapshotMatchdays = hasSnapshots
        ? Object.keys(tableSnapshotsData[tier]).map(Number).sort((a, b) => a - b)
        : [];
    
    // Update table body, applying current sort state
    const tbody = document.querySelector(`#tier-${tier}-content .league-table tbody`);
    if (tbody) {
        const sortState = tableSortStates[tier] || { col: TABLE_DEFAULT_SORT_COL, dir: TABLE_DEFAULT_SORT_DIR };
        const sorted = [...displayTable].sort((a, b) => {
            let valA = a[sortState.col] ?? 0;
            let valB = b[sortState.col] ?? 0;
            if (typeof valA === 'string') {
                return sortState.dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            }
            return sortState.dir === 'asc' ? valA - valB : valB - valA;
        });
        tbody.innerHTML = sorted.map((entry, idx) => createTableRow(
            entry,
            idx,
            tier,
            hasSnapshots,
            tierFullSizes[tier] || displayTable.length,
            tierStats
        )).join('');
    }
    
    // Update navigation buttons
    const navContainer = document.querySelector(`#tier-${tier}-content .table-snapshot-navigator`);
    if (navContainer && hasSnapshots) {
        const currentSnapshotMatchday = selectedTableSnapshots[tier];
        const prevBtn = navContainer.querySelector('.snapshot-nav-btn:first-child');
        const nextBtn = navContainer.querySelector('.snapshot-nav-btn:last-child');
        const label = navContainer.querySelector('.snapshot-matchday-label');
        
        if (prevBtn) {
            prevBtn.disabled = currentSnapshotMatchday <= snapshotMatchdays[0];
        }
        if (nextBtn) {
            nextBtn.disabled = currentSnapshotMatchday >= snapshotMatchdays[snapshotMatchdays.length - 1];
        }
        if (label) {
            label.textContent = `MD ${currentSnapshotMatchday}`;
        }
    }
}

/**
 * Sort the league table for a specific tier by a given column.
 * Clicking the same column toggles between descending and ascending.
 * Clicking a different column sorts descending by default.
 */
function sortTierTable(tier, column) {
    // Determine current sort direction for this tier/column
    const current = tableSortStates[tier] || { col: TABLE_DEFAULT_SORT_COL, dir: TABLE_DEFAULT_SORT_DIR };
    let dir;
    if (current.col === column) {
        dir = current.dir === 'desc' ? 'asc' : 'desc';
    } else {
        // First click on a new column: always descending (best first)
        dir = 'desc';
    }
    tableSortStates[tier] = { col: column, dir };

    // Get current display table
    const hasSnapshots = tableSnapshotsData[tier] && Object.keys(tableSnapshotsData[tier]).length > 0;
    const displayTable = getDisplayTableForTier(tier);
    if (!displayTable) return;
    const tierStats = getTierTableStats(displayTable);

    // Sort a copy of the table
    const sorted = [...displayTable].sort((a, b) => {
        let valA = a[column] ?? 0;
        let valB = b[column] ?? 0;
        // For string columns, use locale compare
        if (typeof valA === 'string') {
            return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return dir === 'asc' ? valA - valB : valB - valA;
    });

    // Re-render rows
    const tbody = document.querySelector(`#tier-${tier}-content .league-table tbody`);
    if (tbody) {
        tbody.innerHTML = sorted.map((entry, idx) =>
            createTableRow(
                entry,
                idx,
                tier,
                hasSnapshots,
                tierFullSizes[tier] || displayTable.length,
                tierStats
            )
        ).join('');
    }

    // Update header sort indicators
    const thead = document.querySelector(`#tier-${tier}-content .league-table thead`);
    if (thead) {
        thead.querySelectorAll('th.sortable').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        // Find the header that matches the column by its onclick attribute
        const activeHeader = Array.from(thead.querySelectorAll('th.sortable')).find(th => {
            const onclick = th.getAttribute('onclick') || '';
            return onclick.includes(`'${column}'`);
        });
        if (activeHeader) {
            activeHeader.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    }
}

/**
 * Get position legend for tier
 */
function getPositionLegend(tier, tierSize = 8) {
    let html = '<div class="position-legend">';

    if (tierSize >= 10) {
        // Legacy S1 rules (10 beys per tier, 3 tiers)
        if (tier > 1) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator promotion"></div>
                    <span>Promotion (Ranks 1–2)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator playoff"></div>
                    <span>Promotion Playoff (3rd)</span>
                </div>
            `;
        }
        if (tier < 3) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator qualification"></div>
                    <span>Relegation Playoff (8th)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator relegation"></div>
                    <span>Relegation (9th–10th)</span>
                </div>
            `;
        }
        if (tier === 3) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator qualification"></div>
                    <span>Qualification Tournament (7th–10th)</span>
                </div>
            `;
        }
    } else {
        // S2+ rules (8 beys per tier, 4 tiers)
        if (tier === 2) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator promotion"></div>
                    <span>Promotion (1st)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator playoff"></div>
                    <span>Promotion Playoff (2nd)</span>
                </div>
            `;
        } else if (tier > 2) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator promotion"></div>
                    <span>Promotion (Ranks 1–2)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator playoff"></div>
                    <span>Promotion Playoff (3rd)</span>
                </div>
            `;
        }
        if (tier === 1) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator qualification"></div>
                    <span>Relegation Playoff (7th)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator relegation"></div>
                    <span>Relegation (8th)</span>
                </div>
            `;
        } else if (tier === 2 || tier === 3) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator qualification"></div>
                    <span>Relegation Playoff (6th)</span>
                </div>
                <div class="position-legend-item">
                    <div class="position-legend-indicator relegation"></div>
                    <span>Relegation (7th–8th)</span>
                </div>
            `;
        }
        if (tier === 4) {
            html += `
                <div class="position-legend-item">
                    <div class="position-legend-indicator qualification"></div>
                    <span>Qualification Pool (5th–8th)</span>
                </div>
            `;
        }
    }

    html += '</div>';
    return html;
}

/**
 * Compute tier-level stats for conditional formatting.
 */
function getTierTableStats(table = []) {
    if (!Array.isArray(table) || table.length === 0) {
        return {
            maxSeasonPoints: 0,
            maxAbsPointDiff: 0,
            minElo: 0,
            maxElo: 0,
            eloLow: 0,
            eloHigh: 0
        };
    }

    const seasonPoints = table.map(entry => entry.season_points ?? 0);
    const pointDiffs = table.map(entry => entry.point_diff ?? 0);
    const elos = table.map(entry => {
        const value = xtremeEloData[entry.bey] !== undefined ? xtremeEloData[entry.bey] : entry.elo;
        return value ?? 0;
    });

    const maxSeasonPoints = Math.max(...seasonPoints);
    const maxAbsPointDiff = Math.max(...pointDiffs.map(diff => Math.abs(diff)));

    const sortedElos = [...elos].sort((a, b) => a - b);
    const minElo = sortedElos[0] ?? 0;
    const maxElo = sortedElos[sortedElos.length - 1] ?? 0;
    const lowIndex = Math.floor((sortedElos.length - 1) / 3);
    const highIndex = Math.floor(((sortedElos.length - 1) * 2) / 3);

    return {
        maxSeasonPoints,
        maxAbsPointDiff,
        minElo,
        maxElo,
        eloLow: sortedElos[lowIndex] ?? minElo,
        eloHigh: sortedElos[highIndex] ?? maxElo
    };
}

/**
 * Determine trend class for point differential values.
 */
function getPointDiffClass(value, maxAbs) {
    if (!maxAbs || value === 0) return 'trend-neutral';

    const ratio = Math.abs(value) / maxAbs;
    if (value > 0) return ratio >= 0.66 ? 'trend-very-positive' : 'trend-positive';
    if (value < 0) return ratio >= 0.66 ? 'trend-very-negative' : 'trend-negative';
    return 'trend-neutral';
}

/**
 * Determine ELO trend class within a tier.
 */
function getEloTrendClass(value, stats) {
    if (!stats || stats.maxElo === stats.minElo) return 'trend-neutral';
    if (value === stats.maxElo) return 'trend-very-positive';
    if (value === stats.minElo) return 'trend-very-negative';
    if (value >= stats.eloHigh) return 'trend-positive';
    if (value <= stats.eloLow) return 'trend-negative';
    return 'trend-neutral';
}

/**
 * Create table row with position indicators.
 * tierSize is the number of entries in the tier (used to pick S1 vs S2+ rules).
 */
function createTableRow(entry, idx, tier, hasSnapshots = false, tierSize = 8, tierStats = null) {
    let positionClass = '';
    let positionIndicator = '';

    if (tierSize >= 10) {
        // Legacy S1 rules (10 beys per tier, 3 tiers)
        if (tier > 1 && idx < 2) {
            positionClass = 'promotion-zone';
            positionIndicator = ' ↑';
        } else if (tier > 1 && idx === 2) {
            positionClass = 'playoff-zone';
            positionIndicator = ' ↕';
        } else if (tier < 3 && idx === 7) {
            positionClass = 'qualification-zone';
            positionIndicator = ' ↕';
        } else if (tier < 3 && idx >= 8) {
            positionClass = 'relegation-zone';
            positionIndicator = ' ↓';
        } else if (tier === 3 && idx >= 6) {
            positionClass = 'qualification-zone';
            positionIndicator = ' Q';
        }
    } else {
        // S2+ rules (8 beys per tier, 4 tiers)
        // Promotion zone (top 1 for Tier II, else top 2, except Tier I)
        if ((tier > 2 && idx < 2) || (tier === 2 && idx < 1)) {
            positionClass = 'promotion-zone';
            positionIndicator = ' ↑';
        }
        // Promotion playoff zone (2nd place in Tier II, 3rd place in Tiers III & IV)
        else if ((tier > 2 && idx === 2) || (tier === 2 && idx === 1)) {
            positionClass = 'playoff-zone';
            positionIndicator = ' ↕';
        }
        // Relegation match zone (7th in Tier I, 6th in Tiers II & III)
        else if ((tier < 4 && idx === 5 && tier > 1) || (tier === 1 && idx === 6)) {
            positionClass = 'qualification-zone';
            positionIndicator = ' ↕';
        }
        // Relegation zone (bottom 2 for Tiers II-III, last rank for Tier I)
        else if ((tier < 4 && tier > 1 && idx >= 6) || (tier === 1 && idx === 7)) {
            positionClass = 'relegation-zone';
            positionIndicator = ' ↓';
        }
        // Qualification zone (Tier IV positions 5-8 enter qualification)
        else if (tier === 4 && idx >= 4) {
            positionClass = 'qualification-zone';
            positionIndicator = ' Q';
        }
    }
    
    // Create Bey link with soft hyphens
    const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${addSoftHyphens(entry.bey)}</a>`;
    
    // Use Xtreme ELO if available, otherwise fall back to entry.elo
    const displayElo = xtremeEloData[entry.bey] !== undefined ? xtremeEloData[entry.bey] : entry.elo;
    const eloTrendClass = tierStats ? getEloTrendClass(displayElo ?? 0, tierStats) : '';
    const pointDiffClass = tierStats ? getPointDiffClass(entry.point_diff ?? 0, tierStats.maxAbsPointDiff) : '';
    const seasonPointsClass = tierStats && entry.season_points === tierStats.maxSeasonPoints ? 'stat-leader' : '';
    
    // Format position delta if snapshots are available
    let deltaCell = '';
    if (hasSnapshots && entry.position_delta !== undefined) {
        const delta = entry.position_delta;
        let deltaClass = '';
        let deltaSymbol = '';
        
        if (delta > 0) {
            deltaClass = 'delta-up';
            deltaSymbol = `↑${delta}`;
        } else if (delta < 0) {
            deltaClass = 'delta-down';
            deltaSymbol = `↓${Math.abs(delta)}`;
        } else {
            deltaClass = 'delta-same';
            deltaSymbol = '━';
        }
        
        deltaCell = `<td class="position-delta ${deltaClass}" style="width:2.0rem;min-width:0;">${deltaSymbol}</td>`;
    }
    
    return `
        <tr class="${positionClass}">
            <td>${entry.position}${positionIndicator}</td>
            ${deltaCell}
            <td class="bey-name"><strong>${beyLink}</strong></td>
            <td>${entry.matches}</td>
            <td>${entry.wins}</td>
            <td>${entry.losses}</td>
            <td class="${seasonPointsClass}"><strong>${entry.season_points}</strong></td>
            <td>${entry.points_for}</td>
            <td>${entry.points_against}</td>
            <td class="${pointDiffClass}">${entry.point_diff > 0 ? '+' : ''}${entry.point_diff}</td>
            <td>${entry.rw ?? 0}</td>
            <td>${entry.rl ?? 0}</td>
            <td>${entry.ppr != null && (entry.rw + entry.rl) > 0 ? entry.ppr.toFixed(2) : '—'}</td>
            <td>${entry.ppw != null && entry.rw > 0 ? entry.ppw.toFixed(2) : '—'}</td>
            <td class="${eloTrendClass}">${Math.round(displayElo)}</td>
        </tr>
    `;
}

/**
 * Display promotion and relegation summary
 */
function displayPromotionRelegation(data) {
    const container = document.getElementById('promotion-relegation-content');
    const sectionContainer = document.getElementById('promotion-relegation-container');
    
    sectionContainer.style.display = 'block';
    
    let html = '<div class="pr-grid">';
    
    // Automatic Promotions
    if (data.automatic_promotion && data.automatic_promotion.length > 0) {
        html += `
            <div class="pr-section promotion-section">
                <h4>⬆️ Automatic Promotions</h4>
                <ul>
                    ${data.automatic_promotion.map(p => {
                        const beyLink = `<a href="bey.html?name=${encodeURIComponent(p.bey)}" class="bey-link">${addSoftHyphens(p.bey)}</a>`;
                        return `<li><strong>${beyLink}</strong> (Tier ${p.from_tier} → Tier ${p.to_tier})</li>`;
                    }).join('')}
                </ul>
            </div>
        `;
    }
    
    // Automatic Relegations
    if (data.automatic_relegation && data.automatic_relegation.length > 0) {
        html += `
            <div class="pr-section relegation-section">
                <h4>⬇️ Automatic Relegations</h4>
                <ul>
                    ${data.automatic_relegation.map(r => {
                        const beyLink = `<a href="bey.html?name=${encodeURIComponent(r.bey)}" class="bey-link">${addSoftHyphens(r.bey)}</a>`;
                        return `<li><strong>${beyLink}</strong> (Tier ${r.from_tier} → Tier ${r.to_tier})</li>`;
                    }).join('')}
                </ul>
            </div>
        `;
    }
    
    html += '</div>';
    
    // Relegation matches
    if (data.relegation_matches && data.relegation_matches.length > 0) {
        displayRelegationMatches(data.relegation_matches);
    }
    
    container.innerHTML = html;
}

/**
 * Display relegation matches
 */
function displayRelegationMatches(matches) {
    const container = document.getElementById('relegation-matches');
    const sectionContainer = document.getElementById('relegation-matches-container');
    
    sectionContainer.style.display = 'block';
    
    const html = `
        <div class="relegation-matches-list">
            ${matches.map(match => {
                const higherBeyLink = `<a href="bey.html?name=${encodeURIComponent(match.higher_bey)}" class="bey-link">${addSoftHyphens(match.higher_bey)}</a>`;
                const lowerBeyLink = `<a href="bey.html?name=${encodeURIComponent(match.lower_bey)}" class="bey-link">${addSoftHyphens(match.lower_bey)}</a>`;
                const scoreHigher = Number.isFinite(match.score_higher) ? match.score_higher : null;
                const scoreLower = Number.isFinite(match.score_lower) ? match.score_lower : null;
                const scoreLabel = (scoreHigher !== null && scoreLower !== null)
                    ? `${scoreHigher} - ${scoreLower}`
                    : 'TBD';
                
                return `
                <div class="relegation-match-card">
                    <div class="match-header">
                        <span class="tier-badge">Tier ${match.higher_tier} ↔ Tier ${match.lower_tier}</span>
                    </div>
                    <div class="match-participants">
                        <div class="participant">
                            <span class="position-badge">${match.higher_position}th</span>
                            <span class="bey-name">${higherBeyLink}</span>
                            <span class="tier-label">Tier ${match.higher_tier}</span>
                        </div>
                        <div class="vs">VS</div>
                        <div class="participant">
                            <span class="position-badge">${match.lower_position}rd</span>
                            <span class="bey-name">${lowerBeyLink}</span>
                            <span class="tier-label">Tier ${match.lower_tier}</span>
                        </div>
                    </div>
                    <div class="relegation-score">
                        <span class="score-label">Score</span>
                        <span class="score-value">${scoreLabel}</span>
                    </div>
                    <p class="match-note">Winner plays in Tier ${match.higher_tier} next season</p>
                </div>
            `;
            }).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Display Qualification Pool
 */
function displayQualificationPool(qualificationPool) {
    const container = document.getElementById('qualification-pool');
    const sectionContainer = document.getElementById('qualification-pool-container');
    
    if (!qualificationPool || qualificationPool.length === 0) {
        sectionContainer.style.display = 'none';
        return;
    }
    
    sectionContainer.style.display = 'block';
    
    let html = `
        <div class="qualification-pool-section">
            <h4>🎯 Beys Competing for Tier III Slots</h4>
            <p class="qualification-intro">These Beys will compete in the Qualification Tournament. Top 4 finishers earn Tier III placement for the next season.</p>
            <div class="qualification-grid">
                ${qualificationPool.map((entry, idx) => {
                    const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${addSoftHyphens(entry.bey)}</a>`;
                    return `
                    <div class="qualification-card">
                        <div class="qualification-rank">${idx + 1}</div>
                        <div class="qualification-bey">${beyLink}</div>
                        <div class="qualification-elo">ELO: ${Math.round(entry.elo)}</div>
                    </div>
                `;
                }).join('')}
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Display Season Cup bracket
 */
function displaySeasonCup(cupData) {
    const container = document.getElementById('season-cup-bracket');
    const sectionContainer = document.getElementById('season-cup-container');
    
    sectionContainer.style.display = 'block';
    
    const winner = cupData.cup_winner;
    
    let html = '';
    
    if (winner) {
        const winnerLink = `<a href="bey.html?name=${encodeURIComponent(winner)}" class="bey-link">${addSoftHyphens(winner)}</a>`;
        html += `
            <div class="cup-winner-banner">
                <h3>🏆 Season Cup Champion: ${winnerLink}</h3>
            </div>
        `;
    }
    
    html += `
        <div class="bracket-info">
            <p>Double-elimination tournament featuring the top performers from each tier.</p>
            <p><em>Full bracket visualization coming soon</em></p>
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Format ELO display with optional change indicator
 */
function formatEloWithChange(elo, eloChange) {
    const roundedElo = Math.round(elo);
    if (eloChange === null) {
        return `ELO: ${roundedElo}`;
    }
    const sign = eloChange >= 0 ? '+' : '';
    const changeClass = eloChange >= 0 ? 'positive' : 'negative';
    return `ELO: ${roundedElo} <span class="elo-change ${changeClass}">(${sign}${eloChange})</span>`;
}

/**
 * Display matchdays
 */
function displayMatchdays(matchdays) {
    const container = document.getElementById('matchdays');
    const sectionContainer = document.getElementById('matchdays-container');
    
    if (Object.keys(matchdays).length === 0) return;
    
    sectionContainer.style.display = 'block';
    
    // Sort matchdays numerically
    const sortedMatchdays = Object.keys(matchdays)
        .map(Number)
        .filter(n => !isNaN(n))
        .sort((a, b) => a - b);
    
    let html = '';
    
    sortedMatchdays.forEach(md => {
        const matches = matchdays[md];
        if (!matches || matches.length === 0) return;
        
        const sectionId = `matchday-${md}-content`;
        
        html += `
            <div class="matchday-section">
                <h4 class="collapsible-header" onclick="toggleSection('${sectionId}')" data-section-id="${sectionId}">
                    <span class="section-toggle-icon">▼</span>
                    <span>Matchday ${md}</span>
                </h4>
                <div id="${sectionId}" class="collapsible-content">
                    <div class="matches-grid">
                        ${matches.map(match => {
                        const beyALink = `<a href="bey.html?name=${encodeURIComponent(match.bey_a)}" class="bey-link">${addSoftHyphens(match.bey_a)}</a>`;
                        const beyBLink = `<a href="bey.html?name=${encodeURIComponent(match.bey_b)}" class="bey-link">${addSoftHyphens(match.bey_b)}</a>`;
                        
                        // Determine winner, loser, or tie
                        const isAWinner = match.score_a > match.score_b;
                        const isBWinner = match.score_b > match.score_a;
                        const isTie = match.score_a === match.score_b;
                        
                        // Get bey classes based on result
                        const beyAClass = isTie ? '' : (isAWinner ? 'winner' : 'loser');
                        const beyBClass = isTie ? '' : (isBWinner ? 'winner' : 'loser');
                        
                        // Get season and arena info
                        const seasonId = match.season_id || currentSeason?.season_id || 'S?';
                        const tierNum = match.tier || '?';
                        const arena = match.arena || 'Xtreme';
                        
                        // Get rounds data and ELO values
                        const matchData = roundsData[match.match_id];
                        const hasRounds = matchData && matchData.rounds && matchData.rounds.length > 0;
                        const isExpanded = expandedMatches.has(match.match_id);
                        
                        // Use ELO from roundsData if available, otherwise fallback to Xtreme ELO
                        // Skip match.elo_a/elo_b if they're default 1000 values
                        const eloA = matchData?.elo_a || 
                                    (match.elo_a && match.elo_a !== 1000 ? match.elo_a : null) || 
                                    xtremeEloData[match.bey_a] || 1000;
                        const eloB = matchData?.elo_b || 
                                    (match.elo_b && match.elo_b !== 1000 ? match.elo_b : null) || 
                                    xtremeEloData[match.bey_b] || 1000;
                        const postEloA = matchData?.post_elo_a;
                        const postEloB = matchData?.post_elo_b;
                        
                        // Calculate ELO changes if post-ELO is available
                        const eloChangeA = postEloA ? Math.round(postEloA - eloA) : null;
                        const eloChangeB = postEloB ? Math.round(postEloB - eloB) : null;
                        
                        // Determine if it's a blowout (3+ point difference) or close match (1 point)
                        const pointDiff = Math.abs(match.score_a - match.score_b);
                        const isBlowout = pointDiff >= 3 && !isTie;
                        const isClose = pointDiff === 1;
                        
                        // Generate rounds HTML if available
                        const roundsHtml = hasRounds ? createRoundsHtml(match, matchData.rounds) : '';
                        
                        return `
                        <div class="match-card" data-match-id="${match.match_id}">
                            <div class="match-card-header">
                                <div class="match-card-context">
                                    <span class="match-card-context-item">${seasonId}</span>
                                    <span class="match-card-context-separator">·</span>
                                    <span class="match-card-context-item tier-badge-subtle">Tier ${tierNum}</span>
                                    <span class="match-card-context-separator">·</span>
                                    <span class="match-card-context-item">MD ${md}</span>
                                    <span class="match-card-context-separator">·</span>
                                    <span class="match-card-context-item">${arena}</span>
                                </div>
                                <span class="match-date">${match.date || ''}</span>
                            </div>
                            <div class="match-card-body">
                                <div class="card-match">
                                    <div class="card-bey ${beyAClass}">
                                        <div class="bey-name">${beyALink}</div>
                                        <div class="bey-elo">${formatEloWithChange(eloA, eloChangeA)}</div>
                                        <div class="bey-score">${match.score_a}</div>
                                    </div>
                                    <div class="card-vs">VS</div>
                                    <div class="card-bey ${beyBClass}">
                                        <div class="bey-name">${beyBLink}</div>
                                        <div class="bey-elo">${formatEloWithChange(eloB, eloChangeB)}</div>
                                        <div class="bey-score">${match.score_b}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="match-card-footer">
                                <span class="match-id">${match.match_id || ''}</span>
                                <div class="match-tags">
                                    ${isTie ? '<span class="match-tag">Tie</span>' : ''}
                                    ${isBlowout ? '<span class="match-tag">Blowout</span>' : ''}
                                    ${isClose ? '<span class="match-tag">Close Match</span>' : ''}
                                </div>
                            </div>
                            ${hasRounds ? `
                            <div class="match-card-rounds">
                                <button class="rounds-toggle ${isExpanded ? 'expanded' : ''}" onclick="toggleMatchRounds('${match.match_id}', ${matchData.rounds.length})">
                                    <span class="toggle-icon">${isExpanded ? '▲' : '▼'}</span>
                                    <span class="toggle-text">${isExpanded ? 'Hide' : 'Show'} Round Details (${matchData.rounds.length})</span>
                                </button>
                                <div class="rounds-content ${isExpanded ? 'expanded' : ''}" id="rounds-${match.match_id}">
                                    ${roundsHtml}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    `;
                    }).join('')}
                </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function getFixtureKey(fixture) {
    if (fixture.fixture_id) return fixture.fixture_id;
    const seasonId = fixture.season_id || 'S?';
    const tier = fixture.tier || '?';
    const matchday = fixture.matchday ?? 'TBD';
    return `${seasonId}_T${tier}_${fixture.bey_a}_${fixture.bey_b}_${matchday}`;
}

function buildFixturesByMatchday(fixtures) {
    return fixtures.reduce((acc, fixture) => {
        const key = fixture.matchday != null ? String(fixture.matchday) : 'TBD';
        if (!acc[key]) {
            acc[key] = [];
        }
        acc[key].push(fixture);
        return acc;
    }, {});
}

function sortFixtureMatchdays(matchdays) {
    return matchdays.sort((a, b) => {
        const numA = parseInt(a, 10);
        const numB = parseInt(b, 10);
        const isNumA = !Number.isNaN(numA);
        const isNumB = !Number.isNaN(numB);
        if (isNumA && isNumB) return numA - numB;
        if (isNumA) return -1;
        if (isNumB) return 1;
        return a.localeCompare(b);
    });
}

function buildFixturesTable(fixtures) {
    if (!fixtures || fixtures.length === 0) {
        return '<p class="no-data">No upcoming fixtures for this matchday</p>';
    }

    return `
        <div class="fixtures-table-container">
            <table class="fixtures-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Tier</th>
                        <th colspan="3">Match</th>
                        <th>Sim Score</th>
                    </tr>
                </thead>
                <tbody>
                    ${fixtures.map(fixture => {
                        const fixtureKey = getFixtureKey(fixture);
                        const simResult = simulatedFixtureResults[fixtureKey];
                        const beyALink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_a)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_a)}</a>`;
                        const beyBLink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_b)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_b)}</a>`;
                        const scoreAValue = simResult ? simResult.score_a : '';
                        const scoreBValue = simResult ? simResult.score_b : '';
                        const simLabel = simResult ? '<span class="fixture-sim-tag is-active">Simulated</span>' : '';

                        return `
                        <tr class="fixture-row">
                            <td class="fixture-date">${fixture.date || 'TBD'}</td>
                            <td class="fixture-tier"><span class="tier-badge-compact">T${fixture.tier || '?'}</span></td>
                            <td class="fixture-bey-home">${beyALink}</td>
                            <td class="fixture-vs"><span class="vs-text">vs</span></td>
                            <td class="fixture-bey-away">${beyBLink}</td>
                            <td class="fixture-sim">
                                <div class="fixture-sim-controls" data-fixture-id="${fixtureKey}">
                                    <input type="number" min="0" inputmode="numeric" class="fixture-score-input" data-team="a" value="${scoreAValue}" oninput="handleFixtureScoreInput(this)">
                                    <span class="fixture-score-sep">-</span>
                                    <input type="number" min="0" inputmode="numeric" class="fixture-score-input" data-team="b" value="${scoreBValue}" oninput="handleFixtureScoreInput(this)">
                                </div>
                                <div class="fixture-sim-status" data-fixture-id="${fixtureKey}">
                                    <span class="fixture-badge">Scheduled</span>
                                    ${simLabel}
                                </div>
                            </td>
                        </tr>
                    `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function updateFixturesMatchday() {
    const tableSlot = document.getElementById('fixtures-table-slot');
    if (!tableSlot) return;

    const fixtures = fixturesByMatchday[selectedFixtureMatchday] || [];
    tableSlot.innerHTML = buildFixturesTable(fixtures);

    const title = document.getElementById('fixtures-matchday-title');
    if (title) {
        title.textContent = `Matchday ${selectedFixtureMatchday}`;
    }

    const prevBtn = document.getElementById('fixtures-prev-btn');
    const nextBtn = document.getElementById('fixtures-next-btn');
    if (prevBtn) {
        prevBtn.disabled = fixtureMatchdays.indexOf(selectedFixtureMatchday) <= 0;
    }
    if (nextBtn) {
        nextBtn.disabled = fixtureMatchdays.indexOf(selectedFixtureMatchday) >= fixtureMatchdays.length - 1;
    }

    updateFixtureResetState();
}

function changeFixtureMatchday(direction) {
    if (fixtureMatchdays.length === 0) return;
    const currentIndex = fixtureMatchdays.indexOf(selectedFixtureMatchday);
    if (currentIndex === -1) return;
    const nextIndex = currentIndex + direction;
    if (nextIndex < 0 || nextIndex >= fixtureMatchdays.length) return;
    selectedFixtureMatchday = fixtureMatchdays[nextIndex];
    updateFixturesMatchday();
}

function handleFixtureScoreInput(input) {
    const controls = input.closest('.fixture-sim-controls');
    if (!controls) return;
    const fixtureId = controls.dataset.fixtureId;
    const scoreAInput = controls.querySelector('input[data-team="a"]');
    const scoreBInput = controls.querySelector('input[data-team="b"]');
    updateSimulatedFixture(fixtureId, scoreAInput?.value, scoreBInput?.value);
}

function parseSimScore(value) {
    if (value === '' || value === null || value === undefined) {
        return null;
    }
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) {
        return null;
    }
    return parsed;
}

function updateSimulatedFixture(fixtureId, scoreAValue, scoreBValue) {
    const fixture = fixturesById[fixtureId];
    if (!fixture) return;

    const scoreA = parseSimScore(scoreAValue);
    const scoreB = parseSimScore(scoreBValue);
    const hasScores = Number.isInteger(scoreA) && Number.isInteger(scoreB);
    const hadSimulation = Boolean(simulatedFixtureResults[fixtureId]);

    if (!hasScores || (scoreA === 0 && scoreB === 0)) {
        delete simulatedFixtureResults[fixtureId];
    } else {
        const tierValue = fixture.tier != null ? Number(fixture.tier) : null;
        simulatedFixtureResults[fixtureId] = {
            score_a: scoreA,
            score_b: scoreB,
            tier: Number.isNaN(tierValue) ? fixture.tier : tierValue,
            bey_a: fixture.bey_a,
            bey_b: fixture.bey_b
        };
    }

    const hasSimulation = Boolean(simulatedFixtureResults[fixtureId]);
    updateFixtureSimStatus(fixtureId, hasSimulation);
    updateFixtureResetState();

    if (hadSimulation || hasSimulation) {
        refreshSimulatedTables();
    }
}

function resetFixtureSimulations() {
    simulatedFixtureResults = {};
    updateFixturesMatchday();
    refreshSimulatedTables();
}

function updateFixtureResetState() {
    const resetBtn = document.getElementById('fixtures-reset-btn');
    if (resetBtn) {
        resetBtn.disabled = Object.keys(simulatedFixtureResults).length === 0;
    }
}

function updateFixtureSimStatus(fixtureId, isSimulated) {
    const status = document.querySelector(`.fixture-sim-status[data-fixture-id="${fixtureId}"]`);
    if (!status) return;

    let simTag = status.querySelector('.fixture-sim-tag');
    if (isSimulated) {
        if (!simTag) {
            simTag = document.createElement('span');
            simTag.className = 'fixture-sim-tag is-active';
            simTag.textContent = 'Simulated';
            status.appendChild(simTag);
        }
    } else if (simTag) {
        simTag.remove();
    }
}

function calculateSeasonPoints(scoreA, scoreB) {
    const POINTS_WIN = 3;
    const POINTS_DOMINANT_WIN = 4;
    const DOMINANT_WIN_THRESHOLD = 4;

    if (scoreA === scoreB) {
        return [0, 0];
    }

    const winnerScore = Math.max(scoreA, scoreB);
    const loserScore = Math.min(scoreA, scoreB);
    const difference = winnerScore - loserScore;
    const isDominant = difference >= DOMINANT_WIN_THRESHOLD && loserScore === 0;
    const winnerPoints = isDominant ? POINTS_DOMINANT_WIN : POINTS_WIN;

    return scoreA > scoreB ? [winnerPoints, 0] : [0, winnerPoints];
}

function getBaseTableForTier(tier) {
    const hasSnapshots = tableSnapshotsData[tier] && Object.keys(tableSnapshotsData[tier]).length > 0;
    if (hasSnapshots && selectedTableSnapshots[tier]) {
        return tableSnapshotsData[tier][selectedTableSnapshots[tier]];
    }
    const leagueTables = currentSeason?.league_tables || {};
    return leagueTables[tier.toString()];
}

function getSimulatedFixturesForTier(tier) {
    return Object.values(simulatedFixtureResults).filter(result => Number(result.tier) === tier);
}

function buildSimulatedTable(baseTable, simulatedFixtures, hasSnapshots) {
    const table = baseTable.map(entry => ({ ...entry }));
    const entryMap = new Map(table.map(entry => [entry.bey, entry]));
    const basePositions = new Map(baseTable.map(entry => [entry.bey, entry.position]));

    table.forEach(entry => {
        entry.matches = Number(entry.matches || 0);
        entry.wins = Number(entry.wins || 0);
        entry.losses = Number(entry.losses || 0);
        entry.season_points = Number(entry.season_points || 0);
        entry.points_for = Number(entry.points_for || 0);
        entry.points_against = Number(entry.points_against || 0);
        entry.point_diff = Number(entry.point_diff || 0);
        entry.rw = Number(entry.rw || 0);
        entry.rl = Number(entry.rl || 0);
        entry.elo = Number(entry.elo || 0);
    });

    simulatedFixtures.forEach(fixture => {
        const entryA = entryMap.get(fixture.bey_a);
        const entryB = entryMap.get(fixture.bey_b);
        if (!entryA || !entryB) return;

        const scoreA = fixture.score_a;
        const scoreB = fixture.score_b;
        const [spA, spB] = calculateSeasonPoints(scoreA, scoreB);

        entryA.matches += 1;
        entryB.matches += 1;
        entryA.season_points += spA;
        entryB.season_points += spB;
        entryA.points_for += scoreA;
        entryA.points_against += scoreB;
        entryB.points_for += scoreB;
        entryB.points_against += scoreA;

        if (scoreA > scoreB) {
            entryA.wins += 1;
            entryB.losses += 1;
        } else if (scoreB > scoreA) {
            entryB.wins += 1;
            entryA.losses += 1;
        }

        entryA.rw = (entryA.rw ?? 0) + scoreA;
        entryA.rl = (entryA.rl ?? 0) + scoreB;
        entryB.rw = (entryB.rw ?? 0) + scoreB;
        entryB.rl = (entryB.rl ?? 0) + scoreA;
    });

    table.forEach(entry => {
        entry.point_diff = entry.points_for - entry.points_against;
        const totalRounds = (entry.rw ?? 0) + (entry.rl ?? 0);
        entry.ppr = totalRounds > 0 ? entry.points_for / totalRounds : 0;
        entry.ppw = (entry.rw ?? 0) > 0 ? entry.points_for / entry.rw : 0;
    });

    table.sort((a, b) => (
        b.season_points - a.season_points ||
        b.point_diff - a.point_diff ||
        b.points_for - a.points_for ||
        b.elo - a.elo
    ));

    table.forEach((entry, index) => {
        entry.position = index + 1;
        if (hasSnapshots) {
            const basePos = basePositions.get(entry.bey) ?? entry.position;
            entry.position_delta = basePos - entry.position;
        }
    });

    return table;
}

function getDisplayTableForTier(tier) {
    const baseTable = getBaseTableForTier(tier);
    if (!baseTable) return baseTable;

    const simulatedFixtures = getSimulatedFixturesForTier(tier);
    if (simulatedFixtures.length === 0) {
        return baseTable;
    }

    const hasSnapshots = tableSnapshotsData[tier] && Object.keys(tableSnapshotsData[tier]).length > 0;
    return buildSimulatedTable(baseTable, simulatedFixtures, hasSnapshots);
}

function refreshSimulatedTables() {
    const leagueTables = currentSeason?.league_tables || {};
    Object.keys(leagueTables).forEach(tierKey => {
        updateTierTable(parseInt(tierKey, 10));
    });
}

/**
 * Display upcoming fixtures
 */
function displayFixtures(fixturesData) {
    const container = document.getElementById('fixtures-section');
    if (!container) return;

    const upcomingMatches = fixturesData.upcoming_matches || [];
    const groupedByMatchday = fixturesData.fixtures_by_matchday || {};

    if (upcomingMatches.length === 0) {
        container.style.display = 'none';
        return;
    }

    fixturesByMatchday = Object.keys(groupedByMatchday).length > 0
        ? groupedByMatchday
        : buildFixturesByMatchday(upcomingMatches);
    fixtureMatchdays = sortFixtureMatchdays(Object.keys(fixturesByMatchday));
    selectedFixtureMatchday = fixtureMatchdays.includes(selectedFixtureMatchday)
        ? selectedFixtureMatchday
        : fixtureMatchdays[0];

    fixturesById = {};
    upcomingMatches.forEach(fixture => {
        fixturesById[getFixtureKey(fixture)] = fixture;
    });

    container.style.display = 'block';

    const navigatorHtml = fixtureMatchdays.length > 1 ? `
        <div class="matchday-navigator fixtures-matchday-navigator">
            <button class="matchday-nav-btn" id="fixtures-prev-btn" onclick="changeFixtureMatchday(-1)">
                <span class="nav-arrow">◀</span>
            </button>
            <h4 class="matchday-title" id="fixtures-matchday-title">Matchday ${selectedFixtureMatchday}</h4>
            <button class="matchday-nav-btn" id="fixtures-next-btn" onclick="changeFixtureMatchday(1)">
                <span class="nav-arrow">▶</span>
            </button>
        </div>
    ` : '';

    container.innerHTML = `
        <div class="fixtures-header">
            <h2 class="section-header">📅 Upcoming Fixtures</h2>
            <div class="fixtures-actions">
                <button class="fixtures-reset-btn" id="fixtures-reset-btn" onclick="resetFixtureSimulations()">Reset Simulations</button>
            </div>
        </div>
        <p class="fixtures-intro">Enter hypothetical scores to preview how standings would change.</p>
        ${navigatorHtml}
        <div id="fixtures-table-slot"></div>
        <p class="fixtures-sim-note">Simulated results update the tier tables above without saving any data.</p>
    `;

    updateFixturesMatchday();
}

/**
 * Show error message
 */
function showError(message) {
    document.getElementById('season-title').textContent = 'Error';
    document.getElementById('season-subtitle').textContent = message;
    document.getElementById('season-overview').innerHTML = `
        <div class="error-message">
            <p>${message}</p>
            <p><a href="seasons.html">← Back to Seasons Overview</a></p>
        </div>
    `;
}

/**
 * Create rounds HTML for match card (compact single-row format)
 */
function createRoundsHtml(match, rounds) {
    if (!rounds || rounds.length === 0) return '';

    let html = '<div class="rounds-compact">';
    let runningScoreA = 0;
    let runningScoreB = 0;

    rounds.forEach((round, index) => {
        const finishStyle = FINISH_TYPE_STYLES[round.finish_type] || FINISH_TYPE_STYLES.spin;
        const isWinnerA = round.winner === match.bey_a;
        const isWinnerB = round.winner === match.bey_b;

        if (isWinnerA) runningScoreA += round.points_awarded;
        else if (isWinnerB) runningScoreB += round.points_awarded;

        const winnerClass = isWinnerA ? 'rc-winner-a' : (isWinnerB ? 'rc-winner-b' : '');

        html += `
            <div class="rc-row ${winnerClass}">
                <div class="rc-top">
                    <span class="rc-num">R${round.round_number || index + 1}</span>
                    <span class="rc-badge" style="background:${finishStyle.bgColor};color:${finishStyle.color};">${finishStyle.icon} ${finishStyle.label}</span>
                    <span class="rc-pts">+${round.points_awarded}</span>
                    <span class="rc-score">${runningScoreA}–${runningScoreB}</span>
                </div>
                <div class="rc-bottom">
                    <span class="rc-winner">${round.winner || '—'}</span>
                </div>
            </div>
        `;
    });

    // Finish type summary
    const finishCounts = {};
    rounds.forEach(round => {
        const type = round.finish_type || 'spin';
        finishCounts[type] = (finishCounts[type] || 0) + 1;
    });

    html += '<div class="rc-summary">';
    Object.entries(finishCounts).forEach(([type, count]) => {
        const style = FINISH_TYPE_STYLES[type] || FINISH_TYPE_STYLES.spin;
        html += `<span class="finish-summary-badge" style="background:${style.bgColor};color:${style.color};">${style.icon} ${style.label}: ${count}</span>`;
    });
    html += '</div>';

    html += '</div>';
    return html;
}

/**
 * Toggle match rounds visibility
 */
function toggleMatchRounds(matchId, roundCount) {
    const content = document.getElementById(`rounds-${matchId}`);
    const toggle = document.querySelector(`[data-match-id="${matchId}"] .rounds-toggle`);
    const icon = toggle?.querySelector('.toggle-icon');
    const text = toggle?.querySelector('.toggle-text');
    
    if (expandedMatches.has(matchId)) {
        expandedMatches.delete(matchId);
        if (content) content.classList.remove('expanded');
        if (toggle) toggle.classList.remove('expanded');
        if (icon) icon.textContent = '▼';
        if (text) {
            text.textContent = `${roundCount} ${roundCount === 1 ? 'round' : 'rounds'}`;
        }
    } else {
        expandedMatches.add(matchId);
        
        // Generate rounds HTML on first expand if not already present
        if (content && content.innerHTML.trim() === '') {
            const matchData = roundsData[matchId];
            if (matchData && matchData.rounds) {
                const match = {
                    match_id: matchId,
                    bey_a: matchData.bey_a || '',
                    bey_b: matchData.bey_b || '',
                    score_a: matchData.score_a || 0,
                    score_b: matchData.score_b || 0,
                };
                content.innerHTML = createRoundsHtml(match, matchData.rounds);
            }
        }
        
        if (content) content.classList.add('expanded');
        if (toggle) toggle.classList.add('expanded');
        if (icon) icon.textContent = '▲';
        if (text) {
            text.textContent = `${roundCount} ${roundCount === 1 ? 'round' : 'rounds'}`;
        }
    }
}

/**
 * Toggle section visibility (for collapsible sections)
 */
function toggleSection(sectionId) {
    const content = document.getElementById(sectionId);
    const button = document.querySelector(`[data-section-id="${sectionId}"]`);
    const icon = button?.querySelector('.section-toggle-icon');
    
    if (collapsedSections.has(sectionId)) {
        // Expand
        collapsedSections.delete(sectionId);
        if (content) content.classList.remove('collapsed');
        if (button) button.classList.remove('collapsed');
        if (icon) icon.textContent = '▼';
    } else {
        // Collapse
        collapsedSections.add(sectionId);
        if (content) content.classList.add('collapsed');
        if (button) button.classList.add('collapsed');
        if (icon) icon.textContent = '▶';
    }
}

// Expose toggleSection to global scope for onclick handlers
window.toggleSection = toggleSection;

/**
 * Copy match ID to clipboard
 */
function copyMatchId(matchId) {
    const showCopiedFeedback = () => {
        const elements = document.querySelectorAll(`.match-id`);
        elements.forEach(el => {
            if (el.textContent === matchId) {
                el.classList.add('copied');
                setTimeout(() => el.classList.remove('copied'), 1000);
            }
        });
    };

    // Use modern clipboard API if available, fallback to legacy method
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(matchId).then(showCopiedFeedback).catch(err => {
            console.error('Failed to copy match ID:', err);
        });
    } else {
        // Fallback for older browsers or non-HTTPS contexts
        const textArea = document.createElement('textarea');
        textArea.value = matchId;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showCopiedFeedback();
        } catch (err) {
            console.error('Failed to copy match ID:', err);
        }
        document.body.removeChild(textArea);
    }
}

// Expose copyMatchId to global scope for onclick handlers
window.copyMatchId = copyMatchId;
