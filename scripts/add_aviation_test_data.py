# scripts/add_aviation_test_data.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.weather_data import WeatherStation
from app.models.aviation_data import TurbulenceData
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    # Récupérer la première station
    station = WeatherStation.query.first()
    
    if station:
        print(f"Ajout de données de test pour la station : {station.name}")
        
        # Créer 10 enregistrements de turbulence pour les dernières heures
        for i in range(10):
            timestamp = datetime.utcnow() - timedelta(hours=i)
            
            # Données aléatoires réalistes
            turbulence_data = TurbulenceData(
                station_id=station.id,
                timestamp=timestamp,
                wind_speed=random.uniform(5, 30),  # 5-30 knots
                wind_direction=random.uniform(0, 360),  # 0-360 degrés
                wind_direction_variance=random.uniform(0, 20),  # 0-20 degrés
                pressure_gradient=random.uniform(-1, 1),  # Gradient de pression
                temperature_gradient=random.uniform(-2, 2),  # Gradient de température
            )
            
            # Calculer l'indice de turbulence
            from app.modules.aviation.turbulence import TurbulenceIndex
            turbulence_index = TurbulenceIndex.calculate_turbulence_risk(
                turbulence_data.wind_speed,
                turbulence_data.wind_direction_variance,
                turbulence_data.pressure_gradient,
                turbulence_data.temperature_gradient
            )
            
            severity = TurbulenceIndex.get_turbulence_severity(turbulence_index)
            
            turbulence_data.turbulence_index = turbulence_index
            turbulence_data.turbulence_level = severity['level']
            
            db.session.add(turbulence_data)
        
        db.session.commit()
        print("✅ Données de test ajoutées avec succès !")
    else:
        print("❌ Aucune station trouvée. Importez d'abord des données météo.")