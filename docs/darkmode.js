// Migrate from old localStorage key (darkmode) to new key (theme)
if (localStorage.getItem("darkmode") === "1" && !localStorage.getItem("theme")) {
    localStorage.setItem("theme", "dark");
    localStorage.removeItem("darkmode");
}

// Restore theme preference on page load
const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") {
    document.body.classList.add("dark");
} else if (savedTheme === "light") {
    document.body.classList.remove("dark");
}

const toggle = document.getElementById("darkToggle");

toggle.onclick = () => {
    document.body.classList.toggle("dark");
    const theme = document.body.classList.contains("dark") ? "dark" : "light";
    localStorage.setItem("theme", theme);
};

