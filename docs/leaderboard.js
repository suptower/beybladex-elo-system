let leaderboardRows = [];
let leaderboardHeaders = [];
let currentSort = { column: null, asc: true };
let currentSearchQuery = ""; // Track the current search query
let isAdvancedMode = false; // Track which leaderboard is being displayed

function getAbbreviatedHeader(header) {
    const abbreviations = {
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
    return abbreviations[header] || header;
}

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);  // Handle both \n and \r\n
    const headers = lines[0].split(",").map(h => h.trim());

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

    // Add "Platz" column for advanced mode
    const displayHeaders = isAdvancedMode ? ["Platz", ...headers] : headers;

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
            
            // For advanced mode, add rank column
            let value;
            if (isAdvancedMode && colIndex === 0) {
                value = (rowIndex + 1).toString();
            } else {
                value = row[h] ?? "";
            }

            // Standard-Text setzen (wird ggf. durch HTML ersetzt bei Cards)
            td.textContent = value;

            // Highlight ELO
            if (h.toLowerCase() === "elo") {
                const elo = parseInt(value);
                if (!isNaN(elo)) {
                    if (elo >= 1200) td.classList.add("elo-high");
                    else if (elo <= 900) td.classList.add("elo-low");
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
        // Use index+1 for advanced mode since it doesn't have "Platz"
        rank.textContent = row["Platz"] || (index + 1);
        
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
            details.appendChild(createDetail("ELO Trend", row["ELOTrend"]));
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
        
        const abbreviations = {
            'Platz': 'Rank/Position',
            'Bey': 'Beyblade Name',
            'Pts+': 'Points For',
            'Pts-': 'Points Against',
            'AvgΔPts': 'Average Point Difference',
            'Vol': 'Volatility',
            'AvgΔ': 'Average ELO Change',
            'MaxΔ': 'Maximum ELO Change',
            'MinΔ': 'Minimum ELO Change',
            'U-W': 'Upset Wins',
            'U-L': 'Upset Losses',
            'Trend': 'ELO Trend'
        };
        
        legendContent.innerHTML = Object.entries(abbreviations)
            .map(([abbr, full]) => `
                <div class="legend-item">
                    <span class="legend-abbr">${abbr}</span>
                    <span class="legend-full">= ${full}</span>
                </div>
            `).join('');
    } else {
        // Show legend for standard mode
        legend.style.display = "block";
        
        const standardColumns = {
            'Platz': 'Rank/Position',
            'Name': 'Beyblade Name',
            'Spiele': 'Games Played',
            'Siege': 'Wins',
            'Niederlagen': 'Losses',
            'Gewonnene Punkte': 'Points Won',
            'Verlorene Punkte': 'Points Lost',
            'Differenz': 'Point Difference',
            'Positionsdelta': 'Position Change',
            'ELOdelta': 'ELO Change'
        };
        
        legendContent.innerHTML = Object.entries(standardColumns)
            .map(([col, desc]) => `
                <div class="legend-item">
                    <span class="legend-abbr">${col}</span>
                    <span class="legend-full">= ${desc}</span>
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
