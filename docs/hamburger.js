// Hamburger menu functionality - shared across all pages
const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

// Detect if we're on mobile
function isMobile() {
    return window.innerWidth <= 768;
}

if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navMenu.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        }
    });

    // Close menu when clicking a link (but not dropdown toggles on mobile)
    navMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            // On mobile, if this is a dropdown toggle, prevent navigation and toggle dropdown
            if (link.hasAttribute('data-dropdown-link') && isMobile()) {
                e.preventDefault();
                const dropdown = link.closest('.nav-dropdown');
                dropdown.classList.toggle('active');
                return;
            }
            // Otherwise, close the menu
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
        });
    });
}
