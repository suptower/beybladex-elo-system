let leaderboardRows = [];
let leaderboardHeaders = [];
let currentSort = { column: null, asc: true };

function parseCSV(text) {
    const lines = text.trim().split("\n");
    const headers = lines[0].split(",");

    const rows = lines.slice(1).map(line => {
        const values = line.split(",");
        const obj = {};
        headers.forEach((h, i) => obj[h] = values[i]);
        return obj;
    });

    return { headers, rows };
}

function renderTable(headers, rows) {
    const headRow = document.getElementById("leaderboardHeadRow");
    const body = document.getElementById("leaderboardBody");

    headRow.innerHTML = "";
    body.innerHTML = "";

    // --- Kopfzeile bauen ---
    headers.forEach((h, index) => {
        const th = document.createElement("th");
        th.classList.add("sortable");
        th.textContent = h;

        // Set sort indicator if this is the active column
        if (currentSort.column === index) {
            th.classList.add(currentSort.asc ? "sorted-asc" : "sorted-desc");
        }

        th.onclick = () => sortByColumn(index);
        headRow.appendChild(th);
    });

    // --- Datenzeilen bauen ---
    rows.forEach(row => {
        const tr = document.createElement("tr");

        headers.forEach(h => {
            const td = document.createElement("td");
            const value = row[h] ?? "";

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

    headers.forEach(h => {
        if (h === "Bey") return;

        const div = document.createElement("div");
        div.className = "lb-line";

        let value = row[h];
        let styled = value;

        if (h.toLowerCase().includes("positionsdelta") || h.toLowerCase().includes("elod")) {
            styled = `<span class="${getDeltaClass(value)}">${value}</span>`;
        }

        div.innerHTML = `<strong>${h}:</strong> ${styled}`;
        card.appendChild(div);
    });


    rows.forEach(row => {
        const card = document.createElement("div");
        card.className = "lb-card";

        const title = document.createElement("h3");
        title.textContent = row["Bey"] || "Unbekannt";
        card.appendChild(title);

        headers.forEach(h => {
            if (h === "Bey") return;
            const div = document.createElement("div");
            div.className = "lb-line";
            div.innerHTML = `<strong>${h}:</strong> ${row[h]}`;
            card.appendChild(div);
        });

        container.appendChild(card);
    });
}

function updateView() {
    const isMobile = window.innerWidth < 900;
    const tableWrapper = document.querySelector(".table-wrapper");
    const cardWrapper = document.getElementById("leaderboardCards");

    if (isMobile) {
        tableWrapper.style.display = "none";
        cardWrapper.style.display = "grid";
        renderCards(leaderboardHeaders, leaderboardRows);
    } else {
        tableWrapper.style.display = "block";
        cardWrapper.style.display = "none";
        renderTable(leaderboardHeaders, leaderboardRows);
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
    query = query.toLowerCase();
    const filtered = leaderboardRows.filter(r =>
        Object.values(r).some(v => v.toLowerCase().includes(query))
    );

    if (window.innerWidth < 900) {
        renderCards(leaderboardHeaders, filtered);
    } else {
        renderTable(leaderboardHeaders, filtered);
    }
}

document.getElementById("searchInput").addEventListener("input", e => {
    filterRows(e.target.value);
});

window.addEventListener("resize", updateView);

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("input", e => filterRows(e.target.value));
    }

    window.addEventListener("resize", updateView);

    fetch("./data/leaderboard.csv")
        .then(res => res.text())
        .then(csv => {
            const parsed = parseCSV(csv);
            leaderboardHeaders = parsed.headers;
            leaderboardRows = parsed.rows;
            updateView();
        });
});


function getDeltaClass(value) {
    if (!value) return "delta-neutral";

    if (value.includes("▲")) return "delta-pos-up";
    if (value.includes("▼")) return "delta-pos-down";
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
