import metpy.calc as mpcalc
import metpy.units as units
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pandas as pd

class GabonMeteoCore:
    """Cœur météorologique avancé pour le Gabon"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.temp_model = None
        self.rain_model = None
        
    # ===== CALCULS METPY ESSENTIELS =====
    
    def calculate_heat_index(self, temp_c, humidity_pct):
        """Indice de chaleur - CRUCIAL pour le Gabon tropical"""
        temp = temp_c * units.celsius
        rh = humidity_pct * units.percent
        heat_idx = mpcalc.heat_index(temp, rh)
        return float(heat_idx.to('celsius').magnitude)
    
    def calculate_dewpoint(self, temp_c, humidity_pct):
        """Point de rosée - indicateur de confort"""
        temp = temp_c * units.celsius
        rh = humidity_pct * units.percent
        dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, rh)
        return float(dewpoint.to('celsius').magnitude)
    
    def calculate_wet_bulb(self, temp_c, pressure_hpa, humidity_pct):
        """Température humide - stress thermique"""
        temp = temp_c * units.celsius
        press = pressure_hpa * units.hPa
        rh = humidity_pct * units.percent
        
        dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, rh)
        wet_bulb = mpcalc.wet_bulb_temperature(press, temp, dewpoint)
        return float(wet_bulb.to('celsius').magnitude)
    
    def analyze_thermal_stress(self, temp_c, humidity_pct, wind_kmh=5):
        """Analyse complète du stress thermique"""
        heat_index = self.calculate_heat_index(temp_c, humidity_pct)
        dewpoint = self.calculate_dewpoint(temp_c, humidity_pct)
        
        # Facteur refroidissement du vent
        wind_cooling = min(wind_kmh * 0.1, 2.0)
        effective_temp = heat_index - wind_cooling
        
        # Classification du stress thermique
        if effective_temp < 26:
            level = "CONFORTABLE"
            risk = "success"
            advice = "Conditions idéales pour toutes activités"
        elif effective_temp < 30:
            level = "ACCEPTABLE"
            risk = "info"
            advice = "Conditions normales, hydratation régulière"
        elif effective_temp < 35:
            level = "ATTENTION"
            risk = "warning" 
            advice = "Éviter efforts prolongés, boire fréquemment"
        elif effective_temp < 40:
            level = "DANGER"
            risk = "danger"
            advice = "Limiter exposition, risque de coup de chaleur"
        else:
            level = "EXTRÊME"
            risk = "danger"
            advice = "Éviter toute activité extérieure"
        
        return {
            'heat_index': round(heat_index, 1),
            'dewpoint': round(dewpoint, 1),
            'effective_temperature': round(effective_temp, 1),
            'thermal_stress_level': level,
            'risk_category': risk,
            'health_advice': advice,
            'wind_cooling_effect': round(wind_cooling, 1)
        }
    
    # ===== PRÉVISIONS INTELLIGENTES =====
    
    def train_prediction_models(self, historical_data):
        """Entraîne les modèles de prévision sur données historiques"""
        
        # Préparation des données
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['timestamp'])
        df['day_of_year'] = df['date'].dt.dayofyear
        df['month'] = df['date'].dt.month
        df['hour'] = df['date'].dt.hour
        
        # Features pour prédiction
        features = ['day_of_year', 'month', 'hour', 'pressure', 'humidity', 'wind_speed']
        
        # Modèle température
        temp_features = df[features].dropna()
        temp_targets = df.loc[temp_features.index, 'temperature']
        
        self.temp_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.temp_model.fit(temp_features, temp_targets)
        
        # Modèle précipitations
        rain_features = df[features].dropna()
        rain_targets = df.loc[rain_features.index, 'precipitation'].fillna(0)
        
        self.rain_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.rain_model.fit(rain_features, rain_targets)
        
        return {
            'temp_score': self.temp_model.score(temp_features, temp_targets),
            'rain_score': self.rain_model.score(rain_features, rain_targets)
        }
    
    def predict_advanced_weather(self, current_conditions, days_ahead=7):
        """Prévisions météo avancées avec MetPy + ML"""
        
        if not self.temp_model or not self.rain_model:
            # Fallback sur prédictions simples si modèles pas entraînés
            return self._simple_predictions(current_conditions, days_ahead)
        
        predictions = []
        base_date = datetime.now()
        
        for day in range(1, days_ahead + 1):
            future_date = base_date + timedelta(days=day)
            
            # Features pour prédiction
            features = [[
                future_date.timetuple().tm_yday,  # day_of_year
                future_date.month,
                12,  # heure midi par défaut
                current_conditions.get('pressure', 1013),
                current_conditions.get('humidity', 80),
                current_conditions.get('wind_speed', 8)
            ]]
            
            # Prédictions ML
            temp_pred = self.temp_model.predict(features)[0]
            rain_pred = max(0, self.rain_model.predict(features)[0])
            
            # Ajustements saisonniers pour le Gabon
            temp_pred = self._adjust_seasonal_temp(temp_pred, future_date)
            rain_pred = self._adjust_seasonal_rain(rain_pred, future_date)
            
            # Calculs MetPy pour la prédiction
            pred_humidity = current_conditions.get('humidity', 80) + np.random.normal(0, 5)
            pred_humidity = max(60, min(95, pred_humidity))
            
            thermal_analysis = self.analyze_thermal_stress(
                temp_pred, pred_humidity, current_conditions.get('wind_speed', 8)
            )
            
            predictions.append({
                'date': future_date.date(),
                'temperature': round(temp_pred, 1),
                'precipitation': round(rain_pred, 1),
                'humidity': round(pred_humidity, 1),
                'thermal_analysis': thermal_analysis,
                'confidence': self._calculate_confidence(day)
            })
        
        return predictions
    
    def _adjust_seasonal_temp(self, base_temp, date):
        """Ajustements saisonniers température pour Gabon"""
        month = date.month
        
        # Saison sèche (juin-août) : +1-2°C
        if 6 <= month <= 8:
            return base_temp + np.random.uniform(1, 2)
        # Saison des pluies (oct-avril) : température plus stable  
        elif month in [10, 11, 12, 1, 2, 3, 4]:
            return base_temp + np.random.uniform(-0.5, 0.5)
        # Transition
        else:
            return base_temp + np.random.uniform(0, 1)
    
    def _adjust_seasonal_rain(self, base_rain, date):
        """Ajustements saisonniers précipitations pour Gabon"""
        month = date.month
        
        # Saison sèche (juin-août) : très peu de pluie
        if 6 <= month <= 8:
            return base_rain * 0.2
        # Pic de pluies (oct-nov, mars-avril)
        elif month in [10, 11, 3, 4]:
            return base_rain * 1.5
        # Saison des pluies normale
        else:
            return base_rain
    
    def _calculate_confidence(self, day):
        """Calcule la confiance de la prévision"""
        # Confiance décroissante avec le temps
        if day <= 3:
            return "ÉLEVÉE"
        elif day <= 5:
            return "MOYENNE"
        else:
            return "FAIBLE"
    
    def _simple_predictions(self, current_conditions, days_ahead):
        """Prédictions simples si ML pas disponible"""
        predictions = []
        base_temp = current_conditions.get('temperature', 27)
        base_humidity = current_conditions.get('humidity', 80)
        
        for day in range(1, days_ahead + 1):
            # Variation aléatoire simple
            temp_variation = np.random.normal(0, 2)
            pred_temp = base_temp + temp_variation
            
            # Probabilité de pluie saisonnière
            future_date = datetime.now() + timedelta(days=day)
            rain_prob = 0.3 if future_date.month in [6, 7, 8] else 0.6
            pred_rain = np.random.exponential(5) if np.random.random() < rain_prob else 0
            
            thermal_analysis = self.analyze_thermal_stress(pred_temp, base_humidity)
            
            predictions.append({
                'date': future_date.date(),
                'temperature': round(pred_temp, 1),
                'precipitation': round(pred_rain, 1),
                'humidity': base_humidity,
                'thermal_analysis': thermal_analysis,
                'confidence': self._calculate_confidence(day)
            })
        
        return predictions