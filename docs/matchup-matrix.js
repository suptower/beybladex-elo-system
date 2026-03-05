// matchup-matrix.js
// Interactive Matchup Matrix for Beyblade X

let matchupData = null;
let filteredBeys = [];

// DOM Elements
const loadingEl = document.getElementById('loading');
const errorEl = document.getElementById('error');
const contentEl = document.getElementById('content');
const matrixTable = document.getElementById('matrixTable');
const matrixHeader = document.getElementById('matrixHeader');
const matrixBody = document.getElementById('matrixBody');
const tooltip = document.getElementById('tooltip');
const hardCountersList = document.getElementById('hardCountersList');

// Controls
const minMatchesInput = document.getElementById('minMatches');
const filterTierSelect = document.getElementById('filterTier');
const filterArchetypeSelect = document.getElementById('filterArchetype');
const sortBySelect = document.getElementById('sortBy');

// Load matchup data
async function loadMatchupData() {
    try {
        const response = await fetch('data/analytics/matchup_matrix.json');
        if (!response.ok) {
            throw new Error('Failed to load matchup data');
        }
        matchupData = await response.json();
        
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        
        initializeFilters();
        renderHardCounters();
        filterAndRenderMatrix();
    } catch (error) {
        console.error('Error loading matchup data:', error);
        loadingEl.style.display = 'none';
        errorEl.style.display = 'block';
    }
}

// Initialize filter dropdowns
function initializeFilters() {
    // Populate tier filter
    const tiers = [...new Set(matchupData.beys.map(b => b.tier))].sort();
    tiers.forEach(tier => {
        const option = document.createElement('option');
        option.value = tier;
        option.textContent = tier;
        filterTierSelect.appendChild(option);
    });
    
    // Populate archetype filter
    const archetypes = [...new Set(matchupData.beys.map(b => {
        if (typeof b.archetype === 'object' && b.archetype !== null && b.archetype.name) {
            return b.archetype.name;
        } else if (typeof b.archetype === 'string' && b.archetype) {
            return b.archetype;
        }
        return 'Unknown';
    }))].sort();
    
    archetypes.forEach(archetype => {
        const option = document.createElement('option');
        option.value = archetype;
        option.textContent = archetype;
        filterArchetypeSelect.appendChild(option);
    });
    
    // Add event listeners
    minMatchesInput.addEventListener('change', filterAndRenderMatrix);
    filterTierSelect.addEventListener('change', filterAndRenderMatrix);
    filterArchetypeSelect.addEventListener('change', filterAndRenderMatrix);
    sortBySelect.addEventListener('change', filterAndRenderMatrix);
}

// Render hard counters section
function renderHardCounters() {
    const hardCounters = matchupData.hard_counters || [];
    
    if (hardCounters.length === 0) {
        hardCountersList.innerHTML = '<p>No hard counters identified with current criteria (70%+ winrate, 5+ matches).</p>';
        return;
    }
    
    hardCountersList.innerHTML = '';
    hardCounters.slice(0, 12).forEach(counter => { // Show top 12
        const item = document.createElement('div');
        item.className = 'counter-item';
        
        const matchup = document.createElement('div');
        matchup.className = 'counter-matchup';
        matchup.textContent = `${counter.counter} counters ${counter.counters}`;
        
        const stats = document.createElement('div');
        stats.className = 'counter-stats';
        stats.textContent = `${(counter.winrate * 100).toFixed(1)}% winrate (${counter.matches} matches, ${counter.avg_diff > 0 ? '+' : ''}${counter.avg_diff.toFixed(1)} avg diff)`;
        
        item.appendChild(matchup);
        item.appendChild(stats);
        hardCountersList.appendChild(item);
    });
}

// Filter and sort beys
function filterAndRenderMatrix() {
    const minMatches = parseInt(minMatchesInput.value) || 0;
    const selectedTier = filterTierSelect.value;
    const selectedArchetype = filterArchetypeSelect.value;
    const sortBy = sortBySelect.value;
    
    // Filter beys
    filteredBeys = matchupData.beys.filter(bey => {
        // Filter by tier
        if (selectedTier !== 'all' && bey.tier !== selectedTier) {
            return false;
        }
        
        // Filter by archetype
        if (selectedArchetype !== 'all') {
            let beyArchetype = 'Unknown';
            if (typeof bey.archetype === 'object' && bey.archetype !== null) {
                beyArchetype = bey.archetype.name || 'Unknown';
            } else if (typeof bey.archetype === 'string') {
                beyArchetype = bey.archetype;
            }
            
            if (beyArchetype !== selectedArchetype) {
                return false;
            }
        }
        
        // Filter by minimum matches (check if bey has at least one matchup with enough matches)
        if (minMatches > 0) {
            const hasEnoughMatches = Object.values(matchupData.matrix[bey.name] || {}).some(
                matchup => matchup.matches >= minMatches
            );
            if (!hasEnoughMatches) {
                return false;
            }
        }
        
        return true;
    });
    
    // Sort beys
    filteredBeys.sort((a, b) => {
        switch (sortBy) {
            case 'elo':
                return (b.elo || 0) - (a.elo || 0);
            case 'matches':
                const aMatches = Object.values(matchupData.matrix[a.name] || {})
                    .reduce((sum, m) => sum + m.matches, 0);
                const bMatches = Object.values(matchupData.matrix[b.name] || {})
                    .reduce((sum, m) => sum + m.matches, 0);
                return bMatches - aMatches;
            case 'name':
            default:
                return a.name.localeCompare(b.name);
        }
    });
    
    renderMatrix();
}

