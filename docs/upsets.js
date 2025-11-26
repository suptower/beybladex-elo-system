// upsets.js - Display upset analysis from CSV
let upsetRows = [];
let upsetHeaders = [];
let matchRows = [];
let matchHeaders = [];
let currentSort = { column: null, asc: true };
let currentSearchQuery = "";
let isMatchesMode = false; // false = Giant Killers, true = Biggest Upsets

// Column abbreviations for Giant Killers view
const COLUMN_ABBREVIATIONS = {
    'GiantKillerScore': 'GK',
    'UpsetWins': 'U-W',
    'UpsetLosses': 'U-L',
    'UpsetRate': 'U-Rate',
    'Vulnerability': 'Vuln',
    'AvgUpsetWinMagnitude': 'AvgMag+',
    'AvgUpsetLossMagnitude': 'AvgMag-',
    'BiggestUpsetWin': 'MaxU+',
    'BiggestUpsetLoss': 'MaxU-'
};

// Full descriptions for legend
const COLUMN_DESCRIPTIONS = {
    'Rank': { short: 'Rank', long: 'Current ranking position based on Giant Killer Score' },
    'Bey': { short: 'Beyblade Name', long: 'Name of the Beyblade' },
    'ELO': { short: 'ELO Rating', long: 'Current ELO rating' },
    'GK': { short: 'Giant Killer Score', long: 'Composite score (0-100) measuring ability to defeat stronger opponents: Upset Win Rate (35%), Upset Frequency (25%), Avg Magnitude (25%), Total Upsets (15%)' },
    'Matches': { short: 'Games Played', long: 'Total number of matches played' },
    'Wins': { short: 'Wins', long: 'Total number of wins' },
    'Losses': { short: 'Losses', long: 'Total number of losses' },
    'U-W': { short: 'Upset Wins', long: 'Wins against higher-rated opponents' },
    'U-L': { short: 'Upset Losses', long: 'Losses against lower-rated opponents' },
    'U-Rate': { short: 'Upset Rate', long: 'Percentage of wins that are upsets' },
    'Vuln': { short: 'Vulnerability', long: 'Percentage of losses that are upsets (lost to lower-rated)' },
    'AvgMag+': { short: 'Avg Upset Win Magnitude', long: 'Average ELO difference overcome in upset wins' },
    'AvgMag-': { short: 'Avg Upset Loss Magnitude', long: 'Average ELO difference in upset losses' },
    'MaxU+': { short: 'Biggest Upset Win', long: 'Largest ELO difference overcome in a single win' },
    'MaxU-': { short: 'Biggest Upset Loss', long: 'Largest ELO difference in a single upset loss' },
    // Match view columns
    'Date': { short: 'Date', long: 'Date of the match' },
    'Winner': { short: 'Winner', long: 'The Beyblade that won the upset match' },
    'Loser': { short: 'Loser', long: 'The Beyblade that lost the upset match' },
    'WinnerPreELO': { short: 'Winner Pre-ELO', long: 'Winner\'s ELO rating before the match' },
    'LoserPreELO': { short: 'Loser Pre-ELO', long: 'Loser\'s ELO rating before the match' },
    'ELODifference': { short: 'ELO Difference', long: 'How much higher the loser\'s ELO was compared to the winner' },
    'Score': { short: 'Score', long: 'Final match score' }
};

function getAbbreviatedHeader(header) {
    return COLUMN_ABBREVIATIONS[header] || header;
}

// Get display info for the value shown in mobile card header
// When sorting by a non-GK column, show that column's value instead
function getCardHeaderDisplayInfo(row) {
    const headers = isMatchesMode ? matchHeaders : upsetHeaders;
    
    // Default to showing GK Score for Giant Killers, ELO Difference for Matches
    let displayValue = isMatchesMode ? (row["ELODifference"] || "-") : (row["GiantKillerScore"] || "0");
    let displayLabel = isMatchesMode ? "ELO Diff" : "GK Score";
    let sortedColumn = null;

    // Check if we're sorting by a column other than the default
    if (currentSort.column !== null) {
        sortedColumn = headers[currentSort.column];
        
        // If not sorting by the default column or name columns, show the sorted column
        if (sortedColumn && 
            sortedColumn !== "GiantKillerScore" && 
            sortedColumn !== "ELODifference" &&
            sortedColumn !== "Bey" && 
            sortedColumn !== "Winner" &&
            sortedColumn !== "Loser" &&
            sortedColumn !== "Rank") {
            displayValue = row[sortedColumn] || "-";
            displayLabel = getAbbreviatedHeader(sortedColumn);
        }
    }

    return { displayValue, displayLabel, sortedColumn };
}

