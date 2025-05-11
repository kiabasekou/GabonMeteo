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
    """Prédit les températures futures en utilisant une régression polynomiale"""
    if not historical_data or len(historical_data) < 5:
        return []
    
    # Extraire les températures et les dates (converties en nombres)
    x = []  # Jours depuis aujourd'hui
    y_temp = []  # Températures
    y_humidity = []  # Humidité
    y_precip = []  # Précipitations
    
    base_date = datetime.now().date()
    
    for data in historical_data:
        days_diff = (data.timestamp.date() - base_date).days
        x.append(days_diff)
        y_temp.append(data.temperature)
        
        # Récupérer également l'humidité et la précipitation pour des prévisions plus complètes
        if hasattr(data, 'humidity') and data.humidity is not None:
            y_humidity.append(data.humidity)
        else:
            y_humidity.append(75)  # Valeur par défaut
            
        if hasattr(data, 'precipitation') and data.precipitation is not None:
            y_precip.append(data.precipitation)
        else:
            y_precip.append(0)  # Valeur par défaut
    
    # Utiliser numpy pour la régression polynomiale (degré 2)
    temp_coeffs = np.polyfit(x, y_temp, 2)
    temp_polynomial = np.poly1d(temp_coeffs)
    
    # Calculer des tendances simples pour l'humidité et les précipitations
    # (ne pas utiliser de régression polynomiale car ces données sont plus stochastiques)
    avg_humidity = sum(y_humidity) / len(y_humidity)
    
    # Calculer la probabilité de pluie à partir des données historiques
    rain_days = sum(1 for precip in y_precip if precip > 0)
    rain_probability = rain_days / len(y_precip) if y_precip else 0.2
    
    # Calculer l'intensité moyenne des précipitations les jours de pluie
    rain_intensity = sum(precip for precip in y_precip if precip > 0) / max(1, rain_days)
    
    # Prédire pour les jours futurs
    predictions = []
    for i in range(1, days_ahead + 1):
        # Prédire la température avec la régression polynomiale
        predicted_temp = temp_polynomial(i)
        
        # Ajouter un facteur saisonnier (simulation d'une tendance journalière)
        # Plus chaud en milieu de journée, plus frais le matin et le soir
        day_factor = 0.5 * np.sin(np.pi * (i % 1))
        predicted_temp += day_factor
        
        # Limiter la température à des valeurs réalistes pour le Gabon
        predicted_temp = max(18, min(38, predicted_temp))
        
        # Déterminer s'il va pleuvoir ce jour-là
        # La probabilité augmente légèrement pour les jours plus éloignés (incertitude)
        daily_rain_probability = rain_probability + (i * 0.02)
        daily_rain_probability = min(0.75, daily_rain_probability)  # Limiter à 75% max
        
        is_rainy_day = np.random.random() < daily_rain_probability
        
        # Déterminer la quantité de précipitations
        if is_rainy_day:
            # Varier autour de l'intensité moyenne avec une distribution normale
            precipitation = max(0, np.random.normal(rain_intensity, rain_intensity/2))
            
            # Les jours de pluie ont généralement une humidité plus élevée
            humidity = min(100, avg_humidity + np.random.uniform(5, 15))
        else:
            precipitation = 0
            # Les jours sans pluie ont généralement une humidité plus basse
            humidity = max(50, avg_humidity - np.random.uniform(5, 15))
        
        # Ajuster l'humidité en fonction de la température
        # Les jours plus chauds tendent à être moins humides
        temp_humidity_factor = (30 - predicted_temp) / 10
        humidity += temp_humidity_factor * 5
        humidity = max(50, min(95, humidity))
        
        # Calculer la vitesse du vent (simpliste)
        if precipitation > 5:
            # Vents plus forts pendant les fortes pluies
            wind_speed = np.random.uniform(10, 20)
        else:
            wind_speed = np.random.uniform(5, 12)
        
        # Déterminer la direction du vent (simpliste)
        wind_direction = np.random.uniform(0, 360)
        
        predictions.append({
            'date': base_date + timedelta(days=i),
            'temperature': round(predicted_temp, 1),
            'precipitation': round(precipitation, 1),
            'humidity': round(humidity, 1),
            'wind_speed': round(wind_speed, 1),
            'wind_direction': round(wind_direction, 0)
        })
    
    return predictions

def calculate_weather_alert_level(weather_data):
    """Calcule le niveau d'alerte météo en fonction des données"""
    if not weather_data:
        return None
    
    alert_level = 0
    alerts = []
    
    # Niveau d'alerte basé sur la précipitation
    if weather_data.precipitation > 20:
        alert_level += 3  # Alerte élevée
        alerts.append({"type": "Précipitation", "message": "Risque d'inondation", "level": "danger"})
    elif weather_data.precipitation > 10:
        alert_level += 2  # Alerte moyenne
        alerts.append({"type": "Précipitation", "message": "Fortes pluies", "level": "warning"})
    elif weather_data.precipitation > 5:
        alert_level += 1  # Alerte faible
        alerts.append({"type": "Précipitation", "message": "Pluie modérée", "level": "info"})
    
    # Niveau d'alerte basé sur la vitesse du vent
    if weather_data.wind_speed > 30:
        alert_level += 3  # Alerte élevée
        alerts.append({"type": "Vent", "message": "Vents violents", "level": "danger"})
    elif weather_data.wind_speed > 20:
        alert_level += 2  # Alerte moyenne
        alerts.append({"type": "Vent", "message": "Vents forts", "level": "warning"})
    elif weather_data.wind_speed > 15:
        alert_level += 1  # Alerte faible
        alerts.append({"type": "Vent", "message": "Vents modérés", "level": "info"})
    
    # Niveau d'alerte basé sur la température
    if weather_data.temperature > 35:
        alert_level += 2  # Alerte moyenne
        alerts.append({"type": "Température", "message": "Chaleur extrême", "level": "warning"})
    elif weather_data.temperature > 32:
        alert_level += 1  # Alerte faible
        alerts.append({"type": "Température", "message": "Fortes chaleurs", "level": "info"})
    
    # Classement du niveau d'alerte global
    if alert_level >= 5:
        return {"level": "danger", "alerts": alerts}  # Rouge
    elif alert_level >= 3:
        return {"level": "warning", "alerts": alerts}  # Orange
    elif alert_level >= 1:
        return {"level": "info", "alerts": alerts}  # Bleu
    else:
        return {"level": "success", "alerts": []}  # Vert