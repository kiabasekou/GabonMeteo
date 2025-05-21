# scripts/create_maritime_stations.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.weather_data import WeatherStation
from app.models.maritime_data import MaritimeData
import random
from datetime import datetime

app = create_app()

with app.app_context():
    # Ajouter des stations côtières si elles n'existent pas
    maritime_stations = [
        {
            'name': 'Port-Gentil',
            'latitude': -0.7193,
            'longitude': 8.7815,
            'altitude': 4,
            'region': 'Ogooué-Maritime'
        },
        {
            'name': 'Libreville',
            'latitude': 0.4162,
            'longitude': 9.4673,
            'altitude': 13,
            'region': 'Estuaire'
        },
        {
            'name': 'Cap Lopez',
            'latitude': -0.6372,
            'longitude': 8.7069,
            'altitude': 10,
            'region': 'Ogooué-Maritime'
        }
    ]
    
    print("🌊 Création des stations maritimes...")
    
    for station_data in maritime_stations:
        # Vérifier si la station existe déjà
        existing = WeatherStation.query.filter_by(name=station_data['name']).first()
        
        if not existing:
            # Créer la station
            station = WeatherStation(**station_data)
            db.session.add(station)
            db.session.commit()
            print(f"✅ Station créée: {station_data['name']}")
        else:
            print(f"📍 Station existante: {station_data['name']}")
    
    print("🎉 Stations maritimes prêtes !")