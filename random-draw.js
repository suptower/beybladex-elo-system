/**
 * Random Bey Draw - Frontend Logic
 * 
 * Handles the UI and logic for randomly selecting Beys from the leaderboard
 * using various draw algorithms.
 */

let leaderboardData = [];
let beyMetadata = {};
let rpgStats = {};

// Algorithm descriptions for hints
const ALGORITHM_HINTS = {
    pure_random: 'Uniform random selection from all Beys',
    ranking_bucket: 'Draw evenly from rank ranges (Top, Mid, Bottom)',
    weighted_elo: 'Higher Elo = higher selection probability',
    type_based: 'Balanced mix of Attack/Defense/Stamina/Balance',
    archetype_based: 'Ensures diversity across playstyles',
    custom: 'Advanced filtering with custom constraints'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
});

/**
 * Load necessary data files
 */
async function loadData() {
    try {
        // Load leaderboard
        const leaderboardResponse = await fetch(DATA_PATHS.LEADERBOARD_CSV);
        const leaderboardText = await leaderboardResponse.text();
        leaderboardData = parseLeaderboardCSV(leaderboardText);

        // Load Bey metadata
        const metadataResponse = await fetch(DATA_PATHS.BEYS_DATA_JSON);
        beyMetadata = await metadataResponse.json();

        // Load RPG stats
        const rpgResponse = await fetch(DATA_PATHS.RPG_STATS_JSON);
        rpgStats = await rpgResponse.json();

        console.log(`Loaded ${leaderboardData.length} Beys from leaderboard`);
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Failed to load leaderboard data. Please refresh the page.');
    }
}

/**
 * Parse leaderboard CSV
 */
function parseLeaderboardCSV(csvText) {
    const lines = csvText.trim().split('\n');
    const headers = lines[0].split(',');
    const beys = [];

    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const bey = {
            rank: parseInt(values[0]),
            name: values[1],
            elo: parseInt(values[2]),
            matches: parseInt(values[3]),
            wins: parseInt(values[4]),
            losses: parseInt(values[5]),
            winrate: parseFloat(values[6].replace('%', ''))
        };
        beys.push(bey);
    }

    return beys;
}

/**
 * Get Bey metadata (type, code, etc.)
 */
function getBeyMetadata(beyName) {
    for (const bey of beyMetadata) {
        if (bey.blade === beyName) {
            return bey;
        }
    }
    return null;
}

/**
 * Get Bey archetype from RPG stats
 */
function getBeyArchetype(beyName) {
    if (rpgStats[beyName] && rpgStats[beyName].archetype) {
        return rpgStats[beyName].archetype;
    }
    return null;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const algorithmSelect = document.getElementById('algorithmSelect');
    const drawButton = document.getElementById('drawButton');
    const clearButton = document.getElementById('clearButton');
    const exportListButton = document.getElementById('exportListButton');
    const exportCSVButton = document.getElementById('exportCSVButton');
    const exportJSONButton = document.getElementById('exportJSONButton');

    algorithmSelect.addEventListener('change', updateAlgorithmOptions);
    drawButton.addEventListener('click', performDraw);
    clearButton.addEventListener('click', clearResults);
    exportListButton.addEventListener('click', exportAsList);
    exportCSVButton.addEventListener('click', exportAsCSV);
    exportJSONButton.addEventListener('click', exportAsJSON);

    // Initialize with default algorithm options
    updateAlgorithmOptions();
}

/**
 * Update algorithm-specific options based on selection
 */
