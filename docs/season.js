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
        const response = await fetch('data/matches_with_rounds.json');
        const data = await response.json();
        
        // Create a mapping of match_id to rounds and ELO values
        if (data.matches) {
            data.matches.forEach(match => {
                if (match.rounds && match.rounds.length > 0) {
                    roundsData[match.match_id] = {
                        rounds: match.rounds,
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
        const response = await fetch('data/leaderboard_xtreme.csv');
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
 * Load specific season data
 */
async function loadSeason(seasonId) {
    try {
        const response = await fetch('data/season_data.json');
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
 * Display season overview and all components
 */
function displaySeason(seasonId, season) {
    // Update title
    document.getElementById('season-title').textContent = seasonId;
    document.getElementById('season-subtitle').textContent = 
        `${season.start_date ? new Date(season.start_date).toLocaleDateString() : ''} - ${season.end_date ? new Date(season.end_date).toLocaleDateString() : 'Ongoing'}`;
    
    // Initialize matchday selections
    initializeSelectedMatchdays(season.matchdays || {});
    
    // Display overview
    displayOverview(season);
    
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
function displayOverview(season) {
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
        
        const tierNames = ['I', 'II', 'III', 'IV'];
        const sectionId = `tier-${tier}-content`;
        
        // Get all matchdays for this tier
        const tierMatchdays = getTierMatchdays(matchdays, tier);
        const currentMatchday = selectedMatchdays[tier] || tierMatchdays[0] || 1;
        
        html += `
            <div class="tier-section-new">
                <h3 class="collapsible-header" onclick="toggleSection('${sectionId}')" data-section-id="${sectionId}">
                    <span class="section-toggle-icon">▼</span>
                    <span>🏆 Tier ${tierNames[tier-1]}</span>
                </h3>
                <div id="${sectionId}" class="collapsible-content">
                    <div class="tier-content-grid">
                        <div class="tier-table-column">
                            <h4 class="tier-subsection-header">📊 Table</h4>
                            <div class="table-responsive">
                                <table class="league-table">
                                    <thead>
                                        <tr>
                                            <th>Pos</th>
                                            <th>Bey</th>
                                            <th>M</th>
                                            <th>W</th>
                                            <th>L</th>
                                            <th>SP</th>
                                            <th>RPW</th>
                                            <th>RPL</th>
                                            <th>RPD</th>
                                            <th>ELO</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${table.map((entry, idx) => createTableRow(entry, idx, tier)).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="table-legend">
                                <span><strong>M</strong>=Matches, <strong>W</strong>=Wins, <strong>L</strong>=Losses, <strong>SP</strong>=Season Points</span>
                                <span><strong>RPW</strong>=Round Points Won, <strong>RPL</strong>=Round Points Lost, <strong>RPD</strong>=Round Points Difference</span>
                            </div>
                            ${getPositionLegend(tier)}
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
                <div class="season-compact-bey ${beyAClass}">
                    <span class="compact-bey-name">${beyALink}</span>
                    <span class="compact-bey-elo-change">${deltaBadgeA}</span>
                    <span class="compact-bey-score">${match.score_a}</span>
                </div>
                <span class="compact-vs">vs.</span>
                <div class="season-compact-bey ${beyBClass}">
                    <span class="compact-bey-score">${match.score_b}</span>
                    <span class="compact-bey-elo-change">${deltaBadgeB}</span>
                    <span class="compact-bey-name">${beyBLink}</span>
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
 * Get position legend for tier
 */
function getPositionLegend(tier) {
    let html = '<div class="position-legend">';
    
    // Tier II and III show promotion indicators
    if (tier > 1) {
        html += `
            <div class="position-legend-item">
                <div class="position-legend-indicator promotion"></div>
                <span>Promotion (Top 2)</span>
            </div>
            <div class="position-legend-item">
                <div class="position-legend-indicator playoff"></div>
                <span>Promotion Playoff (3rd)</span>
            </div>
        `;
    }
    
    // Tier I and II show relegation indicators
    if (tier < 3) {
        html += `
            <div class="position-legend-item">
                <div class="position-legend-indicator qualification"></div>
                <span>Relegation Match (8th)</span>
            </div>
            <div class="position-legend-item">
                <div class="position-legend-indicator relegation"></div>
                <span>Relegation (Bottom 2)</span>
            </div>
        `;
    }
    
    // Tier III shows qualification zone
    if (tier === 3) {
        html += `
            <div class="position-legend-item">
                <div class="position-legend-indicator qualification"></div>
                <span>Qualification Tournament (7-10)</span>
            </div>
        `;
    }
    
    html += '</div>';
    return html;
}

/**
 * Create table row with position indicators
 */
function createTableRow(entry, idx, tier) {
    let positionClass = '';
    let positionIndicator = '';
    
    // Promotion zone (top 2, except Tier I)
    if (tier > 1 && idx < 2) {
        positionClass = 'promotion-zone';
        positionIndicator = ' ↑';
    }
    // Promotion playoff zone (3rd place in Tiers II & III - faces 8th from tier above)
    else if (tier > 1 && idx === 2) {
        positionClass = 'playoff-zone';
        positionIndicator = ' ↕';
    }
    // Relegation match zone (8th place in Tiers I & II - faces 3rd from tier below)
    else if (tier < 3 && idx === 7) {
        positionClass = 'qualification-zone';
        positionIndicator = ' ↕';
    }
    // Relegation zone (bottom 2 for Tiers I-II)
    else if (tier < 3 && idx >= 8) {
        positionClass = 'relegation-zone';
        positionIndicator = ' ↓';
    }
    // Qualification zone (Tier III positions 7-10 enter qualification)
    else if (tier === 3 && idx >= 6) {
        positionClass = 'qualification-zone';
        positionIndicator = ' Q';
    }
    
    // Create Bey link with soft hyphens
    const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${addSoftHyphens(entry.bey)}</a>`;
    
    // Use Xtreme ELO if available, otherwise fall back to entry.elo
    const displayElo = xtremeEloData[entry.bey] !== undefined ? xtremeEloData[entry.bey] : entry.elo;
    
    return `
        <tr class="${positionClass}">
            <td>${entry.position}${positionIndicator}</td>
            <td class="bey-name"><strong>${beyLink}</strong></td>
            <td>${entry.matches}</td>
            <td>${entry.wins}</td>
            <td>${entry.losses}</td>
            <td><strong>${entry.season_points}</strong></td>
            <td>${entry.points_for}</td>
            <td>${entry.points_against}</td>
            <td>${entry.point_diff > 0 ? '+' : ''}${entry.point_diff}</td>
            <td>${Math.round(displayElo)}</td>
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

/**
 * Display upcoming fixtures
 */
function displayFixtures(fixturesData) {
    const container = document.getElementById('fixtures-section');
    if (!container) return;
    
    const upcomingMatches = fixturesData.upcoming_matches || [];
    const fixturesByMatchday = fixturesData.fixtures_by_matchday || {};
    
    if (upcomingMatches.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    
    let html = `
        <h2 class="section-header">📅 Upcoming Fixtures</h2>
        <p class="fixtures-intro">Scheduled matches that haven't been played yet</p>
    `;
    
    // Group by matchday if available
    if (Object.keys(fixturesByMatchday).length > 0) {
        const sortedMatchdays = Object.keys(fixturesByMatchday).sort((a, b) => parseInt(a) - parseInt(b));
        
        sortedMatchdays.forEach(md => {
            const fixtures = fixturesByMatchday[md];
            if (!fixtures || fixtures.length === 0) return;
            
            html += `
                <div class="fixtures-matchday">
                    <h4 class="fixtures-matchday-header">📆 Matchday ${md}</h4>
                    <div class="fixtures-table-container">
                        <table class="fixtures-table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Tier</th>
                                    <th colspan="3">Match</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${fixtures.map(fixture => {
                                    const beyALink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_a)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_a)}</a>`;
                                    const beyBLink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_b)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_b)}</a>`;
                                    
                                    return `
                                    <tr class="fixture-row">
                                        <td class="fixture-date">${fixture.date || 'TBD'}</td>
                                        <td class="fixture-tier"><span class="tier-badge-compact">T${fixture.tier || '?'}</span></td>
                                        <td class="fixture-bey-home">${beyALink}</td>
                                        <td class="fixture-vs"><span class="vs-text">vs</span></td>
                                        <td class="fixture-bey-away">${beyBLink}</td>
                                        <td class="fixture-status"><span class="fixture-badge">Scheduled</span></td>
                                    </tr>
                                `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        });
    } else {
        // Show all fixtures without matchday grouping
        html += `
            <div class="fixtures-table-container">
                <table class="fixtures-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Tier</th>
                            <th colspan="3">Match</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${upcomingMatches.map(fixture => {
                            const beyALink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_a)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_a)}</a>`;
                            const beyBLink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_b)}" class="bey-link fixture-bey">${addSoftHyphens(fixture.bey_b)}</a>`;
                            
                            return `
                            <tr class="fixture-row">
                                <td class="fixture-date">${fixture.date || 'TBD'}</td>
                                <td class="fixture-tier"><span class="tier-badge-compact">T${fixture.tier || '?'}</span></td>
                                <td class="fixture-bey-home">${beyALink}</td>
                                <td class="fixture-vs"><span class="vs-text">vs</span></td>
                                <td class="fixture-bey-away">${beyBLink}</td>
                                <td class="fixture-status"><span class="fixture-badge">Scheduled</span></td>
                            </tr>
                        `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    
    container.innerHTML = html;
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
 * Create rounds HTML for match card
 */
function createRoundsHtml(match, rounds) {
    if (!rounds || rounds.length === 0) return '';
    
    let html = '<div class="rounds-list">';
    let runningScoreA = 0;
    let runningScoreB = 0;
    
    rounds.forEach((round, index) => {
        const finishStyle = FINISH_TYPE_STYLES[round.finish_type] || FINISH_TYPE_STYLES.spin;
        
        // Update running score
        if (round.winner === match.bey_a) {
            runningScoreA += round.points_awarded;
        } else if (round.winner === match.bey_b) {
            runningScoreB += round.points_awarded;
        }
        
        html += `
            <div class="round-item">
                <div class="round-header">
                    <span class="round-number">R${round.round_number || index + 1}</span>
                    <span class="finish-badge" style="background: ${finishStyle.bgColor}; color: ${finishStyle.color};">
                        <span class="finish-icon">${finishStyle.icon}</span>
                        <span class="finish-label">${finishStyle.label}</span>
                    </span>
                    <span class="round-points">+${round.points_awarded}</span>
                </div>
                <div class="round-details">
                    <span class="round-winner">${round.winner}</span>
                    <span class="round-score">${runningScoreA} - ${runningScoreB}</span>
                </div>
            </div>
        `;
    });
    
    // Add finish type summary
    const finishCounts = {};
    rounds.forEach(round => {
        const type = round.finish_type || 'spin';
        finishCounts[type] = (finishCounts[type] || 0) + 1;
    });
    
    html += '<div class="rounds-summary">';
    Object.entries(finishCounts).forEach(([type, count]) => {
        const style = FINISH_TYPE_STYLES[type] || FINISH_TYPE_STYLES.spin;
        html += `
            <span class="finish-summary-badge" style="background: ${style.bgColor}; color: ${style.color};">
                ${style.icon} ${style.label}: ${count}
            </span>
        `;
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
                // Find the match data to pass to createRoundsHtml
                const matchCard = document.querySelector(`[data-match-id="${matchId}"]`);
                if (matchCard) {
                    // Get match info from DOM or reconstruct it
                    const match = {
                        match_id: matchId,
                        bey_a: matchCard.querySelector('.card-bey:first-child .bey-link')?.textContent.replace(/\u00AD/g, '') || '',
                        bey_b: matchCard.querySelector('.card-bey:last-child .bey-link')?.textContent.replace(/\u00AD/g, '') || '',
                        score_a: parseInt(matchCard.querySelector('.card-bey:first-child .bey-score')?.textContent || '0'),
                        score_b: parseInt(matchCard.querySelector('.card-bey:last-child .bey-score')?.textContent || '0')
                    };
                    content.innerHTML = createRoundsHtml(match, matchData.rounds);
                }
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
