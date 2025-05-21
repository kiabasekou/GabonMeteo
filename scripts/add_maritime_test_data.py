# scripts/add_maritime_test_data.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.weather_data import WeatherStation
from app.models.maritime_data import MaritimeData
from app.modules.maritime.sea_state import SeaStateCalculator
from datetime import datetime, timedelta
import random
import math

app = create_app()

with app.app_context():
    # Récupérer les stations (privilégier les stations côtières)
    stations = WeatherStation.query.all()
    
    if not stations:
        print("❌ Aucune station trouvée")
        exit()
    
    print("🌊 Ajout de données maritimes de test...")
    
    for station in stations:
        print(f"  📍 Station: {station.name}")
        
        # Générer des données pour les dernières 72 heures
        for i in range(72):
            timestamp = datetime.utcnow() - timedelta(hours=i)
            
            # Simuler des conditions météo variables
            wind_speed = random.uniform(5, 35)  # 5-35 nœuds
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
                min(sea_state_info['height_range'][1], 15)  # Limiter à 15m
            )
            
            # Calculer la période des vagues
            wave_period = SeaStateCalculator.calculate_wave_period(wave_height)
            
            # Simuler la marée (cycle de 12h25min)
            tide_phase = (i / 12.416) * 2 * math.pi
            tide_height = 2.0 + 1.5 * math.sin(tide_phase)  # Marée entre 0.5m et 3.5m
            
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
    
    print("🎉 Toutes les données maritimes ont été ajoutées avec succès !")