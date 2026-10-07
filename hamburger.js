// Hamburger menu functionality - shared across all pages

// Detect if we're on mobile (based on screen width)
function isMobile() {
    return window.innerWidth <= 768;
}

// Detect if the device is touch-capable
// This detects tablets at desktop breakpoints that still use touch input
function isTouchDevice() {
    return (('ontouchstart' in window) ||
            (navigator.maxTouchPoints > 0) ||
            (navigator.msMaxTouchPoints > 0));
}

// Add touch device class to body for CSS targeting
if (isTouchDevice()) {
    document.body.classList.add('touch-device');
}

// Close all dropdowns
function closeAllDropdowns() {
    document.querySelectorAll('.nav-dropdown.active').forEach(dropdown => {
        dropdown.classList.remove('active');
        const toggle = dropdown.querySelector('.nav-dropdown-toggle');
        if (toggle) {
            toggle.setAttribute('aria-expanded', 'false');
        }
    });
}

// Close mobile menu
function closeMobileMenu() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    if (hamburger && navMenu) {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
        closeAllDropdowns();
    }
}

// Toggle dropdown state with accessibility
function toggleDropdown(dropdown, forceState) {
    const toggle = dropdown.querySelector('.nav-dropdown-toggle');
    const isCurrentlyActive = dropdown.classList.contains('active');
    const shouldBeActive = forceState !== undefined ? forceState : !isCurrentlyActive;
    
    if (shouldBeActive) {
        // Close other dropdowns first
        document.querySelectorAll('.nav-dropdown.active').forEach(d => {
            if (d !== dropdown) {
                d.classList.remove('active');
                const otherToggle = d.querySelector('.nav-dropdown-toggle');
                if (otherToggle) {
                    otherToggle.setAttribute('aria-expanded', 'false');
                }
            }
        });
        dropdown.classList.add('active');
        if (toggle) toggle.setAttribute('aria-expanded', 'true');
    } else {
        dropdown.classList.remove('active');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }
}

// Store handlers so we can remove them before re-adding
let hamburgerClickHandler = null;
let documentClickHandler = null;
let documentKeydownHandler = null;
let windowResizeHandler = null;

