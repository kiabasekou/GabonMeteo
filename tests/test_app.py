import unittest
import os
import sys

# Ajout du répertoire parent au path pour pouvoir importer l'application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.weather_data import WeatherStation, WeatherData
from app.models.user import User

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Création d'une station de test
            station = WeatherStation(
                name='Station Test',
                latitude=0.4162,
                longitude=-9.4673,
                altitude=13,
                region='Test'
            )
            db.session.add(station)
            db.session.commit()
            
            # Création de données météo de test
            from datetime import datetime
            
            weather_data = WeatherData(
                station_id=station.id,
                timestamp=datetime.now(),
                temperature=28.5,
                humidity=85,
                pressure=1010.2,
                wind_speed=10.5,
                wind_direction=180,
                precipitation=0
            )
            db.session.add(weather_data)
            db.session.commit()
    
    def tearDown(self):
        with self.app.app_context():
            db.drop_all()
    
    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GabonM', response.data)
    
    def test_forecasts_page(self):
        response = self.client.get('/forecasts')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'visions', response.data)
    
    def test_historical_page(self):
        response = self.client.get('/historical')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'historiques', response.data)
    
    def test_agriculture_page(self):
        response = self.client.get('/agriculture')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'agricoles', response.data)
    
    def test_alerts_page(self):
        response = self.client.get('/alerts')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alertes', response.data)

if __name__ == '__main__':
    unittest.main()