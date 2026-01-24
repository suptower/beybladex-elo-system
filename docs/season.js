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
    
    // Create champion link if not TBD
    const championHtml = champion !== 'TBD' 
        ? `<a href="bey.html?name=${encodeURIComponent(champion)}" class="bey-link">${champion}</a>`
        : champion;
    const cupWinnerHtml = cupWinner !== 'TBD'
        ? `<a href="bey.html?name=${encodeURIComponent(cupWinner)}" class="bey-link">${cupWinner}</a>`
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
        
        const tierNames = ['I', 'II', 'III', 'IV'];
        
        html += `
            <div class="tier-section">
                <h3>🏆 Tier ${tierNames[tier-1]}</h3>
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
                ${getPositionLegend(tier)}
            </div>
        `;
    }
    
    container.innerHTML = html;
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
    
    // Create Bey link
    const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${entry.bey}</a>`;
    
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
                    ${data.automatic_promotion.map(p => {
                        const beyLink = `<a href="bey.html?name=${encodeURIComponent(p.bey)}" class="bey-link">${p.bey}</a>`;
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
                        const beyLink = `<a href="bey.html?name=${encodeURIComponent(r.bey)}" class="bey-link">${r.bey}</a>`;
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
                const higherBeyLink = `<a href="bey.html?name=${encodeURIComponent(match.higher_bey)}" class="bey-link">${match.higher_bey}</a>`;
                const lowerBeyLink = `<a href="bey.html?name=${encodeURIComponent(match.lower_bey)}" class="bey-link">${match.lower_bey}</a>`;
                
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
    const container = document.getElementById('qualification-pool-content');
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
                    const beyLink = `<a href="bey.html?name=${encodeURIComponent(entry.bey)}" class="bey-link">${entry.bey}</a>`;
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
        const winnerLink = `<a href="bey.html?name=${encodeURIComponent(winner)}" class="bey-link">${winner}</a>`;
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
                    ${matches.map(match => {
                        const beyALink = `<a href="bey.html?name=${encodeURIComponent(match.bey_a)}" class="bey-link">${match.bey_a}</a>`;
                        const beyBLink = `<a href="bey.html?name=${encodeURIComponent(match.bey_b)}" class="bey-link">${match.bey_b}</a>`;
                        
                        return `
                        <div class="match-card">
                            <div class="match-info">
                                <span class="tier-badge">Tier ${match.tier || '?'}</span>
                                <span class="match-date">${match.date || ''}</span>
                            </div>
                            <div class="match-result">
                                <span class="bey ${match.score_a > match.score_b ? 'winner' : ''}">${beyALink}</span>
                                <span class="score">${match.score_a} - ${match.score_b}</span>
                                <span class="bey ${match.score_b > match.score_a ? 'winner' : ''}">${beyBLink}</span>
                            </div>
                        </div>
                    `;
                    }).join('')}
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
                                    const beyALink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_a)}" class="bey-link fixture-bey">${fixture.bey_a}</a>`;
                                    const beyBLink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_b)}" class="bey-link fixture-bey">${fixture.bey_b}</a>`;
                                    
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
                            const beyALink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_a)}" class="bey-link fixture-bey">${fixture.bey_a}</a>`;
                            const beyBLink = `<a href="bey.html?name=${encodeURIComponent(fixture.bey_b)}" class="bey-link fixture-bey">${fixture.bey_b}</a>`;
                            
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
