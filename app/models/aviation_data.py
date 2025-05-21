# app/models/aviation_data.py
from app.extensions import db  # ✅ Maintenant ça devrait marcher !
from datetime import datetime

class TurbulenceData(db.Model):
    __tablename__ = 'turbulence_data'
    
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('weather_station.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Données de turbulence
    wind_speed = db.Column(db.Float, nullable=False)
    wind_direction = db.Column(db.Float, nullable=False)
    wind_direction_variance = db.Column(db.Float)
    pressure_gradient = db.Column(db.Float)
    temperature_gradient = db.Column(db.Float)
    
    # Résultats calculés
    turbulence_index = db.Column(db.Float)
    turbulence_level = db.Column(db.String(50))
    wind_shear = db.Column(db.Float)
    
    def __repr__(self):
        return f'<TurbulenceData {self.station_id} at {self.timestamp}>'