// Restore dark mode
if (localStorage.getItem("darkmode") === "1") {
    document.body.classList.add("dark");
}

const toggle = document.getElementById("darkToggle");
if (toggle) {
    toggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem("darkmode",
            document.body.classList.contains("dark") ? "1" : "0"
        );
    };
}
