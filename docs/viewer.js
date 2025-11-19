function openViewer(src) {
    const overlay = document.createElement("div");
    overlay.id = "viewerOverlay";
    overlay.onclick = () => overlay.remove();

    const img = document.createElement("img");
    img.src = src;

    overlay.appendChild(img);
    document.body.appendChild(overlay);
}
