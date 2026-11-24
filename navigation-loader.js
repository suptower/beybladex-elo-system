// Navigation Menu Loader - Load shared navigation menu into all pages
(function() {
    'use strict';
    
    // Load the shared navigation menu
    async function loadNavigationMenu() {
        try {
            const response = await fetch('navigation-menu.html');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const html = await response.text();
            
            // Find the existing nav menu placeholder or container
            const navContainer = document.querySelector('nav');
            if (!navContainer) {
                console.warn('Navigation container not found');
                return;
            }
            
            // Find existing nav menu to replace
            const existingNavMenu = navContainer.querySelector('#navMenu');
            if (existingNavMenu) {
                // Create a temporary container to parse the HTML
                const temp = document.createElement('div');
                temp.innerHTML = html;
                const newNavMenu = temp.firstElementChild;
                
                // Replace the old menu with the new one
                existingNavMenu.replaceWith(newNavMenu);
                
                // Dispatch event to notify that navigation has been loaded
                // This allows hamburger.js to reinitialize event listeners
                document.dispatchEvent(new CustomEvent('navigationLoaded'));
            } else {
                console.warn('Nav menu element (#navMenu) not found');
            }
        } catch (error) {
            console.error('Error loading navigation menu:', error);
        }
    }
    
    // Load navigation when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadNavigationMenu);
    } else {
        loadNavigationMenu();
    }
})();
