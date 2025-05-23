import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
import requests

app = create_app()

def test_api_endpoints():
    """Teste tous les endpoints des modules"""
    base_url = "http://localhost:5000"
    
    endpoints = [
        # Aviation
        ("/api/aviation/test", "GET"),
        ("/api/aviation/stations", "GET"),
        ("/api/aviation/turbulence/1", "GET"),
        
        # Maritime
        ("/api/maritime/stations", "GET"),
        ("/api/maritime/conditions/1", "GET"),
        ("/api/maritime/tides/1", "GET"),
    ]
    
    print("🔍 Test des endpoints API...\n")
    
    with app.app_context():
        with app.test_client() as client:
            for endpoint, method in endpoints:
                print(f"Testing {method} {endpoint}...")
                
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json={})
                
                status = "✅" if response.status_code in [200, 404] else "❌"
                print(f"  {status} Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        print(f"  📦 Response: {list(data.keys())}")
                    except:
                        print("  ⚠️  Response is not JSON")
                
                print()

if __name__ == "__main__":
    test_api_endpoints()