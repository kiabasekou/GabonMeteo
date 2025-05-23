# app/models/maritime_data.py
from app.extensions import db
from datetime import datetime

class MaritimeData(db.Model):
    """Modèle pour les données maritimes"""
    __tablename__ = 'maritime_data'
    
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('weather_station.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Données des vagues
    wave_height = db.Column(db.Float)  # Hauteur en mètres
    wave_period = db.Column(db.Float)  # Période en secondes
    wave_direction = db.Column(db.Float)  # Direction en degrés
    
    # État de la mer (échelle Douglas 0-9)
    sea_state = db.Column(db.Integer)
    
    # Données de marée
    tide_height = db.Column(db.Float)  # Hauteur de marée en mètres
    tide_direction = db.Column(db.String(10))  # 'montante' ou 'descendante'
    next_high_tide = db.Column(db.DateTime)  # Prochaine marée haute
    next_low_tide = db.Column(db.DateTime)  # Prochaine marée basse
    
    # Conditions de navigation
    navigation_safety = db.Column(db.String(20))  # 'SAFE', 'CAUTION', 'DANGER'
    surface_current_speed = db.Column(db.Float)  # Vitesse du courant en nœuds
    surface_current_direction = db.Column(db.Float)  # Direction du courant
    
    # Relation avec la station - Utiliser une relation lazy
    station = db.relationship('WeatherStation', backref=db.backref('maritime_data_records', lazy='dynamic'))
    
    def __repr__(self):
        return f'<MaritimeData Station:{self.station_id} - Sea State {self.sea_state}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'station_id': self.station_id,
            'timestamp': self.timestamp.isoformat(),
            'wave_height': self.wave_height,
            'wave_period': self.wave_period,
            'wave_direction': self.wave_direction,
            'sea_state': self.sea_state,
            'tide_height': self.tide_height,
            'navigation_safety': self.navigation_safety,
            'surface_current': {
                'speed': self.surface_current_speed,
                'direction': self.surface_current_direction
            }
        }