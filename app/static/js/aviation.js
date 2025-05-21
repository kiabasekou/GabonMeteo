// app/static/js/aviation.js
/**
 * Code JavaScript pour l'interface aviation
 */

class TurbulenceDisplay {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.setupEventListeners();
    }
    
    async loadTurbulenceData(stationId) {
        try {
            const response = await fetch(`/api/aviation/turbulence/${stationId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.displayTurbulenceData(data);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            this.showError('Erreur de connexion');
        }
    }
    
    displayTurbulenceData(data) {
        const turbulenceHtml = `
            <div class="turbulence-card">
                <div class="card-header">
                    <h5>Conditions de Turbulence</h5>
                    <small>Dernière mise à jour: ${new Date(data.timestamp).toLocaleString()}</small>
                </div>
                <div class="card-body">
                    <div class="turbulence-gauge">
                        <canvas id="turbulenceGauge" width="200" height="200"></canvas>
                    </div>
                    <div class="turbulence-info">
                        <div class="info-item">
                            <span class="label">Indice:</span>
                            <span class="value">${data.turbulence_index}/10</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Niveau:</span>
                            <span class="badge badge-${data.severity.color}">
                                ${data.severity.description}
                            </span>
                        </div>
                        <div class="recommendations">
                            <h6>Recommandations:</h6>
                            <p>${data.severity.recommendations}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = turbulenceHtml;
        this.drawTurbulenceGauge(data.turbulence_index);
    }
    
    drawTurbulenceGauge(value) {
        const canvas = document.getElementById('turbulenceGauge');
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = 80;
        
        // Effacer le canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Dessiner l'arc de fond
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 20;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.stroke();
        
        // Dessiner l'arc de valeur
        const angle = (value / 10) * 2 * Math.PI;
        const color = this.getTurbulenceColor(value);
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 20;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -Math.PI/2, -Math.PI/2 + angle);
        ctx.stroke();
        
        // Afficher la valeur
        ctx.fillStyle = '#333';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(value.toFixed(1), centerX, centerY + 8);
    }
    
    getTurbulenceColor(value) {
        if (value <= 2) return '#4CAF50'; // Vert
        if (value <= 4) return '#FFC107'; // Jaune
        if (value <= 6) return '#FF9800'; // Orange
        if (value <= 8) return '#F44336'; // Rouge
        return '#8B0000'; // Rouge foncé
    }
    
    setupEventListeners() {
        // Mise à jour automatique toutes les 5 minutes
        setInterval(() => {
            if (this.currentStationId) {
                this.loadTurbulenceData(this.currentStationId);
            }
        }, 300000);
    }
    
    showError(message) {
        this.container.innerHTML = `
            <div class="alert alert-danger">
                <strong>Erreur:</strong> ${message}
            </div>
        `;
    }
}

// Initialiser l'affichage des turbulences
document.addEventListener('DOMContentLoaded', function() {
    const turbulenceDisplay = new TurbulenceDisplay('turbulence-container');
    
    // Charger les données pour la station par défaut
    const defaultStationId = document.querySelector('[data-default-station]')
                                   ?.getAttribute('data-default-station');
    if (defaultStationId) {
        turbulenceDisplay.currentStationId = defaultStationId;
        turbulenceDisplay.loadTurbulenceData(defaultStationId);
    }
});