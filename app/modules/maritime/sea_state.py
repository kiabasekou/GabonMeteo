# app/modules/maritime/sea_state.py
import math
from datetime import datetime, timedelta

class SeaStateCalculator:
    """Calculateur pour l'état de la mer et conditions maritimes"""
    
    # Échelle Douglas pour l'état de la mer
    DOUGLAS_SCALE = {
        0: {'description': 'Calme', 'height_range': (0, 0.1), 'conditions': 'Mer comme un miroir'},
        1: {'description': 'Ridée', 'height_range': (0.1, 0.5), 'conditions': 'Petites rides, pas d\'écume'},
        2: {'description': 'Belle', 'height_range': (0.5, 1.25), 'conditions': 'Vaguelettes courtes, crêtes d\'aspect vitreux'},
        3: {'description': 'Peu agitée', 'height_range': (1.25, 2.5), 'conditions': 'Petites vagues, crêtes commencent à déferler'},
        4: {'description': 'Agitée', 'height_range': (2.5, 4), 'conditions': 'Vagues modérées, moutons nombreux'},
        5: {'description': 'Assez forte', 'height_range': (4, 6), 'conditions': 'Grosses vagues, embruns possibles'},
        6: {'description': 'Forte', 'height_range': (6, 9), 'conditions': 'Lames très hautes, embruns denses'},
        7: {'description': 'Très forte', 'height_range': (9, 14), 'conditions': 'Lames déferlantes, traînées d\'écume'},
        8: {'description': 'Grosse', 'height_range': (14, 20), 'conditions': 'Lames exceptionnellement hautes'},
        9: {'description': 'Énorme', 'height_range': (20, float('inf')), 'conditions': 'Mer entièrement blanche'}
    }
    
    @staticmethod
    def calculate_sea_state(wind_speed, wind_duration_hours, fetch_distance_km):
        """
        Calcule l'état de la mer selon le vent
        wind_speed: vitesse en nœuds
        wind_duration_hours: durée du vent en heures
        fetch_distance_km: distance de fetch en km
        """
        # Conversion en unités métriques
        wind_speed_ms = wind_speed * 0.514444  # nœuds vers m/s
        
        # Formule de Sverdrup-Munk-Bretschneider (simplifiée)
        if wind_speed_ms <= 0:
            return 0
        
        # Hauteur significative des vagues
        H_max = 0.016 * (wind_speed_ms ** 2) / 9.81  # Hauteur max théorique
        
        # Facteur de limitation par le fetch
        fetch_factor = min(1.0, math.sqrt(fetch_distance_km / 100))
        
        # Facteur de durée
        duration_factor = min(1.0, wind_duration_hours / 24)
        
        # Hauteur significative ajustée
        wave_height = H_max * fetch_factor * duration_factor * 0.4
        
        # Déterminer l'état de la mer selon l'échelle Douglas
        for state, info in SeaStateCalculator.DOUGLAS_SCALE.items():
            if info['height_range'][0] <= wave_height < info['height_range'][1]:
                return state
        
        return 9  # Si c'est au-delà, c'est état 9
    
    @staticmethod
    def get_sea_state_info(sea_state):
        """Retourne les informations détaillées sur un état de la mer"""
        return SeaStateCalculator.DOUGLAS_SCALE.get(sea_state, SeaStateCalculator.DOUGLAS_SCALE[0])
    
    @staticmethod
    def calculate_wave_period(wave_height):
        """Calcule la période des vagues en fonction de leur hauteur"""
        # Formule approximative : T ≈ 3.5 * √H
        return round(3.5 * math.sqrt(max(0.1, wave_height)), 1)
    
    @staticmethod
    def calculate_navigation_safety(sea_state, wind_speed, visibility_km):
        """
        Évalue la sécurité de navigation
        """
        safety_score = 10
        
        # Déduction basée sur l'état de la mer
        if sea_state >= 7:
            safety_score -= 5
        elif sea_state >= 5:
            safety_score -= 3
        elif sea_state >= 3:
            safety_score -= 1
        
        # Déduction basée sur le vent
        if wind_speed >= 35:  # Force 8+
            safety_score -= 4
        elif wind_speed >= 25:  # Force 6-7
            safety_score -= 2
        elif wind_speed >= 17:  # Force 4-5
            safety_score -= 1
        
        # Déduction basée sur la visibilité
        if visibility_km < 0.5:
            safety_score -= 3
        elif visibility_km < 2:
            safety_score -= 2
        elif visibility_km < 5:
            safety_score -= 1
        
        # Déterminer le niveau de sécurité
        if safety_score >= 7:
            return {
                'level': 'SAFE',
                'color': 'green',
                'description': 'Conditions de navigation sûres',
                'recommendations': 'Navigation normale autorisée'
            }
        elif safety_score >= 4:
            return {
                'level': 'CAUTION',
                'color': 'yellow', 
                'description': 'Conditions nécessitant de la prudence',
                'recommendations': 'Navigation avec précaution, surveiller les conditions'
            }
        else:
            return {
                'level': 'DANGER',
                'color': 'red',
                'description': 'Conditions dangereuses pour la navigation',
                'recommendations': 'Éviter la navigation, rester au port'
            }
    
    @staticmethod
    def predict_tide_times(current_time, current_tide_height):
        """
        Prédiction simple des marées (simulation)
        En réalité, cela nécessiterait des données astronomiques complexes
        """
        # Cycle de marée approximatif : 12h25min
        tide_cycle = timedelta(hours=12, minutes=25)
        
        # Estimation simplifiée basée sur l'heure actuelle
        hours_since_midnight = current_time.hour + current_time.minute / 60
        
        # Prédiction basée sur un cycle sinusoïdal simple
        tide_phase = (hours_since_midnight / 12.416) * 2 * math.pi
        
        if math.sin(tide_phase) >= 0:
            # Marée montante
            next_high = current_time + timedelta(hours=(math.pi/2 - tide_phase % (2*math.pi)) / (2*math.pi) * 12.416)
            next_low = next_high + tide_cycle / 2
        else:
            # Marée descendante
            next_low = current_time + timedelta(hours=(3*math.pi/2 - tide_phase % (2*math.pi)) / (2*math.pi) * 12.416)
            next_high = next_low + tide_cycle / 2
        
        return {
            'next_high_tide': next_high,
            'next_low_tide': next_low,
            'tide_direction': 'montante' if math.sin(tide_phase) >= 0 else 'descendante'
        }

class TidalCalculator:
    """Calculateur spécialisé pour les marées"""
    
    @staticmethod
    def calculate_tidal_current(tide_phase, max_current_speed=2.0):
        """
        Calcule la vitesse du courant de marée
        tide_phase: phase de marée (0-1, où 0 = basse mer, 0.5 = haute mer)
        """
        # Le courant est maximal à mi-marée
        current_speed = max_current_speed * abs(math.sin(tide_phase * 2 * math.pi))
        
        # Direction du courant (simplifié)
        if 0 <= tide_phase < 0.5:
            direction = 'incoming'  # Courant entrant
        else:
            direction = 'outgoing'  # Courant sortant
        
        return {
            'speed': round(current_speed, 1),
            'direction': direction,
            'direction_degrees': 90 if direction == 'incoming' else 270
        }