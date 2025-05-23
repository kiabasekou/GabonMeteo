# app/routes/metpy_enhanced.py
from flask import Blueprint, jsonify, request
from app.utils.metpy_core import GabonMeteoCore
from app.models.weather_data import WeatherStation, WeatherData

metpy_enhanced_bp = Blueprint('metpy_enhanced', __name__, url_prefix='/api/v2')

@metpy_enhanced_bp.route('/station/<int:station_id>/advanced-analysis')
def advanced_station_analysis(station_id):
    """Analyse météorologique avancée d'une station"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        latest_data = WeatherData.query.filter_by(station_id=station_id)\
                                      .order_by(WeatherData.timestamp.desc())\
                                      .first()
        
        if not latest_data:
            return jsonify({'error': 'Aucune donnée disponible'}), 404
        
        meteo_core = GabonMeteoCore()
        
        # Conditions actuelles
        current_conditions = {
            'temperature': latest_data.temperature,
            'humidity': latest_data.humidity or 80,
            'pressure': latest_data.pressure or 1013,
            'wind_speed': latest_data.wind_speed or 8,
            'precipitation': latest_data.precipitation or 0
        }
        
        # Analyse thermique complète
        thermal_analysis = meteo_core.analyze_thermal_stress(
            current_conditions['temperature'],
            current_conditions['humidity'],
            current_conditions['wind_speed']
        )
        
        # Prévisions avancées 7 jours
        predictions = meteo_core.predict_advanced_weather(current_conditions, days_ahead=7)
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name,
                'region': station.region,
                'coordinates': [station.latitude, station.longitude]
            },
            'timestamp': latest_data.timestamp.isoformat(),
            'current_conditions': current_conditions,
            'thermal_analysis': thermal_analysis,
            'advanced_forecasts': predictions,
            'analysis_type': 'MetPy Enhanced'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@metpy_enhanced_bp.route('/national-thermal-comfort')
def national_thermal_comfort():
    """Carte nationale de confort thermique"""
    try:
        stations = WeatherStation.query.all()
        meteo_core = GabonMeteoCore()
        
        comfort_data = []
        
        for station in stations:
            latest_data = WeatherData.query.filter_by(station_id=station.id)\
                                          .order_by(WeatherData.timestamp.desc())\
                                          .first()
            
            if latest_data:
                thermal_analysis = meteo_core.analyze_thermal_stress(
                    latest_data.temperature,
                    latest_data.humidity or 80,
                    latest_data.wind_speed or 8
                )
                
                comfort_data.append({
                    'station': {
                        'id': station.id,
                        'name': station.name,
                        'latitude': station.latitude,
                        'longitude': station.longitude,
                        'region': station.region
                    },
                    'thermal_comfort': thermal_analysis,
                    'timestamp': latest_data.timestamp.isoformat()
                })
        
        return jsonify({
            'thermal_comfort_map': comfort_data,
            'generated_at': datetime.now().isoformat(),
            'methodology': 'MetPy heat index + wind cooling factor'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500