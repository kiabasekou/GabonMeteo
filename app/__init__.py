from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    # Création de l'application Flask
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'votre_clé_secrète_provisoire'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gabonmeteo.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation des extensions avec l'application
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Import des modèles (après initialisation de db)
    from app.models import user, weather_data, agent
    
    # Import et enregistrement des blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.agent import agent_bp
    from app.routes.admin_agent import admin_agent_bp
    from app.routes.superadmin import superadmin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_agent_bp)
    app.register_blueprint(superadmin_bp)
    
    # Création des tables de la base de données
    with app.app_context():
        db.create_all()
        
        # Création d'un utilisateur administrateur par défaut si aucun n'existe
        if not user.User.query.filter_by(role='admin').first() and not user.User.query.filter_by(role='superadmin').first():
            admin = user.User(username='admin', email='admin@gabonmeteo.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Création d'un super administrateur par défaut
            superadmin = user.User(username='superadmin', email='superadmin@gabonmeteo.com', role='superadmin')
            superadmin.set_password('superadmin123')
            db.session.add(superadmin)
            
            db.session.commit()
        
        # Création des directions et services par défaut si nécessaire
        create_default_settings(app)
    
    return app

def create_default_settings(app):
    """Création des paramètres par défaut (directions, services)"""
    from app.models.agent import Direction, Service
    
    with app.app_context():
        # Création des directions si elles n'existent pas
        if Direction.query.count() == 0:
            directions = [
                ('Direction Générale', 'Direction Générale de la Météorologie'),
                ('Direction des Observations', 'Direction des Observations Météorologiques'),
                ('Direction des Prévisions', 'Direction des Prévisions Météorologiques'),
                ('Direction Administrative', 'Direction Administrative et Financière')
            ]
            
            for name, desc in directions:
                direction = Direction(name=name, description=desc)
                db.session.add(direction)
            
            db.session.commit()
        
        # Création des services si ils n'existent pas
        if Service.query.count() == 0:
            # Récupérer les directions
            dir_generale = Direction.query.filter_by(name='Direction Générale').first()
            dir_observations = Direction.query.filter_by(name='Direction des Observations').first()
            dir_previsions = Direction.query.filter_by(name='Direction des Prévisions').first()
            dir_admin = Direction.query.filter_by(name='Direction Administrative').first()
            
            services = [
                ('Cabinet', 'Cabinet du Directeur Général', dir_generale.id if dir_generale else None),
                ('Service des Stations', 'Service de gestion des stations météorologiques', dir_observations.id if dir_observations else None),
                ('Service de la Climatologie', 'Service de la climatologie', dir_observations.id if dir_observations else None),
                ('Service des Prévisions', 'Service des prévisions météorologiques', dir_previsions.id if dir_previsions else None),
                ('Service des Alertes', 'Service des alertes météorologiques', dir_previsions.id if dir_previsions else None),
                ('Service des Ressources Humaines', 'Service des ressources humaines', dir_admin.id if dir_admin else None),
                ('Service Financier', 'Service financier et comptable', dir_admin.id if dir_admin else None)
            ]
            
            for name, desc, dir_id in services:
                if dir_id:  # Ne créer que si une direction associée existe
                    service = Service(name=name, description=desc, direction_id=dir_id)
                    db.session.add(service)
            
            db.session.commit()
        
        # Création du dossier config s'il n'existe pas
        os.makedirs('app/config', exist_ok=True)