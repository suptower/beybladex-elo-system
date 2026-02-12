// Navigation enhancements - active page indicators and breadcrumbs
(function() {
    'use strict';
    
    // Get current page path
    const currentPath = window.location.pathname;
    const currentPage = currentPath.split('/').pop() || 'index.html';
    
    // Add active class to current page link in navigation
    function setActiveNavLink() {
        const navLinks = document.querySelectorAll('nav a[href]:not(.nav-dropdown-toggle)');
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage || (currentPage === '' && href === 'index.html')) {
                link.classList.add('active');
                // Also mark parent dropdown as active
                const dropdown = link.closest('.nav-dropdown');
                if (dropdown) {
                    const toggle = dropdown.querySelector('.nav-dropdown-toggle');
                    if (toggle) {
                        toggle.classList.add('active');
                    }
                }
            }
        });
    }
    
    // Generate and insert breadcrumb navigation
    function addBreadcrumbs() {
        // Don't add breadcrumbs on homepage
        if (currentPage === 'index.html' || currentPage === '') {
            return;
        }
        
        // Define page titles and categories
        const pageInfo = {
            // Data pages
            'leaderboard.html': { title: 'Leaderboard', category: 'Data' },
            'wiki.html': { title: 'Wiki', category: 'Data' },
            'beys.html': { title: 'Beys', category: 'Data' },
            'bey.html': { title: 'Bey Details', category: 'Data' },
            'matches.html': { title: 'Matches', category: 'Data' },
            'milestones.html': { title: 'Milestones', category: 'Data' },
            'tournaments.html': { title: 'Tournaments', category: 'Data' },
            'changelog.html': { title: 'Changelog', category: 'Data' },
            'seasons.html': { title: 'Seasons', category: 'Data' },
            'season.html': { title: 'Season Details', category: 'Data' },
            
            // Tools pages
            'compare.html': { title: 'Compare', category: 'Tools' },
            'quick-entry.html': { title: 'Quick Entry', category: 'Tools' },
            'explorer.html': { title: 'Parts Explorer', category: 'Tools' },
            
            // Analytics pages
            'analytics.html': { title: 'Analytics Tools', category: 'Analytics' },
            'plots.html': { title: 'Plots', category: 'Analytics' },
            'upsets.html': { title: 'Upsets', category: 'Analytics' },
            'parts.html': { title: 'Parts', category: 'Misc' },
            'synergy.html': { title: 'Synergy Heatmaps', category: 'Misc' },
            'meta-balance.html': { title: 'Meta Balance', category: 'Analytics' },
            'matchup-matrix.html': { title: 'Matchup Matrix', category: 'Analytics' },
            'archetype-dashboard.html': { title: 'Archetype Dashboard', category: 'Analytics' },
            'recommended-matches.html': { title: 'Recommended Matches', category: 'Analytics' },
            'gallery.html': { title: 'Gallery', category: 'Analytics' },
            
            'counters.html': { title: 'Counters', category: 'Analytics' },
            'simulator.html': { title: 'Simulator', category: 'Misc' },
            'predictor.html': { title: 'Predictor', category: 'Misc' }
        };
        
        const info = pageInfo[currentPage];
        if (!info) {
            return; // Unknown page, skip breadcrumbs
        }
        
        // Create breadcrumb HTML
        const breadcrumbHTML = `
            <nav class="breadcrumb" aria-label="Breadcrumb">
                <a href="index.html">🏠 Home</a>
                <span class="breadcrumb-separator">›</span>
                ${info.category ? `<span class="breadcrumb-current">${info.category}</span>
                <span class="breadcrumb-separator">›</span>` : ''}
                <span class="breadcrumb-current">${info.title}</span>
            </nav>
        `;
        
        // Insert breadcrumb after header, before main content
        const main = document.querySelector('main');
        if (main) {
            main.insertAdjacentHTML('afterbegin', breadcrumbHTML);
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setActiveNavLink();
            addBreadcrumbs();
        });
    } else {
        setActiveNavLink();
        addBreadcrumbs();
    }
})();
