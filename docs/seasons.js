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
    for (let tier = 1; tier <= 4; tier++) {
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
                <a href="season.html?id=${seasonId}" class="btn btn-primary">View Season Details</a>
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
