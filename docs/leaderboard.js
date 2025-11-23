let leaderboardRows = [];
let leaderboardHeaders = [];
let currentSort = { column: null, asc: true };
let currentSearchQuery = ""; // Track the current search query
let isAdvancedMode = false; // Track which leaderboard is being displayed

// Column abbreviations for advanced mode
const COLUMN_ABBREVIATIONS = {
    'PointsFor': 'Pts+',
    'PointsAgainst': 'Pts-',
    'AvgPointDiff': 'AvgΔPts',
    'Volatility': 'Vol',
    'AvgΔELO': 'AvgΔ',
    'MaxΔELO': 'MaxΔ',
    'MinΔELO': 'MinΔ',
    'UpsetWins': 'U-W',
    'UpsetLosses': 'U-L',
    'ELOTrend': 'Trend'
};

// Full descriptions for legend with detailed explanations
const COLUMN_DESCRIPTIONS = {
    'Platz': { short: 'Rank/Position', long: 'Current ranking position in the leaderboard' },
    'Bey': { short: 'Beyblade Name', long: 'Name of the Beyblade' },
    'ELO': { short: 'ELO Rating', long: 'Current ELO rating (skill level indicator)' },
    'Matches': { short: 'Games Played', long: 'Total number of matches played' },
    'Wins': { short: 'Wins', long: 'Total number of wins' },
    'Losses': { short: 'Losses', long: 'Total number of losses' },
    'Winrate': { short: 'Win Rate', long: 'Percentage of games won' },
    'Pts+': { short: 'Points For', long: 'Total points scored across all matches' },
    'Pts-': { short: 'Points Against', long: 'Total points conceded across all matches' },
    'AvgΔPts': { short: 'Average Point Difference', long: 'Average point margin per match (positive = more points scored than conceded)' },
    'Vol': { short: 'Volatility', long: 'Standard deviation of ELO changes - measures performance consistency (lower = more consistent)' },
    'AvgΔ': { short: 'Average ELO Change', long: 'Average ELO rating change per match' },
    'MaxΔ': { short: 'Maximum ELO Change', long: 'Largest single-match ELO gain' },
    'MinΔ': { short: 'Minimum ELO Change', long: 'Largest single-match ELO loss' },
    'U-W': { short: 'Upset Wins', long: 'Number of wins against higher-rated opponents' },
    'U-L': { short: 'Upset Losses', long: 'Number of losses against lower-rated opponents' },
    'Trend': { short: 'ELO Trend', long: 'Overall ELO trend/momentum (positive = improving, negative = declining)' },
    // Standard mode columns
    'Name': { short: 'Beyblade Name', long: 'Name of the Beyblade' },
    'Spiele': { short: 'Games Played', long: 'Total number of matches played' },
    'Siege': { short: 'Wins', long: 'Total number of wins' },
    'Niederlagen': { short: 'Losses', long: 'Total number of losses' },
    'Gewonnene Punkte': { short: 'Points Won', long: 'Total points scored across all matches' },
    'Verlorene Punkte': { short: 'Points Lost', long: 'Total points conceded across all matches' },
    'Differenz': { short: 'Point Difference', long: 'Total point difference (points won - points lost)' },
    'Positionsdelta': { short: 'Position Change', long: 'Change in ranking position since last update' },
    'ELOdelta': { short: 'ELO Change', long: 'ELO rating change since last update' },
    'ΔPosition': { short: 'Position Change', long: 'Change in ranking position since last update' },
    'ΔELO': { short: 'ELO Change', long: 'ELO rating change since last update' }
};

function getAbbreviatedHeader(header) {
    return COLUMN_ABBREVIATIONS[header] || header;
}

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);  // Handle both \n and \r\n
    const headers = lines[0].split(",").map(h => h.trim());
    console.log("Parsed Headers:", headers);

    const rows = lines.slice(1).map(line => {
        const values = line.split(",").map(v => v.trim());
        const obj = {};
        headers.forEach((h, i) => obj[h] = values[i]);
        return obj;
    });

    return { headers, rows };
}