// Apply appropriate styling for a value based on its column type
function applyValueStyling(element, value, columnName) {
    if (!value || !columnName) return;

    const col = columnName.toLowerCase();
    
    if (col === "giantkillerscore") {
        applyGiantKillerStyling(element, value);
    } else if (col === "elo") {
        const eloValue = parseInt(value);
        if (!isNaN(eloValue)) {
            if (eloValue >= 1050) element.classList.add("trend-very-positive");
            else if (eloValue >= 1010) element.classList.add("trend-positive");
            else if (eloValue >= 990) element.classList.add("trend-neutral");
            else if (eloValue >= 950) element.classList.add("trend-negative");
            else if (eloValue < 950) element.classList.add("trend-very-negative");
        }
    } else if (col === "elodifference") {
        const diff = parseFloat(value);
        if (!isNaN(diff)) {
            if (diff >= 50) element.classList.add("trend-very-positive");
            else if (diff >= 30) element.classList.add("trend-positive");
            else if (diff >= 15) element.classList.add("trend-neutral");
            else element.classList.add("trend-negative");
        }
    } else if (col === "upsetrate" || col === "vulnerability") {
        const numValue = parseFloat(value.replace("%", ""));
        if (!isNaN(numValue)) {
            if (numValue >= 80) element.classList.add("trend-very-positive");
            else if (numValue >= 60) element.classList.add("trend-positive");
            else if (numValue >= 40) element.classList.add("trend-neutral");
            else if (numValue >= 20) element.classList.add("trend-negative");
            else element.classList.add("trend-very-negative");
        }
    }
}

function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = lines[0].split(",").map(h => h.trim());
    const rows = lines.slice(1).map(line => {
        const values = line.split(",").map(v => v.trim());
        const obj = {};
        headers.forEach((h, i) => obj[h] = values[i]);
        return obj;
    });
    return { headers, rows };
}

function loadUpsetAnalysis() {
    fetch("./data/upset_analysis.csv")
        .then(res => res.text())
        .then(csv => {
            const parsed = parseCSV(csv);
            upsetHeaders = parsed.headers;
            upsetRows = parsed.rows;
            if (!isMatchesMode) {
                currentSort = { column: null, asc: true };
                updateView();
                updateLegend();
                updateSummaryCards();
            }
        })
        .catch(err => console.error("Error loading upset analysis:", err));
}

function loadUpsetMatches() {
    fetch("./data/upset_matches.csv")
        .then(res => res.text())
        .then(csv => {
            const parsed = parseCSV(csv);
            matchHeaders = parsed.headers;
            matchRows = parsed.rows;
            if (isMatchesMode) {
                currentSort = { column: null, asc: true };
                updateView();
                updateLegend();
                updateSummaryCards();
            }
        })
        .catch(err => console.error("Error loading upset matches:", err));
}

