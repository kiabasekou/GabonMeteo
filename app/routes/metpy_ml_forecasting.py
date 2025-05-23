# app/routes/metpy_ml_forecasting.py
from flask import Blueprint, jsonify, request
from flask_login import login_required
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import metpy.calc as mpcalc
from metpy.units import units
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
from app.models.weather_data import WeatherStation, WeatherData
from app.extensions import db

metpy_ml_bp = Blueprint('metpy_ml', __name__, url_prefix='/api/metpy/ml')

class WeatherMLPredictor:
    """Classe pour prédictions météo avec ML et MetPy"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        
    def prepare_features(self, weather_data):
        """Prépare les features avec calculs MetPy"""
        features = []
        
        for i, data in enumerate(weather_data):
            if not (data.temperature and data.humidity and data.pressure):
                continue
                
            temp = data.temperature * units.celsius
            humidity = data.humidity * units.percent
            pressure = data.pressure * units.hPa
            
            # Features de base
            feature_row = {
                'temperature': temp.magnitude,
                'humidity': humidity.magnitude,
                'pressure': pressure.magnitude,
                'wind_speed': data.wind_speed or 0,
                'wind_direction': data.wind_direction or 0,
                'precipitation': data.precipitation or 0
            }
            
            # Features MetPy calculées
            try:
                # Point de rosée
                dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, humidity)
                feature_row['dewpoint'] = dewpoint.to('celsius').magnitude
                
                # Température potentielle
                potential_temp = mpcalc.potential_temperature(pressure, temp)
                feature_row['potential_temperature'] = potential_temp.to('kelvin').magnitude
                
                # Température équivalente potentielle
                equiv_potential_temp = mpcalc.equivalent_potential_temperature(pressure, temp, dewpoint)
                feature_row['equiv_potential_temp'] = equiv_potential_temp.to('kelvin').magnitude
                
                # Rapport de mélange
                mixing_ratio = mpcalc.mixing_ratio_from_relative_humidity(pressure, temp, humidity)
                feature_row['mixing_ratio'] = mixing_ratio.magnitude
                
                # Température virtuelle
                virtual_temp = mpcalc.virtual_temperature(temp, mixing_ratio)
                feature_row['virtual_temperature'] = virtual_temp.to('celsius').magnitude
                
                # Indice de chaleur (si applicable)
                if temp.magnitude > 20:
                    heat_index = mpcalc.heat_index(temp, humidity)
                    feature_row['heat_index'] = heat_index.to('celsius').magnitude
                else:
                    feature_row['heat_index'] = temp.magnitude
                    
            except Exception as e:
                # Valeurs par défaut si calculs échouent
                feature_row.update({
                    'dewpoint': temp.magnitude - 10,
                    'potential_temperature': temp.magnitude + 273.15,
                    'equiv_potential_temp': temp.magnitude + 280,
                    'mixing_ratio': 0.01,
                    'virtual_temperature': temp.magnitude,
                    'heat_index': temp.magnitude
                })
            
            # Features temporelles
            feature_row['hour'] = data.timestamp.hour
            feature_row['day_of_year'] = data.timestamp.timetuple().tm_yday
            feature_row['month'] = data.timestamp.month
            
            # Features de tendance (si suffisamment de données)
            if i >= 3:
                recent_temps = [weather_data[j].temperature for j in range(i-3, i) if weather_data[j].temperature]
                recent_pressures = [weather_data[j].pressure for j in range(i-3, i) if weather_data[j].pressure]
                
                if len(recent_temps) >= 2:
                    feature_row['temp_trend'] = np.mean(np.diff(recent_temps))
                else:
                    feature_row['temp_trend'] = 0
                    
                if len(recent_pressures) >= 2:
                    feature_row['pressure_trend'] = np.mean(np.diff(recent_pressures))
                else:
                    feature_row['pressure_trend'] = 0
            else:
                feature_row['temp_trend'] = 0
                feature_row['pressure_trend'] = 0
            
            features.append(feature_row)
        
        return pd.DataFrame(features)
    
    def train_models(self, station_id, days_back=90):
        """Entraîne les modèles de prédiction"""
        try:
            # Récupérer données d'entraînement
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)
            
            training_data = WeatherData.query.filter(
                WeatherData.station_id == station_id,
                WeatherData.timestamp >= start_time,
                WeatherData.temperature.isnot(None),
                WeatherData.humidity.isnot(None),
                WeatherData.pressure.isnot(None)
            ).order_by(WeatherData.timestamp).all()
            
            if len(training_data) < 100:
                return False, "Données insuffisantes pour l'entraînement"
            
            # Préparer features
            features_df = self.prepare_features(training_data)
            
            if features_df.empty:
                return False, "Impossible de calculer les features"
            
            # Targets (variables à prédire)
            targets = {
                'temperature_6h': [],
                'temperature_12h': [],
                'temperature_24h': [],
                'precipitation_6h': [],
                'precipitation_12h': [],
                'pressure_6h': []
            }
            
            # Créer les targets décalés dans le temps
            for i in range(len(training_data)):
                # Trouver les données futures
                current_time = training_data[i].timestamp
                
                # 6h, 12h, 24h dans le futur
                future_6h = current_time + timedelta(hours=6)
                future_12h = current_time + timedelta(hours=12)
                future_24h = current_time + timedelta(hours=24)
                
                # Chercher les données correspondantes
                for target_time, suffix in [(future_6h, '6h'), (future_12h, '12h'), (future_24h, '24h')]:
                    future_data = next((d for d in training_data[i+1:] 
                                      if abs((d.timestamp - target_time).total_seconds()) < 3600), None)
                    
                    if future_data:
                        if suffix in ['6h', '12h', '24h'] and 'temperature' in targets[f'temperature_{suffix}'] or len(targets[f'temperature_{suffix}']) <= i:
                            if len(targets[f'temperature_{suffix}']) <= i:
                                targets[f'temperature_{suffix}'].extend([None] * (i + 1 - len(targets[f'temperature_{suffix}'])))
                            targets[f'temperature_{suffix}'][i] = future_data.temperature
                        
                        if suffix in ['6h', '12h'] and f'precipitation_{suffix}' in targets:
                            if len(targets[f'precipitation_{suffix}']) <= i:
                                targets[f'precipitation_{suffix}'].extend([None] * (i + 1 - len(targets[f'precipitation_{suffix}'])))
                            targets[f'precipitation_{suffix}'][i] = future_data.precipitation or 0
                        
                        if suffix == '6h':
                            if len(targets['pressure_6h']) <= i:
                                targets['pressure_6h'].extend([None] * (i + 1 - len(targets['pressure_6h'])))
                            targets['pressure_6h'][i] = future_data.pressure
                    else:
                        # Remplir avec None si pas de données futures
                        for key in targets:
                            if suffix in key:
                                if len(targets[key]) <= i:
                                    targets[key].extend([None] * (i + 1 - len(targets[key])))
                                if len(targets[key]) <= i:
                                    targets[key].append(None)
            
            # Nettoyer les données (enlever les None)
            valid_indices = []
            for i in range(min(len(features_df), min(len(v) for v in targets.values()))):
                if all(targets[key][i] is not None for key in targets if i < len(targets[key])):
                    valid_indices.append(i)
            
            if len(valid_indices) < 50:
                return False, "Pas assez de données valides"
            
            X = features_df.iloc[valid_indices]
            
            # Entraîner un modèle pour chaque target
            for target_name in targets:
                if not targets[target_name]:
                    continue
                    
                y = [targets[target_name][i] for i in valid_indices if i < len(targets[target_name])]
                
                if len(y) != len(X):
                    continue
                
                # Diviser données
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                # Normalisation
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Modèle Random Forest
                model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                model.fit(X_train_scaled, y_train)
                
                # Évaluation
                y_pred = model.predict(X_test_scaled)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Sauvegarder modèle et scaler
                self.models[target_name] = {
                    'model': model,
                    'mae': mae,
                    'r2': r2,
                    'feature_names': list(X.columns)
                }
                self.scalers[target_name] = scaler
            
            self.is_trained = True
            return True, f"Modèles entraînés avec succès sur {len(valid_indices)} échantillons"
            
        except Exception as e:
            return False, f"Erreur entraînement: {str(e)}"
    
    def predict(self, current_data, station_id):
        """Fait des prédictions"""
        if not self.is_trained:
            success, message = self.train_models(station_id)
            if not success:
                return None, message
        
        try:
            # Préparer features pour données actuelles
            features_df = self.prepare_features([current_data])
            
            if features_df.empty:
                return None, "Impossible de calculer les features"
            
            predictions = {}
            
            for target_name, model_info in self.models.items():
                try:
                    model = model_info['model']
                    scaler = self.scalers[target_name]
                    
                    # S'assurer que toutes les features sont présentes
                    missing_features = set(model_info['feature_names']) - set(features_df.columns)
                    for feature in missing_features:
                        features_df[feature] = 0
                    
                    # Réorganiser colonnes selon l'ordre d'entraînement
                    features_ordered = features_df[model_info['feature_names']]
                    
                    # Normaliser et prédire
                    X_scaled = scaler.transform(features_ordered)
                    prediction = model.predict(X_scaled)[0]
                    
                    predictions[target_name] = {
                        'value': float(prediction),
                        'mae': model_info['mae'],
                        'r2': model_info['r2']
                    }
                    
                except Exception as e:
                    predictions[target_name] = {
                        'value': None,
                        'error': str(e)
                    }
            
            return predictions, "Prédictions générées"
            
        except Exception as e:
            return None, f"Erreur prédiction: {str(e)}"

# Instance globale du prédicteur
weather_predictor = WeatherMLPredictor()

@metpy_ml_bp.route('/forecast/<int:station_id>')
@login_required
def ml_forecast(station_id):
    """Prévisions météo avec Machine Learning et MetPy"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données actuelles
        current_data = WeatherData.query.filter_by(station_id=station_id)\
                                       .order_by(WeatherData.timestamp.desc())\
                                       .first()
        
        if not current_data:
            return jsonify({'error': 'Aucune donnée actuelle disponible'}), 404
        
        # Faire prédictions
        predictions, message = weather_predictor.predict(current_data, station_id)
        
        if predictions is None:
            return jsonify({'error': message}), 500
        
        # Organiser les résultats par horizon temporel
        forecast_data = {
            '6h': {
                'temperature': predictions.get('temperature_6h', {}).get('value'),
                'precipitation': predictions.get('precipitation_6h', {}).get('value'),
                'pressure': predictions.get('pressure_6h', {}).get('value'),
                'timestamp': (current_data.timestamp + timedelta(hours=6)).isoformat()
            },
            '12h': {
                'temperature': predictions.get('temperature_12h', {}).get('value'),
                'precipitation': predictions.get('precipitation_12h', {}).get('value'),
                'timestamp': (current_data.timestamp + timedelta(hours=12)).isoformat()
            },
            '24h': {
                'temperature': predictions.get('temperature_24h', {}).get('value'),
                'timestamp': (current_data.timestamp + timedelta(hours=24)).isoformat()
            }
        }
        
        # Ajouter indices de confiance
        confidence_scores = {}
        for target_name, pred_info in predictions.items():
            if 'r2' in pred_info:
                confidence_scores[target_name] = {
                    'r2_score': pred_info['r2'],
                    'mean_absolute_error': pred_info['mae']
                }
        
        # Calculs MetPy pour conditions actuelles
        temp = current_data.temperature * units.celsius
        humidity = current_data.humidity * units.percent
        pressure = current_data.pressure * units.hPa
        
        current_metpy = {}
        try:
            dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, humidity)
            heat_index = mpcalc.heat_index(temp, humidity)
            
            current_metpy = {
                'dewpoint': float(dewpoint.to('celsius').magnitude),
                'heat_index': float(heat_index.to('celsius').magnitude),
                'apparent_temperature': float(heat_index.to('celsius').magnitude)
            }
        except:
            current_metpy = {
                'dewpoint': current_data.temperature - 10,
                'heat_index': current_data.temperature,
                'apparent_temperature': current_data.temperature
            }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'current_conditions': {
                'timestamp': current_data.timestamp.isoformat(),
                'temperature': current_data.temperature,
                'humidity': current_data.humidity,
                'pressure': current_data.pressure,
                'wind_speed': current_data.wind_speed,
                'precipitation': current_data.precipitation,
                **current_metpy
            },
            'ml_forecast': forecast_data,
            'model_confidence': confidence_scores,
            'forecast_method': 'Machine Learning + MetPy',
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur prévision ML: {str(e)}'}), 500