function loadLeaderboard(isAdvanced = false) {
    const csvPath = isAdvanced 
        ? "./data/advanced_leaderboard.csv" 
        : "./data/leaderboard.csv";
    
    fetch(csvPath)
        .then(res => res.text())
        .then(csv => {
            const parsed = parseCSV(csv);
            leaderboardHeaders = parsed.headers;
            leaderboardRows = parsed.rows;
            currentSort = { column: null, asc: true }; // Reset sort when switching
            updateView();
            updateLegend(); // Update legend when data loads
        })
        .catch(err => {
            console.error("Error loading leaderboard:", err);
        });
}

function renderTable(headers, rows) {
    const headRow = document.getElementById("leaderboardHeadRow");
    const body = document.getElementById("leaderboardBody");

    headRow.innerHTML = "";
    body.innerHTML = "";

    const displayHeaders = headers;

    // --- Kopfzeile bauen ---
    displayHeaders.forEach((h, index) => {
        const th = document.createElement("th");
        th.classList.add("sortable");
        // Use abbreviated headers for advanced mode
        th.textContent = (isAdvancedMode && index > 0) ? getAbbreviatedHeader(h) : h;

        // Set sort indicator if this is the active column
        // Adjust index for advanced mode since we added "Platz" column
        const sortIndex = isAdvancedMode && index > 0 ? index - 1 : index;
        if (currentSort.column === sortIndex && (!isAdvancedMode || index > 0)) {
            th.classList.add(currentSort.asc ? "sorted-asc" : "sorted-desc");
        }

        // Only make sortable if not the rank column in advanced mode or any column in standard mode
        if (!isAdvancedMode || index > 0) {
            th.onclick = () => sortByColumn(sortIndex);
        } else {
            th.classList.remove("sortable");
            th.style.cursor = "default";
        }
        
        headRow.appendChild(th);
    });

    // --- Datenzeilen bauen ---
    rows.forEach((row, rowIndex) => {
        const tr = document.createElement("tr");

        displayHeaders.forEach((h, colIndex) => {
            const td = document.createElement("td");
            
            // For advanced mode, use the actual Platz value from the data
            let value;
            if (isAdvancedMode && colIndex === 0) {
                // Use the Platz value from the row data, or calculate from original position
                value = row["Platz"] || (leaderboardRows.indexOf(row) + 1).toString();
            } else {
                value = row[h] ?? "";
            }

            // Standard-Text setzen (wird ggf. durch HTML ersetzt bei Cards)
            td.textContent = value;

            // Highlight ELO
            if (h.toLowerCase() === "elo") {
                const elo = parseInt(value);
                if (!isNaN(elo)) {
                    if (elo >= 1050) td.classList.add("trend-very-positive");
                    else if (elo >= 1010) td.classList.add("trend-positive");
                    else if (elo >= 990) td.classList.add("trend-neutral");
                    else if (elo >= 950) td.classList.add("trend-negative");
                    else if (elo < 950) td.classList.add("trend-very-negative");
                }
            }

            // Highlight Winrate
            if (h.toLowerCase() === "winrate") {
                applyWinrateStyling(td, value);
            }

            // Highlight Positionsdelta (Spaltenname enthält "positionsdelta" oder ähnlich)
            if (h.toLowerCase().includes("positionsdelta") || h.toLowerCase().includes("positiondelta")) {
                applyDeltaStyling(td, value, "pos");
            }

            // Highlight ELOdelta (Spaltenname enthält "elod" oder "elodelta")
            if (h.toLowerCase().includes("elod") || h.toLowerCase().includes("elodelta")) {
                applyDeltaStyling(td, value, "elo");
            }

            // Highlight ELOTrend (for advanced mode)
            if (h === "ELOTrend" || h.toLowerCase() === "trend") {
                applyTrendStyling(td, value);
            }

            // Highlight Volatility (for advanced mode)
            if (h === "Volatility" || h.toLowerCase() === "vol") {
                applyVolatilityStyling(td, value);
            }

            tr.appendChild(td);
        });

        body.appendChild(tr);
    });
}


