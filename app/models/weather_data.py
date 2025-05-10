from app import db
from datetime import datetime

class WeatherStation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float)
    region = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    
    weather_data = db.relationship('WeatherData', backref='station', lazy='dynamic')
    
    def __repr__(self):
        return f'<Station {self.name}>'

class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('weather_station.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pressure = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    precipitation = db.Column(db.Float)
    
    def __repr__(self):
        return f'<WeatherData {self.station.name} at {self.timestamp}>'