function updateAlgorithmOptions() {
    const algorithm = document.getElementById('algorithmSelect').value;
    const hintElement = document.getElementById('algorithmHint');
    const optionsContainer = document.getElementById('algorithmOptions');

    hintElement.textContent = ALGORITHM_HINTS[algorithm];
    optionsContainer.innerHTML = '';

    switch (algorithm) {
        case 'ranking_bucket':
            optionsContainer.innerHTML = `
                <div class="control-group">
                    <label for="bucketsInput">Number of Buckets</label>
                    <input type="number" id="bucketsInput" value="3" min="2" max="10" class="control-input">
                    <span class="control-hint">Split leaderboard into N rank ranges</span>
                </div>
            `;
            break;

        case 'weighted_elo':
            optionsContainer.innerHTML = `
                <div class="control-group">
                    <label for="weightingType">Weighting Type</label>
                    <select id="weightingType" class="control-input">
                        <option value="linear">Linear (Direct proportion to Elo)</option>
                        <option value="soft">Soft (Logarithmic, reduces advantage)</option>
                    </select>
                </div>
            `;
            break;

        case 'type_based':
            optionsContainer.innerHTML = `
                <div class="control-group">
                    <label for="distributionType">Distribution Type</label>
                    <select id="distributionType" class="control-input">
                        <option value="balanced">Balanced (Equal from each type)</option>
                        <option value="proportional">Proportional (By availability)</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="maxPerType">Max Per Type (Optional)</label>
                    <input type="number" id="maxPerType" placeholder="No limit" min="1" class="control-input">
                    <span class="control-hint">Maximum Beys per type</span>
                </div>
            `;
            break;

        case 'custom':
            optionsContainer.innerHTML = `
                <div class="control-group">
                    <label for="minElo">Minimum Elo (Optional)</label>
                    <input type="number" id="minElo" placeholder="No minimum" class="control-input">
                </div>
                <div class="control-group">
                    <label for="maxElo">Maximum Elo (Optional)</label>
                    <input type="number" id="maxElo" placeholder="No maximum" class="control-input">
                </div>
                <div class="control-group">
                    <label for="excludeList">Exclude Beys (comma-separated)</label>
                    <input type="text" id="excludeList" placeholder="BeyA, BeyB, BeyC..." class="control-input">
                </div>
                <div class="control-group">
                    <label for="includeList">Force Include Beys (comma-separated)</label>
                    <input type="text" id="includeList" placeholder="BeyX, BeyY, BeyZ..." class="control-input">
                </div>
            `;
            break;
    }
}

/**
 * Perform the draw using selected algorithm
 */
function performDraw() {
    const algorithm = document.getElementById('algorithmSelect').value;
    const count = parseInt(document.getElementById('drawCount').value);
    const seedInput = document.getElementById('randomSeed').value;
    const seed = seedInput ? parseInt(seedInput) : null;

    if (!leaderboardData.length) {
        alert('Leaderboard data not loaded yet. Please wait and try again.');
        return;
    }

    if (count < 1 || count > 50) {
        alert('Please enter a valid number between 1 and 50.');
        return;
    }

    // Get algorithm-specific parameters
    const params = { seed };

    switch (algorithm) {
        case 'ranking_bucket':
            const bucketsInput = document.getElementById('bucketsInput');
            params.buckets = bucketsInput ? parseInt(bucketsInput.value) : 3;
            break;

        case 'weighted_elo':
            const weightingType = document.getElementById('weightingType');
            params.weighting = weightingType ? weightingType.value : 'linear';
            break;

        case 'type_based':
            const distributionType = document.getElementById('distributionType');
            const maxPerType = document.getElementById('maxPerType');
            params.distribution = distributionType ? distributionType.value : 'balanced';
            if (maxPerType && maxPerType.value) {
                params.max_per_type = parseInt(maxPerType.value);
            }
            break;

        case 'custom':
            const minElo = document.getElementById('minElo');
            const maxElo = document.getElementById('maxElo');
            const excludeList = document.getElementById('excludeList');
            const includeList = document.getElementById('includeList');

            if (minElo && minElo.value) params.min_elo = parseInt(minElo.value);
            if (maxElo && maxElo.value) params.max_elo = parseInt(maxElo.value);
            if (excludeList && excludeList.value) {
                params.exclude = excludeList.value.split(',').map(s => s.trim()).filter(s => s);
            }
            if (includeList && includeList.value) {
                params.include = includeList.value.split(',').map(s => s.trim()).filter(s => s);
            }
            break;
    }

    // Execute the draw
    const selectedBeys = executeDraw(algorithm, count, params);

    // Display results
    displayResults(selectedBeys, algorithm);
}

/**
 * Execute draw algorithm
 */