function renderCards(headers, rows) {
    const container = document.getElementById("leaderboardCards");
    container.innerHTML = "";

    rows.forEach((row, index) => {
        const card = document.createElement("div");
        card.className = "lb-card";

        // Header with rank, name, and ELO
        const cardHeader = document.createElement("div");
        cardHeader.className = "lb-card-header";
        
        const rank = document.createElement("div");
        rank.className = "lb-card-rank";
        // Use the Platz value from the row data, or calculate from original position
        rank.textContent = row["Platz"] || (leaderboardRows.indexOf(row) + 1);
        
        const name = document.createElement("h3");
        name.className = "lb-card-name";
        // Advanced mode uses "Bey", standard uses "Name"
        name.textContent = row["Name"] || row["Bey"] || "Unknown";
        
        const elo = document.createElement("div");
        elo.className = "lb-card-elo";
        elo.textContent = row["ELO"] || "-";
        
        cardHeader.appendChild(rank);
        cardHeader.appendChild(name);
        cardHeader.appendChild(elo);
        card.appendChild(cardHeader);

        // Main stats (Wins/Losses/Winrate)
        const stats = document.createElement("div");
        stats.className = "lb-card-stats";
        
        const createStat = (label, value) => {
            const stat = document.createElement("div");
            stat.className = "lb-stat";
            
            const statLabel = document.createElement("div");
            statLabel.className = "lb-stat-label";
            statLabel.textContent = label;
            
            const statValue = document.createElement("div");
            statValue.className = "lb-stat-value";
            statValue.textContent = value;
            
            stat.appendChild(statLabel);
            stat.appendChild(statValue);
            return stat;
        };
        
        // Advanced mode uses "Wins/Losses/Matches", standard uses "Siege/Niederlagen/Spiele"
        stats.appendChild(createStat("Wins", row["Siege"] || row["Wins"] || "0"));
        stats.appendChild(createStat("Losses", row["Niederlagen"] || row["Losses"] || "0"));
        stats.appendChild(createStat("Winrate", row["Winrate"] || "0%"));
        card.appendChild(stats);

        // Expandable details section
        const expandSection = document.createElement("div");
        expandSection.className = "lb-card-expand";
        
        const details = document.createElement("div");
        details.className = "lb-card-details";
        
        const createDetail = (label, value, applyDelta = false) => {
            const detail = document.createElement("div");
            detail.className = "lb-detail";
            
            const detailLabel = document.createElement("span");
            detailLabel.className = "lb-detail-label";
            detailLabel.textContent = label;
            
            const detailValue = document.createElement("span");
            detailValue.className = "lb-detail-value";
            
            if (applyDelta && value) {
                detailValue.classList.add(getDeltaClass(value));
            }
            detailValue.textContent = value || "-";
            
            detail.appendChild(detailLabel);
            detail.appendChild(detailValue);
            return detail;
        };
        
        // Conditional details based on mode
        if (isAdvancedMode) {
            details.appendChild(createDetail("Matches", row["Matches"]));
            details.appendChild(createDetail("Pts For", row["PointsFor"]));
            details.appendChild(createDetail("Pts Against", row["PointsAgainst"]));
            details.appendChild(createDetail("Avg Δ", row["AvgPointDiff"]));
            details.appendChild(createDetail("Volatility", row["Volatility"]));
            details.appendChild(createDetail("Avg ΔELO", row["AvgΔELO"]));
            details.appendChild(createDetail("Max ΔELO", row["MaxΔELO"]));
            details.appendChild(createDetail("Min ΔELO", row["MinΔELO"]));
            details.appendChild(createDetail("Upset W", row["UpsetWins"]));
            details.appendChild(createDetail("Upset L", row["UpsetLosses"]));
            
            // Add ELO Trend with conditional styling
            const trendDetail = createDetail("ELO Trend", row["ELOTrend"]);
            const trendValue = trendDetail.querySelector('.lb-detail-value');
            if (trendValue && row["ELOTrend"]) {
                applyTrendStyling(trendValue, row["ELOTrend"]);
            }
            details.appendChild(trendDetail);
        } else {
            details.appendChild(createDetail("Games", row["Spiele"]));
            details.appendChild(createDetail("Pts Won", row["Gewonnene Punkte"]));
            details.appendChild(createDetail("Pts Lost", row["Verlorene Punkte"]));
            details.appendChild(createDetail("Difference", row["Differenz"]));
            details.appendChild(createDetail("Pos Δ", row["Positionsdelta"], true));
            details.appendChild(createDetail("ELO Δ", row["ELOdelta"], true));
        }
        
        expandSection.appendChild(details);
        card.appendChild(expandSection);
        
        // Expand button
        const expandBtn = document.createElement("button");
        expandBtn.className = "lb-expand-btn";
        expandBtn.textContent = "Show Details";
        expandBtn.onclick = () => {
            expandSection.classList.toggle("expanded");
            expandBtn.textContent = expandSection.classList.contains("expanded") 
                ? "Hide Details" 
                : "Show Details";
        };
        card.appendChild(expandBtn);

        container.appendChild(card);
    });
}


