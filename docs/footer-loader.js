// Footer Loader - Load shared footer into all pages
// Replaces any <footer> element (or #site-footer placeholder) with the centralized footer.html content
(function() {
    'use strict';

    function updateFooterYear() {
        const yearEl = document.getElementById('footer-year');
        if (yearEl) {
            yearEl.textContent = new Date().getFullYear();
        }
    }

    function updateVersionDisplay() {
        if (!window.VERSION_INFO) {
            return;
        }
        const versionElement = document.getElementById('site-version');
        if (versionElement) {
            versionElement.textContent = window.VERSION_INFO.getVersionString();
        }
    }

    async function loadFooter() {
        try {
            const response = await fetch('footer.html');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const html = await response.text();

            // Parse the footer HTML
            const temp = document.createElement('div');
            temp.innerHTML = html;
            const newFooter = temp.firstElementChild;
            if (!newFooter) {
                console.warn('Footer content is empty');
                return;
            }

            // Look for an explicit placeholder first
            const placeholder = document.getElementById('site-footer');
            if (placeholder) {
                placeholder.replaceWith(newFooter);
            } else {
                // Otherwise, replace the first existing <footer> element
                const existingFooter = document.querySelector('footer');
                if (existingFooter) {
                    existingFooter.replaceWith(newFooter);
                } else {
                    // No footer present - append before </body>
                    document.body.appendChild(newFooter);
                }
            }

            // Populate dynamic content
            updateFooterYear();
            updateVersionDisplay();
        } catch (error) {
            console.error('Error loading footer:', error);
        }
    }

    // Re-run version update if VERSION_INFO loads after the footer
    document.addEventListener('DOMContentLoaded', () => {
        if (window.VERSION_INFO) {
            updateVersionDisplay();
        } else {
            // Wait a bit in case version.js is still loading
            let attempts = 0;
            const checkInterval = setInterval(() => {
                if (window.VERSION_INFO || attempts >= 20) {
                    clearInterval(checkInterval);
                    updateVersionDisplay();
                }
                attempts++;
            }, 50);
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadFooter);
    } else {
        loadFooter();
    }
})();
