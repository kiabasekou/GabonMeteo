# app/routes/aviation.py
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.modules.aviation.turbulence import TurbulenceIndex
from app.models.aviation_data import TurbulenceData
from app.models.weather_data import WeatherStation
from app.extensions import db
from datetime import datetime, timedelta

aviation_bp = Blueprint('aviation', __name__, url_prefix='/api/aviation')

@aviation_bp.route('/test')
def test():
    """Route de test"""
    return jsonify({"message": "Aviation module working!", "status": "ok"})

@aviation_bp.route('/turbulence/<int:station_id>')
def get_turbulence_data(station_id):
    """Récupère les données de turbulence pour une station"""
    try:
        # Récupérer les données les plus récentes
        turbulence = TurbulenceData.query.filter_by(station_id=station_id)\
                                       .order_by(TurbulenceData.timestamp.desc())\
                                       .first()
        
        if not turbulence:
            return jsonify({'error': 'Aucune donnée de turbulence disponible'}), 404
        
        # Calculer l'indice de turbulence en temps réel
        turbulence_index = TurbulenceIndex.calculate_turbulence_risk(
            turbulence.wind_speed,
            turbulence.wind_direction_variance or 0,
            turbulence.pressure_gradient or 0,
            turbulence.temperature_gradient or 0
        )
        
        severity = TurbulenceIndex.get_turbulence_severity(turbulence_index)
        
        return jsonify({
            'station_id': station_id,
            'timestamp': turbulence.timestamp.isoformat(),
            'turbulence_index': round(turbulence_index, 1),
            'severity': severity,
            'raw_data': {
                'wind_speed': turbulence.wind_speed,
                'wind_direction': turbulence.wind_direction,
                'wind_direction_variance': turbulence.wind_direction_variance,
                'pressure_gradient': turbulence.pressure_gradient
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@aviation_bp.route('/turbulence/calculate', methods=['POST'])
@login_required
def calculate_turbulence():
    """Calcule la turbulence à partir de paramètres fournis"""
    try:
        data = request.get_json()
        
        # Valeurs par défaut si les champs sont manquants
        wind_speed = data.get('wind_speed', 0)
        wind_direction_variance = data.get('wind_direction_variance', 0)
        pressure_gradient = data.get('pressure_gradient', 0)
        temperature_gradient = data.get('temperature_gradient', 0)
        
        if wind_speed < 0:
            return jsonify({'error': 'La vitesse du vent ne peut être négative'}), 400
        
        turbulence_index = TurbulenceIndex.calculate_turbulence_risk(
            wind_speed,
            wind_direction_variance,
            pressure_gradient,
            temperature_gradient
        )
        
        severity = TurbulenceIndex.get_turbulence_severity(turbulence_index)
        
        return jsonify({
            'turbulence_index': round(turbulence_index, 1),
            'severity': severity,
            'input_parameters': data,
            'calculation_timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@aviation_bp.route('/stations')
def get_aviation_stations():
    """Liste toutes les stations avec capacités aviation"""
    try:
        stations = WeatherStation.query.all()
        
        stations_data = []
        for station in stations:
            # Vérifier s'il y a des données de turbulence récentes
            has_turbulence_data = TurbulenceData.query.filter_by(station_id=station.id).first() is not None
            
            stations_data.append({
                'id': station.id,
                'name': station.name,
                'region': station.region,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'altitude': station.altitude,
                'has_aviation_data': has_turbulence_data
            })
        
        return jsonify({
            'stations': stations_data,
            'total_count': len(stations_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500