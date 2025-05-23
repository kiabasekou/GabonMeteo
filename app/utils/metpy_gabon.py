# app/utils/metpy_gabon.py
"""
Module MetPy spécialisé pour le climat gabonais
Calculs météorologiques avancés adaptés au contexte tropical équatorial
"""

import metpy.calc as mpcalc
import metpy.units as units
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GabonClimateConstants:
    """Constantes climatologiques spécifiques au Gabon"""
    
    # Zones climatiques du Gabon
    CLIMATE_ZONES = {
        'COASTAL': {
            'regions': ['Estuaire', 'Ogooué-Maritime'],
            'temp_range': (24, 32),
            'humidity_range': (75, 95),
            'rainfall_annual': (1800, 3000)
        },
        'EQUATORIAL_CENTER': {
            'regions': ['Moyen-Ogooué', 'Ogooué-Ivindo'],
            'temp_range': (22, 30),
            'humidity_range': (80, 95),
            'rainfall_annual': (1500, 2500)
        },
        'NORTHERN': {
            'regions': ['Woleu-Ntem'],
            'temp_range': (20, 28),
            'humidity_range': (70, 90),
            'rainfall_annual': (1300, 2000)
        },
        'EASTERN_PLATEAU': {
            'regions': ['Haut-Ogooué', 'Ogooué-Lolo'],
            'temp_range': (18, 26),
            'humidity_range': (65, 85),
            'rainfall_annual': (1200, 1800)
        }
    }
    
    # Seuils de confort thermique adaptés au Gabon
    THERMAL_COMFORT = {
        'OPTIMAL': {'temp_range': (22, 26), 'humidity_max': 75},
        'COMFORTABLE': {'temp_range': (20, 28), 'humidity_max': 80},
        'ACCEPTABLE': {'temp_range': (18, 30), 'humidity_max': 85},
        'UNCOMFORTABLE': {'temp_range': (16, 35), 'humidity_max': 90}
    }
    
    # Saisons gabonaises
    SEASONS = {
        'DRY_SEASON': [6, 7, 8],  # Juin-Août
        'LONG_RAINY': [9, 10, 11, 12],  # Sept-Déc
        'SHORT_DRY': [1, 2],  # Jan-Fév
        'SHORT_RAINY': [3, 4, 5]  # Mar-Mai
    }

