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
    const head = document.getElementById("leaderboardHead");
    const body = document.getElementById("leaderboardBody");

    head.innerHTML = "";
    body.innerHTML = "";

    const trHead = document.createElement("tr");
    headers.forEach((h, i) => {
        const th = document.createElement("th");
        th.textContent = h;

        // sortable
        th.onclick = () => sortByColumn(i);

        trHead.appendChild(th);
    });
    head.appendChild(trHead);

    rows.forEach(row => {
        const tr = document.createElement("tr");
        headers.forEach(h => {
            const td = document.createElement("td");
            td.textContent = row[h];

            // Color highlights
            if (h.toLowerCase() === "elo") {
                const elo = parseInt(row[h]);
                if (!isNaN(elo)) {
                    if (elo >= 1200) td.classList.add("elo-high");
                    else if (elo <= 900) td.classList.add("elo-low");
                }
            }

            tr.appendChild(td);
        });
        body.appendChild(tr);
    });
}

function renderCards(headers, rows) {
    const container = document.getElementById("leaderboardCards");
    container.innerHTML = "";

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

function sortByColumn(colIndex) {
    const key = leaderboardHeaders[colIndex];

    const asc = currentSort.column === colIndex ? !currentSort.asc : true;
    currentSort = { column: colIndex, asc };

    leaderboardRows.sort((a, b) => {
        const v1 = a[key];
        const v2 = b[key];

        const n1 = parseFloat(v1);
        const n2 = parseFloat(v2);

        // numeric sort if applicable
        if (!isNaN(n1) && !isNaN(n2)) {
            return asc ? n1 - n2 : n2 - n1;
        }
        return asc
            ? v1.localeCompare(v2)
            : v2.localeCompare(v1);
    });

    updateView();
}

function filterRows(query) {
    query = query.toLowerCase();
    const filtered = leaderboardRows.filter(r =>
        Object.values(r).some(v =>
            v.toLowerCase().includes(query)
        )
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

fetch("./data/leaderboard.csv")
    .then(res => res.text())
    .then(csv => {
        const parsed = parseCSV(csv);
        leaderboardHeaders = parsed.headers;
        leaderboardRows = parsed.rows;
        updateView();
    });
