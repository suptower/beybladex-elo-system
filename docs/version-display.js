// Auto-inject version information into footer
// This script should be loaded in all HTML pages after version.js

(function() {
    function updateVersionDisplay() {
        if (!window.VERSION_INFO) {
            console.debug('VERSION_INFO not loaded yet');
            return;
        }
        
        const versionElement = document.getElementById('site-version');
        if (versionElement) {
            versionElement.textContent = window.VERSION_INFO.getVersionString();
        }
    }
    
    // Try to update immediately if VERSION_INFO is already loaded
    if (window.VERSION_INFO) {
        updateVersionDisplay();
    }
    
    // Also update on DOMContentLoaded to ensure it works
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateVersionDisplay);
    } else {
        updateVersionDisplay();
    }
})();