class GabonMetPyCore:
    """Cœur des calculs météorologiques MetPy pour le Gabon"""
    
    def __init__(self):
        self.constants = GabonClimateConstants()
        self.models = {}
        self.scaler = StandardScaler()
        self.models_trained = False
        
    # ========= CALCULS METPY FONDAMENTAUX =========
    
    def calculate_heat_index(self, temperature, humidity):
        """
        Calcule l'indice de chaleur avec MetPy
        Crucial pour le climat tropical gabonais
        """
        try:
            temp = temperature * units.celsius
            rh = humidity * units.percent
            heat_index = mpcalc.heat_index(temp, rh)
            return float(heat_index.to('celsius').magnitude)
        except Exception as e:
            logger.warning(f"Erreur calcul heat index: {e}")
            return temperature  # Fallback
    
    def calculate_dewpoint(self, temperature, humidity):
        """Calcule le point de rosée"""
        try:
            temp = temperature * units.celsius
            rh = humidity * units.percent
            dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, rh)
            return float(dewpoint.to('celsius').magnitude)
        except Exception as e:
            logger.warning(f"Erreur calcul dewpoint: {e}")
            return temperature - 5  # Approximation simple
    
    def calculate_wet_bulb_temperature(self, temperature, pressure, humidity):
        """Calcule la température du thermomètre mouillé"""
        try:
            temp = temperature * units.celsius
            press = pressure * units.hPa
            rh = humidity * units.percent
            
            dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, rh)
            wet_bulb = mpcalc.wet_bulb_temperature(press, temp, dewpoint)
            return float(wet_bulb.to('celsius').magnitude)
        except Exception as e:
            logger.warning(f"Erreur calcul wet bulb: {e}")
            return temperature - 2  # Approximation
    
    def calculate_equivalent_potential_temperature(self, temperature, pressure, humidity):
        """Calcule la température potentielle équivalente"""
        try:
            temp = temperature * units.celsius
            press = pressure * units.hPa
            rh = humidity * units.percent
            
            dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, rh)
            equiv_pot_temp = mpcalc.equivalent_potential_temperature(press, temp, dewpoint)
            return float(equiv_pot_temp.to('kelvin').magnitude)
        except Exception as e:
            logger.warning(f"Erreur calcul EPT: {e}")
            return temperature + 273.15
    
    # ========= ANALYSES SPÉCIALISÉES GABON =========
    
    def analyze_thermal_comfort(self, temperature, humidity, wind_speed=5, region='COASTAL'):
        """
        Analyse complète du confort thermique adapté au Gabon
        """
        # Calculs MetPy de base
        heat_index = self.calculate_heat_index(temperature, humidity)
        dewpoint = self.calculate_dewpoint(temperature, humidity)
        
        # Effet refroidissant du vent (formule adaptée climat tropical)
        wind_cooling = min(wind_speed * 0.15, 3.0) if wind_speed > 2 else 0
        effective_temperature = heat_index - wind_cooling
        
        # Classification basée sur constantes gabonaises
        comfort_level = self._classify_thermal_comfort(effective_temperature, humidity, region)
        
        # Indices de stress thermique
        stress_indices = self._calculate_thermal_stress_indices(
            temperature, humidity, heat_index, dewpoint
        )
        
        return {
            'heat_index': round(heat_index, 1),
            'dewpoint': round(dewpoint, 1),
            'effective_temperature': round(effective_temperature, 1),
            'wind_cooling_effect': round(wind_cooling, 1),
            'comfort_level': comfort_level['level'],
            'comfort_category': comfort_level['category'],
            'comfort_description': comfort_level['description'],
            'health_recommendations': comfort_level['recommendations'],
            'stress_indices': stress_indices,
            'climate_zone': region,
            'timestamp': datetime.now().isoformat()
        }
    
    def _classify_thermal_comfort(self, effective_temp, humidity, region):
        """Classification du confort thermique selon les standards gabonais"""
        
        # Ajustements selon la zone climatique
        zone_data = self.constants.CLIMATE_ZONES.get(region, self.constants.CLIMATE_ZONES['COASTAL'])
        temp_tolerance = 1.0 if region in ['COASTAL', 'EQUATORIAL_CENTER'] else 2.0
        
        # Classification progressive
        if effective_temp <= 24 + temp_tolerance:
            if humidity <= 75:
                return {
                    'level': 'TRÈS CONFORTABLE',
                    'category': 'success',
                    'description': 'Conditions idéales pour toutes activités',
                    'recommendations': ['Conditions parfaites', 'Activités extérieures recommandées']
                }
            else:
                return {
                    'level': 'CONFORTABLE',
                    'category': 'info',
                    'description': 'Conditions agréables malgré l\'humidité',
                    'recommendations': ['Hydratation normale', 'Activités extérieures possibles']
                }
        
        elif effective_temp <= 28 + temp_tolerance:
            return {
                'level': 'ACCEPTABLE',
                'category': 'info',
                'description': 'Légère sensation de chaleur',
                'recommendations': ['Hydratation régulière', 'Éviter efforts intenses midi']
            }
        
        elif effective_temp <= 32 + temp_tolerance:
            return {
                'level': 'CHAUD',
                'category': 'warning',
                'description': 'Inconfort thermique notable',
                'recommendations': [
                    'Hydratation fréquente',
                    'Rechercher l\'ombre',
                    'Limiter activités extérieures 11h-15h'
                ]
            }
        
        elif effective_temp <= 36 + temp_tolerance:
            return {
                'level': 'TRÈS CHAUD',
                'category': 'danger',
                'description': 'Stress thermique important',
                'recommendations': [
                    'Hydratation constante',
                    'Éviter exposition solaire',
                    'Surveiller signes malaise',
                    'Activités intérieures recommandées'
                ]
            }
        
        else:
            return {
                'level': 'EXTRÊME',
                'category': 'danger',
                'description': 'Conditions dangereuses',
                'recommendations': [
                    'URGENCE: Rester à l\'intérieur',
                    'Hydratation massive',
                    'Surveillance médicale si nécessaire',
                    'Éviter toute activité physique'
                ]
            }
    
    def _calculate_thermal_stress_indices(self, temperature, humidity, heat_index, dewpoint):
        """Calcule les indices de stress thermique"""
        
        # Indice d'humidex (utilisé au Canada, adapté au Gabon)
        humidex = temperature + 0.5555 * (6.11 * np.exp(5417.7530 * 
                   ((1/273.16) - (1/(273.16 + dewpoint)))) - 10)
        
        # Indice de Thom (discomfort index)
        thom_index = temperature - 0.55 * (1 - humidity/100) * (temperature - 14.5)
        
        # Température ressentie australienne (Australian Apparent Temperature)
        wind_speed = 5  # Valeur par défaut
        apparent_temp = temperature + 0.33 * (6.105 * np.exp(17.27 * dewpoint / (237.7 + dewpoint)) / 100) - 0.70 * wind_speed - 4.00
        
        return {
            'humidex': round(humidex, 1),
            'thom_discomfort_index': round(thom_index, 1),
            'apparent_temperature': round(apparent_temp, 1),
            'heat_stress_risk': self._assess_heat_stress_risk(heat_index)
        }
    
    def _assess_heat_stress_risk(self, heat_index):
        """Évalue le risque de stress thermique"""
        if heat_index < 27:
            return {'level': 'MINIMAL', 'description': 'Aucun risque particulier'}
        elif heat_index < 32:
            return {'level': 'FAIBLE', 'description': 'Fatigue possible efforts prolongés'}
        elif heat_index < 38:
            return {'level': 'MODÉRÉ', 'description': 'Crampes et épuisement possibles'}
        elif heat_index < 46:
            return {'level': 'ÉLEVÉ', 'description': 'Coup de chaleur probable'}
        else:
            return {'level': 'EXTRÊME', 'description': 'Coup de chaleur imminent'}
    
    # ========= PRÉVISIONS AVANCÉES =========
    
    def train_gabon_forecast_models(self, historical_weather_data):
        """
        Entraîne des modèles de prévision spécialisés pour le Gabon
        """
        try:
            logger.info("Début entraînement modèles prévision Gabon...")
            
            # Conversion en DataFrame
            df = pd.DataFrame(historical_weather_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Feature engineering spécialisé Gabon
            df = self._create_gabon_features(df)
            
            # Séparation des données
            features = ['day_of_year', 'month', 'hour', 'season_code', 
                       'pressure', 'humidity', 'wind_speed', 'heat_index_lag']
            
            # Préparation données température
            temp_data = df[features + ['temperature']].dropna()
            if len(temp_data) < 50:
                logger.warning("Données insuffisantes pour entraînement")
                return False
            
            X_temp = temp_data[features]
            y_temp = temp_data['temperature']
            
            # Entraînement modèle température (Gradient Boosting plus adapté au climat tropical)
            self.models['temperature'] = GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            X_temp_train, X_temp_test, y_temp_train, y_temp_test = train_test_split(
                X_temp, y_temp, test_size=0.2, random_state=42
            )
            
            self.models['temperature'].fit(X_temp_train, y_temp_train)
            temp_score = self.models['temperature'].score(X_temp_test, y_temp_test)
            
            # Préparation données précipitations
            rain_data = df[features + ['precipitation']].dropna()
            rain_data['has_rain'] = (rain_data['precipitation'] > 0.1).astype(int)
            
            X_rain = rain_data[features]
            y_rain = rain_data['precipitation']
            y_rain_class = rain_data['has_rain']
            
            # Modèle précipitations (Random Forest pour gérer la sparsité)
            self.models['precipitation'] = RandomForestRegressor(
                n_estimators=150,
                max_depth=8,
                min_samples_split=5,
                random_state=42
            )
            
            self.models['precipitation'].fit(X_rain, y_rain)
            rain_score = self.models['precipitation'].score(X_rain, y_rain)
            
            # Sauvegarde des modèles
            self._save_models()
            
            self.models_trained = True
            
            logger.info(f"Modèles entraînés - Temp: {temp_score:.3f}, Rain: {rain_score:.3f}")
            
            return {
                'success': True,
                'temperature_score': round(temp_score, 3),
                'precipitation_score': round(rain_score, 3),
                'training_samples': len(temp_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur entraînement modèles: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_gabon_features(self, df):
        """Crée des features spécialisées pour le climat gabonais"""
        
        # Features temporelles
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['month'] = df['timestamp'].dt.month
        df['hour'] = df['timestamp'].dt.hour
        
        # Codage des saisons gabonaises
        season_map = {}
        for season, months in self.constants.SEASONS.items():
            for month in months:
                season_map[month] = hash(season) % 4  # Code numérique
        
        df['season_code'] = df['month'].map(season_map)
        
        # Features météorologiques dérivées
        df['heat_index'] = df.apply(lambda row: self.calculate_heat_index(
            row['temperature'], row.get('humidity', 80)
        ), axis=1)
        
        # Lag features (valeurs précédentes)
        df['heat_index_lag'] = df['heat_index'].shift(1).fillna(df['heat_index'].mean())
        
        return df
    
    def predict_gabon_weather(self, current_conditions, days_ahead=7):
        """
        Prévisions météo spécialisées pour le Gabon
        """
        if not self.models_trained:
            # Charger les modèles sauvegardés ou utiliser prévisions simples
            if not self._load_models():
                return self._simple_gabon_predictions(current_conditions, days_ahead)
        
        try:
            predictions = []
            base_date = datetime.now()
            
            for day in range(1, days_ahead + 1):
                future_date = base_date + timedelta(days=day)
                
                # Préparation features pour prédiction
                features = self._prepare_prediction_features(future_date, current_conditions)
                
                # Prédictions
                temp_pred = self.models['temperature'].predict([features])[0]
                rain_pred = max(0, self.models['precipitation'].predict([features])[0])
                
                # Ajustements climatiques Gabon
                temp_pred, rain_pred = self._apply_gabon_climate_adjustments(
                    temp_pred, rain_pred, future_date
                )
                
                # Estimation humidité (basée sur patterns gabonais)
                humidity_pred = self._predict_humidity_gabon(temp_pred, rain_pred, future_date)
                
                # Analyse thermique de la prédiction
                thermal_analysis = self.analyze_thermal_comfort(
                    temp_pred, humidity_pred, 
                    current_conditions.get('wind_speed', 6)
                )
                
                predictions.append({
                    'date': future_date.date(),
                    'temperature': round(temp_pred, 1),
                    'precipitation': round(rain_pred, 1),
                    'humidity': round(humidity_pred, 1),
                    'thermal_comfort': thermal_analysis,
                    'confidence': self._calculate_prediction_confidence(day),
                    'climate_factors': self._get_climate_factors(future_date)
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return self._simple_gabon_predictions(current_conditions, days_ahead)
    
    def _prepare_prediction_features(self, future_date, current_conditions):
        """Prépare les features pour la prédiction"""
        
        # Mapping des saisons
        season_map = {}
        for season, months in self.constants.SEASONS.items():
            for month in months:
                season_map[month] = hash(season) % 4
        
        return [
            future_date.timetuple().tm_yday,  # day_of_year
            future_date.month,
            12,  # heure midi par défaut
            season_map.get(future_date.month, 0),  # season_code
            current_conditions.get('pressure', 1013),
            current_conditions.get('humidity', 80),
            current_conditions.get('wind_speed', 6),
            self.calculate_heat_index(
                current_conditions.get('temperature', 27),
                current_conditions.get('humidity', 80)
            )  # heat_index_lag
        ]
    
    def _apply_gabon_climate_adjustments(self, temp_pred, rain_pred, date):
        """Applique les ajustements climatiques spécifiques au Gabon"""
        month = date.month
        
        # Ajustements saisonniers température
        if month in self.constants.SEASONS['DRY_SEASON']:
            temp_pred += np.random.uniform(0.5, 1.5)  # Saison sèche plus chaude
        elif month in self.constants.SEASONS['LONG_RAINY']:
            temp_pred += np.random.uniform(-1.0, 0.5)  # Pluies refroidissent
        
        # Ajustements précipitations
        if month in self.constants.SEASONS['DRY_SEASON']:
            rain_pred *= 0.1  # Très peu de pluie en saison sèche
        elif month in self.constants.SEASONS['LONG_RAINY']:
            rain_pred *= 1.8  # Amplification période des pluies
        
        return temp_pred, rain_pred
    
    def _predict_humidity_gabon(self, temperature, precipitation, date):
        """Prédit l'humidité selon les patterns gabonais"""
        
        # Humidité de base élevée (climat équatorial)
        base_humidity = 75
        
        # Ajustements selon température
        temp_factor = max(0, (30 - temperature) * 2)  # Moins chaud = plus humide
        
        # Ajustements selon précipitations
        rain_factor = min(precipitation * 3, 15)  # Pluie augmente humidité
        
        # Ajustements saisonniers
        month = date.month
        if month in self.constants.SEASONS['DRY_SEASON']:
            seasonal_factor = -10  # Saison sèche moins humide
        else:
            seasonal_factor = 5   # Autres saisons plus humides
        
        humidity = base_humidity + temp_factor + rain_factor + seasonal_factor
        return max(60, min(95, humidity))  # Limites réalistes Gabon
    
    def _calculate_prediction_confidence(self, day):
        """Calcule la confiance de prédiction"""
        if day <= 2:
            return {'level': 'TRÈS ÉLEVÉE', 'percentage': 85}
        elif day <= 4:
            return {'level': 'ÉLEVÉE', 'percentage': 75}
        elif day <= 6:
            return {'level': 'MOYENNE', 'percentage': 65}
        else:
            return {'level': 'FAIBLE', 'percentage': 50}
    
    def _get_climate_factors(self, date):
        """Retourne les facteurs climatiques pour la date"""
        month = date.month
        
        for season_name, months in self.constants.SEASONS.items():
            if month in months:
                return {
                    'season': season_name.replace('_', ' ').title(),
                    'characteristics': self._get_season_characteristics(season_name)
                }
        
        return {'season': 'Transition', 'characteristics': ['Conditions variables']}
    
    def _get_season_characteristics(self, season):
        """Caractéristiques de chaque saison gabonaise"""
        characteristics = {
            'DRY_SEASON': ['Temps sec', 'Températures élevées', 'Peu de pluie'],
            'LONG_RAINY': ['Pluies fréquentes', 'Humidité très élevée', 'Températures modérées'],
            'SHORT_DRY': ['Petite saison sèche', 'Temps variable'],
            'SHORT_RAINY': ['Pluies intermittentes', 'Forte humidité']
        }
        return characteristics.get(season, ['Conditions standard'])
    
    def _simple_gabon_predictions(self, current_conditions, days_ahead):
        """Prédictions simples si ML non disponible"""
        predictions = []
        base_temp = current_conditions.get('temperature', 27)
        
        for day in range(1, days_ahead + 1):
            future_date = datetime.now() + timedelta(days=day)
            
            # Variation climatologique gabonaise
            temp_variation = np.random.normal(0, 1.5)
            pred_temp = base_temp + temp_variation
            
            # Probabilité pluie saisonnière
            month = future_date.month
            if month in self.constants.SEASONS['DRY_SEASON']:
                rain_prob = 0.15
            elif month in self.constants.SEASONS['LONG_RAINY']:
                rain_prob = 0.75
            else:
                rain_prob = 0.45
            
            pred_rain = np.random.exponential(8) if np.random.random() < rain_prob else 0
            pred_humidity = self._predict_humidity_gabon(pred_temp, pred_rain, future_date)
            
            thermal_analysis = self.analyze_thermal_comfort(pred_temp, pred_humidity)
            
            predictions.append({
                'date': future_date.date(),
                'temperature': round(pred_temp, 1),
                'precipitation': round(pred_rain, 1),
                'humidity': round(pred_humidity, 1),
                'thermal_comfort': thermal_analysis,
                'confidence': self._calculate_prediction_confidence(day),
                'climate_factors': self._get_climate_factors(future_date)
            })
        
        return predictions
    
    def _save_models(self):
        """Sauvegarde les modèles entraînés"""
        try:
            os.makedirs('app/ml_models', exist_ok=True)
            for model_name, model in self.models.items():
                joblib.dump(model, f'app/ml_models/{model_name}_gabon.pkl')
            logger.info("Modèles sauvegardés avec succès")
        except Exception as e:
            logger.error(f"Erreur sauvegarde modèles: {e}")
    
    def _load_models(self):
        """Charge les modèles sauvegardés"""
        try:
            model_files = ['temperature_gabon.pkl', 'precipitation_gabon.pkl']
            for model_file in model_files:
                model_path = f'app/ml_models/{model_file}'
                if os.path.exists(model_path):
                    model_name = model_file.replace('_gabon.pkl', '')
                    self.models[model_name] = joblib.load(model_path)
            
            if len(self.models) == 2:
                self.models_trained = True
                logger.info("Modèles chargés avec succès")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur chargement modèles: {e}")
            return False