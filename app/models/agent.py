from app import db
from flask_login import UserMixin
from app.models.user import User
from app.models.weather_data import WeatherStation
from datetime import datetime

class Direction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    
    # Relations
    services = db.relationship('Service', backref='direction', lazy='dynamic')
    
    def __repr__(self):
        return f'<Direction {self.name}>'

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id'), nullable=False)
    
    # Relations
    agents = db.relationship('AgentDGM', backref='service', lazy='dynamic')
    
    def __repr__(self):
        return f'<Service {self.name} - Direction {self.direction.name}>'

class AgentDGM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    fonction = db.Column(db.String(100), nullable=False)
    date_embauche = db.Column(db.Date)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('weather_station.id'))
    
    # Relations
    user = db.relationship('User', backref=db.backref('agent', uselist=False))
    station = db.relationship('WeatherStation', backref='agents')
    prelevements = db.relationship('Prelevement', backref='agent', lazy='dynamic')
    
    @property
    def fullname(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    def __repr__(self):
        return f'<Agent {self.matricule} - {self.user.username}>'

class Prelevement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent_dgm.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('weather_station.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_prelevement = db.Column(db.DateTime, nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pressure = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    precipitation = db.Column(db.Float)
    notes = db.Column(db.Text)
    validated = db.Column(db.Boolean, default=False)
    
    # Relation avec la station météo
    station = db.relationship('WeatherStation', backref='prelevements')
    
    def to_weather_data(self):
        """Convertit un prélèvement en données météo après validation"""
        from app.models.weather_data import WeatherData
        
        weather_data = WeatherData(
            station_id=self.station_id,
            timestamp=self.date_prelevement,
            temperature=self.temperature,
            humidity=self.humidity,
            pressure=self.pressure,
            wind_speed=self.wind_speed,
            wind_direction=self.wind_direction,
            precipitation=self.precipitation
        )
        
        return weather_data
    
    def __repr__(self):
        return f'<Prelevement #{self.id} par {self.agent.matricule} à {self.station.name}>'