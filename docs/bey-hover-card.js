// bey-hover-card.js - Reusable hover card component for bey previews
// Shows a mini preview card similar to wiki cards when hovering over bey names

// Constants for hover card dimensions
const HOVER_CARD_WIDTH = 280;
const HOVER_CARD_ESTIMATED_HEIGHT = 300; // Estimated height before card is rendered
const HOVER_CARD_PADDING = 10;

let beysDataCache = null;
let hoverCardElement = null;
let hoverTimeout = null;
let hideTimeout = null;

// Load bey data once and cache it
async function loadBeysData() {
    if (beysDataCache) return beysDataCache;
    
    try {
        const response = await fetch('data/beys_data.json');
        beysDataCache = await response.json();
        return beysDataCache;
    } catch (error) {
        console.warn('Could not load beys data for hover cards:', error);
        return [];
    }
}

// Normalize bey name for matching
function normalizeHoverBeyName(name) {
    if (!name) return '';
    return name.toLowerCase().replace(/[\s\-_]/g, '');
}

// Find bey by name in cached data
function findBeyByName(name) {
    if (!beysDataCache || !name) return null;
    const normalizedSearch = normalizeHoverBeyName(name);
    
    // Try exact match on blade name first
    let found = beysDataCache.find(b => normalizeHoverBeyName(b.blade) === normalizedSearch);
    if (found) return found;
    
    // Then try full name match
    found = beysDataCache.find(b => normalizeHoverBeyName(b.name) === normalizedSearch);
    if (found) return found;
    
    // Try partial match on blade
    found = beysDataCache.find(b => 
        normalizeHoverBeyName(b.blade).includes(normalizedSearch) || 
        normalizedSearch.includes(normalizeHoverBeyName(b.blade))
    );
    return found;
}

// Create the hover card element if it doesn't exist
function createHoverCard() {
    if (hoverCardElement) return hoverCardElement;
    
    hoverCardElement = document.createElement('div');
    hoverCardElement.className = 'bey-hover-card';
    hoverCardElement.innerHTML = `
        <div class="hover-card-inner">
            <div class="hover-card-image">
                <img src="" alt="" loading="lazy">
                <div class="hover-card-type"></div>
            </div>
            <div class="hover-card-content">
                <h4 class="hover-card-title"></h4>
                <p class="hover-card-code"></p>
                <p class="hover-card-description"></p>
                <div class="hover-card-parts"></div>
                <div class="hover-card-footer">Click to view full profile</div>
            </div>
        </div>
    `;
    document.body.appendChild(hoverCardElement);
    
    // Keep hover card visible when mouse is over it
    hoverCardElement.addEventListener('mouseenter', () => {
        clearTimeout(hideTimeout);
    });
    
    hoverCardElement.addEventListener('mouseleave', () => {
        hideHoverCard();
    });
    
    return hoverCardElement;
}

// Show hover card with bey data
function showHoverCard(beyData, targetElement) {
    if (!beyData) return;
    
    const card = createHoverCard();
    
    // Populate card content
    const img = card.querySelector('.hover-card-image img');
    img.src = beyData.image;
    img.alt = beyData.name;
    
    const type = card.querySelector('.hover-card-type');
    type.textContent = beyData.type;
    type.className = `hover-card-type ${beyData.type.toLowerCase()}`;
    
    card.querySelector('.hover-card-title').textContent = beyData.name;
    
    const codeEl = card.querySelector('.hover-card-code');
    if (beyData.code) {
        codeEl.textContent = beyData.code;
        codeEl.style.display = 'inline-block';
        // Set line class
        codeEl.className = 'hover-card-code';
        if (beyData.code.startsWith('BX')) codeEl.classList.add('basic-line');
        else if (beyData.code.startsWith('UX')) codeEl.classList.add('unique-line');
        else if (beyData.code.startsWith('CX')) codeEl.classList.add('custom-line');
    } else {
        codeEl.style.display = 'none';
    }
    
    card.querySelector('.hover-card-description').textContent = beyData.description || '';
    
    // Build parts list
    const partsContainer = card.querySelector('.hover-card-parts');
    partsContainer.innerHTML = '';
    
    const parts = [
        { label: 'Blade', value: beyData.blade },
        { label: 'Ratchet', value: beyData.ratchet_integrated_bit ? null : beyData.ratchet },
        { label: 'Bit', value: beyData.ratchet_integrated_bit || beyData.bit }
    ];
    
    parts.forEach(part => {
        if (part.value) {
            const partEl = document.createElement('div');
            partEl.className = 'hover-card-part';
            partEl.innerHTML = `<span class="part-label">${part.label}:</span> <span class="part-value">${part.value}</span>`;
            partsContainer.appendChild(partEl);
        }
    });
    
    // Position the card near the target element
    positionHoverCard(card, targetElement);
    
    // Show the card
    card.classList.add('visible');
}

