/**
 * seasons.js
 * Loads and displays seasonal league data on the seasons overview page.
 */

// Load season data on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSeasons();
});

/**
 * Load all seasons from season_data.json
 */
async function loadSeasons() {
    try {
        const response = await fetch('data/season_data.json');
        if (!response.ok) {
            throw new Error('Failed to load season data');
        }
        
        const data = await response.json();
        const seasons = data.seasons || {};
        
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

    for (const seasonId of Object.keys(seasons)) {
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

    // Sort: wins desc, then win rate desc, then alphabetical
    const rows = Object.values(totals).sort((a, b) => {
        if (b.wins !== a.wins) return b.wins - a.wins;
        const wrA = a.matches > 0 ? a.wins / a.matches : 0;
        const wrB = b.matches > 0 ? b.wins / b.matches : 0;
        if (wrB !== wrA) return wrB - wrA;
        return a.bey.localeCompare(b.bey);
    });

    const tbody = document.getElementById('alltime-tbody');
    if (!tbody) return;
    if (rows.length === 0) return;

    tbody.innerHTML = rows.map((entry, idx) => {
        const winRate = entry.matches > 0 ? ((entry.wins / entry.matches) * 100).toFixed(1) : '0.0';
        const pointDiff = entry.points_for - entry.points_against;
        const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${addSoftHyphens(entry.bey)}</a>`;
        return `
            <tr>
                <td>${idx + 1}</td>
                <td class="bey-name"><strong>${beyLink}</strong></td>
                <td>${entry.seasons.size}</td>
                <td>${entry.matches}</td>
                <td>${entry.wins}</td>
                <td>${entry.losses}</td>
                <td>${winRate}%</td>
                <td><strong>${entry.season_points}</strong></td>
                <td>${entry.points_for}</td>
                <td>${entry.points_against}</td>
                <td>${pointDiff > 0 ? '+' : ''}${pointDiff}</td>
            </tr>
        `;
    }).join('');

    const container = document.getElementById('alltime-standings-container');
    if (container) container.style.display = 'block';
}

/**
 * Create HTML for a season card
 */
function createSeasonCard(seasonId, season) {
    const champion = season.league_champion || 'TBD';
    const cupWinner = season.cup_winner || 'TBD';
    const totalMatches = season.statistics?.total_matches || 0;
    const startDate = season.start_date ? new Date(season.start_date).toLocaleDateString() : 'Unknown';
    const endDate = season.end_date ? new Date(season.end_date).toLocaleDateString() : 'Ongoing';
    
    // Get tier champions
    const tierChampions = [];
    const leagueTables = season.league_tables || {};
    for (let tier = 1; tier <= 3; tier++) {
        const table = leagueTables[tier.toString()];
        if (table && table.length > 0) {
            tierChampions.push({
                tier: tier,
                champion: table[0].bey
            });
        }
    }
    
    return `
        <div class="season-card">
            <div class="season-header">
                <h3>${seasonId}</h3>
                <span class="season-dates">${startDate} - ${endDate}</span>
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