function executeDraw(algorithm, count, params) {
    // Create a seeded random number generator if seed provided
    const rng = params.seed !== null ? new SeededRandom(params.seed) : Math;

    switch (algorithm) {
        case 'pure_random':
            return pureRandom(leaderboardData, count, rng);

        case 'ranking_bucket':
            return rankingBucketBalanced(leaderboardData, count, params.buckets, rng);

        case 'weighted_elo':
            return weightedByElo(leaderboardData, count, params.weighting, rng);

        case 'type_based':
            return typeBasedDistribution(leaderboardData, count, params.distribution, params.max_per_type, rng);

        case 'archetype_based':
            return archetypeBasedDistribution(leaderboardData, count, rng);

        case 'custom':
            return customConstraints(leaderboardData, count, params, rng);

        default:
            return pureRandom(leaderboardData, count, rng);
    }
}

/**
 * Pure Random Algorithm
 */
function pureRandom(beys, count, rng) {
    const available = [...beys];
    const selected = [];

    count = Math.min(count, available.length);

    for (let i = 0; i < count; i++) {
        const index = Math.floor(rng.random() * available.length);
        selected.push(available[index]);
        available.splice(index, 1);
    }

    return selected;
}

/**
 * Ranking Bucket Balanced Algorithm
 */
function rankingBucketBalanced(beys, count, buckets, rng) {
    const sorted = [...beys].sort((a, b) => a.rank - b.rank);
    count = Math.min(count, sorted.length);

    const effectiveBuckets = Math.min(buckets, sorted.length);
    if (effectiveBuckets === 0) return [];

    // Split into buckets
    const bucketSize = Math.floor(sorted.length / effectiveBuckets);
    const beyBuckets = [];

    for (let i = 0; i < effectiveBuckets; i++) {
        const start = i * bucketSize;
        const end = i < effectiveBuckets - 1 ? start + bucketSize : sorted.length;
        beyBuckets.push(sorted.slice(start, end));
    }

    // Calculate distribution
    const perBucket = Math.floor(count / beyBuckets.length);
    const remainder = count % beyBuckets.length;

    const selected = [];
    for (let i = 0; i < beyBuckets.length; i++) {
        const bucket = beyBuckets[i];
        if (!bucket.length) continue;

        let bucketCount = perBucket + (i < remainder ? 1 : 0);
        bucketCount = Math.min(bucketCount, bucket.length);

        const bucketSelection = pureRandom(bucket, bucketCount, rng);
        selected.push(...bucketSelection);
    }

    return selected;
}

/**
 * Weighted by Elo Algorithm
 */
function weightedByElo(beys, count, weighting, rng) {
    count = Math.min(count, beys.length);

    // Calculate weights
    let weights = beys.map(bey => {
        if (weighting === 'soft') {
            return Math.log(Math.max(bey.elo, 1));
        }
        return bey.elo;
    });

    // Ensure positive weights
    const minWeight = Math.min(...weights);
    if (minWeight <= 0) {
        weights = weights.map(w => w - minWeight + 1);
    }

    const selected = [];
    const available = [...beys];
    let availableWeights = [...weights];

    for (let i = 0; i < count; i++) {
        const totalWeight = availableWeights.reduce((sum, w) => sum + w, 0);
        let rand = rng.random() * totalWeight;

        let index = 0;
        for (let j = 0; j < availableWeights.length; j++) {
            rand -= availableWeights[j];
            if (rand <= 0) {
                index = j;
                break;
            }
        }

        selected.push(available[index]);
        available.splice(index, 1);
        availableWeights.splice(index, 1);
    }

    return selected;
}

/**
 * Type-Based Distribution Algorithm
 */
