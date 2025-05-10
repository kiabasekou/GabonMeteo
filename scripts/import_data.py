import os
import sys
import csv
from datetime import datetime

# Ajout du répertoire parent au path pour pouvoir importer l'application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.weather_data import WeatherStation, WeatherData

def import_weather_data(csv_file):
    app = create_app()
    
    with app.app_context():
        # Lecture du fichier CSV
        with open(csv_file, 'r') as file:
            csv_reader = csv.DictReader(file)
            
            # Dictionnaire pour stocker les stations par nom
            stations = {}
            
            for row in csv_reader:
                # Vérifier si la station existe déjà dans notre dictionnaire
                station_name = row['station_name']
                
                if station_name not in stations:
                    # Vérifier si la station existe dans la base de données
                    station = WeatherStation.query.filter_by(name=station_name).first()
                    
                    if not station:
                        # Créer une nouvelle station
                        station = WeatherStation(
                            name=station_name,
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude']),
                            altitude=float(row['altitude']),
                            region=row['region']
                        )
                        db.session.add(station)
                        db.session.commit()
                    
                    stations[station_name] = station
                
                # Créer un nouvel enregistrement de données météo
                date = datetime.strptime(row['date'], '%Y-%m-%d')
                
                weather_data = WeatherData(
                    station_id=stations[station_name].id,
                    timestamp=date,
                    temperature=float(row['temperature']),
                    humidity=float(row['humidity']),
                    pressure=float(row['pressure']),
                    wind_speed=float(row['wind_speed']),
                    wind_direction=float(row['wind_direction']),
                    precipitation=float(row['precipitation'])
                )
                
                db.session.add(weather_data)
            
            # Enregistrer toutes les modifications
            db.session.commit()
            
            print(f"Importation terminée. {len(stations)} stations et {csv_reader.line_num - 1} enregistrements importés.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_data.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    import_weather_data(csv_file)