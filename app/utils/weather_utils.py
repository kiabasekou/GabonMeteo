import numpy as np
from datetime import datetime, timedelta

def calculate_average_temperature(data_list):
    """Calcule la température moyenne à partir d'une liste de données météo"""
    if not data_list:
        return None
    
    temperatures = [data.temperature for data in data_list if data.temperature is not None]
    
    if not temperatures:
        return None
    
    return sum(temperatures) / len(temperatures)

def predict_temperature(historical_data, days_ahead=3):
    """Prédit les températures futures en utilisant une régression linéaire simple"""
    if not historical_data or len(historical_data) < 3:
        return []
    
    # Extraire les températures et les dates (converties en nombres)
    x = []  # Jours depuis aujourd'hui
    y = []  # Températures
    
    base_date = datetime.now().date()
    
    for data in historical_data:
        days_diff = (data.timestamp.date() - base_date).days
        x.append(days_diff)
        y.append(data.temperature)
    
    # Utiliser numpy pour la régression linéaire
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    
    # Prédire pour les jours futurs
    predictions = []
    for i in range(1, days_ahead + 1):
        predicted_temp = slope * i + intercept
        predictions.append({
            'date': base_date + timedelta(days=i),
            'temperature': round(predicted_temp, 1)
        })
    
    return predictions

def calculate_weather_alert_level(weather_data):
    """Calcule le niveau d'alerte météo en fonction des données"""
    if not weather_data:
        return None
    
    alert_level = 0
    
    # Niveau d'alerte basé sur la précipitation
    if weather_data.precipitation > 20:
        alert_level += 3  # Alerte élevée
    elif weather_data.precipitation > 10:
        alert_level += 2  # Alerte moyenne
    elif weather_data.precipitation > 5:
        alert_level += 1  # Alerte faible
    
    # Niveau d'alerte basé sur la vitesse du vent
    if weather_data.wind_speed > 30:
        alert_level += 3  # Alerte élevée
    elif weather_data.wind_speed > 20:
        alert_level += 2  # Alerte moyenne
    elif weather_data.wind_speed > 15:
        alert_level += 1  # Alerte faible
    
    # Niveau d'alerte basé sur la température
    if weather_data.temperature > 35:
        alert_level += 2  # Alerte moyenne
    elif weather_data.temperature > 32:
        alert_level += 1  # Alerte faible
    
    # Classement du niveau d'alerte
    if alert_level >= 5:
        return 'danger'  # Rouge
    elif alert_level >= 3:
        return 'warning'  # Orange
    elif alert_level >= 1:
        return 'info'  # Bleu
    else:
        return 'success'  # Vert