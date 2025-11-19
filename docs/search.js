function renderSearchResults(images) {
    const gallery = document.getElementById("gallery");
    gallery.innerHTML = "";

    images.forEach(imgObj => {
        const img = document.createElement("img");
        img.src = imgObj.src;
        img.alt = imgObj.title;
        img.onclick = () => openViewer(imgObj.src);

        gallery.appendChild(img);
    });
}

document.getElementById("searchInput").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();

    const filtered = window.allImages.filter(im =>
        im.title.toLowerCase().includes(q)
    );

    renderSearchResults(filtered);
});
