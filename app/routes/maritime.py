# app/routes/maritime.py
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.modules.maritime.sea_state import SeaStateCalculator, TidalCalculator
from app.models.maritime_data import MaritimeData
from app.models.weather_data import WeatherStation, WeatherData
from app.extensions import db
from datetime import datetime, timedelta
import random
import logging
import math  # ✅ Ajoutez cette ligne en haut du fichier

maritime_bp = Blueprint('maritime', __name__, url_prefix='/api/maritime')


@maritime_bp.route('/conditions/<int:station_id>')
def get_maritime_conditions(station_id):
    """Récupère les conditions maritimes pour une station"""
    try:
        # Récupérer la station
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer les données maritimes les plus récentes
        maritime_data = MaritimeData.query.filter_by(station_id=station_id)\
                                        .order_by(MaritimeData.timestamp.desc())\
                                        .first()
        
        # Récupérer les données météo pour compléter
        weather_data = WeatherData.query.filter_by(station_id=station_id)\
                                       .order_by(WeatherData.timestamp.desc())\
                                       .first()
        
        if not maritime_data:
            return jsonify({'error': 'Aucune donnée maritime disponible'}), 404
        
        # Calculer des informations supplémentaires
        sea_state_info = SeaStateCalculator.get_sea_state_info(maritime_data.sea_state)
        
        navigation_safety = SeaStateCalculator.calculate_navigation_safety(
            maritime_data.sea_state,
            weather_data.wind_speed if weather_data else 10,
            5.0  # Visibilité par défaut
        )
        
        # Informations sur les marées
        tide_info = SeaStateCalculator.predict_tide_times(
            maritime_data.timestamp,
            maritime_data.tide_height
        )
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name,
                'location': [station.latitude, station.longitude]
            },
            'timestamp': maritime_data.timestamp.isoformat(),
            'sea_conditions': {
                'state': maritime_data.sea_state,
                'description': sea_state_info['description'],
                'conditions': sea_state_info['conditions'],
                'wave_height': maritime_data.wave_height,
                'wave_period': maritime_data.wave_period,
                'wave_direction': maritime_data.wave_direction
            },
            'navigation': navigation_safety,
            'tides': {
                'current_height': maritime_data.tide_height,
                'direction': tide_info['tide_direction'],
                'next_high': tide_info['next_high_tide'].isoformat(),
                'next_low': tide_info['next_low_tide'].isoformat()
            },
            'surface_current': {
                'speed': maritime_data.surface_current_speed,
                'direction': maritime_data.surface_current_direction
            }
        })
    
    except Exception as e:
        logging.error(f"Erreur dans get_maritime_conditions: {str(e)}")
        logging.error(f"Station ID: {station_id}")
        return jsonify({'error': str(e), 'detail': 'Voir les logs'}), 500


@maritime_bp.route('/sea-state/calculate', methods=['POST'])
def calculate_sea_state():
    """Calcule l'état de la mer à partir de paramètres météo"""
    try:
        data = request.get_json()
        
        wind_speed = data.get('wind_speed', 0)
        wind_duration = data.get('wind_duration_hours', 12)
        fetch_distance = data.get('fetch_distance_km', 50)
        
        # Calculs
        sea_state = SeaStateCalculator.calculate_sea_state(
            wind_speed, wind_duration, fetch_distance
        )
        
        sea_state_info = SeaStateCalculator.get_sea_state_info(sea_state)
        
        # Estimer la hauteur des vagues
        wave_height = (sea_state_info['height_range'][0] + sea_state_info['height_range'][1]) / 2
        wave_period = SeaStateCalculator.calculate_wave_period(wave_height)
        
        navigation_safety = SeaStateCalculator.calculate_navigation_safety(
            sea_state, wind_speed, data.get('visibility', 5)
        )
        
        return jsonify({
            'sea_state': sea_state,
            'description': sea_state_info['description'],
            'conditions': sea_state_info['conditions'],
            'wave_height': round(wave_height, 1),
            'wave_period': wave_period,
            'navigation_safety': navigation_safety,
            'calculation_parameters': data,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@maritime_bp.route('/stations')
def get_maritime_stations():
    """Liste les stations avec données maritimes"""
    try:
        # Stations côtières (simplification: toutes les stations)
        stations = WeatherStation.query.all()
        
        maritime_stations = []
        for station in stations:
            # Vérifier s'il y a des données maritimes
            has_data = MaritimeData.query.filter_by(station_id=station.id).first() is not None
            
            maritime_stations.append({
                'id': station.id,
                'name': station.name,
                'region': station.region,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'has_maritime_data': has_data,
                'is_coastal': True  # Simplification
            })
        
        return jsonify({
            'stations': maritime_stations,
            'total_count': len(maritime_stations)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@maritime_bp.route('/tides/<int:station_id>')
def get_tide_information(station_id):
    """Informations détaillées sur les marées"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer les données de marée récentes
        maritime_data = MaritimeData.query.filter_by(station_id=station_id)\
                                        .order_by(MaritimeData.timestamp.desc())\
                                        .limit(10).all()
        
        if not maritime_data:
            return jsonify({'error': 'Aucune donnée de marée disponible'}), 404
        
        # Prédictions des prochaines marées (24h)
        current_time = datetime.utcnow()
        tide_predictions = []
        
        for hour in range(24):
            future_time = current_time + timedelta(hours=hour)
            tide_info = SeaStateCalculator.predict_tide_times(future_time, 2.0)
            
            tide_predictions.append({
                'time': future_time.isoformat(),
                'predicted_height': round(2.0 + 1.5 * math.sin((hour / 12.416) * 2 * math.pi), 1),
                'tide_direction': tide_info['tide_direction']
            })
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'current_conditions': {
                'tide_height': maritime_data[0].tide_height,
                'direction': maritime_data[0].tide_direction,
                'timestamp': maritime_data[0].timestamp.isoformat()
            },
            'predictions_24h': tide_predictions,
            'historical_data': [data.to_dict() for data in maritime_data]
        })
    
    except Exception as e:
        logging.error(f"Erreur dans get_maritime_conditions: {str(e)}")
        logging.error(f"Station ID: {station_id}")
        return jsonify({'error': str(e), 'detail': 'Voir les logs'}), 500