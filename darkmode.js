// Migrate from old localStorage key (darkmode) to new key (theme)
if (localStorage.getItem("darkmode") === "1" && !localStorage.getItem("theme")) {
    localStorage.setItem("theme", "dark");
    localStorage.removeItem("darkmode");
}

// Restore theme preference on page load
const savedTheme = localStorage.getItem("theme");
const toggle = document.getElementById("darkToggle");

if (savedTheme === "dark") {
    document.body.classList.add("dark");
    if (toggle) toggle.checked = true;
} else {
    document.body.classList.remove("dark");
    if (toggle) toggle.checked = false;
}

if (toggle) {
    toggle.onchange = () => {
        document.body.classList.toggle("dark");
        const theme = document.body.classList.contains("dark") ? "dark" : "light";
        localStorage.setItem("theme", theme);
    };
}