// Position the hover card near the target element
function positionHoverCard(card, targetElement) {
    const targetRect = targetElement.getBoundingClientRect();
    const cardHeight = card.offsetHeight || HOVER_CARD_ESTIMATED_HEIGHT;
    
    let left = targetRect.left + window.scrollX;
    let top = targetRect.bottom + window.scrollY + HOVER_CARD_PADDING;
    
    // Check if card would go off right edge of screen
    if (left + HOVER_CARD_WIDTH > window.innerWidth) {
        left = window.innerWidth - HOVER_CARD_WIDTH - HOVER_CARD_PADDING;
    }
    
    // Check if card would go off left edge
    if (left < HOVER_CARD_PADDING) {
        left = HOVER_CARD_PADDING;
    }
    
    // Check if card would go off bottom of viewport
    if (targetRect.bottom + cardHeight + HOVER_CARD_PADDING > window.innerHeight) {
        // Position above the element instead
        top = targetRect.top + window.scrollY - cardHeight - HOVER_CARD_PADDING;
    }
    
    card.style.left = `${left}px`;
    card.style.top = `${top}px`;
}

// Hide the hover card
function hideHoverCard() {
    if (hoverCardElement) {
        hoverCardElement.classList.remove('visible');
    }
}

// Initialize hover functionality for bey links
function initBeyHoverCards() {
    // Load beys data first
    loadBeysData().then(() => {
        // Use event delegation for better performance
        document.addEventListener('mouseover', handleMouseOver);
        document.addEventListener('mouseout', handleMouseOut);
    });
}

// Handle mouseover events
async function handleMouseOver(event) {
    const link = event.target.closest('.bey-link');
    if (!link) return;
    
    // Clear any pending hide timeout
    clearTimeout(hideTimeout);
    
    // Debounce the show to prevent flickering
    clearTimeout(hoverTimeout);
    hoverTimeout = setTimeout(async () => {
        // Get the bey name from the link
        let beyName = link.textContent.trim();
        
        // Try to extract from href if available (e.g., bey.html?name=FoxBrush)
        const href = link.getAttribute('href');
        if (href && href.includes('?') && href.includes('name=')) {
            const queryString = href.split('?')[1];
            if (queryString) {
                const urlParams = new URLSearchParams(queryString);
                beyName = urlParams.get('name') || beyName;
            }
        }
        
        // Find bey data
        const beyData = findBeyByName(beyName);
        if (beyData) {
            showHoverCard(beyData, link);
        }
    }, 200); // 200ms delay before showing
}

// Handle mouseout events
function handleMouseOut(event) {
    const link = event.target.closest('.bey-link');
    if (!link) return;
    
    // Clear pending show timeout
    clearTimeout(hoverTimeout);
    
    // Delay hiding to allow moving to the hover card
    hideTimeout = setTimeout(() => {
        hideHoverCard();
    }, 100);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBeyHoverCards);
} else {
    initBeyHoverCards();
}