function updateSummaryCards() {
    const container = document.getElementById("summaryCards");
    if (!container) return;

    if (!isMatchesMode && upsetRows.length > 0) {
        // Giant Killers summary
        const topGiantKiller = upsetRows.reduce((max, row) => 
            parseFloat(row.GiantKillerScore) > parseFloat(max.GiantKillerScore) ? row : max
        );
        const totalUpsetWins = upsetRows.reduce((sum, row) => sum + parseInt(row.UpsetWins || 0), 0);
        const avgGKScore = (upsetRows.reduce((sum, row) => sum + parseFloat(row.GiantKillerScore || 0), 0) / upsetRows.length).toFixed(1);
        
        container.innerHTML = `
            <div class="summary-card">
                <div class="summary-icon">🏆</div>
                <div class="summary-content">
                    <div class="summary-value">${topGiantKiller.Bey}</div>
                    <div class="summary-label">Top Giant Killer (Score: ${topGiantKiller.GiantKillerScore})</div>
                </div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">⚡</div>
                <div class="summary-content">
                    <div class="summary-value">${totalUpsetWins}</div>
                    <div class="summary-label">Total Upset Wins</div>
                </div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">📊</div>
                <div class="summary-content">
                    <div class="summary-value">${avgGKScore}</div>
                    <div class="summary-label">Average GK Score</div>
                </div>
            </div>
        `;
    } else if (isMatchesMode && matchRows.length > 0) {
        // Biggest Upsets summary
        const biggestUpset = matchRows[0]; // Already sorted by magnitude
        const totalUpsets = matchRows.length;
        const avgMagnitude = (matchRows.reduce((sum, row) => sum + parseFloat(row.ELODifference || 0), 0) / matchRows.length).toFixed(1);
        
        container.innerHTML = `
            <div class="summary-card">
                <div class="summary-icon">💥</div>
                <div class="summary-content">
                    <div class="summary-value">${biggestUpset.Winner} vs ${biggestUpset.Loser}</div>
                    <div class="summary-label">Biggest Upset (${biggestUpset.ELODifference} ELO diff)</div>
                </div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">🎯</div>
                <div class="summary-content">
                    <div class="summary-value">${totalUpsets}</div>
                    <div class="summary-label">Total Upsets Recorded</div>
                </div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">📈</div>
                <div class="summary-content">
                    <div class="summary-value">${avgMagnitude}</div>
                    <div class="summary-label">Average ELO Difference</div>
                </div>
            </div>
        `;
    }
}

function renderTable(headers, rows) {
    const headRow = document.getElementById("upsetsHeadRow");
    const body = document.getElementById("upsetsBody");

    headRow.innerHTML = "";
    body.innerHTML = "";

    headers.forEach((h, index) => {
        const th = document.createElement("th");
        th.classList.add("sortable");
        th.textContent = getAbbreviatedHeader(h);
        
        if (currentSort.column === index) {
            th.classList.add(currentSort.asc ? "sorted-asc" : "sorted-desc");
        }

        th.onclick = () => sortByColumn(index);
        headRow.appendChild(th);
    });

    rows.forEach(row => {
        const tr = document.createElement("tr");

        headers.forEach(h => {
            const td = document.createElement("td");
            const value = row[h] ?? "";

            // Make bey names clickable
            if (h === "Bey" || h === "Winner" || h === "Loser") {
                const link = document.createElement("a");
                link.href = `bey.html?name=${encodeURIComponent(value)}`;
                link.className = "bey-link";
                link.textContent = value;
                td.appendChild(link);
            } else {
                td.textContent = value;
            }

            // Styling for Giant Killer Score
            if (h === "GiantKillerScore") {
                applyGiantKillerStyling(td, value);
            }

            // Styling for ELO
            if (h === "ELO") {
                const elo = parseInt(value);
                if (!isNaN(elo)) {
                    if (elo >= 1050) td.classList.add("trend-very-positive");
                    else if (elo >= 1010) td.classList.add("trend-positive");
                    else if (elo >= 990) td.classList.add("trend-neutral");
                    else if (elo >= 950) td.classList.add("trend-negative");
                    else td.classList.add("trend-very-negative");
                }
            }

            // Styling for ELO Difference (in matches view)
            if (h === "ELODifference") {
                const diff = parseFloat(value);
                if (!isNaN(diff)) {
                    if (diff >= 50) td.classList.add("trend-very-positive");
                    else if (diff >= 30) td.classList.add("trend-positive");
                    else if (diff >= 15) td.classList.add("trend-neutral");
                    else td.classList.add("trend-negative");
                }
            }

            tr.appendChild(td);
        });

        body.appendChild(tr);
    });
}

