from flask import Blueprint, jsonify, request
from app import db
from app.models.weather_data import WeatherStation, WeatherData
from app.utils.weather_utils import predict_temperature
from datetime import datetime, timedelta
import json

# Création d'un Blueprint pour les routes API
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status', methods=['GET'])
def api_status():
    """Vérifier si l'API fonctionne"""
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@api_bp.route('/stations', methods=['GET'])
def get_stations():
    """Obtenir la liste de toutes les stations météo"""
    stations = WeatherStation.query.all()
    result = []
    
    for station in stations:
        result.append({
            "id": station.id,
            "name": station.name,
            "region": station.region,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "altitude": station.altitude
        })
    
    return jsonify({
        "status": "success",
        "count": len(result),
        "stations": result
    })

@api_bp.route('/stations/<int:station_id>', methods=['GET'])
def get_station(station_id):
    """Obtenir les détails d'une station spécifique"""
    station = WeatherStation.query.get_or_404(station_id)
    
    result = {
        "id": station.id,
        "name": station.name,
        "region": station.region,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "altitude": station.altitude
    }
    
    return jsonify({
        "status": "success",
        "station": result
    })

@api_bp.route('/current', methods=['GET'])
def get_current_weather():
    """Obtenir les données météo actuelles pour toutes les stations"""
    stations = WeatherStation.query.all()
    result = []
    
    for station in stations:
        # Récupérer les données les plus récentes
        weather_data = WeatherData.query.filter_by(station_id=station.id).order_by(WeatherData.timestamp.desc()).first()
        
        if weather_data:
            result.append({
                "station_id": station.id,
                "station_name": station.name,
                "region": station.region,
                "timestamp": weather_data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "temperature": round(weather_data.temperature, 1),
                "humidity": round(weather_data.humidity, 1) if weather_data.humidity else None,
                "pressure": round(weather_data.pressure, 1) if weather_data.pressure else None,
                "wind_speed": round(weather_data.wind_speed, 1) if weather_data.wind_speed else None,
                "wind_direction": round(weather_data.wind_direction, 0) if weather_data.wind_direction else None,
                "precipitation": round(weather_data.precipitation, 1) if weather_data.precipitation else None
            })
    
    return jsonify({
        "status": "success",
        "count": len(result),
        "data": result,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@api_bp.route('/stations/<int:station_id>/current', methods=['GET'])
def get_station_current_weather(station_id):
    """Obtenir les données météo actuelles pour une station spécifique"""
    station = WeatherStation.query.get_or_404(station_id)
    
    # Récupérer les données les plus récentes
    weather_data = WeatherData.query.filter_by(station_id=station.id).order_by(WeatherData.timestamp.desc()).first()
    
    if not weather_data:
        return jsonify({
            "status": "error",
            "message": "Aucune donnée météo disponible pour cette station"
        }), 404
    
    result = {
        "station_id": station.id,
        "station_name": station.name,
        "region": station.region,
        "timestamp": weather_data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "temperature": round(weather_data.temperature, 1),
        "humidity": round(weather_data.humidity, 1) if weather_data.humidity else None,
        "pressure": round(weather_data.pressure, 1) if weather_data.pressure else None,
        "wind_speed": round(weather_data.wind_speed, 1) if weather_data.wind_speed else None,
        "wind_direction": round(weather_data.wind_direction, 0) if weather_data.wind_direction else None,
        "precipitation": round(weather_data.precipitation, 1) if weather_data.precipitation else None
    }
    
    return jsonify({
        "status": "success",
        "data": result
    })

@api_bp.route('/stations/<int:station_id>/historical', methods=['GET'])
def get_station_historical_data(station_id):
    """Obtenir les données historiques pour une station spécifique"""
    station = WeatherStation.query.get_or_404(station_id)
    
    # Paramètres de filtrage
    days = request.args.get('days', default=7, type=int)
    if days > 30:  # Limiter à 30 jours pour éviter les requêtes trop lourdes
        days = 30
    
    # Calculer la date de début
    start_date = datetime.now() - timedelta(days=days)
    
    # Récupérer les données historiques
    historical_data = WeatherData.query.filter_by(station_id=station.id).filter(
        WeatherData.timestamp >= start_date
    ).order_by(WeatherData.timestamp).all()
    
    result = []
    for data in historical_data:
        result.append({
            "timestamp": data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": round(data.temperature, 1),
            "humidity": round(data.humidity, 1) if data.humidity else None,
            "pressure": round(data.pressure, 1) if data.pressure else None,
            "wind_speed": round(data.wind_speed, 1) if data.wind_speed else None,
            "wind_direction": round(data.wind_direction, 0) if data.wind_direction else None,
            "precipitation": round(data.precipitation, 1) if data.precipitation else None
        })
    
    return jsonify({
        "status": "success",
        "station_id": station.id,
        "station_name": station.name,
        "days_requested": days,
        "count": len(result),
        "data": result
    })

@api_bp.route('/forecast', methods=['GET'])
def get_forecast():
    """Obtenir les prévisions météo pour toutes les stations"""
    stations = WeatherStation.query.all()
    result = []
    
    for station in stations:
        # Récupérer les données historiques récentes pour faire des prédictions
        historical_data = WeatherData.query.filter_by(station_id=station.id).order_by(
            WeatherData.timestamp.desc()
        ).limit(10).all()
        
        # Utiliser la fonction de prévision
        if historical_data:
            predictions = predict_temperature(historical_data, days_ahead=3)
            
            station_forecast = {
                "station_id": station.id,
                "station_name": station.name,
                "region": station.region,
                "forecast": []
            }
            
            for prediction in predictions:
                station_forecast["forecast"].append({
                    "date": prediction['date'].strftime('%Y-%m-%d'),
                    "temperature": round(prediction['temperature'], 1),
                    "precipitation": round(prediction['precipitation'], 1) if 'precipitation' in prediction else None,
                    "humidity": round(prediction['humidity'], 1) if 'humidity' in prediction else None
                })
            
            result.append(station_forecast)
    
    return jsonify({
        "status": "success",
        "count": len(result),
        "data": result,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@api_bp.route('/stations/<int:station_id>/forecast', methods=['GET'])
def get_station_forecast(station_id):
    """Obtenir les prévisions météo pour une station spécifique"""
    station = WeatherStation.query.get_or_404(station_id)
    
    # Récupérer les données historiques récentes pour faire des prédictions
    historical_data = WeatherData.query.filter_by(station_id=station.id).order_by(
        WeatherData.timestamp.desc()
    ).limit(10).all()
    
    # Utiliser la fonction de prévision
    if not historical_data:
        return jsonify({
            "status": "error",
            "message": "Données insuffisantes pour générer des prévisions"
        }), 404
    
    predictions = predict_temperature(historical_data, days_ahead=3)
    
    result = []
    for prediction in predictions:
        result.append({
            "date": prediction['date'].strftime('%Y-%m-%d'),
            "temperature": round(prediction['temperature'], 1),
            "precipitation": round(prediction['precipitation'], 1) if 'precipitation' in prediction else None,
            "humidity": round(prediction['humidity'], 1) if 'humidity' in prediction else None
        })
    
    return jsonify({
        "status": "success",
        "station_id": station.id,
        "station_name": station.name,
        "region": station.region,
        "forecast": result,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# Route pour obtenir les statistiques météo
@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Obtenir des statistiques météorologiques globales"""
    # Paramètres
    days = request.args.get('days', default=30, type=int)
    if days > 365:  # Limiter pour éviter les requêtes trop lourdes
        days = 365
    
    # Calculer la date de début
    start_date = datetime.now() - timedelta(days=days)
    
    # Construire la réponse statistique
    result = {
        "period": f"Derniers {days} jours",
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "stations": {},
        "global": {
            "temperature": {
                "avg": None,
                "min": None,
                "max": None
            },
            "precipitation": {
                "total": None,
                "avg": None,
                "max": None
            },
            "humidity": {
                "avg": None
            }
        }
    }
    
    # Variables pour les statistiques globales
    all_temps = []
    all_precips = []
    all_humidity = []
    
    # Récupérer les statistiques par station
    stations = WeatherStation.query.all()
    
    for station in stations:
        # Récupérer les données de la période
        data = WeatherData.query.filter_by(station_id=station.id).filter(
            WeatherData.timestamp >= start_date
        ).all()
        
        if data:
            temps = [d.temperature for d in data if d.temperature is not None]
            precips = [d.precipitation for d in data if d.precipitation is not None]
            humidity = [d.humidity for d in data if d.humidity is not None]
            
            # Ajouter aux listes globales
            all_temps.extend(temps)
            all_precips.extend(precips)
            all_humidity.extend(humidity)
            
            # Statistiques de station
            station_stats = {
                "temperature": {
                    "avg": round(sum(temps) / len(temps), 1) if temps else None,
                    "min": round(min(temps), 1) if temps else None,
                    "max": round(max(temps), 1) if temps else None
                },
                "precipitation": {
                    "total": round(sum(precips), 1) if precips else None,
                    "avg": round(sum(precips) / len(precips), 1) if precips else None,
                    "max": round(max(precips), 1) if precips else None
                },
                "humidity": {
                    "avg": round(sum(humidity) / len(humidity), 1) if humidity else None
                }
            }
            
            result["stations"][station.name] = station_stats
    
    # Calculer les statistiques globales
    if all_temps:
        result["global"]["temperature"]["avg"] = round(sum(all_temps) / len(all_temps), 1)
        result["global"]["temperature"]["min"] = round(min(all_temps), 1)
        result["global"]["temperature"]["max"] = round(max(all_temps), 1)
    
    if all_precips:
        result["global"]["precipitation"]["total"] = round(sum(all_precips), 1)
        result["global"]["precipitation"]["avg"] = round(sum(all_precips) / len(all_precips), 1)
        result["global"]["precipitation"]["max"] = round(max(all_precips), 1)
    
    if all_humidity:
        result["global"]["humidity"]["avg"] = round(sum(all_humidity) / len(all_humidity), 1)
    
    return jsonify({
        "status": "success",
        "statistics": result
    })