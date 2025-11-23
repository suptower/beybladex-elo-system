// matches.js - Display match history from CSV
let allMatches = [];
let filteredMatches = [];

// Load matches from CSV
async function loadMatches() {
    try {
        const response = await fetch('data/matches.csv');
        const text = await response.text();
        
        const lines = text.trim().split('\n');
        // Skip the header row
        const headers = lines[0].split(',');
        
        allMatches = lines.slice(1).map(line => {
            const values = line.split(',');
            return {
                date: adaptDate(values[0]),
                beyA: values[1],
                beyB: values[2],
                scoreA: parseInt(values[3]),
                scoreB: parseInt(values[4]),
                winner: parseInt(values[3]) > parseInt(values[4]) ? values[1] : values[2]
            };
        });
        
        // Reverse to show newest first
        // allMatches.reverse();
        filteredMatches = [...allMatches];
        
        populateDateFilter();
        displayMatches();
    } catch (error) {
        console.error('Error loading matches:', error);
        document.getElementById('matchesBody').innerHTML = 
            '<tr><td colspan="6">Error loading matches data</td></tr>';
    }
}

function adaptDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

// Populate date filter dropdown
function populateDateFilter() {
    const dates = [...new Set(allMatches.map(m => m.date))];
    const select = document.getElementById('dateFilter');
    
    dates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = date;
        select.appendChild(option);
    });
    
    select.addEventListener('change', filterMatches);
}

// Filter matches based on search and date
function filterMatches() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const dateFilter = document.getElementById('dateFilter').value;
    
    filteredMatches = allMatches.filter(match => {
        const matchesSearch = !searchTerm || 
            match.beyA.toLowerCase().includes(searchTerm) ||
            match.beyB.toLowerCase().includes(searchTerm) ||
            match.date.includes(searchTerm);
        
        const matchesDate = dateFilter === 'all' || match.date === dateFilter;
        
        return matchesSearch && matchesDate;
    });
    
    displayMatches();
}

// Display matches in table and cards
function displayMatches() {
    const isMobile = window.innerWidth < 900;
    const tbody = document.getElementById('matchesBody');
    const cardsContainer = document.getElementById('matchesCards');
    const tableWrapper = document.querySelector('.table-wrapper');
    
    // Clear existing content
    tbody.innerHTML = '';
    cardsContainer.innerHTML = '';
    
    if (filteredMatches.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No matches found</td></tr>';
        cardsContainer.innerHTML = '<div class="no-results">No matches found</div>';
        return;
    }
    
    // Show/hide based on screen size
    if (isMobile) {
        tableWrapper.style.display = 'none';
        cardsContainer.style.display = 'grid';
    } else {
        tableWrapper.style.display = 'block';
        cardsContainer.style.display = 'none';
    }
    
    // Display table rows (desktop)
    filteredMatches.forEach(match => {
        const row = document.createElement('tr');
        
        const winnerClass = match.winner === match.beyA ? 'winner-a' : 'winner-b';
        
        row.innerHTML = `
            <td>${match.date}</td>
            <td class="${match.winner === match.beyA ? 'winner' : ''}">${match.beyA}</td>
            <td class="${match.winner === match.beyA ? 'score-winner' : ''}">${match.scoreA}</td>
            <td class="${match.winner === match.beyB ? 'score-winner' : ''}">${match.scoreB}</td>
            <td class="${match.winner === match.beyB ? 'winner' : ''}">${match.beyB}</td>
            <td class="match-winner">${match.winner}</td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Display cards (mobile)
    filteredMatches.forEach(match => {
        const card = document.createElement('div');
        card.className = 'card';
        
        card.innerHTML = `
            <div class="card-header">
                <span class="card-date">${match.date}</span>
            </div>
            <div class="card-match">
                <div class="card-bey ${match.winner === match.beyA ? 'winner' : ''}">
                    <div class="bey-name">${match.beyA}</div>
                    <div class="bey-score ${match.winner === match.beyA ? 'score-winner' : ''}">${match.scoreA}</div>
                </div>
                <div class="card-vs">VS</div>
                <div class="card-bey ${match.winner === match.beyB ? 'winner' : ''}">
                    <div class="bey-name">${match.beyB}</div>
                    <div class="bey-score ${match.winner === match.beyB ? 'score-winner' : ''}">${match.scoreB}</div>
                </div>
            </div>
            <div class="card-footer">
                Winner: <strong>${match.winner}</strong>
            </div>
        `;
        
        cardsContainer.appendChild(card);
    });
}

// Search input handler
document.addEventListener('DOMContentLoaded', () => {
    loadMatches();
    
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', filterMatches);
    
    // Add resize event listener to handle responsive view switching
    window.addEventListener('resize', displayMatches);
});
