# scripts/migrate_to_dgm_structure.py
"""
Script de migration pour adapter GabonMétéo+ à la structure officielle de la DGM
Basé sur le décret n°0768/PR/MERN du 22 août 2008
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User
from app.models.agent import Direction, Service, AgentDGM
from app.models.weather_data import WeatherStation
from datetime import datetime

def create_dgm_structure():
    """Crée la structure organisationnelle officielle de la DGM"""
    
    app = create_app()
    
    with app.app_context():
        print("🏢 Migration vers la structure officielle DGM...")
        
        # 1. Supprimer l'ancienne structure (si nécessaire)
        print("📋 Nettoyage de l'ancienne structure...")
        Service.query.delete()
        Direction.query.delete()
        db.session.commit()
        
        # 2. Créer les Divisions selon le décret
        print("🔨 Création des Divisions officielles...")
        
        divisions_data = [
            {
                'name': 'Direction Générale',
                'description': 'Direction Générale de la Météorologie',
                'code': 'DG'
            },
            {
                'name': 'Division Administrative et Financière',
                'description': 'Gestion administrative, financière et des ressources humaines',
                'code': 'DAF'
            },
            {
                'name': 'Division des Études et de la Recherche',
                'description': 'Études climatologiques, recherche et météorologie spécialisée',
                'code': 'DER'
            },
            {
                'name': 'Division des Observations',
                'description': 'Réseau d\'observation, stations et instrumentation',
                'code': 'DO'
            },
            {
                'name': 'Division des Prévisions',
                'description': 'Prévisions météorologiques, alertes et diffusion',
                'code': 'DP'
            }
        ]
        
        divisions = {}
        for div_data in divisions_data:
            division = Direction(
                name=div_data['name'],
                description=div_data['description']
            )
            db.session.add(division)
            db.session.flush()  # Pour obtenir l'ID
            divisions[div_data['code']] = division
            print(f"   ✅ {div_data['name']}")
        
        db.session.commit()
        
        # 3. Créer les Services selon l'organigramme
        print("🔧 Création des Services...")
        
        services_data = [
            # Direction Générale
            {
                'name': 'Secrétariat Particulier',
                'description': 'Secrétariat du Directeur Général',
                'division': 'DG',
                'code': 'SP'
            },
            {
                'name': 'Cellule de Communication',
                'description': 'Communication institutionnelle et relations publiques',
                'division': 'DG',
                'code': 'CC'
            },
            
            # Division Administrative et Financière
            {
                'name': 'Service du Personnel',
                'description': 'Gestion des ressources humaines et formation',
                'division': 'DAF',
                'code': 'SP'
            },
            {
                'name': 'Service Financier et Comptable',
                'description': 'Gestion financière, comptabilité et budget',
                'division': 'DAF',
                'code': 'SFC'
            },
            {
                'name': 'Service de la Logistique',
                'description': 'Approvisionnement, équipements et infrastructure',
                'division': 'DAF',
                'code': 'SL'
            },
            
            # Division des Études et de la Recherche
            {
                'name': 'Service de la Climatologie',
                'description': 'Études climatologiques et analyses historiques',
                'division': 'DER',
                'code': 'SC'
            },
            {
                'name': 'Service de l\'Agro-météorologie',
                'description': 'Météorologie agricole et services aux secteurs',
                'division': 'DER',
                'code': 'SAM'
            },
            {
                'name': 'Service de la Météorologie Aéronautique',
                'description': 'Services météorologiques pour l\'aviation',
                'division': 'DER',
                'code': 'SMA'
            },
            
            # Division des Observations
            {
                'name': 'Service des Stations Météorologiques',
                'description': 'Gestion et exploitation du réseau de stations',
                'division': 'DO',
                'code': 'SSM'
            },
            {
                'name': 'Service de l\'Instrumentation',
                'description': 'Instruments météorologiques et métrologie',
                'division': 'DO',
                'code': 'SI'
            },
            {
                'name': 'Service de la Maintenance',
                'description': 'Maintenance des équipements et infrastructure',
                'division': 'DO',
                'code': 'SM'
            },
            
            # Division des Prévisions
            {
                'name': 'Service des Prévisions Météorologiques',
                'description': 'Élaboration des prévisions météorologiques',
                'division': 'DP',
                'code': 'SPM'
            },
            {
                'name': 'Service de la Diffusion',
                'description': 'Diffusion des bulletins et informations météo',
                'division': 'DP',
                'code': 'SD'
            },
            {
                'name': 'Service des Alertes Météorologiques',
                'description': 'Surveillance et émission des alertes météo',
                'division': 'DP',
                'code': 'SAM'
            }
        ]
        
        services = {}
        for serv_data in services_data:
            service = Service(
                name=serv_data['name'],
                description=serv_data['description'],
                direction_id=divisions[serv_data['division']].id
            )
            db.session.add(service)
            db.session.flush()
            services[serv_data['code']] = service
            print(f"   ✅ {serv_data['name']} ({divisions[serv_data['division']].name})")
        
        db.session.commit()
        
        # 4. Créer les utilisateurs par défaut selon la hiérarchie
        print("👥 Création des utilisateurs par défaut...")
        
        default_users = [
            {
                'username': 'directeur_general',
                'email': 'dg@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_general',
                'service': None  # Direction générale
            },
            {
                'username': 'directeur_adjoint',
                'email': 'adjoint@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_adjoint',
                'service': None
            },
            {
                'username': 'dir_administrative',
                'email': 'admin@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_division',
                'service': 'SP'  # Service du Personnel
            },
            {
                'username': 'dir_observations',
                'email': 'observations@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_division',
                'service': 'SSM'  # Service des Stations
            },
            {
                'username': 'dir_previsions',
                'email': 'previsions@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_division',
                'service': 'SPM'  # Service des Prévisions
            },
            {
                'username': 'dir_etudes',
                'email': 'etudes@dgm.ga',
                'password': 'dgm2025!',
                'role': 'directeur_division',
                'service': 'SC'  # Service Climatologie
            },
            {
                'username': 'chef_stations',
                'email': 'stations@dgm.ga',
                'password': 'dgm2025!',
                'role': 'chef_service',
                'service': 'SSM'
            },
            {
                'username': 'agent_libreville',
                'email': 'libreville@dgm.ga',
                'password': 'dgm2025!',
                'role': 'agent_dgm',
                'service': 'SSM'
            }
        ]
        
        for user_data in default_users:
            # Vérifier si l'utilisateur existe déjà
            existing = User.query.filter_by(username=user_data['username']).first()
            if not existing:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                db.session.flush()
                
                # Créer l'agent DGM correspondant si c'est un agent
                if user_data['role'] in ['directeur_division', 'chef_service', 'agent_dgm']:
                    agent = AgentDGM(
                        matricule=f"DGM{user.id:04d}",
                        user_id=user.id,
                        date_naissance=datetime(1980, 1, 1).date(),
                        fonction=get_fonction_from_role(user_data['role']),
                        service_id=services[user_data['service']].id if user_data['service'] else None
                    )
                    db.session.add(agent)
                
                print(f"   ✅ {user_data['username']} ({user_data['role']})")
        
        db.session.commit()
        
        # 5. Créer les centres régionaux (structure déconcentrée)
        print("🌍 Création des centres régionaux...")
        
        centres_regionaux = [
            {
                'name': 'Centre Météorologique de Libreville',
                'region': 'Estuaire',
                'type': 'centre_regional'
            },
            {
                'name': 'Centre Météorologique de Port-Gentil',
                'region': 'Ogooué-Maritime',
                'type': 'centre_regional'
            },
            {
                'name': 'Centre Météorologique de Franceville',
                'region': 'Haut-Ogooué',
                'type': 'centre_regional'
            }
        ]
        
        for centre in centres_regionaux:
            print(f"   ✅ {centre['name']}")
        
        print("\n🎉 Migration terminée avec succès!")
        print("\n📋 Récapitulatif:")
        print(f"   - {len(divisions_data)} Divisions créées")
        print(f"   - {len(services_data)} Services créés")
        print(f"   - {len(default_users)} Utilisateurs créés")
        print(f"   - {len(centres_regionaux)} Centres régionaux définis")
        
        print("\n🔐 Comptes par défaut:")
        print("   Directeur Général: directeur_general / dgm2025!")
        print("   Directeur Adjoint: directeur_adjoint / dgm2025!")
        print("   Dir. Administrative: dir_administrative / dgm2025!")
        print("   Dir. Observations: dir_observations / dgm2025!")
        print("   Dir. Prévisions: dir_previsions / dgm2025!")
        print("   Dir. Études: dir_etudes / dgm2025!")

def get_fonction_from_role(role):
    """Retourne la fonction correspondant au rôle"""
    roles_fonctions = {
        'directeur_general': 'Directeur Général',
        'directeur_adjoint': 'Directeur Général Adjoint',
        'directeur_division': 'Directeur de Division',
        'chef_service': 'Chef de Service',
        'agent_dgm': 'Agent Météorologique'
    }
    return roles_fonctions.get(role, 'Agent DGM')

def create_stations_hierarchy():
    """Organise les stations selon la hiérarchie régionale"""
    
    print("\n🏢 Organisation des stations par centres régionaux...")
    
    # Mapper les stations existantes aux centres régionaux
    station_mapping = {
        'Libreville': 'Centre Météorologique de Libreville',
        'Port-Gentil': 'Centre Météorologique de Port-Gentil', 
        'Franceville': 'Centre Météorologique de Franceville',
        'Lambaréné': 'Centre Météorologique de Libreville',  # Rattaché à Libreville
        'Oyem': 'Centre Météorologique de Libreville'  # Rattaché à Libreville
    }
    
    stations = WeatherStation.query.all()
    for station in stations:
        if station.name in station_mapping:
            centre = station_mapping[station.name]
            print(f"   📍 {station.name} → {centre}")

if __name__ == "__main__":
    print("🚀 Démarrage de la migration vers la structure DGM officielle...")
    create_dgm_structure()
    create_stations_hierarchy()
    print("\n✅ Migration complète!")