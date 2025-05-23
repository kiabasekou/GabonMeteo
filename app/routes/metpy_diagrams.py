# app/routes/metpy_diagrams.py
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import metpy.calc as mpcalc
from metpy.units import units
from metpy.plots import SkewT, Hodograph
import metpy.constants as constants
from app.models.weather_data import WeatherStation, WeatherData
from app.extensions import db
import io
import base64
import matplotlib
matplotlib.use('Agg')

metpy_diagrams_bp = Blueprint('metpy_diagrams', __name__, url_prefix='/api/metpy/diagrams')

@metpy_diagrams_bp.route('/skewt/<int:station_id>')
@login_required
def generate_skewt(station_id):
    """Génère un diagramme Skew-T log-P"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données récentes pour simulation profil vertical
        recent_data = WeatherData.query.filter_by(station_id=station_id)\
                                     .order_by(WeatherData.timestamp.desc())\
                                     .limit(1).first()
        
        if not recent_data:
            return jsonify({'error': 'Aucune donnée disponible'}), 404
        
        # Simulation d'un profil vertical (approximation)
        # En réalité, il faudrait des données de radiosondage
        pressure_levels = np.array([1000, 925, 850, 700, 500, 400, 300, 250, 200, 150, 100]) * units.hPa
        
        # Température de surface
        surface_temp = recent_data.temperature * units.celsius
        surface_pressure = recent_data.pressure * units.hPa
        surface_humidity = recent_data.humidity * units.percent
        
        # Génération profil vertical approximatif
        # Gradient thermique standard : -6.5°C/km jusqu'à tropopause
        altitudes = mpcalc.pressure_to_height_std(pressure_levels)
        
        # Profil de température (adiabatique sec puis humide)
        temperatures = []
        dewpoints = []
        
        surface_dewpoint = mpcalc.dewpoint_from_relative_humidity(surface_temp, surface_humidity)
        
        for i, p in enumerate(pressure_levels):
            if p >= surface_pressure:
                # À la surface
                temp = surface_temp
                dewp = surface_dewpoint
            else:
                # Profil adiabatique sec approximé
                temp = mpcalc.dry_lapse(surface_pressure, surface_temp, p)
                # Décroissance du point de rosée (approximation)
                dewp = surface_dewpoint - (surface_pressure - p) * 0.02 * units.celsius
            
            temperatures.append(temp.to('celsius'))
            dewpoints.append(dewp.to('celsius'))
        
        temperatures = np.array([t.magnitude for t in temperatures]) * units.celsius
        dewpoints = np.array([d.magnitude for d in dewpoints]) * units.celsius
        
        # Création du diagramme Skew-T
        fig = plt.figure(figsize=(9, 12))
        skew = SkewT(fig, rotation=45)
        
        # Tracé température et point de rosée
        skew.plot(pressure_levels, temperatures, 'r-', linewidth=2, label='Température')
        skew.plot(pressure_levels, dewpoints, 'g-', linewidth=2, label='Point de rosée')
        
        # Calcul et tracé de la parcelle d'air soulevée
        parcel_prof = mpcalc.parcel_profile(pressure_levels, temperatures[0], dewpoints[0])
        skew.plot(pressure_levels, parcel_prof, 'k--', linewidth=2, label='Parcelle soulevée')
        
        # Zones d'instabilité (CAPE et CIN)
        try:
            cape, cin = mpcalc.cape_cin(pressure_levels, temperatures, dewpoints, parcel_prof)
            
            # Mise en évidence des zones CAPE et CIN
            positive_cape = np.where(parcel_prof > temperatures)[0]
            if len(positive_cape) > 0:
                skew.ax.fill_betweenx(pressure_levels[positive_cape], 
                                    temperatures[positive_cape].magnitude,
                                    parcel_prof[positive_cape].magnitude,
                                    alpha=0.3, color='red', label=f'CAPE: {cape:.0f} J/kg')
            
            negative_cin = np.where(parcel_prof < temperatures)[0]
            if len(negative_cin) > 0:
                skew.ax.fill_betweenx(pressure_levels[negative_cin], 
                                    temperatures[negative_cin].magnitude,
                                    parcel_prof[negative_cin].magnitude,
                                    alpha=0.3, color='blue', label=f'CIN: {cin:.0f} J/kg')
        except:
            cape, cin = 0 * units('J/kg'), 0 * units('J/kg')
        
        # Vent (simulation barbes de vent)
        wind_speed = recent_data.wind_speed * units('m/s') if recent_data.wind_speed else 0 * units('m/s')
        wind_dir = recent_data.wind_direction * units.degrees if recent_data.wind_direction else 0 * units.degrees
        
        # Barbes de vent simulées à différents niveaux
        wind_speeds = np.full_like(pressure_levels, wind_speed.magnitude) * units('m/s')
        wind_dirs = np.full_like(pressure_levels, wind_dir.magnitude) * units.degrees
        
        # Variation du vent avec l'altitude (simulation)
        for i in range(len(wind_speeds)):
            wind_speeds[i] = wind_speed * (1 + i * 0.1)
            wind_dirs[i] = wind_dir + i * 5 * units.degrees  # Rotation avec altitude
        
        # Barbes de vent sur le diagramme
        u_wind, v_wind = mpcalc.wind_components(wind_speeds, wind_dirs)
        skew.plot_barbs(pressure_levels[::2], u_wind[::2], v_wind[::2])
        
        # Configuration du diagramme
        skew.ax.set_ylim(1000, 100)
        skew.ax.set_xlim(-40, 60)
        
        # Lignes de référence
        skew.plot_dry_adiabats(t0=np.arange(233, 533, 10) * units.kelvin, alpha=0.25)
        skew.plot_moist_adiabats(t0=np.arange(233, 400, 5) * units.kelvin, alpha=0.25)
        skew.plot_mixing_lines(pressure=np.arange(1000, 99, -100) * units.hPa, alpha=0.25)
        
        # Titre et légendes
        plt.title(f'Diagramme Skew-T - {station.name}\n{recent_data.timestamp.strftime("%Y-%m-%d %H:%M UTC")}', 
                 fontsize=14, fontweight='bold')
        skew.ax.legend(loc='upper right')
        
        # Informations météo dans un coin
        info_text = f"""Conditions de surface:
