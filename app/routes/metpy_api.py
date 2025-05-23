# app/routes/metpy_api.py
"""
Routes API avancées MetPy pour GabonMétéo+
Endpoints spécialisés pour analyses météorologiques du Gabon
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.utils.metpy_gabon import GabonMetPyCore
from app.models.weather_data import WeatherStation, WeatherData
from app.models.agent import AgentDGM
from app import db
from datetime import datetime, timedelta
import logging

# Configuration logging
logger = logging.getLogger(__name__)

# Blueprint pour les APIs MetPy
metpy_api_bp = Blueprint('metpy_api', __name__, url_prefix='/api/metpy')

# Instance globale du calculateur MetPy
gabon_metpy = GabonMetPyCore()

# ============ ENDPOINTS ANALYSES THERMIQUES ============

@metpy_api_bp.route('/thermal-analysis/<int:station_id>')
def thermal_analysis_station(station_id):
    """
    Analyse thermique complète d'une station avec MetPy
    """
    try:
        # Récupération station et données
        station = WeatherStation.query.get_or_404(station_id)
        latest_data = WeatherData.query.filter_