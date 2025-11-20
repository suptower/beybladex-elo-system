// Restore dark mode
if (localStorage.getItem("darkmode") === "1") {
    document.body.classList.add("dark");
}

const toggle = document.getElementById("darkToggle");

toggle.onclick = () => {
    document.body.classList.toggle("dark");
    localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light");
};

if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark");
}

