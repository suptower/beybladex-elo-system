/**
 * seasons.js
 * Loads and displays seasonal league data on the seasons overview page.
 */

// All-time standings state
let allTimeRows = [];
let allTimeSortKey = 'season_points';
let allTimeSortAsc = false;

// Global leaderboard ELO map (bey name → ELO)
let globalEloData = {};

// Load season data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSeasons();
});

/**
 * Load global ELO data from the leaderboard CSV.
 */
async function loadGlobalEloData() {
    try {
        const response = await fetch(DATA_PATHS.LEADERBOARD_XTREME_CSV);
        if (!response.ok) throw new Error('Failed to load leaderboard');
        const csvText = await response.text();
        const lines = csvText.trim().split('\n');
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            if (values.length >= 3) {
                const name = values[1];
                const elo = parseFloat(values[2]);
                if (name && !isNaN(elo)) globalEloData[name] = elo;
            }
        }
    } catch (error) {
        console.error('Error loading global ELO data:', error);
        globalEloData = {};
    }
}

/**
 * Load all seasons from season_data.json
 */
async function loadSeasons() {
    try {
        const [seasonResponse, seasonsMetaResponse] = await Promise.all([
            fetch(DATA_PATHS.SEASON_DATA_JSON),
            fetch(DATA_PATHS.SEASONS_JSON),
            loadGlobalEloData()
        ]);
        if (!seasonResponse.ok) {
            throw new Error('Failed to load season data');
        }
        
        const data = await seasonResponse.json();
        const seasons = data.seasons || {};

        // seasons.json is the authoritative source for status/start_date/end_date.
        // Override those fields so the UI stays accurate even when season_data.json
        // was generated before a status change (e.g. upcoming → active).
        if (seasonsMetaResponse.ok) {
            const seasonsMeta = await seasonsMetaResponse.json();
            for (const [seasonId, season] of Object.entries(seasons)) {
                const meta = seasonsMeta[seasonId];
                if (meta) {
                    season.status = meta.status;
                    season.start_date = meta.start_date;
                    if (meta.end_date !== undefined) season.end_date = meta.end_date;
                }
            }
        }

        displaySeasons(seasons);
    } catch (error) {
        console.error('Error loading seasons:', error);
        displayNoSeasons();
    }
}

/**
 * Display seasons in a list
 */
function displaySeasons(seasons) {
    const container = document.getElementById('seasons-list');
    
    if (Object.keys(seasons).length === 0) {
        displayNoSeasons();
        return;
    }
    
    // Sort seasons by ID (most recent first)
    const seasonIds = Object.keys(seasons).sort().reverse();
    
    container.innerHTML = seasonIds.map(seasonId => {
        const season = seasons[seasonId];
        return createSeasonCard(seasonId, season);
    }).join('');

    buildAllTimeStandings(seasons);
}

/**
 * Add soft hyphens before capital letters to allow line breaks in long Bey names
 */
function addSoftHyphens(name) {
    return name.replace(/([a-z])([A-Z])/g, '$1&shy;$2');
}

/**
 * Build and display the all-time standings table by aggregating stats
 * from every season and every tier.
 */
function buildAllTimeStandings(seasons) {
    const totals = {};

    for (const seasonId of Object.keys(seasons).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))) {
        const leagueTables = seasons[seasonId].league_tables || {};
        for (const tier of Object.keys(leagueTables)) {
            const table = leagueTables[tier] || [];
            for (const entry of table) {
                const bey = entry.bey;
                if (!totals[bey]) {
                    totals[bey] = { bey, seasons: new Set(), matches: 0, wins: 0, losses: 0, season_points: 0, points_for: 0, points_against: 0 };
                }
                totals[bey].seasons.add(seasonId);
                totals[bey].matches += entry.matches || 0;
                totals[bey].wins += entry.wins || 0;
                totals[bey].losses += entry.losses || 0;
                totals[bey].season_points += entry.season_points || 0;
                totals[bey].points_for += entry.points_for || 0;
                totals[bey].points_against += entry.points_against || 0;
            }
        }
    }

    // Convert to flat array, add derived fields (use global leaderboard ELO)
    const flat = Object.values(totals).map(entry => ({
        ...entry,
        seasons_count: entry.seasons.size,
        win_rate: entry.matches > 0 ? entry.wins / entry.matches : 0,
        point_diff: entry.points_for - entry.points_against,
        elo: globalEloData[entry.bey] !== undefined ? globalEloData[entry.bey] : 0
    }));

    // Assign fixed rank based on default sort (Pts desc)
    const defaultSorted = [...flat].sort((a, b) => b.season_points - a.season_points);
    defaultSorted.forEach((entry, idx) => { entry.allTimeRank = idx + 1; });

    allTimeRows = flat;

    if (allTimeRows.length === 0) return;

    // Wire up header click handlers
    const thead = document.querySelector('#alltime-table thead tr');
    if (thead) {
        thead.querySelectorAll('th[data-sort-key]').forEach(th => {
            th.addEventListener('click', () => sortAlltimeTable(th.dataset.sortKey));
        });
    }

    // Initial render with default sort (Pts desc)
    renderAlltimeRows();

    const container = document.getElementById('alltime-standings-container');
    if (container) container.style.display = 'block';
}

/**
 * Sort the all-time table by the given key, toggling direction if already sorted by that key.
 */
function sortAlltimeTable(key) {
    if (allTimeSortKey === key) {
        allTimeSortAsc = !allTimeSortAsc;
    } else {
        allTimeSortKey = key;
        // Numeric columns default desc; Bey name defaults asc
        allTimeSortAsc = (key === 'bey');
    }
    renderAlltimeRows();
}

