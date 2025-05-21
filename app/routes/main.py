from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.weather_data import WeatherStation, WeatherData
from app.utils.weather_utils import predict_temperature
from app.models.user import User
from sqlalchemy import func
from datetime import datetime, timedelta
import csv
import io

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Récupération des stations
    stations = WeatherStation.query.all()
    
    # Récupération des données météo les plus récentes pour chaque station
    latest_data = {}
    for station in stations:
        data = WeatherData.query.filter_by(station_id=station.id).order_by(WeatherData.timestamp.desc()).first()
        if data:
            latest_data[station.id] = data
    
    # Calcul de la température moyenne sur toutes les stations
    avg_temp = 0
    if latest_data:
        avg_temp = sum(data.temperature for data in latest_data.values()) / len(latest_data)
    
    return render_template('index.html', 
                          stations=stations, 
                          latest_data=latest_data, 
                          avg_temp=avg_temp)



@main_bp.route('/forecasts')
def forecasts():
    # Récupération des stations
    stations = WeatherStation.query.all()
    
    # Prévisions plus avancées
    forecasts = {}
    
    for station in stations:
        # Récupérer les données des 10 derniers jours pour faire des prédictions
        historical = WeatherData.query.filter_by(station_id=station.id).order_by(WeatherData.timestamp.desc()).limit(10).all()
        
        # Utiliser notre fonction de prédiction
        station_forecast = predict_temperature(historical, days_ahead=3)
        
        # Ajouter quelques données supplémentaires aux prévisions
        for pred in station_forecast:
            # Simuler d'autres données comme l'humidité et les précipitations
            day_index = station_forecast.index(pred)
            pred['humidity'] = max(60, min(90, 75 + (day_index - 1) * 5))
            pred['precipitation'] = max(0, min(15, day_index * 2.5))
        
        forecasts[station.id] = station_forecast
    
    return render_template('forecasts.html', stations=stations, forecasts=forecasts)

@main_bp.route('/historical')
def historical():
    # Récupération des stations
    stations = WeatherStation.query.all()
    selected_station_id = request.args.get('station', type=int)
    
    # Si aucune station n'est sélectionnée, prendre la première
    if not selected_station_id and stations:
        selected_station_id = stations[0].id
    
    # Récupération des données historiques pour la station sélectionnée
    historical_data = []
    if selected_station_id:
        historical_data = WeatherData.query.filter_by(station_id=selected_station_id).order_by(WeatherData.timestamp).all()
    
    # Préparation des données pour le graphique
    dates = [data.timestamp.strftime('%d/%m/%Y') for data in historical_data]
    temperatures = [data.temperature for data in historical_data]
    precipitations = [data.precipitation for data in historical_data]
    
    return render_template('historical.html', 
                          stations=stations, 
                          selected_station_id=selected_station_id,
                          historical_data=historical_data,
                          dates=dates,
                          temperatures=temperatures,
                          precipitations=precipitations)

@main_bp.route('/agriculture')
def agriculture():
    # Code de votre route agriculture...
    return render_template('agriculture.html')

@main_bp.route('/alerts')
def alerts():
    # Code de votre route alerts...
    return render_template('alerts.html')

# Puis toutes vos autres routes pour le dashboard...

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération des statistiques
    stats = {}
    
    # Nombre de stations
    stats['stations_count'] = WeatherStation.query.count()
    
    # Nombre d'enregistrements météo
    stats['weather_data_count'] = WeatherData.query.count()
    
    # Nombre d'utilisateurs
    stats['users_count'] = User.query.count()
    
    # Derniers enregistrements météo
    latest_data = WeatherData.query.order_by(WeatherData.timestamp.desc()).limit(10).all()
    
    # Stations
    stations = WeatherStation.query.all()
    
    # Utilisateurs
    users = User.query.all()
    
    # Calcul de la température moyenne (avec vérification)
    avg_temp = None
    temp_data = WeatherData.query.order_by(WeatherData.timestamp.desc()).limit(50).all()
    if temp_data:
        temperatures = [data.temperature for data in temp_data if data.temperature is not None]
        if temperatures:
            avg_temp = sum(temperatures) / len(temperatures)
    
    return render_template('dashboard/index.html', 
                          stats=stats,
                          latest_data=latest_data,
                          stations=stations,
                          users=users,
                          avg_temp=avg_temp)


@main_bp.route('/dashboard/station/<int:id>')
@login_required
def station_detail(id):
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération de la station
    station = WeatherStation.query.get_or_404(id)
    
    # Récupération des données météo de la station
    weather_data = WeatherData.query.filter_by(station_id=id).order_by(WeatherData.timestamp.desc()).limit(30).all()
    
    return render_template('dashboard/station_detail.html', 
                          station=station,
                          weather_data=weather_data)

