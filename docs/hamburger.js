// Hamburger menu functionality - shared across all pages
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

// Detect if we're on mobile
function isMobile() {
    return window.innerWidth <= 768;
}

// Close all dropdowns
function closeAllDropdowns() {
    document.querySelectorAll('.nav-dropdown.active').forEach(dropdown => {
        dropdown.classList.remove('active');
    });
}

// Close mobile menu
function closeMobileMenu() {
    if (hamburger && navMenu) {
        hamburger.classList.remove('active');
        navMenu.classList.remove('active');
        closeAllDropdowns();
    }
}

if (hamburger && navMenu) {
    // Toggle menu on hamburger click
    hamburger.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpening = !hamburger.classList.contains('active');
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
        
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
            // On mobile, if this is a dropdown toggle, prevent navigation and toggle dropdown
            if (link.hasAttribute('data-dropdown-link') && isMobile()) {
                e.preventDefault();
                e.stopPropagation();
                const dropdown = link.closest('.nav-dropdown');
                
                // Close other dropdowns first
                document.querySelectorAll('.nav-dropdown.active').forEach(d => {
                    if (d !== dropdown) d.classList.remove('active');
                });
                
                dropdown.classList.toggle('active');
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
    
    // Handle escape key to close menu
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navMenu.classList.contains('active')) {
            closeMobileMenu();
            document.body.style.overflow = '';
            hamburger.focus();
        }
    });
}