function updateView() {
    const isMobile = window.innerWidth < 900;
    const tableWrapper = document.querySelector(".table-wrapper");
    const cardWrapper = document.getElementById("leaderboardCards");

    // Apply current search filter
    const filtered = currentSearchQuery 
        ? leaderboardRows.filter(r =>
            Object.values(r).some(v => String(v).toLowerCase().includes(currentSearchQuery.toLowerCase()))
          )
        : leaderboardRows;

    if (isMobile) {
        tableWrapper.style.display = "none";
        cardWrapper.style.display = "grid";
        renderCards(leaderboardHeaders, filtered);
    } else {
        tableWrapper.style.display = "block";
        cardWrapper.style.display = "none";
        renderTable(leaderboardHeaders, filtered);
    }
}

function parseDeltaValue(value) {
    if (!value) return 0;

    value = value.trim();

    // Kein Pfeil → normaler integer
    if (!value.includes("▲") && !value.includes("▼")) {
        const n = parseInt(value);
        return isNaN(n) ? 0 : n;
    }

    // ▲ = +, ▼ = -
    if (value.startsWith("▲")) {
        const n = parseInt(value.replace("▲", "").trim());
        return isNaN(n) ? 0 : +n;
    }

    if (value.startsWith("▼")) {
        const n = parseInt(value.replace("▼", "").trim());
        return isNaN(n) ? 0 : -n;
    }

    return 0;
}


function sortByColumn(colIndex) {
    const key = leaderboardHeaders[colIndex];

    const asc = currentSort.column === colIndex ? !currentSort.asc : true;
    currentSort = { column: colIndex, asc };

    leaderboardRows.sort((a, b) => {
        const raw1 = a[key];
        const raw2 = b[key];

        // --- Spezialfall: Positionsdelta ---
        if (key.toLowerCase().includes("positionsdelta")) {
            const v1 = parseDeltaValue(raw1);
            const v2 = parseDeltaValue(raw2);
            return asc ? v1 - v2 : v2 - v1;
        }

        // --- normaler numeric sort ---
        const n1 = parseFloat(raw1);
        const n2 = parseFloat(raw2);

        if (!isNaN(n1) && !isNaN(n2)) {
            return asc ? n1 - n2 : n2 - n1;
        }

        // --- fallback: alphabetic ---
        return asc ? raw1.localeCompare(raw2) : raw2.localeCompare(raw1);
    });
    
    // Animation für sortierte Zeilen
    const rows = document.querySelectorAll("#leaderboardBody tr");
    rows.forEach(r => {
        r.classList.add("sort-animate");
        setTimeout(() => r.classList.remove("sort-animate"), 250);
    });


    updateView();
}


function filterRows(query) {
    currentSearchQuery = query; // Store the current search query
    query = query.toLowerCase();
    const filtered = leaderboardRows.filter(r =>
        Object.values(r).some(v => String(v).toLowerCase().includes(query))
    );

    if (window.innerWidth < 900) {
        renderCards(leaderboardHeaders, filtered);
    } else {
        renderTable(leaderboardHeaders, filtered);
    }
}