@main_bp.route('/dashboard/export_data', methods=['GET'])
@login_required
def export_data():
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération des données à exporter
    station_id = request.args.get('station_id', type=int)
    
    if station_id:
        # Exporter les données d'une station spécifique
        station = WeatherStation.query.get_or_404(station_id)
        weather_data = WeatherData.query.filter_by(station_id=station_id).order_by(WeatherData.timestamp).all()
        filename = f"data_{station.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        # Exporter toutes les données
        weather_data = WeatherData.query.order_by(WeatherData.timestamp).all()
        filename = f"data_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Création du CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow(['ID', 'Station', 'Date', 'Température', 'Humidité', 'Pression', 'Vitesse du vent', 'Direction du vent', 'Précipitations'])
    
    # Données
    for data in weather_data:
        station = WeatherStation.query.get(data.station_id)
        writer.writerow([
            data.id,
            station.name,
            data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            data.temperature,
            data.humidity,
            data.pressure,
            data.wind_speed,
            data.wind_direction,
            data.precipitation
        ])
    
    # Préparation de la réponse
    output.seek(0)
    
    return jsonify({
        'data': output.getvalue(),
        'filename': filename
    })

@main_bp.route('/dashboard/add_station', methods=['POST'])
@login_required
def add_station():
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération des données du formulaire
    name = request.form.get('name')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    altitude = request.form.get('altitude')
    region = request.form.get('region')
    
    # Vérification des données
    if not name or not latitude or not longitude:
        flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Création de la station
    station = WeatherStation(
        name=name,
        latitude=float(latitude),
        longitude=float(longitude),
        altitude=float(altitude) if altitude else None,
        region=region
    )
    
    # Enregistrement de la station
    db.session.add(station)
    db.session.commit()
    
    flash(f'La station {name} a été ajoutée avec succès.', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard/add_data', methods=['POST'])
@login_required
def add_data():
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération des données du formulaire
    station_id = request.form.get('station_id')
    date_str = request.form.get('date')
    temperature = request.form.get('temperature')
    humidity = request.form.get('humidity')
    pressure = request.form.get('pressure')
    wind_speed = request.form.get('wind_speed')
    wind_direction = request.form.get('wind_direction')
    precipitation = request.form.get('precipitation')
    
    # Vérification des données
    if not station_id or not date_str or not temperature:
        flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Conversion de la date
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        flash('Format de date invalide. Utilisez le format YYYY-MM-DD.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Création des données météo
    weather_data = WeatherData(
        station_id=int(station_id),
        timestamp=date,
        temperature=float(temperature),
        humidity=float(humidity) if humidity else None,
        pressure=float(pressure) if pressure else None,
        wind_speed=float(wind_speed) if wind_speed else None,
        wind_direction=float(wind_direction) if wind_direction else None,
        precipitation=float(precipitation) if precipitation else None
    )
    
    # Enregistrement des données
    db.session.add(weather_data)
    db.session.commit()
    
    flash('Les données météorologiques ont été ajoutées avec succès.', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard/manage_users')
@login_required
def manage_users():
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération des utilisateurs
    users = User.query.all()
    
    return render_template('dashboard/manage_users.html', users=users)

@main_bp.route('/dashboard/toggle_user_role/<int:id>')
@login_required
def toggle_user_role(id):
    # Vérifier si l'utilisateur est un administrateur
    if current_user.role != 'admin':
        flash('Accès non autorisé. Vous devez être administrateur pour accéder à cette page.', 'danger')
        return redirect(url_for('main.index'))
    
    # Récupération de l'utilisateur
    user = User.query.get_or_404(id)
    
    # Protection contre la modification de son propre rôle
    if user.id == current_user.id:
        flash('Vous ne pouvez pas modifier votre propre rôle.', 'danger')
        return redirect(url_for('main.manage_users'))
    
    # Modification du rôle
    if user.role == 'admin':
        user.role = 'user'
    else:
        user.role = 'admin'
    
    # Enregistrement des modifications
    db.session.commit()
    
    flash(f'Le rôle de {user.username} a été modifié avec succès.', 'success')
    return redirect(url_for('main.manage_users'))


@main_bp.route('/statistics')
def statistics():
    """Page de statistiques et analyses météorologiques"""
    # Récupération des stations
    stations = WeatherStation.query.all()
    
    # Récupérer les données météo les plus récentes pour chaque station
    latest_data = {}
    for station in stations:
        data = WeatherData.query.filter_by(station_id=station.id).order_by(WeatherData.timestamp.desc()).first()
        if data:
            latest_data[station.id] = data
    
    return render_template('statistics.html', 
                           stations=stations, 
                           latest_data=latest_data)

@main_bp.route('/api-docs')
def api_docs():
    """Page de documentation de l'API"""
    return render_template('api-docs.html')

@main_bp.route('/aviation')
def aviation():
    return render_template('aviation.html')

@main_bp.route('/maritime')
def maritime():
    return render_template('maritime.html')