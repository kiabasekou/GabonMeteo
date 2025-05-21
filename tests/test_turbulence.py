# tests/test_turbulence.py
import unittest
from app.modules.aviation.turbulence import TurbulenceIndex

class TestTurbulenceCalculation(unittest.TestCase):
    
    def test_calculate_turbulence_basic(self):
        """Test du calcul de base de turbulence"""
        result = TurbulenceIndex.calculate_turbulence_risk(
            wind_speed=20,
            wind_direction_variance=10,
            pressure_gradient=0.5,
            temperature_gradient=0.2
        )
        
        # Vérifier que le résultat est dans la plage attendue
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 10)
    
    def test_turbulence_severity_levels(self):
        """Test des niveaux de sévérité"""
        # Test niveau faible
        severity = TurbulenceIndex.get_turbulence_severity(1.5)
        self.assertEqual(severity['level'], 'LIGHT')
        
        # Test niveau élevé
        severity = TurbulenceIndex.get_turbulence_severity(8.5)
        self.assertEqual(severity['level'], 'SEVERE')
    
    def test_wind_shear_calculation(self):
        """Test du calcul de cisaillement"""
        wind_data = {
            1000: 15,  # 1000ft: 15 knots
            2000: 25,  # 2000ft: 25 knots
            3000: 30   # 3000ft: 30 knots
        }
        
        shear = TurbulenceIndex.calculate_wind_shear(wind_data)
        self.assertGreater(shear, 0)

if __name__ == '__main__':
    unittest.main()