window.addEventListener("resize", updateView);

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", e => filterRows(e.target.value));
    }

    const toggleInput = document.getElementById("leaderboardToggle");
    if (toggleInput) {
        // Load saved preference from localStorage
        const savedMode = localStorage.getItem("leaderboardMode");
        if (savedMode === "advanced") {
            toggleInput.checked = true;
            isAdvancedMode = true;
        }
        
        // Load initial data
        loadLeaderboard(isAdvancedMode);
        
        // Handle toggle changes
        toggleInput.addEventListener("change", (e) => {
            isAdvancedMode = e.target.checked;
            // Save preference
            localStorage.setItem("leaderboardMode", isAdvancedMode ? "advanced" : "standard");
            // Reload data
            loadLeaderboard(isAdvancedMode);
            // Update legend
            updateLegend();
        });
    } else {
        // Fallback if toggle doesn't exist
        loadLeaderboard(false);
    }

    // Setup legend toggle
    setupLegend();
});

function setupLegend() {
    const legendToggle = document.getElementById("legendToggle");
    const legendContent = document.getElementById("legendContent");
    const legendHeader = document.querySelector(".legend-header");
    
    if (legendToggle && legendContent && legendHeader) {
        // Start collapsed
        legendContent.classList.add("collapsed");
        
        // Toggle on click
        legendHeader.addEventListener("click", () => {
            const isExpanded = legendContent.classList.contains("expanded");
            
            if (isExpanded) {
                legendContent.classList.remove("expanded");
                legendContent.classList.add("collapsed");
                legendToggle.textContent = "▼";
            } else {
                legendContent.classList.remove("collapsed");
                legendContent.classList.add("expanded");
                legendToggle.textContent = "▲";
            }
        });
    }
}

function updateLegend() {
    const legend = document.getElementById("legend");
    const legendContent = document.getElementById("legendContent");
    
    if (!legend || !legendContent) return;
    
    if (isAdvancedMode) {
        // Show legend for advanced mode with abbreviations
        legend.style.display = "block";
        
        // Get headers and map them to descriptions
        const legendEntries = [
            ['Platz', COLUMN_DESCRIPTIONS['Platz']],
            ['Bey', COLUMN_DESCRIPTIONS['Bey']],
            ['ELO', COLUMN_DESCRIPTIONS['ELO']],
            ['Matches', COLUMN_DESCRIPTIONS['Matches']],
            ['Wins', COLUMN_DESCRIPTIONS['Wins']],
            ['Losses', COLUMN_DESCRIPTIONS['Losses']],
            ['Winrate', COLUMN_DESCRIPTIONS['Winrate']],
            ['Pts+', COLUMN_DESCRIPTIONS['Pts+']],
            ['Pts-', COLUMN_DESCRIPTIONS['Pts-']],
            ['AvgΔPts', COLUMN_DESCRIPTIONS['AvgΔPts']],
            ['Vol', COLUMN_DESCRIPTIONS['Vol']],
            ['AvgΔ', COLUMN_DESCRIPTIONS['AvgΔ']],
            ['MaxΔ', COLUMN_DESCRIPTIONS['MaxΔ']],
            ['MinΔ', COLUMN_DESCRIPTIONS['MinΔ']],
            ['U-W', COLUMN_DESCRIPTIONS['U-W']],
            ['U-L', COLUMN_DESCRIPTIONS['U-L']],
            ['Trend', COLUMN_DESCRIPTIONS['Trend']]
        ];
        
        legendContent.innerHTML = legendEntries
            .map(([abbr, desc]) => `
                <div class="legend-item">
                    <div class="legend-abbr">${abbr}</div>
                    <div class="legend-desc">
                        <div class="legend-short">${desc.short}</div>
                        <div class="legend-long">${desc.long}</div>
                    </div>
                </div>
            `).join('');
    } else {
        // Show legend for standard mode
        legend.style.display = "block";
        
        const standardEntries = [
            ['Platz', COLUMN_DESCRIPTIONS['Platz']],
            ['Name', COLUMN_DESCRIPTIONS['Name']],
            ['ELO', COLUMN_DESCRIPTIONS['ELO']],
            ['Spiele', COLUMN_DESCRIPTIONS['Spiele']],
            ['Siege', COLUMN_DESCRIPTIONS['Siege']],
            ['Niederlagen', COLUMN_DESCRIPTIONS['Niederlagen']],
            ['Winrate', COLUMN_DESCRIPTIONS['Winrate']],
            ['Gewonnene Punkte', COLUMN_DESCRIPTIONS['Gewonnene Punkte']],
            ['Verlorene Punkte', COLUMN_DESCRIPTIONS['Verlorene Punkte']],
            ['Differenz', COLUMN_DESCRIPTIONS['Differenz']],
            ['Positionsdelta', COLUMN_DESCRIPTIONS['Positionsdelta']],
            ['ELOdelta', COLUMN_DESCRIPTIONS['ELOdelta']]
        ];
        
        legendContent.innerHTML = standardEntries
            .map(([col, desc]) => `
                <div class="legend-item">
                    <div class="legend-abbr">${col}</div>
                    <div class="legend-desc">
                        <div class="legend-short">${desc.short}</div>
                        <div class="legend-long">${desc.long}</div>
                    </div>
                </div>
            `).join('');
    }
}



