# app/utils/aviation_utils.py
"""
Fonctions utilitaires pour le module aviation
"""
from app.modules.aviation.turbulence import TurbulenceIndex
from app.models.aviation_data import TurbulenceData
import numpy as np

def update_turbulence_data(station_id, weather_data):
    """
    Met à jour les données de turbulence basées sur les données météo
    """
    # Calculer les gradients nécessaires
    pressure_gradient = calculate_pressure_gradient(station_id)
    temperature_gradient = calculate_temperature_gradient(station_id)
    
    # Calculer l'indice de turbulence
    turbulence_index = TurbulenceIndex.calculate_turbulence_risk(
        weather_data.wind_speed,
        weather_data.wind_direction_variance or 0,
        pressure_gradient,
        temperature_gradient
    )
    
    # Déterminer le niveau de sévérité
    severity = TurbulenceIndex.get_turbulence_severity(turbulence_index)
    
    # Créer l'enregistrement
    turbulence_data = TurbulenceData(
        station_id=station_id,
        wind_speed=weather_data.wind_speed,
        wind_direction=weather_data.wind_direction,
        wind_direction_variance=weather_data.wind_direction_variance or 0,
        pressure_gradient=pressure_gradient,
        temperature_gradient=temperature_gradient,
        turbulence_index=turbulence_index,
        turbulence_level=severity['level']
    )
    
    return turbulence_data

def calculate_pressure_gradient(station_id):
    """Calcule le gradient de pression"""
    # Récupérer les données récentes de pression
    recent_data = TurbulenceData.query.filter_by(station_id=station_id)\
                                    .order_by(TurbulenceData.timestamp.desc())\
                                    .limit(10).all()
    
    if len(recent_data) < 2:
        return 0.0
    
    # Calculer le gradient sur les dernières mesures
    pressures = [d.station.weather_data[-1].pressure for d in recent_data if d.station.weather_data]
    if len(pressures) < 2:
        return 0.0
    
    return np.gradient(pressures)[0]

def calculate_temperature_gradient(station_id):
    """Calcule le gradient de température"""
    # Logique similaire pour la température
    recent_data = TurbulenceData.query.filter_by(station_id=station_id)\
                                    .order_by(TurbulenceData.timestamp.desc())\
                                    .limit(10).all()
    
    if len(recent_data) < 2:
        return 0.0
    
    temperatures = [d.station.weather_data[-1].temperature for d in recent_data if d.station.weather_data]
    if len(temperatures) < 2:
        return 0.0
    
    return np.gradient(temperatures)[0]