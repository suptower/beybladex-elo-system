let leaderboardRows = [];
let leaderboardHeaders = [];
let currentSort = { column: null, asc: true };
let currentSearchQuery = ""; // Track the current search query
let isAdvancedMode = false; // Track which leaderboard is being displayed

// Column abbreviations for advanced mode
const COLUMN_ABBREVIATIONS = {
    'PowerIndex': 'PWR',
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
    'PWR': { short: 'Power Index', long: 'Composite score (0-100) combining ELO (40%), Winrate (25%), Trend (15%), Activity (10%), and Consistency (10%)' },
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
        if (currentSort.column === index) {
            th.classList.add(currentSort.asc ? "sorted-asc" : "sorted-desc");
        }

        // Only make sortable if not the rank column (Platz) in advanced mode or any column in standard mode
        if (!isAdvancedMode || index > 0) {
            th.onclick = () => sortByColumn(index);
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

            // Check if this is the name/bey column and make it a link
            if (h.toLowerCase() === "name" || h.toLowerCase() === "bey") {
                const link = document.createElement("a");
                link.href = `bey.html?name=${encodeURIComponent(value)}`;
                link.className = "bey-link";
                link.textContent = value;
                td.appendChild(link);
            } else {
                // Standard-Text setzen (wird ggf. durch HTML ersetzt bei Cards)
                td.textContent = value;
            }

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

            // Highlight diff
            if (h.toLowerCase().includes("differenz") || h.toLowerCase().includes("pointdiff")) {
                const diff = parseInt(value);
                if (!isNaN(diff)) {
                    if (diff > 0) td.classList.add("trend-very-positive");
                    else if (diff < 0) td.classList.add("trend-very-negative");
                }
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

            // Highlight Power Index (for advanced mode)
            if (h === "PowerIndex" || h.toLowerCase() === "powerindex") {
                applyPowerIndexStyling(td, value);
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
        // make rank gold/silver/bronze for top 3
        if (rank.textContent === "1") rank.classList.add("rank-gold");
        else if (rank.textContent === "2") rank.classList.add("rank-silver");
        else if (rank.textContent === "3") rank.classList.add("rank-bronze");
        
        // Make the name a clickable link
        const nameLink = document.createElement("a");
        nameLink.className = "lb-card-name bey-link";
        const beyNameValue = row["Name"] || row["Bey"] || "Unknown";
        nameLink.textContent = beyNameValue;
        nameLink.href = `bey.html?name=${encodeURIComponent(beyNameValue)}`;
        
        // show ELO and add small text "ELO" below number, also apply elo color coding
        const elo = document.createElement("div");
        elo.className = "lb-card-elo";
        elo.textContent = row["ELO"] || "-";
        // Apply ELO color coding
        const eloValue = parseInt(row["ELO"]);
        if (!isNaN(eloValue)) {
            if (eloValue >= 1050) elo.classList.add("trend-very-positive");
            else if (eloValue >= 1010) elo.classList.add("trend-positive");
            else if (eloValue >= 990) elo.classList.add("trend-neutral");
            else if (eloValue >= 950) elo.classList.add("trend-negative");
            else if (eloValue < 950) elo.classList.add("trend-very-negative");
        }
        const eloLabel = document.createElement("div");
        eloLabel.className = "lb-card-elo-label";
        eloLabel.textContent = "ELO";
        elo.appendChild(eloLabel);
        
        cardHeader.appendChild(rank);
        cardHeader.appendChild(nameLink);
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
        // apply winrate styling via css class
        const winrateStatValue = stats.children[2].querySelector(".lb-stat-value");
        if (winrateStatValue) {
            applyWinrateStyling(winrateStatValue, row["Winrate"] || "0%");
        }
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
            // Add Power Index at the top for advanced mode
            const pwrDetail = createDetail("Power Index", row["PowerIndex"]);
            const pwrValue = pwrDetail.querySelector('.lb-detail-value');
            if (pwrValue && row["PowerIndex"]) {
                applyPowerIndexStyling(pwrValue, row["PowerIndex"]);
            }
            details.appendChild(pwrDetail);
            
            details.appendChild(createDetail("Matches", row["Matches"]));
            details.appendChild(createDetail("Pts For", row["PointsFor"]));
            details.appendChild(createDetail("Pts Against", row["PointsAgainst"]));
            details.appendChild(createDetail("Avg Δ", row["AvgPointDiff"]));
            const volDetail = createDetail("Volatility", row["Volatility"]);
            const volValue = volDetail.querySelector('.lb-detail-value');
            if (volValue && row["Volatility"]) {
                applyVolatilityStyling(volValue, row["Volatility"]);
            }
            details.appendChild(volDetail);
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
            const diffDetail = createDetail("Difference", row["Differenz"]);
            const diffValue = diffDetail.querySelector('.lb-detail-value');
            if (diffValue && row["Differenz"]) {
                const diffNum = parseInt(row["Differenz"]);
                if (!isNaN(diffNum)) {
                    if (diffNum > 0) diffValue.classList.add("trend-very-positive");
                    else if (diffNum < 0) diffValue.classList.add("trend-very-negative");
                }
            }
            details.appendChild(diffDetail);
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


// Shared sorting logic
function performSort(colIndex, asc) {
    const key = leaderboardHeaders[colIndex];

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
}

function sortByColumn(colIndex) {
    const asc = currentSort.column === colIndex ? !currentSort.asc : true;
    currentSort = { column: colIndex, asc };

    performSort(colIndex, asc);
    
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

// Mobile sorting functions
function setupMobileSorting() {
    const sortButton = document.getElementById("mobileSortButton");
    const sortModal = document.getElementById("sortModal");
    const sortModalClose = document.getElementById("sortModalClose");
    const sortModalBody = document.getElementById("sortModalBody");
    
    if (!sortButton || !sortModal || !sortModalClose || !sortModalBody) return;
    
    // Open modal on button click
    sortButton.addEventListener("click", () => {
        openSortModal();
    });
    
    // Close modal on close button click
    sortModalClose.addEventListener("click", () => {
        closeSortModal();
    });
    
    // Close modal when clicking outside
    sortModal.addEventListener("click", (e) => {
        if (e.target === sortModal) {
            closeSortModal();
        }
    });
}

function openSortModal() {
    const sortModal = document.getElementById("sortModal");
    const sortModalBody = document.getElementById("sortModalBody");
    
    if (!sortModal || !sortModalBody) return;
    
    // Generate sort options based on current headers
    sortModalBody.innerHTML = "";
    
    leaderboardHeaders.forEach((header, index) => {
        // Skip rank column in advanced mode (it's calculated, not sortable)
        if (isAdvancedMode && index === 0) return;
        
        const option = document.createElement("div");
        option.className = "sort-option";
        if (currentSort.column === index) {
            option.classList.add("active");
        }
        
        const label = document.createElement("div");
        label.className = "sort-option-label";
        // Use abbreviated header for advanced mode
        label.textContent = (isAdvancedMode && index > 0) ? getAbbreviatedHeader(header) : header;
        
        const directionContainer = document.createElement("div");
        directionContainer.className = "sort-option-direction";
        
        const ascBtn = document.createElement("button");
        ascBtn.className = "direction-btn";
        ascBtn.textContent = "↑";
        ascBtn.title = "Ascending";
        if (currentSort.column === index && currentSort.asc) {
            ascBtn.classList.add("active");
        }
        ascBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, true);
            closeSortModal();
        };
        
        const descBtn = document.createElement("button");
        descBtn.className = "direction-btn";
        descBtn.textContent = "↓";
        descBtn.title = "Descending";
        if (currentSort.column === index && !currentSort.asc) {
            descBtn.classList.add("active");
        }
        descBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, false);
            closeSortModal();
        };
        
        directionContainer.appendChild(ascBtn);
        directionContainer.appendChild(descBtn);
        
        option.appendChild(label);
        option.appendChild(directionContainer);
        
        // Click on option also sorts (with toggle direction)
        option.addEventListener("click", () => {
            const newAsc = currentSort.column === index ? !currentSort.asc : true;
            sortByColumnMobile(index, newAsc);
            closeSortModal();
        });
        
        sortModalBody.appendChild(option);
    });
    
    sortModal.classList.add("active");
}

function closeSortModal() {
    const sortModal = document.getElementById("sortModal");
    if (sortModal) {
        sortModal.classList.remove("active");
    }
}

function sortByColumnMobile(colIndex, asc) {
    currentSort = { column: colIndex, asc };
    performSort(colIndex, asc);
    updateView();
    updateCurrentSortLabel();
}

function updateCurrentSortLabel() {
    const currentSortLabel = document.getElementById("currentSortLabel");
    if (!currentSortLabel || currentSort.column === null) return;
    
    const header = leaderboardHeaders[currentSort.column];
    const displayHeader = (isAdvancedMode && currentSort.column > 0) ? getAbbreviatedHeader(header) : header;
    const direction = currentSort.asc ? "↑" : "↓";
    
    currentSortLabel.textContent = `${displayHeader} ${direction}`;
}

function updateView() {
    const isMobile = window.innerWidth < 900;
    const tableWrapper = document.querySelector(".table-wrapper");
    const cardWrapper = document.getElementById("leaderboardCards");
    const mobileSortControls = document.getElementById("mobileSortControls");

    // Apply current search filter
    const filtered = currentSearchQuery 
        ? leaderboardRows.filter(r =>
            Object.values(r).some(v => String(v).toLowerCase().includes(currentSearchQuery.toLowerCase()))
          )
        : leaderboardRows;

    if (isMobile) {
        tableWrapper.style.display = "none";
        cardWrapper.style.display = "grid";
        if (mobileSortControls) mobileSortControls.style.display = "block";
        renderCards(leaderboardHeaders, filtered);
    } else {
        tableWrapper.style.display = "block";
        cardWrapper.style.display = "none";
        if (mobileSortControls) mobileSortControls.style.display = "none";
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
    
    // Setup mobile sorting
    setupMobileSorting();
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
            ['PWR', COLUMN_DESCRIPTIONS['PWR']],
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

function applyPowerIndexStyling(td, value) {
    if (!value) return;
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    // Power Index ranges from 0-100
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