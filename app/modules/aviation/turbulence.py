# app/modules/aviation/turbulence.py
class TurbulenceIndex:
    @staticmethod
    def calculate_turbulence_risk(wind_speed, wind_direction_variance=0, 
                                pressure_gradient=0, temperature_gradient=0):
        """Calcul simple de l'indice de turbulence"""
        base_index = wind_speed * 0.1
        direction_factor = wind_direction_variance / 100
        pressure_factor = abs(pressure_gradient) * 2
        temp_factor = abs(temperature_gradient) * 3
        
        turbulence_index = base_index + direction_factor + pressure_factor + temp_factor
        return min(turbulence_index, 10)
    
    @staticmethod
    def get_turbulence_severity(turbulence_index):
        """Retourne le niveau de sévérité"""
        if turbulence_index <= 2:
            return {'level': 'LIGHT', 'color': 'green', 'description': 'Turbulence légère'}
        elif turbulence_index <= 4:
            return {'level': 'MODERATE', 'color': 'yellow', 'description': 'Turbulence modérée'}
        elif turbulence_index <= 6:
            return {'level': 'MODERATE_TO_SEVERE', 'color': 'orange', 'description': 'Turbulence modérée à forte'}
        else:
            return {'level': 'SEVERE', 'color': 'red', 'description': 'Turbulence forte'}