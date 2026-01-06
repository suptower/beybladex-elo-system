/**
 * Changelog Page JavaScript
 * Loads and displays commit history from changelog.json
 */

let allCommits = [];
let filteredCommits = [];

// Category emoji mapping
const categoryEmojis = {
    'Feature': '✨',
    'Fix': '🐛',
    'Balance': '⚖️',
    'UI': '🎨',
    'Documentation': '📝',
    'Performance': '⚡',
    'Refactor': '♻️',
    'Data': '📊',
    'Test': '✅',
    'Build': '🔧',
    'CI': '🤖',
    'Style': '💄',
    'Chore': '🔨',
    'Other': '📦'
};

/**
 * Initialize the changelog page
 */
async function initChangelog() {
    try {
        const response = await fetch('data/changelog.json');
        if (!response.ok) {
            throw new Error('Failed to load changelog data');
        }

        const data = await response.json();
        allCommits = data.commits;
        filteredCommits = [...allCommits];

        updateStats(data);
        renderCommits(filteredCommits);
        setupEventListeners();
    } catch (error) {
        console.error('Error loading changelog:', error);
        showError('Failed to load changelog. Please try again later.');
    }
}

/**
 * Update statistics display
 */
function updateStats(data) {
    document.getElementById('totalCommits').textContent = data.commit_count;

    // Format last updated time
    const lastUpdated = new Date(data.generated_at);
    const formattedDate = lastUpdated.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    document.getElementById('lastUpdated').textContent = formattedDate;
}

/**
 * Render commit entries
 */
function renderCommits(commits) {
    const container = document.getElementById('changelogContainer');
    const noResultsMessage = document.getElementById('noResultsMessage');

    if (commits.length === 0) {
        container.style.display = 'none';
        noResultsMessage.style.display = 'block';
        return;
    }

    container.style.display = 'flex';
    noResultsMessage.style.display = 'none';

    container.innerHTML = commits.map(commit => createCommitEntry(commit)).join('');
}

/**
 * Create HTML for a single commit entry
 */
function createCommitEntry(commit) {
    const date = new Date(commit.date);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });

    const emoji = categoryEmojis[commit.category] || '📦';
    
    return `
        <div class="commit-entry" data-category="${commit.category}">
            <div class="commit-header">
                <div class="commit-message">${escapeHtml(commit.message)}</div>
                <div class="commit-category">${emoji} ${commit.category}</div>
            </div>
            <div class="commit-meta">
                <div class="commit-date">
                    <span>📅</span>
                    <span>${formattedDate}</span>
                </div>
                <div class="commit-author">
                    <span>👤</span>
                    <span>${escapeHtml(commit.author)}</span>
                </div>
                <div class="commit-hash">
                    <a href="${commit.github_url}" target="_blank" rel="noopener" class="commit-link">
                        ${commit.hash}
                    </a>
                </div>
            </div>
        </div>
    `;
}

/**
 * Setup event listeners for filters and search
 */
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');

    searchInput.addEventListener('input', applyFilters);
    categoryFilter.addEventListener('change', applyFilters);
}

/**
 * Apply filters and search to commits
 */
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;

    filteredCommits = allCommits.filter(commit => {
        // Apply search filter
        const matchesSearch = 
            commit.message.toLowerCase().includes(searchTerm) ||
            commit.author.toLowerCase().includes(searchTerm) ||
            commit.hash.toLowerCase().includes(searchTerm);

        // Apply category filter
        const matchesCategory = 
            categoryFilter === 'all' || 
            commit.category === categoryFilter;

        return matchesSearch && matchesCategory;
    });

    renderCommits(filteredCommits);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error message
 */
function showError(message) {
    const container = document.getElementById('changelogContainer');
    container.innerHTML = `
        <div class="error-message" style="
            text-align: center;
            padding: 3rem;
            color: var(--text-light);
            background: var(--card);
            border-radius: var(--radius);
        ">
            <p style="font-size: 1.2rem; margin-bottom: 1rem;">⚠️ ${message}</p>
        </div>
    `;
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChangelog);
} else {
    initChangelog();
}
