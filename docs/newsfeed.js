// Newsfeed page – loads all news items with search and category filtering

(function () {
    'use strict';

    const categoryConfig = {
        announcement: { label: 'Announcement', emoji: '📢' },
        tournament:   { label: 'Tournament',    emoji: '🏆' },
        match:        { label: 'Match',          emoji: '⚔️' },
        feature:      { label: 'New Feature',   emoji: '✨' },
        system:       { label: 'System',         emoji: '⚙️' }
    };

    function escapeHtml(str) {
        if (typeof str !== 'string') return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function buildSafeLink(link) {
        if (typeof link !== 'string') return '';
        const trimmed = link.trim();
        if (/^https?:\/\//i.test(trimmed)) return trimmed;
        if (trimmed !== '' && !trimmed.includes(':') && !trimmed.startsWith('//')) return trimmed;
        return '';
    }

    function renderItem(item) {
        const cat = categoryConfig[item.category] || { label: escapeHtml(item.category), emoji: '📌' };
        const dateObj = new Date(item.date);
        const formattedDate = dateObj.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        const pinnedBadge = item.pinned ? '<span class="news-pinned-badge">📌 Pinned</span>' : '';
        const safeLink = buildSafeLink(item.link);
        const linkHtml = safeLink
            ? `<a href="${escapeHtml(safeLink)}" class="news-read-more">Read more →</a>`
            : '';

        return `
            <article class="news-item${item.pinned ? ' news-item-pinned' : ''}">
                <div class="news-item-header">
                    <div class="news-item-meta">
                        <span class="news-category-badge news-category-${escapeHtml(item.category)}">${cat.emoji} ${cat.label}</span>
                        <span class="news-date">${formattedDate}</span>
                        ${pinnedBadge}
                    </div>
                    <h3 class="news-item-title">${escapeHtml(item.title)}</h3>
                </div>
                <p class="news-item-content">${escapeHtml(item.content)}</p>
                ${linkHtml}
            </article>
        `;
    }

    let allItems = [];

    function applyFilters() {
        const searchQuery = document.getElementById('newsfeedSearch').value.trim().toLowerCase();
        const categoryFilter = document.getElementById('newsfeedCategoryFilter').value;
        const container = document.getElementById('newsfeedContainer');
        const noResults = document.getElementById('noResultsMessage');

        const filtered = allItems.filter(item => {
            const matchesCategory = categoryFilter === 'all' || item.category === categoryFilter;
            const matchesSearch = !searchQuery
                || item.title.toLowerCase().includes(searchQuery)
                || item.content.toLowerCase().includes(searchQuery);
            return matchesCategory && matchesSearch;
        });

        if (filtered.length === 0) {
            container.innerHTML = '';
            noResults.style.display = 'block';
        } else {
            noResults.style.display = 'none';
            container.innerHTML = filtered.map(renderItem).join('');
        }

        document.getElementById('newsfeedCount').textContent = filtered.length;
    }

    async function loadNewsfeed() {
        const container = document.getElementById('newsfeedContainer');
        try {
            const response = await fetch(DATA_PATHS.NEWSFEED_JSON);
            const data = await response.json();

            const items = data.news || [];

            // Sort: pinned first, then by date descending
            allItems = [...items].sort((a, b) => {
                if (a.pinned && !b.pinned) return -1;
                if (!a.pinned && b.pinned) return 1;
                return new Date(b.date) - new Date(a.date);
            });

            document.getElementById('newsfeedTotal').textContent = allItems.length;
            if (allItems.length > 0) {
                const latestDate = allItems.reduce((max, item) => {
                    const d = new Date(item.date);
                    return d > max ? d : max;
                }, new Date(0));
                document.getElementById('newsfeedLatest').textContent = latestDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
            }

            if (allItems.length === 0) {
                container.innerHTML = '<p class="no-data-text">No news available.</p>';
                return;
            }

            applyFilters();
        } catch (error) {
            console.error('Error loading newsfeed:', error);
            container.innerHTML = '<p class="error-text">Failed to load news.</p>';
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        loadNewsfeed();

        document.getElementById('newsfeedSearch').addEventListener('input', applyFilters);
        document.getElementById('newsfeedCategoryFilter').addEventListener('change', applyFilters);
    });
})();
