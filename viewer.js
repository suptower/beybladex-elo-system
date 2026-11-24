let currentViewerIndex = 0;
let viewerImages = [];

function openViewer(index, images) {
    currentViewerIndex = index;
    viewerImages = images;
    
    const overlay = document.createElement("div");
    overlay.id = "viewerOverlay";
    
    // Create navigation buttons
    const prevBtn = document.createElement("button");
    prevBtn.className = "viewer-nav prev";
    prevBtn.innerHTML = "&#8249;"; // Left arrow
    prevBtn.onclick = (e) => {
        e.stopPropagation();
        navigateViewer(-1);
    };
    
    const nextBtn = document.createElement("button");
    nextBtn.className = "viewer-nav next";
    nextBtn.innerHTML = "&#8250;"; // Right arrow
    nextBtn.onclick = (e) => {
        e.stopPropagation();
        navigateViewer(1);
    };
    
    // Create image container
    const imgContainer = document.createElement("div");
    imgContainer.className = "viewer-image-container";
    
    const img = document.createElement("img");
    img.src = viewerImages[currentViewerIndex].src;
    img.id = "viewerImage";
    
    // Create title
    const title = document.createElement("div");
    title.className = "viewer-title";
    title.id = "viewerTitle";
    title.textContent = viewerImages[currentViewerIndex].title;
    
    // Create counter
    const counter = document.createElement("div");
    counter.className = "viewer-counter";
    counter.id = "viewerCounter";
    counter.textContent = `${currentViewerIndex + 1} / ${viewerImages.length}`;
    
    imgContainer.appendChild(img);
    
    overlay.appendChild(prevBtn);
    overlay.appendChild(imgContainer);
    overlay.appendChild(nextBtn);
    overlay.appendChild(title);
    overlay.appendChild(counter);
    
    // Close on overlay click (not on image or buttons)
    overlay.onclick = (e) => {
        if (e.target === overlay) {
            overlay.remove();
            document.removeEventListener("keydown", handleKeyPress);
        }
    };
    
    document.body.appendChild(overlay);
    document.addEventListener("keydown", handleKeyPress);
    
    // Update button visibility
    updateNavButtons();
}

function navigateViewer(direction) {
    currentViewerIndex += direction;
    
    if (currentViewerIndex < 0) {
        currentViewerIndex = viewerImages.length - 1;
    } else if (currentViewerIndex >= viewerImages.length) {
        currentViewerIndex = 0;
    }
    
    const img = document.getElementById("viewerImage");
    const title = document.getElementById("viewerTitle");
    const counter = document.getElementById("viewerCounter");
    
    img.src = viewerImages[currentViewerIndex].src;
    title.textContent = viewerImages[currentViewerIndex].title;
    counter.textContent = `${currentViewerIndex + 1} / ${viewerImages.length}`;
    
    updateNavButtons();
}

function updateNavButtons() {
    const prevBtn = document.querySelector(".viewer-nav.prev");
    const nextBtn = document.querySelector(".viewer-nav.next");
    
    if (prevBtn && nextBtn) {
        prevBtn.style.display = viewerImages.length > 1 ? "block" : "none";
        nextBtn.style.display = viewerImages.length > 1 ? "block" : "none";
    }
}

function handleKeyPress(e) {
    if (e.key === "ArrowLeft") {
        navigateViewer(-1);
    } else if (e.key === "ArrowRight") {
        navigateViewer(1);
    } else if (e.key === "Escape") {
        const overlay = document.getElementById("viewerOverlay");
        if (overlay) {
            overlay.remove();
            document.removeEventListener("keydown", handleKeyPress);
        }
    }
}