// Initialize hamburger menu functionality
function initializeHamburgerMenu() {
    // Get fresh references to elements
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    
    if (!hamburger || !navMenu) {
        return;  // Elements not ready yet
    }
    
    // Remove existing event listeners if they exist
    if (hamburgerClickHandler) {
        hamburger.removeEventListener('click', hamburgerClickHandler);
    }
    if (documentClickHandler) {
        document.removeEventListener('click', documentClickHandler);
    }
    if (documentKeydownHandler) {
        document.removeEventListener('keydown', documentKeydownHandler);
    }
    if (windowResizeHandler) {
        window.removeEventListener('resize', windowResizeHandler);
    }
    
    // Set initial ARIA attributes
    hamburger.setAttribute('aria-expanded', 'false');
    hamburger.setAttribute('aria-controls', 'navMenu');
    navMenu.setAttribute('role', 'navigation');
    navMenu.setAttribute('aria-label', 'Main navigation');
    
    // Set ARIA attributes for dropdowns
    let dropdownCounter = 0;
    document.querySelectorAll('.nav-dropdown').forEach(dropdown => {
        const toggle = dropdown.querySelector('.nav-dropdown-toggle');
        const content = dropdown.querySelector('.nav-dropdown-content');
        if (toggle && content) {
            // Use a counter for reliable unique IDs
            const dropdownId = 'nav-dropdown-' + (++dropdownCounter);
            content.id = dropdownId;
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-haspopup', 'true');
            toggle.setAttribute('aria-controls', dropdownId);
            content.setAttribute('role', 'menu');
            
            // Set role for dropdown items
            content.querySelectorAll('a').forEach(link => {
                link.setAttribute('role', 'menuitem');
            });
        }
    });

    // Toggle menu on hamburger click
    hamburgerClickHandler = (e) => {
        e.stopPropagation();
        const ham = document.getElementById('hamburger');
        const menu = document.getElementById('navMenu');
        if (!ham || !menu) return;
        
        const isOpening = !ham.classList.contains('active');
        ham.classList.toggle('active');
        menu.classList.toggle('active');
        ham.setAttribute('aria-expanded', isOpening ? 'true' : 'false');
        
        // Close dropdowns when closing menu
        if (!isOpening) {
            closeAllDropdowns();
        }
        
        // Prevent body scroll when menu is open on mobile
        if (isMobile()) {
            document.body.style.overflow = isOpening ? 'hidden' : '';
        }
    };
    hamburger.addEventListener('click', hamburgerClickHandler);

    // Close menu when clicking outside
    documentClickHandler = (e) => {
        const ham = document.getElementById('hamburger');
        const menu = document.getElementById('navMenu');
        if (ham && menu && !ham.contains(e.target) && !menu.contains(e.target)) {
            closeMobileMenu();
            document.body.style.overflow = '';
        }
    };
    document.addEventListener('click', documentClickHandler);

    // Handle link clicks
    navMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            // On mobile OR touch devices, if this is a dropdown toggle, 
            // prevent navigation and toggle dropdown
            if (link.hasAttribute('data-dropdown-link') && (isMobile() || isTouchDevice())) {
                e.preventDefault();
                e.stopPropagation();
                const dropdown = link.closest('.nav-dropdown');
                toggleDropdown(dropdown);
                return;
            }
            // Otherwise, close the menu
            closeMobileMenu();
            document.body.style.overflow = '';
        });
    });
    
    // Handle window resize - close menu if resizing to desktop
    windowResizeHandler = () => {
        const menu = document.getElementById('navMenu');
        if (!isMobile() && menu && menu.classList.contains('active')) {
            closeMobileMenu();
            document.body.style.overflow = '';
        }
    };
    window.addEventListener('resize', windowResizeHandler);
    
    // Handle keyboard navigation
    documentKeydownHandler = (e) => {
        const menu = document.getElementById('navMenu');
        const ham = document.getElementById('hamburger');
        
        // Escape key - close menu or dropdown
        if (e.key === 'Escape') {
            if (menu && menu.classList.contains('active')) {
                closeMobileMenu();
                document.body.style.overflow = '';
                if (ham) ham.focus();
            } else {
                // Close any open dropdowns
                closeAllDropdowns();
            }
        }
        
        // Arrow keys for dropdown navigation on desktop
        if (!isMobile() && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
            const activeDropdown = document.querySelector('.nav-dropdown:hover, .nav-dropdown.active');
            if (activeDropdown) {
                const items = activeDropdown.querySelectorAll('.nav-dropdown-content a');
                const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
                
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                    items[nextIndex]?.focus();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                    items[prevIndex]?.focus();
                }
            }
        }
        
        // Enter or Space to toggle dropdown (on mobile or touch devices)
        if ((e.key === 'Enter' || e.key === ' ') && e.target.hasAttribute('data-dropdown-link')) {
            if (isMobile() || isTouchDevice()) {
                e.preventDefault();
                const dropdown = e.target.closest('.nav-dropdown');
                toggleDropdown(dropdown);
            }
        }
    };
    document.addEventListener('keydown', documentKeydownHandler);
    
    // For touch devices at desktop breakpoints: close dropdowns when clicking outside
    if (isTouchDevice()) {
        document.addEventListener('click', (e) => {
            // Early return if no dropdowns are active
            const activeDropdowns = document.querySelectorAll('.nav-dropdown.active');
            if (activeDropdowns.length === 0) {
                return;
            }
            // If not clicking inside a dropdown, close all dropdowns
            if (!e.target.closest('.nav-dropdown')) {
                closeAllDropdowns();
            }
        });
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeHamburgerMenu);
} else {
    initializeHamburgerMenu();
}

// Re-initialize when navigation menu is dynamically loaded
document.addEventListener('navigationLoaded', initializeHamburgerMenu);