/**
 * Toggle the all-time standings section open/closed.
 */
function toggleAlltimeSection() {
    const content = document.getElementById('alltime-content');
    const header = document.querySelector('[data-section-id="alltime-content"]');
    const icon = header && header.querySelector('.section-toggle-icon');

    const isCollapsed = content && content.classList.contains('collapsed');
    if (isCollapsed) {
        if (content) content.classList.remove('collapsed');
        if (header) header.classList.remove('collapsed');
        if (icon) icon.textContent = '▼';
    } else {
        if (content) content.classList.add('collapsed');
        if (header) header.classList.add('collapsed');
        if (icon) icon.textContent = '▶';
    }
}

/**
 * Re-render the all-time tbody based on current sort state.
 */
function renderAlltimeRows() {
    const sorted = [...allTimeRows].sort((a, b) => {
        const key = allTimeSortKey;
        let valA = key === 'bey' ? a.bey : (key === 'seasons' ? a.seasons_count : a[key]);
        let valB = key === 'bey' ? b.bey : (key === 'seasons' ? b.seasons_count : b[key]);

        if (typeof valA === 'string') {
            return allTimeSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return allTimeSortAsc ? valA - valB : valB - valA;
    });

    const tbody = document.getElementById('alltime-tbody');
    if (!tbody) return;

    tbody.innerHTML = sorted.map((entry) => {
        const winRate = (entry.win_rate * 100).toFixed(1);
        const pd = entry.point_diff;
        const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${addSoftHyphens(entry.bey)}</a>`;
        return `
            <tr>
                <td>${entry.allTimeRank}</td>
                <td class="bey-name"><strong>${beyLink}</strong></td>
                <td>${entry.seasons_count}</td>
                <td>${entry.matches}</td>
                <td>${entry.wins}</td>
                <td>${entry.losses}</td>
                <td>${winRate}%</td>
                <td><strong>${entry.season_points}</strong></td>
                <td>${entry.points_for}</td>
                <td>${entry.points_against}</td>
                <td>${pd > 0 ? '+' : ''}${pd}</td>
                <td>${Math.round(entry.elo)}</td>
            </tr>
        `;
    }).join('');

    // Update header indicators
    document.querySelectorAll('#alltime-table th.sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.sortKey === allTimeSortKey) {
            th.classList.add(allTimeSortAsc ? 'sorted-asc' : 'sorted-desc');
        }
    });
}

/**
 * Create HTML for a season card
 */
function createSeasonCard(seasonId, season) {
    const isUpcoming = season.status === 'upcoming';
    const champion = isUpcoming ? 'TBD' : (season.league_champion || 'TBD');
    const cupWinner = isUpcoming ? 'TBD' : (season.cup_winner || 'TBD');
    const totalMatches = season.statistics?.total_matches || 0;
    const startDate = season.start_date ? new Date(season.start_date).toLocaleDateString() : (isUpcoming ? 'Upcoming' : 'Unknown');
    const endDate = season.end_date ? new Date(season.end_date).toLocaleDateString() : (isUpcoming ? 'TBD' : 'Ongoing');
    const dateRange = isUpcoming ? startDate : `${startDate} - ${endDate}`;
    
    // Determine status badge
    let statusBadge = '';
    if (season.status === 'upcoming') {
        statusBadge = '<span class="season-status-badge upcoming">Upcoming</span>';
    } else if (!season.end_date) {
        statusBadge = '<span class="season-status-badge active">Active</span>';
    }

    // Get tier champions (up to 4 tiers)
    const tierChampions = [];
    const leagueTables = season.league_tables || {};
    for (let tier = 1; tier <= 4; tier++) {
        const table = leagueTables[tier.toString()];
        if (table && table.length > 0) {
            tierChampions.push({
                tier: tier,
                champion: isUpcoming ? 'TBD' : table[0].bey
            });
        }
    }
    
    return `
        <div class="season-card${isUpcoming ? ' upcoming-season' : ''}">
            <div class="season-header">
                <h3>${seasonId} ${statusBadge}</h3>
                <span class="season-dates">${dateRange}</span>
            </div>
            
            <div class="season-highlights">
                <div class="highlight">
                    <span class="highlight-label">🏆 League Champion</span>
                    <span class="highlight-value">${champion}</span>
                </div>
                <div class="highlight">
                    <span class="highlight-label">🏅 Cup Winner</span>
                    <span class="highlight-value">${cupWinner}</span>
                </div>
                <div class="highlight">
                    <span class="highlight-label">📊 Total Matches</span>
                    <span class="highlight-value">${totalMatches}</span>
                </div>
            </div>
            
            ${tierChampions.length > 0 ? `
                <div class="tier-champions">
                    <h4>Tier Champions</h4>
                    <div class="tier-champions-grid">
                        ${tierChampions.map(tc => `
                            <div class="tier-champion">
                                <span class="tier-badge">Tier ${tc.tier}</span>
                                <span class="champion-name">${tc.champion}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="season-actions">
                <a href="season.html?id=${seasonId}" class="season-details-btn">View Season Details →</a>
            </div>
        </div>
    `;
}

/**
 * Display message when no seasons are available
 */
function displayNoSeasons() {
    const container = document.getElementById('seasons-list');
    container.innerHTML = `
        <div class="no-data-message">
            <p>No seasons have been played yet.</p>
            <p>Check back once the first season begins!</p>
        </div>
    `;
}