function getDeltaClass(value) {
    if (!value) return "delta-neutral";
    
    const strValue = String(value).trim();

    // Handle arrows (for Positionsdelta)
    if (strValue.includes("▲")) return "delta-pos-up";
    if (strValue.includes("▼")) return "delta-pos-down";
    
    // Handle +/- signs (for ELOdelta)
    if (strValue.startsWith("+") || (strValue.match(/^[0-9]/) && !strValue.startsWith("-"))) {
        return "delta-elo-up";
    }
    if (strValue.startsWith("-")) {
        return "delta-elo-down";
    }
    
    return "delta-neutral";
}

function applyDeltaStyling(td, value, type) {
    if (!value) {
        td.classList.add("delta-neutral");
        return;
    }

    if (value.includes("▲") || value.includes("+")) {
        td.classList.add(type === "pos" ? "delta-pos-up" : "delta-elo-up");
    } else if (value.includes("▼") || value.includes("-")) {
        td.classList.add(type === "pos" ? "delta-pos-down" : "delta-elo-down");
    } else {
        td.classList.add("delta-neutral");
    }
}

function applyTrendStyling(element, value) {
    if (!value) {
        element.classList.add("trend-neutral");
        return;
    }

    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
        element.classList.add("trend-neutral");
        return;
    }

    // Apply color based on trend value
    if (numValue > 20) {
        element.classList.add("trend-very-positive");
    } else if (numValue > 0) {
        element.classList.add("trend-positive");
    } else if (numValue < -20) {
        element.classList.add("trend-very-negative");
    } else if (numValue < 0) {
        element.classList.add("trend-negative");
    } else {
        element.classList.add("trend-neutral");
    }
}

function applyWinrateStyling(td, value) {
    if (!value) return;
    const numValue = parseFloat(value.replace("%", ""));
    if (isNaN(numValue)) return;
    if (numValue >= 80) {
        td.classList.add("trend-very-positive");
    } else if (numValue >= 60) {
        td.classList.add("trend-positive");
    } else if (numValue >= 40) {
        td.classList.add("trend-neutral");
    } else if (numValue >= 20) {
        td.classList.add("trend-negative");
    } else {
        td.classList.add("trend-very-negative");
    }
}

function applyVolatilityStyling(td, value) {
    if (!value) return;
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    if (numValue <= 1) {
        td.classList.add("trend-very-positive");
    } else if (numValue <= 3) {
        td.classList.add("trend-positive");
    } else if (numValue <= 5) {
        td.classList.add("trend-neutral");
    } else if (numValue <= 10) {
        td.classList.add("trend-negative");
    } else {
        td.classList.add("trend-very-negative");
    }
}