@metpy_ml_bp.route('/train-models/<int:station_id>', methods=['POST'])
@login_required
def train_station_models(station_id):
    """Réentraîne les modèles pour une station"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        days_back = request.json.get('days_back', 90) if request.is_json else 90
        
        success, message = weather_predictor.train_models(station_id, days_back)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'station_id': station_id,
                'trained_models': list(weather_predictor.models.keys()),
                'training_completed_at': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({'error': f'Erreur entraînement: {str(e)}'}), 500

@metpy_ml_bp.route('/model-performance/<int:station_id>')
@login_required
def model_performance(station_id):
    """Retourne les performances des modèles"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        if not weather_predictor.is_trained:
            return jsonify({'error': 'Modèles non entraînés'}), 400
        
        performance_data = {}
        
        for target_name, model_info in weather_predictor.models.items():
            performance_data[target_name] = {
                'mean_absolute_error': model_info['mae'],
                'r2_score': model_info['r2'],
                'feature_count': len(model_info['feature_names']),
                'model_type': 'Random Forest'
            }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'model_performance': performance_data,
            'training_status': 'trained' if weather_predictor.is_trained else 'not_trained',
            'evaluation_timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur évaluation modèles: {str(e)}'}), 500

@metpy_ml_bp.route('/ensemble-forecast/<int:station_id>')
@login_required
def ensemble_forecast(station_id):
    """Prévision d'ensemble combinant ML et méthodes traditionnelles"""
    try:
        station = WeatherStation.query.get_or_404(station_id)
        
        # Récupérer données récentes
        recent_data = WeatherData.query.filter_by(station_id=station_id)\
                                     .order_by(WeatherData.timestamp.desc())\
                                     .limit(48).all()  # 48h de données
        
        if len(recent_data) < 24:
            return jsonify({'error': 'Données insuffisantes'}), 400
        
        current_data = recent_data[0]
        
        # 1. Prévision ML
        ml_predictions, ml_message = weather_predictor.predict(current_data, station_id)
        
        # 2. Prévision statistique simple (moyennes mobiles)
        statistical_forecast = {}
        
        # Moyennes sur différentes périodes
        temps_24h = [d.temperature for d in recent_data[:24] if d.temperature]
        temps_7d = [d.temperature for d in recent_data if d.temperature]
        
        if len(temps_24h) >= 12:
            # Tendance linéaire
            hours = np.arange(len(temps_24h))
            trend = np.polyfit(hours, temps_24h, 1)[0]
            
            statistical_forecast = {
                '6h': current_data.temperature + trend * 6,
                '12h': current_data.temperature + trend * 12,
                '24h': current_data.temperature + trend * 24
            }
        
        # 3. Prévision MetPy (persistence modifiée)
        metpy_forecast = {}
        
        if current_data.temperature and current_data.humidity and current_data.pressure:
            temp = current_data.temperature * units.celsius
            humidity = current_data.humidity * units.percent
            pressure = current_data.pressure * units.hPa
            
            # Évolution basée sur tendances physiques
            try:
                dewpoint = mpcalc.dewpoint_from_relative_humidity(temp, humidity)
                
                # Variation de température basée sur l'heure et la saison
                hour = current_data.timestamp.hour
                month = current_data.timestamp.month
                
                # Cycle diurne approximatif
                temp_variation = 3 * np.sin((hour - 6) * np.pi / 12)  # Max à 14h, min à 2h
                
                # Variation saisonnière (approximation)
                seasonal_factor = np.sin((month - 1) * np.pi / 6) * 2  # Variation ±2°C
                
                metpy_forecast = {
                    '6h': temp.magnitude + temp_variation * 0.3 + seasonal_factor * 0.1,
                    '12h': temp.magnitude + temp_variation * 0.6 + seasonal_factor * 0.2,
                    '24h': temp.magnitude + seasonal_factor * 0.4
                }
                
            except:
                metpy_forecast = {
                    '6h': current_data.temperature,
                    '12h': current_data.temperature,
                    '24h': current_data.temperature
                }
        
        # 4. Combinaison d'ensemble (moyenne pondérée)
        ensemble_forecast = {}
        
        for horizon in ['6h', '12h', '24h']:
            forecasts = []
            weights = []
            
            # ML (poids élevé si bon R²)
            if ml_predictions and f'temperature_{horizon}' in ml_predictions:
                ml_temp = ml_predictions[f'temperature_{horizon}'].get('value')
                ml_r2 = ml_predictions[f'temperature_{horizon}'].get('r2', 0)
                
                if ml_temp is not None:
                    forecasts.append(ml_temp)
                    weights.append(max(0.2, ml_r2))  # Poids minimum 0.2
            
            # Statistique
            if horizon in statistical_forecast:
                forecasts.append(statistical_forecast[horizon])
                weights.append(0.3)
            
            # MetPy
            if horizon in metpy_forecast:
                forecasts.append(metpy_forecast[horizon])
                weights.append(0.4)
            
            # Moyenne pondérée
            if forecasts and weights:
                ensemble_temp = np.average(forecasts, weights=weights)
                uncertainty = np.std(forecasts)  # Écart-type comme mesure d'incertitude
                
                ensemble_forecast[horizon] = {
                    'temperature': float(ensemble_temp),
                    'uncertainty': float(uncertainty),
                    'methods_used': len(forecasts),
                    'confidence': 1.0 - min(uncertainty / 5.0, 0.5)  # Confiance basée sur accord
                }
            else:
                ensemble_forecast[horizon] = {
                    'temperature': current_data.temperature,
                    'uncertainty': 5.0,
                    'methods_used': 0,
                    'confidence': 0.3
                }
        
        return jsonify({
            'station': {
                'id': station.id,
                'name': station.name
            },
            'current_conditions': {
                'temperature': current_data.temperature,
                'humidity': current_data.humidity,
                'pressure': current_data.pressure,
                'timestamp': current_data.timestamp.isoformat()
            },
            'ensemble_forecast': ensemble_forecast,
            'individual_forecasts': {
                'machine_learning': {horizon: ml_predictions.get(f'temperature_{horizon}', {}).get('value') 
                                   for horizon in ['6h', '12h', '24h']} if ml_predictions else {},
                'statistical': statistical_forecast,
                'metpy_physical': metpy_forecast
            },
            'forecast_method': 'Ensemble (ML + Statistical + MetPy)',
            'data_period': f'{len(recent_data)} heures',
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur prévision ensemble: {str(e)}'}), 500