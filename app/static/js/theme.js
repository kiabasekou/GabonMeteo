// Gestion du thème clair/sombre
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si un thème est déjà enregistré
    const currentTheme = localStorage.getItem('theme');
    
    // Si c'est le cas, appliquer ce thème
    if (currentTheme) {
        document.documentElement.setAttribute('data-bs-theme', currentTheme);
        updateThemeToggle(currentTheme);
    }
    
    // Gérer le bouton de changement de thème
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            // Changer le thème
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            
            // Enregistrer le choix de l'utilisateur
            localStorage.setItem('theme', newTheme);
            
            // Mettre à jour l'icône
            updateThemeToggle(newTheme);
        });
    }
});

// Mettre à jour l'icône du bouton selon le thème
function updateThemeToggle(theme) {
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.classList.remove('bi-moon');
            themeIcon.classList.add('bi-sun');
        } else {
            themeIcon.classList.remove('bi-sun');
            themeIcon.classList.add('bi-moon');
        }
    }
}