// Hamburger menu functionality - shared across all pages
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

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

if (hamburger && navMenu) {
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
    hamburger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpening = !hamburger.classList.contains('active');
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        hamburger.setAttribute('aria-expanded', isOpening ? 'true' : 'false');
        
        // Close dropdowns when closing menu
        if (!isOpening) {
            closeAllDropdowns();
        }
        
        // Prevent body scroll when menu is open on mobile
        if (isMobile()) {
            document.body.style.overflow = isOpening ? 'hidden' : '';
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
            closeMobileMenu();
            document.body.style.overflow = '';
        }
    });

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
    window.addEventListener('resize', () => {
        if (!isMobile() && navMenu.classList.contains('active')) {
            closeMobileMenu();
            document.body.style.overflow = '';
        }
    });
    
    // Handle keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Escape key - close menu or dropdown
        if (e.key === 'Escape') {
            if (navMenu.classList.contains('active')) {
                closeMobileMenu();
                document.body.style.overflow = '';
                hamburger.focus();
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
    });
    
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