function renderCards(headers, rows) {
    const container = document.getElementById("upsetsCards");
    container.innerHTML = "";

    if (!isMatchesMode) {
        // Giant Killers cards
        rows.forEach(row => {
            const card = document.createElement("div");
            card.className = "lb-card";

            const cardHeader = document.createElement("div");
            cardHeader.className = "lb-card-header";
            
            const rank = document.createElement("div");
            rank.className = "lb-card-rank";
            rank.textContent = row["Rank"] || "-";
            if (rank.textContent === "1") rank.classList.add("rank-gold");
            else if (rank.textContent === "2") rank.classList.add("rank-silver");
            else if (rank.textContent === "3") rank.classList.add("rank-bronze");
            
            const nameLink = document.createElement("a");
            nameLink.className = "lb-card-name bey-link";
            nameLink.textContent = row["Bey"] || "Unknown";
            nameLink.href = `bey.html?name=${encodeURIComponent(row["Bey"])}`;
            
            // Get the value to display in header (GK Score by default, or sorted column value)
            const headerInfo = getCardHeaderDisplayInfo(row);
            
            const headerValue = document.createElement("div");
            headerValue.className = "lb-card-elo";
            headerValue.textContent = headerInfo.displayValue;
            // Apply appropriate styling based on the column being displayed
            applyValueStyling(headerValue, headerInfo.displayValue, headerInfo.sortedColumn || "GiantKillerScore");
            const headerLabel = document.createElement("div");
            headerLabel.className = "lb-card-elo-label";
            headerLabel.textContent = headerInfo.displayLabel;
            headerValue.appendChild(headerLabel);
            
            cardHeader.appendChild(rank);
            cardHeader.appendChild(nameLink);
            cardHeader.appendChild(headerValue);
            card.appendChild(cardHeader);

            // Stats row
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
            
            stats.appendChild(createStat("Upset Wins", row["UpsetWins"] || "0"));
            stats.appendChild(createStat("Upset Rate", row["UpsetRate"] || "0%"));
            stats.appendChild(createStat("ELO", row["ELO"] || "-"));
            card.appendChild(stats);

            // Expandable details
            const expandSection = document.createElement("div");
            expandSection.className = "lb-card-expand";
            
            const details = document.createElement("div");
            details.className = "lb-card-details";
            
            const createDetail = (label, value, columnName) => {
                const detail = document.createElement("div");
                detail.className = "lb-detail";
                const detailLabel = document.createElement("span");
                detailLabel.className = "lb-detail-label";
                detailLabel.textContent = label;
                const detailValue = document.createElement("span");
                detailValue.className = "lb-detail-value";
                detailValue.textContent = value || "-";
                // Apply styling to the detail value
                if (columnName) {
                    applyValueStyling(detailValue, value, columnName);
                }
                detail.appendChild(detailLabel);
                detail.appendChild(detailValue);
                return detail;
            };
            
            // If sorting by non-GK column, add GK Score to the details section first
            if (headerInfo.sortedColumn && headerInfo.sortedColumn !== "GiantKillerScore") {
                const gkDetail = createDetail("GK Score", row["GiantKillerScore"], "GiantKillerScore");
                details.appendChild(gkDetail);
            }
            
            if (headerInfo.sortedColumn !== "Matches") {
                details.appendChild(createDetail("Matches", row["Matches"]));
            }
            if (headerInfo.sortedColumn !== "Wins") {
                details.appendChild(createDetail("Wins", row["Wins"]));
            }
            if (headerInfo.sortedColumn !== "Losses") {
                details.appendChild(createDetail("Losses", row["Losses"]));
            }
            if (headerInfo.sortedColumn !== "UpsetLosses") {
                details.appendChild(createDetail("Upset Losses", row["UpsetLosses"]));
            }
            if (headerInfo.sortedColumn !== "Vulnerability") {
                details.appendChild(createDetail("Vulnerability", row["Vulnerability"], "Vulnerability"));
            }
            if (headerInfo.sortedColumn !== "AvgUpsetWinMagnitude") {
                details.appendChild(createDetail("Avg Upset Mag", row["AvgUpsetWinMagnitude"]));
            }
            if (headerInfo.sortedColumn !== "BiggestUpsetWin") {
                details.appendChild(createDetail("Biggest Upset", row["BiggestUpsetWin"]));
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
    } else {
        // Biggest Upsets cards
        rows.forEach(row => {
            const card = document.createElement("div");
            card.className = "card upset-match-card";
            
            card.innerHTML = `
                <div class="card-header">
                    <span class="card-date">${row["Date"] || ""}</span>
                    <span class="upset-magnitude">+${row["ELODifference"]} ELO</span>
                </div>
                <div class="card-match">
                    <div class="card-bey winner">
                        <div class="bey-name"><a href="bey.html?name=${encodeURIComponent(row["Winner"])}" class="bey-link">${row["Winner"]}</a></div>
                        <div class="bey-elo">${row["WinnerPreELO"]} ELO</div>
                    </div>
                    <div class="card-vs">beat</div>
                    <div class="card-bey loser">
                        <div class="bey-name"><a href="bey.html?name=${encodeURIComponent(row["Loser"])}" class="bey-link">${row["Loser"]}</a></div>
                        <div class="bey-elo">${row["LoserPreELO"]} ELO</div>
                    </div>
                </div>
                <div class="card-footer">
                    Score: <strong>${row["Score"]}</strong>
                </div>
            `;
            
            container.appendChild(card);
        });
    }
}

function applyGiantKillerStyling(element, value) {
    if (!value) return;
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    
    if (numValue >= 70) {
        element.classList.add("trend-very-positive");
    } else if (numValue >= 50) {
        element.classList.add("trend-positive");
    } else if (numValue >= 30) {
        element.classList.add("trend-neutral");
    } else if (numValue >= 10) {
        element.classList.add("trend-negative");
    } else {
        element.classList.add("trend-very-negative");
    }
}

function performSort(colIndex, asc) {
    const headers = isMatchesMode ? matchHeaders : upsetHeaders;
    const rows = isMatchesMode ? matchRows : upsetRows;
    const key = headers[colIndex];

    rows.sort((a, b) => {
        const raw1 = a[key];
        const raw2 = b[key];

        const n1 = parseFloat(raw1);
        const n2 = parseFloat(raw2);

        if (!isNaN(n1) && !isNaN(n2)) {
            return asc ? n1 - n2 : n2 - n1;
        }

        return asc ? raw1.localeCompare(raw2) : raw2.localeCompare(raw1);
    });
}

function sortByColumn(colIndex) {
    const asc = currentSort.column === colIndex ? !currentSort.asc : true;
    currentSort = { column: colIndex, asc };

    performSort(colIndex, asc);
    updateView();
}

function filterRows(query) {
    currentSearchQuery = query;
    updateView();
}

function updateView() {
    const isMobile = window.innerWidth < 900;
    const tableWrapper = document.querySelector(".table-wrapper");
    const cardWrapper = document.getElementById("upsetsCards");
    const mobileSortControls = document.getElementById("mobileSortControls");

    const headers = isMatchesMode ? matchHeaders : upsetHeaders;
    const allRows = isMatchesMode ? matchRows : upsetRows;
    
    // Apply search filter
    const filtered = currentSearchQuery 
        ? allRows.filter(r =>
            Object.values(r).some(v => String(v).toLowerCase().includes(currentSearchQuery.toLowerCase()))
          )
        : allRows;

    if (isMobile) {
        tableWrapper.style.display = "none";
        cardWrapper.style.display = "grid";
        if (mobileSortControls) mobileSortControls.style.display = "block";
        renderCards(headers, filtered);
    } else {
        tableWrapper.style.display = "block";
        cardWrapper.style.display = "none";
        if (mobileSortControls) mobileSortControls.style.display = "none";
        renderTable(headers, filtered);
    }
}

function updateLegend() {
    const legend = document.getElementById("legend");
    const legendContent = document.getElementById("legendContent");
    
    if (!legend || !legendContent) return;

    legend.style.display = "block";
    
    let legendEntries;
    if (!isMatchesMode) {
        // Giant Killers legend
        legendEntries = [
            ['Rank', COLUMN_DESCRIPTIONS['Rank']],
            ['Bey', COLUMN_DESCRIPTIONS['Bey']],
            ['ELO', COLUMN_DESCRIPTIONS['ELO']],
            ['GK', COLUMN_DESCRIPTIONS['GK']],
            ['Matches', COLUMN_DESCRIPTIONS['Matches']],
            ['Wins', COLUMN_DESCRIPTIONS['Wins']],
            ['Losses', COLUMN_DESCRIPTIONS['Losses']],
            ['U-W', COLUMN_DESCRIPTIONS['U-W']],
            ['U-L', COLUMN_DESCRIPTIONS['U-L']],
            ['U-Rate', COLUMN_DESCRIPTIONS['U-Rate']],
            ['Vuln', COLUMN_DESCRIPTIONS['Vuln']],
            ['AvgMag+', COLUMN_DESCRIPTIONS['AvgMag+']],
            ['AvgMag-', COLUMN_DESCRIPTIONS['AvgMag-']],
            ['MaxU+', COLUMN_DESCRIPTIONS['MaxU+']],
            ['MaxU-', COLUMN_DESCRIPTIONS['MaxU-']]
        ];
    } else {
        // Biggest Upsets legend
        legendEntries = [
            ['Rank', COLUMN_DESCRIPTIONS['Rank']],
            ['Date', COLUMN_DESCRIPTIONS['Date']],
            ['Winner', COLUMN_DESCRIPTIONS['Winner']],
            ['Loser', COLUMN_DESCRIPTIONS['Loser']],
            ['WinnerPreELO', COLUMN_DESCRIPTIONS['WinnerPreELO']],
            ['LoserPreELO', COLUMN_DESCRIPTIONS['LoserPreELO']],
            ['ELODifference', COLUMN_DESCRIPTIONS['ELODifference']],
            ['Score', COLUMN_DESCRIPTIONS['Score']]
        ];
    }
    
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
}

function setupLegend() {
    const legendToggle = document.getElementById("legendToggle");
    const legendContent = document.getElementById("legendContent");
    const legendHeader = document.querySelector(".legend-header");
    
    if (legendToggle && legendContent && legendHeader) {
        legendContent.classList.add("collapsed");
        
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

// Mobile sorting
function setupMobileSorting() {
    const sortButton = document.getElementById("mobileSortButton");
    const sortModal = document.getElementById("sortModal");
    const sortModalClose = document.getElementById("sortModalClose");
    
    if (!sortButton || !sortModal || !sortModalClose) return;
    
    sortButton.addEventListener("click", openSortModal);
    sortModalClose.addEventListener("click", closeSortModal);
    sortModal.addEventListener("click", (e) => {
        if (e.target === sortModal) closeSortModal();
    });
}

function openSortModal() {
    const sortModal = document.getElementById("sortModal");
    const sortModalBody = document.getElementById("sortModalBody");
    
    if (!sortModal || !sortModalBody) return;
    
    const headers = isMatchesMode ? matchHeaders : upsetHeaders;
    sortModalBody.innerHTML = "";
    
    headers.forEach((header, index) => {
        const option = document.createElement("div");
        option.className = "sort-option";
        if (currentSort.column === index) option.classList.add("active");
        
        const label = document.createElement("div");
        label.className = "sort-option-label";
        label.textContent = getAbbreviatedHeader(header);
        
        const directionContainer = document.createElement("div");
        directionContainer.className = "sort-option-direction";
        
        const ascBtn = document.createElement("button");
        ascBtn.className = "direction-btn";
        ascBtn.textContent = "↑";
        if (currentSort.column === index && currentSort.asc) ascBtn.classList.add("active");
        ascBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, true);
            closeSortModal();
        };
        
        const descBtn = document.createElement("button");
        descBtn.className = "direction-btn";
        descBtn.textContent = "↓";
        if (currentSort.column === index && !currentSort.asc) descBtn.classList.add("active");
        descBtn.onclick = (e) => {
            e.stopPropagation();
            sortByColumnMobile(index, false);
            closeSortModal();
        };
        
        directionContainer.appendChild(ascBtn);
        directionContainer.appendChild(descBtn);
        
        option.appendChild(label);
        option.appendChild(directionContainer);
        
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
    if (sortModal) sortModal.classList.remove("active");
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
    
    const headers = isMatchesMode ? matchHeaders : upsetHeaders;
    const header = headers[currentSort.column];
    const displayHeader = getAbbreviatedHeader(header);
    const direction = currentSort.asc ? "↑" : "↓";
    
    currentSortLabel.textContent = `${displayHeader} ${direction}`;
}

window.addEventListener("resize", updateView);

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", e => filterRows(e.target.value));
    }

    const toggleInput = document.getElementById("upsetToggle");
    if (toggleInput) {
        // Load saved preference
        const savedMode = localStorage.getItem("upsetMode");
        if (savedMode === "matches") {
            toggleInput.checked = true;
            isMatchesMode = true;
        }
        
        // Load both datasets
        loadUpsetAnalysis();
        loadUpsetMatches();
        
        // Handle toggle changes
        toggleInput.addEventListener("change", (e) => {
            isMatchesMode = e.target.checked;
            localStorage.setItem("upsetMode", isMatchesMode ? "matches" : "giantkillers");
            currentSort = { column: null, asc: true };
            updateView();
            updateLegend();
            updateSummaryCards();
        });
    } else {
        loadUpsetAnalysis();
        loadUpsetMatches();
    }

    setupLegend();
    setupMobileSorting();
});
