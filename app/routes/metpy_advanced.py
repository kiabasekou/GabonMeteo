# app/routes/metpy_advanced.py
from flask import Blueprint, jsonify, request
from flask_login import login_required
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import metpy.calc as mpcalc
from metpy.units import units
import metpy.constants as constants
from metpy.plots import SkewT
import xarray as xr
from app.models.weather_data import WeatherStation, WeatherData
from app.extensions import db
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif
import io
import base64

metpy_advanced_bp = Blueprint('metpy_advanced', __name__, url_prefix='/api/metpy')

@metpy_advanced_bp.route('/atmospheric-stability/<int:station_id>')
@login_required
def atmospheric_stability(station_id):
    """Calcule la stabilité atmosphérique avec indices avancés"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données récentes (72h)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=72)
        
        weather_data = WeatherData.query.filter(
            WeatherData.station_id == station_id,
            WeatherData.timestamp >= start_time,
            WeatherData.timestamp <= end_time
        ).order_by(WeatherData.timestamp).all()
        
        if len(weather_data) < 10:
            return jsonify({'error': 'Données insuffisantes pour l\'analyse'}), 400
        
        # Conversion en arrays avec unités MetPy
        temperatures = [data.temperature for data in weather_data] * units.celsius
        pressures = [data.pressure for data in weather_data] * units.hPa
        humidities = [data.humidity for data in weather_data] * units.percent
        
        # Calculs de stabilité atmosphérique
        results = {}
        
        # 1. Point de rosée
        dewpoints = mpcalc.dewpoint_from_relative_humidity(temperatures, humidities)
        results['dewpoint_avg'] = float(np.mean(dewpoints.to('celsius').magnitude))
        
        # 2. Température potentielle
        potential_temps = mpcalc.potential_temperature(pressures, temperatures)
        results['potential_temperature_avg'] = float(np.mean(potential_temps.to('kelvin').magnitude))
        
        # 3. Température équivalente potentielle
        equiv_potential_temps = mpcalc.equivalent_potential_temperature(pressures, temperatures, dewpoints)
        results['equiv_potential_temp_avg'] = float(np.mean(equiv_potential_temps.to('kelvin').magnitude))
        
        # 4. Indice de stabilité (gradient de température potentielle)
        temp_gradient = np.gradient(potential_temps.magnitude)
        stability_index = np.mean(temp_gradient)
        
        if stability_index > 0:
            stability_class = "Stable"
            stability_description = "Atmosphère stable - dispersion limitée"
        elif stability_index < -0.5:
            stability_class = "Très Instable"
            stability_description = "Atmosphère très instable - forte convection possible"
        elif stability_index < 0:
            stability_class = "Instable"
            stability_description = "Atmosphère instable - convection modérée"
        else:
            stability_class = "Neutre"
            stability_description = "Atmosphère neutre"
        
        results['stability'] = {
            'index': float(stability_index),
            'class': stability_class,
            'description': stability_description
        }
        
        # 5. Indice de soulèvement (Lifted Index approximé)
        surface_temp = temperatures[-1]
        surface_pressure = pressures[-1]
        surface_dewpoint = dewpoints[-1]
        
        # Calcul température d'une parcelle soulevée à 500 hPa
        lifted_temp = mpcalc.dry_lapse(surface_pressure, surface_temp, 500 * units.hPa)
        lifted_index = 15 * units.celsius - lifted_temp  # Approximation simple
        
        results['lifted_index'] = {
            'value': float(lifted_index.to('celsius').magnitude),
            'interpretation': get_lifted_index_interpretation(lifted_index.magnitude)
        }
        
        # 6. Indice de convection (K-Index approximé)
        if len(temperatures) >= 3:
            temp_850 = temperatures[-1]  # Approximation surface
            temp_500 = temp_850 - 15 * units.celsius  # Estimation 500 hPa
            dewpoint_850 = dewpoints[-1]
            
            k_index = (temp_850 - temp_500) + dewpoint_850 - 5 * units.celsius
            results['k_index'] = {
                'value': float(k_index.to('celsius').magnitude),
                'interpretation': get_k_index_interpretation(k_index.magnitude)
            }
        
        # 7. Indice de cisaillement de vent (approximé)
        wind_speeds = [data.wind_speed for data in weather_data]
        wind_directions = [data.wind_direction for data in weather_data]
        
        if len(wind_speeds) >= 6:
            recent_winds = wind_speeds[-6:]
            wind_shear = np.std(recent_winds)
            results['wind_shear'] = {
                'value': float(wind_shear),
                'interpretation': get_wind_shear_interpretation(wind_shear)
            }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name,
                'coordinates': [station.latitude, station.longitude]
            },
            'analysis_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'data_points': len(weather_data)
            },
            'atmospheric_stability': results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur calcul stabilité: {str(e)}'}), 500

@metpy_advanced_bp.route('/convective-parameters/<int:station_id>')
@login_required 
def convective_parameters(station_id):
    """Calcule les paramètres de convection pour prévision orages"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données récentes
        recent_data = WeatherData.query.filter_by(station_id=station_id)\
                                     .order_by(WeatherData.timestamp.desc())\
                                     .limit(24).all()
        
        if len(recent_data) < 12:
            return jsonify({'error': 'Données insuffisantes'}), 400
        
        # Données actuelles
        current = recent_data[0]
        temperature = current.temperature * units.celsius
        pressure = current.pressure * units.hPa
        humidity = current.humidity * units.percent
        wind_speed = current.wind_speed * units('m/s')
        
        # Calculs convectifs
        results = {}
        
        # 1. CAPE (Convective Available Potential Energy) - approximation
        dewpoint = mpcalc.dewpoint_from_relative_humidity(temperature, humidity)
        
        # Simulation profil vertical (approximation pour surface unique)
        surface_pressure = pressure
        surface_temp = temperature
        
        # Estimation CAPE basique
        virtual_temp = mpcalc.virtual_temperature(temperature, 
                                                mpcalc.mixing_ratio_from_relative_humidity(pressure, temperature, humidity))
        
        # CAPE approximé (méthode simplifiée)
        cape_approx = max(0, (virtual_temp.to('kelvin').magnitude - 273.15) * 100)
        
        results['cape'] = {
            'value': cape_approx,
            'units': 'J/kg',
            'interpretation': get_cape_interpretation(cape_approx)
        }
        
        # 2. CIN (Convective Inhibition) - approximation
        cin_approx = max(0, 50 - cape_approx/10)
        results['cin'] = {
            'value': cin_approx,
            'units': 'J/kg',
            'interpretation': get_cin_interpretation(cin_approx)
        }
        
        # 3. Bulk Richardson Number (BRN)
        # Approximation basée sur les données de surface
        shear_magnitude = 5.0  # m/s (valeur typique)
        if cape_approx > 0:
            brn = cape_approx / (0.5 * shear_magnitude**2)
        else:
            brn = 0
            
        results['bulk_richardson_number'] = {
            'value': float(brn),
            'interpretation': get_brn_interpretation(brn)
        }
        
        # 4. Helicity relative à la tempête (approximation)
        # Basée sur cisaillement de vent et direction
        wind_directions = [data.wind_direction for data in recent_data[:6]]
        dir_shear = np.std(wind_directions) if len(wind_directions) > 1 else 0
        
        storm_relative_helicity = dir_shear * wind_speed.magnitude * 0.1
        results['storm_relative_helicity'] = {
            'value': float(storm_relative_helicity),
            'units': 'm²/s²',
            'interpretation': get_helicity_interpretation(storm_relative_helicity)
        }
        
        # 5. Supercell Composite Parameter
        if cape_approx > 0 and storm_relative_helicity > 0:
            scp = (cape_approx/1000) * (storm_relative_helicity/100) * (shear_magnitude/10)
        else:
            scp = 0
            
        results['supercell_composite'] = {
            'value': float(scp),
            'interpretation': get_scp_interpretation(scp)
        }
        
        # 6. Significant Tornado Parameter
        stp = scp * 0.5 if brn < 45 else scp * 0.1
        results['significant_tornado'] = {
            'value': float(stp),
            'interpretation': get_stp_interpretation(stp)
        }
        
        # 7. Probabilité d'orage (modèle simple)
        thunderstorm_prob = min(100, max(0, 
            (cape_approx/50) + (storm_relative_helicity*2) + 
            (humidity.magnitude - 50) - (cin_approx/10)
        ))
        
        results['thunderstorm_probability'] = {
            'value': float(thunderstorm_prob),
            'units': '%',
            'category': get_storm_probability_category(thunderstorm_prob)
        }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'convective_parameters': results,
            'surface_conditions': {
                'temperature': float(temperature.magnitude),
                'dewpoint': float(dewpoint.to('celsius').magnitude),
                'humidity': float(humidity.magnitude),
                'pressure': float(pressure.magnitude)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur paramètres convectifs: {str(e)}'}), 500

@metpy_advanced_bp.route('/wind-analysis/<int:station_id>')
@login_required
def wind_analysis(station_id):
    """Analyse avancée du vent avec MetPy"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer 48h de données
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=48)
        
        wind_data = WeatherData.query.filter(
            WeatherData.station_id == station_id,
            WeatherData.timestamp >= start_time,
            WeatherData.wind_speed.isnot(None),
            WeatherData.wind_direction.isnot(None)
        ).order_by(WeatherData.timestamp).all()
        
        if len(wind_data) < 10:
            return jsonify({'error': 'Données de vent insuffisantes'}), 400
        
        # Extraction des données
        speeds = np.array([data.wind_speed for data in wind_data]) * units('m/s')
        directions = np.array([data.wind_direction for data in wind_data]) * units.degrees
        timestamps = [data.timestamp for data in wind_data]
        
        # Conversion en composantes U et V
        u_wind, v_wind = mpcalc.wind_components(speeds, directions)
        
        results = {}
        
        # 1. Statistiques de base
        results['basic_stats'] = {
            'mean_speed': float(np.mean(speeds.magnitude)),
            'max_speed': float(np.max(speeds.magnitude)),
            'min_speed': float(np.min(speeds.magnitude)),
            'std_speed': float(np.std(speeds.magnitude)),
            'mean_direction': float(np.mean(directions.magnitude)),
            'direction_variability': float(np.std(directions.magnitude))
        }
        
        # 2. Analyse de persistance
        direction_changes = np.abs(np.diff(directions.magnitude))
        direction_changes[direction_changes > 180] = 360 - direction_changes[direction_changes > 180]
        
        persistence_index = 1 - (np.mean(direction_changes) / 180)
        results['persistence'] = {
            'index': float(persistence_index),
            'interpretation': get_wind_persistence_interpretation(persistence_index)
        }
        
        # 3. Analyse de rafales (approximation)
        speed_changes = np.abs(np.diff(speeds.magnitude))
        gust_factor = np.max(speed_changes) / np.mean(speeds.magnitude) if np.mean(speeds.magnitude) > 0 else 0
        
        results['gustiness'] = {
            'factor': float(gust_factor),
            'max_change': float(np.max(speed_changes)),
            'interpretation': get_gustiness_interpretation(gust_factor)
        }
        
        # 4. Vorticité relative (approximation locale)
        # Gradient de vent approximé
        du_dx = np.gradient(u_wind.magnitude)
        dv_dy = np.gradient(v_wind.magnitude)
        relative_vorticity = dv_dy - du_dx
        
        results['vorticity'] = {
            'mean_relative': float(np.mean(relative_vorticity)),
            'max_relative': float(np.max(relative_vorticity)),
            'interpretation': get_vorticity_interpretation(np.mean(relative_vorticity))
        }
        
        # 5. Divergence du vent (approximation)
        du_dx_div = np.gradient(u_wind.magnitude)
        dv_dy_div = np.gradient(v_wind.magnitude)
        divergence = du_dx_div + dv_dy_div
        
        results['divergence'] = {
            'mean': float(np.mean(divergence)),
            'interpretation': get_divergence_interpretation(np.mean(divergence))
        }
        
        # 6. Rose des vents avancée
        # Distribution par secteurs
        wind_rose_data = {}
        sectors = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        
        for i, sector in enumerate(sectors):
            sector_start = i * 22.5 - 11.25
            sector_end = i * 22.5 + 11.25
            
            # Gérer le passage par 0°
            if sector_start < 0:
                mask = (directions.magnitude >= sector_start + 360) | (directions.magnitude <= sector_end)
            elif sector_end > 360:
                mask = (directions.magnitude >= sector_start) | (directions.magnitude <= sector_end - 360)
            else:
                mask = (directions.magnitude >= sector_start) & (directions.magnitude <= sector_end)
            
            sector_speeds = speeds[mask]
            
            wind_rose_data[sector] = {
                'frequency': float(np.sum(mask) / len(directions) * 100),
                'mean_speed': float(np.mean(sector_speeds.magnitude)) if len(sector_speeds) > 0 else 0,
                'max_speed': float(np.max(sector_speeds.magnitude)) if len(sector_speeds) > 0 else 0
            }
        
        results['wind_rose'] = wind_rose_data
        
        # 7. Prévision de tendance (régression simple)
        if len(speeds) >= 12:
            time_hours = np.arange(len(speeds))
            speed_trend = np.polyfit(time_hours, speeds.magnitude, 1)[0]
            direction_trend = np.polyfit(time_hours, directions.magnitude, 1)[0]
            
            results['trends'] = {
                'speed_trend_per_hour': float(speed_trend),
                'direction_trend_per_hour': float(direction_trend),
                'speed_forecast_6h': float(speeds[-1].magnitude + speed_trend * 6),
                'interpretation': get_wind_trend_interpretation(speed_trend, direction_trend)
            }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'analysis_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'data_points': len(wind_data)
            },
            'wind_analysis': results,
            'current_conditions': {
                'speed': float(speeds[-1].magnitude),
                'direction': float(directions[-1].magnitude),
                'u_component': float(u_wind[-1].magnitude),
                'v_component': float(v_wind[-1].magnitude)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur analyse vent: {str(e)}'}), 500

# Fonctions d'interprétation
def get_lifted_index_interpretation(li_value):
    if li_value > 6:
        return "Très stable - pas de convection"
    elif li_value > 0:
        return "Stable - convection peu probable"
    elif li_value > -3:
        return "Légèrement instable - convection faible possible"
    elif li_value > -6:
        return "Modérément instable - orages possibles"
    else:
        return "Très instable - orages forts probables"

def get_k_index_interpretation(k_value):
    if k_value < 15:
        return "Convection très peu probable"
    elif k_value < 25:
        return "Convection isolée possible"
    elif k_value < 35:
        return "Orages épars probables"
    else:
        return "Orages nombreux probables"

def get_wind_shear_interpretation(shear_value):
    if shear_value < 2:
        return "Cisaillement faible"
    elif shear_value < 5:
        return "Cisaillement modéré"
    else:
        return "Cisaillement fort - turbulence possible"

def get_cape_interpretation(cape_value):
    if cape_value < 1000:
        return "Faible - convection limitée"
    elif cape_value < 2500:
        return "Modérée - orages possibles"
    elif cape_value < 4000:
        return "Forte - orages probables"
    else:
        return "Extrême - orages violents possibles"

def get_cin_interpretation(cin_value):
    if cin_value < 50:
        return "Faible - déclenchement facile"
    elif cin_value < 200:
        return "Modérée - déclenchement plus difficile"
    else:
        return "Forte - inhibition significative"

def get_brn_interpretation(brn_value):
    if brn_value < 10:
        return "Cisaillement dominant - orages linéaires"
    elif brn_value < 45:
        return "Équilibré - supercellules possibles"
    else:
        return "Flottabilité dominante - orages pulsés"

def get_helicity_interpretation(helicity_value):
    if helicity_value < 100:
        return "Faible - rotation peu probable"
    elif helicity_value < 300:
        return "Modérée - rotation possible"
    else:
        return "Forte - rotation probable"

def get_scp_interpretation(scp_value):
    if scp_value < 1:
        return "Supercellules peu probables"
    elif scp_value < 4:
        return "Supercellules possibles"
    else:
        return "Supercellules probables"

def get_stp_interpretation(stp_value):
    if stp_value < 0.5:
        return "Tornades peu probables"
    elif stp_value < 1:
        return "Tornades faibles possibles"
    else:
        return "Tornades significatives possibles"

def get_storm_probability_category(prob):
    if prob < 20:
        return "Faible"
    elif prob < 50:
        return "Modérée"
    elif prob < 80:
        return "Élevée"
    else:
        return "Très élevée"

def get_wind_persistence_interpretation(persistence):
    if persistence > 0.8:
        return "Très persistant - conditions stables"
    elif persistence > 0.6:
        return "Persistant - changements graduels"
    elif persistence > 0.4:
        return "Modérément variable"
    else:
        return "Très variable - changements fréquents"

def get_gustiness_interpretation(gust_factor):
    if gust_factor < 0.3:
        return "Vent régulier"
    elif gust_factor < 0.6:
        return "Modérément rafales"
    else:
        return "Très rafales - turbulence"

def get_vorticity_interpretation(vorticity):
    if abs(vorticity) < 0.01:
        return "Rotation négligeable"
    elif vorticity > 0:
        return "Rotation cyclonique (antihoraire)"
    else:
        return "Rotation anticyclonique (horaire)"

def get_divergence_interpretation(divergence):
    if abs(divergence) < 0.01:
        return "Flux neutre"
    elif divergence > 0:
        return "Divergence - mouvement ascendant favorisé"
    else:
        return "Convergence - mouvement descendant favorisé"

def get_wind_trend_interpretation(speed_trend, direction_trend):
    speed_desc = "en hausse" if speed_trend > 0.1 else "en baisse" if speed_trend < -0.1 else "stable"
    direction_desc = "tournant" if abs(direction_trend) > 2 else "stable"
    return f"Vitesse {speed_desc}, direction {direction_desc}"