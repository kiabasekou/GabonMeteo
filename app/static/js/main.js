// Fonctions JavaScript pour l'application GabonMétéo+

document.addEventListener('DOMContentLoaded', function() {
    // Animation pour les cartes
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            // L'animation CSS s'occupe de l'effet
        });
        
        card.addEventListener('mouseleave', function() {
            // L'animation CSS s'occupe de l'effet
        });
    });
    
    // Mise à jour automatique des alertes (simulée)
    const alertsContainer = document.querySelector('.alerts-container');
    
    if (alertsContainer) {
        // Simulation d'une mise à jour des alertes toutes les 30 secondes
        setInterval(function() {
            const alertBadges = document.querySelectorAll('.badge');
            
            alertBadges.forEach(badge => {
                // Animation simple pour montrer que la page est active
                badge.classList.add('badge-pulse');
                
                setTimeout(function() {
                    badge.classList.remove('badge-pulse');
                }, 1000);
            });
        }, 30000);
    }
    
    // Gestion des tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Fonction pour formater la date en français
function formatDateFr(date) {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('fr-FR', options);
}

// Fonction pour déterminer l'icône météo en fonction des conditions
function getWeatherIcon(temperature, precipitation) {
    if (precipitation > 10) {
        return 'heavy-rain';
    } else if (precipitation > 0) {
        return 'rain';
    } else if (temperature > 30) {
        return 'sun';
    } else {
        return 'cloud';
    }
}

// Gérer les loaders pendant les chargements
function showLoader(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loader"></div>';
    }
}

function hideLoader(elementId, content) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    }
}

// Intercepter les soumissions de formulaire pour afficher un loader
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Chargement...';
                submitBtn.disabled = true;
                
                // Rétablir le bouton si la soumission prend trop de temps
                setTimeout(function() {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 5000);
            }
        });
    });
});