function typeBasedDistribution(beys, count, distribution, maxPerType, rng) {
    count = Math.min(count, beys.length);

    // Group by type
    const beysByType = {};
    for (const bey of beys) {
        const metadata = getBeyMetadata(bey.name);
        const type = metadata ? metadata.type : 'Unknown';
        if (!beysByType[type]) beysByType[type] = [];
        beysByType[type].push(bey);
    }

    const types = Object.keys(beysByType);
    const selected = [];

    if (distribution === 'balanced') {
        const perType = Math.floor(count / types.length);
        const remainder = count % types.length;

        for (let i = 0; i < types.length; i++) {
            const type = types[i];
            let typeCount = perType + (i < remainder ? 1 : 0);

            if (maxPerType !== undefined) {
                typeCount = Math.min(typeCount, maxPerType);
            }

            typeCount = Math.min(typeCount, beysByType[type].length);
            const typeSelection = pureRandom(beysByType[type], typeCount, rng);
            selected.push(...typeSelection);
        }
    } else {
        // Proportional
        for (const type of types) {
            const proportion = beysByType[type].length / beys.length;
            let typeCount = Math.round(count * proportion);

            if (maxPerType !== undefined) {
                typeCount = Math.min(typeCount, maxPerType);
            }

            typeCount = Math.min(typeCount, beysByType[type].length);
            const typeSelection = pureRandom(beysByType[type], typeCount, rng);
            selected.push(...typeSelection);
        }
    }

    // Adjust to exact count
    if (selected.length < count) {
        const remaining = beys.filter(b => !selected.includes(b));
        const needed = count - selected.length;
        const additional = pureRandom(remaining, Math.min(needed, remaining.length), rng);
        selected.push(...additional);
    } else if (selected.length > count) {
        selected.splice(count);
    }

    return selected;
}

/**
 * Archetype-Based Distribution Algorithm
 */
function archetypeBasedDistribution(beys, count, rng) {
    count = Math.min(count, beys.length);

    // Group by archetype
    const beysByArchetype = {};
    const withoutArchetype = [];

    for (const bey of beys) {
        const archetype = getBeyArchetype(bey.name);
        if (archetype) {
            const archetypeId = archetype.id;
            if (!beysByArchetype[archetypeId]) beysByArchetype[archetypeId] = [];
            beysByArchetype[archetypeId].push(bey);
        } else {
            withoutArchetype.push(bey);
        }
    }

    const archetypes = Object.keys(beysByArchetype);
    if (archetypes.length === 0) {
        return pureRandom(beys, count, rng);
    }

    const perArchetype = Math.floor(count / archetypes.length);
    const remainder = count % archetypes.length;

    const selected = [];
    for (let i = 0; i < archetypes.length; i++) {
        const archetype = archetypes[i];
        let archetypeCount = perArchetype + (i < remainder ? 1 : 0);
        archetypeCount = Math.min(archetypeCount, beysByArchetype[archetype].length);

        const archetypeSelection = pureRandom(beysByArchetype[archetype], archetypeCount, rng);
        selected.push(...archetypeSelection);
    }

    // Fill remaining from Beys without archetype
    if (selected.length < count && withoutArchetype.length) {
        const needed = count - selected.length;
        const additional = pureRandom(withoutArchetype, Math.min(needed, withoutArchetype.length), rng);
        selected.push(...additional);
    }

    // Fill any remaining from all Beys
    if (selected.length < count) {
        const remaining = beys.filter(b => !selected.includes(b));
        const needed = count - selected.length;
        const additional = pureRandom(remaining, Math.min(needed, remaining.length), rng);
        selected.push(...additional);
    }

    return selected;
}

/**
 * Custom Constraints Algorithm
 */
function customConstraints(beys, count, params, rng) {
    const { min_elo, max_elo, exclude, include } = params;

    // Start with included Beys
    let selected = [];
    if (include && include.length) {
        selected = beys.filter(b => include.includes(b.name));
    }

    // Filter eligible Beys
    const eligible = beys.filter(bey => {
        if (selected.includes(bey)) return false;
        if (exclude && exclude.includes(bey.name)) return false;
        if (min_elo !== undefined && bey.elo < min_elo) return false;
        if (max_elo !== undefined && bey.elo > max_elo) return false;
        return true;
    });

    // Draw remaining
    const remainingCount = count - selected.length;
    if (remainingCount > 0 && eligible.length) {
        const additional = pureRandom(eligible, Math.min(remainingCount, eligible.length), rng);
        selected.push(...additional);
    }

    return selected.slice(0, count);
}

/**
 * Display results in table
 */
