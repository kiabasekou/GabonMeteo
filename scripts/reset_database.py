import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
import shutil

app = create_app()

with app.app_context():
    print("⚠️  ATTENTION: Ceci va supprimer toutes les données!")
    response = input("Êtes-vous sûr? (yes/no): ")
    
    if response.lower() == 'yes':
        # Supprimer l'ancienne base de données
        db_path = 'gabonmeteo.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            print("✅ Base de données supprimée")
        
        # Recréer toutes les tables
        db.create_all()
        print("✅ Tables recréées")
        
        print("\n📌 Maintenant, exécutez dans l'ordre:")
        print("1. python scripts/import_data.py data/sample_weather_data.csv")
        print("2. python scripts/initialize_modules_data.py")
    else:
        print("❌ Opération annulée")