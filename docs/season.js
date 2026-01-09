/**
 * season.js
 * Loads and displays individual season details including tier tables,
 * promotion/relegation, matchdays, and Season Cup bracket.
 */

let currentSeason = null;

// Load season data on page load
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const seasonId = urlParams.get('id');
    
    if (seasonId) {
        loadSeason(seasonId);
    } else {
        showError('No season ID provided');
    }
});

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
 * Display season overview and all components
 */
function displaySeason(seasonId, season) {
    // Update title
    document.getElementById('season-title').textContent = seasonId;
    document.getElementById('season-subtitle').textContent = 
        `${season.start_date ? new Date(season.start_date).toLocaleDateString() : ''} - ${season.end_date ? new Date(season.end_date).toLocaleDateString() : 'Ongoing'}`;
    
    // Display overview
    displayOverview(season);
    
    // Display tier tables
    displayTierTables(season.league_tables || {});
    
    // Display promotion/relegation
    if (season.promotion_relegation) {
        displayPromotionRelegation(season.promotion_relegation);
    }
    
    // Display Season Cup
    if (season.season_cup) {
        displaySeasonCup(season.season_cup);
    }
    
    // Display matchdays
    if (season.matchdays) {
        displayMatchdays(season.matchdays);
    }
}

/**
 * Display season overview stats
 */
function displayOverview(season) {
    const container = document.getElementById('season-overview');
    
    const stats = season.statistics || {};
    const champion = season.league_champion || 'TBD';
    const cupWinner = season.cup_winner || 'TBD';
    
    container.innerHTML = `
        <div class="season-overview-grid">
            <div class="overview-card champion-card">
                <h3>🏆 League Champion</h3>
                <p class="champion-name">${champion}</p>
                <p class="champion-note">Most consistent performer of the season</p>
            </div>
            <div class="overview-card cup-card">
                <h3>🏅 Season Cup Winner</h3>
                <p class="champion-name">${cupWinner}</p>
                <p class="champion-note">Post-season tournament champion</p>
            </div>
            <div class="overview-card stats-card">
                <h3>📊 Season Statistics</h3>
                <div class="stat-row">
                    <span>Total Matches:</span>
                    <span>${stats.total_matches || 0}</span>
                </div>
                <div class="stat-row">
                    <span>Total Points Scored:</span>
                    <span>${stats.total_goals || 0}</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Display tier tables
 */
function displayTierTables(leagueTables) {
    const container = document.getElementById('tier-tables');
    
    if (Object.keys(leagueTables).length === 0) {
        container.innerHTML = '<p class="no-data">No league tables available</p>';
        return;
    }
    
    let html = '';
    
    // Display each tier
    for (let tier = 1; tier <= 4; tier++) {
        const table = leagueTables[tier.toString()];
        if (!table || table.length === 0) continue;
        
        html += `
            <div class="tier-section">
                <h3>Tier ${tier}</h3>
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
                                <th>PF</th>
                                <th>PA</th>
                                <th>PD</th>
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
                    <span><strong>PF</strong>=Points For, <strong>PA</strong>=Points Against, <strong>PD</strong>=Point Difference</span>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
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
    // Relegation match zone (8th place, except Tier IV)
    else if (tier < 4 && idx === 7) {
        positionClass = 'playoff-zone';
        positionIndicator = ' ↕';
    }
    // Relegation zone (bottom 2, except Tier IV)
    else if (tier < 4 && idx >= 8) {
        positionClass = 'relegation-zone';
        positionIndicator = ' ↓';
    }
    
    return `
        <tr class="${positionClass}">
            <td>${entry.position}${positionIndicator}</td>
            <td class="bey-name"><strong>${entry.bey}</strong></td>
            <td>${entry.matches}</td>
            <td>${entry.wins}</td>
            <td>${entry.losses}</td>
            <td><strong>${entry.season_points}</strong></td>
            <td>${entry.points_for}</td>
            <td>${entry.points_against}</td>
            <td>${entry.point_diff > 0 ? '+' : ''}${entry.point_diff}</td>
            <td>${Math.round(entry.elo)}</td>
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
                    ${data.automatic_promotion.map(p => 
                        `<li><strong>${p.bey}</strong> (Tier ${p.from_tier} → Tier ${p.to_tier})</li>`
                    ).join('')}
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
                    ${data.automatic_relegation.map(r => 
                        `<li><strong>${r.bey}</strong> (Tier ${r.from_tier} → Tier ${r.to_tier})</li>`
                    ).join('')}
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
            ${matches.map(match => `
                <div class="relegation-match-card">
                    <div class="match-header">
                        <span class="tier-badge">Tier ${match.higher_tier} ↔ Tier ${match.lower_tier}</span>
                    </div>
                    <div class="match-participants">
                        <div class="participant">
                            <span class="position-badge">${match.higher_position}th</span>
                            <span class="bey-name">${match.higher_bey}</span>
                            <span class="tier-label">Tier ${match.higher_tier}</span>
                        </div>
                        <div class="vs">VS</div>
                        <div class="participant">
                            <span class="position-badge">${match.lower_position}rd</span>
                            <span class="bey-name">${match.lower_bey}</span>
                            <span class="tier-label">Tier ${match.lower_tier}</span>
                        </div>
                    </div>
                    <p class="match-note">Winner plays in Tier ${match.higher_tier} next season</p>
                </div>
            `).join('')}
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
        html += `
            <div class="cup-winner-banner">
                <h3>🏆 Season Cup Champion: ${winner}</h3>
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
        
        html += `
            <div class="matchday-section">
                <h4>Matchday ${md}</h4>
                <div class="matches-grid">
                    ${matches.map(match => `
                        <div class="match-card">
                            <div class="match-info">
                                <span class="tier-badge">Tier ${match.tier || '?'}</span>
                                <span class="match-date">${match.date || ''}</span>
                            </div>
                            <div class="match-result">
                                <span class="bey ${match.score_a > match.score_b ? 'winner' : ''}">${match.bey_a}</span>
                                <span class="score">${match.score_a} - ${match.score_b}</span>
                                <span class="bey ${match.score_b > match.score_a ? 'winner' : ''}">${match.bey_b}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });
    
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