function displayResults(selectedBeys, algorithm) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsTableBody = document.getElementById('resultsTableBody');
    const resultsCount = document.getElementById('resultsCount');
    const resultsAlgorithm = document.getElementById('resultsAlgorithm');

    // Update header info
    resultsCount.textContent = `${selectedBeys.length} Beys Selected`;
    resultsAlgorithm.textContent = `Algorithm: ${algorithm.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}`;

    // Clear table
    resultsTableBody.innerHTML = '';

    // Add rows
    selectedBeys.forEach((bey, index) => {
        const metadata = getBeyMetadata(bey.name);
        const archetype = getBeyArchetype(bey.name);

        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="col-seed">${index + 1}</td>
            <td class="col-bey"><a href="bey.html?bey=${encodeURIComponent(bey.name)}">${bey.name}</a></td>
            <td class="col-elo">${bey.elo}</td>
            <td class="col-rank">#${bey.rank}</td>
            <td class="col-type">${metadata ? metadata.type : 'Unknown'}</td>
            <td class="col-archetype">${archetype ? archetype.icon + ' ' + archetype.name : '❓ Unknown'}</td>
            <td class="col-stats">${bey.wins}W-${bey.losses}L (${bey.winrate.toFixed(1)}%)</td>
        `;
        resultsTableBody.appendChild(row);
    });

    // Show results section
    resultsSection.style.display = 'block';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Store results for export
    window.lastDrawResults = selectedBeys;
}

/**
 * Clear results
 */
function clearResults() {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'none';
    window.lastDrawResults = null;
}

/**
 * Export as plain text list
 */
function exportAsList() {
    if (!window.lastDrawResults) return;

    const list = window.lastDrawResults.map((bey, i) => 
        `${i + 1}. ${bey.name} (ELO ${bey.elo}, Rank #${bey.rank})`
    ).join('\n');

    copyToClipboard(list);
    alert('List copied to clipboard!');
}

/**
 * Export as CSV
 */
function exportAsCSV() {
    if (!window.lastDrawResults) return;

    const headers = ['Seed', 'Name', 'ELO', 'Rank', 'Type', 'Archetype', 'Matches', 'Wins', 'Losses', 'Winrate'];
    const rows = window.lastDrawResults.map((bey, i) => {
        const metadata = getBeyMetadata(bey.name);
        const archetype = getBeyArchetype(bey.name);
        return [
            i + 1,
            bey.name,
            bey.elo,
            bey.rank,
            metadata ? metadata.type : 'Unknown',
            archetype ? archetype.name : 'Unknown',
            bey.matches,
            bey.wins,
            bey.losses,
            bey.winrate.toFixed(1) + '%'
        ];
    });

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');

    downloadFile('random_draw.csv', csv, 'text/csv');
}

/**
 * Export as JSON
 */
function exportAsJSON() {
    if (!window.lastDrawResults) return;

    const data = window.lastDrawResults.map((bey, i) => {
        const metadata = getBeyMetadata(bey.name);
        const archetype = getBeyArchetype(bey.name);
        return {
            seed: i + 1,
            name: bey.name,
            elo: bey.elo,
            rank: bey.rank,
            type: metadata ? metadata.type : 'Unknown',
            archetype: archetype ? archetype.name : 'Unknown',
            matches: bey.matches,
            wins: bey.wins,
            losses: bey.losses,
            winrate: bey.winrate
        };
    });

    const json = JSON.stringify(data, null, 2);
    downloadFile('random_draw.json', json, 'application/json');
}

/**
 * Utility: Copy text to clipboard
 */
function copyToClipboard(text) {
    // Use modern Clipboard API if available
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(err => {
            console.error('Failed to copy text: ', err);
            // Fallback to older method
            fallbackCopyToClipboard(text);
        });
    } else {
        // Fallback for older browsers
        fallbackCopyToClipboard(text);
    }
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
    } catch (err) {
        console.error('Fallback: Failed to copy text: ', err);
    }
    document.body.removeChild(textarea);
}

/**
 * Utility: Download file
 */
function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Seeded Random Number Generator
 * Uses a simple LCG (Linear Congruential Generator)
 */
class SeededRandom {
    constructor(seed) {
        this.seed = seed;
    }

    random() {
        this.seed = (this.seed * 9301 + 49297) % 233280;
        return this.seed / 233280;
    }
}
