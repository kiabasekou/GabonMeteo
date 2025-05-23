import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.weather_data import WeatherStation
from app.models.aviation_data import TurbulenceData
from app.models.maritime_data import MaritimeData
from app.modules.aviation.turbulence import TurbulenceIndex
from app.modules.maritime.sea_state import SeaStateCalculator
from datetime import datetime, timedelta
import random
import math

app = create_app()

with app.app_context():
    print("🚀 Initialisation des données pour les modules Aviation et Maritime...")
    
    # Récupérer toutes les stations
    stations = WeatherStation.query.all()
    
    if not stations:
        print("❌ Aucune station trouvée. Importez d'abord des données météo.")
        exit()
    
    # Ajouter des données pour chaque station
    for station in stations:
        print(f"\n📍 Station: {station.name}")
        
        # Générer des données pour les dernières 24 heures
        for i in range(24):
            timestamp = datetime.utcnow() - timedelta(hours=i)
            
            # === DONNÉES AVIATION ===
            wind_speed = random.uniform(5, 35)  # 5-35 nœuds
            wind_direction = random.uniform(0, 360)
            wind_direction_variance = random.uniform(0, 20)
            pressure_gradient = random.uniform(-1, 1)
            temperature_gradient = random.uniform(-2, 2)
            
            # Calculer l'indice de turbulence
            turbulence_index = TurbulenceIndex.calculate_turbulence_risk(
                wind_speed,
                wind_direction_variance,
                pressure_gradient,
                temperature_gradient
            )
            
            severity = TurbulenceIndex.get_turbulence_severity(turbulence_index)
            
            turbulence_data = TurbulenceData(
                station_id=station.id,
                timestamp=timestamp,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                wind_direction_variance=wind_direction_variance,
                pressure_gradient=pressure_gradient,
                temperature_gradient=temperature_gradient,
                turbulence_index=turbulence_index,
                turbulence_level=severity['level']
            )
            
            db.session.add(turbulence_data)
            
            # === DONNÉES MARITIMES ===
            # Ne générer des données maritimes que pour les stations côtières
            coastal_regions = ['Ogooué-Maritime', 'Estuaire']
            if station.region in coastal_regions:
                wind_duration = random.uniform(6, 24)  # 6-24 heures
                fetch_distance = random.uniform(20, 200)  # 20-200 km
                
                # Calculer l'état de la mer
                sea_state = SeaStateCalculator.calculate_sea_state(
                    wind_speed, wind_duration, fetch_distance
                )
                
                # Calculer la hauteur des vagues
                sea_state_info = SeaStateCalculator.get_sea_state_info(sea_state)
                wave_height = random.uniform(
                    sea_state_info['height_range'][0],
                    min(sea_state_info['height_range'][1], 15)
                )
                
                # Calculer la période des vagues
                wave_period = SeaStateCalculator.calculate_wave_period(wave_height)
                
                # Simuler la marée
                tide_phase = (i / 12.416) * 2 * math.pi
                tide_height = 2.0 + 1.5 * math.sin(tide_phase)
                
                maritime_data = MaritimeData(
                    station_id=station.id,
                    timestamp=timestamp,
                    wave_height=round(wave_height, 1),
                    wave_period=wave_period,
                    wave_direction=random.uniform(0, 360),
                    sea_state=sea_state,
                    tide_height=round(tide_height, 1),
                    tide_direction='montante' if math.sin(tide_phase) >= 0 else 'descendante',
                    navigation_safety=SeaStateCalculator.calculate_navigation_safety(
                        sea_state, wind_speed, random.uniform(2, 10)
                    )['level'],
                    surface_current_speed=random.uniform(0.5, 3.0),
                    surface_current_direction=random.uniform(0, 360)
                )
                
                db.session.add(maritime_data)
        
        # Commit pour chaque station
        db.session.commit()
        print(f"  ✅ Données ajoutées pour {station.name}")
    
    print("\n🎉 Toutes les données ont été ajoutées avec succès !")
    
    # Afficher un résumé
    turbulence_count = TurbulenceData.query.count()
    maritime_count = MaritimeData.query.count()
    
    print(f"\n📊 Résumé:")
    print(f"  - Données de turbulence: {turbulence_count} enregistrements")
    print(f"  - Données maritimes: {maritime_count} enregistrements")