T: {surface_temp:.1f}
Td: {surface_dewpoint:.1f} 
P: {surface_pressure:.1f}
RH: {surface_humidity:.0f}
Vent: {wind_speed:.1f} m/s @ {wind_dir:.0f}°

Indices:
CAPE: {cape:.0f} J/kg
CIN: {cin:.0f} J/kg"""
        
        skew.ax.text(0.02, 0.98, info_text, transform=skew.ax.transAxes, 
                    verticalalignment='top', fontsize=10, 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Sauvegarde en base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'diagram_type': 'skew_t',
            'image': f'data:image/png;base64,{image_base64}',
            'parameters': {
                'cape': float(cape.magnitude),
                'cin': float(cin.magnitude),
                'surface_temperature': float(surface_temp.magnitude),
                'surface_dewpoint': float(surface_dewpoint.magnitude),
                'surface_pressure': float(surface_pressure.magnitude)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur génération Skew-T: {str(e)}'}), 500

@metpy_diagrams_bp.route('/hodograph/<int:station_id>')
@login_required
def generate_hodograph(station_id):
    """Génère un hodographe du vent"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données de vent sur 24h
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        wind_data = WeatherData.query.filter(
            WeatherData.station_id == station_id,
            WeatherData.timestamp >= start_time,
            WeatherData.wind_speed.isnot(None),
            WeatherData.wind_direction.isnot(None)
        ).order_by(WeatherData.timestamp).all()
        
        if len(wind_data) < 6:
            return jsonify({'error': 'Données de vent insuffisantes'}), 400
        
        # Simulation profil vertical de vent
        pressure_levels = np.array([1000, 925, 850, 700, 500, 400, 300, 250]) * units.hPa
        
        # Utiliser les données récentes pour extrapoler
        recent_speeds = [data.wind_speed for data in wind_data[-6:]]
        recent_dirs = [data.wind_direction for data in wind_data[-6:]]
        
        base_speed = np.mean(recent_speeds) * units('m/s')
        base_dir = np.mean(recent_dirs) * units.degrees
        
        # Simulation profil vertical (augmentation avec altitude + rotation)
        wind_speeds = []
        wind_dirs = []
        
        for i, p in enumerate(pressure_levels):
            # Augmentation vitesse avec altitude
            speed = base_speed * (1 + i * 0.15)
            # Rotation horaire avec altitude (cisaillement typique)
            direction = base_dir + i * 20 * units.degrees
            
            wind_speeds.append(speed)
            wind_dirs.append(direction)
        
        wind_speeds = np.array([s.magnitude for s in wind_speeds]) * units('m/s')
        wind_dirs = np.array([d.magnitude for d in wind_dirs]) * units.degrees
        
        # Conversion en composantes U et V
        u_wind, v_wind = mpcalc.wind_components(wind_speeds, wind_dirs)
        
        # Création hodographe
        fig, ax = plt.subplots(figsize=(8, 8))
        h = Hodograph(ax, component_range=60)
        
        # Tracé du profil de vent
        h.plot_colormapped(u_wind, v_wind, pressure_levels, linewidth=3)
        
        # Points pour chaque niveau
        for i, (u, v, p) in enumerate(zip(u_wind, v_wind, pressure_levels)):
            ax.plot(u.magnitude, v.magnitude, 'ko', markersize=6)
            ax.annotate(f'{p.magnitude:.0f}', 
                       (u.magnitude, v.magnitude), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9, fontweight='bold')
        
        # Calcul paramètres cisaillement
        # Cisaillement 0-6 km (approximé par niveaux de pression)
        u_sfc, v_sfc = u_wind[0], v_wind[0]  # Surface
        u_6km, v_6km = u_wind[4], v_wind[4]  # ~500 hPa ≈ 6km
        
        bulk_shear = np.sqrt((u_6km - u_sfc)**2 + (v_6km - v_sfc)**2)
        
        # Storm motion (approximation Bunkers)
        mean_u = np.mean(u_wind[:4])  # 0-6 km moyen
        mean_v = np.mean(v_wind[:4])
        
        # Déviation perpendiculaire au cisaillement moyen
        shear_u = u_6km - u_sfc
        shear_v = v_6km - v_sfc
        shear_mag = np.sqrt(shear_u**2 + shear_v**2)
        
        if shear_mag > 0:
            # Mouvement tempête droite (supercellule droite)
            dev_factor = 7.5 * units('m/s')  # Déviation standard
            storm_u_right = mean_u + dev_factor * (-shear_v/shear_mag)
            storm_v_right = mean_v + dev_factor * (shear_u/shear_mag)
            
            # Mouvement tempête gauche
            storm_u_left = mean_u - dev_factor * (-shear_v/shear_mag)
            storm_v_left = mean_v - dev_factor * (shear_u/shear_mag)
            
            # Marqueurs mouvement tempêtes
            ax.plot(storm_u_right.magnitude, storm_v_right.magnitude, 'r*', 
                   markersize=15, label='Supercellule droite')
            ax.plot(storm_u_left.magnitude, storm_v_left.magnitude, 'b*', 
                   markersize=15, label='Supercellule gauche')
        
        # Vecteur cisaillement total
        ax.arrow(u_sfc.magnitude, v_sfc.magnitude, 
                shear_u.magnitude, shear_v.magnitude,
                head_width=2, head_length=2, fc='purple', ec='purple',
                label=f'Cisaillement: {bulk_shear:.1f} m/s')
        
        # Configuration
        ax.set_title(f'Hodographe - {station.name}\n{wind_data[-1].timestamp.strftime("%Y-%m-%d %H:%M UTC")}', 
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.5)
        
        # Informations dans un coin
        info_text = f"""Paramètres:
Cisaillement 0-6km: {bulk_shear:.1f} m/s
Vent surface: {wind_speeds[0]:.1f} m/s @ {wind_dirs[0]:.0f}°
Vent 500hPa: {wind_speeds[4]:.1f} m/s @ {wind_dirs[4]:.0f}°
Helicity: {calculate_storm_relative_helicity(u_wind, v_wind, storm_u_right, storm_v_right):.0f} m²/s²"""
        
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Sauvegarde
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'diagram_type': 'hodograph',
            'image': f'data:image/png;base64,{image_base64}',
            'parameters': {
                'bulk_shear_0_6km': float(bulk_shear.magnitude),
                'surface_wind_speed': float(wind_speeds[0].magnitude),
                'surface_wind_direction': float(wind_dirs[0].magnitude),
                'storm_motion_right': [float(storm_u_right.magnitude), float(storm_v_right.magnitude)] if shear_mag > 0 else None,
                'storm_motion_left': [float(storm_u_left.magnitude), float(storm_v_left.magnitude)] if shear_mag > 0 else None
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur génération hodographe: {str(e)}'}), 500

@metpy_diagrams_bp.route('/meteogram/<int:station_id>')
@login_required
def generate_meteogram(station_id):
    """Génère un météogramme avancé"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer 7 jours de données
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        weather_data = WeatherData.query.filter(
            WeatherData.station_id == station_id,
            WeatherData.timestamp >= start_time
        ).order_by(WeatherData.timestamp).all()
        
        if len(weather_data) < 24:
            return jsonify({'error': 'Données insuffisantes (minimum 24h)'}), 400
        
        # Extraction données
        timestamps = [data.timestamp for data in weather_data]
        temperatures = [data.temperature for data in weather_data]
        pressures = [data.pressure for data in weather_data]
        humidities = [data.humidity for data in weather_data]
        wind_speeds = [data.wind_speed for data in weather_data]
        wind_dirs = [data.wind_direction for data in weather_data]
        precipitations = [data.precipitation for data in weather_data]
        
        # Calculs MetPy
        temp_array = np.array(temperatures) * units.celsius
        pressure_array = np.array(pressures) * units.hPa
        humidity_array = np.array(humidities) * units.percent
        
        # Point de rosée
        dewpoints = mpcalc.dewpoint_from_relative_humidity(temp_array, humidity_array)
        
        # Température ressentie
        wind_speed_array = np.array(wind_speeds) * units('m/s')
        heat_index = mpcalc.heat_index(temp_array, humidity_array)
        wind_chill = mpcalc.windchill(temp_array, wind_speed_array)
        
        # Création météogramme multi-panneaux
        fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
        
        # Panneau 1: Température et point de rosée
        ax1 = axes[0]
        ax1.plot(timestamps, temperatures, 'r-', linewidth=2, label='Température')
        ax1.plot(timestamps, [d.to('celsius').magnitude for d in dewpoints], 'g-', linewidth=2, label='Point de rosée')
        ax1.plot(timestamps, [hi.to('celsius').magnitude for hi in heat_index], 'orange', linewidth=1, alpha=0.7, label='Indice chaleur')
        ax1.fill_between(timestamps, temperatures, [d.to('celsius').magnitude for d in dewpoints], alpha=0.3, color='lightblue')
        ax1.set_ylabel('Température (°C)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.5)
        ax1.set_title(f'Météogramme - {station.name}', fontsize=14, fontweight='bold')
        
        # Panneau 2: Pression et tendance
        ax2 = axes[1]
        ax2.plot(timestamps, pressures, 'b-', linewidth=2)
        ax2.set_ylabel('Pression (hPa)')
        ax2.grid(True, alpha=0.5)
        
        # Tendance pression (dérivée)
        if len(pressures) > 3:
            pressure_trend = np.gradient(pressures)
            ax2_twin = ax2.twinx()
            ax2_twin.plot(timestamps, pressure_trend, 'purple', linewidth=1, alpha=0.7)
            ax2_twin.set_ylabel('Tendance pression', color='purple')
            ax2_twin.tick_params(axis='y', labelcolor='purple')
        
        # Panneau 3: Vent
        ax3 = axes[2]
        ax3.plot(timestamps, wind_speeds, 'brown', linewidth=2, label='Vitesse')
        ax3.set_ylabel('Vent (m/s)')
        ax3.grid(True, alpha=0.5)
        
        # Barbes de vent (échantillonnées)
        sample_indices = range(0, len(timestamps), max(1, len(timestamps)//20))
        sample_times = [timestamps[i] for i in sample_indices]
        sample_u = []
        sample_v = []
        
        for i in sample_indices:
            if wind_speeds[i] is not None and wind_dirs[i] is not None:
                u, v = mpcalc.wind_components(wind_speeds[i] * units('m/s'), 
                                            wind_dirs[i] * units.degrees)
                sample_u.append(u.magnitude)
                sample_v.append(v.magnitude)
            else:
                sample_u.append(0)
                sample_v.append(0)
        
        # Conversion des dates pour barbes
        sample_nums = mdates.date2num(sample_times)
        y_pos = np.full_like(sample_nums, max(wind_speeds)*0.8)
        ax3.barbs(sample_nums, y_pos, sample_u, sample_v, length=6, barbcolor='darkred')
        
        # Panneau 4: Précipitations et humidité
        ax4 = axes[3]
        bars = ax4.bar(timestamps, precipitations, width=0.02, alpha=0.7, color='blue', label='Précipitations')
        ax4.set_ylabel('Précipitations (mm)')
        ax4.set_xlabel('Temps')
        
        # Humidité sur axe secondaire
        ax4_twin = ax4.twinx()
        ax4_twin.plot(timestamps, humidities, 'green', linewidth=2, alpha=0.7, label='Humidité')
        ax4_twin.set_ylabel('Humidité (%)', color='green')
        ax4_twin.tick_params(axis='y', labelcolor='green')
        ax4_twin.set_ylim(0, 100)
        
        # Configuration axes temporels
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Sauvegarde
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        # Statistiques période
        stats = {
            'temperature': {
                'min': float(np.min(temperatures)),
                'max': float(np.max(temperatures)),
                'mean': float(np.mean(temperatures))
            },
            'pressure': {
                'min': float(np.min(pressures)),
                'max': float(np.max(pressures)),
                'trend': float(np.mean(np.gradient(pressures)))
            },
            'wind': {
                'max_speed': float(np.max(wind_speeds)),
                'mean_speed': float(np.mean(wind_speeds))
            },
            'precipitation': {
                'total': float(np.sum(precipitations)),
                'max_rate': float(np.max(precipitations))
            }
        }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'diagram_type': 'meteogram',
            'image': f'data:image/png;base64,{image_base64}',
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'data_points': len(weather_data)
            },
            'statistics': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur génération météogramme: {str(e)}'}), 500

def calculate_storm_relative_helicity(u_wind, v_wind, storm_u, storm_v):
    """Calcule l'hélicité relative à la tempête"""
    try:
        # Vent relatif à la tempête
        u_rel = u_wind - storm_u
        v_rel = v_wind - storm_v
        
        # Calcul hélicité (approximation)
        helicity = 0
        for i in range(len(u_wind)-1):
            du = u_rel[i+1] - u_rel[i]
            dv = v_rel[i+1] - v_rel[i]
            helicity += u_rel[i] * dv - v_rel[i] * du
        
        return helicity.magnitude if hasattr(helicity, 'magnitude') else helicity
    except:
        return 0

@metpy_diagrams_bp.route('/composite-index/<int:station_id>')
@login_required
def composite_index_diagram(station_id):
    """Génère un diagramme des indices composites"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données sur plusieurs jours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=5)
        
        weather_data = WeatherData.query.filter(
            WeatherData.station_id == station_id,
            WeatherData.timestamp >= start_time
        ).order_by(WeatherData.timestamp).all()
        
        if len(weather_data) < 24:
            return jsonify({'error': 'Données insuffisantes'}), 400
        
        # Calculs des indices pour chaque point temporel
        timestamps = []
        cape_values = []
        lifted_index_values = []
        k_index_values = []
        storm_prob_values = []
        
        for data in weather_data:
            if data.temperature and data.humidity and data.pressure:
                timestamps.append(data.timestamp)
                
                # CAPE approximé
                temp = data.temperature * units.celsius
                humidity = data.humidity * units.percent
                pressure = data.pressure * units.hPa
                
                dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, humidity)
                virtual_temp = mpcalc.virtual_temperature(temp, 
                    mpcalc.mixing_ratio_from_relative_humidity(pressure, temp, humidity))
                
                cape_approx = max(0, (virtual_temp.to('kelvin').magnitude - 273.15) * 100)
                cape_values.append(cape_approx)
                
                # Lifted Index approximé
                lifted_temp = temp - 15 * units.celsius  # Approximation 500 hPa
                li = 15 - lifted_temp.magnitude
                lifted_index_values.append(li)
                
                # K-Index approximé
                k_index = (temp.magnitude - 20) + dewpoint.to('celsius').magnitude - 5
                k_index_values.append(k_index)
                
                # Probabilité orage
                storm_prob = min(100, max(0, 
                    (cape_approx/50) + (humidity.magnitude - 50) + (k_index - 15)
                ))
                storm_prob_values.append(storm_prob)
        
        # Création graphique composite
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Indices Composites de Convection - {station.name}', fontsize=16, fontweight='bold')
        
        # CAPE
        ax1 = axes[0, 0]
        ax1.plot(timestamps, cape_values, 'red', linewidth=2)
        ax1.fill_between(timestamps, cape_values, alpha=0.3, color='red')
        ax1.set_ylabel('CAPE (J/kg)')
        ax1.set_title('Énergie Convective (CAPE)')
        ax1.grid(True, alpha=0.5)
        ax1.axhline(y=1000, color='orange', linestyle='--', alpha=0.7, label='Seuil modéré')
        ax1.axhline(y=2500, color='red', linestyle='--', alpha=0.7, label='Seuil fort')
        ax1.legend()
        
        # Lifted Index
        ax2 = axes[0, 1]
        ax2.plot(timestamps, lifted_index_values, 'blue', linewidth=2)
        ax2.fill_between(timestamps, lifted_index_values, alpha=0.3, color='blue')
        ax2.set_ylabel('Lifted Index (°C)')
        ax2.set_title('Indice de Soulèvement')
        ax2.grid(True, alpha=0.5)
        ax2.axhline(y=0, color='orange', linestyle='--', alpha=0.7, label='Instable')
        ax2.axhline(y=-3, color='red', linestyle='--', alpha=0.7, label='Très instable')
        ax2.legend()
        
        # K-Index
        ax3 = axes[1, 0]
        ax3.plot(timestamps, k_index_values, 'green', linewidth=2)
        ax3.fill_between(timestamps, k_index_values, alpha=0.3, color='green')
        ax3.set_ylabel('K-Index (°C)')
        ax3.set_title('Indice K')
        ax3.grid(True, alpha=0.5)
        ax3.axhline(y=20, color='orange', linestyle='--', alpha=0.7, label='Orages isolés')
        ax3.axhline(y=30, color='red', linestyle='--', alpha=0.7, label='Orages nombreux')
        ax3.legend()
        
        # Probabilité orage
        ax4 = axes[1, 1]
        colors = ['green' if p < 30 else 'orange' if p < 70 else 'red' for p in storm_prob_values]
        ax4.scatter(timestamps, storm_prob_values, c=colors, s=20)
        ax4.plot(timestamps, storm_prob_values, 'black', linewidth=1, alpha=0.5)
        ax4.set_ylabel('Probabilité (%)')
        ax4.set_title('Probabilité d\'Orages')
        ax4.set_ylim(0, 100)
        ax4.grid(True, alpha=0.5)
        
        # Configuration axes temporels
        for ax in axes.flat:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Sauvegarde
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        # Valeurs actuelles
        current_indices = {
            'cape': float(cape_values[-1]) if cape_values else 0,
            'lifted_index': float(lifted_index_values[-1]) if lifted_index_values else 0,
            'k_index': float(k_index_values[-1]) if k_index_values else 0,
            'storm_probability': float(storm_prob_values[-1]) if storm_prob_values else 0
        }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'diagram_type': 'composite_indices',
            'image': f'data:image/png;base64,{image_base64}',
            'current_indices': current_indices,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'data_points': len(timestamps)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur génération indices composites: {str(e)}'}), 500