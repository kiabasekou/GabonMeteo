# app/models/__init__.py
# Importer tous les modèles pour s'assurer qu'ils sont chargés dans le bon ordre
from app.models.user import User
from app.models.weather_data import WeatherStation, WeatherData
from app.models.agent import Direction, Service, AgentDGM, Prelevement
from app.models.aviation_data import TurbulenceData
from app.models.maritime_data import MaritimeData

__all__ = [
    'User',
    'WeatherStation',
    'WeatherData',
    'Direction',
    'Service',
    'AgentDGM',
    'Prelevement',
    'TurbulenceData',
    'MaritimeData'
]