// Render the matrix table
function renderMatrix() {
    const minMatches = parseInt(minMatchesInput.value) || 0;
    
    // Clear existing content
    matrixHeader.innerHTML = '';
    matrixBody.innerHTML = '';
    
    if (filteredBeys.length === 0) {
        matrixBody.innerHTML = '<tr><td colspan="100" style="text-align: center; padding: 20px;">No beys match the current filters.</td></tr>';
        return;
    }
    
    // Create header row
    const headerRow = document.createElement('tr');
    
    // Top-left corner cell
    const cornerCell = document.createElement('th');
    cornerCell.className = 'row-header';
    cornerCell.textContent = 'vs →';
    headerRow.appendChild(cornerCell);
    
    // Column headers (opponents)
    filteredBeys.forEach(bey => {
        const th = document.createElement('th');
        th.className = 'col-header';
        th.textContent = bey.name;
        th.title = bey.name;
        headerRow.appendChild(th);
    });
    
    matrixHeader.appendChild(headerRow);
    
    // Create data rows
    filteredBeys.forEach(beyA => {
        const row = document.createElement('tr');
        
        // Row header (bey name)
        const rowHeader = document.createElement('th');
        rowHeader.className = 'row-header';
        rowHeader.textContent = beyA.name;
        rowHeader.title = beyA.name;
        row.appendChild(rowHeader);
        
        // Data cells
        filteredBeys.forEach(beyB => {
            const cell = document.createElement('td');
            cell.className = 'matrix-cell';
            
            const matchup = matchupData.matrix[beyA.name]?.[beyB.name];
            
            if (beyA.name === beyB.name) {
                // Self-matchup
                cell.classList.add('self-matchup');
                cell.textContent = '—';
                cell.title = 'Same Beyblade';
            } else if (!matchup || matchup.matches === 0) {
                // No data
                cell.classList.add('no-data');
                cell.textContent = '—';
                cell.title = 'No matches';
            } else if (matchup.matches < minMatches) {
                // Insufficient matches (when filter is active)
                cell.classList.add('no-data');
                cell.innerHTML = `<div class="cell-winrate">${(matchup.winrate * 100).toFixed(0)}%</div><div class="cell-matches">${matchup.matches}m</div>`;
                cell.title = `Insufficient data (${matchup.matches} matches)`;
            } else {
                // Valid matchup data
                const winrate = matchup.winrate * 100;
                
                // Apply color class
                if (winrate < 20) cell.classList.add('wr-0-20');
                else if (winrate < 40) cell.classList.add('wr-20-40');
                else if (winrate < 60) cell.classList.add('wr-40-60');
                else if (winrate < 80) cell.classList.add('wr-60-80');
                else cell.classList.add('wr-80-100');
                
                // Display winrate and match count
                cell.innerHTML = `
                    <div class="cell-winrate">${winrate.toFixed(0)}%</div>
                    <div class="cell-matches">${matchup.matches}m</div>
                `;
                
                // Add hover tooltip
                cell.addEventListener('mouseenter', (e) => showTooltip(e, beyA.name, beyB.name, matchup));
                cell.addEventListener('mouseleave', hideTooltip);
            }
            
            row.appendChild(cell);
        });
        
        matrixBody.appendChild(row);
    });
}

// Show tooltip with matchup details
function showTooltip(event, beyA, beyB, matchup) {
    const winrate = (matchup.winrate * 100).toFixed(1);
    const avgDiff = matchup.avg_diff > 0 ? `+${matchup.avg_diff.toFixed(1)}` : matchup.avg_diff.toFixed(1);
    
    tooltip.innerHTML = `
        <strong>${beyA} vs ${beyB}</strong>
        <div class="tooltip-row">Winrate: ${winrate}%</div>
        <div class="tooltip-row">Record: ${matchup.wins}-${matchup.losses} (${matchup.matches} matches)</div>
        <div class="tooltip-row">Avg Point Diff: ${avgDiff}</div>
    `;
    
    // Position tooltip
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = `${rect.left + window.scrollX + rect.width / 2}px`;
    tooltip.style.top = `${rect.top + window.scrollY - tooltip.offsetHeight - 10}px`;
    tooltip.classList.add('show');
}

// Hide tooltip
function hideTooltip() {
    tooltip.classList.remove('show');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadMatchupData();
});
